"""
Tests for configuration system
"""
import os
import pytest
from config import (
    Config,
    DevelopmentConfig,
    ProductionConfig,
    TestingConfig,
    get_config
)


@pytest.mark.unit
class TestBaseConfig:
    """Tests for base configuration"""

    def test_base_config_has_secret_key(self):
        """Test that base config has a secret key"""
        config = Config()
        assert hasattr(config, 'SECRET_KEY')
        assert config.SECRET_KEY is not None

    def test_base_config_has_max_content_length(self):
        """Test that base config has max content length"""
        config = Config()
        assert config.MAX_CONTENT_LENGTH == 50 * 1024 * 1024

    def test_base_config_has_cors_settings(self):
        """Test that base config has CORS settings"""
        config = Config()
        assert hasattr(config, 'CORS_ORIGINS')
        assert hasattr(config, 'CORS_METHODS')
        assert 'GET' in config.CORS_METHODS
        assert 'POST' in config.CORS_METHODS

    def test_base_config_has_ai_models(self):
        """Test that base config has AI model configuration"""
        config = Config()
        assert 'claude' in config.AI_MODELS
        assert 'gpt4' in config.AI_MODELS
        assert config.AI_MODELS['claude']['model'] == 'claude-sonnet-4-20250514'

    def test_base_config_has_retry_settings(self):
        """Test that base config has retry settings"""
        config = Config()
        assert config.AI_RETRY_ATTEMPTS == 3
        assert config.AI_RETRY_DELAY == 2
        assert config.AI_TIMEOUT == 120

    def test_base_config_has_logging_settings(self):
        """Test that base config has logging settings"""
        config = Config()
        assert config.LOG_LEVEL == 'INFO'
        assert config.LOG_FILE == 'app.log'


@pytest.mark.unit
class TestDevelopmentConfig:
    """Tests for development configuration"""

    def test_development_config_has_debug(self):
        """Test that development config has debug enabled"""
        config = DevelopmentConfig()
        assert config.DEBUG is True

    def test_development_config_has_testing_disabled(self):
        """Test that development config has testing disabled"""
        config = DevelopmentConfig()
        assert config.TESTING is False

    def test_development_config_has_debug_log_level(self):
        """Test that development config has DEBUG log level"""
        config = DevelopmentConfig()
        assert config.LOG_LEVEL == 'DEBUG'

    def test_development_config_allows_all_cors(self):
        """Test that development config allows all CORS origins"""
        config = DevelopmentConfig()
        assert '*' in config.CORS_ORIGINS


@pytest.mark.unit
class TestProductionConfig:
    """Tests for production configuration"""

    def test_production_config_has_debug_disabled(self):
        """Test that production config has debug disabled"""
        config = ProductionConfig()
        assert config.DEBUG is False

    def test_production_config_has_testing_disabled(self):
        """Test that production config has testing disabled"""
        config = ProductionConfig()
        assert config.TESTING is False

    def test_production_config_has_secure_cookies(self):
        """Test that production config has secure cookies"""
        config = ProductionConfig()
        assert config.SESSION_COOKIE_SECURE is True
        assert config.SESSION_COOKIE_HTTPONLY is True
        assert config.SESSION_COOKIE_SAMESITE == 'Lax'

    def test_production_config_has_https_scheme(self):
        """Test that production config prefers HTTPS"""
        config = ProductionConfig()
        assert config.PREFERRED_URL_SCHEME == 'https'


@pytest.mark.unit
class TestTestingConfig:
    """Tests for testing configuration"""

    def test_testing_config_has_debug(self):
        """Test that testing config has debug enabled"""
        config = TestingConfig()
        assert config.DEBUG is True

    def test_testing_config_has_testing_enabled(self):
        """Test that testing config has testing enabled"""
        config = TestingConfig()
        assert config.TESTING is True

    def test_testing_config_disables_database(self):
        """Test that testing config disables database"""
        config = TestingConfig()
        assert config.USE_DATABASE is False

    def test_testing_config_disables_rate_limiting(self):
        """Test that testing config disables rate limiting"""
        config = TestingConfig()
        assert config.RATELIMIT_ENABLED is False


@pytest.mark.unit
class TestGetConfig:
    """Tests for configuration selector"""

    def test_get_config_returns_development_by_default(self):
        """Test that get_config returns development config by default"""
        # Clear environment
        old_env = os.environ.get('FLASK_ENV')
        if 'FLASK_ENV' in os.environ:
            del os.environ['FLASK_ENV']

        config_class = get_config()
        assert config_class == DevelopmentConfig

        # Restore environment
        if old_env:
            os.environ['FLASK_ENV'] = old_env

    def test_get_config_returns_production_when_set(self):
        """Test that get_config returns production config when env is production"""
        old_env = os.environ.get('FLASK_ENV')
        os.environ['FLASK_ENV'] = 'production'

        config_class = get_config()
        assert config_class == ProductionConfig

        # Restore environment
        if old_env:
            os.environ['FLASK_ENV'] = old_env
        else:
            del os.environ['FLASK_ENV']

    def test_get_config_returns_testing_when_set(self):
        """Test that get_config returns testing config when env is testing"""
        old_env = os.environ.get('FLASK_ENV')
        os.environ['FLASK_ENV'] = 'testing'

        config_class = get_config()
        assert config_class == TestingConfig

        # Restore environment
        if old_env:
            os.environ['FLASK_ENV'] = old_env
        else:
            del os.environ['FLASK_ENV']
