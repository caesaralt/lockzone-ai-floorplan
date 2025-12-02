"""
WSGI Entry Point for Gunicorn

This module provides the WSGI application entry point for production deployment.
Gunicorn should be configured to use: wsgi:app

The actual Flask application is created in app.py, which is imported here.
This separation avoids conflicts with the app/ package directory.
"""

# Import the Flask application from app.py
# Note: We import 'app' from the app.py FILE, not the app/ PACKAGE
import sys
import os

# Ensure the app.py file is imported, not the app/ package
# by importing from the module directly
from importlib import import_module

# Get the directory containing this file
_dir = os.path.dirname(os.path.abspath(__file__))

# Import app.py as a module (avoiding the app/ package)
import importlib.util
spec = importlib.util.spec_from_file_location("app_module", os.path.join(_dir, "app.py"))
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)

# Export the Flask app for gunicorn
app = app_module.app

