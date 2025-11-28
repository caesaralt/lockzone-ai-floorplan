"""
SQLAlchemy models for LockZone AI Floorplan application.
Defines all core database tables for CRM, operations, and AI features.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, Date,
    ForeignKey, JSON, Enum as SQLEnum, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from database.connection import Base


def generate_uuid():
    """Generate a new UUID."""
    return str(uuid.uuid4())


# =============================================================================
# ORGANIZATION (Multi-tenant foundation)
# =============================================================================

class Organization(Base):
    """
    Organization/Company - foundation for multi-tenant support.
    For now, we use a single default organization.
    """
    __tablename__ = 'organizations'
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    settings = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="organization")
    customers = relationship("Customer", back_populates="organization")
    projects = relationship("Project", back_populates="organization")
    jobs = relationship("Job", back_populates="organization")
    technicians = relationship("Technician", back_populates="organization")
    suppliers = relationship("Supplier", back_populates="organization")
    inventory_items = relationship("InventoryItem", back_populates="organization")
    price_classes = relationship("PriceClass", back_populates="organization")
    quotes = relationship("Quote", back_populates="organization")
    communications = relationship("Communication", back_populates="organization")
    calendar_events = relationship("CalendarEvent", back_populates="organization")
    documents = relationship("Document", back_populates="organization")
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'settings': self.settings or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# =============================================================================
# USERS & AUTHENTICATION
# =============================================================================

class User(Base):
    """Application users with authentication and permissions."""
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    organization_id = Column(UUID(as_uuid=False), ForeignKey('organizations.id'), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(255))
    role = Column(String(50), default='user')  # admin, user, technician, etc.
    permissions = Column(JSONB, default=[])
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    
    __table_args__ = (
        Index('ix_users_email', 'email'),
        Index('ix_users_organization', 'organization_id'),
    )
    
    def to_dict(self, include_sensitive=False):
        data = {
            'id': self.id,
            'organization_id': self.organization_id,
            'email': self.email,
            'username': self.username,
            'display_name': self.display_name,
            'role': self.role,
            'permissions': self.permissions or [],
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if include_sensitive:
            data['password_hash'] = self.password_hash
        return data


# =============================================================================
# CRM - CUSTOMERS
# =============================================================================

class Customer(Base):
    """Customer/Client records."""
    __tablename__ = 'customers'
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    organization_id = Column(UUID(as_uuid=False), ForeignKey('organizations.id'), nullable=False)
    name = Column(String(255), nullable=False)
    company = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(100), default='Australia')
    notes = Column(Text)
    tags = Column(JSONB, default=[])
    extra_data = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="customers")
    projects = relationship("Project", back_populates="customer")
    quotes = relationship("Quote", back_populates="customer")
    communications = relationship("Communication", back_populates="customer")
    
    __table_args__ = (
        Index('ix_customers_organization', 'organization_id'),
        Index('ix_customers_email', 'email'),
        Index('ix_customers_name', 'name'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'name': self.name,
            'company': self.company,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'postal_code': self.postal_code,
            'country': self.country,
            'notes': self.notes,
            'tags': self.tags or [],
            'metadata': self.extra_data or {},
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# =============================================================================
# CRM - PROJECTS
# =============================================================================

class Project(Base):
    """Projects linked to customers."""
    __tablename__ = 'projects'
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    organization_id = Column(UUID(as_uuid=False), ForeignKey('organizations.id'), nullable=False)
    customer_id = Column(UUID(as_uuid=False), ForeignKey('customers.id'))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default='pending')  # pending, in_progress, completed, cancelled
    project_type = Column(String(100))  # residential, commercial, etc.
    address = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)
    estimated_value = Column(Float, default=0)
    actual_value = Column(Float, default=0)
    notes = Column(Text)
    extra_data = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="projects")
    customer = relationship("Customer", back_populates="projects")
    jobs = relationship("Job", back_populates="project")
    quotes = relationship("Quote", back_populates="project")
    documents = relationship("Document", back_populates="project")
    
    __table_args__ = (
        Index('ix_projects_organization', 'organization_id'),
        Index('ix_projects_customer', 'customer_id'),
        Index('ix_projects_status', 'status'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'customer_id': self.customer_id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'project_type': self.project_type,
            'address': self.address,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'estimated_value': self.estimated_value,
            'actual_value': self.actual_value,
            'notes': self.notes,
            'metadata': self.extra_data or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# =============================================================================
# CRM - JOBS / WORK ORDERS
# =============================================================================

class Job(Base):
    """Jobs/Work orders within projects."""
    __tablename__ = 'jobs'
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    organization_id = Column(UUID(as_uuid=False), ForeignKey('organizations.id'), nullable=False)
    project_id = Column(UUID(as_uuid=False), ForeignKey('projects.id'))
    technician_id = Column(UUID(as_uuid=False), ForeignKey('technicians.id'))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default='pending')  # pending, in_progress, completed, cancelled, upcoming, recurring
    priority = Column(String(20), default='normal')  # low, normal, high, urgent
    job_type = Column(String(100))
    scheduled_date = Column(DateTime)
    completed_date = Column(DateTime)
    estimated_hours = Column(Float)
    actual_hours = Column(Float)
    labor_cost = Column(Float, default=0)
    materials_cost = Column(Float, default=0)
    notes = Column(Text)
    extra_data = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="jobs")
    project = relationship("Project", back_populates="jobs")
    technician = relationship("Technician", back_populates="jobs")
    
    __table_args__ = (
        Index('ix_jobs_organization', 'organization_id'),
        Index('ix_jobs_project', 'project_id'),
        Index('ix_jobs_technician', 'technician_id'),
        Index('ix_jobs_status', 'status'),
        Index('ix_jobs_scheduled_date', 'scheduled_date'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'project_id': self.project_id,
            'technician_id': self.technician_id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'job_type': self.job_type,
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'estimated_hours': self.estimated_hours,
            'actual_hours': self.actual_hours,
            'labor_cost': self.labor_cost,
            'materials_cost': self.materials_cost,
            'notes': self.notes,
            'metadata': self.extra_data or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# =============================================================================
# TECHNICIANS
# =============================================================================

class Technician(Base):
    """Technicians/Field workers."""
    __tablename__ = 'technicians'
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    organization_id = Column(UUID(as_uuid=False), ForeignKey('organizations.id'), nullable=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey('users.id'))  # Optional link to user account
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    specialties = Column(JSONB, default=[])  # ['electrical', 'hvac', 'security']
    hourly_rate = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    notes = Column(Text)
    extra_data = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="technicians")
    jobs = relationship("Job", back_populates="technician")
    
    __table_args__ = (
        Index('ix_technicians_organization', 'organization_id'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'specialties': self.specialties or [],
            'hourly_rate': self.hourly_rate,
            'is_active': self.is_active,
            'notes': self.notes,
            'metadata': self.extra_data or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# =============================================================================
# SUPPLIERS
# =============================================================================

class Supplier(Base):
    """Suppliers/Vendors."""
    __tablename__ = 'suppliers'
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    organization_id = Column(UUID(as_uuid=False), ForeignKey('organizations.id'), nullable=False)
    name = Column(String(255), nullable=False)
    company = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    address = Column(Text)
    website = Column(String(255))
    account_number = Column(String(100))
    payment_terms = Column(String(100))
    categories = Column(JSONB, default=[])  # ['electrical', 'lighting', 'security']
    is_active = Column(Boolean, default=True)
    notes = Column(Text)
    extra_data = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="suppliers")
    
    __table_args__ = (
        Index('ix_suppliers_organization', 'organization_id'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'name': self.name,
            'company': self.company,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'website': self.website,
            'account_number': self.account_number,
            'payment_terms': self.payment_terms,
            'categories': self.categories or [],
            'is_active': self.is_active,
            'notes': self.notes,
            'metadata': self.extra_data or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# =============================================================================
# INVENTORY
# =============================================================================

class InventoryItem(Base):
    """Inventory/Stock items."""
    __tablename__ = 'inventory_items'
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    organization_id = Column(UUID(as_uuid=False), ForeignKey('organizations.id'), nullable=False)
    supplier_id = Column(UUID(as_uuid=False), ForeignKey('suppliers.id'))
    name = Column(String(255), nullable=False)
    sku = Column(String(100))
    category = Column(String(100))  # lighting, security, hvac, etc.
    description = Column(Text)
    unit_price = Column(Float, default=0)
    cost_price = Column(Float, default=0)
    quantity = Column(Integer, default=0)
    reorder_level = Column(Integer, default=5)
    location = Column(String(255))
    serial_numbers = Column(JSONB, default=[])
    image_url = Column(Text)
    is_active = Column(Boolean, default=True)
    extra_data = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="inventory_items")
    
    __table_args__ = (
        Index('ix_inventory_organization', 'organization_id'),
        Index('ix_inventory_category', 'category'),
        Index('ix_inventory_sku', 'sku'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'supplier_id': self.supplier_id,
            'name': self.name,
            'sku': self.sku,
            'category': self.category,
            'description': self.description,
            'unit_price': self.unit_price,
            'cost_price': self.cost_price,
            'quantity': self.quantity,
            'reorder_level': self.reorder_level,
            'location': self.location,
            'serial_numbers': self.serial_numbers or [],
            'image_url': self.image_url,
            'is_active': self.is_active,
            'metadata': self.extra_data or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# =============================================================================
# PRICE CLASSES (for quote automation)
# =============================================================================

class PriceClass(Base):
    """Price classes for grouping items in quotes."""
    __tablename__ = 'price_classes'
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    organization_id = Column(UUID(as_uuid=False), ForeignKey('organizations.id'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    icon = Column(Text)  # Base64 encoded icon or URL
    color = Column(String(20))
    category = Column(String(100))
    total_price = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    extra_data = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="price_classes")
    items = relationship("PriceClassItem", back_populates="price_class", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_price_classes_organization', 'organization_id'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'name': self.name,
            'description': self.description,
            'icon': self.icon,
            'color': self.color,
            'category': self.category,
            'total_price': self.total_price,
            'items': [item.to_dict() for item in self.items] if self.items else [],
            'is_active': self.is_active,
            'metadata': self.extra_data or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class PriceClassItem(Base):
    """Individual items within a price class."""
    __tablename__ = 'price_class_items'
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    price_class_id = Column(UUID(as_uuid=False), ForeignKey('price_classes.id'), nullable=False)
    inventory_item_id = Column(UUID(as_uuid=False), ForeignKey('inventory_items.id'))
    name = Column(String(255), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    price_class = relationship("PriceClass", back_populates="items")
    
    def to_dict(self):
        return {
            'id': self.id,
            'price_class_id': self.price_class_id,
            'inventory_item_id': self.inventory_item_id,
            'name': self.name,
            'quantity': self.quantity,
            'unit_price': self.unit_price
        }


# =============================================================================
# QUOTES
# =============================================================================

class Quote(Base):
    """Quotes/Estimates."""
    __tablename__ = 'quotes'
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    organization_id = Column(UUID(as_uuid=False), ForeignKey('organizations.id'), nullable=False)
    customer_id = Column(UUID(as_uuid=False), ForeignKey('customers.id'))
    project_id = Column(UUID(as_uuid=False), ForeignKey('projects.id'))
    quote_number = Column(String(50))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default='draft')  # draft, sent, accepted, rejected, expired
    source = Column(String(50), default='customer')  # customer, supplier
    supplier_name = Column(String(255))
    subtotal = Column(Float, default=0)
    markup_percentage = Column(Float, default=20)
    markup_amount = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    labor_cost = Column(Float, default=0)
    materials_cost = Column(Float, default=0)
    valid_until = Column(Date)
    notes = Column(Text)
    
    # Canvas/floorplan data
    canvas_state = Column(JSONB)  # Fabric.js canvas state
    floorplan_image = Column(Text)  # Base64 or path
    components = Column(JSONB, default=[])  # Placed symbols/components
    costs = Column(JSONB, default={})  # Cost breakdown
    analysis = Column(JSONB, default={})  # AI analysis results
    
    extra_data = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="quotes")
    customer = relationship("Customer", back_populates="quotes")
    project = relationship("Project", back_populates="quotes")
    line_items = relationship("QuoteLineItem", back_populates="quote", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_quotes_organization', 'organization_id'),
        Index('ix_quotes_customer', 'customer_id'),
        Index('ix_quotes_project', 'project_id'),
        Index('ix_quotes_status', 'status'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'customer_id': self.customer_id,
            'project_id': self.project_id,
            'quote_number': self.quote_number,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'source': self.source,
            'supplier_name': self.supplier_name,
            'subtotal': self.subtotal,
            'markup_percentage': self.markup_percentage,
            'markup_amount': self.markup_amount,
            'total_amount': self.total_amount,
            'quote_amount': self.total_amount,  # Alias for compatibility
            'labor_cost': self.labor_cost,
            'materials_cost': self.materials_cost,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'notes': self.notes,
            'canvas_state': self.canvas_state,
            'floorplan_image': self.floorplan_image,
            'components': self.components or [],
            'costs': self.costs or {},
            'analysis': self.analysis or {},
            'line_items': [item.to_dict() for item in self.line_items] if self.line_items else [],
            'metadata': self.extra_data or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class QuoteLineItem(Base):
    """Individual line items in a quote."""
    __tablename__ = 'quote_line_items'
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    quote_id = Column(UUID(as_uuid=False), ForeignKey('quotes.id'), nullable=False)
    inventory_item_id = Column(UUID(as_uuid=False), ForeignKey('inventory_items.id'))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, default=0)
    total_price = Column(Float, default=0)
    category = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    quote = relationship("Quote", back_populates="line_items")
    
    def to_dict(self):
        return {
            'id': self.id,
            'quote_id': self.quote_id,
            'inventory_item_id': self.inventory_item_id,
            'name': self.name,
            'description': self.description,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'total_price': self.total_price,
            'category': self.category
        }


# =============================================================================
# COMMUNICATIONS
# =============================================================================

class Communication(Base):
    """Communication records (notes, emails, calls)."""
    __tablename__ = 'communications'
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    organization_id = Column(UUID(as_uuid=False), ForeignKey('organizations.id'), nullable=False)
    customer_id = Column(UUID(as_uuid=False), ForeignKey('customers.id'))
    project_id = Column(UUID(as_uuid=False), ForeignKey('projects.id'))
    job_id = Column(UUID(as_uuid=False), ForeignKey('jobs.id'))
    user_id = Column(UUID(as_uuid=False), ForeignKey('users.id'))
    comm_type = Column(String(50))  # note, email, call, meeting, sms
    subject = Column(String(255))
    content = Column(Text)
    direction = Column(String(20))  # inbound, outbound
    status = Column(String(50))  # sent, received, draft
    extra_data = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="communications")
    customer = relationship("Customer", back_populates="communications")
    
    __table_args__ = (
        Index('ix_communications_organization', 'organization_id'),
        Index('ix_communications_customer', 'customer_id'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'customer_id': self.customer_id,
            'project_id': self.project_id,
            'job_id': self.job_id,
            'user_id': self.user_id,
            'type': self.comm_type,
            'subject': self.subject,
            'content': self.content,
            'direction': self.direction,
            'status': self.status,
            'metadata': self.extra_data or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# =============================================================================
# CALENDAR EVENTS
# =============================================================================

class CalendarEvent(Base):
    """Calendar events and scheduling."""
    __tablename__ = 'calendar_events'
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    organization_id = Column(UUID(as_uuid=False), ForeignKey('organizations.id'), nullable=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey('users.id'))
    customer_id = Column(UUID(as_uuid=False), ForeignKey('customers.id'))
    project_id = Column(UUID(as_uuid=False), ForeignKey('projects.id'))
    job_id = Column(UUID(as_uuid=False), ForeignKey('jobs.id'))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    event_type = Column(String(50))  # meeting, site_visit, deadline, reminder
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    all_day = Column(Boolean, default=False)
    location = Column(String(255))
    attendees = Column(JSONB, default=[])
    is_recurring = Column(Boolean, default=False)
    recurrence_rule = Column(String(255))
    status = Column(String(50), default='scheduled')  # scheduled, completed, cancelled
    extra_data = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="calendar_events")
    
    __table_args__ = (
        Index('ix_calendar_events_organization', 'organization_id'),
        Index('ix_calendar_events_start_time', 'start_time'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'user_id': self.user_id,
            'customer_id': self.customer_id,
            'project_id': self.project_id,
            'job_id': self.job_id,
            'title': self.title,
            'description': self.description,
            'event_type': self.event_type,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'all_day': self.all_day,
            'location': self.location,
            'attendees': self.attendees or [],
            'is_recurring': self.is_recurring,
            'recurrence_rule': self.recurrence_rule,
            'status': self.status,
            'metadata': self.extra_data or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# =============================================================================
# DOCUMENTS
# =============================================================================

class Document(Base):
    """Documents and files."""
    __tablename__ = 'documents'
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    organization_id = Column(UUID(as_uuid=False), ForeignKey('organizations.id'), nullable=False)
    project_id = Column(UUID(as_uuid=False), ForeignKey('projects.id'))
    quote_id = Column(UUID(as_uuid=False), ForeignKey('quotes.id'))
    name = Column(String(255), nullable=False)
    file_path = Column(Text)
    file_url = Column(Text)
    mime_type = Column(String(100))
    file_size = Column(Integer)
    doc_type = Column(String(50))  # floorplan, quote_pdf, contract, photo, etc.
    description = Column(Text)
    extra_data = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="documents")
    project = relationship("Project", back_populates="documents")
    
    __table_args__ = (
        Index('ix_documents_organization', 'organization_id'),
        Index('ix_documents_project', 'project_id'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'project_id': self.project_id,
            'quote_id': self.quote_id,
            'name': self.name,
            'file_path': self.file_path,
            'file_url': self.file_url,
            'mime_type': self.mime_type,
            'file_size': self.file_size,
            'doc_type': self.doc_type,
            'description': self.description,
            'metadata': self.extra_data or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# =============================================================================
# PAYMENTS
# =============================================================================

class Payment(Base):
    """Payment records for tracking money in and out."""
    __tablename__ = 'payments'
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    organization_id = Column(UUID(as_uuid=False), ForeignKey('organizations.id'), nullable=False)
    customer_id = Column(UUID(as_uuid=False), ForeignKey('customers.id'))
    supplier_id = Column(UUID(as_uuid=False), ForeignKey('suppliers.id'))
    project_id = Column(UUID(as_uuid=False), ForeignKey('projects.id'))
    quote_id = Column(UUID(as_uuid=False), ForeignKey('quotes.id'))
    job_id = Column(UUID(as_uuid=False), ForeignKey('jobs.id'))
    direction = Column(String(50), default='to_us')  # to_us, to_suppliers
    status = Column(String(50), default='pending')  # upcoming, pending, due, paid, credit, retention
    amount = Column(Float, default=0)
    due_date = Column(Date)
    paid_date = Column(Date)
    invoice_number = Column(String(100))
    invoice_pdf = Column(Text)  # Path or URL to invoice
    payment_method = Column(String(50))  # bank_transfer, card, cash, etc.
    notes = Column(Text)
    linked_to = Column(JSONB, default={})  # Legacy field for linking
    person_id = Column(String(255))  # Legacy field
    extra_data = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_payments_organization', 'organization_id'),
        Index('ix_payments_direction', 'direction'),
        Index('ix_payments_status', 'status'),
        Index('ix_payments_due_date', 'due_date'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'customer_id': self.customer_id,
            'supplier_id': self.supplier_id,
            'project_id': self.project_id,
            'quote_id': self.quote_id,
            'job_id': self.job_id,
            'direction': self.direction,
            'status': self.status,
            'amount': self.amount,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'paid_date': self.paid_date.isoformat() if self.paid_date else None,
            'invoice_number': self.invoice_number,
            'invoice_pdf': self.invoice_pdf,
            'payment_method': self.payment_method,
            'notes': self.notes,
            'linked_to': self.linked_to or {},
            'person_id': self.person_id,
            'metadata': self.extra_data or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# =============================================================================
# KANBAN TASKS
# =============================================================================

class KanbanTask(Base):
    """Kanban board tasks for project/operations management."""
    __tablename__ = 'kanban_tasks'
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    organization_id = Column(UUID(as_uuid=False), ForeignKey('organizations.id'), nullable=False)
    project_id = Column(UUID(as_uuid=False), ForeignKey('projects.id'))
    job_id = Column(UUID(as_uuid=False), ForeignKey('jobs.id'))
    column = Column(String(50), default='todo')  # todo, in_progress, review, done
    content = Column(Text, nullable=False)
    notes = Column(Text)
    color = Column(String(20), default='#ffffff')
    position_x = Column(Float, default=10)
    position_y = Column(Float, default=10)
    assigned_to = Column(String(255))  # User ID or name
    pinned = Column(Boolean, default=False)
    due_date = Column(Date)
    priority = Column(String(20), default='normal')  # low, normal, high, urgent
    archived = Column(Boolean, default=False)
    archived_at = Column(DateTime)
    extra_data = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_kanban_tasks_organization', 'organization_id'),
        Index('ix_kanban_tasks_column', 'column'),
        Index('ix_kanban_tasks_archived', 'archived'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'project_id': self.project_id,
            'job_id': self.job_id,
            'column': self.column,
            'content': self.content,
            'notes': self.notes,
            'color': self.color,
            'position': {'x': self.position_x or 10, 'y': self.position_y or 10},
            'position_x': self.position_x,
            'position_y': self.position_y,
            'assigned_to': self.assigned_to,
            'pinned': self.pinned,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'priority': self.priority,
            'archived': self.archived,
            'archived_at': self.archived_at.isoformat() if self.archived_at else None,
            'metadata': self.extra_data or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# =============================================================================
# AI - EVENT LOG
# =============================================================================

class EventLog(Base):
    """
    Event log for tracking all system activity.
    Powers automation, reminders, and AI reasoning over history.
    """
    __tablename__ = 'event_log'
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    organization_id = Column(UUID(as_uuid=False), ForeignKey('organizations.id'))
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    actor_type = Column(String(50))  # user, system, agent
    actor_id = Column(UUID(as_uuid=False))
    entity_type = Column(String(50), nullable=False)  # customer, project, job, etc.
    entity_id = Column(UUID(as_uuid=False), nullable=False)
    event_type = Column(String(100), nullable=False)  # CREATED, UPDATED, STATUS_CHANGED, etc.
    description = Column(Text)
    extra_data = Column(JSONB, default={})
    
    __table_args__ = (
        Index('ix_event_log_organization', 'organization_id'),
        Index('ix_event_log_entity', 'entity_type', 'entity_id'),
        Index('ix_event_log_timestamp', 'timestamp'),
        Index('ix_event_log_event_type', 'event_type'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'actor_type': self.actor_type,
            'actor_id': self.actor_id,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'event_type': self.event_type,
            'description': self.description,
            'metadata': self.extra_data or {}
        }


# =============================================================================
# NOTIFICATIONS
# =============================================================================

class Notification(Base):
    """User notifications for alerts, reminders, and system messages."""
    __tablename__ = 'notifications'
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    organization_id = Column(UUID(as_uuid=False), ForeignKey('organizations.id'), nullable=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey('users.id'))  # None = broadcast to all
    title = Column(String(255), nullable=False)
    message = Column(Text)
    notification_type = Column(String(50), default='info')  # info, warning, alert, reminder, success
    priority = Column(String(20), default='normal')  # low, normal, high, urgent
    entity_type = Column(String(50))  # Related entity type
    entity_id = Column(UUID(as_uuid=False))  # Related entity ID
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    sent_email = Column(Boolean, default=False)
    extra_data = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_notifications_organization', 'organization_id'),
        Index('ix_notifications_user', 'user_id'),
        Index('ix_notifications_is_read', 'is_read'),
        Index('ix_notifications_created_at', 'created_at'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message,
            'notification_type': self.notification_type,
            'priority': self.priority,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'is_read': self.is_read,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'sent_email': self.sent_email,
            'metadata': self.extra_data or {},
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# =============================================================================
# AI - DOCUMENT INDEX
# =============================================================================

class DocumentIndex(Base):
    """
    Document index for AI retrieval.
    Tracks all AI-relevant documents with extracted text and metadata.
    """
    __tablename__ = 'document_index'
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    organization_id = Column(UUID(as_uuid=False), ForeignKey('organizations.id'))
    source_table = Column(String(100), nullable=False)  # projects, jobs, documents, etc.
    source_id = Column(UUID(as_uuid=False), nullable=False)
    path_or_name = Column(Text)
    mime_type = Column(String(100))
    text_content = Column(Text)  # Extracted text for AI
    summary = Column(Text)  # AI-generated summary
    embedding = Column(JSONB)  # Placeholder for vector embeddings
    status = Column(String(50), default='raw')  # raw, indexed, error
    extra_metadata = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_document_index_organization', 'organization_id'),
        Index('ix_document_index_source', 'source_table', 'source_id'),
        Index('ix_document_index_status', 'status'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'source_table': self.source_table,
            'source_id': self.source_id,
            'path_or_name': self.path_or_name,
            'mime_type': self.mime_type,
            'text_content': self.text_content,
            'summary': self.summary,
            'status': self.status,
            'extra_metadata': self.extra_metadata or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

