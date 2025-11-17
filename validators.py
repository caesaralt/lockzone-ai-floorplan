"""
Input Validation & Sanitization Utilities
Provides secure validation for API requests, file uploads, and user input
"""
import re
import os
from typing import Dict, Any, List, Optional, Tuple
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
import logging

logger = logging.getLogger(__name__)

# Allowed file extensions by category
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
ALLOWED_CAD_EXTENSIONS = {'dxf', 'dwg', 'svg'}
ALLOWED_DATA_EXTENSIONS = {'json', 'csv', 'xlsx'}

# Maximum file sizes (in bytes)
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_DOCUMENT_SIZE = 20 * 1024 * 1024  # 20MB
MAX_CAD_SIZE = 50 * 1024 * 1024  # 50MB

# Regex patterns
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
PHONE_PATTERN = re.compile(r'^\+?1?\d{9,15}$')
URL_PATTERN = re.compile(r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}.*$')


class ValidationError(Exception):
    """Custom exception for validation errors"""
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate that all required fields are present in the data

    Args:
        data: Dictionary of input data
        required_fields: List of required field names

    Returns:
        Tuple of (is_valid, error_message)
    """
    missing_fields = [field for field in required_fields if field not in data or data[field] is None or data[field] == '']

    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"

    return True, None


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email format

    Args:
        email: Email address to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email or not isinstance(email, str):
        return False, "Email must be a non-empty string"

    if not EMAIL_PATTERN.match(email):
        return False, "Invalid email format"

    if len(email) > 254:  # RFC 5321
        return False, "Email address too long"

    return True, None


def validate_phone(phone: str) -> Tuple[bool, Optional[str]]:
    """
    Validate phone number format

    Args:
        phone: Phone number to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not phone or not isinstance(phone, str):
        return False, "Phone must be a non-empty string"

    # Remove common separators
    cleaned_phone = re.sub(r'[\s\-\(\)]', '', phone)

    if not PHONE_PATTERN.match(cleaned_phone):
        return False, "Invalid phone number format"

    return True, None


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate URL format

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string"

    if not URL_PATTERN.match(url):
        return False, "Invalid URL format"

    if len(url) > 2048:
        return False, "URL too long"

    return True, None


def validate_string_length(value: str, min_length: int = 0, max_length: int = 1000) -> Tuple[bool, Optional[str]]:
    """
    Validate string length is within acceptable range

    Args:
        value: String to validate
        min_length: Minimum allowed length
        max_length: Maximum allowed length

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(value, str):
        return False, "Value must be a string"

    if len(value) < min_length:
        return False, f"Value too short (minimum {min_length} characters)"

    if len(value) > max_length:
        return False, f"Value too long (maximum {max_length} characters)"

    return True, None


def validate_number_range(value: float, min_value: Optional[float] = None, max_value: Optional[float] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate number is within acceptable range

    Args:
        value: Number to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(value, (int, float)):
        return False, "Value must be a number"

    if min_value is not None and value < min_value:
        return False, f"Value too small (minimum {min_value})"

    if max_value is not None and value > max_value:
        return False, f"Value too large (maximum {max_value})"

    return True, None


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Sanitize string input by removing potentially dangerous characters

    Args:
        value: String to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return str(value)

    # Remove null bytes
    sanitized = value.replace('\x00', '')

    # Trim whitespace
    sanitized = sanitized.strip()

    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal attacks

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Use werkzeug's secure_filename
    safe_name = secure_filename(filename)

    # If secure_filename removes everything, generate a default name
    if not safe_name:
        safe_name = 'file'

    return safe_name


def validate_file_extension(filename: str, allowed_extensions: set) -> Tuple[bool, Optional[str]]:
    """
    Validate file has an allowed extension

    Args:
        filename: Filename to check
        allowed_extensions: Set of allowed extensions (without dots)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not filename or '.' not in filename:
        return False, "File must have an extension"

    extension = filename.rsplit('.', 1)[1].lower()

    if extension not in allowed_extensions:
        return False, f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"

    return True, None


