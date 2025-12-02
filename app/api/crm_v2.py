"""
CRM V2 API Routes Blueprint

Enhanced CRM API with pagination, search, and better error handling:
- /api/v2/crm/stats - Comprehensive statistics
- /api/v2/crm/customers - Customer management with pagination
- /api/v2/crm/projects - Project management with pagination
- /api/v2/crm/quotes - Quote management with pagination
- /api/v2/crm/stock - Stock management with pagination
- /api/v2/crm/integrity - Data integrity checks
"""

import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

# Create blueprint
crm_v2_bp = Blueprint('crm_v2_bp', __name__)


def get_crm_data():
    """Get crm_data layer instance"""
    from crm_data_layer import get_crm_data_layer
    return get_crm_data_layer()


# ============================================================================
# STATS
# ============================================================================

@crm_v2_bp.route('/api/v2/crm/stats', methods=['GET'])
def get_crm_stats_v2():
    """Get comprehensive CRM statistics with quote stats"""
    try:
        crm_data = get_crm_data()
        result = crm_data.get_stats()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting CRM stats: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# CUSTOMERS
# ============================================================================

@crm_v2_bp.route('/api/v2/crm/customers', methods=['GET', 'POST'])
def handle_customers_v2():
    """Enhanced customer management with pagination and search"""
    try:
        crm_data = get_crm_data()
        if request.method == 'GET':
            result = crm_data.get_customers(
                search=request.args.get('search'),
                status=request.args.get('status'),
                page=int(request.args.get('page', 1)),
                per_page=int(request.args.get('per_page', 50)),
                sort_by=request.args.get('sort_by', 'created_at'),
                sort_order=request.args.get('sort_order', 'desc')
            )
            return jsonify(result)
        else:
            result = crm_data.create_customer(request.json)
            if result['success']:
                return jsonify(result), 201
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Error handling customers: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_v2_bp.route('/api/v2/crm/customers/<customer_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_customer_v2(customer_id):
    """Enhanced single customer management with related data"""
    try:
        crm_data = get_crm_data()
        if request.method == 'GET':
            result = crm_data.get_customer(customer_id)
            if not result['success']:
                return jsonify(result), 404
            return jsonify(result)
        
        elif request.method == 'PUT':
            result = crm_data.update_customer(customer_id, request.json)
            if not result['success']:
                return jsonify(result), 400 if 'not found' not in result.get('error', '').lower() else 404
            return jsonify(result)
        
        elif request.method == 'DELETE':
            cascade = request.args.get('cascade', 'false').lower() == 'true'
            result = crm_data.delete_customer(customer_id, cascade=cascade)
            if not result['success']:
                return jsonify(result), 400 if 'related' in str(result) else 404
            return jsonify(result)
    except Exception as e:
        logger.error(f"Error handling customer {customer_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# PROJECTS
# ============================================================================

@crm_v2_bp.route('/api/v2/crm/projects', methods=['GET', 'POST'])
def handle_projects_v2():
    """Enhanced project management with pagination and search"""
    try:
        crm_data = get_crm_data()
        if request.method == 'GET':
            result = crm_data.get_projects(
                customer_id=request.args.get('customer_id'),
                status=request.args.get('status'),
                search=request.args.get('search'),
                page=int(request.args.get('page', 1)),
                per_page=int(request.args.get('per_page', 50)),
                sort_by=request.args.get('sort_by', 'created_at'),
                sort_order=request.args.get('sort_order', 'desc')
            )
            return jsonify(result)
        else:
            result = crm_data.create_project(request.json)
            if result['success']:
                return jsonify(result), 201
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Error handling projects: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_v2_bp.route('/api/v2/crm/projects/<project_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_project_v2(project_id):
    """Enhanced single project management with related data"""
    try:
        crm_data = get_crm_data()
        if request.method == 'GET':
            result = crm_data.get_project(project_id)
            if not result['success']:
                return jsonify(result), 404
            return jsonify(result)
        
        elif request.method == 'PUT':
            result = crm_data.update_project(project_id, request.json)
            if not result['success']:
                return jsonify(result), 400 if 'not found' not in result.get('error', '').lower() else 404
            return jsonify(result)
        
        elif request.method == 'DELETE':
            result = crm_data.delete_project(project_id)
            if not result['success']:
                return jsonify(result), 404
            return jsonify(result)
    except Exception as e:
        logger.error(f"Error handling project {project_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# QUOTES
# ============================================================================

@crm_v2_bp.route('/api/v2/crm/quotes', methods=['GET', 'POST'])
def handle_quotes_v2():
    """Enhanced quote management with pagination and search"""
    try:
        crm_data = get_crm_data()
        if request.method == 'GET':
            result = crm_data.get_quotes(
                customer_id=request.args.get('customer_id'),
                status=request.args.get('status'),
                search=request.args.get('search'),
                page=int(request.args.get('page', 1)),
                per_page=int(request.args.get('per_page', 50)),
                sort_by=request.args.get('sort_by', 'created_at'),
                sort_order=request.args.get('sort_order', 'desc')
            )
            return jsonify(result)
        else:
            result = crm_data.create_quote(request.json)
            if result['success']:
                return jsonify(result), 201
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Error handling quotes: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_v2_bp.route('/api/v2/crm/quotes/<quote_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_quote_v2(quote_id):
    """Enhanced single quote management with related data"""
    try:
        crm_data = get_crm_data()
        if request.method == 'GET':
            result = crm_data.get_quote(quote_id)
            if not result['success']:
                return jsonify(result), 404
            return jsonify(result)
        
        elif request.method == 'PUT':
            result = crm_data.update_quote(quote_id, request.json)
            if not result['success']:
                return jsonify(result), 400 if 'not found' not in result.get('error', '').lower() else 404
            return jsonify(result)
        
        elif request.method == 'DELETE':
            result = crm_data.delete_quote(quote_id)
            if not result['success']:
                return jsonify(result), 404
            return jsonify(result)
    except Exception as e:
        logger.error(f"Error handling quote {quote_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_v2_bp.route('/api/v2/crm/quotes/<quote_id>/convert', methods=['POST'])
def convert_quote_v2(quote_id):
    """Convert a quote to a project using the data layer"""
    try:
        crm_data = get_crm_data()
        result = crm_data.convert_quote_to_project(quote_id)
        if not result['success']:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error converting quote {quote_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# STOCK
# ============================================================================

@crm_v2_bp.route('/api/v2/crm/stock', methods=['GET', 'POST'])
def handle_stock_v2():
    """Enhanced stock management with pagination and search"""
    try:
        crm_data = get_crm_data()
        if request.method == 'GET':
            result = crm_data.get_stock(
                category=request.args.get('category'),
                search=request.args.get('search'),
                low_stock_only=request.args.get('low_stock', 'false').lower() == 'true',
                page=int(request.args.get('page', 1)),
                per_page=int(request.args.get('per_page', 50)),
                sort_by=request.args.get('sort_by', 'name'),
                sort_order=request.args.get('sort_order', 'asc')
            )
            return jsonify(result)
        else:
            result = crm_data.create_stock_item(request.json)
            if result['success']:
                return jsonify(result), 201
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Error handling stock: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_v2_bp.route('/api/v2/crm/stock/<item_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_stock_item_v2(item_id):
    """Enhanced single stock item management"""
    try:
        crm_data = get_crm_data()
        if request.method == 'GET':
            result = crm_data.get_stock_item(item_id)
            if not result['success']:
                return jsonify(result), 404
            return jsonify(result)
        
        elif request.method == 'PUT':
            result = crm_data.update_stock_item(item_id, request.json)
            if not result['success']:
                return jsonify(result), 400 if 'not found' not in result.get('error', '').lower() else 404
            return jsonify(result)
        
        elif request.method == 'DELETE':
            result = crm_data.delete_stock_item(item_id)
            if not result['success']:
                return jsonify(result), 404
            return jsonify(result)
    except Exception as e:
        logger.error(f"Error handling stock item {item_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_v2_bp.route('/api/v2/crm/stock/<item_id>/adjust', methods=['POST'])
def adjust_stock_v2(item_id):
    """Adjust stock quantity"""
    try:
        crm_data = get_crm_data()
        data = request.json
        adjustment = int(data.get('adjustment', 0))
        reason = data.get('reason', '')
        
        result = crm_data.adjust_stock_quantity(item_id, adjustment, reason)
        if not result['success']:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error adjusting stock {item_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# INTEGRITY
# ============================================================================

@crm_v2_bp.route('/api/v2/crm/integrity', methods=['GET'])
def check_crm_integrity():
    """Check CRM data integrity"""
    try:
        crm_data = get_crm_data()
        result = crm_data.check_data_integrity()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error checking integrity: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_v2_bp.route('/api/v2/crm/integrity/repair', methods=['POST'])
def repair_crm_integrity():
    """Repair CRM data integrity issues"""
    try:
        crm_data = get_crm_data()
        result = crm_data.repair_data_integrity()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error repairing integrity: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

