"""
Authentication Routes Blueprint

Handles user authentication, login/logout, and user management API endpoints.
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth_bp', __name__)


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
        if not auth.is_admin():
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


def login_required_wrapper(f):
    """Wrapper for login_required that works with blueprint"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = get_auth()
        if not auth.is_authenticated():
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated


# ============================================================================
# LOGIN/LOGOUT ROUTES
# ============================================================================

@auth_bp.route('/login')
def login_page():
    """Login page"""
    auth = get_auth()
    # If already logged in, redirect to main menu
    if auth.is_authenticated():
        return redirect(url_for('pages.index'))
    return render_template('login.html')


@auth_bp.route('/api/auth/login', methods=['POST'])
def api_login():
    """API endpoint for user login"""
    auth = get_auth()
    try:
        data = request.json
        name = data.get('name')
        code = data.get('code')

        if not name or not code:
            return jsonify({'success': False, 'error': 'Name and code required'}), 400

        # Authenticate user
        user, error = auth.authenticate_user(name, code)

        if error:
            return jsonify({'success': False, 'error': error}), 401

        # Set session
        auth.login_user(user)

        return jsonify({
            'success': True,
            'user': {
                'name': user['name'],
                'display_name': user['display_name'],
                'role': user['role'],
                'permissions': user['permissions']
            },
            'redirect': '/'
        })

    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'success': False, 'error': 'Login failed'}), 500


@auth_bp.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """API endpoint for user logout"""
    auth = get_auth()
    auth.logout_user()
    return jsonify({'success': True})


# ============================================================================
# USER MANAGEMENT API (Admin only)
# ============================================================================

@auth_bp.route('/api/auth/users', methods=['GET'])
@admin_required_wrapper
def get_users():
    """Get all users (admin only)"""
    auth = get_auth()
    try:
        users = auth.load_users()
        # Remove password hashes from response
        safe_users = [{k: v for k, v in user.items() if k != 'code'} for user in users]
        return jsonify({'success': True, 'users': safe_users})
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@auth_bp.route('/api/auth/users/<user_id>', methods=['GET'])
@admin_required_wrapper
def get_user(user_id):
    """Get specific user (admin only)"""
    auth = get_auth()
    try:
        user = auth.get_user_by_id(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        # Remove password hash
        safe_user = {k: v for k, v in user.items() if k != 'code'}
        return jsonify({'success': True, 'user': safe_user})
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@auth_bp.route('/api/auth/users', methods=['POST'])
@admin_required_wrapper
def create_user_api():
    """Create new user (admin only)"""
    auth = get_auth()
    try:
        data = request.json
        name = data.get('name')
        code = data.get('code')
        display_name = data.get('display_name')
        role = data.get('role', 'viewer')
        custom_permissions = data.get('permissions')

        if not name or not code or not display_name:
            return jsonify({'success': False, 'error': 'Name, code, and display name required'}), 400

        user, error = auth.create_user(name, code, display_name, role, custom_permissions)

        if error:
            return jsonify({'success': False, 'error': error}), 400

        # Remove password hash
        safe_user = {k: v for k, v in user.items() if k != 'code'}
        return jsonify({'success': True, 'user': safe_user})

    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@auth_bp.route('/api/auth/users/<user_id>', methods=['PUT'])
@admin_required_wrapper
def update_user_api(user_id):
    """Update user (admin only)"""
    auth = get_auth()
    try:
        data = request.json

        # Build update kwargs
        update_data = {}
        if 'name' in data:
            update_data['name'] = data['name']
        if 'display_name' in data:
            update_data['display_name'] = data['display_name']
        if 'code' in data and data['code']:  # Only update if provided
            update_data['code'] = data['code']
        if 'role' in data:
            update_data['role'] = data['role']
        if 'permissions' in data:
            update_data['permissions'] = data['permissions']
        if 'active' in data:
            update_data['active'] = data['active']

        user, error = auth.update_user(user_id, **update_data)

        if error:
            return jsonify({'success': False, 'error': error}), 400

        # Remove password hash
        safe_user = {k: v for k, v in user.items() if k != 'code'}
        return jsonify({'success': True, 'user': safe_user})

    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@auth_bp.route('/api/auth/users/<user_id>', methods=['DELETE'])
@admin_required_wrapper
def delete_user_api(user_id):
    """Delete user (admin only)"""
    auth = get_auth()
    try:
        success, error = auth.delete_user(user_id)

        if error:
            return jsonify({'success': False, 'error': error}), 400

        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@auth_bp.route('/api/auth/permissions', methods=['GET'])
@admin_required_wrapper
def get_permissions():
    """Get available permissions and roles (admin only)"""
    auth = get_auth()
    return jsonify({
        'success': True,
        'permissions': auth.PERMISSIONS,
        'crm_permissions': auth.CRM_PERMISSIONS,
        'roles': auth.ROLES
    })


@auth_bp.route('/api/auth/current-user', methods=['GET'])
@login_required_wrapper
def get_current_user_api():
    """Get current logged-in user info"""
    auth = get_auth()
    user = auth.get_current_user()
    if user:
        safe_user = {k: v for k, v in user.items() if k != 'code'}
        return jsonify({'success': True, 'user': safe_user})
    return jsonify({'success': False, 'error': 'Not authenticated'}), 401


@auth_bp.route('/api/auth/usernames', methods=['GET'])
def get_usernames():
    """Get list of active usernames for autocomplete"""
    auth = get_auth()
    try:
        users = auth.load_users()
        # Return only active user names for autocomplete
        usernames = [user['name'] for user in users if user.get('active', True)]
        return jsonify({'success': True, 'usernames': usernames})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
