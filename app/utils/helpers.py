"""
Helper utility functions for file operations and common tasks.
"""

import os
import json


def load_json_file(filepath, default=None):
    """
    Load JSON data from a file.
    
    Args:
        filepath: Path to the JSON file
        default: Default value if file doesn't exist (defaults to empty list)
    
    Returns:
        Parsed JSON data or default value
    """
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return default if default is not None else []


def save_json_file(filepath, data):
    """
    Save data to a JSON file.
    
    Args:
        filepath: Path to the JSON file
        data: Data to save (must be JSON serializable)
    """
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

