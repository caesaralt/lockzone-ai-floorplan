"""
Kanban Board Routes Blueprint

Handles kanban task management:
- /api/kanban/tasks: List/create tasks
- /api/kanban/tasks/<task_id>: Update/delete tasks

STORAGE POLICY:
- Production: DATABASE_URL is REQUIRED. JSON persistence is disabled.
- Development: Database preferred, JSON fallback allowed if no DATABASE_URL.
"""

import os
import json
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
import logging

logger = logging.getLogger(__name__)

# Create blueprint
kanban_bp = Blueprint('kanban_bp', __name__)


# ============================================================================
# STORAGE POLICY HELPERS
# ============================================================================

def use_database():
    """Check if database should be used for kanban data."""
    from config import has_database
    return has_database()


def use_json_fallback():
    """Check if JSON fallback is allowed for kanban data."""
    from config import allow_json_persistence
    return allow_json_persistence()


def get_app_config():
    """Get app config values"""
    return {
        'CRM_USE_DATABASE': use_database(),
        'CRM_DATA_FOLDER': current_app.config.get('CRM_DATA_FOLDER', 'crm_data')
    }


def _get_kanban_org_id():
    """Get the organization ID for kanban operations."""
    if use_database():
        try:
            from database.seed import get_or_create_default_organization
            from database.connection import get_db_session
            with get_db_session() as session:
                org = get_or_create_default_organization(session)
                return org.id
        except Exception as e:
            logger.error(f"Error getting org ID for kanban: {e}")
            return None
    return None


# ============================================================================
# JSON FILE HELPERS (for local dev fallback ONLY)
# ============================================================================

def load_json_file(filepath, default=None):
    """
    Load JSON file with default fallback.
    Raises StoragePolicyError if called in production without database.
    """
    from config import is_production, StoragePolicyError
    
    if is_production() and not use_database():
        raise StoragePolicyError(
            "JSON persistence is disabled in production. DATABASE_URL must be configured."
        )
    
    if default is None:
        default = []
    try:
        if filepath and os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
    except StoragePolicyError:
        raise
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
    return default


def save_json_file(filepath, data):
    """
    Save data to JSON file.
    Raises StoragePolicyError if called in production without database.
    """
    from config import is_production, StoragePolicyError
    
    if is_production() and not use_database():
        raise StoragePolicyError(
            "JSON persistence is disabled in production. DATABASE_URL must be configured."
        )
    
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except StoragePolicyError:
        raise
    except Exception as e:
        logger.error(f"Error saving {filepath}: {e}")
        return False


# ============================================================================
# KANBAN ROUTES
# ============================================================================

@kanban_bp.route('/api/kanban/tasks', methods=['GET', 'POST'])
def handle_kanban_tasks():
    """Get all tasks or create new task"""
    try:
        config = get_app_config()
        
        if config['CRM_USE_DATABASE']:
            from database.connection import get_db_session
            from services.kanban_repository import KanbanRepository
            
            org_id = _get_kanban_org_id()
            if not org_id:
                return jsonify({'success': False, 'error': 'Organization not found'}), 500
            
            with get_db_session() as session:
                repo = KanbanRepository(session, org_id)
                
                if request.method == 'GET':
                    show_archived = request.args.get('archived') == 'true'
                    tasks = repo.list_tasks(archived=show_archived)
                    return jsonify({'success': True, 'tasks': tasks})
                else:
                    data = request.json
                    task = repo.create_task(data)
                    session.commit()
                    return jsonify({'success': True, 'task': task})
        else:
            # Fallback to JSON file
            KANBAN_FILE = os.path.join(config['CRM_DATA_FOLDER'], 'kanban_tasks.json')
            
            if request.method == 'GET':
                show_archived = request.args.get('archived') == 'true'
                all_tasks = load_json_file(KANBAN_FILE, [])
                if show_archived:
                    tasks = [t for t in all_tasks if t.get('archived', False)]
                else:
                    tasks = [t for t in all_tasks if not t.get('archived', False)]
                return jsonify({'success': True, 'tasks': tasks})
            else:
                data = request.json
                task_id = str(uuid.uuid4())
                position = data.get('position', {'x': 10, 'y': 10})

                tasks = load_json_file(KANBAN_FILE, [])
                task = {
                    'id': task_id,
                    'column': data.get('column', 'todo'),
                    'content': data.get('content', 'New Task'),
                    'notes': data.get('notes', ''),
                    'color': data.get('color', '#ffffff'),
                    'position': position,
                    'assigned_to': data.get('assigned_to'),
                    'pinned': data.get('pinned', False),
                    'due_date': data.get('due_date'),
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                tasks.append(task)
                save_json_file(KANBAN_FILE, tasks)
                return jsonify({'success': True, 'task': task})
    except Exception as e:
        logger.error(f"Kanban tasks error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@kanban_bp.route('/api/kanban/tasks/<task_id>', methods=['PUT', 'DELETE'])
def handle_kanban_task(task_id):
    """Update or delete a specific task"""
    try:
        config = get_app_config()
        
        if config['CRM_USE_DATABASE']:
            from database.connection import get_db_session
            from services.kanban_repository import KanbanRepository
            
            org_id = _get_kanban_org_id()
            if not org_id:
                return jsonify({'success': False, 'error': 'Organization not found'}), 500
            
            with get_db_session() as session:
                repo = KanbanRepository(session, org_id)
                
                if request.method == 'PUT':
                    data = request.json
                    task = repo.update_task(task_id, data)
                    if not task:
                        return jsonify({'success': False, 'error': 'Task not found'}), 404
                    session.commit()
                    return jsonify({'success': True, 'task': task})
                
                elif request.method == 'DELETE':
                    if not repo.delete_task(task_id):
                        return jsonify({'success': False, 'error': 'Task not found'}), 404
                    session.commit()
                    return jsonify({'success': True})
        else:
            # Fallback to JSON file
            KANBAN_FILE = os.path.join(config['CRM_DATA_FOLDER'], 'kanban_tasks.json')
            tasks = load_json_file(KANBAN_FILE, [])
            idx = next((i for i, t in enumerate(tasks) if t['id'] == task_id), None)

            if idx is None:
                return jsonify({'success': False, 'error': 'Task not found'}), 404

            if request.method == 'PUT':
                data = request.json
                task = tasks[idx]
                for field in ['column', 'content', 'notes', 'color', 'position', 'due_date', 'assigned_to', 'pinned', 'archived']:
                    if field in data:
                        task[field] = data[field]
                if 'archived' in data and data['archived']:
                    task['archived_at'] = datetime.now().isoformat()
                elif 'archived' in data and not data['archived']:
                    task['archived_at'] = None
                task['updated_at'] = datetime.now().isoformat()
                tasks[idx] = task
                save_json_file(KANBAN_FILE, tasks)
                return jsonify({'success': True, 'task': task})

            elif request.method == 'DELETE':
                tasks.pop(idx)
                save_json_file(KANBAN_FILE, tasks)
                return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Kanban task error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

