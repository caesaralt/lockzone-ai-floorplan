"""
Tests for input validation utilities
"""
import pytest
from io import BytesIO
from werkzeug.datastructures import FileStorage
from validators import (
    validate_required_fields,
    validate_email,
    validate_phone,
    validate_url,
    validate_string_length,
    validate_number_range,
    sanitize_string,
    sanitize_filename,
    validate_file_extension,
    validate_quote_request,
    validate_ai_chat_request,
    validate_mapping_request,
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_DOCUMENT_EXTENSIONS
)


@pytest.mark.unit
class TestRequiredFields:
    """Tests for required fields validation"""

    def test_validate_all_fields_present(self):
        """Test validation passes when all fields present"""
        data = {'name': 'John', 'email': 'john@example.com'}
        is_valid, error = validate_required_fields(data, ['name', 'email'])
        assert is_valid is True
        assert error is None

    def test_validate_missing_field(self):
        """Test validation fails when field missing"""
        data = {'name': 'John'}
        is_valid, error = validate_required_fields(data, ['name', 'email'])
        assert is_valid is False
        assert 'email' in error

    def test_validate_empty_field(self):
        """Test validation fails when field is empty string"""
        data = {'name': 'John', 'email': ''}
        is_valid, error = validate_required_fields(data, ['name', 'email'])
        assert is_valid is False

    def test_validate_none_field(self):
        """Test validation fails when field is None"""
        data = {'name': 'John', 'email': None}
        is_valid, error = validate_required_fields(data, ['name', 'email'])
        assert is_valid is False


@pytest.mark.unit
class TestEmailValidation:
    """Tests for email validation"""

    def test_valid_email(self):
        """Test valid email passes"""
        is_valid, error = validate_email('test@example.com')
        assert is_valid is True
        assert error is None

    def test_valid_email_with_subdomain(self):
        """Test valid email with subdomain passes"""
        is_valid, error = validate_email('user@mail.example.com')
        assert is_valid is True

    def test_invalid_email_no_at(self):
        """Test invalid email without @ fails"""
        is_valid, error = validate_email('invalidemail.com')
        assert is_valid is False

    def test_invalid_email_no_domain(self):
        """Test invalid email without domain fails"""
        is_valid, error = validate_email('test@')
        assert is_valid is False

    def test_invalid_email_too_long(self):
        """Test email that's too long fails"""
        long_email = 'a' * 250 + '@example.com'
        is_valid, error = validate_email(long_email)
        assert is_valid is False

    def test_empty_email(self):
        """Test empty email fails"""
        is_valid, error = validate_email('')
        assert is_valid is False


@pytest.mark.unit
class TestPhoneValidation:
    """Tests for phone number validation"""

    def test_valid_phone_with_country_code(self):
        """Test valid phone with country code passes"""
        is_valid, error = validate_phone('+1234567890')
        assert is_valid is True

    def test_valid_phone_without_country_code(self):
        """Test valid phone without country code passes"""
        is_valid, error = validate_phone('1234567890')
        assert is_valid is True

    def test_valid_phone_with_formatting(self):
        """Test valid phone with formatting passes"""
        is_valid, error = validate_phone('(123) 456-7890')
        assert is_valid is True

    def test_invalid_phone_too_short(self):
        """Test phone that's too short fails"""
        is_valid, error = validate_phone('12345')
        assert is_valid is False

    def test_invalid_phone_letters(self):
        """Test phone with letters fails"""
        is_valid, error = validate_phone('123-ABC-7890')
        assert is_valid is False


@pytest.mark.unit
class TestURLValidation:
    """Tests for URL validation"""

    def test_valid_http_url(self):
        """Test valid HTTP URL passes"""
        is_valid, error = validate_url('http://example.com')
        assert is_valid is True

    def test_valid_https_url(self):
        """Test valid HTTPS URL passes"""
        is_valid, error = validate_url('https://example.com')
        assert is_valid is True

    def test_valid_url_with_path(self):
        """Test valid URL with path passes"""
        is_valid, error = validate_url('https://example.com/path/to/page')
        assert is_valid is True

    def test_invalid_url_no_protocol(self):
        """Test URL without protocol fails"""
        is_valid, error = validate_url('example.com')
        assert is_valid is False

    def test_invalid_url_too_long(self):
        """Test URL that's too long fails"""
        long_url = 'https://example.com/' + 'a' * 2100
        is_valid, error = validate_url(long_url)
        assert is_valid is False


@pytest.mark.unit
class TestStringValidation:
    """Tests for string length validation"""

    def test_valid_string_length(self):
        """Test string within length limits passes"""
        is_valid, error = validate_string_length('test', min_length=1, max_length=10)
        assert is_valid is True

    def test_string_too_short(self):
        """Test string below minimum fails"""
        is_valid, error = validate_string_length('a', min_length=5)
        assert is_valid is False

    def test_string_too_long(self):
        """Test string above maximum fails"""
        is_valid, error = validate_string_length('a' * 100, max_length=50)
        assert is_valid is False

    def test_non_string_value(self):
        """Test non-string value fails"""
        is_valid, error = validate_string_length(123)
        assert is_valid is False


@pytest.mark.unit
class TestNumberValidation:
    """Tests for number range validation"""

    def test_valid_number_in_range(self):
        """Test number within range passes"""
        is_valid, error = validate_number_range(5, min_value=0, max_value=10)
        assert is_valid is True

    def test_number_below_minimum(self):
        """Test number below minimum fails"""
        is_valid, error = validate_number_range(-5, min_value=0)
        assert is_valid is False

    def test_number_above_maximum(self):
        """Test number above maximum fails"""
        is_valid, error = validate_number_range(15, max_value=10)
        assert is_valid is False

    def test_non_number_value(self):
        """Test non-number value fails"""
        is_valid, error = validate_number_range('not a number')
        assert is_valid is False


