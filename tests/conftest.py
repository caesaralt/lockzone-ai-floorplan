"""
Pytest configuration and shared fixtures
"""
import os
import sys
import pytest
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def app_config():
    """Fixture providing test configuration"""
    from config import TestingConfig
    return TestingConfig


@pytest.fixture
def test_env_vars():
    """Fixture providing test environment variables"""
    original_env = os.environ.copy()

    # Set test environment variables
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['SECRET_KEY'] = 'test-secret-key-minimum-32-chars-long-for-security'
    os.environ['ANTHROPIC_API_KEY'] = 'test-anthropic-key'
    os.environ['OPENAI_API_KEY'] = 'test-openai-key'

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def sample_project_data():
    """Fixture providing sample project data"""
    return {
        'project_name': 'Test Office Building',
        'client_name': 'Test Client LLC',
        'client_email': 'client@example.com',
        'client_phone': '+1234567890',
        'components': [
            {'type': 'light', 'quantity': 10, 'location': 'Office Area'},
            {'type': 'outlet', 'quantity': 15, 'location': 'Work Stations'},
            {'type': 'switch', 'quantity': 5, 'location': 'Entry Points'}
        ]
    }


@pytest.fixture
def sample_chat_request():
    """Fixture providing sample chat request data"""
    return {
        'message': 'What are the electrical requirements for a commercial office?',
        'enable_vision': False,
        'agentic_mode': False
    }


@pytest.fixture
def sample_file_data():
    """Fixture providing sample file upload data"""
    return {
        'valid_image_name': 'floorplan.png',
        'valid_pdf_name': 'specification.pdf',
        'invalid_name': 'malicious.exe',
        'path_traversal_name': '../../../etc/passwd'
    }


@pytest.fixture
def mock_ai_response():
    """Fixture providing mock AI response"""
    class MockResponse:
        def __init__(self):
            self.stop_reason = 'end_turn'
            self.content = [
                type('Content', (), {
                    'type': 'text',
                    'text': 'This is a test response from the AI'
                })()
            ]

    return MockResponse()


@pytest.fixture
def create_temp_directories(tmp_path):
    """Fixture creating temporary directory structure"""
    directories = [
        'uploads',
        'outputs',
        'data',
        'learning_data',
        'logs'
    ]

    created_dirs = {}
    for dir_name in directories:
        dir_path = tmp_path / dir_name
        dir_path.mkdir()
        created_dirs[dir_name] = dir_path

    return created_dirs
