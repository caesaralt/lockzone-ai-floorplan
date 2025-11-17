"""
CRM Data Integration Module
============================

This module provides comprehensive data linking and integration for the CRM system.
It ensures all CRM entities are properly connected and can communicate with each other.

Entities:
- Customers
- Projects (linked to customers)
- Communications (linked to customers/projects)
- Calendar Events (linked to projects/customers)
- Technicians (linked to users)
- Inventory (linked to suppliers, projects)
- Suppliers
- Jobs (linked to projects, technicians)

Author: Claude AI Assistant
Date: November 2025
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any

# File paths (imported from app.py config)
CRM_DATA_FOLDER = 'crm_data'
CUSTOMERS_FILE = os.path.join(CRM_DATA_FOLDER, 'customers.json')
PROJECTS_FILE = os.path.join(CRM_DATA_FOLDER, 'projects.json')
COMMUNICATIONS_FILE = os.path.join(CRM_DATA_FOLDER, 'communications.json')
CALENDAR_FILE = os.path.join(CRM_DATA_FOLDER, 'calendar.json')
TECHNICIANS_FILE = os.path.join(CRM_DATA_FOLDER, 'technicians.json')
INVENTORY_FILE = os.path.join(CRM_DATA_FOLDER, 'inventory.json')
SUPPLIERS_FILE = os.path.join(CRM_DATA_FOLDER, 'suppliers.json')
JOBS_FILE = os.path.join(CRM_DATA_FOLDER, 'jobs.json')


def ensure_crm_folders():
    """Ensure CRM data folder and files exist"""
    if not os.path.exists(CRM_DATA_FOLDER):
        os.makedirs(CRM_DATA_FOLDER)
        print(f"✅ Created CRM data folder: {CRM_DATA_FOLDER}")


def load_json_file(filepath: str, default: Any = None) -> Any:
    """Load JSON file with error handling"""
    if default is None:
        default = []

    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return default
    except Exception as e:
        print(f"❌ Error loading {filepath}: {str(e)}")
        return default


def save_json_file(filepath: str, data: Any) -> bool:
    """Save JSON file with error handling"""
    try:
        ensure_crm_folders()
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"❌ Error saving {filepath}: {str(e)}")
        return False


# ============================================================================
# ENTITY LINKING FUNCTIONS
# ============================================================================

def link_technician_to_user(tech_id: str, user_id: str) -> bool:
    """Link a technician record to a user account"""
    technicians = load_json_file(TECHNICIANS_FILE, [])

    for tech in technicians:
        if tech.get('id') == tech_id:
            tech['user_id'] = user_id
            tech['updated_at'] = datetime.now().isoformat()
            save_json_file(TECHNICIANS_FILE, technicians)
            return True

    return False


def link_project_to_customer(project_id: str, customer_id: str) -> bool:
    """Link a project to a customer"""
    projects = load_json_file(PROJECTS_FILE, [])

    for project in projects:
        if project.get('id') == project_id:
            project['customer_id'] = customer_id
            project['updated_at'] = datetime.now().isoformat()
            save_json_file(PROJECTS_FILE, projects)
            return True

    return False


def link_communication_to_entities(comm_id: str, customer_id: Optional[str] = None,
                                   project_id: Optional[str] = None) -> bool:
    """Link a communication to customer and/or project"""
    comms = load_json_file(COMMUNICATIONS_FILE, [])

    for comm in comms:
        if comm.get('id') == comm_id:
            if customer_id:
                comm['customer_id'] = customer_id
            if project_id:
                comm['project_id'] = project_id
            comm['updated_at'] = datetime.now().isoformat()
            save_json_file(COMMUNICATIONS_FILE, comms)
            return True

    return False


def link_event_to_entities(event_id: str, project_id: Optional[str] = None,
                           technician_id: Optional[str] = None) -> bool:
    """Link a calendar event to project and/or technician"""
    events = load_json_file(CALENDAR_FILE, [])

    for event in events:
        if event.get('id') == event_id:
            if project_id:
                event['project_id'] = project_id
            if technician_id:
                event['assigned_to'] = technician_id
            event['updated_at'] = datetime.now().isoformat()
            save_json_file(CALENDAR_FILE, events)
            return True

    return False


def link_inventory_to_supplier(item_id: str, supplier_id: str) -> bool:
    """Link an inventory item to a supplier"""
    inventory = load_json_file(INVENTORY_FILE, [])

    for item in inventory:
        if item.get('id') == item_id:
            item['supplier_id'] = supplier_id
            item['updated_at'] = datetime.now().isoformat()
            save_json_file(INVENTORY_FILE, inventory)
            return True

    return False


# ============================================================================
# RELATIONSHIP QUERIES
# ============================================================================

def get_customer_projects(customer_id: str) -> List[Dict]:
    """Get all projects for a customer"""
    projects = load_json_file(PROJECTS_FILE, [])
    return [p for p in projects if p.get('customer_id') == customer_id]


def get_customer_communications(customer_id: str) -> List[Dict]:
    """Get all communications for a customer"""
    comms = load_json_file(COMMUNICATIONS_FILE, [])
    return [c for c in comms if c.get('customer_id') == customer_id]


def get_project_details(project_id: str) -> Optional[Dict]:
    """Get project with all related data"""
    projects = load_json_file(PROJECTS_FILE, [])
    project = next((p for p in projects if p.get('id') == project_id), None)

    if not project:
        return None

    # Enrich with related data
    customer_id = project.get('customer_id')
    if customer_id:
        customers = load_json_file(CUSTOMERS_FILE, [])
        project['customer'] = next((c for c in customers if c.get('id') == customer_id), None)

    # Get communications
    comms = load_json_file(COMMUNICATIONS_FILE, [])
    project['communications'] = [c for c in comms if c.get('project_id') == project_id]

    # Get events
    events = load_json_file(CALENDAR_FILE, [])
    project['events'] = [e for e in events if e.get('project_id') == project_id]

    return project


def get_technician_schedule(tech_id: str) -> List[Dict]:
    """Get all calendar events assigned to a technician"""
    events = load_json_file(CALENDAR_FILE, [])
    tech_events = [e for e in events if e.get('assigned_to') == tech_id]

    # Enrich with project details
    projects = load_json_file(PROJECTS_FILE, [])
    for event in tech_events:
        project_id = event.get('project_id')
        if project_id:
            event['project'] = next((p for p in projects if p.get('id') == project_id), None)

    return tech_events


def get_inventory_by_supplier(supplier_id: str) -> List[Dict]:
    """Get all inventory items from a supplier"""
    inventory = load_json_file(INVENTORY_FILE, [])
    return [item for item in inventory if item.get('supplier_id') == supplier_id]


def get_user_assigned_projects(user_id: str) -> List[Dict]:
    """Get all projects assigned to a user (via technician link)"""
    # Find technician linked to user
    technicians = load_json_file(TECHNICIANS_FILE, [])
    tech = next((t for t in technicians if t.get('user_id') == user_id), None)

    if not tech:
        return []

    # Get events for this technician
    events = load_json_file(CALENDAR_FILE, [])
    tech_events = [e for e in events if e.get('assigned_to') == tech.get('id')]

    # Get unique project IDs
    project_ids = list(set([e.get('project_id') for e in tech_events if e.get('project_id')]))

    # Get project details
    projects = load_json_file(PROJECTS_FILE, [])
    return [p for p in projects if p.get('id') in project_ids]


# ============================================================================
# DATA VALIDATION AND CLEANUP
# ============================================================================

def validate_project_references(project_id: str) -> Dict[str, bool]:
    """Validate all references to a project are correct"""
    validation = {
        'project_exists': False,
        'customer_valid': False,
        'communications_linked': False,
        'events_linked': False
    }

    projects = load_json_file(PROJECTS_FILE, [])
    project = next((p for p in projects if p.get('id') == project_id), None)

    if not project:
        return validation

    validation['project_exists'] = True

    # Validate customer
    customer_id = project.get('customer_id')
    if customer_id:
        customers = load_json_file(CUSTOMERS_FILE, [])
        if any(c.get('id') == customer_id for c in customers):
            validation['customer_valid'] = True

    # Check communications
    comms = load_json_file(COMMUNICATIONS_FILE, [])
    if any(c.get('project_id') == project_id for c in comms):
        validation['communications_linked'] = True

    # Check events
    events = load_json_file(CALENDAR_FILE, [])
    if any(e.get('project_id') == project_id for e in events):
        validation['events_linked'] = True

    return validation


def cleanup_orphaned_references() -> Dict[str, int]:
    """Remove references to deleted entities"""
    cleanup_count = {
        'projects': 0,
        'communications': 0,
        'events': 0,
        'inventory': 0
    }

    # Get valid IDs
    customers = load_json_file(CUSTOMERS_FILE, [])
    customer_ids = [c.get('id') for c in customers]

    projects = load_json_file(PROJECTS_FILE, [])
    project_ids = [p.get('id') for p in projects]

    suppliers = load_json_file(SUPPLIERS_FILE, [])
    supplier_ids = [s.get('id') for s in suppliers]

    technicians = load_json_file(TECHNICIANS_FILE, [])
    tech_ids = [t.get('id') for t in technicians]

    # Clean projects
    modified = False
    for project in projects:
        if project.get('customer_id') and project.get('customer_id') not in customer_ids:
            project['customer_id'] = None
            cleanup_count['projects'] += 1
            modified = True
    if modified:
        save_json_file(PROJECTS_FILE, projects)

    # Clean communications
    comms = load_json_file(COMMUNICATIONS_FILE, [])
    modified = False
    for comm in comms:
        if comm.get('customer_id') and comm.get('customer_id') not in customer_ids:
            comm['customer_id'] = None
            cleanup_count['communications'] += 1
            modified = True
        if comm.get('project_id') and comm.get('project_id') not in project_ids:
            comm['project_id'] = None
            cleanup_count['communications'] += 1
            modified = True
    if modified:
        save_json_file(COMMUNICATIONS_FILE, comms)

    # Clean events
    events = load_json_file(CALENDAR_FILE, [])
    modified = False
    for event in events:
        if event.get('project_id') and event.get('project_id') not in project_ids:
            event['project_id'] = None
            cleanup_count['events'] += 1
            modified = True
        if event.get('assigned_to') and event.get('assigned_to') not in tech_ids:
            event['assigned_to'] = None
            cleanup_count['events'] += 1
            modified = True
    if modified:
        save_json_file(CALENDAR_FILE, events)

    # Clean inventory
    inventory = load_json_file(INVENTORY_FILE, [])
    modified = False
    for item in inventory:
        if item.get('supplier_id') and item.get('supplier_id') not in supplier_ids:
            item['supplier_id'] = None
            cleanup_count['inventory'] += 1
            modified = True
    if modified:
        save_json_file(INVENTORY_FILE, inventory)

    return cleanup_count


# ============================================================================
# DATA EXPORT AND REPORTING
# ============================================================================

def get_complete_crm_snapshot() -> Dict[str, Any]:
    """Get a complete snapshot of all CRM data with relationships"""
    return {
        'customers': load_json_file(CUSTOMERS_FILE, []),
        'projects': load_json_file(PROJECTS_FILE, []),
        'communications': load_json_file(COMMUNICATIONS_FILE, []),
        'calendar': load_json_file(CALENDAR_FILE, []),
        'technicians': load_json_file(TECHNICIANS_FILE, []),
        'inventory': load_json_file(INVENTORY_FILE, []),
        'suppliers': load_json_file(SUPPLIERS_FILE, []),
        'jobs': load_json_file(JOBS_FILE, []),
        'generated_at': datetime.now().isoformat()
    }


def get_crm_health_report() -> Dict[str, Any]:
    """Generate a health report of CRM data integrity"""
    customers = load_json_file(CUSTOMERS_FILE, [])
    projects = load_json_file(PROJECTS_FILE, [])
    comms = load_json_file(COMMUNICATIONS_FILE, [])
    events = load_json_file(CALENDAR_FILE, [])
    technicians = load_json_file(TECHNICIANS_FILE, [])
    inventory = load_json_file(INVENTORY_FILE, [])
    suppliers = load_json_file(SUPPLIERS_FILE, [])

    # Count relationships
    projects_with_customers = sum(1 for p in projects if p.get('customer_id'))
    comms_with_links = sum(1 for c in comms if c.get('customer_id') or c.get('project_id'))
    events_with_links = sum(1 for e in events if e.get('project_id') or e.get('assigned_to'))
    inventory_with_suppliers = sum(1 for i in inventory if i.get('supplier_id'))
    techs_with_users = sum(1 for t in technicians if t.get('user_id'))

    return {
        'totals': {
            'customers': len(customers),
            'projects': len(projects),
            'communications': len(comms),
            'events': len(events),
            'technicians': len(technicians),
            'inventory_items': len(inventory),
            'suppliers': len(suppliers)
        },
        'relationships': {
            'projects_linked_to_customers': projects_with_customers,
            'projects_without_customers': len(projects) - projects_with_customers,
            'communications_with_links': comms_with_links,
            'events_with_links': events_with_links,
            'inventory_with_suppliers': inventory_with_suppliers,
            'technicians_with_users': techs_with_users
        },
        'health_score': {
            'projects': round((projects_with_customers / len(projects) * 100) if projects else 100, 1),
            'communications': round((comms_with_links / len(comms) * 100) if comms else 100, 1),
            'events': round((events_with_links / len(events) * 100) if events else 100, 1),
            'inventory': round((inventory_with_suppliers / len(inventory) * 100) if inventory else 100, 1),
            'technicians': round((techs_with_users / len(technicians) * 100) if technicians else 100, 1)
        },
        'generated_at': datetime.now().isoformat()
    }


# ============================================================================
# INITIALIZATION
# ============================================================================

def initialize_crm_system():
    """Initialize CRM system with folders and default data"""
    ensure_crm_folders()

    # Create empty files if they don't exist
    files = [
        CUSTOMERS_FILE,
        PROJECTS_FILE,
        COMMUNICATIONS_FILE,
        CALENDAR_FILE,
        TECHNICIANS_FILE,
        INVENTORY_FILE,
        SUPPLIERS_FILE,
        JOBS_FILE
    ]

    for filepath in files:
        if not os.path.exists(filepath):
            save_json_file(filepath, [])
            print(f"✅ Initialized: {filepath}")


# Auto-initialize on import
initialize_crm_system()
