"""
Tests for health check endpoints
"""
import pytest
import time
from unittest.mock import Mock, patch
from health_checks import (
    get_system_metrics,
    get_uptime,
    check_ai_services,
    check_filesystem,
    START_TIME
)


@pytest.mark.unit
class TestSystemMetrics:
    """Tests for system metrics collection"""

    def test_get_system_metrics_returns_dict(self):
        """Test that get_system_metrics returns a dictionary"""
        metrics = get_system_metrics()
        assert isinstance(metrics, dict)

    def test_system_metrics_has_cpu_percent(self):
        """Test that system metrics includes CPU percent"""
        metrics = get_system_metrics()
        if metrics:  # Only check if psutil is available
            assert 'cpu_percent' in metrics
            assert isinstance(metrics['cpu_percent'], (int, float))

    def test_system_metrics_has_memory_info(self):
        """Test that system metrics includes memory info"""
        metrics = get_system_metrics()
        if metrics:
            assert 'memory_mb' in metrics
            assert 'memory_percent' in metrics

    @patch('health_checks.psutil.Process')
    def test_system_metrics_handles_errors(self, mock_process):
        """Test that get_system_metrics handles errors gracefully"""
        mock_process.side_effect = Exception("Test error")
        metrics = get_system_metrics()
        assert isinstance(metrics, dict)
        assert len(metrics) == 0  # Should return empty dict on error


@pytest.mark.unit
class TestUptime:
    """Tests for uptime calculation"""

    def test_get_uptime_returns_dict(self):
        """Test that get_uptime returns a dictionary"""
        uptime = get_uptime()
        assert isinstance(uptime, dict)

    def test_uptime_has_required_fields(self):
        """Test that uptime includes all required fields"""
        uptime = get_uptime()
        assert 'uptime_seconds' in uptime
        assert 'uptime_minutes' in uptime
        assert 'uptime_hours' in uptime
        assert 'started_at' in uptime

    def test_uptime_seconds_is_positive(self):
        """Test that uptime seconds is positive"""
        uptime = get_uptime()
        assert uptime['uptime_seconds'] >= 0

    def test_uptime_increases_over_time(self):
        """Test that uptime increases over time"""
        uptime1 = get_uptime()
        time.sleep(0.1)
        uptime2 = get_uptime()
        assert uptime2['uptime_seconds'] > uptime1['uptime_seconds']


@pytest.mark.unit
class TestAIServicesCheck:
    """Tests for AI services availability check"""

    def test_check_ai_services_with_all_keys(self):
        """Test AI services check when all keys are present"""
        mock_app = Mock()
        mock_app.config = {
            'ANTHROPIC_API_KEY': 'test-key',
            'OPENAI_API_KEY': 'test-key',
            'TAVILY_API_KEY': 'test-key'
        }

        services = check_ai_services(mock_app)

        assert services['anthropic_claude'] is True
        assert services['openai_gpt4'] is True
        assert services['tavily_search'] is True

    def test_check_ai_services_with_no_keys(self):
        """Test AI services check when no keys are present"""
        mock_app = Mock()
        mock_app.config = {}

        services = check_ai_services(mock_app)

        assert services['anthropic_claude'] is False
        assert services['openai_gpt4'] is False
        assert services['tavily_search'] is False

    def test_check_ai_services_with_partial_keys(self):
        """Test AI services check when only some keys are present"""
        mock_app = Mock()
        mock_app.config = {
            'ANTHROPIC_API_KEY': 'test-key'
        }

        services = check_ai_services(mock_app)

        assert services['anthropic_claude'] is True
        assert services['openai_gpt4'] is False
        assert services['tavily_search'] is False


