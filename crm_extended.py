"""
CRM Extended Module
Handles People, Jobs, Materials, Payments, and Schedules

STORAGE POLICY:
- Production: DATABASE_URL is REQUIRED. JSON persistence is disabled.
- Development: Database preferred, JSON fallback allowed if no DATABASE_URL.
"""
import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# ====================================================================================
# STORAGE POLICY HELPERS
# ====================================================================================

def _use_database():
    """Check if database should be used."""
    from config import has_database
    return has_database()


def _use_json_fallback():
    """Check if JSON fallback is allowed."""
    from config import allow_json_persistence
    return allow_json_persistence()


def _get_crm_data_folder():
    """Get CRM data folder path."""
    return os.environ.get('CRM_DATA_FOLDER', 'crm_data')


def _load_json_file(filename, default=None):
    """Load JSON file with storage policy check."""
    from config import is_production, StoragePolicyError
    
    if is_production() and not _use_database():
        raise StoragePolicyError("JSON persistence is disabled in production.")
    
    if default is None:
        default = []
    filepath = os.path.join(_get_crm_data_folder(), filename)
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                data = json.load(f)
                # Handle nested dict formats (e.g., {"people": [...], "jobs": [...]})
                if isinstance(data, dict):
                    # Try to extract the list from common key patterns
                    key = filename.replace('.json', '')  # e.g., 'people' from 'people.json'
                    if key in data:
                        return data[key]
                    # Fallback: return first list value found
                    for v in data.values():
                        if isinstance(v, list):
                            return v
                return data
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
    return default


