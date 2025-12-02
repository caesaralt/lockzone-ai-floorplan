"""
User Authentication and Authorization Module
Handles user login, session management, and role-based permissions
Uses NAME + CODE authentication (admin creates users)

STORAGE POLICY:
- Production: DATABASE_URL is REQUIRED. JSON persistence is disabled.
- Development: Database preferred, JSON fallback allowed if no DATABASE_URL.
"""
import os
import json
import uuid
from datetime import datetime
from functools import wraps
from flask import session, redirect, url_for, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash

# Use pbkdf2 method which is compatible with older Python/OpenSSL versions
def safe_generate_password_hash(password):
    """Generate password hash using pbkdf2 for compatibility"""
    return generate_password_hash(password, method='pbkdf2:sha256')

def safe_check_password_hash(pwhash, password):
    """Check password hash with fallback"""
    return check_password_hash(pwhash, password)
import logging

logger = logging.getLogger(__name__)

# User data file
USERS_FILE = 'crm_data/users.json'


# ============================================================================
# STORAGE POLICY HELPERS
# ============================================================================

def use_database():
    """Check if database should be used for auth data."""
    from config import has_database
    return has_database()


def use_json_fallback():
    """Check if JSON fallback is allowed for auth data."""
    from config import allow_json_persistence
    return allow_json_persistence()


def _check_json_allowed():
    """
    Check if JSON persistence is allowed.
    Raises StoragePolicyError if called in production without database.
    """
    from config import is_production, StoragePolicyError
    
    if is_production() and not use_database():
        raise StoragePolicyError(
            "JSON persistence is disabled in production. DATABASE_URL must be configured."
        )

# Available permissions
PERMISSIONS = {
    'crm': 'CRM Dashboard',
    'quotes': 'Quote Automation',
    'canvas': 'Canvas Editor',
    'mapping': 'Electrical Mapping',
    'board_builder': 'Board Builder',
    'electrical_cad': 'Electrical CAD',
    'learning': 'AI Learning',
    'kanban': 'Operations Board',
    'ai_mapping': 'AI Mapping',
    'simpro': 'Simpro Integration',
    'admin': 'Admin Panel'
}

# CRM sub-permissions for granular access control
CRM_PERMISSIONS = {
    'crm_customers': 'Customers',
    'crm_projects': 'Projects',
    'crm_communications': 'Communications',
    'crm_calendar': 'Calendar',
    'crm_technicians': 'Technicians',
    'crm_inventory': 'Inventory',
    'crm_suppliers': 'Suppliers',
    'crm_stock': 'Stock Management',
    'crm_reports': 'Reports & Analytics'
}

# Predefined roles
ROLES = {
    'admin': {
        'name': 'Administrator',
        'permissions': list(PERMISSIONS.keys())  # All permissions
    },
    'manager': {
        'name': 'Manager',
        'permissions': ['crm', 'quotes', 'canvas', 'mapping', 'board_builder', 'electrical_cad', 'kanban']
    },
    'technician': {
        'name': 'Technician',
        'permissions': ['crm', 'quotes', 'canvas', 'mapping', 'electrical_cad']
    },
    'viewer': {
        'name': 'Viewer',
        'permissions': ['crm', 'quotes']
    }
}


def init_users_file():
    """
    Initialize users file with default admin account.
    Only used in development when JSON fallback is allowed.
    """
    # Check storage policy
    _check_json_allowed()
    
    os.makedirs('crm_data', exist_ok=True)

    if not os.path.exists(USERS_FILE):
        # Create default admin user
        default_admin = {
            'id': str(uuid.uuid4()),
            'name': 'Admin',
            'code': safe_generate_password_hash('1234'),  # Simple 4-digit code
            'display_name': 'System Administrator',
            'role': 'admin',
            'permissions': list(PERMISSIONS.keys()),
            'active': True,
            'created_at': datetime.utcnow().isoformat(),
            'last_login': None
        }

        users_data = {
            'users': [default_admin]
        }

        with open(USERS_FILE, 'w') as f:
            json.dump(users_data, f, indent=2)

        logger.info("Created default admin account: Admin / 1234")
        return True
    return False


def load_users():
    """
    Load users from JSON file.
    Only used in development when JSON fallback is allowed.
    """
    # Check storage policy
    _check_json_allowed()
    
    init_users_file()

    try:
        with open(USERS_FILE, 'r') as f:
            data = json.load(f)
            return data.get('users', [])
    except Exception as e:
        logger.error(f"Error loading users: {e}")
        return []


