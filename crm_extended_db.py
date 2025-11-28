"""
CRM Extended Database Module
Drop-in replacement for crm_extended.py that uses PostgreSQL.
Handles People, Jobs, Materials, Payments, and Schedules.
"""
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Check if database is available
try:
    from database.connection import get_db_session, is_db_configured
    from database.seed import get_default_organization_id
    from services.crm_repository import CRMRepository
    from services.inventory_repository import InventoryRepository
    DB_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Database modules not available: {e}")
    DB_AVAILABLE = False

# Get organization ID
_org_id = None


def _get_org_id():
    global _org_id
    if _org_id is None and DB_AVAILABLE and is_db_configured():
        _org_id = get_default_organization_id()
    return _org_id


# ====================================================================================
# PEOPLE MODULE
# ====================================================================================

PEOPLE_TYPES = {
    'employee': 'Employees',
    'customer': 'Customers',
    'supplier': 'Suppliers',
    'contractor': 'Contractors',
    'contact': 'Contacts'
}


def load_people(person_type=None) -> List[Dict]:
    """Load people from database."""
    if not DB_AVAILABLE or not is_db_configured():
        return []
    
    try:
        with get_db_session() as session:
            repo = CRMRepository(session, _get_org_id())
            
            # Get customers and suppliers based on type
            people = []
            
            if person_type in [None, 'customer']:
                customers = repo.list_customers()
                for c in customers:
                    people.append({
                        'id': c['id'],
                        'type': 'customer',
                        'name': c.get('name', ''),
                        'company': c.get('company', ''),
                        'email': c.get('email', ''),
                        'phone': c.get('phone', ''),
                        'address': c.get('address', ''),
                        'notes': c.get('notes', ''),
                        'linked_jobs': [],
                        'linked_quotes': [],
                        'created_at': c.get('created_at'),
                        'updated_at': c.get('updated_at')
                    })
            
            if person_type in [None, 'supplier']:
                suppliers = repo.list_suppliers()
                for s in suppliers:
                    people.append({
                        'id': s['id'],
                        'type': 'supplier',
                        'name': s.get('name', ''),
                        'company': s.get('company', ''),
                        'email': s.get('email', ''),
                        'phone': s.get('phone', ''),
                        'address': s.get('address', ''),
                        'notes': s.get('notes', ''),
                        'linked_jobs': [],
                        'linked_quotes': [],
                        'created_at': s.get('created_at'),
                        'updated_at': s.get('updated_at')
                    })
            
            if person_type in [None, 'employee', 'contractor', 'contact']:
                technicians = repo.list_technicians()
                for t in technicians:
                    people.append({
                        'id': t['id'],
                        'type': 'employee',
                        'name': t.get('name', ''),
                        'company': '',
                        'email': t.get('email', ''),
                        'phone': t.get('phone', ''),
                        'address': '',
                        'notes': t.get('notes', ''),
                        'linked_jobs': [],
                        'linked_quotes': [],
                        'created_at': t.get('created_at'),
                        'updated_at': t.get('updated_at')
                    })
            
            return people
    except Exception as e:
        logger.error(f"Error loading people: {e}")
        return []


