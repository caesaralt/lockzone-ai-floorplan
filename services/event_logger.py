"""
Event Logger Service - Tracks all system activity for AI learning and automation.

This service logs all significant events in the system, creating a comprehensive
audit trail that can be used by AI for:
- Understanding context and history
- Learning patterns in user behavior
- Providing intelligent suggestions
- Automating routine tasks
"""

import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Event types for different operations
EVENT_TYPES = {
    # CRUD Operations
    'CREATED': 'Entity was created',
    'UPDATED': 'Entity was updated',
    'DELETED': 'Entity was deleted',
    
    # Status changes
    'STATUS_CHANGED': 'Status was changed',
    'ASSIGNED': 'Entity was assigned to someone',
    'UNASSIGNED': 'Entity was unassigned',
    
    # Quote/Project lifecycle
    'QUOTE_SENT': 'Quote was sent to customer',
    'QUOTE_ACCEPTED': 'Quote was accepted',
    'QUOTE_REJECTED': 'Quote was rejected',
    'QUOTE_EXPIRED': 'Quote expired',
    'PROJECT_STARTED': 'Project work started',
    'PROJECT_COMPLETED': 'Project was completed',
    
    # Job lifecycle
    'JOB_SCHEDULED': 'Job was scheduled',
    'JOB_STARTED': 'Job work started',
    'JOB_COMPLETED': 'Job was completed',
    'JOB_CANCELLED': 'Job was cancelled',
    
    # Payment events
    'PAYMENT_RECEIVED': 'Payment was received',
    'PAYMENT_SENT': 'Payment was sent',
    'INVOICE_GENERATED': 'Invoice was generated',
    'PAYMENT_OVERDUE': 'Payment is overdue',
    
    # Communication events
    'EMAIL_SENT': 'Email was sent',
    'EMAIL_RECEIVED': 'Email was received',
    'CALL_LOGGED': 'Phone call was logged',
    'NOTE_ADDED': 'Note was added',
    
    # Calendar events
    'EVENT_SCHEDULED': 'Calendar event was scheduled',
    'EVENT_COMPLETED': 'Calendar event was completed',
    'EVENT_CANCELLED': 'Calendar event was cancelled',
    'REMINDER_TRIGGERED': 'Reminder was triggered',
    
    # Inventory events
    'STOCK_ADDED': 'Stock was added',
    'STOCK_REMOVED': 'Stock was removed',
    'LOW_STOCK_ALERT': 'Low stock alert triggered',
    'REORDER_NEEDED': 'Reorder needed',
    
    # AI events
    'AI_ANALYSIS_COMPLETED': 'AI analysis was completed',
    'AI_SUGGESTION_MADE': 'AI made a suggestion',
    'AI_ACTION_TAKEN': 'AI took an automated action',
    
    # User events
    'USER_LOGIN': 'User logged in',
    'USER_LOGOUT': 'User logged out',
    'PERMISSION_CHANGED': 'User permission was changed',
}

# Entity types
ENTITY_TYPES = [
    'customer', 'project', 'quote', 'job', 'technician', 'supplier',
    'inventory_item', 'price_class', 'payment', 'communication',
    'calendar_event', 'kanban_task', 'document', 'user'
]