@pytest.mark.unit
class TestStringsanitization:
    """Tests for string sanitization"""

    def test_sanitize_removes_null_bytes(self):
        """Test sanitization removes null bytes"""
        result = sanitize_string('test\x00string')
        assert '\x00' not in result

    def test_sanitize_trims_whitespace(self):
        """Test sanitization trims whitespace"""
        result = sanitize_string('  test  ')
        assert result == 'test'

    def test_sanitize_limits_length(self):
        """Test sanitization limits length"""
        result = sanitize_string('a' * 2000, max_length=100)
        assert len(result) == 100

    def test_sanitize_handles_non_string(self):
        """Test sanitization handles non-string input"""
        result = sanitize_string(123)
        assert result == '123'


@pytest.mark.unit
class TestFilenameSanitization:
    """Tests for filename sanitization"""

    def test_sanitize_normal_filename(self):
        """Test normal filename is preserved"""
        result = sanitize_filename('document.pdf')
        assert result == 'document.pdf'

    def test_sanitize_removes_path_traversal(self):
        """Test path traversal is removed"""
        result = sanitize_filename('../../../etc/passwd')
        assert '..' not in result
        assert '/' not in result

    def test_sanitize_removes_special_chars(self):
        """Test special characters are removed"""
        result = sanitize_filename('file<>:"|?*.txt')
        assert '<' not in result
        assert '>' not in result

    def test_sanitize_empty_filename(self):
        """Test empty filename gets default name"""
        result = sanitize_filename('')
        assert result == 'file'


@pytest.mark.unit
class TestFileExtensionValidation:
    """Tests for file extension validation"""

    def test_valid_image_extension(self):
        """Test valid image extension passes"""
        is_valid, error = validate_file_extension('photo.jpg', ALLOWED_IMAGE_EXTENSIONS)
        assert is_valid is True

    def test_valid_document_extension(self):
        """Test valid document extension passes"""
        is_valid, error = validate_file_extension('doc.pdf', ALLOWED_DOCUMENT_EXTENSIONS)
        assert is_valid is True

    def test_invalid_extension(self):
        """Test invalid extension fails"""
        is_valid, error = validate_file_extension('malware.exe', ALLOWED_IMAGE_EXTENSIONS)
        assert is_valid is False

    def test_no_extension(self):
        """Test file without extension fails"""
        is_valid, error = validate_file_extension('noextension', ALLOWED_IMAGE_EXTENSIONS)
        assert is_valid is False

    def test_case_insensitive(self):
        """Test extension check is case-insensitive"""
        is_valid, error = validate_file_extension('PHOTO.JPG', ALLOWED_IMAGE_EXTENSIONS)
        assert is_valid is True


@pytest.mark.unit
class TestQuoteRequestValidation:
    """Tests for quote request validation"""

    def test_valid_quote_request(self, sample_project_data):
        """Test valid quote request passes"""
        is_valid, error = validate_quote_request(sample_project_data)
        assert is_valid is True

    def test_quote_request_missing_project_name(self):
        """Test quote request without project_name fails"""
        data = {'client_name': 'Test Client'}
        is_valid, error = validate_quote_request(data)
        assert is_valid is False
        assert 'project_name' in error

    def test_quote_request_with_invalid_email(self):
        """Test quote request with invalid email fails"""
        data = {'project_name': 'Test', 'client_email': 'invalid-email'}
        is_valid, error = validate_quote_request(data)
        assert is_valid is False


@pytest.mark.unit
class TestChatRequestValidation:
    """Tests for AI chat request validation"""

    def test_valid_chat_request(self, sample_chat_request):
        """Test valid chat request passes"""
        is_valid, error = validate_ai_chat_request(sample_chat_request)
        assert is_valid is True

    def test_chat_request_missing_message(self):
        """Test chat request without message fails"""
        data = {'enable_vision': True}
        is_valid, error = validate_ai_chat_request(data)
        assert is_valid is False
        assert 'message' in error

    def test_chat_request_empty_message(self):
        """Test chat request with empty message fails"""
        data = {'message': ''}
        is_valid, error = validate_ai_chat_request(data)
        assert is_valid is False

    def test_chat_request_with_image(self):
        """Test chat request with valid image data passes"""
        data = {
            'message': 'What is in this image?',
            'image_data': 'data:image/png;base64,iVBORw0KGg...'
        }
        is_valid, error = validate_ai_chat_request(data)
        assert is_valid is True


@pytest.mark.unit
class TestMappingRequestValidation:
    """Tests for electrical mapping request validation"""

    def test_valid_mapping_request(self):
        """Test valid mapping request passes"""
        data = {
            'project_name': 'Office Building',
            'components': [
                {'type': 'light', 'quantity': 10}
            ]
        }
        is_valid, error = validate_mapping_request(data)
        assert is_valid is True

    def test_mapping_request_empty_data(self):
        """Test mapping request with empty data passes"""
        is_valid, error = validate_mapping_request({})
        assert is_valid is True

    def test_mapping_request_invalid_components(self):
        """Test mapping request with invalid components fails"""
        data = {'components': 'not an array'}
        is_valid, error = validate_mapping_request(data)
        assert is_valid is False
