"""
CRM Extended Module
Handles People, Jobs, Materials, Payments, and Schedules
"""
import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Data directory
CRM_DATA_DIR = 'crm_data'

# Ensure directories exist
os.makedirs(CRM_DATA_DIR, exist_ok=True)

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

def load_people(person_type=None):
    """Load people from JSON file"""
    file_path = os.path.join(CRM_DATA_DIR, 'people.json')
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                data = json.load(f)
                # Handle both list and dict formats
                if isinstance(data, list):
                    people = data
                elif isinstance(data, dict):
                    people = data.get('people', [])
                else:
                    people = []

                if person_type:
                    return [p for p in people if p.get('type') == person_type]
                return people
        return []
    except Exception as e:
        logger.error(f"Error loading people: {e}")
        return []

def save_people(people):
    """Save people to JSON file"""
    file_path = os.path.join(CRM_DATA_DIR, 'people.json')
    try:
        with open(file_path, 'w') as f:
            json.dump({'people': people}, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving people: {e}")
        return False

def create_person(data):
    """Create a new person"""
    people = load_people()

    new_person = {
        'id': str(uuid.uuid4()),
        'type': data.get('type', 'contact'),
        'name': data.get('name'),
        'company': data.get('company', ''),
        'email': data.get('email', ''),
        'phone': data.get('phone', ''),
        'address': data.get('address', ''),
        'notes': data.get('notes', ''),
        'linked_jobs': [],
        'linked_quotes': [],
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat()
    }

    people.append(new_person)

    if save_people(people):
        return new_person, None
    return None, "Failed to save person"

def update_person(person_id, data):
    """Update a person"""
    people = load_people()

    for i, person in enumerate(people):
        if person['id'] == person_id:
            person.update({
                'name': data.get('name', person['name']),
                'company': data.get('company', person.get('company', '')),
                'email': data.get('email', person.get('email', '')),
                'phone': data.get('phone', person.get('phone', '')),
                'address': data.get('address', person.get('address', '')),
                'notes': data.get('notes', person.get('notes', '')),
                'updated_at': datetime.utcnow().isoformat()
            })

            people[i] = person

            if save_people(people):
                return person, None
            return None, "Failed to save changes"

    return None, "Person not found"

def delete_person(person_id):
    """Delete a person"""
    people = load_people()
    people = [p for p in people if p['id'] != person_id]

    if save_people(people):
        return True, None
    return False, "Failed to save changes"

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

def load_jobs(status=None):
    """Load jobs from JSON file"""
    file_path = os.path.join(CRM_DATA_DIR, 'jobs.json')
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                data = json.load(f)
                # Handle both list and dict formats
                if isinstance(data, list):
                    jobs = data
                elif isinstance(data, dict):
                    jobs = data.get('jobs', [])
                else:
                    jobs = []

                if status:
                    return [j for j in jobs if j.get('status') == status]
                return jobs
        return []
    except Exception as e:
        logger.error(f"Error loading jobs: {e}")
        return []

def save_jobs(jobs):
    """Save jobs to JSON file"""
    file_path = os.path.join(CRM_DATA_DIR, 'jobs.json')
    try:
        with open(file_path, 'w') as f:
            json.dump({'jobs': jobs}, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving jobs: {e}")
        return False

def create_job(data):
    """Create a new job"""
    jobs = load_jobs()

    new_job = {
        'id': str(uuid.uuid4()),
        'status': data.get('status', 'pending'),
        'name': data.get('name'),
        'customer_id': data.get('customer_id', ''),
        'description': data.get('description', ''),
        'start_date': data.get('start_date', ''),
        'due_date': data.get('due_date', ''),
        'value': float(data.get('value', 0)),
        'materials': [],
        'payments': [],
        'assigned_to': data.get('assigned_to', []),
        'recurring_schedule': data.get('recurring_schedule', ''),
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat()
    }

    jobs.append(new_job)

    if save_jobs(jobs):
        return new_job, None
    return None, "Failed to save job"

def update_job(job_id, data):
    """Update a job"""
    jobs = load_jobs()

    for i, job in enumerate(jobs):
        if job['id'] == job_id:
            job.update({
                'name': data.get('name', job['name']),
                'status': data.get('status', job['status']),
                'customer_id': data.get('customer_id', job.get('customer_id', '')),
                'description': data.get('description', job.get('description', '')),
                'start_date': data.get('start_date', job.get('start_date', '')),
                'due_date': data.get('due_date', job.get('due_date', '')),
                'value': float(data.get('value', job.get('value', 0))),
                'recurring_schedule': data.get('recurring_schedule', job.get('recurring_schedule', '')),
                'updated_at': datetime.utcnow().isoformat()
            })

            jobs[i] = job

            if save_jobs(jobs):
                return job, None
            return None, "Failed to save changes"

    return None, "Job not found"

def delete_job(job_id):
    """Delete a job"""
    jobs = load_jobs()
    jobs = [j for j in jobs if j['id'] != job_id]

    if save_jobs(jobs):
        return True, None
    return False, "Failed to save changes"

# ====================================================================================
# MATERIALS MODULE
# ====================================================================================

MATERIAL_LOCATIONS = ['sydney', 'melbourne']
MATERIAL_TYPES = ['stock', 'order']

def load_materials(mat_type=None, location=None):
    """Load materials from JSON file"""
    file_path = os.path.join(CRM_DATA_DIR, 'materials.json')
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                data = json.load(f)
                # Handle both list and dict formats
                if isinstance(data, list):
                    materials = data
                elif isinstance(data, dict):
                    materials = data.get('materials', [])
                else:
                    materials = []

                if mat_type:
                    materials = [m for m in materials if m.get('type') == mat_type]
                if location:
                    materials = [m for m in materials if m.get('location') == location]

                return materials
        return []
    except Exception as e:
        logger.error(f"Error loading materials: {e}")
        return []

def save_materials(materials):
    """Save materials to JSON file"""
    file_path = os.path.join(CRM_DATA_DIR, 'materials.json')
    try:
        with open(file_path, 'w') as f:
            json.dump({'materials': materials}, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving materials: {e}")
        return False

def create_material(data):
    """Create a new material"""
    materials = load_materials()

    new_material = {
        'id': str(uuid.uuid4()),
        'type': data.get('type', 'stock'),
        'category': data.get('category', ''),
        'name': data.get('name'),
        'location': data.get('location', 'sydney'),
        'quantity': int(data.get('quantity', 0)),
        'unit_price': float(data.get('unit_price', 0)),
        'images': data.get('images', []),
        'assigned_to_jobs': [],
        'assigned_to_quotes': [],
        'group_items': data.get('group_items', []),
        'supplier_id': data.get('supplier_id', ''),
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat()
    }

    materials.append(new_material)

    if save_materials(materials):
        return new_material, None
    return None, "Failed to save material"

def update_material(material_id, data):
    """Update a material"""
    materials = load_materials()

    for i, material in enumerate(materials):
        if material['id'] == material_id:
            material.update({
                'name': data.get('name', material['name']),
                'category': data.get('category', material.get('category', '')),
                'location': data.get('location', material.get('location', 'sydney')),
                'quantity': int(data.get('quantity', material.get('quantity', 0))),
                'unit_price': float(data.get('unit_price', material.get('unit_price', 0))),
                'images': data.get('images', material.get('images', [])),
                'supplier_id': data.get('supplier_id', material.get('supplier_id', '')),
                'updated_at': datetime.utcnow().isoformat()
            })

            materials[i] = material

            if save_materials(materials):
                return material, None
            return None, "Failed to save changes"

    return None, "Material not found"

def delete_material(material_id):
    """Delete a material"""
    materials = load_materials()
    materials = [m for m in materials if m['id'] != material_id]

    if save_materials(materials):
        return True, None
    return False, "Failed to save changes"

# ====================================================================================
# PAYMENTS MODULE
# ====================================================================================

PAYMENT_DIRECTIONS = ['to_us', 'to_suppliers']
PAYMENT_STATUSES = ['upcoming', 'pending', 'due', 'paid', 'credit', 'retention']

def load_payments(direction=None, status=None):
    """Load payments from JSON file"""
    file_path = os.path.join(CRM_DATA_DIR, 'payments.json')
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                data = json.load(f)
                # Handle both list and dict formats
                if isinstance(data, list):
                    payments = data
                elif isinstance(data, dict):
                    payments = data.get('payments', [])
                else:
                    payments = []

                if direction:
                    payments = [p for p in payments if p.get('direction') == direction]
                if status:
                    payments = [p for p in payments if p.get('status') == status]

                return payments
        return []
    except Exception as e:
        logger.error(f"Error loading payments: {e}")
        return []

def save_payments(payments):
    """Save payments to JSON file"""
    file_path = os.path.join(CRM_DATA_DIR, 'payments.json')
    try:
        with open(file_path, 'w') as f:
            json.dump({'payments': payments}, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving payments: {e}")
        return False

def create_payment(data):
    """Create a new payment"""
    payments = load_payments()

    new_payment = {
        'id': str(uuid.uuid4()),
        'direction': data.get('direction', 'to_us'),
        'status': data.get('status', 'pending'),
        'amount': float(data.get('amount', 0)),
        'due_date': data.get('due_date', ''),
        'paid_date': data.get('paid_date', ''),
        'linked_to': data.get('linked_to', {}),
        'person_id': data.get('person_id', ''),
        'invoice_pdf': data.get('invoice_pdf', ''),
        'notes': data.get('notes', ''),
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat()
    }

    payments.append(new_payment)

    if save_payments(payments):
        return new_payment, None
    return None, "Failed to save payment"

def update_payment(payment_id, data):
    """Update a payment"""
    payments = load_payments()

    for i, payment in enumerate(payments):
        if payment['id'] == payment_id:
            payment.update({
                'status': data.get('status', payment['status']),
                'amount': float(data.get('amount', payment.get('amount', 0))),
                'due_date': data.get('due_date', payment.get('due_date', '')),
                'paid_date': data.get('paid_date', payment.get('paid_date', '')),
                'notes': data.get('notes', payment.get('notes', '')),
                'updated_at': datetime.utcnow().isoformat()
            })

            payments[i] = payment

            if save_payments(payments):
                return payment, None
            return None, "Failed to save changes"

    return None, "Payment not found"

def delete_payment(payment_id):
    """Delete a payment"""
    payments = load_payments()
    payments = [p for p in payments if p['id'] != payment_id]

    if save_payments(payments):
        return True, None
    return False, "Failed to save changes"

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

def load_events():
    """Load calendar events from JSON file"""
    file_path = os.path.join(CRM_DATA_DIR, 'calendar.json')
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                data = json.load(f)
                # Handle both list and dict formats
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return data.get('events', [])
                else:
                    return []
        return []
    except Exception as e:
        logger.error(f"Error loading events: {e}")
        return []

def save_events(events):
    """Save calendar events to JSON file"""
    file_path = os.path.join(CRM_DATA_DIR, 'calendar.json')
    try:
        with open(file_path, 'w') as f:
            json.dump({'events': events}, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving events: {e}")
        return False

def get_event(event_id):
    """Get a single event by ID"""
    events = load_events()
    for event in events:
        if event['id'] == event_id:
            return event
    return None

def create_event(data):
    """Create a new calendar event"""
    events = load_events()

    # Validate required fields
    if not data.get('title'):
        return None, "Title is required"
    if not data.get('start_date'):
        return None, "Start date is required"

    new_event = {
        'id': str(uuid.uuid4()),
        'title': data.get('title'),
        'description': data.get('description', ''),
        'type': data.get('type', 'event'),
        'start_date': data.get('start_date'),
        'start_time': data.get('start_time', ''),
        'end_date': data.get('end_date', data.get('start_date')),
        'end_time': data.get('end_time', ''),
        'all_day': data.get('all_day', False),
        'recurrence': data.get('recurrence', 'none'),
        'location': data.get('location', ''),
        'attendees': data.get('attendees', []),
        'linked_to': data.get('linked_to', {}),  # Can link to jobs, people, etc.
        'google_event_id': data.get('google_event_id', ''),
        'color': data.get('color', '#3b82f6'),
        'reminder_minutes': data.get('reminder_minutes', 0),
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat()
    }

    events.append(new_event)

    if save_events(events):
        return new_event, None
    return None, "Failed to save event"

def update_event(event_id, data):
    """Update a calendar event"""
    events = load_events()

    for i, event in enumerate(events):
        if event['id'] == event_id:
            event.update({
                'title': data.get('title', event['title']),
                'description': data.get('description', event.get('description', '')),
                'type': data.get('type', event.get('type', 'event')),
                'start_date': data.get('start_date', event['start_date']),
                'start_time': data.get('start_time', event.get('start_time', '')),
                'end_date': data.get('end_date', event.get('end_date', '')),
                'end_time': data.get('end_time', event.get('end_time', '')),
                'all_day': data.get('all_day', event.get('all_day', False)),
                'recurrence': data.get('recurrence', event.get('recurrence', 'none')),
                'location': data.get('location', event.get('location', '')),
                'attendees': data.get('attendees', event.get('attendees', [])),
                'color': data.get('color', event.get('color', '#3b82f6')),
                'reminder_minutes': data.get('reminder_minutes', event.get('reminder_minutes', 0)),
                'updated_at': datetime.utcnow().isoformat()
            })

            events[i] = event

            if save_events(events):
                return event, None
            return None, "Failed to save changes"

    return None, "Event not found"

def delete_event(event_id):
    """Delete a calendar event"""
    events = load_events()
    events = [e for e in events if e['id'] != event_id]

    if save_events(events):
        return True, None
    return False, "Failed to save changes"

def get_events_by_date_range(start_date, end_date):
    """Get events within a date range"""
    events = load_events()

    try:
        from datetime import datetime as dt
        start = dt.fromisoformat(start_date.replace('Z', '+00:00'))
        end = dt.fromisoformat(end_date.replace('Z', '+00:00'))

        filtered_events = []
        for event in events:
            event_start = dt.fromisoformat(event['start_date'].replace('Z', '+00:00'))
            if start <= event_start <= end:
                filtered_events.append(event)

        return filtered_events
    except Exception as e:
        logger.error(f"Error filtering events by date range: {e}")
        return events
