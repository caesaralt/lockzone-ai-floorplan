"""
Centralized Configuration for Lockzone AI Floorplan Application
Manages environment-specific settings, secrets, and service configurations.
"""
import os
from datetime import timedelta

class Config:
    """Base configuration with defaults"""

    # Flask Settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32).hex()
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file upload

    # CORS Settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization', 'X-Requested-With']

    # Database Settings
    USE_DATABASE = os.environ.get('USE_DATABASE', 'false').lower() == 'true'
    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://localhost/lockzone_ai')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # File Storage Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_FOLDER = 'uploads'
    OUTPUT_FOLDER = 'outputs'
    DATA_FOLDER = 'data'
    LEARNING_FOLDER = 'learning_data'
    SIMPRO_CONFIG_FOLDER = 'simpro_config'
    CRM_DATA_FOLDER = 'crm_data'
    AI_MAPPING_FOLDER = 'ai_mapping'
    MAPPING_LEARNING_FOLDER = 'mapping_learning'
    SESSION_DATA_FOLDER = 'session_data'
    CAD_SESSIONS_FOLDER = 'cad_sessions'

    # AI Service API Keys
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    TAVILY_API_KEY = os.environ.get('TAVILY_API_KEY')

    # AI Model Configuration
    AI_MODELS = {
        'claude': {
            'model': 'claude-sonnet-4-20250514',
            'max_tokens': 16000,
            'temperature': 0.7,
            'thinking_budget': 8000,
        },
        'gpt4': {
            'model': 'gpt-4',
            'max_tokens': 2000,
            'temperature': 0.7,
        },
    }

    # AI Retry Configuration
    AI_RETRY_ATTEMPTS = int(os.environ.get('AI_RETRY_ATTEMPTS', '3'))
    AI_RETRY_DELAY = int(os.environ.get('AI_RETRY_DELAY', '2'))  # seconds
    AI_TIMEOUT = int(os.environ.get('AI_TIMEOUT', '120'))  # seconds

    # Rate Limiting
    RATELIMIT_ENABLED = os.environ.get('RATELIMIT_ENABLED', 'true').lower() == 'true'
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '100 per hour')
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')

    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = os.environ.get('LOG_FILE', 'app.log')

    # Session Configuration
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)


class DevelopmentConfig(Config):
    """Development-specific configuration"""
    DEBUG = True
    TESTING = False
    LOG_LEVEL = 'DEBUG'
    # Allow all CORS in development
    CORS_ORIGINS = ['*']


class ProductionConfig(Config):
    """Production-specific configuration"""
    DEBUG = False
    TESTING = False
    # Strict CORS in production
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'https://lockzone-ai-floorplan.onrender.com').split(',')
    # Force HTTPS
    PREFERRED_URL_SCHEME = 'https'
    # Enable all security features
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class TestingConfig(Config):
    """Testing-specific configuration"""
    DEBUG = True
    TESTING = True
    USE_DATABASE = False  # Use JSON files for tests
    # Disable rate limiting in tests
    RATELIMIT_ENABLED = False


# Configuration selector
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}


def get_config():
    """Get configuration based on FLASK_ENV environment variable"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config_by_name.get(env, DevelopmentConfig)
