"""
CRM Repository - Database access layer for CRM entities.
Handles customers, projects, jobs, technicians, suppliers, quotes, communications, calendar.
All operations are logged to the event_log table for AI learning.
"""

import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from database.models import (
    Customer, Project, Job, Technician, Supplier,
    Quote, QuoteLineItem, Communication, CalendarEvent,
    PriceClass, PriceClassItem, EventLog
)

logger = logging.getLogger(__name__)


class CRMRepository:
    """Repository for CRM database operations with event logging for AI."""
    
    # Map API field names to database column names
    FIELD_MAPPING = {
        'metadata': 'extra_data'
    }
    
    def __init__(self, session: Session, organization_id: str, user_id: str = None):
        self.session = session
        self.organization_id = organization_id
        self.user_id = user_id  # For tracking who made changes
    
    def _log_event(self, entity_type: str, entity_id: str, event_type: str,
                   description: str = None, metadata: Dict = None):
        """Log an event to the event_log table for AI learning."""
        try:
            event = EventLog(
                organization_id=self.organization_id,
                timestamp=datetime.utcnow(),
                actor_type='user' if self.user_id else 'system',
                actor_id=self.user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                event_type=event_type,
                description=description,
                extra_data=metadata or {}
            )
            self.session.add(event)
        except Exception as e:
            logger.warning(f"Failed to log event: {e}")
    
    def _map_field(self, key: str) -> str:
        """Map API field name to database column name."""
        return self.FIELD_MAPPING.get(key, key)
    
    # =========================================================================
    # CUSTOMERS
    # =========================================================================
    
    def list_customers(self, active_only: bool = True) -> List[Dict]:
        """List all customers."""
        query = self.session.query(Customer).filter(
            Customer.organization_id == self.organization_id
        )
        if active_only:
            query = query.filter(Customer.is_active == True)
        customers = query.order_by(Customer.name).all()
        return [c.to_dict() for c in customers]
    
    def get_customer(self, customer_id: str) -> Optional[Dict]:
        """Get a customer by ID."""
        customer = self.session.query(Customer).filter(
            Customer.id == customer_id,
            Customer.organization_id == self.organization_id
        ).first()
        return customer.to_dict() if customer else None
    
    def create_customer(self, data: Dict) -> Dict:
        """Create a new customer."""
        customer = Customer(
            organization_id=self.organization_id,
            name=data.get('name', ''),
            company=data.get('company'),
            email=data.get('email'),
            phone=data.get('phone'),
            address=data.get('address'),
            city=data.get('city'),
            state=data.get('state'),
            postal_code=data.get('postal_code'),
            country=data.get('country', 'Australia'),
            notes=data.get('notes'),
            tags=data.get('tags', []),
            extra_data=data.get('metadata', {})
        )
        self.session.add(customer)
        self.session.flush()
        
        # Log event for AI learning
        self._log_event(
            entity_type='customer',
            entity_id=customer.id,
            event_type='CREATED',
            description=f"Customer '{customer.name}' was created",
            metadata={'customer_name': customer.name, 'email': customer.email}
        )
        
        logger.info(f"Created customer: {customer.id}")
        return customer.to_dict()
    
    def update_customer(self, customer_id: str, data: Dict) -> Optional[Dict]:
        """Update a customer."""
        customer = self.session.query(Customer).filter(
            Customer.id == customer_id,
            Customer.organization_id == self.organization_id
        ).first()
        if not customer:
            return None
        
        # Track changes for AI learning
        changes = {}
        for key in ['name', 'company', 'email', 'phone', 'address', 
                    'city', 'state', 'postal_code', 'country', 'notes', 
                    'tags', 'metadata', 'is_active']:
            if key in data:
                old_value = getattr(customer, self._map_field(key))
                new_value = data[key]
                if old_value != new_value:
                    changes[key] = {'old': old_value, 'new': new_value}
                setattr(customer, self._map_field(key), data[key])
        
        customer.updated_at = datetime.utcnow()
        self.session.flush()
        
        # Log event for AI learning
        if changes:
            self._log_event(
                entity_type='customer',
                entity_id=customer_id,
                event_type='UPDATED',
                description=f"Customer '{customer.name}' was updated",
                metadata={'changes': changes}
            )
        
        logger.info(f"Updated customer: {customer_id}")
        return customer.to_dict()
    
    def delete_customer(self, customer_id: str) -> bool:
        """Soft delete a customer (set inactive)."""
        customer = self.session.query(Customer).filter(
            Customer.id == customer_id,
            Customer.organization_id == self.organization_id
        ).first()
        if not customer:
            return False
        
        customer_name = customer.name
        customer.is_active = False
        customer.updated_at = datetime.utcnow()
        self.session.flush()
        
        # Log event for AI learning
        self._log_event(
            entity_type='customer',
            entity_id=customer_id,
            event_type='DELETED',
            description=f"Customer '{customer_name}' was deactivated",
            metadata={'customer_name': customer_name}
        )
        
        logger.info(f"Deleted (deactivated) customer: {customer_id}")
        return True
    
    def search_customers(self, query: str) -> List[Dict]:
        """Search customers by name, company, or email."""
        search = f"%{query}%"
        customers = self.session.query(Customer).filter(
            Customer.organization_id == self.organization_id,
            Customer.is_active == True,
            or_(
                Customer.name.ilike(search),
                Customer.company.ilike(search),
                Customer.email.ilike(search)
            )
        ).all()
        return [c.to_dict() for c in customers]
    
    # =========================================================================
    # PROJECTS
    # =========================================================================
    
    def list_projects(self, customer_id: str = None, status: str = None) -> List[Dict]:
        """List projects, optionally filtered by customer or status."""
        query = self.session.query(Project).filter(
            Project.organization_id == self.organization_id
        )
        if customer_id:
            query = query.filter(Project.customer_id == customer_id)
        if status:
            query = query.filter(Project.status == status)
        projects = query.order_by(Project.created_at.desc()).all()
        return [p.to_dict() for p in projects]
    
    def get_project(self, project_id: str) -> Optional[Dict]:
        """Get a project by ID."""
        project = self.session.query(Project).filter(
            Project.id == project_id,
            Project.organization_id == self.organization_id
        ).first()
        return project.to_dict() if project else None
    
    def create_project(self, data: Dict) -> Dict:
        """Create a new project."""
        project = Project(
            organization_id=self.organization_id,
            customer_id=data.get('customer_id'),
            name=data.get('name', ''),
            description=data.get('description'),
            status=data.get('status', 'pending'),
            project_type=data.get('project_type'),
            address=data.get('address'),
            start_date=self._parse_date(data.get('start_date')),
            end_date=self._parse_date(data.get('end_date')),
            estimated_value=data.get('estimated_value', 0),
            notes=data.get('notes'),
            extra_data=data.get('metadata', {})
        )
        self.session.add(project)
        self.session.flush()
        logger.info(f"Created project: {project.id}")
        return project.to_dict()
    
    def update_project(self, project_id: str, data: Dict) -> Optional[Dict]:
        """Update a project."""
        project = self.session.query(Project).filter(
            Project.id == project_id,
            Project.organization_id == self.organization_id
        ).first()
        if not project:
            return None
        
        for key in ['name', 'description', 'status', 'project_type', 'address',
                    'estimated_value', 'actual_value', 'notes', 'metadata']:
            if key in data:
                setattr(project, self._map_field(key), data[key])
        
        if 'start_date' in data:
            project.start_date = self._parse_date(data['start_date'])
        if 'end_date' in data:
            project.end_date = self._parse_date(data['end_date'])
        if 'customer_id' in data:
            project.customer_id = data['customer_id'] or None
        
        project.updated_at = datetime.utcnow()
        self.session.flush()
        logger.info(f"Updated project: {project_id}")
        return project.to_dict()
    
    def delete_project(self, project_id: str) -> bool:
        """Delete a project."""
        project = self.session.query(Project).filter(
            Project.id == project_id,
            Project.organization_id == self.organization_id
        ).first()
        if not project:
            return False
        self.session.delete(project)
        self.session.flush()
        logger.info(f"Deleted project: {project_id}")
        return True
    
    # =========================================================================
    # JOBS
    # =========================================================================
    
    def list_jobs(self, project_id: str = None, status: str = None, 
                  technician_id: str = None) -> List[Dict]:
        """List jobs with optional filters."""
        query = self.session.query(Job).filter(
            Job.organization_id == self.organization_id
        )
        if project_id:
            query = query.filter(Job.project_id == project_id)
        if status:
            query = query.filter(Job.status == status)
        if technician_id:
            query = query.filter(Job.technician_id == technician_id)
        jobs = query.order_by(Job.scheduled_date.desc().nullslast()).all()
        return [j.to_dict() for j in jobs]
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get a job by ID."""
        job = self.session.query(Job).filter(
            Job.id == job_id,
            Job.organization_id == self.organization_id
        ).first()
        return job.to_dict() if job else None
    
    def create_job(self, data: Dict) -> Dict:
        """Create a new job."""
        job = Job(
            organization_id=self.organization_id,
            project_id=data.get('project_id'),
            technician_id=data.get('technician_id'),
            title=data.get('title', ''),
            description=data.get('description'),
            status=data.get('status', 'pending'),
            priority=data.get('priority', 'normal'),
            job_type=data.get('job_type'),
            scheduled_date=self._parse_datetime(data.get('scheduled_date')),
            estimated_hours=data.get('estimated_hours'),
            labor_cost=data.get('labor_cost', 0),
            materials_cost=data.get('materials_cost', 0),
            notes=data.get('notes'),
            extra_data=data.get('metadata', {})
        )
        self.session.add(job)
        self.session.flush()
        logger.info(f"Created job: {job.id}")
        return job.to_dict()
    
    def update_job(self, job_id: str, data: Dict) -> Optional[Dict]:
        """Update a job."""
        job = self.session.query(Job).filter(
            Job.id == job_id,
            Job.organization_id == self.organization_id
        ).first()
        if not job:
            return None
        
        for key in ['title', 'description', 'status', 'priority', 'job_type',
                    'estimated_hours', 'actual_hours', 'labor_cost', 
                    'materials_cost', 'notes', 'metadata']:
            if key in data:
                setattr(job, self._map_field(key), data[key])
        
        if 'project_id' in data:
            job.project_id = data['project_id'] or None
        if 'technician_id' in data:
            job.technician_id = data['technician_id'] or None
        if 'scheduled_date' in data:
            job.scheduled_date = self._parse_datetime(data['scheduled_date'])
        if 'completed_date' in data:
            job.completed_date = self._parse_datetime(data['completed_date'])
        
        # Auto-set completed_date when status changes to completed
        if data.get('status') == 'completed' and not job.completed_date:
            job.completed_date = datetime.utcnow()
        
        job.updated_at = datetime.utcnow()
        self.session.flush()
        logger.info(f"Updated job: {job_id}")
        return job.to_dict()
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job."""
        job = self.session.query(Job).filter(
            Job.id == job_id,
            Job.organization_id == self.organization_id
        ).first()
        if not job:
            return False
        self.session.delete(job)
        self.session.flush()
        logger.info(f"Deleted job: {job_id}")
        return True
    
    # =========================================================================
    # TECHNICIANS
    # =========================================================================
    
    def list_technicians(self, active_only: bool = True) -> List[Dict]:
        """List all technicians."""
        query = self.session.query(Technician).filter(
            Technician.organization_id == self.organization_id
        )
        if active_only:
            query = query.filter(Technician.is_active == True)
        technicians = query.order_by(Technician.name).all()
        return [t.to_dict() for t in technicians]
    
    def get_technician(self, technician_id: str) -> Optional[Dict]:
        """Get a technician by ID."""
        tech = self.session.query(Technician).filter(
            Technician.id == technician_id,
            Technician.organization_id == self.organization_id
        ).first()
        return tech.to_dict() if tech else None
    
    def create_technician(self, data: Dict) -> Dict:
        """Create a new technician."""
        tech = Technician(
            organization_id=self.organization_id,
            user_id=data.get('user_id'),
            name=data.get('name', ''),
            email=data.get('email'),
            phone=data.get('phone'),
            specialties=data.get('specialties', []),
            hourly_rate=data.get('hourly_rate', 0),
            notes=data.get('notes'),
            extra_data=data.get('metadata', {})
        )
        self.session.add(tech)
        self.session.flush()
        logger.info(f"Created technician: {tech.id}")
        return tech.to_dict()
    
    def update_technician(self, technician_id: str, data: Dict) -> Optional[Dict]:
        """Update a technician."""
        tech = self.session.query(Technician).filter(
            Technician.id == technician_id,
            Technician.organization_id == self.organization_id
        ).first()
        if not tech:
            return None
        
        for key in ['name', 'email', 'phone', 'specialties', 'hourly_rate',
                    'is_active', 'notes', 'metadata']:
            if key in data:
                setattr(tech, self._map_field(key), data[key])
        
        tech.updated_at = datetime.utcnow()
        self.session.flush()
        logger.info(f"Updated technician: {technician_id}")
        return tech.to_dict()
    
    def delete_technician(self, technician_id: str) -> bool:
        """Soft delete a technician."""
        tech = self.session.query(Technician).filter(
            Technician.id == technician_id,
            Technician.organization_id == self.organization_id
        ).first()
        if not tech:
            return False
        tech.is_active = False
        tech.updated_at = datetime.utcnow()
        self.session.flush()
        logger.info(f"Deleted (deactivated) technician: {technician_id}")
        return True
    
    # =========================================================================
    # SUPPLIERS
    # =========================================================================
    
    def list_suppliers(self, active_only: bool = True) -> List[Dict]:
        """List all suppliers."""
        query = self.session.query(Supplier).filter(
            Supplier.organization_id == self.organization_id
        )
        if active_only:
            query = query.filter(Supplier.is_active == True)
        suppliers = query.order_by(Supplier.name).all()
        return [s.to_dict() for s in suppliers]
    
    def get_supplier(self, supplier_id: str) -> Optional[Dict]:
        """Get a supplier by ID."""
        supplier = self.session.query(Supplier).filter(
            Supplier.id == supplier_id,
            Supplier.organization_id == self.organization_id
        ).first()
        return supplier.to_dict() if supplier else None
    
    def create_supplier(self, data: Dict) -> Dict:
        """Create a new supplier."""
        supplier = Supplier(
            organization_id=self.organization_id,
            name=data.get('name', ''),
            company=data.get('company'),
            email=data.get('email'),
            phone=data.get('phone'),
            address=data.get('address'),
            website=data.get('website'),
            account_number=data.get('account_number'),
            payment_terms=data.get('payment_terms'),
            categories=data.get('categories', []),
            notes=data.get('notes'),
            extra_data=data.get('metadata', {})
        )
        self.session.add(supplier)
        self.session.flush()
        logger.info(f"Created supplier: {supplier.id}")
        return supplier.to_dict()
    
    def update_supplier(self, supplier_id: str, data: Dict) -> Optional[Dict]:
        """Update a supplier."""
        supplier = self.session.query(Supplier).filter(
            Supplier.id == supplier_id,
            Supplier.organization_id == self.organization_id
        ).first()
        if not supplier:
            return None
        
        for key in ['name', 'company', 'email', 'phone', 'address', 'website',
                    'account_number', 'payment_terms', 'categories', 
                    'is_active', 'notes', 'metadata']:
            if key in data:
                setattr(supplier, self._map_field(key), data[key])
        
        supplier.updated_at = datetime.utcnow()
        self.session.flush()
        logger.info(f"Updated supplier: {supplier_id}")
        return supplier.to_dict()
    
    def delete_supplier(self, supplier_id: str) -> bool:
        """Soft delete a supplier."""
        supplier = self.session.query(Supplier).filter(
            Supplier.id == supplier_id,
            Supplier.organization_id == self.organization_id
        ).first()
        if not supplier:
            return False
        supplier.is_active = False
        supplier.updated_at = datetime.utcnow()
        self.session.flush()
        logger.info(f"Deleted (deactivated) supplier: {supplier_id}")
        return True
    
    # =========================================================================
    # QUOTES
    # =========================================================================
    
    def list_quotes(self, customer_id: str = None, project_id: str = None,
                    status: str = None, source: str = None) -> List[Dict]:
        """List quotes with optional filters."""
        query = self.session.query(Quote).filter(
            Quote.organization_id == self.organization_id
        )
        if customer_id:
            query = query.filter(Quote.customer_id == customer_id)
        if project_id:
            query = query.filter(Quote.project_id == project_id)
        if status:
            query = query.filter(Quote.status == status)
        if source:
            query = query.filter(Quote.source == source)
        quotes = query.order_by(Quote.created_at.desc()).all()
        return [q.to_dict() for q in quotes]
    
    def get_quote(self, quote_id: str) -> Optional[Dict]:
        """Get a quote by ID."""
        quote = self.session.query(Quote).filter(
            Quote.id == quote_id,
            Quote.organization_id == self.organization_id
        ).first()
        return quote.to_dict() if quote else None
    
    def create_quote(self, data: Dict) -> Dict:
        """Create a new quote."""
        quote = Quote(
            organization_id=self.organization_id,
            customer_id=data.get('customer_id') or None,
            project_id=data.get('project_id') or None,
            quote_number=data.get('quote_number'),
            title=data.get('title', ''),
            description=data.get('description'),
            status=data.get('status', 'draft'),
            source=data.get('source', 'customer'),
            supplier_name=data.get('supplier_name'),
            subtotal=data.get('subtotal', 0),
            markup_percentage=data.get('markup_percentage', 20),
            markup_amount=data.get('markup_amount', 0),
            total_amount=data.get('total_amount', data.get('quote_amount', 0)),
            labor_cost=data.get('labor_cost', 0),
            materials_cost=data.get('materials_cost', 0),
            valid_until=self._parse_date(data.get('valid_until')),
            notes=data.get('notes'),
            canvas_state=data.get('canvas_state'),
            floorplan_image=data.get('floorplan_image'),
            components=data.get('components', []),
            costs=data.get('costs', {}),
            analysis=data.get('analysis', {}),
            extra_data=data.get('metadata', {})
        )
        self.session.add(quote)
        self.session.flush()
        
        # Log event for AI learning
        self._log_event(
            entity_type='quote',
            entity_id=quote.id,
            event_type='CREATED',
            description=f"Quote '{quote.title}' was created (${quote.total_amount})",
            metadata={
                'title': quote.title,
                'total_amount': quote.total_amount,
                'customer_id': quote.customer_id,
                'status': quote.status
            }
        )
        
        logger.info(f"Created quote: {quote.id}")
        return quote.to_dict()
    
    def update_quote(self, quote_id: str, data: Dict) -> Optional[Dict]:
        """Update a quote."""
        quote = self.session.query(Quote).filter(
            Quote.id == quote_id,
            Quote.organization_id == self.organization_id
        ).first()
        if not quote:
            return None
        
        # Track status changes for AI learning
        old_status = quote.status
        
        for key in ['quote_number', 'title', 'description', 'status', 'source',
                    'supplier_name', 'subtotal', 'markup_percentage', 'markup_amount',
                    'total_amount', 'labor_cost', 'materials_cost', 'notes',
                    'canvas_state', 'floorplan_image', 'components', 'costs',
                    'analysis', 'metadata']:
            if key in data:
                setattr(quote, self._map_field(key), data[key])
        
        if 'quote_amount' in data:
            quote.total_amount = data['quote_amount']
        if 'customer_id' in data:
            quote.customer_id = data['customer_id'] or None
        if 'project_id' in data:
            quote.project_id = data['project_id'] or None
        if 'valid_until' in data:
            quote.valid_until = self._parse_date(data['valid_until'])
        
        quote.updated_at = datetime.utcnow()
        self.session.flush()
        
        # Log event for AI learning - track status changes specially
        if 'status' in data and old_status != data['status']:
            event_type = 'STATUS_CHANGED'
            if data['status'] == 'sent':
                event_type = 'QUOTE_SENT'
            elif data['status'] == 'accepted':
                event_type = 'QUOTE_ACCEPTED'
            elif data['status'] == 'rejected':
                event_type = 'QUOTE_REJECTED'
            elif data['status'] == 'expired':
                event_type = 'QUOTE_EXPIRED'
            
            self._log_event(
                entity_type='quote',
                entity_id=quote_id,
                event_type=event_type,
                description=f"Quote '{quote.title}' status changed from '{old_status}' to '{quote.status}'",
                metadata={
                    'old_status': old_status,
                    'new_status': quote.status,
                    'total_amount': quote.total_amount
                }
            )
        else:
            self._log_event(
                entity_type='quote',
                entity_id=quote_id,
                event_type='UPDATED',
                description=f"Quote '{quote.title}' was updated",
                metadata={'updated_fields': list(data.keys())}
            )
        
        logger.info(f"Updated quote: {quote_id}")
        return quote.to_dict()
    
    def delete_quote(self, quote_id: str) -> bool:
        """Delete a quote."""
        quote = self.session.query(Quote).filter(
            Quote.id == quote_id,
            Quote.organization_id == self.organization_id
        ).first()
        if not quote:
            return False
        self.session.delete(quote)
        self.session.flush()
        logger.info(f"Deleted quote: {quote_id}")
        return True
    
    # =========================================================================
    # COMMUNICATIONS
    # =========================================================================
    
    def list_communications(self, customer_id: str = None, 
                           project_id: str = None) -> List[Dict]:
        """List communications."""
        query = self.session.query(Communication).filter(
            Communication.organization_id == self.organization_id
        )
        if customer_id:
            query = query.filter(Communication.customer_id == customer_id)
        if project_id:
            query = query.filter(Communication.project_id == project_id)
        comms = query.order_by(Communication.created_at.desc()).all()
        return [c.to_dict() for c in comms]
    
    def create_communication(self, data: Dict) -> Dict:
        """Create a new communication record."""
        comm = Communication(
            organization_id=self.organization_id,
            customer_id=data.get('customer_id'),
            project_id=data.get('project_id'),
            job_id=data.get('job_id'),
            user_id=data.get('user_id'),
            comm_type=data.get('type'),
            subject=data.get('subject'),
            content=data.get('content'),
            direction=data.get('direction'),
            status=data.get('status'),
            extra_data=data.get('metadata', {})
        )
        self.session.add(comm)
        self.session.flush()
        logger.info(f"Created communication: {comm.id}")
        return comm.to_dict()
    
    # =========================================================================
    # CALENDAR EVENTS
    # =========================================================================
    
    def list_calendar_events(self, start_date: datetime = None,
                            end_date: datetime = None) -> List[Dict]:
        """List calendar events, optionally within a date range."""
        query = self.session.query(CalendarEvent).filter(
            CalendarEvent.organization_id == self.organization_id
        )
        if start_date:
            query = query.filter(CalendarEvent.start_time >= start_date)
        if end_date:
            query = query.filter(CalendarEvent.start_time <= end_date)
        events = query.order_by(CalendarEvent.start_time).all()
        return [e.to_dict() for e in events]
    
    def get_calendar_event(self, event_id: str) -> Optional[Dict]:
        """Get a calendar event by ID."""
        event = self.session.query(CalendarEvent).filter(
            CalendarEvent.id == event_id,
            CalendarEvent.organization_id == self.organization_id
        ).first()
        return event.to_dict() if event else None
    
    def create_calendar_event(self, data: Dict) -> Dict:
        """Create a new calendar event."""
        event = CalendarEvent(
            organization_id=self.organization_id,
            user_id=data.get('user_id'),
            customer_id=data.get('customer_id'),
            project_id=data.get('project_id'),
            job_id=data.get('job_id'),
            title=data.get('title', ''),
            description=data.get('description'),
            event_type=data.get('event_type'),
            start_time=self._parse_datetime(data.get('start_time')) or datetime.utcnow(),
            end_time=self._parse_datetime(data.get('end_time')),
            all_day=data.get('all_day', False),
            location=data.get('location'),
            attendees=data.get('attendees', []),
            is_recurring=data.get('is_recurring', False),
            recurrence_rule=data.get('recurrence_rule'),
            status=data.get('status', 'scheduled'),
            extra_data=data.get('metadata', {})
        )
        self.session.add(event)
        self.session.flush()
        logger.info(f"Created calendar event: {event.id}")
        return event.to_dict()
    
    def update_calendar_event(self, event_id: str, data: Dict) -> Optional[Dict]:
        """Update a calendar event."""
        event = self.session.query(CalendarEvent).filter(
            CalendarEvent.id == event_id,
            CalendarEvent.organization_id == self.organization_id
        ).first()
        if not event:
            return None
        
        for key in ['title', 'description', 'event_type', 'all_day', 'location',
                    'attendees', 'is_recurring', 'recurrence_rule', 'status', 'metadata']:
            if key in data:
                setattr(event, self._map_field(key), data[key])
        
        if 'start_time' in data:
            event.start_time = self._parse_datetime(data['start_time'])
        if 'end_time' in data:
            event.end_time = self._parse_datetime(data['end_time'])
        
        event.updated_at = datetime.utcnow()
        self.session.flush()
        logger.info(f"Updated calendar event: {event_id}")
        return event.to_dict()
    
    def delete_calendar_event(self, event_id: str) -> bool:
        """Delete a calendar event."""
        event = self.session.query(CalendarEvent).filter(
            CalendarEvent.id == event_id,
            CalendarEvent.organization_id == self.organization_id
        ).first()
        if not event:
            return False
        self.session.delete(event)
        self.session.flush()
        logger.info(f"Deleted calendar event: {event_id}")
        return True
    
    # =========================================================================
    # PRICE CLASSES
    # =========================================================================
    
    def list_price_classes(self, active_only: bool = True) -> List[Dict]:
        """List all price classes."""
        query = self.session.query(PriceClass).filter(
            PriceClass.organization_id == self.organization_id
        )
        if active_only:
            query = query.filter(PriceClass.is_active == True)
        price_classes = query.order_by(PriceClass.name).all()
        return [pc.to_dict() for pc in price_classes]
    
    def get_price_class(self, price_class_id: str) -> Optional[Dict]:
        """Get a price class by ID."""
        pc = self.session.query(PriceClass).filter(
            PriceClass.id == price_class_id,
            PriceClass.organization_id == self.organization_id
        ).first()
        return pc.to_dict() if pc else None
    
    def create_price_class(self, data: Dict) -> Dict:
        """Create a new price class."""
        pc = PriceClass(
            organization_id=self.organization_id,
            name=data.get('name', ''),
            description=data.get('description'),
            icon=data.get('icon'),
            color=data.get('color'),
            category=data.get('category'),
            total_price=data.get('total_price', 0),
            extra_data=data.get('metadata', {})
        )
        self.session.add(pc)
        self.session.flush()
        
        # Add items if provided
        items = data.get('items', [])
        for item_data in items:
            item = PriceClassItem(
                price_class_id=pc.id,
                inventory_item_id=item_data.get('inventory_item_id'),
                name=item_data.get('name', ''),
                quantity=item_data.get('quantity', 1),
                unit_price=item_data.get('unit_price', 0)
            )
            self.session.add(item)
        
        self.session.flush()
        logger.info(f"Created price class: {pc.id}")
        return pc.to_dict()
    
    def update_price_class(self, price_class_id: str, data: Dict) -> Optional[Dict]:
        """Update a price class."""
        pc = self.session.query(PriceClass).filter(
            PriceClass.id == price_class_id,
            PriceClass.organization_id == self.organization_id
        ).first()
        if not pc:
            return None
        
        for key in ['name', 'description', 'icon', 'color', 'category',
                    'total_price', 'is_active', 'metadata']:
            if key in data:
                setattr(pc, self._map_field(key), data[key])
        
        # Update items if provided
        if 'items' in data:
            # Remove existing items
            for item in pc.items:
                self.session.delete(item)
            # Add new items
            for item_data in data['items']:
                item = PriceClassItem(
                    price_class_id=pc.id,
                    inventory_item_id=item_data.get('inventory_item_id'),
                    name=item_data.get('name', ''),
                    quantity=item_data.get('quantity', 1),
                    unit_price=item_data.get('unit_price', 0)
                )
                self.session.add(item)
        
        pc.updated_at = datetime.utcnow()
        self.session.flush()
        logger.info(f"Updated price class: {price_class_id}")
        return pc.to_dict()
    
    def delete_price_class(self, price_class_id: str) -> bool:
        """Soft delete a price class."""
        pc = self.session.query(PriceClass).filter(
            PriceClass.id == price_class_id,
            PriceClass.organization_id == self.organization_id
        ).first()
        if not pc:
            return False
        pc.is_active = False
        pc.updated_at = datetime.utcnow()
        self.session.flush()
        logger.info(f"Deleted (deactivated) price class: {price_class_id}")
        return True
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _parse_date(self, value) -> Optional[date]:
        """Parse a date from string or return None."""
        if not value:
            return None
        if isinstance(value, date):
            return value
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
        except (ValueError, AttributeError):
            return None
    
    def _parse_datetime(self, value) -> Optional[datetime]:
        """Parse a datetime from string or return None."""
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None