def validate_file_upload(
    file: FileStorage,
    allowed_extensions: set,
    max_size: int,
    file_type: str = "file"
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Comprehensive file upload validation

    Args:
        file: FileStorage object from request.files
        allowed_extensions: Set of allowed extensions
        max_size: Maximum file size in bytes
        file_type: Type of file for error messages

    Returns:
        Tuple of (is_valid, error_message, sanitized_filename)
    """
    # Check if file exists
    if not file or not file.filename:
        return False, f"No {file_type} provided", None

    # Sanitize filename
    safe_filename = sanitize_filename(file.filename)

    # Validate extension
    is_valid, error = validate_file_extension(safe_filename, allowed_extensions)
    if not is_valid:
        return False, error, None

    # Check file size (read file to check actual size)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset to beginning

    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        return False, f"{file_type.capitalize()} too large (maximum {max_mb:.1f}MB)", None

    if file_size == 0:
        return False, f"{file_type.capitalize()} is empty", None

    logger.info(f"File validation successful: {safe_filename} ({file_size} bytes)")
    return True, None, safe_filename


def validate_image_upload(file: FileStorage) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate image file upload"""
    return validate_file_upload(file, ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_SIZE, "image")


def validate_document_upload(file: FileStorage) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate document file upload"""
    return validate_file_upload(file, ALLOWED_DOCUMENT_EXTENSIONS, MAX_DOCUMENT_SIZE, "document")


def validate_cad_upload(file: FileStorage) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate CAD file upload"""
    return validate_file_upload(file, ALLOWED_CAD_EXTENSIONS, MAX_CAD_SIZE, "CAD file")


def validate_quote_request(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate quote automation request data

    Args:
        data: Request data dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ['project_name']

    # Check required fields
    is_valid, error = validate_required_fields(data, required_fields)
    if not is_valid:
        return False, error

    # Validate project name
    project_name = data.get('project_name', '')
    is_valid, error = validate_string_length(project_name, min_length=1, max_length=200)
    if not is_valid:
        return False, f"Invalid project_name: {error}"

    # Validate optional fields if present
    if 'client_name' in data:
        is_valid, error = validate_string_length(data['client_name'], max_length=200)
        if not is_valid:
            return False, f"Invalid client_name: {error}"

    if 'client_email' in data and data['client_email']:
        is_valid, error = validate_email(data['client_email'])
        if not is_valid:
            return False, f"Invalid client_email: {error}"

    if 'client_phone' in data and data['client_phone']:
        is_valid, error = validate_phone(data['client_phone'])
        if not is_valid:
            return False, f"Invalid client_phone: {error}"

    return True, None


def validate_ai_chat_request(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate AI chatbot request data

    Args:
        data: Request data dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ['message']

    # Check required fields
    is_valid, error = validate_required_fields(data, required_fields)
    if not is_valid:
        return False, error

    # Validate message
    message = data.get('message', '')
    is_valid, error = validate_string_length(message, min_length=1, max_length=10000)
    if not is_valid:
        return False, f"Invalid message: {error}"

    # Validate optional parameters
    if 'enable_vision' in data and not isinstance(data['enable_vision'], bool):
        return False, "enable_vision must be a boolean"

    if 'agentic_mode' in data and not isinstance(data['agentic_mode'], bool):
        return False, "agentic_mode must be a boolean"

    if 'image_data' in data:
        image_data = data['image_data']
        if not isinstance(image_data, str):
            return False, "image_data must be a base64 string"

        # Check if it's a valid data URL
        if not image_data.startswith('data:image/'):
            return False, "image_data must be a valid image data URL"

    return True, None


def validate_mapping_request(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate electrical mapping request data

    Args:
        data: Request data dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Project name is optional but if present must be valid
    if 'project_name' in data:
        is_valid, error = validate_string_length(data['project_name'], max_length=200)
        if not is_valid:
            return False, f"Invalid project_name: {error}"

    # Validate components if present
    if 'components' in data:
        if not isinstance(data['components'], list):
            return False, "components must be an array"

        for idx, component in enumerate(data['components']):
            if not isinstance(component, dict):
                return False, f"Component {idx} must be an object"

            # Validate component fields
            if 'type' in component:
                is_valid, error = validate_string_length(component['type'], max_length=100)
                if not is_valid:
                    return False, f"Component {idx} invalid type: {error}"

    return True, None


def format_validation_error(field: str, message: str) -> Dict[str, Any]:
    """
    Format validation error for consistent API responses

    Args:
        field: Field name that failed validation
        message: Error message

    Returns:
        Error response dictionary
    """
    return {
        'error': 'Validation Error',
        'field': field,
        'message': message
    }


def format_success_response(data: Any, message: str = "Success") -> Dict[str, Any]:
    """
    Format success response for consistent API responses

    Args:
        data: Response data
        message: Success message

    Returns:
        Success response dictionary
    """
    return {
        'success': True,
        'message': message,
        'data': data
    }
