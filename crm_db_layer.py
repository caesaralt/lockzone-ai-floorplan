"""
CRM Database Layer - PostgreSQL-backed data operations
Drop-in replacement for CRMDataLayer that uses PostgreSQL instead of JSON files.
Maintains the same interface for compatibility with existing code.
"""
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from functools import wraps

logger = logging.getLogger(__name__)

# Check if database is available
try:
    from database.connection import get_db_session, is_db_configured, check_db_connection
    from database.seed import get_default_organization_id, seed_database
    from services.crm_repository import CRMRepository
    from services.inventory_repository import InventoryRepository
    from services.users_repository import UsersRepository
    DB_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Database modules not available: {e}")
    DB_AVAILABLE = False


def db_operation(func):
    """Decorator to handle database session and error handling."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.db_enabled:
            return {'success': False, 'error': 'Database not configured'}
        try:
            with get_db_session() as session:
                self._session = session
                self._crm_repo = CRMRepository(session, self.organization_id)
                self._inv_repo = InventoryRepository(session, self.organization_id)
                result = func(self, *args, **kwargs)
                session.commit()
                return result
        except Exception as e:
            logger.error(f"Database operation error in {func.__name__}: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            self._session = None
            self._crm_repo = None
            self._inv_repo = None
    return wrapper


class CRMDatabaseLayer:
    """
    Database-backed CRM data layer.
    Provides the same interface as CRMDataLayer but uses PostgreSQL.
    """
    
    def __init__(self, organization_id: str = None):
        self.db_enabled = DB_AVAILABLE and is_db_configured()
        self._session = None
        self._crm_repo = None
        self._inv_repo = None
        
        if self.db_enabled:
            try:
                check_db_connection()
                seed_database()
                self.organization_id = organization_id or get_default_organization_id()
                logger.info(f"CRM Database Layer initialized for org: {self.organization_id}")
            except Exception as e:
                logger.error(f"Failed to initialize database: {e}")
                self.db_enabled = False
                self.organization_id = None
        else:
            self.organization_id = None
            logger.warning("Database not configured - CRM operations will fail")
    
    # ==================== SORTING HELPER ====================
    
    def _sort_items(self, items: List[Dict], sort_by: str = 'created_at', 
                   sort_order: str = 'desc') -> List[Dict]:
        """Sort a list of items by a given field."""
        if not items or not sort_by:
            return items
        
        reverse = sort_order.lower() == 'desc'
        
        def get_sort_key(item):
            value = item.get(sort_by)
            if value is None:
                return '' if reverse else 'zzz'  # Sort nulls last
            if isinstance(value, str):
                return value.lower()
            return value
        
        try:
            return sorted(items, key=get_sort_key, reverse=reverse)
        except (TypeError, ValueError):
            return items  # Return unsorted if comparison fails
    
    # ==================== CUSTOMERS ====================
    
    @db_operation
    def get_customers(self, search: str = None, status: str = None,
                     page: int = 1, per_page: int = 50,
                     sort_by: str = 'created_at', sort_order: str = 'desc') -> Dict:
        """Get paginated list of customers."""
        customers = self._crm_repo.list_customers(active_only=(status != 'inactive'))
        
        # Apply search filter
        if search:
            search_lower = search.lower()
            customers = [c for c in customers if 
                        search_lower in (c.get('name') or '').lower() or
                        search_lower in (c.get('company') or '').lower() or
                        search_lower in (c.get('email') or '').lower()]
        
        # Apply sorting
        customers = self._sort_items(customers, sort_by, sort_order)
        
        # Pagination
        total = len(customers)
        start = (page - 1) * per_page
        end = start + per_page
        paginated = customers[start:end]
        
        return {
            'success': True,
            'customers': paginated,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }
    
    @db_operation
    def get_customer(self, customer_id: str) -> Dict:
        """Get a single customer by ID."""
        customer = self._crm_repo.get_customer(customer_id)
        if customer:
            return {'success': True, 'customer': customer}
        return {'success': False, 'error': 'Customer not found'}
    
    @db_operation
    def create_customer(self, data: Dict) -> Dict:
        """Create a new customer."""
        # Validate
        name = data.get('name', '').strip()
        if not name:
            return {'success': False, 'error': 'Customer name is required'}
        
        customer = self._crm_repo.create_customer(data)
        return {'success': True, 'customer': customer}
    
    @db_operation
    def update_customer(self, customer_id: str, data: Dict) -> Dict:
        """Update an existing customer."""
        customer = self._crm_repo.update_customer(customer_id, data)
        if customer:
            return {'success': True, 'customer': customer}
        return {'success': False, 'error': 'Customer not found'}
    
    @db_operation
    def delete_customer(self, customer_id: str, cascade: bool = False) -> Dict:
        """Delete a customer (soft delete)."""
        success = self._crm_repo.delete_customer(customer_id)
        if success:
            return {'success': True, 'message': 'Customer deleted'}
        return {'success': False, 'error': 'Customer not found'}
    
    # ==================== PROJECTS ====================
    
    @db_operation
    def get_projects(self, customer_id: str = None, status: str = None,
                    search: str = None, page: int = 1, per_page: int = 50,
                    sort_by: str = 'created_at', sort_order: str = 'desc') -> Dict:
        """Get paginated list of projects."""
        projects = self._crm_repo.list_projects(customer_id=customer_id, status=status)
        
        # Apply search filter
        if search:
            search_lower = search.lower()
            projects = [p for p in projects if 
                       search_lower in (p.get('name') or '').lower() or
                       search_lower in (p.get('description') or '').lower()]
        
        # Apply sorting
        projects = self._sort_items(projects, sort_by, sort_order)
        
        # Pagination
        total = len(projects)
        start = (page - 1) * per_page
        end = start + per_page
        paginated = projects[start:end]
        
        return {
            'success': True,
            'projects': paginated,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }
    
    @db_operation
    def get_project(self, project_id: str) -> Dict:
        """Get a single project by ID."""
        project = self._crm_repo.get_project(project_id)
        if project:
            return {'success': True, 'project': project}
        return {'success': False, 'error': 'Project not found'}
    
    @db_operation
    def create_project(self, data: Dict) -> Dict:
        """Create a new project."""
        name = data.get('name', '').strip()
        if not name:
            return {'success': False, 'error': 'Project name is required'}
        
        project = self._crm_repo.create_project(data)
        return {'success': True, 'project': project}
    
    @db_operation
    def update_project(self, project_id: str, data: Dict) -> Dict:
        """Update an existing project."""
        project = self._crm_repo.update_project(project_id, data)
        if project:
            return {'success': True, 'project': project}
        return {'success': False, 'error': 'Project not found'}
    
    @db_operation
    def delete_project(self, project_id: str) -> Dict:
        """Delete a project."""
        success = self._crm_repo.delete_project(project_id)
        if success:
            return {'success': True, 'message': 'Project deleted'}
        return {'success': False, 'error': 'Project not found'}
    
    # ==================== QUOTES ====================
    
    @db_operation
    def get_quotes(self, customer_id: str = None, status: str = None,
                  source: str = None, search: str = None, 
                  page: int = 1, per_page: int = 50,
                  sort_by: str = 'created_at', sort_order: str = 'desc') -> Dict:
        """Get paginated list of quotes."""
        quotes = self._crm_repo.list_quotes(
            customer_id=customer_id, 
            status=status,
            source=source
        )
        
        # Apply search filter
        if search:
            search_lower = search.lower()
            quotes = [q for q in quotes if 
                     search_lower in (q.get('title') or '').lower() or
                     search_lower in (q.get('description') or '').lower() or
                     search_lower in (q.get('quote_number') or '').lower()]
        
        # Apply sorting
        quotes = self._sort_items(quotes, sort_by, sort_order)
        
        # Pagination
        total = len(quotes)
        start = (page - 1) * per_page
        end = start + per_page
        paginated = quotes[start:end]
        
        return {
            'success': True,
            'quotes': paginated,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }
    
    @db_operation
    def get_quote(self, quote_id: str) -> Dict:
        """Get a single quote by ID."""
        quote = self._crm_repo.get_quote(quote_id)
        if quote:
            return {'success': True, 'quote': quote}
        return {'success': False, 'error': 'Quote not found'}
    
    @db_operation
    def create_quote(self, data: Dict) -> Dict:
        """Create a new quote."""
        title = data.get('title', '').strip()
        if not title:
            return {'success': False, 'error': 'Quote title is required'}
        
        # Generate quote number if not provided
        if not data.get('quote_number'):
            data['quote_number'] = f"Q-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        quote = self._crm_repo.create_quote(data)
        return {'success': True, 'quote': quote}
    
    @db_operation
    def update_quote(self, quote_id: str, data: Dict) -> Dict:
        """Update an existing quote."""
        quote = self._crm_repo.update_quote(quote_id, data)
        if quote:
            return {'success': True, 'quote': quote}
        return {'success': False, 'error': 'Quote not found'}
    
    @db_operation
    def delete_quote(self, quote_id: str) -> Dict:
        """Delete a quote."""
        success = self._crm_repo.delete_quote(quote_id)
        if success:
            return {'success': True, 'message': 'Quote deleted'}
        return {'success': False, 'error': 'Quote not found'}
    
    @db_operation
    def convert_quote_to_project(self, quote_id: str) -> Dict:
        """Convert a quote to a project."""
        quote = self._crm_repo.get_quote(quote_id)
        if not quote:
            return {'success': False, 'error': 'Quote not found'}
        
        # Create project from quote
        project_data = {
            'name': quote.get('title', 'Converted Project'),
            'customer_id': quote.get('customer_id'),
            'description': quote.get('description'),
            'estimated_value': quote.get('total_amount', 0),
            'status': 'pending',
            'metadata': {'converted_from_quote': quote_id}
        }
        project = self._crm_repo.create_project(project_data)
        
        # Update quote status and link to project
        self._crm_repo.update_quote(quote_id, {
            'status': 'accepted',
            'project_id': project['id']
        })
        
        return {'success': True, 'project': project, 'quote': quote}
    
    # ==================== STOCK / INVENTORY ====================
    
    @db_operation
    def get_stock(self, category: str = None, search: str = None,
                 low_stock: bool = False, low_stock_only: bool = False,
                 page: int = 1, per_page: int = 50,
                 sort_by: str = 'name', sort_order: str = 'asc') -> Dict:
        """Get paginated list of stock items."""
        # Support both low_stock and low_stock_only parameter names
        is_low_stock = low_stock or low_stock_only
        items = self._inv_repo.list_items(category=category, low_stock_only=is_low_stock)
        
        # Apply search filter
        if search:
            search_lower = search.lower()
            items = [i for i in items if 
                    search_lower in (i.get('name') or '').lower() or
                    search_lower in (i.get('sku') or '').lower()]
        
        # Apply sorting
        items = self._sort_items(items, sort_by, sort_order)
        
        # Pagination
        total = len(items)
        start = (page - 1) * per_page
        end = start + per_page
        paginated = items[start:end]
        
        return {
            'success': True,
            'items': paginated,
            'stock': paginated,  # Alias for compatibility
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }
    
    @db_operation
    def get_stock_item(self, item_id: str) -> Dict:
        """Get a single stock item by ID."""
        item = self._inv_repo.get_item(item_id)
        if item:
            return {'success': True, 'item': item}
        return {'success': False, 'error': 'Stock item not found'}
    
    @db_operation
    def create_stock_item(self, data: Dict) -> Dict:
        """Create a new stock item."""
        name = data.get('name', '').strip()
        if not name:
            return {'success': False, 'error': 'Item name is required'}
        
        item = self._inv_repo.create_item(data)
        return {'success': True, 'item': item}
    
    @db_operation
    def update_stock_item(self, item_id: str, data: Dict) -> Dict:
        """Update an existing stock item."""
        item = self._inv_repo.update_item(item_id, data)
        if item:
            return {'success': True, 'item': item}
        return {'success': False, 'error': 'Stock item not found'}
    
    @db_operation
    def delete_stock_item(self, item_id: str) -> Dict:
        """Delete a stock item (soft delete)."""
        success = self._inv_repo.delete_item(item_id)
        if success:
            return {'success': True, 'message': 'Stock item deleted'}
        return {'success': False, 'error': 'Stock item not found'}
    
    @db_operation
    def adjust_stock_quantity(self, item_id: str, adjustment: int, 
                             reason: str = '') -> Dict:
        """Adjust stock quantity."""
        item = self._inv_repo.adjust_quantity(item_id, adjustment, reason)
        if item:
            return {'success': True, 'item': item}
        return {'success': False, 'error': 'Stock item not found'}
    
    # ==================== JOBS ====================
    
    @db_operation
    def get_jobs(self, project_id: str = None, status: str = None,
                technician_id: str = None, page: int = 1, per_page: int = 50) -> Dict:
        """Get paginated list of jobs."""
        jobs = self._crm_repo.list_jobs(
            project_id=project_id,
            status=status,
            technician_id=technician_id
        )
        
        # Pagination
        total = len(jobs)
        start = (page - 1) * per_page
        end = start + per_page
        paginated = jobs[start:end]
        
        return {
            'success': True,
            'jobs': paginated,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }
    
    @db_operation
    def get_job(self, job_id: str) -> Dict:
        """Get a single job by ID."""
        job = self._crm_repo.get_job(job_id)
        if job:
            return {'success': True, 'job': job}
        return {'success': False, 'error': 'Job not found'}
    
    @db_operation
    def create_job(self, data: Dict) -> Dict:
        """Create a new job."""
        title = data.get('title', '').strip()
        if not title:
            return {'success': False, 'error': 'Job title is required'}
        
        job = self._crm_repo.create_job(data)
        return {'success': True, 'job': job}
    
    @db_operation
    def update_job(self, job_id: str, data: Dict) -> Dict:
        """Update an existing job."""
        job = self._crm_repo.update_job(job_id, data)
        if job:
            return {'success': True, 'job': job}
        return {'success': False, 'error': 'Job not found'}
    
    @db_operation
    def delete_job(self, job_id: str) -> Dict:
        """Delete a job."""
        success = self._crm_repo.delete_job(job_id)
        if success:
            return {'success': True, 'message': 'Job deleted'}
        return {'success': False, 'error': 'Job not found'}
    
    # ==================== TECHNICIANS ====================
    
    @db_operation
    def get_technicians(self, active_only: bool = True) -> Dict:
        """Get list of technicians."""
        technicians = self._crm_repo.list_technicians(active_only=active_only)
        return {'success': True, 'technicians': technicians}
    
    @db_operation
    def create_technician(self, data: Dict) -> Dict:
        """Create a new technician."""
        name = data.get('name', '').strip()
        if not name:
            return {'success': False, 'error': 'Technician name is required'}
        
        tech = self._crm_repo.create_technician(data)
        return {'success': True, 'technician': tech}
    
    @db_operation
    def update_technician(self, technician_id: str, data: Dict) -> Dict:
        """Update a technician."""
        tech = self._crm_repo.update_technician(technician_id, data)
        if tech:
            return {'success': True, 'technician': tech}
        return {'success': False, 'error': 'Technician not found'}
    
    @db_operation
    def delete_technician(self, technician_id: str) -> Dict:
        """Delete a technician (soft delete)."""
        success = self._crm_repo.delete_technician(technician_id)
        if success:
            return {'success': True, 'message': 'Technician deleted'}
        return {'success': False, 'error': 'Technician not found'}
    
    # ==================== SUPPLIERS ====================
    
    @db_operation
    def get_suppliers(self, active_only: bool = True) -> Dict:
        """Get list of suppliers."""
        suppliers = self._crm_repo.list_suppliers(active_only=active_only)
        return {'success': True, 'suppliers': suppliers}
    
    @db_operation
    def create_supplier(self, data: Dict) -> Dict:
        """Create a new supplier."""
        name = data.get('name', '').strip()
        if not name:
            return {'success': False, 'error': 'Supplier name is required'}
        
        supplier = self._crm_repo.create_supplier(data)
        return {'success': True, 'supplier': supplier}
    
    @db_operation
    def update_supplier(self, supplier_id: str, data: Dict) -> Dict:
        """Update a supplier."""
        supplier = self._crm_repo.update_supplier(supplier_id, data)
        if supplier:
            return {'success': True, 'supplier': supplier}
        return {'success': False, 'error': 'Supplier not found'}
    
    @db_operation
    def delete_supplier(self, supplier_id: str) -> Dict:
        """Delete a supplier (soft delete)."""
        success = self._crm_repo.delete_supplier(supplier_id)
        if success:
            return {'success': True, 'message': 'Supplier deleted'}
        return {'success': False, 'error': 'Supplier not found'}
    
    # ==================== COMMUNICATIONS ====================
    
    @db_operation
    def get_communications(self, customer_id: str = None, 
                          project_id: str = None) -> Dict:
        """Get list of communications."""
        comms = self._crm_repo.list_communications(
            customer_id=customer_id,
            project_id=project_id
        )
        return {'success': True, 'communications': comms}
    
    @db_operation
    def create_communication(self, data: Dict) -> Dict:
        """Create a new communication record."""
        comm = self._crm_repo.create_communication(data)
        return {'success': True, 'communication': comm}
    
    # ==================== CALENDAR ====================
    
    @db_operation
    def get_calendar_events(self, start_date: str = None, 
                           end_date: str = None) -> Dict:
        """Get calendar events."""
        from datetime import datetime
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None
        events = self._crm_repo.list_calendar_events(start_date=start, end_date=end)
        return {'success': True, 'events': events}
    
    @db_operation
    def get_calendar_event(self, event_id: str) -> Dict:
        """Get a calendar event by ID."""
        event = self._crm_repo.get_calendar_event(event_id)
        if event:
            return {'success': True, 'event': event}
        return {'success': False, 'error': 'Event not found'}
    
    @db_operation
    def create_calendar_event(self, data: Dict) -> Dict:
        """Create a new calendar event."""
        title = data.get('title', '').strip()
        if not title:
            return {'success': False, 'error': 'Event title is required'}
        
        event = self._crm_repo.create_calendar_event(data)
        return {'success': True, 'event': event}
    
    @db_operation
    def update_calendar_event(self, event_id: str, data: Dict) -> Dict:
        """Update a calendar event."""
        event = self._crm_repo.update_calendar_event(event_id, data)
        if event:
            return {'success': True, 'event': event}
        return {'success': False, 'error': 'Event not found'}
    
    @db_operation
    def delete_calendar_event(self, event_id: str) -> Dict:
        """Delete a calendar event."""
        success = self._crm_repo.delete_calendar_event(event_id)
        if success:
            return {'success': True, 'message': 'Event deleted'}
        return {'success': False, 'error': 'Event not found'}
    
    # ==================== PRICE CLASSES ====================
    
    @db_operation
    def get_price_classes(self, active_only: bool = True) -> Dict:
        """Get list of price classes."""
        price_classes = self._crm_repo.list_price_classes(active_only=active_only)
        return {'success': True, 'price_classes': price_classes}
    
    @db_operation
    def get_price_class(self, price_class_id: str) -> Dict:
        """Get a price class by ID."""
        pc = self._crm_repo.get_price_class(price_class_id)
        if pc:
            return {'success': True, 'price_class': pc}
        return {'success': False, 'error': 'Price class not found'}
    
    @db_operation
    def create_price_class(self, data: Dict) -> Dict:
        """Create a new price class."""
        name = data.get('name', '').strip()
        if not name:
            return {'success': False, 'error': 'Price class name is required'}
        
        pc = self._crm_repo.create_price_class(data)
        return {'success': True, 'price_class': pc}
    
    @db_operation
    def update_price_class(self, price_class_id: str, data: Dict) -> Dict:
        """Update a price class."""
        pc = self._crm_repo.update_price_class(price_class_id, data)
        if pc:
            return {'success': True, 'price_class': pc}
        return {'success': False, 'error': 'Price class not found'}
    
    @db_operation
    def delete_price_class(self, price_class_id: str) -> Dict:
        """Delete a price class (soft delete)."""
        success = self._crm_repo.delete_price_class(price_class_id)
        if success:
            return {'success': True, 'message': 'Price class deleted'}
        return {'success': False, 'error': 'Price class not found'}
    
    # ==================== STATISTICS ====================
    
    @db_operation
    def get_stats(self) -> Dict:
        """Get comprehensive CRM statistics."""
        customers = self._crm_repo.list_customers()
        projects = self._crm_repo.list_projects()
        quotes = self._crm_repo.list_quotes()
        jobs = self._crm_repo.list_jobs()
        
        # Calculate stats
        active_projects = [p for p in projects if p.get('status') == 'in_progress']
        pending_quotes = [q for q in quotes if q.get('status') in ['draft', 'sent']]
        total_revenue = sum(q.get('total_amount', 0) for q in quotes 
                          if q.get('status') == 'accepted')
        pending_revenue = sum(q.get('total_amount', 0) for q in pending_quotes)
        
        # Stock stats
        stock_items = self._inv_repo.list_items()
        stock_value = sum(i.get('quantity', 0) * (i.get('cost_price') or i.get('unit_price', 0))
                         for i in stock_items)
        low_stock = [i for i in stock_items 
                    if i.get('quantity', 0) <= i.get('reorder_level', 5)]
        
        return {
            'success': True,
            'stats': {
                'customers': {
                    'total': len(customers),
                    'active': len([c for c in customers if c.get('is_active', True)])
                },
                'projects': {
                    'total': len(projects),
                    'active': len(active_projects),
                    'by_status': self._count_by_status(projects)
                },
                'quotes': {
                    'total': len(quotes),
                    'pending': len(pending_quotes),
                    'by_status': self._count_by_status(quotes)
                },
                'jobs': {
                    'total': len(jobs),
                    'by_status': self._count_by_status(jobs)
                },
                'revenue': {
                    'total': total_revenue,
                    'pending': pending_revenue
                },
                'stock': {
                    'total_items': len(stock_items),
                    'total_value': stock_value,
                    'low_stock_count': len(low_stock)
                }
            }
        }
    
    def _count_by_status(self, items: List[Dict]) -> Dict[str, int]:
        """Count items by status."""
        counts = {}
        for item in items:
            status = item.get('status', 'unknown')
            counts[status] = counts.get(status, 0) + 1
        return counts
    
    # ==================== DATA INTEGRITY ====================
    
    def check_data_integrity(self) -> Dict:
        """Check data integrity (stub for compatibility)."""
        return {
            'success': True,
            'issues': [],
            'message': 'Database integrity verified by PostgreSQL constraints'
        }
    
    def repair_data_integrity(self) -> Dict:
        """Repair data integrity (stub for compatibility)."""
        return {
            'success': True,
            'repairs': [],
            'message': 'No repairs needed - PostgreSQL maintains data integrity'
        }


# Factory function for compatibility
def get_crm_db_layer(organization_id: str = None) -> CRMDatabaseLayer:
    """Get a CRM database layer instance."""
    return CRMDatabaseLayer(organization_id)

