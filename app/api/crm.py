"""
CRM Routes Blueprint

Comprehensive CRM API handling:
- Customers: CRUD operations
- Projects: CRUD with markups, cost centres, room assignments
- Quotes: CRUD with stock items, labour, documents, PDF generation
- Jobs: CRUD with documents, item assignments
- Stock/Inventory: CRUD with serial numbers
- Calendar: Events management
- Communications: Logging
- Google Integration: Calendar, Gmail
- People/Technicians/Suppliers: Management
- Payments: Management with invoice generation
- Integration: Health checks, snapshots, linking
- V2 Enhanced API: With pagination and search
"""

import os
import io
import json
import uuid
import base64
import traceback
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file, current_app, session, redirect, url_for
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import logging

logger = logging.getLogger(__name__)

# Create blueprint
crm_bp = Blueprint('crm_bp', __name__)


def get_app_functions():
    """Get functions from main app"""
    return current_app.config.get('APP_FUNCTIONS', {})


def get_file_paths():
    """Get file paths from app config"""
    return {
        'CUSTOMERS_FILE': current_app.config.get('CUSTOMERS_FILE'),
        'PROJECTS_FILE': current_app.config.get('PROJECTS_FILE'),
        'QUOTES_FILE': current_app.config.get('QUOTES_FILE'),
        'STOCK_FILE': current_app.config.get('STOCK_FILE'),
        'JOBS_FILE': current_app.config.get('JOBS_FILE'),
        'COMMUNICATIONS_FILE': current_app.config.get('COMMUNICATIONS_FILE'),
        'CALENDAR_FILE': current_app.config.get('CALENDAR_FILE'),
        'TECHNICIANS_FILE': current_app.config.get('TECHNICIANS_FILE'),
        'INVENTORY_FILE': current_app.config.get('INVENTORY_FILE'),
        'PRICE_CLASSES_FILE': current_app.config.get('PRICE_CLASSES_FILE'),
        'SUPPLIERS_FILE': current_app.config.get('SUPPLIERS_FILE'),
        'GOOGLE_CONFIG_FILE': current_app.config.get('GOOGLE_CONFIG_FILE'),
        'UPLOAD_FOLDER': current_app.config.get('UPLOAD_FOLDER'),
        'OUTPUT_FOLDER': current_app.config.get('OUTPUT_FOLDER'),
    }


# ============================================================================
# STORAGE POLICY HELPERS
# ============================================================================

def use_database():
    """
    Check if database should be used for CRM data.
    Returns True if DATABASE_URL is configured.
    """
    from config import has_database
    return has_database()


def use_json_fallback():
    """
    Check if JSON fallback is allowed for CRM data.
    Returns True only in development when no database is configured.
    """
    from config import allow_json_persistence
    return allow_json_persistence()


