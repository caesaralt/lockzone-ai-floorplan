"""
CRM Data Integration Module
============================

This module provides comprehensive data linking and integration for the CRM system.
It ensures all CRM entities are properly connected and can communicate with each other.

ALL DATA IS STORED IN THE DATABASE, NOT JSON FILES.

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
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# ============================================================================
# DATABASE LAYER ACCESS
# ============================================================================

def _get_db_components():
    """Get database components for operations"""
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


def _get_db_layer():
    """Get the CRM database layer instance"""
    try:
        from crm_db_layer import CRMDatabaseLayer
        from database.seed import get_default_organization_id
        org_id = get_default_organization_id()
        return CRMDatabaseLayer(org_id)
    except Exception as e:
        logger.error(f"Failed to get database layer: {e}")
        return None


# ============================================================================
# ENTITY LINKING FUNCTIONS
# ============================================================================

def link_technician_to_user(tech_id: str, user_id: str) -> bool:
    """Link a technician record to a user account"""
    get_db_session, org_id, CRMRepository, _ = _get_db_components()
    
    if not get_db_session:
        return False
    
    try:
        from database.models import Technician
        
        with get_db_session() as session:
            tech = session.query(Technician).filter(
                Technician.id == tech_id,
                Technician.organization_id == org_id
            ).first()
            
            if tech:
                tech.user_id = user_id
                tech.updated_at = datetime.utcnow()
                session.commit()
                return True
        return False
    except Exception as e:
        logger.error(f"Error linking technician to user: {e}")
        return False


def link_project_to_customer(project_id: str, customer_id: str) -> bool:
    """Link a project to a customer"""
    get_db_session, org_id, CRMRepository, _ = _get_db_components()
    
    if not get_db_session:
        return False
    
    try:
        from database.models import Project
        
        with get_db_session() as session:
            project = session.query(Project).filter(
                Project.id == project_id,
                Project.organization_id == org_id
            ).first()
            
            if project:
                project.customer_id = customer_id
                project.updated_at = datetime.utcnow()
                session.commit()
                return True
        return False
    except Exception as e:
        logger.error(f"Error linking project to customer: {e}")
        return False


def link_communication_to_entities(comm_id: str, customer_id: Optional[str] = None,
                                   project_id: Optional[str] = None) -> bool:
    """Link a communication to customer and/or project"""
    get_db_session, org_id, _, _ = _get_db_components()
    
    if not get_db_session:
        return False
    
    try:
        from database.models import Communication
        
        with get_db_session() as session:
            comm = session.query(Communication).filter(
                Communication.id == comm_id,
                Communication.organization_id == org_id
            ).first()
            
            if comm:
                if customer_id:
                    comm.customer_id = customer_id
                if project_id:
                    comm.project_id = project_id
                comm.updated_at = datetime.utcnow()
                session.commit()
                return True
        return False
    except Exception as e:
        logger.error(f"Error linking communication: {e}")
        return False


def link_event_to_entities(event_id: str, project_id: Optional[str] = None,
                           technician_id: Optional[str] = None) -> bool:
    """Link a calendar event to project and/or technician"""
    get_db_session, org_id, _, _ = _get_db_components()
    
    if not get_db_session:
        return False
    
    try:
        from database.models import CalendarEvent
        
        with get_db_session() as session:
            event = session.query(CalendarEvent).filter(
                CalendarEvent.id == event_id,
                CalendarEvent.organization_id == org_id
            ).first()
            
            if event:
                if project_id:
                    event.project_id = project_id
                if technician_id:
                    # Store in extra_data since CalendarEvent doesn't have direct technician_id
                    if not event.extra_data:
                        event.extra_data = {}
                    event.extra_data['assigned_to'] = technician_id
                event.updated_at = datetime.utcnow()
                session.commit()
                return True
        return False
    except Exception as e:
        logger.error(f"Error linking event: {e}")
        return False


def link_inventory_to_supplier(item_id: str, supplier_id: str) -> bool:
    """Link an inventory item to a supplier"""
    get_db_session, org_id, _, InventoryRepository = _get_db_components()
    
    if not get_db_session:
        return False
    
    try:
        with get_db_session() as session:
            repo = InventoryRepository(session, org_id)
            result = repo.update_item(item_id, {'supplier_id': supplier_id})
            session.commit()
            return result is not None
    except Exception as e:
        logger.error(f"Error linking inventory to supplier: {e}")
        return False


# ============================================================================
# RELATIONSHIP QUERIES
# ============================================================================

def get_customer_projects(customer_id: str) -> List[Dict]:
    """Get all projects for a customer"""
    db_layer = _get_db_layer()
    
    if not db_layer or not db_layer.db_enabled:
        return []
    
    try:
        result = db_layer.get_projects(customer_id=customer_id)
        return result.get('projects', [])
    except Exception as e:
        logger.error(f"Error getting customer projects: {e}")
        return []


def get_customer_communications(customer_id: str) -> List[Dict]:
    """Get all communications for a customer"""
    db_layer = _get_db_layer()
    
    if not db_layer or not db_layer.db_enabled:
        return []
    
    try:
        result = db_layer.get_communications(customer_id=customer_id)
        return result.get('communications', [])
    except Exception as e:
        logger.error(f"Error getting customer communications: {e}")
        return []


def get_project_details(project_id: str) -> Optional[Dict]:
    """Get project with all related data"""
    get_db_session, org_id, CRMRepository, _ = _get_db_components()
    
    if not get_db_session:
        return None
    
    try:
        with get_db_session() as session:
            repo = CRMRepository(session, org_id)
            
            project = repo.get_project(project_id)
            if not project:
                return None
            
            # Enrich with related data
            customer_id = project.get('customer_id')
            if customer_id:
                project['customer'] = repo.get_customer(customer_id)
            
            # Get communications
            project['communications'] = repo.list_communications(project_id=project_id)
            
            # Get events
            from database.models import CalendarEvent
            events = session.query(CalendarEvent).filter(
                CalendarEvent.organization_id == org_id,
                CalendarEvent.project_id == project_id
            ).all()
            project['events'] = [e.to_dict() for e in events]
            
            return project
    except Exception as e:
        logger.error(f"Error getting project details: {e}")
        return None


def get_technician_schedule(tech_id: str) -> List[Dict]:
    """Get all calendar events assigned to a technician"""
    get_db_session, org_id, CRMRepository, _ = _get_db_components()
    
    if not get_db_session:
        return []
    
    try:
        from database.models import CalendarEvent, Project
        from sqlalchemy import cast
        from sqlalchemy.dialects.postgresql import JSONB
        
        with get_db_session() as session:
            # Get events where assigned_to in extra_data matches tech_id
            events = session.query(CalendarEvent).filter(
                CalendarEvent.organization_id == org_id
            ).all()
            
            tech_events = []
            for event in events:
                if event.extra_data and event.extra_data.get('assigned_to') == tech_id:
                    event_dict = event.to_dict()
                    
                    # Enrich with project details
                    if event.project_id:
                        project = session.query(Project).filter(
                            Project.id == event.project_id
                        ).first()
                        if project:
                            event_dict['project'] = project.to_dict()
                    
                    tech_events.append(event_dict)
            
            return tech_events
    except Exception as e:
        logger.error(f"Error getting technician schedule: {e}")
        return []


def get_inventory_by_supplier(supplier_id: str) -> List[Dict]:
    """Get all inventory items from a supplier"""
    get_db_session, org_id, _, InventoryRepository = _get_db_components()
    
    if not get_db_session:
        return []
    
    try:
        from database.models import InventoryItem
        
        with get_db_session() as session:
            items = session.query(InventoryItem).filter(
                InventoryItem.organization_id == org_id,
                InventoryItem.supplier_id == supplier_id,
                InventoryItem.is_active == True
            ).all()
            return [item.to_dict() for item in items]
    except Exception as e:
        logger.error(f"Error getting inventory by supplier: {e}")
        return []


def get_user_assigned_projects(user_id: str) -> List[Dict]:
    """Get all projects assigned to a user (via technician link)"""
    get_db_session, org_id, CRMRepository, _ = _get_db_components()
    
    if not get_db_session:
        return []
    
    try:
        from database.models import Technician, CalendarEvent, Project
        
        with get_db_session() as session:
            # Find technician linked to user
            tech = session.query(Technician).filter(
                Technician.organization_id == org_id,
                Technician.user_id == user_id
            ).first()
            
            if not tech:
                return []
            
            # Get events for this technician
            events = session.query(CalendarEvent).filter(
                CalendarEvent.organization_id == org_id
            ).all()
            
            project_ids = set()
            for event in events:
                if event.extra_data and event.extra_data.get('assigned_to') == tech.id:
                    if event.project_id:
                        project_ids.add(event.project_id)
            
            # Get project details
            if not project_ids:
                return []
            
            projects = session.query(Project).filter(
                Project.id.in_(list(project_ids))
            ).all()
            
            return [p.to_dict() for p in projects]
    except Exception as e:
        logger.error(f"Error getting user assigned projects: {e}")
        return []


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
    
    get_db_session, org_id, CRMRepository, _ = _get_db_components()
    
    if not get_db_session:
        return validation
    
    try:
        from database.models import Project, Customer, Communication, CalendarEvent
        
        with get_db_session() as session:
            project = session.query(Project).filter(
                Project.id == project_id,
                Project.organization_id == org_id
            ).first()
            
            if not project:
                return validation
            
            validation['project_exists'] = True
            
            # Validate customer
            if project.customer_id:
                customer = session.query(Customer).filter(
                    Customer.id == project.customer_id
                ).first()
                if customer:
                    validation['customer_valid'] = True
            
            # Check communications
            comms = session.query(Communication).filter(
                Communication.project_id == project_id
            ).first()
            if comms:
                validation['communications_linked'] = True
            
            # Check events
            events = session.query(CalendarEvent).filter(
                CalendarEvent.project_id == project_id
            ).first()
            if events:
                validation['events_linked'] = True
            
            return validation
    except Exception as e:
        logger.error(f"Error validating project references: {e}")
        return validation


def cleanup_orphaned_references() -> Dict[str, int]:
    """Remove references to deleted entities"""
    cleanup_count = {
        'projects': 0,
        'communications': 0,
        'events': 0,
        'inventory': 0
    }
    
    get_db_session, org_id, _, _ = _get_db_components()
    
    if not get_db_session:
        return cleanup_count
    
    try:
        from database.models import Project, Customer, Communication, CalendarEvent, InventoryItem, Supplier, Technician
        
        with get_db_session() as session:
            # Get valid IDs
            customer_ids = [c.id for c in session.query(Customer.id).filter(
                Customer.organization_id == org_id,
                Customer.is_active == True
            ).all()]
            
            project_ids = [p.id for p in session.query(Project.id).filter(
                Project.organization_id == org_id
            ).all()]
            
            supplier_ids = [s.id for s in session.query(Supplier.id).filter(
                Supplier.organization_id == org_id,
                Supplier.is_active == True
            ).all()]
            
            tech_ids = [t.id for t in session.query(Technician.id).filter(
                Technician.organization_id == org_id,
                Technician.is_active == True
            ).all()]
            
            # Clean projects with invalid customer references
            projects = session.query(Project).filter(
                Project.organization_id == org_id,
                Project.customer_id.isnot(None),
                ~Project.customer_id.in_(customer_ids) if customer_ids else True
            ).all()
            
            for project in projects:
                project.customer_id = None
                cleanup_count['projects'] += 1
            
            # Clean communications
            comms = session.query(Communication).filter(
                Communication.organization_id == org_id
            ).all()
            
            for comm in comms:
                if comm.customer_id and comm.customer_id not in customer_ids:
                    comm.customer_id = None
                    cleanup_count['communications'] += 1
                if comm.project_id and comm.project_id not in project_ids:
                    comm.project_id = None
                    cleanup_count['communications'] += 1
            
            # Clean inventory
            items = session.query(InventoryItem).filter(
                InventoryItem.organization_id == org_id,
                InventoryItem.supplier_id.isnot(None)
            ).all()
            
            for item in items:
                if item.supplier_id not in supplier_ids:
                    item.supplier_id = None
                    cleanup_count['inventory'] += 1
            
            session.commit()
            return cleanup_count
    except Exception as e:
        logger.error(f"Error cleaning up orphaned references: {e}")
        return cleanup_count


# ============================================================================
# DATA EXPORT AND REPORTING
# ============================================================================

def get_complete_crm_snapshot() -> Dict[str, Any]:
    """Get a complete snapshot of all CRM data with relationships"""
    db_layer = _get_db_layer()
    
    if not db_layer or not db_layer.db_enabled:
        return {
            'error': 'Database not available',
            'generated_at': datetime.now().isoformat()
        }
    
    try:
        customers_result = db_layer.get_customers()
        projects_result = db_layer.get_projects()
        quotes_result = db_layer.get_quotes()
        jobs_result = db_layer.get_jobs()
        technicians_result = db_layer.get_technicians()
        suppliers_result = db_layer.get_suppliers()
        stock_result = db_layer.get_stock()
        calendar_result = db_layer.get_calendar_events()
        
        return {
            'customers': customers_result.get('customers', []),
            'projects': projects_result.get('projects', []),
            'quotes': quotes_result.get('quotes', []),
            'jobs': jobs_result.get('jobs', []),
            'technicians': technicians_result.get('technicians', []),
            'suppliers': suppliers_result.get('suppliers', []),
            'inventory': stock_result.get('items', []),
            'calendar': calendar_result.get('events', []),
            'generated_at': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting CRM snapshot: {e}")
        return {
            'error': str(e),
            'generated_at': datetime.now().isoformat()
        }


def get_crm_health_report() -> Dict[str, Any]:
    """Generate a health report of CRM data integrity"""
    db_layer = _get_db_layer()
    
    if not db_layer or not db_layer.db_enabled:
        return {
            'error': 'Database not available',
            'generated_at': datetime.now().isoformat()
        }
    
    try:
        customers_result = db_layer.get_customers()
        projects_result = db_layer.get_projects()
        quotes_result = db_layer.get_quotes()
        jobs_result = db_layer.get_jobs()
        technicians_result = db_layer.get_technicians()
        suppliers_result = db_layer.get_suppliers()
        stock_result = db_layer.get_stock()
        calendar_result = db_layer.get_calendar_events()
        
        customers = customers_result.get('customers', [])
        projects = projects_result.get('projects', [])
        technicians = technicians_result.get('technicians', [])
        inventory = stock_result.get('items', stock_result.get('stock', []))
        events = calendar_result.get('events', [])
        
        # Get communications count
        get_db_session, org_id, CRMRepository, _ = _get_db_components()
        comms = []
        if get_db_session:
            try:
                with get_db_session() as session:
                    repo = CRMRepository(session, org_id)
                    comms = repo.list_communications()
            except:
                pass
        
        # Count relationships
        projects_with_customers = sum(1 for p in projects if p.get('customer_id'))
        comms_with_links = sum(1 for c in comms if c.get('customer_id') or c.get('project_id'))
        events_with_links = sum(1 for e in events if e.get('project_id') or (e.get('metadata', {}) or {}).get('assigned_to'))
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
                'suppliers': len(suppliers_result.get('suppliers', []))
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
            'storage': 'database',
            'generated_at': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating CRM health report: {e}")
        return {
            'error': str(e),
            'generated_at': datetime.now().isoformat()
        }


# ============================================================================
# INITIALIZATION
# ============================================================================

def initialize_crm_system():
    """Initialize CRM system - database is now the source of truth"""
    logger.info("CRM Integration module initialized - using database storage")


# Auto-initialize on import
initialize_crm_system()
