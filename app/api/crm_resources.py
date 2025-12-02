"""
CRM Resources Routes Blueprint

Handles CRM resource management:
- Calendar
- Communications  
- Inventory
- Jobs
- Materials
- Payments
- People
- Price Classes
- Suppliers
- Technicians

STORAGE POLICY:
- Production: DATABASE_URL is REQUIRED. JSON persistence is disabled.
- Development: Database preferred, JSON fallback allowed if no DATABASE_URL.
"""

import os
import json
import uuid
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app

logger = logging.getLogger(__name__)

# Create blueprint
crm_resources_bp = Blueprint('crm_resources_bp', __name__)


# ============================================================================
# STORAGE POLICY HELPERS
# ============================================================================

def use_database():
    """Check if database should be used for CRM data."""
    from config import has_database
    return has_database()


def use_json_fallback():
    """Check if JSON fallback is allowed for CRM data."""
    from config import allow_json_persistence
    return allow_json_persistence()


def is_db_available():
    """Check if database is available (alias for use_database)"""
    return use_database()


def get_db_layer():
    """Get the CRM database layer instance"""
    if not use_database():
        return None
    try:
        from crm_db_layer import CRMDatabaseLayer
        from database.seed import get_default_organization_id
        org_id = get_default_organization_id()
        layer = CRMDatabaseLayer(org_id)
        if layer.db_enabled:
            return layer
        return None
    except Exception as e:
        logger.error(f"Failed to get database layer: {e}")
        return None


def get_db_session_and_repos():
    """Get database session and repositories for direct operations"""
    if not use_database():
        return None, None, None, None
    try:
        from database.connection import get_db_session
        from database.seed import get_default_organization_id
        from services.crm_repository import CRMRepository
        from services.inventory_repository import InventoryRepository
        
        org_id = get_default_organization_id()
        return get_db_session, org_id, CRMRepository, InventoryRepository
    except Exception as e:
        logger.error(f"Failed to get database components: {e}")
        return None, None, None, None


# ============================================================================
# JSON FILE HELPERS (for local dev fallback ONLY)
# ============================================================================

def get_crm_data_folder():
    """Get CRM data folder path"""
    return current_app.config.get('CRM_DATA_FOLDER', 'crm_data')


def load_json_file(filename, default=None):
    """
    Load JSON file with default fallback.
    
    NOTE: Only allowed in development when no database is configured.
    Raises StoragePolicyError if called in production without database.
    """
    from config import is_production, StoragePolicyError
    
    if is_production() and not use_database():
        raise StoragePolicyError(
            "JSON persistence is disabled in production. DATABASE_URL must be configured."
        )
    
    if default is None:
        default = []
    filepath = os.path.join(get_crm_data_folder(), filename)
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                data = json.load(f)
                # Handle nested dict format (e.g., calendar.json with {events: []})
                if isinstance(data, dict) and filename == 'calendar.json':
                    return data.get('events', [])
                return data
    except StoragePolicyError:
        raise
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
    return default


def save_json_file(filename, data):
    """
    Save data to JSON file.
    
    NOTE: Only allowed in development when no database is configured.
    Raises StoragePolicyError if called in production without database.
    """
    from config import is_production, StoragePolicyError
    
    if is_production() and not use_database():
        raise StoragePolicyError(
            "JSON persistence is disabled in production. DATABASE_URL must be configured."
        )
    
    folder = get_crm_data_folder()
    try:
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, filename)
        # Handle calendar.json special case
        if filename == 'calendar.json':
            data = {'events': data}
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except StoragePolicyError:
        raise
    except Exception as e:
        logger.error(f"Error saving {filename}: {e}")
        return False


# ============================================================================
# COMMUNICATIONS
# ============================================================================

