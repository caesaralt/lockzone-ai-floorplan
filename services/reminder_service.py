"""
Reminder Service - Automated task and reminder system.

This service checks for items that need attention and can trigger
notifications, create tasks, or log events for the AI to act on.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

logger = logging.getLogger(__name__)


# Reminder types and their configurations
REMINDER_CONFIGS = {
    'quote_followup': {
        'description': 'Follow up on quotes that have been sent but not responded to',
        'days_threshold': 7,
        'priority': 'normal'
    },
    'quote_expiring': {
        'description': 'Quotes that are about to expire',
        'days_threshold': 3,
        'priority': 'high'
    },
    'payment_overdue': {
        'description': 'Payments that are past their due date',
        'days_threshold': 0,
        'priority': 'urgent'
    },
    'payment_upcoming': {
        'description': 'Payments coming due soon',
        'days_threshold': 7,
        'priority': 'normal'
    },
    'low_stock': {
        'description': 'Inventory items below reorder level',
        'priority': 'normal'
    },
    'job_overdue': {
        'description': 'Jobs that are past their scheduled date',
        'days_threshold': 0,
        'priority': 'high'
    },
    'task_stale': {
        'description': 'Tasks that have been in progress for too long',
        'days_threshold': 3,
        'priority': 'normal'
    },
    'event_upcoming': {
        'description': 'Calendar events coming up soon',
        'hours_threshold': 24,
        'priority': 'normal'
    }
}


class ReminderService:
    """Service for checking and generating automated reminders."""
    
    def __init__(self, session: Session, organization_id: str):
        self.session = session
        self.organization_id = organization_id
    
    def check_all_reminders(self) -> Dict[str, List[Dict]]:
        """
        Check all reminder types and return items needing attention.
        
        Returns a dictionary with reminder types as keys and lists of
        items needing attention as values.
        """
        reminders = {}
        
        # Check each reminder type
        reminders['quote_followup'] = self.check_quote_followups()
        reminders['quote_expiring'] = self.check_expiring_quotes()
        reminders['payment_overdue'] = self.check_overdue_payments()
        reminders['payment_upcoming'] = self.check_upcoming_payments()
        reminders['low_stock'] = self.check_low_stock()
        reminders['job_overdue'] = self.check_overdue_jobs()
        reminders['task_stale'] = self.check_stale_tasks()
        reminders['event_upcoming'] = self.check_upcoming_events()
        
        # Filter out empty categories
        reminders = {k: v for k, v in reminders.items() if v}
        
        return reminders
    
    def check_quote_followups(self) -> List[Dict]:
        """Check for quotes that need follow-up."""
        try:
            from database.models import Quote
            
            threshold = datetime.utcnow() - timedelta(days=REMINDER_CONFIGS['quote_followup']['days_threshold'])
            
            quotes = self.session.query(Quote).filter(
                Quote.organization_id == self.organization_id,
                Quote.status == 'sent',
                Quote.updated_at <= threshold
            ).all()
            
            return [{
                'type': 'quote_followup',
                'entity_type': 'quote',
                'entity_id': q.id,
                'title': f"Follow up on quote: {q.title}",
                'description': f"Quote sent {(datetime.utcnow() - q.updated_at).days} days ago, no response yet",
                'amount': q.total_amount,
                'priority': REMINDER_CONFIGS['quote_followup']['priority'],
                'created_at': datetime.utcnow().isoformat()
            } for q in quotes]
        except Exception as e:
            logger.error(f"Error checking quote followups: {e}")
            return []
    
    def check_expiring_quotes(self) -> List[Dict]:
        """Check for quotes that are about to expire."""
        try:
            from database.models import Quote
            
            today = datetime.utcnow().date()
            threshold = today + timedelta(days=REMINDER_CONFIGS['quote_expiring']['days_threshold'])
            
            quotes = self.session.query(Quote).filter(
                Quote.organization_id == self.organization_id,
                Quote.status.in_(['draft', 'sent']),
                Quote.valid_until != None,
                Quote.valid_until <= threshold,
                Quote.valid_until >= today
            ).all()
            
            return [{
                'type': 'quote_expiring',
                'entity_type': 'quote',
                'entity_id': q.id,
                'title': f"Quote expiring soon: {q.title}",
                'description': f"Quote expires on {q.valid_until}",
                'amount': q.total_amount,
                'priority': REMINDER_CONFIGS['quote_expiring']['priority'],
                'expires_in_days': (q.valid_until - today).days,
                'created_at': datetime.utcnow().isoformat()
            } for q in quotes]
        except Exception as e:
            logger.error(f"Error checking expiring quotes: {e}")
            return []
    
    def check_overdue_payments(self) -> List[Dict]:
        """Check for overdue payments."""
        try:
            from database.models import Payment
            
            today = datetime.utcnow().date()
            
            payments = self.session.query(Payment).filter(
                Payment.organization_id == self.organization_id,
                Payment.status.in_(['pending', 'due']),
                Payment.due_date != None,
                Payment.due_date < today
            ).all()
            
            return [{
                'type': 'payment_overdue',
                'entity_type': 'payment',
                'entity_id': p.id,
                'title': f"Overdue payment: ${p.amount}",
                'description': f"Payment was due on {p.due_date}, {(today - p.due_date).days} days overdue",
                'amount': p.amount,
                'direction': p.direction,
                'priority': REMINDER_CONFIGS['payment_overdue']['priority'],
                'days_overdue': (today - p.due_date).days,
                'created_at': datetime.utcnow().isoformat()
            } for p in payments]
        except Exception as e:
            logger.error(f"Error checking overdue payments: {e}")
            return []
    
    def check_upcoming_payments(self) -> List[Dict]:
        """Check for payments coming due soon."""
        try:
            from database.models import Payment
            
            today = datetime.utcnow().date()
            threshold = today + timedelta(days=REMINDER_CONFIGS['payment_upcoming']['days_threshold'])
            
            payments = self.session.query(Payment).filter(
                Payment.organization_id == self.organization_id,
                Payment.status.in_(['pending', 'upcoming']),
                Payment.due_date != None,
                Payment.due_date >= today,
                Payment.due_date <= threshold
            ).all()
            
            return [{
                'type': 'payment_upcoming',
                'entity_type': 'payment',
                'entity_id': p.id,
                'title': f"Payment due soon: ${p.amount}",
                'description': f"Payment due on {p.due_date}",
                'amount': p.amount,
                'direction': p.direction,
                'priority': REMINDER_CONFIGS['payment_upcoming']['priority'],
                'days_until_due': (p.due_date - today).days,
                'created_at': datetime.utcnow().isoformat()
            } for p in payments]
        except Exception as e:
            logger.error(f"Error checking upcoming payments: {e}")
            return []
    
    def check_low_stock(self) -> List[Dict]:
        """Check for inventory items below reorder level."""
        try:
            from database.models import InventoryItem
            
            items = self.session.query(InventoryItem).filter(
                InventoryItem.organization_id == self.organization_id,
                InventoryItem.is_active == True,
                InventoryItem.quantity <= InventoryItem.reorder_level
            ).all()
            
            return [{
                'type': 'low_stock',
                'entity_type': 'inventory_item',
                'entity_id': i.id,
                'title': f"Low stock: {i.name}",
                'description': f"Current quantity: {i.quantity}, Reorder level: {i.reorder_level}",
                'quantity': i.quantity,
                'reorder_level': i.reorder_level,
                'priority': REMINDER_CONFIGS['low_stock']['priority'],
                'created_at': datetime.utcnow().isoformat()
            } for i in items]
        except Exception as e:
            logger.error(f"Error checking low stock: {e}")
            return []
    
    def check_overdue_jobs(self) -> List[Dict]:
        """Check for jobs that are past their scheduled date."""
        try:
            from database.models import Job
            
            now = datetime.utcnow()
            
            jobs = self.session.query(Job).filter(
                Job.organization_id == self.organization_id,
                Job.status.in_(['pending', 'in_progress']),
                Job.scheduled_date != None,
                Job.scheduled_date < now
            ).all()
            
            return [{
                'type': 'job_overdue',
                'entity_type': 'job',
                'entity_id': j.id,
                'title': f"Overdue job: {j.title}",
                'description': f"Job was scheduled for {j.scheduled_date}",
                'priority': REMINDER_CONFIGS['job_overdue']['priority'],
                'created_at': datetime.utcnow().isoformat()
            } for j in jobs]
        except Exception as e:
            logger.error(f"Error checking overdue jobs: {e}")
            return []
    
    def check_stale_tasks(self) -> List[Dict]:
        """Check for tasks that have been in progress for too long."""
        try:
            from database.models import KanbanTask
            
            threshold = datetime.utcnow() - timedelta(days=REMINDER_CONFIGS['task_stale']['days_threshold'])
            
            tasks = self.session.query(KanbanTask).filter(
                KanbanTask.organization_id == self.organization_id,
                KanbanTask.archived == False,
                KanbanTask.column == 'in_progress',
                KanbanTask.updated_at <= threshold
            ).all()
            
            return [{
                'type': 'task_stale',
                'entity_type': 'kanban_task',
                'entity_id': t.id,
                'title': f"Stale task: {t.content[:50]}...",
                'description': f"Task has been in progress for {(datetime.utcnow() - t.updated_at).days} days",
                'priority': REMINDER_CONFIGS['task_stale']['priority'],
                'days_in_progress': (datetime.utcnow() - t.updated_at).days,
                'created_at': datetime.utcnow().isoformat()
            } for t in tasks]
        except Exception as e:
            logger.error(f"Error checking stale tasks: {e}")
            return []
    
    def check_upcoming_events(self) -> List[Dict]:
        """Check for calendar events coming up soon."""
        try:
            from database.models import CalendarEvent
            
            now = datetime.utcnow()
            threshold = now + timedelta(hours=REMINDER_CONFIGS['event_upcoming']['hours_threshold'])
            
            events = self.session.query(CalendarEvent).filter(
                CalendarEvent.organization_id == self.organization_id,
                CalendarEvent.status != 'cancelled',
                CalendarEvent.start_time >= now,
                CalendarEvent.start_time <= threshold
            ).order_by(CalendarEvent.start_time).all()
            
            return [{
                'type': 'event_upcoming',
                'entity_type': 'calendar_event',
                'entity_id': e.id,
                'title': f"Upcoming: {e.title}",
                'description': f"Starts at {e.start_time}",
                'event_type': e.event_type,
                'location': e.location,
                'priority': REMINDER_CONFIGS['event_upcoming']['priority'],
                'hours_until': int((e.start_time - now).total_seconds() / 3600),
                'created_at': datetime.utcnow().isoformat()
            } for e in events]
        except Exception as e:
            logger.error(f"Error checking upcoming events: {e}")
            return []
    
    def get_dashboard_alerts(self) -> List[Dict]:
        """
        Get a prioritized list of alerts for the dashboard.
        
        Returns the most important items that need attention,
        sorted by priority and urgency.
        """
        all_reminders = self.check_all_reminders()
        
        # Flatten all reminders into a single list
        alerts = []
        for reminder_type, items in all_reminders.items():
            alerts.extend(items)
        
        # Sort by priority (urgent > high > normal > low)
        priority_order = {'urgent': 0, 'high': 1, 'normal': 2, 'low': 3}
        alerts.sort(key=lambda x: priority_order.get(x.get('priority', 'normal'), 2))
        
        return alerts[:20]  # Return top 20 alerts
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all reminders for AI context."""
        all_reminders = self.check_all_reminders()
        
        summary = {
            'checked_at': datetime.utcnow().isoformat(),
            'total_items': sum(len(items) for items in all_reminders.values()),
            'by_type': {k: len(v) for k, v in all_reminders.items()},
            'urgent_items': [],
            'high_priority_items': []
        }
        
        # Extract urgent and high priority items
        for items in all_reminders.values():
            for item in items:
                if item.get('priority') == 'urgent':
                    summary['urgent_items'].append(item)
                elif item.get('priority') == 'high':
                    summary['high_priority_items'].append(item)
        
        return summary


def get_reminder_service(session: Session, organization_id: str) -> ReminderService:
    """Factory function to create a ReminderService instance."""
    return ReminderService(session, organization_id)


def run_reminder_check(session: Session, organization_id: str) -> Dict[str, Any]:
    """
    Run a complete reminder check and return results.
    
    This function can be called from a background job or scheduled task.
    """
    service = ReminderService(session, organization_id)
    return {
        'reminders': service.check_all_reminders(),
        'summary': service.get_summary(),
        'dashboard_alerts': service.get_dashboard_alerts()
    }

