"""
Database package for LockZone AI Floorplan application.
Provides SQLAlchemy models, connection management, and session handling.
"""

from database.connection import (
    engine,
    SessionLocal,
    Base,
    get_db,
    init_db,
    check_db_connection
)

from database.models import (
    Organization,
    User,
    Customer,
    Project,
    Job,
    Technician,
    Supplier,
    InventoryItem,
    PriceClass,
    PriceClassItem,
    Quote,
    QuoteLineItem,
    Communication,
    CalendarEvent,
    Document,
    EventLog,
    DocumentIndex
)

__all__ = [
    # Connection
    'engine',
    'SessionLocal',
    'Base',
    'get_db',
    'init_db',
    'check_db_connection',
    # Models
    'Organization',
    'User',
    'Customer',
    'Project',
    'Job',
    'Technician',
    'Supplier',
    'InventoryItem',
    'PriceClass',
    'PriceClassItem',
    'Quote',
    'QuoteLineItem',
    'Communication',
    'CalendarEvent',
    'Document',
    'EventLog',
    'DocumentIndex'
]