def save_users(users):
    """
    Save users to JSON file.
    Only used in development when JSON fallback is allowed.
    """
    # Check storage policy
    _check_json_allowed()
    
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump({'users': users}, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving users: {e}")
        return False


def get_user_by_name(name):
    """Get user by name"""
    users = load_users()
    for user in users:
        if user['name'].lower() == name.lower():
            return user
    return None


def get_user_by_id(user_id):
    """Get user by ID"""
    users = load_users()
    for user in users:
        if user['id'] == user_id:
            return user
    return None


def create_user(name, code, display_name, role='viewer', custom_permissions=None, crm_permissions=None):
    """Create a new user (admin only)"""
    users = load_users()

    # Check if user already exists
    if get_user_by_name(name):
        return None, "User with this name already exists"

    # Get permissions from role or use custom
    if custom_permissions:
        permissions = custom_permissions
    else:
        permissions = ROLES.get(role, {}).get('permissions', ['crm', 'quotes'])

    new_user = {
        'id': str(uuid.uuid4()),
        'name': name,
        'code': safe_generate_password_hash(code),  # Hash the code
        'display_name': display_name,
        'role': role,
        'permissions': permissions,
        'crm_permissions': crm_permissions or list(CRM_PERMISSIONS.keys()) if 'crm' in permissions else [],
        'active': True,
        'created_at': datetime.utcnow().isoformat(),
        'last_login': None
    }

    users.append(new_user)

    if save_users(users):
        logger.info(f"Created new user: {name} with role {role}")
        return new_user, None
    else:
        return None, "Failed to save user"


def update_user(user_id, **kwargs):
    """Update user information"""
    users = load_users()

    for i, user in enumerate(users):
        if user['id'] == user_id:
            # Update allowed fields
            if 'name' in kwargs:
                user['name'] = kwargs['name']
            if 'display_name' in kwargs:
                user['display_name'] = kwargs['display_name']
            if 'role' in kwargs:
                user['role'] = kwargs['role']
                # Update permissions based on role if not custom
                if 'permissions' not in kwargs:
                    user['permissions'] = ROLES.get(kwargs['role'], {}).get('permissions', [])
            if 'permissions' in kwargs:
                user['permissions'] = kwargs['permissions']
            if 'active' in kwargs:
                user['active'] = kwargs['active']
            if 'code' in kwargs and kwargs['code']:
                user['code'] = safe_generate_password_hash(kwargs['code'])
            if 'crm_permissions' in kwargs:
                user['crm_permissions'] = kwargs['crm_permissions']

            users[i] = user

            if save_users(users):
                logger.info(f"Updated user: {user['name']}")
                return user, None
            else:
                return None, "Failed to save user"

    return None, "User not found"


def delete_user(user_id):
    """Delete a user"""
    users = load_users()

    # Prevent deleting the last admin
    admin_count = sum(1 for u in users if 'admin' in u.get('permissions', []))
    user_to_delete = get_user_by_id(user_id)

    if user_to_delete and 'admin' in user_to_delete.get('permissions', []) and admin_count <= 1:
        return False, "Cannot delete the last admin user"

    users = [u for u in users if u['id'] != user_id]

    if save_users(users):
        logger.info(f"Deleted user: {user_id}")
        return True, None
    else:
        return False, "Failed to save changes"


def authenticate_user(name, code):
    """Authenticate user with name and code"""
    user = get_user_by_name(name)

    if not user:
        return None, "Invalid name or code"

    if not user.get('active', False):
        return None, "Account is deactivated"

    if not safe_check_password_hash(user['code'], code):
        return None, "Invalid name or code"

    # Update last login
    users = load_users()
    for i, u in enumerate(users):
        if u['id'] == user['id']:
            users[i]['last_login'] = datetime.utcnow().isoformat()
            save_users(users)
            user['last_login'] = users[i]['last_login']
            break

    logger.info(f"User authenticated: {name}")
    return user, None


def login_user(user):
    """Set user session"""
    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['user_display_name'] = user['display_name']
    session['user_role'] = user['role']
    session['user_permissions'] = user['permissions']
    session['crm_permissions'] = user.get('crm_permissions', list(CRM_PERMISSIONS.keys()) if 'crm' in user['permissions'] else [])
    session.permanent = True


def logout_user():
    """Clear user session"""
    session.clear()


def get_current_user():
    """Get currently logged in user"""
    user_id = session.get('user_id')
    if user_id:
        return get_user_by_id(user_id)
    return None


def is_authenticated():
    """Check if user is logged in"""
    return 'user_id' in session


def has_permission(permission):
    """Check if current user has a specific permission"""
    if not is_authenticated():
        return False

    user_permissions = session.get('user_permissions', [])
    return permission in user_permissions or 'admin' in user_permissions


# Decorators for route protection
def login_required(f):
    """Decorator to require login for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required', 'redirect': '/login'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function


def permission_required(permission):
    """Decorator to require specific permission for a route"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not is_authenticated():
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Authentication required', 'redirect': '/login'}), 401
                return redirect(url_for('login_page'))

            if not has_permission(permission):
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Permission denied', 'required': permission}), 403
                return redirect(url_for('index'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """Decorator to require admin permission"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required', 'redirect': '/login'}), 401
            return redirect(url_for('login_page'))

        if not has_permission('admin'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Admin permission required'}), 403
            return redirect(url_for('index'))

        return f(*args, **kwargs)
    return decorated_function
