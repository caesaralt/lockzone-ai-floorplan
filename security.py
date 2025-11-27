"""
Security Utilities & Middleware
Provides security hardening for production deployment
"""
import os
import secrets
from functools import wraps
from typing import Callable, Dict, Any, Optional
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import logging

logger = logging.getLogger(__name__)


class SecurityConfig:
    """Security configuration and validation"""

    @staticmethod
    def generate_secret_key() -> str:
        """
        Generate a cryptographically secure secret key

        Returns:
            Hex-encoded secret key
        """
        return secrets.token_hex(32)

    @staticmethod
    def validate_secret_key(secret_key: str) -> bool:
        """
        Validate that secret key is sufficiently secure

        Args:
            secret_key: Secret key to validate

        Returns:
            True if key is secure, False otherwise
        """
        if not secret_key:
            return False

        # Check minimum length (32 characters for 128-bit security)
        if len(secret_key) < 32:
            logger.warning("Secret key is too short (minimum 32 characters)")
            return False

        # Check if it's a default/weak key
        weak_keys = ['dev', 'test', 'secret', 'password', '12345']
        if any(weak in secret_key.lower() for weak in weak_keys):
            logger.warning("Secret key appears to be weak or default")
            return False

        return True

    @staticmethod
    def ensure_secret_key(config: Dict[str, Any]) -> str:
        """
        Ensure a secure secret key is configured

        Args:
            config: Application configuration dictionary

        Returns:
            Secure secret key
        """
        secret_key = config.get('SECRET_KEY')

        # If no key or invalid key, generate a secure one
        if not secret_key or not SecurityConfig.validate_secret_key(secret_key):
            if os.environ.get('FLASK_ENV') == 'production':
                logger.error("No secure SECRET_KEY in production! Generating one...")
                logger.error("Add SECRET_KEY to environment variables for persistence!")

            secret_key = SecurityConfig.generate_secret_key()
            logger.warning(f"Generated new secret key (length: {len(secret_key)})")

        return secret_key


def setup_security_headers(app: Flask):
    """
    Add security headers to all responses

    Args:
        app: Flask application instance
    """
    @app.after_request
    def add_security_headers(response: Response) -> Response:
        """Add security headers to response"""

        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'

        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # Enable XSS protection
        response.headers['X-XSS-Protection'] = '1; mode=block'

        # Strict Transport Security (HTTPS only in production)
        if not app.debug:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        # Content Security Policy (relaxed for development and production)
        # Allow all CDN resources needed by the app
        csp = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' cdn.tailwindcss.com cdn.jsdelivr.net cdnjs.cloudflare.com unpkg.com; "
            "style-src 'self' 'unsafe-inline' cdn.tailwindcss.com fonts.googleapis.com cdnjs.cloudflare.com unpkg.com; "
            "style-src-elem 'self' 'unsafe-inline' cdn.tailwindcss.com fonts.googleapis.com cdnjs.cloudflare.com unpkg.com; "
            "font-src 'self' fonts.gstatic.com data:; "
            "img-src 'self' data: blob: *; "
            "connect-src 'self' *;"
        )
        response.headers['Content-Security-Policy'] = csp

        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions Policy (formerly Feature Policy)
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

        return response

    logger.info("Security headers configured")


