"""
Health Check & Monitoring Endpoints
Provides endpoints for Render deployment health checks and monitoring
"""
import os
import sys
import time
import psutil
from datetime import datetime
from typing import Dict, Any
from flask import Blueprint, jsonify
import logging

logger = logging.getLogger(__name__)

# Create Blueprint for health check routes
health_bp = Blueprint('health', __name__)

# Track application start time
START_TIME = time.time()


def get_system_metrics() -> Dict[str, Any]:
    """
    Get basic system metrics

    Returns:
        Dictionary of system metrics
    """
    try:
        process = psutil.Process()

        return {
            'cpu_percent': process.cpu_percent(interval=0.1),
            'memory_mb': process.memory_info().rss / 1024 / 1024,
            'memory_percent': process.memory_percent(),
            'threads': process.num_threads(),
            'open_files': len(process.open_files()),
        }
    except Exception as e:
        logger.warning(f"Failed to get system metrics: {e}")
        return {}


def get_uptime() -> Dict[str, Any]:
    """
    Get application uptime

    Returns:
        Dictionary with uptime information
    """
    uptime_seconds = time.time() - START_TIME

    return {
        'uptime_seconds': round(uptime_seconds, 2),
        'uptime_minutes': round(uptime_seconds / 60, 2),
        'uptime_hours': round(uptime_seconds / 3600, 2),
        'started_at': datetime.fromtimestamp(START_TIME).isoformat()
    }


def check_ai_services(app) -> Dict[str, bool]:
    """
    Check if AI services are configured

    Args:
        app: Flask application instance

    Returns:
        Dictionary of service availability
    """
    services = {
        'anthropic_claude': bool(app.config.get('ANTHROPIC_API_KEY')),
        'openai_gpt4': bool(app.config.get('OPENAI_API_KEY')),
        'tavily_search': bool(app.config.get('TAVILY_API_KEY'))
    }

    return services


def check_filesystem() -> Dict[str, bool]:
    """
    Check if required directories exist and are writable

    Returns:
        Dictionary of filesystem checks
    """
    required_dirs = [
        'uploads',
        'outputs',
        'data',
        'learning_data',
        'logs'
    ]

    filesystem_status = {}

    for dir_name in required_dirs:
        dir_path = os.path.join(os.getcwd(), dir_name)
        exists = os.path.exists(dir_path)
        writable = os.access(dir_path, os.W_OK) if exists else False

        filesystem_status[dir_name] = {
            'exists': exists,
            'writable': writable,
            'healthy': exists and writable
        }

    return filesystem_status


@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Basic health check endpoint
    Returns 200 if application is running

    Used by: Render health checks, monitoring tools
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'lockzone-ai-floorplan'
    }), 200


@health_bp.route('/ready', methods=['GET'])
def readiness_check():
    """
    Readiness probe endpoint
    Returns 200 if application is ready to serve requests

    Used by: Render deployment, load balancers
    """
    from flask import current_app

    try:
        # Check AI services
        ai_services = check_ai_services(current_app)
        has_ai_service = any(ai_services.values())

        # Check filesystem
        filesystem = check_filesystem()
        filesystem_healthy = all(
            status['healthy'] for status in filesystem.values()
        )

        # Overall readiness
        is_ready = has_ai_service and filesystem_healthy

        response = {
            'status': 'ready' if is_ready else 'not_ready',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {
                'ai_services': ai_services,
                'filesystem': filesystem,
                'has_ai_service': has_ai_service,
                'filesystem_healthy': filesystem_healthy
            }
        }

        status_code = 200 if is_ready else 503

        return jsonify(response), status_code

    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503


@health_bp.route('/metrics', methods=['GET'])
def metrics():
    """
    Basic metrics endpoint
    Returns system metrics and application statistics

    Used by: Monitoring dashboards, performance analysis
    """
    from flask import current_app

    try:
        response = {
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'lockzone-ai-floorplan',
            'version': '2.0.0',
            'environment': os.environ.get('FLASK_ENV', 'production'),
            'uptime': get_uptime(),
            'system': get_system_metrics(),
            'services': check_ai_services(current_app),
            'filesystem': check_filesystem(),
            'python_version': sys.version.split()[0]
        }

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@health_bp.route('/ping', methods=['GET'])
def ping():
    """
    Simple ping endpoint
    Returns immediate response for basic connectivity tests
    """
    return 'pong', 200


def register_health_checks(app):
    """
    Register health check blueprint with Flask app

    Args:
        app: Flask application instance
    """
    app.register_blueprint(health_bp, url_prefix='/api')
    logger.info("Health check endpoints registered")
    logger.info("Available endpoints: /api/health, /api/ready, /api/metrics, /api/ping")
