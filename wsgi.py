"""
WSGI Entry Point for Gunicorn

This module provides the WSGI application entry point for production deployment.
Gunicorn can be configured to use either:
  - wsgi:app
  - app:app (via app/__init__.py which imports from application.py)
  - application:app

The Flask application is created in application.py.
"""

# Import the Flask app from application.py
from application import app