def _save_json_file(filename, data):
    """Save JSON file with storage policy check."""
    from config import is_production, StoragePolicyError
    
    if is_production() and not _use_database():
        raise StoragePolicyError("JSON persistence is disabled in production.")
    
    folder = _get_crm_data_folder()
    try:
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, filename)
        # Wrap list data in a dict for consistency with existing file formats
        key = filename.replace('.json', '')  # e.g., 'people' from 'people.json'
        wrapped_data = {key: data} if isinstance(data, list) else data
        with open(filepath, 'w') as f:
            json.dump(wrapped_data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving {filename}: {e}")
        return False


# ====================================================================================
# DATABASE LAYER ACCESS
# ====================================================================================

def _get_db_components():
    """Get database components for operations"""
    if not _use_database():
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


def _get_db_layer():
    """Get the CRM database layer instance"""
    if not _use_database():
        return None
    try:
        from crm_db_layer import CRMDatabaseLayer
        from database.seed import get_default_organization_id
        org_id = get_default_organization_id()
        return CRMDatabaseLayer(org_id)
    except Exception as e:
        logger.error(f"Failed to get database layer: {e}")
        return None


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
    """Load people - uses database if available, JSON fallback in dev"""
    get_db_session, org_id, CRMRepository, _ = _get_db_components()
    
    if get_db_session:
        # Use database
        try:
            from database.models import Customer
            
            with get_db_session() as session:
                customers = session.query(Customer).filter(
                    Customer.organization_id == org_id,
                    Customer.is_active == True
                ).all()
                
                people = []
                for c in customers:
                    person = c.to_dict()
                    person['type'] = (c.extra_data or {}).get('person_type', 'contact')
                    person['linked_jobs'] = (c.extra_data or {}).get('linked_jobs', [])
                    person['linked_quotes'] = (c.extra_data or {}).get('linked_quotes', [])
                    
                    if person_type and person['type'] != person_type:
                        continue
                    people.append(person)
                
                return people
        except Exception as e:
            logger.error(f"Error loading people from database: {e}")
            return []
    elif _use_json_fallback():
        # JSON fallback for local dev
        people = _load_json_file('people.json', [])
        if person_type:
            people = [p for p in people if p.get('type') == person_type]
        return people
    else:
        logger.error("No storage available for loading people")
        return []


def save_people(people) -> bool:
    """Save people to DATABASE - deprecated, use create/update methods instead"""
    logger.warning("save_people is deprecated - use create_person/update_person instead")
    return True


def get_person(person_id: str) -> Optional[Dict]:
    """Get a single person by ID - uses database if available, JSON fallback in dev"""
    get_db_session, org_id, _, _ = _get_db_components()
    
    if get_db_session:
        # Use database
        try:
            from database.models import Customer
            
            with get_db_session() as session:
                customer = session.query(Customer).filter(
                    Customer.id == person_id,
                    Customer.organization_id == org_id
                ).first()
                
                if customer:
                    person = customer.to_dict()
                    person['type'] = (customer.extra_data or {}).get('person_type', 'contact')
                    person['linked_jobs'] = (customer.extra_data or {}).get('linked_jobs', [])
                    person['linked_quotes'] = (customer.extra_data or {}).get('linked_quotes', [])
                    return person
                return None
        except Exception as e:
            logger.error(f"Error getting person {person_id}: {e}")
            return None
    elif _use_json_fallback():
        # JSON fallback for local dev
        people = _load_json_file('people.json', [])
        return next((p for p in people if p.get('id') == person_id), None)
    else:
        return None


def create_person(data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Create a new person - uses database if available, JSON fallback in dev"""
    get_db_session, org_id, CRMRepository, _ = _get_db_components()
    
    if get_db_session:
        # Use database
        try:
            with get_db_session() as session:
                repo = CRMRepository(session, org_id)
                
                customer_data = {
                    'name': data.get('name', ''),
                    'company': data.get('company', ''),
                    'email': data.get('email', ''),
                    'phone': data.get('phone', ''),
                    'address': data.get('address', ''),
                    'notes': data.get('notes', ''),
                    'metadata': {
                        'person_type': data.get('type', 'contact'),
                        'title': data.get('title', ''),
                        'linked_to': data.get('linked_to'),
                        'linked_jobs': data.get('linked_jobs', []),
                        'linked_quotes': data.get('linked_quotes', []),
                        'floorplans': data.get('floorplans', []),
                        'documents': data.get('documents', [])
                    }
                }
                
                person = repo.create_customer(customer_data)
                person['type'] = data.get('type', 'contact')
                person['title'] = data.get('title', '')
                person['linked_to'] = data.get('linked_to')
                person['linked_jobs'] = []
                person['linked_quotes'] = []
                person['floorplans'] = data.get('floorplans', [])
                person['documents'] = data.get('documents', [])
                session.commit()
                
                return person, None
        except Exception as e:
            logger.error(f"Error creating person: {e}")
            return None, str(e)
    elif _use_json_fallback():
        # JSON fallback for local dev
        people = _load_json_file('people.json', [])
        person = {
            'id': str(uuid.uuid4()),
            'name': data.get('name', ''),
            'title': data.get('title', ''),
            'company': data.get('company', ''),
            'email': data.get('email', ''),
            'phone': data.get('phone', ''),
            'address': data.get('address', ''),
            'notes': data.get('notes', ''),
            'type': data.get('type', 'contact'),
            'linked_to': data.get('linked_to'),
            'linked_jobs': [],
            'linked_quotes': [],
            'floorplans': data.get('floorplans', []),
            'documents': data.get('documents', []),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        people.append(person)
        _save_json_file('people.json', people)
        return person, None
    else:
        return None, "No storage available"


def update_person(person_id: str, data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Update a person - uses database if available, JSON fallback in dev"""
    get_db_session, org_id, _, _ = _get_db_components()
    
    if get_db_session:
        # Use database
        try:
            from database.models import Customer
            
            with get_db_session() as session:
                customer = session.query(Customer).filter(
                    Customer.id == person_id,
                    Customer.organization_id == org_id
                ).first()
                
                if not customer:
                    return None, "Person not found"
                
                for key in ['name', 'company', 'email', 'phone', 'address', 'notes']:
                    if key in data:
                        setattr(customer, key, data[key])
                
                if 'type' in data:
                    if not customer.extra_data:
                        customer.extra_data = {}
                    customer.extra_data['person_type'] = data['type']
                
                customer.updated_at = datetime.utcnow()
                session.commit()
                
                person = customer.to_dict()
                person['type'] = (customer.extra_data or {}).get('person_type', 'contact')
                person['linked_jobs'] = (customer.extra_data or {}).get('linked_jobs', [])
                person['linked_quotes'] = (customer.extra_data or {}).get('linked_quotes', [])
                
                return person, None
        except Exception as e:
            logger.error(f"Error updating person {person_id}: {e}")
            return None, str(e)
    elif _use_json_fallback():
        # JSON fallback for local dev
        people = _load_json_file('people.json', [])
        idx = next((i for i, p in enumerate(people) if p.get('id') == person_id), None)
        if idx is None:
            return None, "Person not found"
        person = people[idx]
        for key in ['name', 'title', 'company', 'email', 'phone', 'address', 'notes', 'type', 'linked_to', 'floorplans', 'documents']:
            if key in data:
                person[key] = data[key]
        person['updated_at'] = datetime.now().isoformat()
        people[idx] = person
        _save_json_file('people.json', people)
        return person, None
    else:
        return None, "No storage available"


def delete_person(person_id: str) -> Tuple[bool, Optional[str]]:
    """Delete a person - uses database if available, JSON fallback in dev"""
    get_db_session, org_id, _, _ = _get_db_components()
    
    if get_db_session:
        # Use database (soft delete)
        try:
            from database.models import Customer
            
            with get_db_session() as session:
                customer = session.query(Customer).filter(
                    Customer.id == person_id,
                    Customer.organization_id == org_id
                ).first()
                
                if not customer:
                    return False, "Person not found"
                
                customer.is_active = False
                customer.updated_at = datetime.utcnow()
                session.commit()
                
                return True, None
        except Exception as e:
            logger.error(f"Error deleting person {person_id}: {e}")
            return False, str(e)
    elif _use_json_fallback():
        # JSON fallback for local dev
        people = _load_json_file('people.json', [])
        idx = next((i for i, p in enumerate(people) if p.get('id') == person_id), None)
        if idx is None:
            return False, "Person not found"
        people.pop(idx)
        _save_json_file('people.json', people)
        return True, None
    else:
        return False, "No storage available"


# ====================================================================================
# JOBS MODULE
# ====================================================================================

JOB_STATUSES = {
    'in_progress': 'In Progress',
    'upcoming': 'Upcoming',
    'pending': 'Pending',
    'finished': 'Finished',
    'recurring': 'Recurring'
}


def load_jobs(status=None) -> List[Dict]:
    """Load jobs - uses database if available, JSON fallback in dev"""
    db_layer = _get_db_layer()
    
    if db_layer and db_layer.db_enabled:
        # Use database
        try:
            result = db_layer.get_jobs(status=status)
            jobs = result.get('jobs', [])
            
            # Map title to name for backwards compatibility
            for job in jobs:
                if 'title' in job and 'name' not in job:
                    job['name'] = job['title']
            
            return jobs
        except Exception as e:
            logger.error(f"Error loading jobs from database: {e}")
            return []
    elif _use_json_fallback():
        # JSON fallback for local dev
        jobs = _load_json_file('jobs.json', [])
        if status:
            jobs = [j for j in jobs if j.get('status') == status]
        return jobs
    else:
        logger.error("No storage available for loading jobs")
        return []


def save_jobs(jobs) -> bool:
    """Save jobs - deprecated, use create/update methods instead"""
    logger.warning("save_jobs is deprecated - use create_job/update_job instead")
    return True


def get_job(job_id: str) -> Optional[Dict]:
    """Get a single job by ID - uses database if available, JSON fallback in dev"""
    db_layer = _get_db_layer()
    
    if db_layer and db_layer.db_enabled:
        # Use database
        try:
            result = db_layer.get_job(job_id)
            if result.get('success'):
                job = result.get('job')
                if job and 'title' in job and 'name' not in job:
                    job['name'] = job['title']
                return job
            return None
        except Exception as e:
            logger.error(f"Error getting job {job_id}: {e}")
            return None
    elif _use_json_fallback():
        # JSON fallback for local dev
        jobs = _load_json_file('jobs.json', [])
        return next((j for j in jobs if j.get('id') == job_id), None)
    else:
        return None


def create_job(data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Create a new job - uses database if available, JSON fallback in dev"""
    db_layer = _get_db_layer()
    
    if db_layer and db_layer.db_enabled:
        # Use database
        try:
            # Map 'name' to 'title' for database
            if 'name' in data and 'title' not in data:
                data['title'] = data['name']
            
            # Map additional fields
            job_data = {
                'title': data.get('title', data.get('name', '')),
                'description': data.get('description', ''),
                'status': data.get('status', 'pending'),
                'priority': data.get('priority', 'normal'),
                'metadata': {
                    'customer_id': data.get('customer_id', ''),
                    'value': float(data.get('value', 0)),
                    'materials': data.get('materials', []),
                    'payments': data.get('payments', []),
                    'assigned_to': data.get('assigned_to', []),
                    'recurring_schedule': data.get('recurring_schedule', '')
                }
            }
            
            if data.get('start_date'):
                job_data['scheduled_date'] = data['start_date']
            if data.get('due_date'):
                job_data['metadata']['due_date'] = data['due_date']
            
            result = db_layer.create_job(job_data)
            
            if result.get('success'):
                job = result.get('job')
                job['name'] = job.get('title', '')
                return job, None
            return None, result.get('error', 'Failed to create job')
        except Exception as e:
            logger.error(f"Error creating job: {e}")
            return None, str(e)
    elif _use_json_fallback():
        # JSON fallback for local dev
        jobs = _load_json_file('jobs.json', [])
        job = {
            'id': str(uuid.uuid4()),
            'name': data.get('name', data.get('title', '')),
            'title': data.get('title', data.get('name', '')),
            'description': data.get('description', ''),
            'status': data.get('status', 'pending'),
            'priority': data.get('priority', 'normal'),
            'customer_id': data.get('customer_id', ''),
            'value': float(data.get('value', 0)),
            'start_date': data.get('start_date'),
            'due_date': data.get('due_date'),
            'materials': data.get('materials', []),
            'payments': data.get('payments', []),
            'assigned_to': data.get('assigned_to', []),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        jobs.append(job)
        _save_json_file('jobs.json', jobs)
        return job, None
    else:
        return None, "No storage available"


def update_job(job_id: str, data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Update a job - uses database if available, JSON fallback in dev"""
    db_layer = _get_db_layer()
    
    if db_layer and db_layer.db_enabled:
        # Use database
        try:
            # Map 'name' to 'title' for database
            if 'name' in data and 'title' not in data:
                data['title'] = data['name']
            
            result = db_layer.update_job(job_id, data)
            
            if result.get('success'):
                job = result.get('job')
                if job:
                    job['name'] = job.get('title', '')
                return job, None
            return None, result.get('error', 'Failed to update job')
        except Exception as e:
            logger.error(f"Error updating job {job_id}: {e}")
            return None, str(e)
    elif _use_json_fallback():
        # JSON fallback for local dev
        jobs = _load_json_file('jobs.json', [])
        idx = next((i for i, j in enumerate(jobs) if j.get('id') == job_id), None)
        if idx is None:
            return None, "Job not found"
        job = jobs[idx]
        for key in ['name', 'title', 'description', 'status', 'priority', 'customer_id', 'value', 'start_date', 'due_date', 'materials', 'payments', 'assigned_to']:
            if key in data:
                job[key] = data[key]
        job['updated_at'] = datetime.now().isoformat()
        jobs[idx] = job
        _save_json_file('jobs.json', jobs)
        return job, None
    else:
        return None, "No storage available"


def delete_job(job_id: str) -> Tuple[bool, Optional[str]]:
    """Delete a job - uses database if available, JSON fallback in dev"""
    db_layer = _get_db_layer()
    
    if db_layer and db_layer.db_enabled:
        # Use database
        try:
            result = db_layer.delete_job(job_id)
            if result.get('success'):
                return True, None
            return False, result.get('error', 'Failed to delete job')
        except Exception as e:
            logger.error(f"Error deleting job {job_id}: {e}")
            return False, str(e)
    elif _use_json_fallback():
        # JSON fallback for local dev
        jobs = _load_json_file('jobs.json', [])
        idx = next((i for i, j in enumerate(jobs) if j.get('id') == job_id), None)
        if idx is None:
            return False, "Job not found"
        jobs.pop(idx)
        _save_json_file('jobs.json', jobs)
        return True, None
    else:
        return False, "No storage available"


# ====================================================================================
# MATERIALS MODULE
# ====================================================================================

MATERIAL_LOCATIONS = ['sydney', 'melbourne']
MATERIAL_TYPES = ['stock', 'order']


def load_materials(mat_type=None, location=None) -> List[Dict]:
    """Load materials from DATABASE (stored as inventory items)"""
    get_db_session, org_id, _, InventoryRepository = _get_db_components()
    
    if not get_db_session:
        logger.error("Database not available for loading materials")
        return []
    
    try:
        with get_db_session() as session:
            repo = InventoryRepository(session, org_id)
            items = repo.list_items()
            
            materials = []
            for item in items:
                material = {
                    'id': item['id'],
                    'name': item['name'],
                    'type': (item.get('metadata', {}) or {}).get('material_type', 'stock'),
                    'category': item.get('category', ''),
                    'location': item.get('location', 'sydney'),
                    'quantity': item.get('quantity', 0),
                    'unit_price': item.get('unit_price', 0),
                    'supplier_id': item.get('supplier_id', ''),
                    'images': (item.get('metadata', {}) or {}).get('images', []),
                    'assigned_to_jobs': (item.get('metadata', {}) or {}).get('assigned_to_jobs', []),
                    'assigned_to_quotes': (item.get('metadata', {}) or {}).get('assigned_to_quotes', []),
                    'group_items': (item.get('metadata', {}) or {}).get('group_items', []),
                    'created_at': item.get('created_at'),
                    'updated_at': item.get('updated_at')
                }
                
                if mat_type and material['type'] != mat_type:
                    continue
                if location and material['location'] != location:
                    continue
                
                materials.append(material)
            
            return materials
    except Exception as e:
        logger.error(f"Error loading materials from database: {e}")
        return []


def save_materials(materials) -> bool:
    """Save materials to DATABASE - deprecated, use create/update methods instead"""
    logger.warning("save_materials is deprecated - use create_material/update_material instead")
    return True


def get_material(material_id: str) -> Optional[Dict]:
    """Get a single material by ID from DATABASE"""
    get_db_session, org_id, _, InventoryRepository = _get_db_components()
    
    if not get_db_session:
        return None
    
    try:
        with get_db_session() as session:
            repo = InventoryRepository(session, org_id)
            item = repo.get_item(material_id)
            
            if item:
                return {
                    'id': item['id'],
                    'name': item['name'],
                    'type': (item.get('metadata', {}) or {}).get('material_type', 'stock'),
                    'category': item.get('category', ''),
                    'location': item.get('location', 'sydney'),
                    'quantity': item.get('quantity', 0),
                    'unit_price': item.get('unit_price', 0),
                    'supplier_id': item.get('supplier_id', ''),
                    'images': (item.get('metadata', {}) or {}).get('images', []),
                    'created_at': item.get('created_at'),
                    'updated_at': item.get('updated_at')
                }
            return None
    except Exception as e:
        logger.error(f"Error getting material {material_id}: {e}")
        return None


def create_material(data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Create a new material in DATABASE"""
    get_db_session, org_id, _, InventoryRepository = _get_db_components()
    
    if not get_db_session:
        return None, "Database not available"
    
    try:
        with get_db_session() as session:
            repo = InventoryRepository(session, org_id)
            
            item_data = {
                'name': data.get('name', ''),
                'category': data.get('category', ''),
                'quantity': int(data.get('quantity', 0)),
                'unit_price': float(data.get('unit_price', 0)),
                'location': data.get('location', 'sydney'),
                'supplier_id': data.get('supplier_id'),
                'metadata': {
                    'material_type': data.get('type', 'stock'),
                    'images': data.get('images', []),
                    'group_items': data.get('group_items', []),
                    'assigned_to_jobs': [],
                    'assigned_to_quotes': []
                }
            }
            
            item = repo.create_item(item_data)
            session.commit()
            
            material = {
                'id': item['id'],
                'name': item['name'],
                'type': data.get('type', 'stock'),
                'category': item.get('category', ''),
                'location': item.get('location', 'sydney'),
                'quantity': item.get('quantity', 0),
                'unit_price': item.get('unit_price', 0),
                'supplier_id': item.get('supplier_id', ''),
                'images': data.get('images', []),
                'created_at': item.get('created_at'),
                'updated_at': item.get('updated_at')
            }
            
            return material, None
    except Exception as e:
        logger.error(f"Error creating material: {e}")
        return None, str(e)


def update_material(material_id: str, data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Update a material in DATABASE"""
    get_db_session, org_id, _, InventoryRepository = _get_db_components()
    
    if not get_db_session:
        return None, "Database not available"
    
    try:
        with get_db_session() as session:
            repo = InventoryRepository(session, org_id)
            
            # Get current item to preserve metadata
            current = repo.get_item(material_id)
            if not current:
                return None, "Material not found"
            
            update_data = {}
            if 'name' in data:
                update_data['name'] = data['name']
            if 'category' in data:
                update_data['category'] = data['category']
            if 'quantity' in data:
                update_data['quantity'] = int(data['quantity'])
            if 'unit_price' in data:
                update_data['unit_price'] = float(data['unit_price'])
            if 'location' in data:
                update_data['location'] = data['location']
            if 'supplier_id' in data:
                update_data['supplier_id'] = data['supplier_id']
            
            # Handle metadata updates
            metadata = current.get('metadata', {}) or {}
            if 'type' in data:
                metadata['material_type'] = data['type']
            if 'images' in data:
                metadata['images'] = data['images']
            update_data['metadata'] = metadata
            
            item = repo.update_item(material_id, update_data)
            session.commit()
            
            if item:
                material = {
                    'id': item['id'],
                    'name': item['name'],
                    'type': (item.get('metadata', {}) or {}).get('material_type', 'stock'),
                    'category': item.get('category', ''),
                    'location': item.get('location', 'sydney'),
                    'quantity': item.get('quantity', 0),
                    'unit_price': item.get('unit_price', 0),
                    'supplier_id': item.get('supplier_id', ''),
                    'images': (item.get('metadata', {}) or {}).get('images', []),
                    'created_at': item.get('created_at'),
                    'updated_at': item.get('updated_at')
                }
                return material, None
            return None, "Failed to update material"
    except Exception as e:
        logger.error(f"Error updating material {material_id}: {e}")
        return None, str(e)


def delete_material(material_id: str) -> Tuple[bool, Optional[str]]:
    """Delete a material from DATABASE"""
    get_db_session, org_id, _, InventoryRepository = _get_db_components()
    
    if not get_db_session:
        return False, "Database not available"
    
    try:
        with get_db_session() as session:
            repo = InventoryRepository(session, org_id)
            success = repo.delete_item(material_id)
            session.commit()
            
            if success:
                return True, None
            return False, "Material not found"
    except Exception as e:
        logger.error(f"Error deleting material {material_id}: {e}")
        return False, str(e)


# ====================================================================================
# PAYMENTS MODULE
# ====================================================================================

PAYMENT_DIRECTIONS = ['to_us', 'to_suppliers']
PAYMENT_STATUSES = ['upcoming', 'pending', 'due', 'paid', 'credit', 'retention']


def load_payments(direction=None, status=None) -> List[Dict]:
    """Load payments from DATABASE"""
    get_db_session, org_id, _, _ = _get_db_components()
    
    if not get_db_session:
        logger.error("Database not available for loading payments")
        return []
    
    try:
        from database.models import Payment
        
        with get_db_session() as session:
            query = session.query(Payment).filter(
                Payment.organization_id == org_id
            )
            if direction:
                query = query.filter(Payment.direction == direction)
            if status:
                query = query.filter(Payment.status == status)
            
            payments = query.order_by(Payment.created_at.desc()).all()
            return [p.to_dict() for p in payments]
    except Exception as e:
        logger.error(f"Error loading payments from database: {e}")
        return []


def save_payments(payments) -> bool:
    """Save payments to DATABASE - deprecated, use create/update methods instead"""
    logger.warning("save_payments is deprecated - use create_payment/update_payment instead")
    return True


def get_payment(payment_id: str) -> Optional[Dict]:
    """Get a single payment by ID from DATABASE"""
    get_db_session, org_id, _, _ = _get_db_components()
    
    if not get_db_session:
        return None
    
    try:
        from database.models import Payment
        
        with get_db_session() as session:
            payment = session.query(Payment).filter(
                Payment.id == payment_id,
                Payment.organization_id == org_id
            ).first()
            
            if payment:
                return payment.to_dict()
            return None
    except Exception as e:
        logger.error(f"Error getting payment {payment_id}: {e}")
        return None


def create_payment(data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Create a new payment in DATABASE"""
    get_db_session, org_id, _, _ = _get_db_components()
    
    if not get_db_session:
        return None, "Database not available"
    
    try:
        from database.models import Payment
        from datetime import date
        
        with get_db_session() as session:
            payment = Payment(
                organization_id=org_id,
                direction=data.get('direction', 'to_us'),
                status=data.get('status', 'pending'),
                amount=float(data.get('amount', 0)),
                notes=data.get('notes', ''),
                person_id=data.get('person_id'),
                linked_to=data.get('linked_to', {}),
                invoice_pdf=data.get('invoice_pdf', '')
            )
            
            if data.get('due_date'):
                try:
                    payment.due_date = date.fromisoformat(data['due_date'].split('T')[0])
                except:
                    pass
            if data.get('paid_date'):
                try:
                    payment.paid_date = date.fromisoformat(data['paid_date'].split('T')[0])
                except:
                    pass
            
            session.add(payment)
            session.commit()
            
            return payment.to_dict(), None
    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        return None, str(e)


def update_payment(payment_id: str, data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Update a payment in DATABASE"""
    get_db_session, org_id, _, _ = _get_db_components()
    
    if not get_db_session:
        return None, "Database not available"
    
    try:
        from database.models import Payment
        from datetime import date
        
        with get_db_session() as session:
            payment = session.query(Payment).filter(
                Payment.id == payment_id,
                Payment.organization_id == org_id
            ).first()
            
            if not payment:
                return None, "Payment not found"
            
            for key in ['direction', 'status', 'notes']:
                if key in data:
                    setattr(payment, key, data[key])
            
            if 'amount' in data:
                payment.amount = float(data['amount'])
            if 'due_date' in data:
                try:
                    payment.due_date = date.fromisoformat(data['due_date'].split('T')[0])
                except:
                    pass
            if 'paid_date' in data:
                try:
                    payment.paid_date = date.fromisoformat(data['paid_date'].split('T')[0])
                except:
                    pass
            
            payment.updated_at = datetime.utcnow()
            session.commit()
            
            return payment.to_dict(), None
    except Exception as e:
        logger.error(f"Error updating payment {payment_id}: {e}")
        return None, str(e)


def delete_payment(payment_id: str) -> Tuple[bool, Optional[str]]:
    """Delete a payment from DATABASE"""
    get_db_session, org_id, _, _ = _get_db_components()
    
    if not get_db_session:
        return False, "Database not available"
    
    try:
        from database.models import Payment
        
        with get_db_session() as session:
            payment = session.query(Payment).filter(
                Payment.id == payment_id,
                Payment.organization_id == org_id
            ).first()
            
            if not payment:
                return False, "Payment not found"
            
            session.delete(payment)
            session.commit()
            
            return True, None
    except Exception as e:
        logger.error(f"Error deleting payment {payment_id}: {e}")
        return False, str(e)


def generate_invoice(payment_id: str) -> Tuple[Optional[Dict], Optional[str]]:
    """Generate invoice for a payment"""
    get_db_session, org_id, _, _ = _get_db_components()
    
    if not get_db_session:
        return None, "Database not available"
    
    try:
        from database.models import Payment
        
        with get_db_session() as session:
            payment = session.query(Payment).filter(
                Payment.id == payment_id,
                Payment.organization_id == org_id
            ).first()
            
            if not payment:
                return None, "Payment not found"
            
            if not payment.invoice_number:
                payment.invoice_number = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                session.commit()
            
            return {
                'invoice_number': payment.invoice_number,
                'amount': payment.amount,
                'status': payment.status,
                'due_date': payment.due_date.isoformat() if payment.due_date else None
            }, None
    except Exception as e:
        logger.error(f"Error generating invoice for payment {payment_id}: {e}")
        return None, str(e)


# ====================================================================================
# SCHEDULES/CALENDAR MODULE
# ====================================================================================

SCHEDULE_TYPES = {
    'job': 'Job',
    'meeting': 'Meeting',
    'reminder': 'Reminder',
    'event': 'Event'
}

SCHEDULE_RECURRENCE = {
    'none': 'None',
    'daily': 'Daily',
    'weekly': 'Weekly',
    'fortnightly': 'Fortnightly',
    'monthly': 'Monthly',
    'annually': 'Annually'
}


def load_events() -> List[Dict]:
    """Load calendar events from DATABASE"""
    db_layer = _get_db_layer()
    
    if not db_layer or not db_layer.db_enabled:
        logger.error("Database not available for loading events")
        return []
    
    try:
        result = db_layer.get_calendar_events()
        events = result.get('events', [])
        
        # Convert database format to legacy format for backwards compatibility
        converted = []
        for event in events:
            converted_event = {
                'id': event['id'],
                'title': event.get('title', ''),
                'description': event.get('description', ''),
                'type': event.get('event_type', 'event'),
                'start_date': event.get('start_time', '').split('T')[0] if event.get('start_time') else '',
                'start_time': event.get('start_time', '').split('T')[1][:5] if event.get('start_time') and 'T' in event.get('start_time', '') else '',
                'end_date': event.get('end_time', '').split('T')[0] if event.get('end_time') else '',
                'end_time': event.get('end_time', '').split('T')[1][:5] if event.get('end_time') and 'T' in event.get('end_time', '') else '',
                'all_day': event.get('all_day', False),
                'recurrence': event.get('recurrence_rule', 'none') or 'none',
                'location': event.get('location', ''),
                'attendees': event.get('attendees', []),
                'linked_to': event.get('metadata', {}) or {},
                'color': (event.get('metadata', {}) or {}).get('color', '#3b82f6'),
                'reminder_minutes': (event.get('metadata', {}) or {}).get('reminder_minutes', 0),
                'created_at': event.get('created_at'),
                'updated_at': event.get('updated_at')
            }
            converted.append(converted_event)
        
        return converted
    except Exception as e:
        logger.error(f"Error loading events from database: {e}")
        return []


def save_events(events) -> bool:
    """Save events to DATABASE - deprecated, use create/update methods instead"""
    logger.warning("save_events is deprecated - use create_event/update_event instead")
    return True


def get_event(event_id: str) -> Optional[Dict]:
    """Get a single event by ID from DATABASE"""
    get_db_session, org_id, CRMRepository, _ = _get_db_components()
    
    if not get_db_session:
        return None
    
    try:
        with get_db_session() as session:
            repo = CRMRepository(session, org_id)
            event = repo.get_calendar_event(event_id)
            
            if event:
                return {
                    'id': event['id'],
                    'title': event.get('title', ''),
                    'description': event.get('description', ''),
                    'type': event.get('event_type', 'event'),
                    'start_date': event.get('start_time', '').split('T')[0] if event.get('start_time') else '',
                    'start_time': event.get('start_time', '').split('T')[1][:5] if event.get('start_time') and 'T' in event.get('start_time', '') else '',
                    'end_date': event.get('end_time', '').split('T')[0] if event.get('end_time') else '',
                    'end_time': event.get('end_time', '').split('T')[1][:5] if event.get('end_time') and 'T' in event.get('end_time', '') else '',
                    'all_day': event.get('all_day', False),
                    'recurrence': event.get('recurrence_rule', 'none') or 'none',
                    'location': event.get('location', ''),
                    'attendees': event.get('attendees', []),
                    'created_at': event.get('created_at'),
                    'updated_at': event.get('updated_at')
                }
            return None
    except Exception as e:
        logger.error(f"Error getting event {event_id}: {e}")
        return None


def create_event(data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Create a new calendar event in DATABASE"""
    db_layer = _get_db_layer()
    
    if not db_layer or not db_layer.db_enabled:
        return None, "Database not available"
    
    # Validate required fields
    if not data.get('title'):
        return None, "Title is required"
    if not data.get('start_date'):
        return None, "Start date is required"
    
    try:
        # Convert legacy format to database format
        start_datetime = data.get('start_date', '')
        if data.get('start_time'):
            start_datetime = f"{data['start_date']}T{data['start_time']}:00"
        
        end_datetime = data.get('end_date', data.get('start_date', ''))
        if data.get('end_time'):
            end_datetime = f"{end_datetime}T{data['end_time']}:00"
        
        event_data = {
            'title': data.get('title', ''),
            'description': data.get('description', ''),
            'event_type': data.get('type', 'event'),
            'start_time': start_datetime,
            'end_time': end_datetime,
            'all_day': data.get('all_day', False),
            'location': data.get('location', ''),
            'attendees': data.get('attendees', []),
            'recurrence_rule': data.get('recurrence', 'none'),
            'metadata': {
                'color': data.get('color', '#3b82f6'),
                'reminder_minutes': data.get('reminder_minutes', 0),
                'linked_to': data.get('linked_to', {}),
                'google_event_id': data.get('google_event_id', '')
            }
        }
        
        result = db_layer.create_calendar_event(event_data)
        
        if result.get('success'):
            event = result.get('event')
            # Convert back to legacy format
            return {
                'id': event['id'],
                'title': event.get('title', ''),
                'description': event.get('description', ''),
                'type': event.get('event_type', 'event'),
                'start_date': data.get('start_date', ''),
                'start_time': data.get('start_time', ''),
                'end_date': data.get('end_date', data.get('start_date', '')),
                'end_time': data.get('end_time', ''),
                'all_day': event.get('all_day', False),
                'recurrence': data.get('recurrence', 'none'),
                'location': event.get('location', ''),
                'attendees': event.get('attendees', []),
                'color': data.get('color', '#3b82f6'),
                'reminder_minutes': data.get('reminder_minutes', 0),
                'created_at': event.get('created_at'),
                'updated_at': event.get('updated_at')
            }, None
        return None, result.get('error', 'Failed to create event')
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        return None, str(e)


def update_event(event_id: str, data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Update a calendar event in DATABASE"""
    db_layer = _get_db_layer()
    
    if not db_layer or not db_layer.db_enabled:
        return None, "Database not available"
    
    try:
        # Convert legacy format to database format
        event_data = {}
        
        if 'title' in data:
            event_data['title'] = data['title']
        if 'description' in data:
            event_data['description'] = data['description']
        if 'type' in data:
            event_data['event_type'] = data['type']
        if 'all_day' in data:
            event_data['all_day'] = data['all_day']
        if 'location' in data:
            event_data['location'] = data['location']
        if 'attendees' in data:
            event_data['attendees'] = data['attendees']
        if 'recurrence' in data:
            event_data['recurrence_rule'] = data['recurrence']
        
        if 'start_date' in data:
            start_datetime = data['start_date']
            if data.get('start_time'):
                start_datetime = f"{data['start_date']}T{data['start_time']}:00"
            event_data['start_time'] = start_datetime
        
        if 'end_date' in data:
            end_datetime = data['end_date']
            if data.get('end_time'):
                end_datetime = f"{data['end_date']}T{data['end_time']}:00"
            event_data['end_time'] = end_datetime
        
        result = db_layer.update_calendar_event(event_id, event_data)
        
        if result.get('success'):
            event = result.get('event')
            return {
                'id': event['id'],
                'title': event.get('title', ''),
                'description': event.get('description', ''),
                'type': event.get('event_type', 'event'),
                'start_date': event.get('start_time', '').split('T')[0] if event.get('start_time') else '',
                'start_time': event.get('start_time', '').split('T')[1][:5] if event.get('start_time') and 'T' in event.get('start_time', '') else '',
                'end_date': event.get('end_time', '').split('T')[0] if event.get('end_time') else '',
                'end_time': event.get('end_time', '').split('T')[1][:5] if event.get('end_time') and 'T' in event.get('end_time', '') else '',
                'all_day': event.get('all_day', False),
                'recurrence': event.get('recurrence_rule', 'none') or 'none',
                'location': event.get('location', ''),
                'attendees': event.get('attendees', []),
                'created_at': event.get('created_at'),
                'updated_at': event.get('updated_at')
            }, None
        return None, result.get('error', 'Failed to update event')
    except Exception as e:
        logger.error(f"Error updating event {event_id}: {e}")
        return None, str(e)


def delete_event(event_id: str) -> Tuple[bool, Optional[str]]:
    """Delete a calendar event from DATABASE"""
    db_layer = _get_db_layer()
    
    if not db_layer or not db_layer.db_enabled:
        return False, "Database not available"
    
    try:
        result = db_layer.delete_calendar_event(event_id)
        if result.get('success'):
            return True, None
        return False, result.get('error', 'Failed to delete event')
    except Exception as e:
        logger.error(f"Error deleting event {event_id}: {e}")
        return False, str(e)


def get_events_by_date_range(start_date: str, end_date: str) -> List[Dict]:
    """Get events within a date range from DATABASE"""
    db_layer = _get_db_layer()
    
    if not db_layer or not db_layer.db_enabled:
        return []
    
    try:
        result = db_layer.get_calendar_events(start_date=start_date, end_date=end_date)
        events = result.get('events', [])
        
        # Convert to legacy format
        converted = []
        for event in events:
            converted_event = {
                'id': event['id'],
                'title': event.get('title', ''),
                'description': event.get('description', ''),
                'type': event.get('event_type', 'event'),
                'start_date': event.get('start_time', '').split('T')[0] if event.get('start_time') else '',
                'start_time': event.get('start_time', '').split('T')[1][:5] if event.get('start_time') and 'T' in event.get('start_time', '') else '',
                'end_date': event.get('end_time', '').split('T')[0] if event.get('end_time') else '',
                'end_time': event.get('end_time', '').split('T')[1][:5] if event.get('end_time') and 'T' in event.get('end_time', '') else '',
                'all_day': event.get('all_day', False),
                'location': event.get('location', ''),
                'attendees': event.get('attendees', []),
                'created_at': event.get('created_at'),
                'updated_at': event.get('updated_at')
            }
            converted.append(converted_event)
        
        return converted
    except Exception as e:
        logger.error(f"Error getting events by date range: {e}")
        return []


# ====================================================================================
# COMMUNICATIONS MODULE
# ====================================================================================

def get_all_communications(customer_id=None, project_id=None) -> List[Dict]:
    """Get all communications from DATABASE"""
    get_db_session, org_id, CRMRepository, _ = _get_db_components()
    
    if not get_db_session:
        return []
    
    try:
        with get_db_session() as session:
            repo = CRMRepository(session, org_id)
            return repo.list_communications(customer_id=customer_id, project_id=project_id)
    except Exception as e:
        logger.error(f"Error getting communications: {e}")
        return []


def create_communication(data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Create a new communication in DATABASE"""
    get_db_session, org_id, CRMRepository, _ = _get_db_components()
    
    if not get_db_session:
        return None, "Database not available"
    
    try:
        with get_db_session() as session:
            repo = CRMRepository(session, org_id)
            comm = repo.create_communication(data)
            session.commit()
            return comm, None
    except Exception as e:
        logger.error(f"Error creating communication: {e}")
        return None, str(e)


def update_communication(comm_id: str, data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Update a communication in DATABASE"""
    get_db_session, org_id, _, _ = _get_db_components()
    
    if not get_db_session:
        return None, "Database not available"
    
    try:
        from database.models import Communication
        
        with get_db_session() as session:
            comm = session.query(Communication).filter(
                Communication.id == comm_id,
                Communication.organization_id == org_id
            ).first()
            
            if not comm:
                return None, "Communication not found"
            
            for key in ['subject', 'content', 'status']:
                if key in data:
                    setattr(comm, key, data[key])
            if 'type' in data:
                comm.comm_type = data['type']
            
            comm.updated_at = datetime.utcnow()
            session.commit()
            
            return comm.to_dict(), None
    except Exception as e:
        logger.error(f"Error updating communication {comm_id}: {e}")
        return None, str(e)


def delete_communication(comm_id: str) -> Tuple[bool, Optional[str]]:
    """Delete a communication from DATABASE"""
    get_db_session, org_id, _, _ = _get_db_components()
    
    if not get_db_session:
        return False, "Database not available"
    
    try:
        from database.models import Communication
        
        with get_db_session() as session:
            comm = session.query(Communication).filter(
                Communication.id == comm_id,
                Communication.organization_id == org_id
            ).first()
            
            if not comm:
                return False, "Communication not found"
            
            session.delete(comm)
            session.commit()
            
            return True, None
    except Exception as e:
        logger.error(f"Error deleting communication {comm_id}: {e}")
        return False, str(e)
