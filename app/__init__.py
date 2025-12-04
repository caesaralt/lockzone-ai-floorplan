"""
Lockzone AI Floorplan - Application Package

This package contains the modular backend structure:
- api/: HTTP route handlers (Flask Blueprints)
- services/: Business logic (pure Python)
- utils/: Shared utility functions

The app factory and core Flask setup remain in app_init.py at the project root.
This package provides the modular route organization.

STORAGE POLICY:
- Production: DATABASE_URL is REQUIRED. JSON persistence for CRM/auth/kanban is disabled.
- Development: Database preferred, JSON fallback allowed if no DATABASE_URL.
- Session/config JSON files (CAD, PDF autosave, automation_data.json) are always allowed.
"""

from flask import Blueprint
import logging

logger = logging.getLogger(__name__)

# Import blueprints
from app.api.pages import pages_bp
from app.api.auth_routes import auth_bp
from app.api.admin import admin_bp
from app.api.misc import misc_bp
from app.api.learning import learning_bp
from app.api.simpro import simpro_bp
from app.api.kanban import kanban_bp
from app.api.pdf_editor import pdf_editor_bp
from app.api.ai_mapping import ai_mapping_bp
from app.api.board_builder import board_builder_bp
from app.api.canvas import canvas_bp
from app.api.electrical_cad import electrical_cad_bp
from app.api.quote_automation import quote_automation_bp
from app.api.crm import crm_bp
from app.api.dashboard import dashboard_bp
from app.api.ai_chat import ai_chat_bp
from app.api.scheduler import scheduler_bp
from app.api.crm_extended import crm_extended_bp
from app.api.crm_resources import crm_resources_bp
from app.api.crm_google import crm_google_bp
from app.api.crm_integration import crm_integration_bp
from app.api.crm_v2 import crm_v2_bp


def validate_storage_policy():
    """
    Validate storage configuration at startup.
    
    MUST be called during app initialization to enforce:
    - Production requires DATABASE_URL
    - JSON persistence is disabled in production for CRM/auth/kanban
    
    Raises:
        RuntimeError: If production mode without DATABASE_URL
    """
    from config import validate_storage_config, get_app_env, has_database, get_storage_mode
    
    env = get_app_env()
    db_configured = has_database()
    storage_mode = get_storage_mode()
    
    logger.info(f"🔧 Environment: {env.upper()}")
    logger.info(f"🗄️  Database configured: {db_configured}")
    logger.info(f"💾 Storage mode: {storage_mode}")
    
    # This will raise RuntimeError if production without DB
    validate_storage_config()
    
    if storage_mode == 'database':
        logger.info("✅ Using PostgreSQL database for CRM/auth/kanban data")
    elif storage_mode == 'json_fallback':
        logger.warning("⚠️  Using JSON file fallback for CRM/auth/kanban (development mode only)")
    
    return storage_mode


def register_blueprints(app, app_functions=None):
    """
    Register all API blueprints with the Flask app.
    Called from the main app.py after app creation.
    
    Args:
        app: Flask application instance
        app_functions: Dictionary of functions to inject into blueprints
    
    Raises:
        RuntimeError: If production mode without DATABASE_URL configured
    """
    # Validate storage policy FIRST (fail fast in production without DB)
    storage_mode = validate_storage_policy()
    app.config['STORAGE_MODE'] = storage_mode
    
    # Store app functions for blueprints to access
    if app_functions:
        app.config['APP_FUNCTIONS'] = app_functions
    
    # Register blueprints
    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(misc_bp)
    app.register_blueprint(learning_bp)
    app.register_blueprint(simpro_bp)
    app.register_blueprint(kanban_bp)
    app.register_blueprint(pdf_editor_bp)
    app.register_blueprint(ai_mapping_bp)
    app.register_blueprint(board_builder_bp)
    app.register_blueprint(canvas_bp)
    app.register_blueprint(electrical_cad_bp)
    app.register_blueprint(quote_automation_bp)
    app.register_blueprint(crm_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(ai_chat_bp)
    app.register_blueprint(scheduler_bp)
    app.register_blueprint(crm_extended_bp)
    app.register_blueprint(crm_resources_bp)
    app.register_blueprint(crm_google_bp)
    app.register_blueprint(crm_integration_bp)
    app.register_blueprint(crm_v2_bp)


__all__ = ['register_blueprints', 'validate_storage_policy', 'app', 'pages_bp', 'auth_bp', 'admin_bp', 'misc_bp', 'learning_bp', 'simpro_bp', 'kanban_bp', 'pdf_editor_bp', 'ai_mapping_bp', 'board_builder_bp', 'canvas_bp', 'electrical_cad_bp', 'quote_automation_bp', 'crm_bp', 'dashboard_bp', 'ai_chat_bp', 'scheduler_bp', 'crm_extended_bp', 'crm_resources_bp', 'crm_google_bp', 'crm_integration_bp', 'crm_v2_bp']


# ==============================================================================
# WSGI APP EXPORT FOR GUNICORN
# ==============================================================================
# This allows gunicorn to run with: gunicorn app:app
# The Flask app is created in application.py.
# We use __getattr__ for lazy loading to avoid circular import issues.
# ==============================================================================

_flask_app = None

def __getattr__(name):
    """Lazy load the Flask app to avoid circular imports."""
    global _flask_app
    if name == 'app':
        if _flask_app is None:
            from application import app as flask_app
            _flask_app = flask_app
        return _flask_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
