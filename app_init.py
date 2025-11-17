"""
Application Initialization Module
Properly initializes Flask app with all infrastructure components
"""
import os
from flask import Flask
from config import get_config
from logging_config import setup_logging
from ai_service import AIService
from security import setup_security
from health_checks import register_health_checks
import logging

logger = logging.getLogger(__name__)


def create_app():
    """
    Application factory that creates and configures Flask app with all infrastructure

    Returns:
        Configured Flask application instance
    """
    # Create Flask app
    app = Flask(__name__)

    # Load configuration
    config_class = get_config()
    app.config.from_object(config_class)

    logger_instance = setup_logging(app)

    logger.info("=" * 60)
    logger.info("🚀 Initializing Lockzone AI Floorplan Application")
    logger.info("=" * 60)
    logger.info(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    logger.info(f"Debug mode: {app.debug}")

    # Setup security (CORS, headers, error handlers)
    setup_security(app, app.config)

    # Create required directories
    create_required_directories(app)

    # Initialize AI service
    ai_service = initialize_ai_service(app)
    app.ai_service = ai_service

    # Register health check endpoints
    register_health_checks(app)

    logger.info("✅ Application initialization complete")
    logger.info("=" * 60)

    return app


def create_required_directories(app):
    """
    Create all required application directories

    Args:
        app: Flask application instance
    """
    directories = [
        app.config['UPLOAD_FOLDER'],
        app.config['OUTPUT_FOLDER'],
        app.config['DATA_FOLDER'],
        app.config['LEARNING_FOLDER'],
        app.config['SIMPRO_CONFIG_FOLDER'],
        app.config['CRM_DATA_FOLDER'],
        app.config['AI_MAPPING_FOLDER'],
        app.config['MAPPING_LEARNING_FOLDER'],
        app.config['SESSION_DATA_FOLDER'],
        app.config['CAD_SESSIONS_FOLDER'],
        'logs'
    ]

    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            logger.debug(f"Directory ensured: {directory}")
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {e}")

    logger.info(f"✅ Created {len(directories)} required directories")


def initialize_ai_service(app):
    """
    Initialize centralized AI service manager

    Args:
        app: Flask application instance

    Returns:
        AIService instance
    """
    try:
        ai_service = AIService(app.config)

        # Log which services are available
        available_services = []
        if ai_service.is_available('claude'):
            available_services.append('Claude')
        if ai_service.is_available('gpt4'):
            available_services.append('GPT-4')
        if ai_service.is_available('search'):
            available_services.append('Tavily Search')

        if available_services:
            logger.info(f"✅ AI Services initialized: {', '.join(available_services)}")
        else:
            logger.warning("⚠️  No AI services configured - check API keys")

        return ai_service

    except Exception as e:
        logger.error(f"Failed to initialize AI service: {e}")
        # Return a dummy AI service to prevent crashes
        return AIService(app.config)


def get_ai_service(app):
    """
    Get the AI service instance from the app

    Args:
        app: Flask application instance

    Returns:
        AIService instance
    """
    if not hasattr(app, 'ai_service'):
        logger.warning("AI service not initialized, creating new instance")
        app.ai_service = AIService(app.config)

    return app.ai_service
