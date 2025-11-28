"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2025-11-28

Creates all core tables for the LockZone AI Floorplan application.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Organizations table
    op.create_table('organizations',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('settings', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )

    # Users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('display_name', sa.String(255)),
        sa.Column('role', sa.String(50), default='user'),
        sa.Column('permissions', postgresql.JSONB, default=[]),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('last_login', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_organization', 'users', ['organization_id'])

    # Customers table
    op.create_table('customers',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('company', sa.String(255)),
        sa.Column('email', sa.String(255)),
        sa.Column('phone', sa.String(50)),
        sa.Column('address', sa.Text()),
        sa.Column('city', sa.String(100)),
        sa.Column('state', sa.String(100)),
        sa.Column('postal_code', sa.String(20)),
        sa.Column('country', sa.String(100), default='Australia'),
        sa.Column('notes', sa.Text()),
        sa.Column('tags', postgresql.JSONB, default=[]),
        sa.Column('extra_data', postgresql.JSONB, default={}),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_customers_organization', 'customers', ['organization_id'])
    op.create_index('ix_customers_email', 'customers', ['email'])
    op.create_index('ix_customers_name', 'customers', ['name'])

    # Suppliers table
    op.create_table('suppliers',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('company', sa.String(255)),
        sa.Column('email', sa.String(255)),
        sa.Column('phone', sa.String(50)),
        sa.Column('address', sa.Text()),
        sa.Column('website', sa.String(255)),
        sa.Column('account_number', sa.String(100)),
        sa.Column('payment_terms', sa.String(100)),
        sa.Column('categories', postgresql.JSONB, default=[]),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('notes', sa.Text()),
        sa.Column('extra_data', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_suppliers_organization', 'suppliers', ['organization_id'])

    # Technicians table
    op.create_table('technicians',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False)),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255)),
        sa.Column('phone', sa.String(50)),
        sa.Column('specialties', postgresql.JSONB, default=[]),
        sa.Column('hourly_rate', sa.Float(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('notes', sa.Text()),
        sa.Column('extra_data', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_technicians_organization', 'technicians', ['organization_id'])

    # Inventory items table
    op.create_table('inventory_items',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=False)),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('sku', sa.String(100)),
        sa.Column('category', sa.String(100)),
        sa.Column('description', sa.Text()),
        sa.Column('unit_price', sa.Float(), default=0),
        sa.Column('cost_price', sa.Float(), default=0),
        sa.Column('quantity', sa.Integer(), default=0),
        sa.Column('reorder_level', sa.Integer(), default=5),
        sa.Column('location', sa.String(255)),
        sa.Column('serial_numbers', postgresql.JSONB, default=[]),
        sa.Column('image_url', sa.Text()),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('extra_data', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_inventory_organization', 'inventory_items', ['organization_id'])
    op.create_index('ix_inventory_category', 'inventory_items', ['category'])
    op.create_index('ix_inventory_sku', 'inventory_items', ['sku'])

    # Projects table
    op.create_table('projects',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=False)),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('project_type', sa.String(100)),
        sa.Column('address', sa.Text()),
        sa.Column('start_date', sa.Date()),
        sa.Column('end_date', sa.Date()),
        sa.Column('estimated_value', sa.Float(), default=0),
        sa.Column('actual_value', sa.Float(), default=0),
        sa.Column('notes', sa.Text()),
        sa.Column('extra_data', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_projects_organization', 'projects', ['organization_id'])
    op.create_index('ix_projects_customer', 'projects', ['customer_id'])
    op.create_index('ix_projects_status', 'projects', ['status'])

    # Jobs table
    op.create_table('jobs',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=False)),
        sa.Column('technician_id', postgresql.UUID(as_uuid=False)),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('priority', sa.String(20), default='normal'),
        sa.Column('job_type', sa.String(100)),
        sa.Column('scheduled_date', sa.DateTime()),
        sa.Column('completed_date', sa.DateTime()),
        sa.Column('estimated_hours', sa.Float()),
        sa.Column('actual_hours', sa.Float()),
        sa.Column('labor_cost', sa.Float(), default=0),
        sa.Column('materials_cost', sa.Float(), default=0),
        sa.Column('notes', sa.Text()),
        sa.Column('extra_data', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['technician_id'], ['technicians.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_jobs_organization', 'jobs', ['organization_id'])
    op.create_index('ix_jobs_project', 'jobs', ['project_id'])
    op.create_index('ix_jobs_technician', 'jobs', ['technician_id'])
    op.create_index('ix_jobs_status', 'jobs', ['status'])
    op.create_index('ix_jobs_scheduled_date', 'jobs', ['scheduled_date'])

    # Price classes table
    op.create_table('price_classes',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('icon', sa.Text()),
        sa.Column('color', sa.String(20)),
        sa.Column('category', sa.String(100)),
        sa.Column('total_price', sa.Float(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('extra_data', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_price_classes_organization', 'price_classes', ['organization_id'])

    # Price class items table
    op.create_table('price_class_items',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('price_class_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('inventory_item_id', postgresql.UUID(as_uuid=False)),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('quantity', sa.Integer(), default=1),
        sa.Column('unit_price', sa.Float(), default=0),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.ForeignKeyConstraint(['price_class_id'], ['price_classes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['inventory_item_id'], ['inventory_items.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Quotes table
    op.create_table('quotes',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=False)),
        sa.Column('project_id', postgresql.UUID(as_uuid=False)),
        sa.Column('quote_number', sa.String(50)),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('status', sa.String(50), default='draft'),
        sa.Column('source', sa.String(50), default='customer'),
        sa.Column('supplier_name', sa.String(255)),
        sa.Column('subtotal', sa.Float(), default=0),
        sa.Column('markup_percentage', sa.Float(), default=20),
        sa.Column('markup_amount', sa.Float(), default=0),
        sa.Column('total_amount', sa.Float(), default=0),
        sa.Column('labor_cost', sa.Float(), default=0),
        sa.Column('materials_cost', sa.Float(), default=0),
        sa.Column('valid_until', sa.Date()),
        sa.Column('notes', sa.Text()),
        sa.Column('canvas_state', postgresql.JSONB),
        sa.Column('floorplan_image', sa.Text()),
        sa.Column('components', postgresql.JSONB, default=[]),
        sa.Column('costs', postgresql.JSONB, default={}),
        sa.Column('analysis', postgresql.JSONB, default={}),
        sa.Column('extra_data', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_quotes_organization', 'quotes', ['organization_id'])
    op.create_index('ix_quotes_customer', 'quotes', ['customer_id'])
    op.create_index('ix_quotes_project', 'quotes', ['project_id'])
    op.create_index('ix_quotes_status', 'quotes', ['status'])

    # Quote line items table
    op.create_table('quote_line_items',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('quote_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('inventory_item_id', postgresql.UUID(as_uuid=False)),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('quantity', sa.Integer(), default=1),
        sa.Column('unit_price', sa.Float(), default=0),
        sa.Column('total_price', sa.Float(), default=0),
        sa.Column('category', sa.String(100)),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['inventory_item_id'], ['inventory_items.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Communications table
    op.create_table('communications',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=False)),
        sa.Column('project_id', postgresql.UUID(as_uuid=False)),
        sa.Column('job_id', postgresql.UUID(as_uuid=False)),
        sa.Column('user_id', postgresql.UUID(as_uuid=False)),
        sa.Column('comm_type', sa.String(50)),
        sa.Column('subject', sa.String(255)),
        sa.Column('content', sa.Text()),
        sa.Column('direction', sa.String(20)),
        sa.Column('status', sa.String(50)),
        sa.Column('extra_data', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_communications_organization', 'communications', ['organization_id'])
    op.create_index('ix_communications_customer', 'communications', ['customer_id'])

    # Calendar events table
    op.create_table('calendar_events',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False)),
        sa.Column('customer_id', postgresql.UUID(as_uuid=False)),
        sa.Column('project_id', postgresql.UUID(as_uuid=False)),
        sa.Column('job_id', postgresql.UUID(as_uuid=False)),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('event_type', sa.String(50)),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime()),
        sa.Column('all_day', sa.Boolean(), default=False),
        sa.Column('location', sa.String(255)),
        sa.Column('attendees', postgresql.JSONB, default=[]),
        sa.Column('is_recurring', sa.Boolean(), default=False),
        sa.Column('recurrence_rule', sa.String(255)),
        sa.Column('status', sa.String(50), default='scheduled'),
        sa.Column('extra_data', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_calendar_events_organization', 'calendar_events', ['organization_id'])
    op.create_index('ix_calendar_events_start_time', 'calendar_events', ['start_time'])

    # Documents table
    op.create_table('documents',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=False)),
        sa.Column('quote_id', postgresql.UUID(as_uuid=False)),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('file_path', sa.Text()),
        sa.Column('file_url', sa.Text()),
        sa.Column('mime_type', sa.String(100)),
        sa.Column('file_size', sa.Integer()),
        sa.Column('doc_type', sa.String(50)),
        sa.Column('description', sa.Text()),
        sa.Column('extra_data', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_documents_organization', 'documents', ['organization_id'])
    op.create_index('ix_documents_project', 'documents', ['project_id'])

    # Event log table
    op.create_table('event_log',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=False)),
        sa.Column('timestamp', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('actor_type', sa.String(50)),
        sa.Column('actor_id', postgresql.UUID(as_uuid=False)),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('extra_data', postgresql.JSONB, default={}),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_event_log_organization', 'event_log', ['organization_id'])
    op.create_index('ix_event_log_entity', 'event_log', ['entity_type', 'entity_id'])
    op.create_index('ix_event_log_timestamp', 'event_log', ['timestamp'])
    op.create_index('ix_event_log_event_type', 'event_log', ['event_type'])

    # Document index table
    op.create_table('document_index',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=False)),
        sa.Column('source_table', sa.String(100), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('path_or_name', sa.Text()),
        sa.Column('mime_type', sa.String(100)),
        sa.Column('text_content', sa.Text()),
        sa.Column('summary', sa.Text()),
        sa.Column('embedding', postgresql.JSONB),
        sa.Column('status', sa.String(50), default='raw'),
        sa.Column('extra_metadata', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_document_index_organization', 'document_index', ['organization_id'])
    op.create_index('ix_document_index_source', 'document_index', ['source_table', 'source_id'])
    op.create_index('ix_document_index_status', 'document_index', ['status'])


def downgrade() -> None:
    # Drop tables in reverse order of creation (respecting foreign keys)
    op.drop_table('document_index')
    op.drop_table('event_log')
    op.drop_table('documents')
    op.drop_table('calendar_events')
    op.drop_table('communications')
    op.drop_table('quote_line_items')
    op.drop_table('quotes')
    op.drop_table('price_class_items')
    op.drop_table('price_classes')
    op.drop_table('jobs')
    op.drop_table('projects')
    op.drop_table('inventory_items')
    op.drop_table('technicians')
    op.drop_table('suppliers')
    op.drop_table('customers')
    op.drop_table('users')
    op.drop_table('organizations')