class EventLogger:
    """Service for logging system events to the database."""
    
    def __init__(self, session, organization_id: str, actor_type: str = 'system', actor_id: str = None):
        """
        Initialize the event logger.
        
        Args:
            session: SQLAlchemy database session
            organization_id: The organization ID for multi-tenancy
            actor_type: Type of actor (user, system, agent)
            actor_id: ID of the actor (user ID if user, None if system)
        """
        self.session = session
        self.organization_id = organization_id
        self.actor_type = actor_type
        self.actor_id = actor_id
    
    def log(self, entity_type: str, entity_id: str, event_type: str,
            description: str = None, metadata: Dict = None) -> Optional[Dict]:
        """
        Log an event to the database.
        
        Args:
            entity_type: Type of entity (customer, project, quote, etc.)
            entity_id: ID of the entity
            event_type: Type of event (CREATED, UPDATED, etc.)
            description: Human-readable description of the event
            metadata: Additional data about the event
        
        Returns:
            The created event log entry as a dict, or None on failure
        """
        try:
            from database.models import EventLog
            
            event = EventLog(
                organization_id=self.organization_id,
                timestamp=datetime.utcnow(),
                actor_type=self.actor_type,
                actor_id=self.actor_id,
                entity_type=entity_type,
                entity_id=entity_id,
                event_type=event_type,
                description=description or EVENT_TYPES.get(event_type, event_type),
                extra_data=metadata or {}
            )
            
            self.session.add(event)
            self.session.flush()
            
            logger.debug(f"Event logged: {event_type} on {entity_type}:{entity_id}")
            return event.to_dict()
            
        except Exception as e:
            logger.error(f"Failed to log event: {e}")
            return None
    
    def log_create(self, entity_type: str, entity_id: str, entity_data: Dict = None) -> Optional[Dict]:
        """Log a creation event."""
        return self.log(
            entity_type=entity_type,
            entity_id=entity_id,
            event_type='CREATED',
            description=f"New {entity_type} created",
            metadata={'data': entity_data} if entity_data else None
        )
    
    def log_update(self, entity_type: str, entity_id: str, 
                   changes: Dict = None, old_values: Dict = None) -> Optional[Dict]:
        """Log an update event with change tracking."""
        metadata = {}
        if changes:
            metadata['changes'] = changes
        if old_values:
            metadata['previous_values'] = old_values
        
        return self.log(
            entity_type=entity_type,
            entity_id=entity_id,
            event_type='UPDATED',
            description=f"{entity_type.capitalize()} was updated",
            metadata=metadata if metadata else None
        )
    
    def log_delete(self, entity_type: str, entity_id: str, entity_data: Dict = None) -> Optional[Dict]:
        """Log a deletion event."""
        return self.log(
            entity_type=entity_type,
            entity_id=entity_id,
            event_type='DELETED',
            description=f"{entity_type.capitalize()} was deleted",
            metadata={'deleted_data': entity_data} if entity_data else None
        )
    
    def log_status_change(self, entity_type: str, entity_id: str,
                          old_status: str, new_status: str) -> Optional[Dict]:
        """Log a status change event."""
        return self.log(
            entity_type=entity_type,
            entity_id=entity_id,
            event_type='STATUS_CHANGED',
            description=f"{entity_type.capitalize()} status changed from '{old_status}' to '{new_status}'",
            metadata={'old_status': old_status, 'new_status': new_status}
        )
    
    def get_entity_history(self, entity_type: str, entity_id: str, 
                           limit: int = 50) -> List[Dict]:
        """Get the event history for a specific entity."""
        try:
            from database.models import EventLog
            
            events = self.session.query(EventLog).filter(
                EventLog.organization_id == self.organization_id,
                EventLog.entity_type == entity_type,
                EventLog.entity_id == entity_id
            ).order_by(EventLog.timestamp.desc()).limit(limit).all()
            
            return [e.to_dict() for e in events]
            
        except Exception as e:
            logger.error(f"Failed to get entity history: {e}")
            return []
    
    def get_recent_events(self, hours: int = 24, event_types: List[str] = None,
                          entity_types: List[str] = None, limit: int = 100) -> List[Dict]:
        """Get recent events with optional filtering."""
        try:
            from database.models import EventLog
            
            since = datetime.utcnow() - timedelta(hours=hours)
            
            query = self.session.query(EventLog).filter(
                EventLog.organization_id == self.organization_id,
                EventLog.timestamp >= since
            )
            
            if event_types:
                query = query.filter(EventLog.event_type.in_(event_types))
            
            if entity_types:
                query = query.filter(EventLog.entity_type.in_(entity_types))
            
            events = query.order_by(EventLog.timestamp.desc()).limit(limit).all()
            
            return [e.to_dict() for e in events]
            
        except Exception as e:
            logger.error(f"Failed to get recent events: {e}")
            return []
    
    def get_activity_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get a summary of activity for AI context."""
        try:
            from database.models import EventLog
            from sqlalchemy import func
            
            since = datetime.utcnow() - timedelta(days=days)
            
            # Count events by type
            event_counts = self.session.query(
                EventLog.event_type,
                func.count(EventLog.id).label('count')
            ).filter(
                EventLog.organization_id == self.organization_id,
                EventLog.timestamp >= since
            ).group_by(EventLog.event_type).all()
            
            # Count events by entity type
            entity_counts = self.session.query(
                EventLog.entity_type,
                func.count(EventLog.id).label('count')
            ).filter(
                EventLog.organization_id == self.organization_id,
                EventLog.timestamp >= since
            ).group_by(EventLog.entity_type).all()
            
            # Get most recent events
            recent = self.get_recent_events(hours=24, limit=10)
            
            return {
                'period_days': days,
                'event_type_counts': {e[0]: e[1] for e in event_counts},
                'entity_type_counts': {e[0]: e[1] for e in entity_counts},
                'total_events': sum(e[1] for e in event_counts),
                'recent_events': recent
            }
            
        except Exception as e:
            logger.error(f"Failed to get activity summary: {e}")
            return {}


def get_event_logger(session, organization_id: str, user_id: str = None) -> EventLogger:
    """
    Factory function to create an EventLogger instance.
    
    Args:
        session: SQLAlchemy database session
        organization_id: Organization ID
        user_id: Optional user ID if the actor is a user
    
    Returns:
        EventLogger instance
    """
    actor_type = 'user' if user_id else 'system'
    return EventLogger(session, organization_id, actor_type, user_id)


@contextmanager
def logged_operation(session, organization_id: str, entity_type: str, 
                     entity_id: str, operation: str, user_id: str = None):
    """
    Context manager for logging operations with automatic event logging.
    
    Usage:
        with logged_operation(session, org_id, 'customer', customer_id, 'UPDATED'):
            # Perform the operation
            customer.name = new_name
    """
    event_logger = get_event_logger(session, organization_id, user_id)
    
    try:
        yield event_logger
        # Log success after the operation
        event_logger.log(entity_type, entity_id, operation)
    except Exception as e:
        # Log failure
        event_logger.log(
            entity_type, entity_id, f'{operation}_FAILED',
            description=f"Operation failed: {str(e)}",
            metadata={'error': str(e)}
        )
        raise

