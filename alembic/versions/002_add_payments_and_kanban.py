"""Add payments and kanban_tasks tables

Revision ID: 002
Revises: 001
Create Date: 2025-11-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Create payments table
    op.create_table('payments',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('quote_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('direction', sa.String(50), nullable=True, server_default='to_us'),
        sa.Column('status', sa.String(50), nullable=True, server_default='pending'),
        sa.Column('amount', sa.Float(), nullable=True, server_default='0'),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('paid_date', sa.Date(), nullable=True),
        sa.Column('invoice_number', sa.String(100), nullable=True),
        sa.Column('invoice_pdf', sa.Text(), nullable=True),
        sa.Column('payment_method', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('linked_to', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('person_id', sa.String(255), nullable=True),
        sa.Column('extra_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], ),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_payments_direction', 'payments', ['direction'], unique=False)
    op.create_index('ix_payments_due_date', 'payments', ['due_date'], unique=False)
    op.create_index('ix_payments_organization', 'payments', ['organization_id'], unique=False)
    op.create_index('ix_payments_status', 'payments', ['status'], unique=False)

    # Create kanban_tasks table
    op.create_table('kanban_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('column', sa.String(50), nullable=True, server_default='todo'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('color', sa.String(20), nullable=True, server_default='#ffffff'),
        sa.Column('position_x', sa.Float(), nullable=True, server_default='10'),
        sa.Column('position_y', sa.Float(), nullable=True, server_default='10'),
        sa.Column('assigned_to', sa.String(255), nullable=True),
        sa.Column('pinned', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('priority', sa.String(20), nullable=True, server_default='normal'),
        sa.Column('archived', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('archived_at', sa.DateTime(), nullable=True),
        sa.Column('extra_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_kanban_tasks_archived', 'kanban_tasks', ['archived'], unique=False)
    op.create_index('ix_kanban_tasks_column', 'kanban_tasks', ['column'], unique=False)
    op.create_index('ix_kanban_tasks_organization', 'kanban_tasks', ['organization_id'], unique=False)


def downgrade():
    op.drop_index('ix_kanban_tasks_organization', table_name='kanban_tasks')
    op.drop_index('ix_kanban_tasks_column', table_name='kanban_tasks')
    op.drop_index('ix_kanban_tasks_archived', table_name='kanban_tasks')
    op.drop_table('kanban_tasks')
    
    op.drop_index('ix_payments_status', table_name='payments')
    op.drop_index('ix_payments_organization', table_name='payments')
    op.drop_index('ix_payments_due_date', table_name='payments')
    op.drop_index('ix_payments_direction', table_name='payments')
    op.drop_table('payments')

