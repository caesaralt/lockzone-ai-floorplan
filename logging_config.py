"""
Centralized Logging Configuration
Provides structured logging with rotation and different levels
"""
import logging
import logging.handlers
import os
from pathlib import Path


def setup_logging(app):
    """
    Setup application-wide logging with file rotation and console output

    Args:
        app: Flask application instance
    """
    log_level = getattr(logging, app.config['LOG_LEVEL'].upper(), logging.INFO)
    log_format = app.config['LOG_FORMAT']
    log_file = app.config['LOG_FILE']

    # Create logs directory if it doesn't exist
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / log_file

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers = []

    # Console Handler (for development and debugging)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(log_format)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File Handler with rotation (for production)
    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(log_format)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Set specific loggers for third-party libraries
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    app.logger.info(f"Logging initialized at {log_level} level")
    app.logger.info(f"Log file: {log_path}")

    return root_logger


def get_logger(name):
    """
    Get a logger instance for a specific module

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