@crm_resources_bp.route('/api/crm/communications', methods=['GET', 'POST'])
def handle_communications():
    """Manage communications"""
    get_db_session, org_id, CRMRepository, _ = get_db_session_and_repos()
    
    # Use database if available
    if get_db_session:
        try:
            with get_db_session() as session:
                repo = CRMRepository(session, org_id)
                
                if request.method == 'GET':
                    customer_id = request.args.get('customer_id')
                    project_id = request.args.get('project_id')
                    comms = repo.list_communications(customer_id=customer_id, project_id=project_id)
                    return jsonify({'success': True, 'communications': comms})
                else:
                    data = request.json
                    comm = repo.create_communication(data)
                    session.commit()
                    return jsonify({'success': True, 'communication': comm})
        except Exception as e:
            logger.error(f"Error handling communications: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # JSON fallback for local dev
    if request.method == 'GET':
        comms = load_json_file('communications.json', [])
        customer_id = request.args.get('customer_id')
        project_id = request.args.get('project_id')
        if customer_id:
            comms = [c for c in comms if c.get('customer_id') == customer_id]
        if project_id:
            comms = [c for c in comms if c.get('project_id') == project_id]
        return jsonify({'success': True, 'communications': comms})
    else:
        data = request.json
        comms = load_json_file('communications.json', [])
        comm = {
            'id': str(uuid.uuid4()),
            'type': data.get('type', 'note'),
            'subject': data.get('subject', ''),
            'content': data.get('content', ''),
            'customer_id': data.get('customer_id'),
            'project_id': data.get('project_id'),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        comms.append(comm)
        save_json_file('communications.json', comms)
        return jsonify({'success': True, 'communication': comm})


@crm_resources_bp.route('/api/crm/communications/<comm_id>', methods=['PUT', 'DELETE'])
def handle_communication(comm_id):
    """Manage a specific communication"""
    get_db_session, org_id, CRMRepository, _ = get_db_session_and_repos()
    
    # Use database if available
    if get_db_session:
        try:
            from database.models import Communication
            
            with get_db_session() as session:
                comm = session.query(Communication).filter(
                    Communication.id == comm_id,
                    Communication.organization_id == org_id
                ).first()
                
                if not comm:
                    return jsonify({'success': False, 'error': 'Communication not found'}), 404
                
                if request.method == 'PUT':
                    data = request.json
                    for key in ['subject', 'content', 'status']:
                        if key in data:
                            setattr(comm, key, data[key])
                    if 'type' in data:
                        comm.comm_type = data['type']
                    comm.updated_at = datetime.utcnow()
                    session.commit()
                    return jsonify({'success': True, 'communication': comm.to_dict()})
                else:
                    session.delete(comm)
                    session.commit()
                    return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Error handling communication {comm_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # JSON fallback for local dev
    comms = load_json_file('communications.json', [])
    idx = next((i for i, c in enumerate(comms) if c['id'] == comm_id), None)
    
    if idx is None:
        return jsonify({'success': False, 'error': 'Communication not found'}), 404
    
    if request.method == 'PUT':
        data = request.json
        comm = comms[idx]
        for field in ['subject', 'content', 'type', 'status']:
            if field in data:
                comm[field] = data[field]
        comm['updated_at'] = datetime.now().isoformat()
        comms[idx] = comm
        save_json_file('communications.json', comms)
        return jsonify({'success': True, 'communication': comm})
    else:
        comms.pop(idx)
        save_json_file('communications.json', comms)
        return jsonify({'success': True})


# ============================================================================
# CALENDAR
# ============================================================================

@crm_resources_bp.route('/api/crm/calendar', methods=['GET', 'POST'])
def handle_calendar():
    """Manage calendar events"""
    db_layer = get_db_layer()
    
    # Use database if available
    if db_layer:
        if request.method == 'GET':
            start_date = request.args.get('start')
            end_date = request.args.get('end')
            result = db_layer.get_calendar_events(start_date=start_date, end_date=end_date)
            return jsonify(result)
        else:
            data = request.json
            result = db_layer.create_calendar_event(data)
            return jsonify(result)
    
    # JSON fallback for local dev
    if request.method == 'GET':
        events = load_json_file('calendar.json', [])
        return jsonify({'success': True, 'events': events})
    else:
        data = request.json
        events = load_json_file('calendar.json', [])
        event = {
            'id': str(uuid.uuid4()),
            'title': data.get('title', ''),
            'description': data.get('description', ''),
            'start_time': data.get('start_time', data.get('start_date', '')),
            'end_time': data.get('end_time', data.get('end_date', '')),
            'all_day': data.get('all_day', False),
            'location': data.get('location', ''),
            'event_type': data.get('event_type', data.get('type', 'event')),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        events.append(event)
        save_json_file('calendar.json', events)
        return jsonify({'success': True, 'event': event})


@crm_resources_bp.route('/api/crm/calendar/<event_id>', methods=['PUT', 'DELETE'])
def handle_calendar_event(event_id):
    """Manage a specific calendar event"""
    db_layer = get_db_layer()
    
    # Use database if available
    if db_layer:
        if request.method == 'PUT':
            data = request.json
            result = db_layer.update_calendar_event(event_id, data)
            if not result.get('success'):
                return jsonify(result), 404
            return jsonify(result)
        else:
            result = db_layer.delete_calendar_event(event_id)
            if not result.get('success'):
                return jsonify(result), 404
            return jsonify(result)
    
    # JSON fallback for local dev
    events = load_json_file('calendar.json', [])
    idx = next((i for i, e in enumerate(events) if e['id'] == event_id), None)
    
    if idx is None:
        return jsonify({'success': False, 'error': 'Event not found'}), 404
    
    if request.method == 'PUT':
        data = request.json
        event = events[idx]
        for field in ['title', 'description', 'start_time', 'end_time', 'all_day', 'location', 'event_type']:
            if field in data:
                event[field] = data[field]
        event['updated_at'] = datetime.now().isoformat()
        events[idx] = event
        save_json_file('calendar.json', events)
        return jsonify({'success': True, 'event': event})
    else:
        events.pop(idx)
        save_json_file('calendar.json', events)
        return jsonify({'success': True})


@crm_resources_bp.route('/api/crm/calendar/events', methods=['GET', 'POST'])
def handle_calendar_events():
    """Manage calendar events (alternate endpoint)"""
    return handle_calendar()


@crm_resources_bp.route('/api/crm/calendar/events/<event_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_calendar_event_by_id(event_id):
    """Manage a specific calendar event"""
    db_layer = get_db_layer()
    
    if request.method == 'GET':
        # Use database if available
        if db_layer:
            get_db_session, org_id, CRMRepository, _ = get_db_session_and_repos()
            try:
                with get_db_session() as session:
                    repo = CRMRepository(session, org_id)
                    event = repo.get_calendar_event(event_id)
                    if not event:
                        return jsonify({'success': False, 'error': 'Event not found'}), 404
                    return jsonify({'success': True, 'event': event})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        # JSON fallback
        events = load_json_file('calendar.json', [])
        event = next((e for e in events if e['id'] == event_id), None)
        if not event:
            return jsonify({'success': False, 'error': 'Event not found'}), 404
        return jsonify({'success': True, 'event': event})
    
    # PUT and DELETE use the existing handler
    return handle_calendar_event(event_id)


# ============================================================================
# TECHNICIANS
# ============================================================================

@crm_resources_bp.route('/api/crm/technicians', methods=['GET', 'POST'])
def handle_technicians():
    """Manage technicians"""
    db_layer = get_db_layer()
    
    # Use database if available
    if db_layer:
        if request.method == 'GET':
            result = db_layer.get_technicians(active_only=True)
            return jsonify(result)
        else:
            data = request.json
            if 'specialization' in data and 'specialties' not in data:
                data['specialties'] = [data['specialization']] if data['specialization'] else []
            result = db_layer.create_technician(data)
            return jsonify(result)
    
    # JSON fallback for local dev
    if request.method == 'GET':
        techs = load_json_file('technicians.json', [])
        return jsonify({'success': True, 'technicians': techs})
    else:
        data = request.json
        techs = load_json_file('technicians.json', [])
        tech = {
            'id': str(uuid.uuid4()),
            'name': data.get('name', ''),
            'email': data.get('email', ''),
            'phone': data.get('phone', ''),
            'specialization': data.get('specialization', ''),
            'specialties': [data.get('specialization')] if data.get('specialization') else [],
            'user_id': data.get('user_id'),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        techs.append(tech)
        save_json_file('technicians.json', techs)
        return jsonify({'success': True, 'technician': tech})


@crm_resources_bp.route('/api/crm/technicians/<tech_id>', methods=['PUT', 'DELETE'])
def handle_technician(tech_id):
    """Manage a specific technician"""
    db_layer = get_db_layer()
    
    # Use database if available
    if db_layer:
        if request.method == 'PUT':
            data = request.json
            if 'specialization' in data and 'specialties' not in data:
                data['specialties'] = [data['specialization']] if data['specialization'] else []
            result = db_layer.update_technician(tech_id, data)
            if not result.get('success'):
                return jsonify(result), 404
            return jsonify(result)
        else:
            result = db_layer.delete_technician(tech_id)
            if not result.get('success'):
                return jsonify(result), 404
            return jsonify(result)
    
    # JSON fallback for local dev
    techs = load_json_file('technicians.json', [])
    idx = next((i for i, t in enumerate(techs) if t['id'] == tech_id), None)
    
    if idx is None:
        return jsonify({'success': False, 'error': 'Technician not found'}), 404
    
    if request.method == 'PUT':
        data = request.json
        tech = techs[idx]
        for field in ['name', 'email', 'phone', 'specialization', 'user_id']:
            if field in data:
                tech[field] = data[field]
        tech['updated_at'] = datetime.now().isoformat()
        techs[idx] = tech
        save_json_file('technicians.json', techs)
        return jsonify({'success': True, 'technician': tech})
    else:
        techs.pop(idx)
        save_json_file('technicians.json', techs)
        return jsonify({'success': True})


# ============================================================================
# INVENTORY
# ============================================================================

@crm_resources_bp.route('/api/crm/inventory', methods=['GET', 'POST'])
def handle_inventory():
    """Manage inventory items"""
    db_layer = get_db_layer()
    
    # Use database if available
    if db_layer:
        if request.method == 'GET':
            category = request.args.get('category')
            low_stock = request.args.get('low_stock', '').lower() == 'true'
            result = db_layer.get_stock(category=category, low_stock=low_stock)
            return jsonify({
                'success': True,
                'items': result.get('items', result.get('stock', []))
            })
        else:
            data = request.json
            result = db_layer.create_stock_item(data)
            return jsonify(result)
    
    # JSON fallback for local dev
    if request.method == 'GET':
        items = load_json_file('inventory.json', [])
        return jsonify({'success': True, 'items': items})
    else:
        data = request.json
        items = load_json_file('inventory.json', [])
        item = {
            'id': str(uuid.uuid4()),
            'name': data.get('name', ''),
            'sku': data.get('sku', ''),
            'category': data.get('category', ''),
            'quantity': data.get('quantity', 0),
            'unit_price': data.get('unit_price', 0),
            'supplier_id': data.get('supplier_id'),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        items.append(item)
        save_json_file('inventory.json', items)
        return jsonify({'success': True, 'item': item})


@crm_resources_bp.route('/api/crm/inventory/<item_id>', methods=['PUT', 'DELETE'])
def handle_inventory_item(item_id):
    """Manage a specific inventory item"""
    db_layer = get_db_layer()
    
    # Use database if available
    if db_layer:
        if request.method == 'PUT':
            data = request.json
            result = db_layer.update_stock_item(item_id, data)
            if not result.get('success'):
                return jsonify(result), 404
            return jsonify(result)
        else:
            result = db_layer.delete_stock_item(item_id)
            if not result.get('success'):
                return jsonify(result), 404
            return jsonify(result)
    
    # JSON fallback for local dev
    items = load_json_file('inventory.json', [])
    idx = next((i for i, it in enumerate(items) if it['id'] == item_id), None)
    
    if idx is None:
        return jsonify({'success': False, 'error': 'Inventory item not found'}), 404
    
    if request.method == 'PUT':
        data = request.json
        item = items[idx]
        for field in ['name', 'sku', 'category', 'quantity', 'unit_price', 'supplier_id']:
            if field in data:
                item[field] = data[field]
        item['updated_at'] = datetime.now().isoformat()
        items[idx] = item
        save_json_file('inventory.json', items)
        return jsonify({'success': True, 'item': item})
    else:
        items.pop(idx)
        save_json_file('inventory.json', items)
        return jsonify({'success': True})


@crm_resources_bp.route('/api/crm/inventory/search', methods=['GET'])
def search_inventory():
    """Search inventory items"""
    db_layer = get_db_layer()
    
    # Use database if available
    if db_layer:
        query = request.args.get('q', '')
        result = db_layer.get_stock(search=query)
        return jsonify({
            'success': True,
            'items': result.get('items', result.get('stock', []))
        })
    
    # JSON fallback for local dev
    query = request.args.get('q', '').lower()
    items = load_json_file('inventory.json', [])
    if query:
        items = [i for i in items if query in i.get('name', '').lower() or query in i.get('sku', '').lower()]
    return jsonify({'success': True, 'items': items})


# ============================================================================
# PRICE CLASSES
# ============================================================================

@crm_resources_bp.route('/api/crm/price-classes', methods=['GET', 'POST'])
def handle_price_classes():
    """Manage price classes"""
    db_layer = get_db_layer()
    
    # Use database if available
    if db_layer:
        if request.method == 'GET':
            result = db_layer.get_price_classes(active_only=True)
            return jsonify(result)
        else:
            data = request.json
            result = db_layer.create_price_class(data)
            return jsonify(result)
    
    # JSON fallback for local dev
    if request.method == 'GET':
        classes = load_json_file('price_classes.json', [])
        return jsonify({'success': True, 'price_classes': classes})
    else:
        data = request.json
        classes = load_json_file('price_classes.json', [])
        pc = {
            'id': str(uuid.uuid4()),
            'name': data.get('name', ''),
            'description': data.get('description', ''),
            'markup_percentage': data.get('markup_percentage', 0),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        classes.append(pc)
        save_json_file('price_classes.json', classes)
        return jsonify({'success': True, 'price_class': pc})


@crm_resources_bp.route('/api/crm/price-classes/<class_id>', methods=['PUT', 'DELETE'])
def handle_price_class(class_id):
    """Manage a specific price class"""
    db_layer = get_db_layer()
    
    # Use database if available
    if db_layer:
        if request.method == 'PUT':
            data = request.json
            result = db_layer.update_price_class(class_id, data)
            if not result.get('success'):
                return jsonify(result), 404
            return jsonify(result)
        else:
            result = db_layer.delete_price_class(class_id)
            if not result.get('success'):
                return jsonify(result), 404
            return jsonify(result)
    
    # JSON fallback for local dev
    classes = load_json_file('price_classes.json', [])
    idx = next((i for i, c in enumerate(classes) if c['id'] == class_id), None)
    
    if idx is None:
        return jsonify({'success': False, 'error': 'Price class not found'}), 404
    
    if request.method == 'PUT':
        data = request.json
        pc = classes[idx]
        for field in ['name', 'description', 'markup_percentage']:
            if field in data:
                pc[field] = data[field]
        pc['updated_at'] = datetime.now().isoformat()
        classes[idx] = pc
        save_json_file('price_classes.json', classes)
        return jsonify({'success': True, 'price_class': pc})
    else:
        classes.pop(idx)
        save_json_file('price_classes.json', classes)
        return jsonify({'success': True})


# ============================================================================
# SUPPLIERS
# ============================================================================

@crm_resources_bp.route('/api/crm/suppliers', methods=['GET', 'POST'])
def handle_suppliers():
    """Manage suppliers"""
    db_layer = get_db_layer()
    
    # Use database if available
    if db_layer:
        if request.method == 'GET':
            result = db_layer.get_suppliers(active_only=True)
            return jsonify(result)
        else:
            data = request.json
            if 'contact_person' in data:
                data['notes'] = f"Contact: {data['contact_person']}"
            result = db_layer.create_supplier(data)
            return jsonify(result)
    
    # JSON fallback for local dev
    if request.method == 'GET':
        suppliers = load_json_file('suppliers.json', [])
        return jsonify({'success': True, 'suppliers': suppliers})
    else:
        data = request.json
        suppliers = load_json_file('suppliers.json', [])
        supplier = {
            'id': str(uuid.uuid4()),
            'name': data.get('name', ''),
            'email': data.get('email', ''),
            'phone': data.get('phone', ''),
            'address': data.get('address', ''),
            'contact_person': data.get('contact_person', ''),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        suppliers.append(supplier)
        save_json_file('suppliers.json', suppliers)
        return jsonify({'success': True, 'supplier': supplier})


@crm_resources_bp.route('/api/crm/suppliers/<supplier_id>', methods=['PUT', 'DELETE'])
def handle_supplier(supplier_id):
    """Manage a specific supplier"""
    db_layer = get_db_layer()
    
    # Use database if available
    if db_layer:
        if request.method == 'PUT':
            data = request.json
            if 'contact_person' in data:
                data['notes'] = f"Contact: {data['contact_person']}"
            result = db_layer.update_supplier(supplier_id, data)
            if not result.get('success'):
                return jsonify(result), 404
            return jsonify(result)
        else:
            result = db_layer.delete_supplier(supplier_id)
            if not result.get('success'):
                return jsonify(result), 404
            return jsonify(result)
    
    # JSON fallback for local dev
    suppliers = load_json_file('suppliers.json', [])
    idx = next((i for i, s in enumerate(suppliers) if s['id'] == supplier_id), None)
    
    if idx is None:
        return jsonify({'success': False, 'error': 'Supplier not found'}), 404
    
    if request.method == 'PUT':
        data = request.json
        supplier = suppliers[idx]
        for field in ['name', 'email', 'phone', 'address', 'contact_person']:
            if field in data:
                supplier[field] = data[field]
        supplier['updated_at'] = datetime.now().isoformat()
        suppliers[idx] = supplier
        save_json_file('suppliers.json', suppliers)
        return jsonify({'success': True, 'supplier': supplier})
    else:
        suppliers.pop(idx)
        save_json_file('suppliers.json', suppliers)
        return jsonify({'success': True})


# ============================================================================
# PEOPLE
# ============================================================================

@crm_resources_bp.route('/api/crm/people', methods=['GET', 'POST'])
def handle_people():
    """Manage people"""
    import crm_extended
    
    if request.method == 'GET':
        people = crm_extended.load_people()
        return jsonify({'success': True, 'people': people})
    else:
        data = request.json
        person, error = crm_extended.create_person(data)
        if error:
            return jsonify({'success': False, 'error': error}), 400
        return jsonify({'success': True, 'person': person})


@crm_resources_bp.route('/api/crm/people/<person_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_person(person_id):
    """Manage a specific person"""
    import crm_extended
    
    if request.method == 'GET':
        person = crm_extended.get_person(person_id)
        if not person:
            return jsonify({'success': False, 'error': 'Person not found'}), 404
        return jsonify({'success': True, 'person': person})
    elif request.method == 'PUT':
        data = request.json
        person, error = crm_extended.update_person(person_id, data)
        if error:
            return jsonify({'success': False, 'error': error}), 400
        return jsonify({'success': True, 'person': person})
    else:
        success, error = crm_extended.delete_person(person_id)
        if error:
            return jsonify({'success': False, 'error': error}), 400
        return jsonify({'success': True})


# ============================================================================
# JOBS
# ============================================================================

@crm_resources_bp.route('/api/crm/jobs', methods=['GET', 'POST'])
def handle_jobs():
    """Manage jobs"""
    import crm_extended
    
    if request.method == 'GET':
        jobs = crm_extended.load_jobs()
        return jsonify({'success': True, 'jobs': jobs})
    else:
        data = request.json
        job, error = crm_extended.create_job(data)
        if error:
            return jsonify({'success': False, 'error': error}), 400
        return jsonify({'success': True, 'job': job})


@crm_resources_bp.route('/api/crm/jobs/<job_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_job(job_id):
    """Manage a specific job"""
    import crm_extended
    
    if request.method == 'GET':
        job = crm_extended.get_job(job_id)
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
        return jsonify({'success': True, 'job': job})
    elif request.method == 'PUT':
        data = request.json
        job, error = crm_extended.update_job(job_id, data)
        if error:
            return jsonify({'success': False, 'error': error}), 400
        return jsonify({'success': True, 'job': job})
    else:
        success, error = crm_extended.delete_job(job_id)
        if error:
            return jsonify({'success': False, 'error': error}), 400
        return jsonify({'success': True})


# ============================================================================
# MATERIALS
# ============================================================================

@crm_resources_bp.route('/api/crm/materials', methods=['GET', 'POST'])
def handle_materials():
    """Manage materials"""
    import crm_extended
    
    if request.method == 'GET':
        materials = crm_extended.load_materials()
        return jsonify({'success': True, 'materials': materials})
    else:
        data = request.json
        material, error = crm_extended.create_material(data)
        if error:
            return jsonify({'success': False, 'error': error}), 400
        return jsonify({'success': True, 'material': material})


@crm_resources_bp.route('/api/crm/materials/<material_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_material(material_id):
    """Manage a specific material"""
    import crm_extended
    
    if request.method == 'GET':
        material = crm_extended.get_material(material_id)
        if not material:
            return jsonify({'success': False, 'error': 'Material not found'}), 404
        return jsonify({'success': True, 'material': material})
    elif request.method == 'PUT':
        data = request.json
        material, error = crm_extended.update_material(material_id, data)
        if error:
            return jsonify({'success': False, 'error': error}), 400
        return jsonify({'success': True, 'material': material})
    else:
        success, error = crm_extended.delete_material(material_id)
        if error:
            return jsonify({'success': False, 'error': error}), 400
        return jsonify({'success': True})


# ============================================================================
# PAYMENTS
# ============================================================================

@crm_resources_bp.route('/api/crm/payments', methods=['GET', 'POST'])
def handle_payments():
    """Manage payments"""
    import crm_extended
    
    if request.method == 'GET':
        payments = crm_extended.load_payments()
        return jsonify({'success': True, 'payments': payments})
    else:
        data = request.json
        payment, error = crm_extended.create_payment(data)
        if error:
            return jsonify({'success': False, 'error': error}), 400
        return jsonify({'success': True, 'payment': payment})


@crm_resources_bp.route('/api/crm/payments/<payment_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_payment(payment_id):
    """Manage a specific payment"""
    import crm_extended
    
    if request.method == 'GET':
        payment = crm_extended.get_payment(payment_id)
        if not payment:
            return jsonify({'success': False, 'error': 'Payment not found'}), 404
        return jsonify({'success': True, 'payment': payment})
    elif request.method == 'PUT':
        data = request.json
        payment, error = crm_extended.update_payment(payment_id, data)
        if error:
            return jsonify({'success': False, 'error': error}), 400
        return jsonify({'success': True, 'payment': payment})
    else:
        success, error = crm_extended.delete_payment(payment_id)
        if error:
            return jsonify({'success': False, 'error': error}), 400
        return jsonify({'success': True})


@crm_resources_bp.route('/api/crm/payments/<payment_id>/generate-invoice', methods=['POST'])
def generate_payment_invoice(payment_id):
    """Generate invoice for a payment"""
    import crm_extended
    
    result, error = crm_extended.generate_invoice(payment_id)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    return jsonify({'success': True, 'invoice': result})


# ============================================================================
# INTEGRATIONS STATUS
# ============================================================================

@crm_resources_bp.route('/api/crm/integrations', methods=['GET'])
def get_integrations_status():
    """Get available integrations status"""
    db_available = is_db_available()
    return jsonify({
        'success': True,
        'integrations': {
            'google': {'enabled': False, 'connected': False},
            'simpro': {'enabled': True, 'connected': False},
            'database': {'enabled': True, 'connected': db_available}
        }
    })