def create_person(data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Create a new person."""
    if not DB_AVAILABLE or not is_db_configured():
        return None, "Database not configured"
    
    try:
        with get_db_session() as session:
            repo = CRMRepository(session, _get_org_id())
            person_type = data.get('type', 'contact')
            
            if person_type == 'customer':
                result = repo.create_customer(data)
            elif person_type == 'supplier':
                result = repo.create_supplier(data)
            else:
                # Treat as technician/employee
                result = repo.create_technician(data)
            
            session.commit()
            
            person = {
                'id': result['id'],
                'type': person_type,
                'name': result.get('name', ''),
                'company': result.get('company', ''),
                'email': result.get('email', ''),
                'phone': result.get('phone', ''),
                'address': result.get('address', ''),
                'notes': result.get('notes', ''),
                'linked_jobs': [],
                'linked_quotes': [],
                'created_at': result.get('created_at'),
                'updated_at': result.get('updated_at')
            }
            return person, None
    except Exception as e:
        logger.error(f"Error creating person: {e}")
        return None, str(e)


def update_person(person_id: str, data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Update a person."""
    if not DB_AVAILABLE or not is_db_configured():
        return None, "Database not configured"
    
    try:
        with get_db_session() as session:
            repo = CRMRepository(session, _get_org_id())
            
            # Try to update as customer first
            result = repo.update_customer(person_id, data)
            if not result:
                result = repo.update_supplier(person_id, data)
            if not result:
                result = repo.update_technician(person_id, data)
            
            if result:
                session.commit()
                return result, None
            return None, "Person not found"
    except Exception as e:
        logger.error(f"Error updating person: {e}")
        return None, str(e)


def delete_person(person_id: str) -> Tuple[bool, Optional[str]]:
    """Delete a person."""
    if not DB_AVAILABLE or not is_db_configured():
        return False, "Database not configured"
    
    try:
        with get_db_session() as session:
            repo = CRMRepository(session, _get_org_id())
            
            # Try to delete from each type
            if repo.delete_customer(person_id):
                session.commit()
                return True, None
            if repo.delete_supplier(person_id):
                session.commit()
                return True, None
            if repo.delete_technician(person_id):
                session.commit()
                return True, None
            
            return False, "Person not found"
    except Exception as e:
        logger.error(f"Error deleting person: {e}")
        return False, str(e)


# ====================================================================================
# JOBS MODULE
# ====================================================================================

def load_jobs(status=None) -> List[Dict]:
    """Load jobs from database."""
    if not DB_AVAILABLE or not is_db_configured():
        return []
    
    try:
        with get_db_session() as session:
            repo = CRMRepository(session, _get_org_id())
            jobs = repo.list_jobs(status=status)
            return jobs
    except Exception as e:
        logger.error(f"Error loading jobs: {e}")
        return []


def create_job(data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Create a new job."""
    if not DB_AVAILABLE or not is_db_configured():
        return None, "Database not configured"
    
    try:
        with get_db_session() as session:
            repo = CRMRepository(session, _get_org_id())
            job = repo.create_job(data)
            session.commit()
            return job, None
    except Exception as e:
        logger.error(f"Error creating job: {e}")
        return None, str(e)


def update_job(job_id: str, data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Update a job."""
    if not DB_AVAILABLE or not is_db_configured():
        return None, "Database not configured"
    
    try:
        with get_db_session() as session:
            repo = CRMRepository(session, _get_org_id())
            job = repo.update_job(job_id, data)
            if job:
                session.commit()
                return job, None
            return None, "Job not found"
    except Exception as e:
        logger.error(f"Error updating job: {e}")
        return None, str(e)


def delete_job(job_id: str) -> Tuple[bool, Optional[str]]:
    """Delete a job."""
    if not DB_AVAILABLE or not is_db_configured():
        return False, "Database not configured"
    
    try:
        with get_db_session() as session:
            repo = CRMRepository(session, _get_org_id())
            if repo.delete_job(job_id):
                session.commit()
                return True, None
            return False, "Job not found"
    except Exception as e:
        logger.error(f"Error deleting job: {e}")
        return False, str(e)


# ====================================================================================
# MATERIALS MODULE (maps to inventory)
# ====================================================================================

def load_materials(mat_type=None, location=None) -> List[Dict]:
    """Load materials from database."""
    if not DB_AVAILABLE or not is_db_configured():
        return []
    
    try:
        with get_db_session() as session:
            repo = InventoryRepository(session, _get_org_id())
            items = repo.list_items(category=mat_type)
            
            # Filter by location if specified
            if location:
                items = [i for i in items if i.get('location') == location]
            
            # Map to materials format
            materials = []
            for item in items:
                materials.append({
                    'id': item['id'],
                    'type': mat_type or 'stock',
                    'name': item.get('name', ''),
                    'sku': item.get('sku', ''),
                    'category': item.get('category', ''),
                    'quantity': item.get('quantity', 0),
                    'unit_price': item.get('unit_price', 0),
                    'location': item.get('location', ''),
                    'description': item.get('description', ''),
                    'created_at': item.get('created_at'),
                    'updated_at': item.get('updated_at')
                })
            return materials
    except Exception as e:
        logger.error(f"Error loading materials: {e}")
        return []


def create_material(data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Create a new material."""
    if not DB_AVAILABLE or not is_db_configured():
        return None, "Database not configured"
    
    try:
        with get_db_session() as session:
            repo = InventoryRepository(session, _get_org_id())
            item = repo.create_item(data)
            session.commit()
            return item, None
    except Exception as e:
        logger.error(f"Error creating material: {e}")
        return None, str(e)


def update_material(material_id: str, data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Update a material."""
    if not DB_AVAILABLE or not is_db_configured():
        return None, "Database not configured"
    
    try:
        with get_db_session() as session:
            repo = InventoryRepository(session, _get_org_id())
            item = repo.update_item(material_id, data)
            if item:
                session.commit()
                return item, None
            return None, "Material not found"
    except Exception as e:
        logger.error(f"Error updating material: {e}")
        return None, str(e)


def delete_material(material_id: str) -> Tuple[bool, Optional[str]]:
    """Delete a material."""
    if not DB_AVAILABLE or not is_db_configured():
        return False, "Database not configured"
    
    try:
        with get_db_session() as session:
            repo = InventoryRepository(session, _get_org_id())
            if repo.delete_item(material_id):
                session.commit()
                return True, None
            return False, "Material not found"
    except Exception as e:
        logger.error(f"Error deleting material: {e}")
        return False, str(e)


# ====================================================================================
# PAYMENTS MODULE (stub - can be extended)
# ====================================================================================

def load_payments(direction=None) -> List[Dict]:
    """Load payments - stub for now."""
    return []


def create_payment(data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Create a payment - stub for now."""
    return None, "Payments not yet implemented in database"


def update_payment(payment_id: str, data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Update a payment - stub for now."""
    return None, "Payments not yet implemented in database"


def delete_payment(payment_id: str) -> Tuple[bool, Optional[str]]:
    """Delete a payment - stub for now."""
    return False, "Payments not yet implemented in database"


# ====================================================================================
# CALENDAR MODULE
# ====================================================================================

def load_calendar_events(start_date=None, end_date=None) -> List[Dict]:
    """Load calendar events from database."""
    if not DB_AVAILABLE or not is_db_configured():
        return []
    
    try:
        with get_db_session() as session:
            repo = CRMRepository(session, _get_org_id())
            events = repo.list_calendar_events(start_date=start_date, end_date=end_date)
            return events
    except Exception as e:
        logger.error(f"Error loading calendar events: {e}")
        return []


def create_calendar_event(data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Create a calendar event."""
    if not DB_AVAILABLE or not is_db_configured():
        return None, "Database not configured"
    
    try:
        with get_db_session() as session:
            repo = CRMRepository(session, _get_org_id())
            event = repo.create_calendar_event(data)
            session.commit()
            return event, None
    except Exception as e:
        logger.error(f"Error creating calendar event: {e}")
        return None, str(e)


def update_calendar_event(event_id: str, data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Update a calendar event."""
    if not DB_AVAILABLE or not is_db_configured():
        return None, "Database not configured"
    
    try:
        with get_db_session() as session:
            repo = CRMRepository(session, _get_org_id())
            event = repo.update_calendar_event(event_id, data)
            if event:
                session.commit()
                return event, None
            return None, "Event not found"
    except Exception as e:
        logger.error(f"Error updating calendar event: {e}")
        return None, str(e)


def delete_calendar_event(event_id: str) -> Tuple[bool, Optional[str]]:
    """Delete a calendar event."""
    if not DB_AVAILABLE or not is_db_configured():
        return False, "Database not configured"
    
    try:
        with get_db_session() as session:
            repo = CRMRepository(session, _get_org_id())
            if repo.delete_calendar_event(event_id):
                session.commit()
                return True, None
            return False, "Event not found"
    except Exception as e:
        logger.error(f"Error deleting calendar event: {e}")
        return False, str(e)