@pytest.mark.unit
class TestFilesystemCheck:
    """Tests for filesystem availability check"""

    @patch('os.path.exists')
    @patch('os.access')
    @patch('os.getcwd')
    def test_check_filesystem_all_healthy(self, mock_getcwd, mock_access, mock_exists):
        """Test filesystem check when all directories are healthy"""
        mock_getcwd.return_value = '/test'
        mock_exists.return_value = True
        mock_access.return_value = True

        filesystem = check_filesystem()

        assert 'uploads' in filesystem
        assert filesystem['uploads']['exists'] is True
        assert filesystem['uploads']['writable'] is True
        assert filesystem['uploads']['healthy'] is True

    @patch('os.path.exists')
    @patch('os.access')
    @patch('os.getcwd')
    def test_check_filesystem_directory_missing(self, mock_getcwd, mock_access, mock_exists):
        """Test filesystem check when directory is missing"""
        mock_getcwd.return_value = '/test'
        mock_exists.return_value = False
        mock_access.return_value = False

        filesystem = check_filesystem()

        assert filesystem['uploads']['exists'] is False
        assert filesystem['uploads']['healthy'] is False

    @patch('os.path.exists')
    @patch('os.access')
    @patch('os.getcwd')
    def test_check_filesystem_directory_not_writable(self, mock_getcwd, mock_access, mock_exists):
        """Test filesystem check when directory is not writable"""
        mock_getcwd.return_value = '/test'
        mock_exists.return_value = True
        mock_access.return_value = False

        filesystem = check_filesystem()

        assert filesystem['uploads']['exists'] is True
        assert filesystem['uploads']['writable'] is False
        assert filesystem['uploads']['healthy'] is False


@pytest.mark.integration
class TestHealthCheckEndpoints:
    """Integration tests for health check endpoints (requires Flask app)"""

    @pytest.fixture
    def app(self):
        """Create a test Flask app with health check blueprint"""
        from flask import Flask
        from health_checks import register_health_checks

        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['ANTHROPIC_API_KEY'] = 'test-key'

        register_health_checks(app)

        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client"""
        return app.test_client()

    def test_health_endpoint_returns_200(self, client):
        """Test that /health endpoint returns 200"""
        response = client.get('/api/health')
        assert response.status_code == 200

    def test_health_endpoint_returns_json(self, client):
        """Test that /health endpoint returns JSON"""
        response = client.get('/api/health')
        data = response.get_json()
        assert data is not None
        assert data['status'] == 'healthy'

    def test_health_endpoint_has_timestamp(self, client):
        """Test that /health endpoint includes timestamp"""
        response = client.get('/api/health')
        data = response.get_json()
        assert 'timestamp' in data

    def test_ping_endpoint_returns_pong(self, client):
        """Test that /ping endpoint returns 'pong'"""
        response = client.get('/api/ping')
        assert response.status_code == 200
        assert response.data == b'pong'

    def test_ready_endpoint_returns_json(self, client):
        """Test that /ready endpoint returns JSON"""
        response = client.get('/api/ready')
        data = response.get_json()
        assert data is not None
        assert 'status' in data

    def test_ready_endpoint_checks_ai_services(self, client):
        """Test that /ready endpoint checks AI services"""
        response = client.get('/api/ready')
        data = response.get_json()
        assert 'checks' in data
        assert 'ai_services' in data['checks']

    def test_ready_endpoint_checks_filesystem(self, client):
        """Test that /ready endpoint checks filesystem"""
        response = client.get('/api/ready')
        data = response.get_json()
        assert 'checks' in data
        assert 'filesystem' in data['checks']

    def test_metrics_endpoint_returns_200(self, client):
        """Test that /metrics endpoint returns 200"""
        response = client.get('/api/metrics')
        assert response.status_code == 200

    def test_metrics_endpoint_has_uptime(self, client):
        """Test that /metrics endpoint includes uptime"""
        response = client.get('/api/metrics')
        data = response.get_json()
        assert 'uptime' in data
        assert 'uptime_seconds' in data['uptime']

    def test_metrics_endpoint_has_version(self, client):
        """Test that /metrics endpoint includes version"""
        response = client.get('/api/metrics')
        data = response.get_json()
        assert 'version' in data

    def test_metrics_endpoint_has_services(self, client):
        """Test that /metrics endpoint includes services status"""
        response = client.get('/api/metrics')
        data = response.get_json()
        assert 'services' in data
