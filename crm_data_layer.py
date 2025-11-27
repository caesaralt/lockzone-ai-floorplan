"""
CRM Data Layer - Robust data operations with validation, integrity, and pagination
Provides a clean interface for all CRM data operations
"""
import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import logging
import threading
import re

logger = logging.getLogger(__name__)

# File lock for thread-safe operations
_file_locks = {}

def get_file_lock(filepath: str) -> threading.Lock:
    """Get or create a lock for a specific file"""
    if filepath not in _file_locks:
        _file_locks[filepath] = threading.Lock()
    return _file_locks[filepath]


class CRMDataLayer:
    """
    Centralized data layer for CRM operations with:
    - Validation
    - Cascading updates
    - Pagination
    - Search
    - Data integrity
    """
    
    def __init__(self, data_folder: str):
        self.data_folder = data_folder
        self.customers_file = os.path.join(data_folder, 'customers.json')
        self.projects_file = os.path.join(data_folder, 'projects.json')
        self.quotes_file = os.path.join(data_folder, 'quotes.json')
        self.stock_file = os.path.join(data_folder, 'stock.json')
        
        # Ensure data folder exists
        os.makedirs(data_folder, exist_ok=True)
    
    # ==================== FILE OPERATIONS ====================
    
    def _load_json(self, filepath: str, default: Any = None) -> Any:
        """Thread-safe JSON file loading with error handling"""
        if default is None:
            default = []
        
        lock = get_file_lock(filepath)
        with lock:
            try:
                if os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if not content:
                            return default
                        return json.loads(content)
                return default
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in {filepath}: {e}")
                # Backup corrupted file
                if os.path.exists(filepath):
                    backup_path = f"{filepath}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    os.rename(filepath, backup_path)
                    logger.warning(f"Corrupted file backed up to {backup_path}")
                return default
            except Exception as e:
                logger.error(f"Error loading {filepath}: {e}")
                return default
    
    def _save_json(self, filepath: str, data: Any) -> bool:
        """Thread-safe JSON file saving with atomic write"""
        lock = get_file_lock(filepath)
        with lock:
            try:
                # Write to temp file first, then rename (atomic operation)
                temp_path = f"{filepath}.tmp"
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, default=str)
                os.replace(temp_path, filepath)
                return True
            except Exception as e:
                logger.error(f"Error saving {filepath}: {e}")
                # Clean up temp file if it exists
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return False
    
    # ==================== VALIDATION ====================
    
    def validate_customer(self, data: Dict, is_update: bool = False) -> Tuple[bool, str]:
        """Validate customer data"""
        if not is_update:
            name = data.get('name', '').strip()
            if not name:
                return False, "Customer name is required"
            if len(name) < 2:
                return False, "Customer name must be at least 2 characters"
        
        email = data.get('email', '').strip()
        if email and not self._is_valid_email(email):
            return False, "Invalid email format"
        
        phone = data.get('phone', '').strip()
        if phone and not self._is_valid_phone(phone):
            return False, "Invalid phone format"
        
        status = data.get('status', 'active')
        if status not in ['active', 'inactive', 'lead', 'prospect']:
            return False, f"Invalid status: {status}"
        
        return True, ""
    
    def validate_project(self, data: Dict, is_update: bool = False) -> Tuple[bool, str]:
        """Validate project data"""
        if not is_update:
            title = data.get('title', '').strip()
            if not title:
                return False, "Project title is required"
            if len(title) < 2:
                return False, "Project title must be at least 2 characters"
        
        status = data.get('status', 'pending')
        valid_statuses = ['pending', 'planning', 'in_progress', 'on_hold', 'completed', 'cancelled']
        if status not in valid_statuses:
            return False, f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        
        priority = data.get('priority', 'medium')
        if priority not in ['low', 'medium', 'high', 'urgent']:
            return False, "Invalid priority. Must be: low, medium, high, or urgent"
        
        # Validate amounts are non-negative
        for field in ['quote_amount', 'actual_amount']:
            if field in data:
                try:
                    amount = float(data[field])
                    if amount < 0:
                        return False, f"{field} cannot be negative"
                except (TypeError, ValueError):
                    return False, f"{field} must be a valid number"
        
        return True, ""
    
    def validate_quote(self, data: Dict, is_update: bool = False) -> Tuple[bool, str]:
        """Validate quote data"""
        if not is_update:
            title = data.get('title', '').strip()
            if not title:
                return False, "Quote title is required"
        
        status = data.get('status', 'draft')
        valid_statuses = ['draft', 'sent', 'accepted', 'rejected', 'expired', 'revised']
        if status not in valid_statuses:
            return False, f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        
        # Validate amounts
        for field in ['quote_amount', 'labor_cost', 'materials_cost', 'markup_percentage']:
            if field in data:
                try:
                    amount = float(data[field])
                    if amount < 0:
                        return False, f"{field} cannot be negative"
                except (TypeError, ValueError):
                    return False, f"{field} must be a valid number"
        
        return True, ""
    
    def validate_stock_item(self, data: Dict, is_update: bool = False) -> Tuple[bool, str]:
        """Validate stock item data"""
        if not is_update:
            name = data.get('name', '').strip()
            if not name:
                return False, "Stock item name is required"
        
        quantity = data.get('quantity', 0)
        try:
            quantity = int(quantity)
            if quantity < 0:
                return False, "Quantity cannot be negative"
        except (TypeError, ValueError):
            return False, "Quantity must be a valid integer"
        
        for field in ['cost', 'unit_price']:
            if field in data:
                try:
                    price = float(data[field])
                    if price < 0:
                        return False, f"{field} cannot be negative"
                except (TypeError, ValueError):
                    return False, f"{field} must be a valid number"
        
        return True, ""
    
    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _is_valid_phone(self, phone: str) -> bool:
        """Basic phone validation - accepts various formats"""
        # Remove common formatting characters
        cleaned = re.sub(r'[\s\-\(\)\+\.]', '', phone)
        # Should be 7-15 digits
        return bool(re.match(r'^\d{7,15}$', cleaned))
    
    # ==================== CUSTOMERS ====================
    
    def get_customers(self, 
                      search: str = None,
                      status: str = None,
                      page: int = 1,
                      per_page: int = 50,
                      sort_by: str = 'created_at',
                      sort_order: str = 'desc') -> Dict:
        """Get customers with filtering, pagination, and search"""
        customers = self._load_json(self.customers_file, [])
        
        # Filter by status
        if status:
            customers = [c for c in customers if c.get('status') == status]
        
        # Search
        if search:
            search_lower = search.lower()
            customers = [c for c in customers if 
                        search_lower in c.get('name', '').lower() or
                        search_lower in c.get('email', '').lower() or
                        search_lower in c.get('phone', '').lower() or
                        search_lower in c.get('address', '').lower()]
        
        # Sort
        reverse = sort_order == 'desc'
        customers.sort(key=lambda x: x.get(sort_by, ''), reverse=reverse)
        
        # Pagination
        total = len(customers)
        start = (page - 1) * per_page
        end = start + per_page
        paginated = customers[start:end]
        
        return {
            'success': True,
            'customers': paginated,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        }
    
    def get_customer(self, customer_id: str) -> Dict:
        """Get a single customer with related data"""
        customers = self._load_json(self.customers_file, [])
        customer = next((c for c in customers if c['id'] == customer_id), None)
        
        if not customer:
            return {'success': False, 'error': 'Customer not found'}
        
        # Get related projects and quotes
        projects = self._load_json(self.projects_file, [])
        quotes = self._load_json(self.quotes_file, [])
        
        customer_projects = [p for p in projects if p.get('customer_id') == customer_id]
        customer_quotes = [q for q in quotes if q.get('customer_id') == customer_id]
        
        return {
            'success': True,
            'customer': customer,
            'projects': customer_projects,
            'quotes': customer_quotes,
            'stats': {
                'total_projects': len(customer_projects),
                'active_projects': len([p for p in customer_projects if p.get('status') in ['pending', 'in_progress', 'planning']]),
                'total_quotes': len(customer_quotes),
                'total_revenue': sum(p.get('actual_amount', 0) for p in customer_projects if p.get('status') == 'completed')
            }
        }
    
    def create_customer(self, data: Dict) -> Dict:
        """Create a new customer"""
        valid, error = self.validate_customer(data)
        if not valid:
            return {'success': False, 'error': error}
        
        customers = self._load_json(self.customers_file, [])
        
        # Check for duplicate email
        email = data.get('email', '').strip()
        if email:
            existing = next((c for c in customers if c.get('email', '').lower() == email.lower()), None)
            if existing:
                return {'success': False, 'error': 'A customer with this email already exists'}
        
        customer = {
            'id': str(uuid.uuid4()),
            'name': data.get('name', '').strip(),
            'email': email,
            'phone': data.get('phone', '').strip(),
            'address': data.get('address', '').strip(),
            'company': data.get('company', '').strip(),
            'notes': data.get('notes', '').strip(),
            'status': data.get('status', 'active'),
            'tags': data.get('tags', []),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        customers.append(customer)
        
        if self._save_json(self.customers_file, customers):
            return {'success': True, 'customer': customer}
        return {'success': False, 'error': 'Failed to save customer'}
    
    def update_customer(self, customer_id: str, data: Dict) -> Dict:
        """Update a customer"""
        valid, error = self.validate_customer(data, is_update=True)
        if not valid:
            return {'success': False, 'error': error}
        
        customers = self._load_json(self.customers_file, [])
        idx = next((i for i, c in enumerate(customers) if c['id'] == customer_id), None)
        
        if idx is None:
            return {'success': False, 'error': 'Customer not found'}
        
        # Check for duplicate email (excluding current customer)
        email = data.get('email', '').strip()
        if email:
            existing = next((c for c in customers if c.get('email', '').lower() == email.lower() and c['id'] != customer_id), None)
            if existing:
                return {'success': False, 'error': 'Another customer with this email already exists'}
        
        customer = customers[idx]
        updatable_fields = ['name', 'email', 'phone', 'address', 'company', 'notes', 'status', 'tags']
        for field in updatable_fields:
            if field in data:
                customer[field] = data[field].strip() if isinstance(data[field], str) else data[field]
        
        customer['updated_at'] = datetime.now().isoformat()
        customers[idx] = customer
        
        if self._save_json(self.customers_file, customers):
            return {'success': True, 'customer': customer}
        return {'success': False, 'error': 'Failed to save customer'}
    
    def delete_customer(self, customer_id: str, cascade: bool = False) -> Dict:
        """Delete a customer with optional cascade"""
        customers = self._load_json(self.customers_file, [])
        idx = next((i for i, c in enumerate(customers) if c['id'] == customer_id), None)
        
        if idx is None:
            return {'success': False, 'error': 'Customer not found'}
        
        # Check for related records
        projects = self._load_json(self.projects_file, [])
        quotes = self._load_json(self.quotes_file, [])
        
        related_projects = [p for p in projects if p.get('customer_id') == customer_id]
        related_quotes = [q for q in quotes if q.get('customer_id') == customer_id]
        
        if (related_projects or related_quotes) and not cascade:
            return {
                'success': False,
                'error': 'Customer has related records. Use cascade=true to delete all related data.',
                'related': {
                    'projects': len(related_projects),
                    'quotes': len(related_quotes)
                }
            }
        
        # Cascade delete or unlink
        if cascade:
            # Remove customer_id from related records
            for p in projects:
                if p.get('customer_id') == customer_id:
                    p['customer_id'] = None
                    p['updated_at'] = datetime.now().isoformat()
            for q in quotes:
                if q.get('customer_id') == customer_id:
                    q['customer_id'] = None
                    q['updated_at'] = datetime.now().isoformat()
            
            self._save_json(self.projects_file, projects)
            self._save_json(self.quotes_file, quotes)
        
        deleted_customer = customers.pop(idx)
        
        if self._save_json(self.customers_file, customers):
            return {'success': True, 'deleted': deleted_customer}
        return {'success': False, 'error': 'Failed to delete customer'}
    
    # ==================== PROJECTS ====================
    
    def get_projects(self,
                     customer_id: str = None,
                     status: str = None,
                     search: str = None,
                     page: int = 1,
                     per_page: int = 50,
                     sort_by: str = 'created_at',
                     sort_order: str = 'desc') -> Dict:
        """Get projects with filtering, pagination, and search"""
        projects = self._load_json(self.projects_file, [])
        
        # Filter by customer
        if customer_id:
            projects = [p for p in projects if p.get('customer_id') == customer_id]
        
        # Filter by status
        if status:
            projects = [p for p in projects if p.get('status') == status]
        
        # Search
        if search:
            search_lower = search.lower()
            projects = [p for p in projects if 
                       search_lower in p.get('title', '').lower() or
                       search_lower in p.get('description', '').lower()]
        
        # Sort
        reverse = sort_order == 'desc'
        projects.sort(key=lambda x: x.get(sort_by, ''), reverse=reverse)
        
        # Pagination
        total = len(projects)
        start = (page - 1) * per_page
        end = start + per_page
        paginated = projects[start:end]
        
        # Enrich with customer names
        customers = self._load_json(self.customers_file, [])
        customer_map = {c['id']: c['name'] for c in customers}
        for p in paginated:
            p['customer_name'] = customer_map.get(p.get('customer_id'), 'Unknown')
        
        return {
            'success': True,
            'projects': paginated,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        }
    
    def get_project(self, project_id: str) -> Dict:
        """Get a single project with all related data"""
        projects = self._load_json(self.projects_file, [])
        project = next((p for p in projects if p['id'] == project_id), None)
        
        if not project:
            return {'success': False, 'error': 'Project not found'}
        
        # Get customer
        customers = self._load_json(self.customers_file, [])
        customer = next((c for c in customers if c['id'] == project.get('customer_id')), None)
        
        # Get source quote if exists
        quotes = self._load_json(self.quotes_file, [])
        source_quote = next((q for q in quotes if q['id'] == project.get('source_quote_id')), None)
        
        return {
            'success': True,
            'project': project,
            'customer': customer,
            'source_quote': source_quote
        }
    
    def create_project(self, data: Dict) -> Dict:
        """Create a new project"""
        valid, error = self.validate_project(data)
        if not valid:
            return {'success': False, 'error': error}
        
        # Verify customer exists if provided
        customer_id = data.get('customer_id')
        if customer_id:
            customers = self._load_json(self.customers_file, [])
            if not any(c['id'] == customer_id for c in customers):
                return {'success': False, 'error': 'Customer not found'}
        
        projects = self._load_json(self.projects_file, [])
        
        project = {
            'id': str(uuid.uuid4()),
            'customer_id': customer_id,
            'title': data.get('title', '').strip(),
            'description': data.get('description', '').strip(),
            'status': data.get('status', 'pending'),
            'priority': data.get('priority', 'medium'),
            'quote_amount': float(data.get('quote_amount', 0)),
            'actual_amount': float(data.get('actual_amount', 0)),
            'due_date': data.get('due_date'),
            'start_date': data.get('start_date'),
            'address': data.get('address', '').strip(),
            'notes': data.get('notes', '').strip(),
            'tags': data.get('tags', []),
            'takeoffs_session_id': data.get('takeoffs_session_id'),
            'mapping_session_id': data.get('mapping_session_id'),
            'cad_session_id': data.get('cad_session_id'),
            'board_session_id': data.get('board_session_id'),
            'markups': [],
            'cost_centres': [],
            'room_assignments': [],
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        projects.append(project)
        
        if self._save_json(self.projects_file, projects):
            return {'success': True, 'project': project}
        return {'success': False, 'error': 'Failed to save project'}
    
    def update_project(self, project_id: str, data: Dict) -> Dict:
        """Update a project"""
        valid, error = self.validate_project(data, is_update=True)
        if not valid:
            return {'success': False, 'error': error}
        
        projects = self._load_json(self.projects_file, [])
        idx = next((i for i, p in enumerate(projects) if p['id'] == project_id), None)
        
        if idx is None:
            return {'success': False, 'error': 'Project not found'}
        
        # Verify customer exists if being updated
        if 'customer_id' in data and data['customer_id']:
            customers = self._load_json(self.customers_file, [])
            if not any(c['id'] == data['customer_id'] for c in customers):
                return {'success': False, 'error': 'Customer not found'}
        
        project = projects[idx]
        updatable_fields = [
            'title', 'description', 'status', 'priority', 'quote_amount', 
            'actual_amount', 'due_date', 'start_date', 'address', 'notes', 
            'tags', 'customer_id', 'takeoffs_session_id', 'mapping_session_id',
            'cad_session_id', 'board_session_id'
        ]
        
        for field in updatable_fields:
            if field in data:
                value = data[field]
                if isinstance(value, str):
                    project[field] = value.strip()
                elif field in ['quote_amount', 'actual_amount']:
                    project[field] = float(value) if value else 0
                else:
                    project[field] = value
        
        project['updated_at'] = datetime.now().isoformat()
        projects[idx] = project
        
        if self._save_json(self.projects_file, projects):
            return {'success': True, 'project': project}
        return {'success': False, 'error': 'Failed to save project'}
    
    def delete_project(self, project_id: str) -> Dict:
        """Delete a project"""
        projects = self._load_json(self.projects_file, [])
        idx = next((i for i, p in enumerate(projects) if p['id'] == project_id), None)
        
        if idx is None:
            return {'success': False, 'error': 'Project not found'}
        
        deleted_project = projects.pop(idx)
        
        if self._save_json(self.projects_file, projects):
            return {'success': True, 'deleted': deleted_project}
        return {'success': False, 'error': 'Failed to delete project'}
    
    # ==================== QUOTES ====================
    
    def get_quotes(self,
                   customer_id: str = None,
                   status: str = None,
                   search: str = None,
                   page: int = 1,
                   per_page: int = 50,
                   sort_by: str = 'created_at',
                   sort_order: str = 'desc') -> Dict:
        """Get quotes with filtering, pagination, and search"""
        quotes = self._load_json(self.quotes_file, [])
        
        # Filter by customer
        if customer_id:
            quotes = [q for q in quotes if q.get('customer_id') == customer_id]
        
        # Filter by status
        if status:
            quotes = [q for q in quotes if q.get('status') == status]
        
        # Search
        if search:
            search_lower = search.lower()
            quotes = [q for q in quotes if 
                     search_lower in q.get('title', '').lower() or
                     search_lower in q.get('description', '').lower() or
                     search_lower in q.get('quote_number', '').lower()]
        
        # Sort
        reverse = sort_order == 'desc'
        quotes.sort(key=lambda x: x.get(sort_by, ''), reverse=reverse)
        
        # Pagination
        total = len(quotes)
        start = (page - 1) * per_page
        end = start + per_page
        paginated = quotes[start:end]
        
        # Enrich with customer names
        customers = self._load_json(self.customers_file, [])
        customer_map = {c['id']: c['name'] for c in customers}
        for q in paginated:
            q['customer_name'] = customer_map.get(q.get('customer_id'), 'Unknown')
        
        return {
            'success': True,
            'quotes': paginated,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        }
    
    def get_quote(self, quote_id: str) -> Dict:
        """Get a single quote with all related data"""
        quotes = self._load_json(self.quotes_file, [])
        quote = next((q for q in quotes if q['id'] == quote_id), None)
        
        if not quote:
            return {'success': False, 'error': 'Quote not found'}
        
        # Get customer
        customers = self._load_json(self.customers_file, [])
        customer = next((c for c in customers if c['id'] == quote.get('customer_id')), None)
        
        # Get converted project if exists
        projects = self._load_json(self.projects_file, [])
        converted_project = next((p for p in projects if p['id'] == quote.get('converted_to_project_id')), None)
        
        return {
            'success': True,
            'quote': quote,
            'customer': customer,
            'converted_project': converted_project
        }
    
    def create_quote(self, data: Dict) -> Dict:
        """Create a new quote"""
        valid, error = self.validate_quote(data)
        if not valid:
            return {'success': False, 'error': error}
        
        # Verify customer exists if provided
        customer_id = data.get('customer_id')
        if customer_id:
            customers = self._load_json(self.customers_file, [])
            if not any(c['id'] == customer_id for c in customers):
                return {'success': False, 'error': 'Customer not found'}
        
        quotes = self._load_json(self.quotes_file, [])
        
        quote = {
            'id': str(uuid.uuid4()),
            'quote_number': data.get('quote_number', f"Q-{datetime.now().strftime('%Y%m%d%H%M%S')}"),
            'customer_id': customer_id,
            'title': data.get('title', '').strip(),
            'description': data.get('description', '').strip(),
            'status': data.get('status', 'draft'),
            'quote_amount': float(data.get('quote_amount', 0)),
            'labor_cost': float(data.get('labor_cost', 0)),
            'materials_cost': float(data.get('materials_cost', 0)),
            'markup_percentage': float(data.get('markup_percentage', 20)),
            'valid_until': data.get('valid_until'),
            'notes': data.get('notes', '').strip(),
            'terms': data.get('terms', '').strip(),
            # Linked sessions
            'takeoffs_session_id': data.get('takeoffs_session_id'),
            'mapping_session_id': data.get('mapping_session_id'),
            'cad_session_id': data.get('cad_session_id'),
            'board_session_id': data.get('board_session_id'),
            # Canvas state for quote automation
            'canvas_state': data.get('canvas_state'),
            'floorplan_image': data.get('floorplan_image'),
            'analysis': data.get('analysis'),
            'components': data.get('components', []),
            'costs': data.get('costs'),
            # Items
            'markups': [],
            'stock_items': data.get('stock_items', []),
            'labour_items': data.get('labour_items', []),
            'cost_centres': data.get('cost_centres', []),
            # Metadata
            'source': data.get('source', 'manual'),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        quotes.append(quote)
        
        if self._save_json(self.quotes_file, quotes):
            return {'success': True, 'quote': quote}
        return {'success': False, 'error': 'Failed to save quote'}
    
    def update_quote(self, quote_id: str, data: Dict) -> Dict:
        """Update a quote"""
        valid, error = self.validate_quote(data, is_update=True)
        if not valid:
            return {'success': False, 'error': error}
        
        quotes = self._load_json(self.quotes_file, [])
        idx = next((i for i, q in enumerate(quotes) if q['id'] == quote_id), None)
        
        if idx is None:
            return {'success': False, 'error': 'Quote not found'}
        
        quote = quotes[idx]
        updatable_fields = [
            'title', 'description', 'status', 'quote_amount', 'labor_cost',
            'materials_cost', 'markup_percentage', 'valid_until', 'notes',
            'terms', 'customer_id', 'takeoffs_session_id', 'mapping_session_id',
            'cad_session_id', 'board_session_id', 'quote_number', 'canvas_state',
            'floorplan_image', 'analysis', 'components', 'costs', 'stock_items',
            'labour_items', 'cost_centres'
        ]
        
        for field in updatable_fields:
            if field in data:
                value = data[field]
                if isinstance(value, str):
                    quote[field] = value.strip()
                elif field in ['quote_amount', 'labor_cost', 'materials_cost', 'markup_percentage']:
                    quote[field] = float(value) if value else 0
                else:
                    quote[field] = value
        
        quote['updated_at'] = datetime.now().isoformat()
        quotes[idx] = quote
        
        if self._save_json(self.quotes_file, quotes):
            return {'success': True, 'quote': quote}
        return {'success': False, 'error': 'Failed to save quote'}
    
    def delete_quote(self, quote_id: str) -> Dict:
        """Delete a quote"""
        quotes = self._load_json(self.quotes_file, [])
        idx = next((i for i, q in enumerate(quotes) if q['id'] == quote_id), None)
        
        if idx is None:
            return {'success': False, 'error': 'Quote not found'}
        
        deleted_quote = quotes.pop(idx)
        
        if self._save_json(self.quotes_file, quotes):
            return {'success': True, 'deleted': deleted_quote}
        return {'success': False, 'error': 'Failed to delete quote'}
    
    def convert_quote_to_project(self, quote_id: str) -> Dict:
        """Convert an accepted quote into a project"""
        quotes = self._load_json(self.quotes_file, [])
        quote_idx = next((i for i, q in enumerate(quotes) if q['id'] == quote_id), None)
        
        if quote_idx is None:
            return {'success': False, 'error': 'Quote not found'}
        
        quote = quotes[quote_idx]
        
        # Check if already converted
        if quote.get('converted_to_project_id'):
            return {'success': False, 'error': 'Quote has already been converted to a project'}
        
        # Create project from quote
        projects = self._load_json(self.projects_file, [])
        
        project = {
            'id': str(uuid.uuid4()),
            'customer_id': quote.get('customer_id'),
            'title': quote.get('title', 'Converted from Quote'),
            'description': f"Converted from Quote {quote.get('quote_number', quote_id)}\n\n{quote.get('description', '')}",
            'status': 'pending',
            'priority': 'medium',
            'quote_amount': quote.get('quote_amount', 0),
            'actual_amount': 0,
            'due_date': None,
            'start_date': None,
            'address': '',
            'notes': quote.get('notes', ''),
            'tags': [],
            'takeoffs_session_id': quote.get('takeoffs_session_id'),
            'mapping_session_id': quote.get('mapping_session_id'),
            'cad_session_id': quote.get('cad_session_id'),
            'board_session_id': quote.get('board_session_id'),
            'markups': quote.get('markups', []).copy(),
            'cost_centres': quote.get('cost_centres', []).copy(),
            'room_assignments': [],
            'source_quote_id': quote_id,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        projects.append(project)
        
        # Update quote status
        quote['status'] = 'accepted'
        quote['converted_to_project_id'] = project['id']
        quote['converted_at'] = datetime.now().isoformat()
        quote['updated_at'] = datetime.now().isoformat()
        quotes[quote_idx] = quote
        
        if self._save_json(self.projects_file, projects) and self._save_json(self.quotes_file, quotes):
            return {
                'success': True,
                'project': project,
                'quote': quote,
                'message': 'Quote converted to project successfully'
            }
        return {'success': False, 'error': 'Failed to save conversion'}
    
    # ==================== STOCK ====================
    
    def get_stock(self,
                  category: str = None,
                  search: str = None,
                  low_stock_only: bool = False,
                  page: int = 1,
                  per_page: int = 50,
                  sort_by: str = 'name',
                  sort_order: str = 'asc') -> Dict:
        """Get stock items with filtering, pagination, and search"""
        stock = self._load_json(self.stock_file, [])
        
        # Filter by category
        if category:
            stock = [s for s in stock if s.get('category') == category]
        
        # Filter low stock
        if low_stock_only:
            stock = [s for s in stock if s.get('quantity', 0) <= s.get('reorder_level', 5)]
        
        # Search
        if search:
            search_lower = search.lower()
            stock = [s for s in stock if 
                    search_lower in s.get('name', '').lower() or
                    search_lower in s.get('sku', '').lower() or
                    search_lower in s.get('description', '').lower()]
        
        # Sort
        reverse = sort_order == 'desc'
        stock.sort(key=lambda x: x.get(sort_by, ''), reverse=reverse)
        
        # Pagination
        total = len(stock)
        start = (page - 1) * per_page
        end = start + per_page
        paginated = stock[start:end]
        
        # Calculate totals
        total_value = sum(s.get('quantity', 0) * s.get('unit_price', 0) for s in stock)
        total_items = sum(s.get('quantity', 0) for s in stock)
        
        return {
            'success': True,
            'stock': paginated,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            },
            'summary': {
                'total_value': total_value,
                'total_items': total_items,
                'unique_products': len(stock)
            }
        }
    
    def get_stock_item(self, item_id: str) -> Dict:
        """Get a single stock item"""
        stock = self._load_json(self.stock_file, [])
        item = next((s for s in stock if s['id'] == item_id), None)
        
        if not item:
            return {'success': False, 'error': 'Stock item not found'}
        
        return {'success': True, 'item': item}
    
    def create_stock_item(self, data: Dict) -> Dict:
        """Create a new stock item"""
        valid, error = self.validate_stock_item(data)
        if not valid:
            return {'success': False, 'error': error}
        
        stock = self._load_json(self.stock_file, [])
        
        item = {
            'id': str(uuid.uuid4()),
            'name': data.get('name', '').strip(),
            'sku': data.get('sku', '').strip(),
            'description': data.get('description', '').strip(),
            'category': data.get('category', 'general'),
            'type': data.get('type', 'component'),
            'quantity': int(data.get('quantity', 0)),
            'unit_price': float(data.get('unit_price', 0)),
            'cost': float(data.get('cost', 0)),
            'reorder_level': int(data.get('reorder_level', 5)),
            'supplier': data.get('supplier', '').strip(),
            'location': data.get('location', '').strip(),
            'notes': data.get('notes', '').strip(),
            'specifications': data.get('specifications', {}),
            'serial_numbers': data.get('serial_numbers', []),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        stock.append(item)
        
        if self._save_json(self.stock_file, stock):
            return {'success': True, 'item': item}
        return {'success': False, 'error': 'Failed to save stock item'}
    
    def update_stock_item(self, item_id: str, data: Dict) -> Dict:
        """Update a stock item"""
        valid, error = self.validate_stock_item(data, is_update=True)
        if not valid:
            return {'success': False, 'error': error}
        
        stock = self._load_json(self.stock_file, [])
        idx = next((i for i, s in enumerate(stock) if s['id'] == item_id), None)
        
        if idx is None:
            return {'success': False, 'error': 'Stock item not found'}
        
        item = stock[idx]
        updatable_fields = [
            'name', 'sku', 'description', 'category', 'type', 'quantity',
            'unit_price', 'cost', 'reorder_level', 'supplier', 'location',
            'notes', 'specifications', 'serial_numbers'
        ]
        
        for field in updatable_fields:
            if field in data:
                value = data[field]
                if isinstance(value, str):
                    item[field] = value.strip()
                elif field == 'quantity':
                    item[field] = int(value)
                elif field in ['unit_price', 'cost']:
                    item[field] = float(value)
                else:
                    item[field] = value
        
        item['updated_at'] = datetime.now().isoformat()
        stock[idx] = item
        
        if self._save_json(self.stock_file, stock):
            return {'success': True, 'item': item}
        return {'success': False, 'error': 'Failed to save stock item'}
    
    def delete_stock_item(self, item_id: str) -> Dict:
        """Delete a stock item"""
        stock = self._load_json(self.stock_file, [])
        idx = next((i for i, s in enumerate(stock) if s['id'] == item_id), None)
        
        if idx is None:
            return {'success': False, 'error': 'Stock item not found'}
        
        deleted_item = stock.pop(idx)
        
        if self._save_json(self.stock_file, stock):
            return {'success': True, 'deleted': deleted_item}
        return {'success': False, 'error': 'Failed to delete stock item'}
    
    def adjust_stock_quantity(self, item_id: str, adjustment: int, reason: str = '') -> Dict:
        """Adjust stock quantity (positive or negative)"""
        stock = self._load_json(self.stock_file, [])
        idx = next((i for i, s in enumerate(stock) if s['id'] == item_id), None)
        
        if idx is None:
            return {'success': False, 'error': 'Stock item not found'}
        
        item = stock[idx]
        new_quantity = item.get('quantity', 0) + adjustment
        
        if new_quantity < 0:
            return {'success': False, 'error': 'Adjustment would result in negative stock'}
        
        item['quantity'] = new_quantity
        item['updated_at'] = datetime.now().isoformat()
        
        # Log adjustment
        if 'adjustments' not in item:
            item['adjustments'] = []
        item['adjustments'].append({
            'amount': adjustment,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
        
        stock[idx] = item
        
        if self._save_json(self.stock_file, stock):
            return {'success': True, 'item': item, 'new_quantity': new_quantity}
        return {'success': False, 'error': 'Failed to save stock adjustment'}
    
    # ==================== STATISTICS ====================
    
    def get_stats(self) -> Dict:
        """Get comprehensive CRM statistics"""
        customers = self._load_json(self.customers_file, [])
        projects = self._load_json(self.projects_file, [])
        quotes = self._load_json(self.quotes_file, [])
        stock = self._load_json(self.stock_file, [])
        
        # Customer stats
        total_customers = len(customers)
        active_customers = len([c for c in customers if c.get('status') == 'active'])
        
        # Project stats
        total_projects = len(projects)
        active_projects = len([p for p in projects if p.get('status') in ['pending', 'in_progress', 'planning']])
        completed_projects = len([p for p in projects if p.get('status') == 'completed'])
        on_hold_projects = len([p for p in projects if p.get('status') == 'on_hold'])
        
        # Revenue stats
        total_revenue = sum(p.get('actual_amount', 0) for p in projects if p.get('status') == 'completed')
        pending_revenue = sum(p.get('quote_amount', 0) for p in projects if p.get('status') in ['pending', 'in_progress', 'planning'])
        
        # Quote stats
        total_quotes = len(quotes)
        draft_quotes = len([q for q in quotes if q.get('status') == 'draft'])
        sent_quotes = len([q for q in quotes if q.get('status') == 'sent'])
        accepted_quotes = len([q for q in quotes if q.get('status') == 'accepted'])
        rejected_quotes = len([q for q in quotes if q.get('status') == 'rejected'])
        quote_value = sum(q.get('quote_amount', 0) for q in quotes if q.get('status') in ['draft', 'sent'])
        
        # Stock stats
        total_stock_value = sum(s.get('quantity', 0) * s.get('unit_price', 0) for s in stock)
        total_stock_items = len(stock)
        total_stock_units = sum(s.get('quantity', 0) for s in stock)
        low_stock_items = len([s for s in stock if s.get('quantity', 0) <= s.get('reorder_level', 5)])
        
        return {
            'success': True,
            'stats': {
                'customers': {
                    'total': total_customers,
                    'active': active_customers,
                    'inactive': total_customers - active_customers
                },
                'projects': {
                    'total': total_projects,
                    'active': active_projects,
                    'completed': completed_projects,
                    'on_hold': on_hold_projects
                },
                'quotes': {
                    'total': total_quotes,
                    'draft': draft_quotes,
                    'sent': sent_quotes,
                    'accepted': accepted_quotes,
                    'rejected': rejected_quotes,
                    'pending_value': quote_value
                },
                'revenue': {
                    'total': total_revenue,
                    'pending': pending_revenue,
                    'average_project': total_revenue / completed_projects if completed_projects > 0 else 0
                },
                'stock': {
                    'total_value': total_stock_value,
                    'total_items': total_stock_items,
                    'total_units': total_stock_units,
                    'low_stock': low_stock_items
                }
            }
        }
    
    # ==================== DATA INTEGRITY ====================
    
    def check_data_integrity(self) -> Dict:
        """Check data integrity across all CRM files"""
        issues = []
        
        customers = self._load_json(self.customers_file, [])
        projects = self._load_json(self.projects_file, [])
        quotes = self._load_json(self.quotes_file, [])
        stock = self._load_json(self.stock_file, [])
        
        customer_ids = {c['id'] for c in customers}
        project_ids = {p['id'] for p in projects}
        quote_ids = {q['id'] for q in quotes}
        
        # Check project customer references
        for project in projects:
            if project.get('customer_id') and project['customer_id'] not in customer_ids:
                issues.append({
                    'type': 'orphan_reference',
                    'entity': 'project',
                    'id': project['id'],
                    'field': 'customer_id',
                    'value': project['customer_id'],
                    'message': f"Project '{project.get('title')}' references non-existent customer"
                })
        
        # Check quote customer references
        for quote in quotes:
            if quote.get('customer_id') and quote['customer_id'] not in customer_ids:
                issues.append({
                    'type': 'orphan_reference',
                    'entity': 'quote',
                    'id': quote['id'],
                    'field': 'customer_id',
                    'value': quote['customer_id'],
                    'message': f"Quote '{quote.get('title')}' references non-existent customer"
                })
            
            # Check converted project reference
            if quote.get('converted_to_project_id') and quote['converted_to_project_id'] not in project_ids:
                issues.append({
                    'type': 'orphan_reference',
                    'entity': 'quote',
                    'id': quote['id'],
                    'field': 'converted_to_project_id',
                    'value': quote['converted_to_project_id'],
                    'message': f"Quote '{quote.get('title')}' references non-existent project"
                })
        
        # Check project source quote references
        for project in projects:
            if project.get('source_quote_id') and project['source_quote_id'] not in quote_ids:
                issues.append({
                    'type': 'orphan_reference',
                    'entity': 'project',
                    'id': project['id'],
                    'field': 'source_quote_id',
                    'value': project['source_quote_id'],
                    'message': f"Project '{project.get('title')}' references non-existent source quote"
                })
        
        # Check for duplicate IDs
        for name, items in [('customers', customers), ('projects', projects), ('quotes', quotes), ('stock', stock)]:
            ids = [item['id'] for item in items]
            duplicates = [id for id in ids if ids.count(id) > 1]
            if duplicates:
                issues.append({
                    'type': 'duplicate_id',
                    'entity': name,
                    'ids': list(set(duplicates)),
                    'message': f"Duplicate IDs found in {name}"
                })
        
        return {
            'success': True,
            'healthy': len(issues) == 0,
            'issues': issues,
            'counts': {
                'customers': len(customers),
                'projects': len(projects),
                'quotes': len(quotes),
                'stock': len(stock)
            }
        }
    
    def repair_data_integrity(self) -> Dict:
        """Attempt to repair data integrity issues"""
        integrity = self.check_data_integrity()
        repaired = []
        
        if integrity['healthy']:
            return {'success': True, 'message': 'No issues to repair', 'repaired': []}
        
        projects = self._load_json(self.projects_file, [])
        quotes = self._load_json(self.quotes_file, [])
        
        for issue in integrity['issues']:
            if issue['type'] == 'orphan_reference':
                if issue['entity'] == 'project':
                    for p in projects:
                        if p['id'] == issue['id']:
                            p[issue['field']] = None
                            p['updated_at'] = datetime.now().isoformat()
                            repaired.append(f"Cleared {issue['field']} in project {issue['id']}")
                elif issue['entity'] == 'quote':
                    for q in quotes:
                        if q['id'] == issue['id']:
                            q[issue['field']] = None
                            q['updated_at'] = datetime.now().isoformat()
                            repaired.append(f"Cleared {issue['field']} in quote {issue['id']}")
        
        self._save_json(self.projects_file, projects)
        self._save_json(self.quotes_file, quotes)
        
        return {
            'success': True,
            'repaired': repaired,
            'message': f"Repaired {len(repaired)} issues"
        }


# Singleton instance for use across the app
_crm_data_layer = None

def get_crm_data_layer(data_folder: str = None) -> CRMDataLayer:
    """Get or create the CRM data layer singleton"""
    global _crm_data_layer
    if _crm_data_layer is None:
        if data_folder is None:
            raise ValueError("data_folder must be provided on first call")
        _crm_data_layer = CRMDataLayer(data_folder)
    return _crm_data_layer

