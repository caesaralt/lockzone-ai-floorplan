"""
Admin Routes Blueprint

Handles admin panel, page editor, customizations, branding, and app settings.
"""

import os
from flask import Blueprint, render_template, request, jsonify, current_app
from functools import wraps
import logging

from app.utils import load_json_file, save_json_file

logger = logging.getLogger(__name__)

# Create blueprint
admin_bp = Blueprint('admin_bp', __name__)


def get_auth():
    """Get auth module - imported lazily to avoid circular imports"""
    import auth
    return auth


def admin_required_wrapper(f):
    """Wrapper for admin_required that works with blueprint"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = get_auth()
        if not auth.is_authenticated():
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        if not auth.has_permission('admin'):
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


def get_customizations_file():
    """Get the path to the customizations file"""
    return os.path.join(current_app.config['CRM_DATA_FOLDER'], 'customizations.json')


def get_branding_dir():
    """Get the branding directory path"""
    branding_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'branding')
    os.makedirs(branding_dir, exist_ok=True)
    return branding_dir


def get_app_functions():
    """Get functions from main app"""
    return current_app.config.get('APP_FUNCTIONS', {})


# ============================================================================
# ADMIN PAGE ROUTES
# ============================================================================

@admin_bp.route('/admin')
@admin_required_wrapper
def admin_page():
    """Admin panel for user management"""
    return render_template('admin.html')


@admin_bp.route('/admin/page-editor')
def admin_page_editor():
    """Admin page editor for the landing page"""
    funcs = get_app_functions()
    load_page_config = funcs.get('load_page_config')
    config = load_page_config() if load_page_config else {}
    return render_template('admin_page_editor.html', config=config)


# ============================================================================
# PAGE CONFIG API
# ============================================================================

@admin_bp.route('/api/admin/page-config', methods=['GET'])
def get_page_config():
    """Get the current page configuration"""
    funcs = get_app_functions()
    load_page_config = funcs.get('load_page_config')
    config = load_page_config() if load_page_config else {}
    return jsonify(config)


@admin_bp.route('/api/admin/page-config', methods=['POST'])
def update_page_config():
    """Update the page configuration"""
    try:
        funcs = get_app_functions()
        save_page_config = funcs.get('save_page_config')
        if save_page_config:
            config = request.json
            save_page_config(config)
            return jsonify({'success': True, 'message': 'Page configuration saved successfully'})
        return jsonify({'success': False, 'error': 'Save function not available'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# CUSTOMIZATION API
# ============================================================================

@admin_bp.route('/api/admin/customizations', methods=['GET'])
def get_customizations():
    """Get app customizations"""
    try:
        customizations = load_json_file(get_customizations_file(), {})
        return jsonify({'success': True, 'customizations': customizations})
    except Exception as e:
        logger.error(f"Error getting customizations: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/customizations', methods=['POST'])
def save_customizations():
    """Save app customizations"""
    try:
        data = request.json
        existing = load_json_file(get_customizations_file(), {})
        
        # Merge with existing customizations
        if 'modules' in data:
            existing['modules'] = data['modules']
        
        save_json_file(get_customizations_file(), existing)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error saving customizations: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# BRANDING API
# ============================================================================

@admin_bp.route('/api/admin/branding', methods=['POST'])
def save_branding():
    """Save branding images"""
    try:
        saved_files = {}
        branding_dir = get_branding_dir()
        
        for key in ['app_logo', 'login_logo', 'favicon']:
            if key in request.files:
                file = request.files[key]
                if file.filename:
                    # Save file
                    ext = file.filename.rsplit('.', 1)[-1].lower()
                    filename = f"{key}.{ext}"
                    filepath = os.path.join(branding_dir, filename)
                    file.save(filepath)
                    saved_files[key] = f"/static/branding/{filename}"
        
        # Update customizations with branding paths
        if saved_files:
            customizations = load_json_file(get_customizations_file(), {})
            if 'branding' not in customizations:
                customizations['branding'] = {}
            customizations['branding'].update(saved_files)
            save_json_file(get_customizations_file(), customizations)
        
        return jsonify({'success': True, 'files': saved_files})
    except Exception as e:
        logger.error(f"Error saving branding: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# APP SETTINGS API
# ============================================================================

@admin_bp.route('/api/admin/settings', methods=['GET'])
def get_app_settings():
    """Get app settings"""
    try:
        customizations = load_json_file(get_customizations_file(), {})
        settings = customizations.get('settings', {
            'app_name': 'Integratd Living',
            'tagline': 'Your complete business automation platform',
            'primary_color': '#6AB64B'
        })
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/admin/settings', methods=['POST'])
def save_app_settings():
    """Save app settings"""
    try:
        data = request.json
        customizations = load_json_file(get_customizations_file(), {})
        customizations['settings'] = {
            'app_name': data.get('app_name', 'Integratd Living'),
            'tagline': data.get('tagline', 'Your complete business automation platform'),
            'primary_color': data.get('primary_color', '#6AB64B')
        }
        save_json_file(get_customizations_file(), customizations)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

