"""
CRM Integration Routes Blueprint

Handles CRM data integration and cross-entity operations:
- Health reports
- Data snapshots
- Entity linking
- Validation
- Cleanup
"""

import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

# Create blueprint
crm_integration_bp = Blueprint('crm_integration_bp', __name__)


def get_crm_integration():
    """Get crm_integration module"""
    import crm_integration
    return crm_integration


# ============================================================================
# HEALTH & SNAPSHOT
# ============================================================================

@crm_integration_bp.route('/api/crm/integration/health', methods=['GET'])
def get_crm_health():
    """Get CRM data health report"""
    try:
        crm_int = get_crm_integration()
        report = crm_int.get_crm_health_report()
        return jsonify({'success': True, 'report': report})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_integration_bp.route('/api/crm/integration/snapshot', methods=['GET'])
def get_crm_snapshot():
    """Get complete CRM data snapshot with all relationships"""
    try:
        crm_int = get_crm_integration()
        snapshot = crm_int.get_complete_crm_snapshot()
        return jsonify({'success': True, 'data': snapshot})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# ENTITY QUERIES
# ============================================================================

@crm_integration_bp.route('/api/crm/integration/project/<project_id>', methods=['GET'])
def get_project_with_relations(project_id):
    """Get project with all related data (customer, communications, events)"""
    try:
        crm_int = get_crm_integration()
        project = crm_int.get_project_details(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        return jsonify({'success': True, 'project': project})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_integration_bp.route('/api/crm/integration/customer/<customer_id>/projects', methods=['GET'])
def get_customer_projects_api(customer_id):
    """Get all projects for a customer"""
    try:
        crm_int = get_crm_integration()
        projects = crm_int.get_customer_projects(customer_id)
        return jsonify({'success': True, 'projects': projects})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_integration_bp.route('/api/crm/integration/customer/<customer_id>/communications', methods=['GET'])
def get_customer_comms_api(customer_id):
    """Get all communications for a customer"""
    try:
        crm_int = get_crm_integration()
        comms = crm_int.get_customer_communications(customer_id)
        return jsonify({'success': True, 'communications': comms})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_integration_bp.route('/api/crm/integration/technician/<tech_id>/schedule', methods=['GET'])
def get_tech_schedule_api(tech_id):
    """Get technician's schedule with project details"""
    try:
        crm_int = get_crm_integration()
        schedule = crm_int.get_technician_schedule(tech_id)
        return jsonify({'success': True, 'schedule': schedule})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_integration_bp.route('/api/crm/integration/user/<user_id>/projects', methods=['GET'])
def get_user_projects_api(user_id):
    """Get projects assigned to a user (via technician link)"""
    try:
        crm_int = get_crm_integration()
        projects = crm_int.get_user_assigned_projects(user_id)
        return jsonify({'success': True, 'projects': projects})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_integration_bp.route('/api/crm/integration/supplier/<supplier_id>/inventory', methods=['GET'])
def get_supplier_inventory_api(supplier_id):
    """Get all inventory from a supplier"""
    try:
        crm_int = get_crm_integration()
        inventory = crm_int.get_inventory_by_supplier(supplier_id)
        return jsonify({'success': True, 'inventory': inventory})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# ENTITY LINKING
# ============================================================================

@crm_integration_bp.route('/api/crm/integration/link/technician', methods=['POST'])
def link_technician_to_user_api():
    """Link a technician to a user account"""
    try:
        crm_int = get_crm_integration()
        data = request.json
        tech_id = data.get('tech_id')
        user_id = data.get('user_id')

        if not tech_id or not user_id:
            return jsonify({'success': False, 'error': 'Missing tech_id or user_id'}), 400

        success = crm_int.link_technician_to_user(tech_id, user_id)
        if success:
            return jsonify({'success': True, 'message': 'Technician linked to user'})
        else:
            return jsonify({'success': False, 'error': 'Technician not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_integration_bp.route('/api/crm/integration/link/project', methods=['POST'])
def link_project_to_customer_api():
    """Link a project to a customer"""
    try:
        crm_int = get_crm_integration()
        data = request.json
        project_id = data.get('project_id')
        customer_id = data.get('customer_id')

        if not project_id or not customer_id:
            return jsonify({'success': False, 'error': 'Missing project_id or customer_id'}), 400

        success = crm_int.link_project_to_customer(project_id, customer_id)
        if success:
            return jsonify({'success': True, 'message': 'Project linked to customer'})
        else:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_integration_bp.route('/api/crm/integration/link/communication', methods=['POST'])
def link_communication_api():
    """Link a communication to customer and/or project"""
    try:
        crm_int = get_crm_integration()
        data = request.json
        comm_id = data.get('comm_id')
        customer_id = data.get('customer_id')
        project_id = data.get('project_id')

        if not comm_id:
            return jsonify({'success': False, 'error': 'Missing comm_id'}), 400

        success = crm_int.link_communication_to_entities(comm_id, customer_id, project_id)
        if success:
            return jsonify({'success': True, 'message': 'Communication linked'})
        else:
            return jsonify({'success': False, 'error': 'Communication not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_integration_bp.route('/api/crm/integration/link/event', methods=['POST'])
def link_event_api():
    """Link a calendar event to project and/or technician"""
    try:
        crm_int = get_crm_integration()
        data = request.json
        event_id = data.get('event_id')
        project_id = data.get('project_id')
        technician_id = data.get('technician_id')

        if not event_id:
            return jsonify({'success': False, 'error': 'Missing event_id'}), 400

        success = crm_int.link_event_to_entities(event_id, project_id, technician_id)
        if success:
            return jsonify({'success': True, 'message': 'Event linked'})
        else:
            return jsonify({'success': False, 'error': 'Event not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_integration_bp.route('/api/crm/integration/link/inventory', methods=['POST'])
def link_inventory_api():
    """Link an inventory item to a supplier"""
    try:
        crm_int = get_crm_integration()
        data = request.json
        item_id = data.get('item_id')
        supplier_id = data.get('supplier_id')

        if not item_id or not supplier_id:
            return jsonify({'success': False, 'error': 'Missing item_id or supplier_id'}), 400

        success = crm_int.link_inventory_to_supplier(item_id, supplier_id)
        if success:
            return jsonify({'success': True, 'message': 'Inventory item linked to supplier'})
        else:
            return jsonify({'success': False, 'error': 'Inventory item not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# CLEANUP & VALIDATION
# ============================================================================

@crm_integration_bp.route('/api/crm/integration/cleanup', methods=['POST'])
def cleanup_orphaned_refs_api():
    """Clean up orphaned references in CRM data"""
    try:
        crm_int = get_crm_integration()
        cleanup_count = crm_int.cleanup_orphaned_references()
        return jsonify({
            'success': True,
            'message': 'Cleanup completed',
            'cleaned': cleanup_count
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_integration_bp.route('/api/crm/integration/validate/project/<project_id>', methods=['GET'])
def validate_project_api(project_id):
    """Validate all references to a project"""
    try:
        crm_int = get_crm_integration()
        validation = crm_int.validate_project_references(project_id)
        return jsonify({'success': True, 'validation': validation})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