def get_db_layer():
    """
    Get the database layer if database is configured.
    Returns CRMDatabaseLayer instance or None.
    """
    if not use_database():
        return None
    try:
        from crm_db_layer import CRMDatabaseLayer
        return CRMDatabaseLayer()
    except Exception as e:
        logger.error(f"Failed to initialize database layer: {e}")
        return None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_json_file(filepath, default=None):
    """
    Load JSON file with default fallback.
    
    NOTE: This is only used when JSON fallback is allowed (dev mode without DB).
    In production, database operations are used instead.
    
    Raises StoragePolicyError if called in production without database.
    """
    from config import allow_json_persistence, is_production, StoragePolicyError
    
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
    
    NOTE: This is only used when JSON fallback is allowed (dev mode without DB).
    In production, database operations are used instead.
    
    Raises StoragePolicyError if called in production without database.
    """
    from config import allow_json_persistence, is_production, StoragePolicyError
    
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
# STOCK/INVENTORY ROUTES
# ============================================================================

@crm_bp.route('/api/crm/stock', methods=['GET', 'POST'])
def get_or_create_crm_stock():
    """Get or create CRM stock data"""
    paths = get_file_paths()
    STOCK_FILE = paths['STOCK_FILE']
    
    if request.method == 'GET':
        try:
            stock_data = load_json_file(STOCK_FILE, [])
            return jsonify({
                'success': True,
                'stock': stock_data if isinstance(stock_data, list) else []
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    elif request.method == 'POST':
        try:
            data = request.get_json()
            name = data.get('name', '').strip()
            if not name:
                return jsonify({'success': False, 'error': 'Stock item name is required'}), 400

            stock_data = load_json_file(STOCK_FILE, [])

            new_item = {
                'id': str(uuid.uuid4()),
                'name': name,
                'sku': data.get('sku', ''),
                'category': data.get('category', 'general'),
                'quantity': int(data.get('quantity', 0)),
                'unit_price': float(data.get('unit_price', 0)),
                'location': data.get('location', ''),
                'reorder_level': int(data.get('reorder_level', 5)),
                'serial_numbers': data.get('serial_numbers', []),
                'image': data.get('image', ''),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            stock_data.append(new_item)
            save_json_file(STOCK_FILE, stock_data)

            return jsonify({
                'success': True,
                'id': new_item['id'],
                'message': f'Stock item "{name}" created successfully'
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500


@crm_bp.route('/api/crm/stock/add', methods=['POST'])
def add_to_crm_stock():
    """Add item to CRM stock"""
    try:
        paths = get_file_paths()
        STOCK_FILE = paths['STOCK_FILE']
        
        data = request.get_json()
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Stock item name is required'}), 400

        category = data.get('category', 'general')
        item_type = data.get('type', 'component')
        quantity = data.get('quantity', 1)
        if quantity < 0:
            return jsonify({'success': False, 'error': 'Quantity cannot be negative'}), 400

        stock_data = load_json_file(STOCK_FILE, [])

        existing = next((s for s in stock_data if s.get('name') == name), None)

        if existing:
            existing['quantity'] = existing.get('quantity', 0) + quantity
            existing['updated_at'] = datetime.now().isoformat()
            save_json_file(STOCK_FILE, stock_data)
            return jsonify({
                'success': True,
                'id': existing['id'],
                'message': f'Updated quantity for "{name}"'
            })
        else:
            new_item = {
                'id': str(uuid.uuid4()),
                'name': name,
                'sku': data.get('sku', ''),
                'category': category,
                'type': item_type,
                'quantity': quantity,
                'unit_price': float(data.get('unit_price', 0)),
                'cost': float(data.get('cost', 0)),
                'location': data.get('location', ''),
                'reorder_level': int(data.get('reorder_level', 5)),
                'serial_numbers': [],
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            stock_data.append(new_item)
            save_json_file(STOCK_FILE, stock_data)
            return jsonify({
                'success': True,
                'id': new_item['id'],
                'message': f'Stock item "{name}" created'
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# CUSTOMERS ROUTES
# ============================================================================

@crm_bp.route('/api/crm/customers', methods=['GET', 'POST'])
def handle_customers():
    """Handle customer list and creation"""
    try:
        paths = get_file_paths()
        CUSTOMERS_FILE = paths['CUSTOMERS_FILE']
        
        if request.method == 'GET':
            customers = load_json_file(CUSTOMERS_FILE, [])
            return jsonify({'success': True, 'customers': customers})
        else:
            data = request.json
            name = data.get('name', '').strip()
            if not name:
                return jsonify({'success': False, 'error': 'Customer name is required'}), 400

            customers = load_json_file(CUSTOMERS_FILE, [])
            customer = {
                'id': str(uuid.uuid4()),
                'name': name,
                'company': data.get('company', '').strip(),
                'email': data.get('email', '').strip(),
                'phone': data.get('phone', '').strip(),
                'address': data.get('address', '').strip(),
                'status': data.get('status', 'active'),
                'notes': data.get('notes', '').strip(),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            customers.append(customer)
            save_json_file(CUSTOMERS_FILE, customers)
            return jsonify({'success': True, 'customer': customer})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_bp.route('/api/crm/customers/<customer_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_customer(customer_id):
    """Handle single customer operations"""
    try:
        paths = get_file_paths()
        CUSTOMERS_FILE = paths['CUSTOMERS_FILE']
        
        customers = load_json_file(CUSTOMERS_FILE, [])
        idx = next((i for i, c in enumerate(customers) if c['id'] == customer_id), None)
        
        if request.method == 'GET':
            if idx is None:
                return jsonify({'success': False, 'error': 'Not found'}), 404
            return jsonify({'success': True, 'customer': customers[idx]})
        
        elif request.method == 'PUT':
            if idx is None:
                return jsonify({'success': False, 'error': 'Not found'}), 404
            data = request.json
            customer = customers[idx]
            for field in ['name', 'company', 'email', 'phone', 'address', 'status', 'notes']:
                if field in data:
                    customer[field] = data[field]
            customer['updated_at'] = datetime.now().isoformat()
            customers[idx] = customer
            save_json_file(CUSTOMERS_FILE, customers)
            return jsonify({'success': True, 'customer': customer})
        
        elif request.method == 'DELETE':
            if idx is None:
                return jsonify({'success': False, 'error': 'Not found'}), 404
            customers.pop(idx)
            save_json_file(CUSTOMERS_FILE, customers)
            return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# PROJECTS ROUTES
# ============================================================================

@crm_bp.route('/api/crm/projects', methods=['GET', 'POST'])
def handle_projects():
    """Handle project list and creation"""
    try:
        paths = get_file_paths()
        PROJECTS_FILE = paths['PROJECTS_FILE']
        
        if request.method == 'GET':
            projects = load_json_file(PROJECTS_FILE, [])
            customer_id = request.args.get('customer_id')
            if customer_id:
                projects = [p for p in projects if p.get('customer_id') == customer_id]
            return jsonify({'success': True, 'projects': projects})
        else:
            data = request.json
            title = data.get('title', '').strip()
            if not title:
                return jsonify({'success': False, 'error': 'Project title is required'}), 400

            projects = load_json_file(PROJECTS_FILE, [])
            project = {
                'id': str(uuid.uuid4()),
                'customer_id': data.get('customer_id'),
                'title': title,
                'description': data.get('description', '').strip(),
                'status': data.get('status', 'pending'),
                'priority': data.get('priority', 'medium'),
                'quote_amount': data.get('quote_amount', 0.0),
                'actual_amount': data.get('actual_amount', 0.0),
                'due_date': data.get('due_date'),
                'takeoffs_session_id': data.get('takeoffs_session_id'),
                'mapping_session_id': data.get('mapping_session_id'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            projects.append(project)
            save_json_file(PROJECTS_FILE, projects)
            return jsonify({'success': True, 'project': project})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_bp.route('/api/crm/projects/<project_id>', methods=['PUT', 'DELETE'])
def update_project(project_id):
    """Update or delete a project"""
    try:
        paths = get_file_paths()
        PROJECTS_FILE = paths['PROJECTS_FILE']
        
        projects = load_json_file(PROJECTS_FILE, [])
        idx = next((i for i, p in enumerate(projects) if p['id'] == project_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Not found'}), 404

        if request.method == 'PUT':
            data = request.json
            project = projects[idx]
            for field in ['title', 'description', 'status', 'priority', 'quote_amount', 'actual_amount', 'due_date', 'customer_id', 'takeoffs_session_id', 'mapping_session_id']:
                if field in data:
                    project[field] = data[field]
            project['updated_at'] = datetime.now().isoformat()
            projects[idx] = project
            save_json_file(PROJECTS_FILE, projects)
            return jsonify({'success': True, 'project': project})

        elif request.method == 'DELETE':
            projects.pop(idx)
            save_json_file(PROJECTS_FILE, projects)
            return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# QUOTES ROUTES  
# ============================================================================

@crm_bp.route('/api/crm/quotes', methods=['GET', 'POST'])
def handle_quotes():
    """Handle quote list and creation"""
    try:
        paths = get_file_paths()
        QUOTES_FILE = paths['QUOTES_FILE']
        
        if request.method == 'GET':
            quotes = load_json_file(QUOTES_FILE, [])
            customer_id = request.args.get('customer_id')
            status = request.args.get('status')
            if customer_id:
                quotes = [q for q in quotes if q.get('customer_id') == customer_id]
            if status:
                quotes = [q for q in quotes if q.get('status') == status]
            return jsonify({'success': True, 'quotes': quotes})
        else:
            data = request.json
            quotes = load_json_file(QUOTES_FILE, [])
            
            quote = {
                'id': str(uuid.uuid4()),
                'quote_number': data.get('quote_number', f"Q{len(quotes)+1:03d}"),
                'customer_id': data.get('customer_id'),
                'title': data.get('title', '').strip(),
                'description': data.get('description', '').strip(),
                'status': data.get('status', 'draft'),
                'total_amount': float(data.get('total_amount', 0)),
                'valid_until': data.get('valid_until'),
                'items': data.get('items', []),
                'costs': data.get('costs', {}),
                'notes': data.get('notes', ''),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            quotes.append(quote)
            save_json_file(QUOTES_FILE, quotes)
            return jsonify({'success': True, 'quote': quote})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_bp.route('/api/crm/quotes/<quote_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_quote(quote_id):
    """Handle single quote operations"""
    try:
        paths = get_file_paths()
        QUOTES_FILE = paths['QUOTES_FILE']
        
        quotes = load_json_file(QUOTES_FILE, [])
        idx = next((i for i, q in enumerate(quotes) if q['id'] == quote_id), None)
        
        if request.method == 'GET':
            if idx is None:
                return jsonify({'success': False, 'error': 'Not found'}), 404
            return jsonify({'success': True, 'quote': quotes[idx]})
        
        elif request.method == 'PUT':
            if idx is None:
                return jsonify({'success': False, 'error': 'Not found'}), 404
            data = request.json
            quote = quotes[idx]
            for field in ['title', 'description', 'status', 'total_amount', 'valid_until', 'items', 'costs', 'notes', 'customer_id', 'quote_number']:
                if field in data:
                    quote[field] = data[field]
            quote['updated_at'] = datetime.now().isoformat()
            quotes[idx] = quote
            save_json_file(QUOTES_FILE, quotes)
            return jsonify({'success': True, 'quote': quote})
        
        elif request.method == 'DELETE':
            if idx is None:
                return jsonify({'success': False, 'error': 'Not found'}), 404
            quotes.pop(idx)
            save_json_file(QUOTES_FILE, quotes)
            return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# STATS AND INTEGRATIONS
# ============================================================================

@crm_bp.route('/api/crm/stats', methods=['GET'])
def get_crm_stats():
    """Get CRM statistics"""
    try:
        paths = get_file_paths()
        
        customers = load_json_file(paths['CUSTOMERS_FILE'], [])
        projects = load_json_file(paths['PROJECTS_FILE'], [])
        quotes = load_json_file(paths['QUOTES_FILE'], [])
        
        # Calculate quote stats
        total_quotes = len(quotes)
        pending_quotes = len([q for q in quotes if q.get('status') == 'pending'])
        accepted_quotes = len([q for q in quotes if q.get('status') == 'accepted'])
        total_quote_value = sum(float(q.get('total_amount', 0)) for q in quotes)
        pending_quote_value = sum(float(q.get('total_amount', 0)) for q in quotes if q.get('status') == 'pending')
        
        return jsonify({
            'success': True,
            'stats': {
                'customers': {
                    'total': len(customers),
                    'active': len([c for c in customers if c.get('status') == 'active'])
                },
                'projects': {
                    'total': len(projects),
                    'active': len([p for p in projects if p.get('status') in ['active', 'in_progress']]),
                    'pending': len([p for p in projects if p.get('status') == 'pending'])
                },
                'quotes': {
                    'total': total_quotes,
                    'pending': pending_quotes,
                    'accepted': accepted_quotes,
                    'total_value': total_quote_value,
                    'pending_value': pending_quote_value
                }
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_bp.route('/api/crm/integrations', methods=['GET'])
def get_integrations():
    """Get available integrations status"""
    return jsonify({
        'success': True,
        'integrations': {
            'google': {'enabled': False, 'connected': False},
            'simpro': {'enabled': True, 'connected': False}
        }
    })


# Note: Additional CRM routes (markups, cost centres, documents, etc.) 
# are handled by the main app.py and will be migrated incrementally.
# This blueprint contains the core CRM functionality.