def setup_cors(app: Flask, config: Dict[str, Any]):
    """
    Configure CORS with security best practices

    Args:
        app: Flask application instance
        config: Application configuration dictionary
    """
    cors_origins = config.get('CORS_ORIGINS', ['*'])
    cors_methods = config.get('CORS_METHODS', ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    cors_headers = config.get('CORS_ALLOW_HEADERS', ['Content-Type', 'Authorization'])

    # Warn if using wildcard CORS in production
    if not app.debug and '*' in cors_origins:
        logger.warning("⚠️  Using wildcard CORS in production! Set CORS_ORIGINS environment variable.")

    CORS(
        app,
        origins=cors_origins,
        methods=cors_methods,
        allow_headers=cors_headers,
        supports_credentials=True,
        max_age=3600
    )

    logger.info(f"CORS configured: origins={cors_origins}")


def require_api_key(f: Callable) -> Callable:
    """
    Decorator to require API key for endpoint access

    Usage:
        @app.route('/api/secure-endpoint')
        @require_api_key
        def secure_endpoint():
            return {'data': 'secure'}
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')

        if not api_key:
            logger.warning(f"Missing API key for {request.path}")
            return jsonify({'error': 'API key required'}), 401

        # Validate API key (implement your validation logic)
        expected_key = os.environ.get('API_KEY')
        if expected_key and api_key != expected_key:
            logger.warning(f"Invalid API key for {request.path}")
            return jsonify({'error': 'Invalid API key'}), 403

        return f(*args, **kwargs)

    return decorated_function


def sanitize_error_response(error: Exception, include_details: bool = False) -> Dict[str, Any]:
    """
    Sanitize error response to prevent information leakage

    Args:
        error: Exception object
        include_details: Whether to include detailed error info (dev only)

    Returns:
        Sanitized error response dictionary
    """
    error_response = {
        'error': 'Internal Server Error',
        'message': 'An error occurred while processing your request'
    }

    # Only include details in development
    if include_details:
        error_response['details'] = str(error)
        error_response['type'] = type(error).__name__

    return error_response


def setup_error_handlers(app: Flask):
    """
    Register secure error handlers that don't expose stack traces

    Args:
        app: Flask application instance
    """
    include_details = app.debug

    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request"""
        return jsonify({
            'error': 'Bad Request',
            'message': 'The request could not be understood or was missing required parameters'
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        """Handle 401 Unauthorized"""
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Authentication required'
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 Forbidden"""
        return jsonify({
            'error': 'Forbidden',
            'message': 'You do not have permission to access this resource'
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found"""
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found'
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle 405 Method Not Allowed"""
        return jsonify({
            'error': 'Method Not Allowed',
            'message': 'The method is not allowed for the requested URL'
        }), 405

    @app.errorhandler(413)
    def request_entity_too_large(error):
        """Handle 413 Payload Too Large"""
        return jsonify({
            'error': 'Payload Too Large',
            'message': 'The uploaded file or request is too large'
        }), 413

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        """Handle 429 Too Many Requests"""
        return jsonify({
            'error': 'Rate Limit Exceeded',
            'message': 'Too many requests. Please try again later'
        }), 429

    @app.errorhandler(500)
    def internal_server_error(error):
        """Handle 500 Internal Server Error"""
        logger.error(f"Internal server error: {error}", exc_info=True)
        return jsonify(sanitize_error_response(error, include_details)), 500

    @app.errorhandler(503)
    def service_unavailable(error):
        """Handle 503 Service Unavailable"""
        return jsonify({
            'error': 'Service Unavailable',
            'message': 'The service is temporarily unavailable. Please try again later'
        }), 503

    logger.info("Error handlers registered")


def setup_request_logging(app: Flask):
    """
    Setup request/response logging for security monitoring

    Args:
        app: Flask application instance
    """
    @app.before_request
    def log_request():
        """Log incoming requests"""
        # Don't log health checks to reduce noise
        if request.path in ['/api/health', '/api/ping']:
            return

        logger.info(
            f"Request: {request.method} {request.path} "
            f"from {request.remote_addr} "
            f"User-Agent: {request.user_agent.string[:100]}"
        )

    @app.after_request
    def log_response(response: Response) -> Response:
        """Log outgoing responses"""
        # Don't log health checks
        if request.path in ['/api/health', '/api/ping']:
            return response

        logger.info(
            f"Response: {request.method} {request.path} "
            f"status={response.status_code} "
            f"size={response.content_length}"
        )

        return response

    logger.info("Request logging configured")


def validate_environment_variables(required_vars: list, app: Flask):
    """
    Validate that required environment variables are set

    Args:
        required_vars: List of required environment variable names
        app: Flask application instance
    """
    missing_vars = []

    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
            logger.warning(f"Missing environment variable: {var}")

    if missing_vars and not app.debug:
        logger.error(f"Missing required environment variables in production: {missing_vars}")
        logger.error("Application may not function correctly!")

    return len(missing_vars) == 0


def setup_security(app: Flask, config: Dict[str, Any]):
    """
    Setup all security features for the application

    Args:
        app: Flask application instance
        config: Application configuration dictionary
    """
    logger.info("Configuring application security...")

    # Ensure secure secret key
    app.secret_key = SecurityConfig.ensure_secret_key(config)

    # Setup CORS
    setup_cors(app, config)

    # Setup security headers
    setup_security_headers(app)

    # Setup error handlers
    setup_error_handlers(app)

    # Setup request logging
    setup_request_logging(app)

    # Validate environment in production
    if not app.debug:
        validate_environment_variables(
            ['ANTHROPIC_API_KEY', 'SECRET_KEY'],
            app
        )

    logger.info("✅ Security configuration complete")
