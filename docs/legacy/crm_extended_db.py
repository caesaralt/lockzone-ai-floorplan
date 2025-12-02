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
# PAYMENTS MODULE (Database-backed)
# ====================================================================================

def load_payments(direction=None, status=None) -> List[Dict]:
    """Load payments from database."""
    if not DB_AVAILABLE or not is_db_configured():
        return []
    
    try:
        with get_db_session() as session:
            from database.models import Payment
            query = session.query(Payment).filter(Payment.organization_id == _get_org_id())
            
            if direction:
                query = query.filter(Payment.direction == direction)
            if status:
                query = query.filter(Payment.status == status)
            
            payments = query.order_by(Payment.created_at.desc()).all()
            return [p.to_dict() for p in payments]
    except Exception as e:
        logger.error(f"Error loading payments: {e}")
        return []


def create_payment(data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Create a new payment in database."""
    if not DB_AVAILABLE or not is_db_configured():
        return None, "Database not configured"
    
    try:
        with get_db_session() as session:
            from database.models import Payment
            from dateutil import parser as date_parser
            
            # Parse dates if provided as strings
            due_date = None
            paid_date = None
            if data.get('due_date'):
                try:
                    due_date = date_parser.parse(data['due_date']).date() if isinstance(data['due_date'], str) else data['due_date']
                except:
                    pass
            if data.get('paid_date'):
                try:
                    paid_date = date_parser.parse(data['paid_date']).date() if isinstance(data['paid_date'], str) else data['paid_date']
                except:
                    pass
            
            payment = Payment(
                organization_id=_get_org_id(),
                direction=data.get('direction', 'to_us'),
                status=data.get('status', 'pending'),
                amount=float(data.get('amount', 0)),
                due_date=due_date,
                paid_date=paid_date,
                linked_to=data.get('linked_to', {}),
                person_id=data.get('person_id', ''),
                invoice_pdf=data.get('invoice_pdf', ''),
                notes=data.get('notes', ''),
                customer_id=data.get('customer_id'),
                supplier_id=data.get('supplier_id'),
                project_id=data.get('project_id'),
                quote_id=data.get('quote_id'),
                job_id=data.get('job_id'),
            )
            session.add(payment)
            session.commit()
            session.refresh(payment)
            return payment.to_dict(), None
    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        return None, str(e)


def update_payment(payment_id: str, data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Update a payment in database."""
    if not DB_AVAILABLE or not is_db_configured():
        return None, "Database not configured"
    
    try:
        with get_db_session() as session:
            from database.models import Payment
            from dateutil import parser as date_parser
            
            payment = session.query(Payment).filter(
                Payment.id == payment_id,
                Payment.organization_id == _get_org_id()
            ).first()
            
            if not payment:
                return None, "Payment not found"
            
            # Update fields
            if 'status' in data:
                payment.status = data['status']
            if 'amount' in data:
                payment.amount = float(data['amount'])
            if 'due_date' in data:
                try:
                    payment.due_date = date_parser.parse(data['due_date']).date() if isinstance(data['due_date'], str) and data['due_date'] else None
                except:
                    pass
            if 'paid_date' in data:
                try:
                    payment.paid_date = date_parser.parse(data['paid_date']).date() if isinstance(data['paid_date'], str) and data['paid_date'] else None
                except:
                    pass
            if 'notes' in data:
                payment.notes = data['notes']
            if 'invoice_pdf' in data:
                payment.invoice_pdf = data['invoice_pdf']
            
            session.commit()
            session.refresh(payment)
            return payment.to_dict(), None
    except Exception as e:
        logger.error(f"Error updating payment: {e}")
        return None, str(e)


def delete_payment(payment_id: str) -> Tuple[bool, Optional[str]]:
    """Delete a payment from database."""
    if not DB_AVAILABLE or not is_db_configured():
        return False, "Database not configured"
    
    try:
        with get_db_session() as session:
            from database.models import Payment
            
            payment = session.query(Payment).filter(
                Payment.id == payment_id,
                Payment.organization_id == _get_org_id()
            ).first()
            
            if not payment:
                return False, "Payment not found"
            
            session.delete(payment)
            session.commit()
            return True, None
    except Exception as e:
        logger.error(f"Error deleting payment: {e}")
        return False, str(e)


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


# Aliases for route compatibility
def load_events() -> List[Dict]:
    """Alias for load_calendar_events."""
    return load_calendar_events()


def get_event(event_id: str) -> Optional[Dict]:
    """Get a single calendar event by ID."""
    if not DB_AVAILABLE or not is_db_configured():
        return None
    
    try:
        with get_db_session() as session:
            from database.models import CalendarEvent
            event = session.query(CalendarEvent).filter(
                CalendarEvent.id == event_id,
                CalendarEvent.organization_id == _get_org_id()
            ).first()
            return event.to_dict() if event else None
    except Exception as e:
        logger.error(f"Error getting event: {e}")
        return None


def create_event(data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Alias for create_calendar_event."""
    return create_calendar_event(data)


def update_event(event_id: str, data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Alias for update_calendar_event."""
    return update_calendar_event(event_id, data)


def delete_event(event_id: str) -> Tuple[bool, Optional[str]]:
    """Alias for delete_calendar_event."""
    return delete_calendar_event(event_id)


def get_events_by_date_range(start_date: str, end_date: str) -> List[Dict]:
    """Get calendar events within a date range."""
    if not DB_AVAILABLE or not is_db_configured():
        return []
    
    try:
        from dateutil import parser as date_parser
        
        start = date_parser.parse(start_date) if isinstance(start_date, str) else start_date
        end = date_parser.parse(end_date) if isinstance(end_date, str) else end_date
        
        return load_calendar_events(start_date=start, end_date=end)
    except Exception as e:
        logger.error(f"Error getting events by date range: {e}")
        return []

