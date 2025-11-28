"""
AI Context Service - Provides contextual data for AI interactions.

This service gathers relevant information from the database to provide
context to the AI assistant without sending the entire database.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)


class AIContextService:
    """Service for gathering AI context from the database."""
    
    def __init__(self, session: Session, organization_id: str):
        self.session = session
        self.organization_id = organization_id
    
    def get_business_summary(self) -> Dict[str, Any]:
        """Get a high-level summary of the business for AI context."""
        try:
            from database.models import (
                Customer, Project, Quote, Job, InventoryItem,
                Payment, CalendarEvent, KanbanTask
            )
            
            # Count active entities
            customer_count = self.session.query(func.count(Customer.id)).filter(
                Customer.organization_id == self.organization_id,
                Customer.is_active == True
            ).scalar() or 0
            
            project_count = self.session.query(func.count(Project.id)).filter(
                Project.organization_id == self.organization_id
            ).scalar() or 0
            
            active_project_count = self.session.query(func.count(Project.id)).filter(
                Project.organization_id == self.organization_id,
                Project.status == 'in_progress'
            ).scalar() or 0
            
            quote_count = self.session.query(func.count(Quote.id)).filter(
                Quote.organization_id == self.organization_id
            ).scalar() or 0
            
            pending_quote_count = self.session.query(func.count(Quote.id)).filter(
                Quote.organization_id == self.organization_id,
                Quote.status.in_(['draft', 'sent'])
            ).scalar() or 0
            
            # Calculate revenue from quotes
            total_quote_value = self.session.query(func.sum(Quote.total_amount)).filter(
                Quote.organization_id == self.organization_id,
                Quote.status == 'accepted'
            ).scalar() or 0
            
            pending_quote_value = self.session.query(func.sum(Quote.total_amount)).filter(
                Quote.organization_id == self.organization_id,
                Quote.status.in_(['draft', 'sent'])
            ).scalar() or 0
            
            # Low stock items
            low_stock_count = self.session.query(func.count(InventoryItem.id)).filter(
                InventoryItem.organization_id == self.organization_id,
                InventoryItem.quantity <= InventoryItem.reorder_level
            ).scalar() or 0
            
            # Upcoming tasks
            today = datetime.utcnow().date()
            upcoming_tasks = self.session.query(func.count(KanbanTask.id)).filter(
                KanbanTask.organization_id == self.organization_id,
                KanbanTask.archived == False,
                KanbanTask.column.in_(['todo', 'in_progress'])
            ).scalar() or 0
            
            # Upcoming events
            upcoming_events = self.session.query(func.count(CalendarEvent.id)).filter(
                CalendarEvent.organization_id == self.organization_id,
                CalendarEvent.start_time >= datetime.utcnow(),
                CalendarEvent.start_time <= datetime.utcnow() + timedelta(days=7)
            ).scalar() or 0
            
            return {
                'summary_date': datetime.utcnow().isoformat(),
                'customers': {
                    'total': customer_count,
                },
                'projects': {
                    'total': project_count,
                    'active': active_project_count,
                },
                'quotes': {
                    'total': quote_count,
                    'pending': pending_quote_count,
                    'total_value': float(total_quote_value),
                    'pending_value': float(pending_quote_value),
                },
                'inventory': {
                    'low_stock_items': low_stock_count,
                },
                'tasks': {
                    'pending': upcoming_tasks,
                },
                'calendar': {
                    'upcoming_events_7_days': upcoming_events,
                }
            }
        except Exception as e:
            logger.error(f"Error getting business summary: {e}")
            return {}
    
    def get_recent_activity(self, hours: int = 24, limit: int = 20) -> List[Dict]:
        """Get recent activity from the event log."""
        try:
            from database.models import EventLog
            
            since = datetime.utcnow() - timedelta(hours=hours)
            
            events = self.session.query(EventLog).filter(
                EventLog.organization_id == self.organization_id,
                EventLog.timestamp >= since
            ).order_by(EventLog.timestamp.desc()).limit(limit).all()
            
            return [e.to_dict() for e in events]
        except Exception as e:
            logger.error(f"Error getting recent activity: {e}")
            return []
    
    def get_entity_context(self, entity_type: str, entity_id: str) -> Dict[str, Any]:
        """Get detailed context for a specific entity."""
        try:
            context = {
                'entity_type': entity_type,
                'entity_id': entity_id,
            }
            
            if entity_type == 'customer':
                context.update(self._get_customer_context(entity_id))
            elif entity_type == 'project':
                context.update(self._get_project_context(entity_id))
            elif entity_type == 'quote':
                context.update(self._get_quote_context(entity_id))
            elif entity_type == 'job':
                context.update(self._get_job_context(entity_id))
            
            # Get entity history
            context['history'] = self._get_entity_history(entity_type, entity_id)
            
            return context
        except Exception as e:
            logger.error(f"Error getting entity context: {e}")
            return {'entity_type': entity_type, 'entity_id': entity_id, 'error': str(e)}
    
    def _get_customer_context(self, customer_id: str) -> Dict[str, Any]:
        """Get context for a customer."""
        from database.models import Customer, Quote, Project
        
        customer = self.session.query(Customer).filter(
            Customer.id == customer_id,
            Customer.organization_id == self.organization_id
        ).first()
        
        if not customer:
            return {'error': 'Customer not found'}
        
        # Get related quotes
        quotes = self.session.query(Quote).filter(
            Quote.customer_id == customer_id
        ).order_by(Quote.created_at.desc()).limit(5).all()
        
        # Get related projects
        projects = self.session.query(Project).filter(
            Project.customer_id == customer_id
        ).order_by(Project.created_at.desc()).limit(5).all()
        
        return {
            'customer': customer.to_dict(),
            'recent_quotes': [q.to_dict() for q in quotes],
            'recent_projects': [p.to_dict() for p in projects],
            'quote_count': len(quotes),
            'project_count': len(projects),
        }
    
    def _get_project_context(self, project_id: str) -> Dict[str, Any]:
        """Get context for a project."""
        from database.models import Project, Quote, Job, Customer
        
        project = self.session.query(Project).filter(
            Project.id == project_id,
            Project.organization_id == self.organization_id
        ).first()
        
        if not project:
            return {'error': 'Project not found'}
        
        # Get customer info
        customer = None
        if project.customer_id:
            customer = self.session.query(Customer).filter(
                Customer.id == project.customer_id
            ).first()
        
        # Get related quotes
        quotes = self.session.query(Quote).filter(
            Quote.project_id == project_id
        ).all()
        
        # Get related jobs
        jobs = self.session.query(Job).filter(
            Job.project_id == project_id
        ).all()
        
        return {
            'project': project.to_dict(),
            'customer': customer.to_dict() if customer else None,
            'quotes': [q.to_dict() for q in quotes],
            'jobs': [j.to_dict() for j in jobs],
        }
    
    def _get_quote_context(self, quote_id: str) -> Dict[str, Any]:
        """Get context for a quote."""
        from database.models import Quote, Customer, Project
        
        quote = self.session.query(Quote).filter(
            Quote.id == quote_id,
            Quote.organization_id == self.organization_id
        ).first()
        
        if not quote:
            return {'error': 'Quote not found'}
        
        # Get customer info
        customer = None
        if quote.customer_id:
            customer = self.session.query(Customer).filter(
                Customer.id == quote.customer_id
            ).first()
        
        # Get project info
        project = None
        if quote.project_id:
            project = self.session.query(Project).filter(
                Project.id == quote.project_id
            ).first()
        
        return {
            'quote': quote.to_dict(),
            'customer': customer.to_dict() if customer else None,
            'project': project.to_dict() if project else None,
        }
    
    def _get_job_context(self, job_id: str) -> Dict[str, Any]:
        """Get context for a job."""
        from database.models import Job, Project, Technician
        
        job = self.session.query(Job).filter(
            Job.id == job_id,
            Job.organization_id == self.organization_id
        ).first()
        
        if not job:
            return {'error': 'Job not found'}
        
        # Get project info
        project = None
        if job.project_id:
            project = self.session.query(Project).filter(
                Project.id == job.project_id
            ).first()
        
        # Get technician info
        technician = None
        if job.technician_id:
            technician = self.session.query(Technician).filter(
                Technician.id == job.technician_id
            ).first()
        
        return {
            'job': job.to_dict(),
            'project': project.to_dict() if project else None,
            'technician': technician.to_dict() if technician else None,
        }
    
    def _get_entity_history(self, entity_type: str, entity_id: str, limit: int = 10) -> List[Dict]:
        """Get event history for an entity."""
        from database.models import EventLog
        
        events = self.session.query(EventLog).filter(
            EventLog.organization_id == self.organization_id,
            EventLog.entity_type == entity_type,
            EventLog.entity_id == entity_id
        ).order_by(EventLog.timestamp.desc()).limit(limit).all()
        
        return [e.to_dict() for e in events]
    
    def get_pending_items(self) -> Dict[str, List[Dict]]:
        """Get all pending items that might need attention."""
        try:
            from database.models import Quote, Job, Payment, KanbanTask, CalendarEvent
            
            # Pending quotes
            pending_quotes = self.session.query(Quote).filter(
                Quote.organization_id == self.organization_id,
                Quote.status.in_(['draft', 'sent'])
            ).order_by(Quote.created_at.desc()).limit(10).all()
            
            # Pending jobs
            pending_jobs = self.session.query(Job).filter(
                Job.organization_id == self.organization_id,
                Job.status.in_(['pending', 'in_progress'])
            ).order_by(Job.scheduled_date).limit(10).all()
            
            # Overdue payments
            today = datetime.utcnow().date()
            overdue_payments = self.session.query(Payment).filter(
                Payment.organization_id == self.organization_id,
                Payment.status.in_(['pending', 'due']),
                Payment.due_date < today
            ).all()
            
            # Pending tasks
            pending_tasks = self.session.query(KanbanTask).filter(
                KanbanTask.organization_id == self.organization_id,
                KanbanTask.archived == False,
                KanbanTask.column.in_(['todo', 'in_progress'])
            ).order_by(KanbanTask.due_date).limit(10).all()
            
            # Upcoming events (next 7 days)
            upcoming_events = self.session.query(CalendarEvent).filter(
                CalendarEvent.organization_id == self.organization_id,
                CalendarEvent.start_time >= datetime.utcnow(),
                CalendarEvent.start_time <= datetime.utcnow() + timedelta(days=7)
            ).order_by(CalendarEvent.start_time).limit(10).all()
            
            return {
                'pending_quotes': [q.to_dict() for q in pending_quotes],
                'pending_jobs': [j.to_dict() for j in pending_jobs],
                'overdue_payments': [p.to_dict() for p in overdue_payments],
                'pending_tasks': [t.to_dict() for t in pending_tasks],
                'upcoming_events': [e.to_dict() for e in upcoming_events],
            }
        except Exception as e:
            logger.error(f"Error getting pending items: {e}")
            return {}
    
    def build_ai_context(self, query: str = None, entity_type: str = None, 
                         entity_id: str = None) -> Dict[str, Any]:
        """
        Build comprehensive context for an AI query.
        
        This is the main method to call when preparing context for AI.
        It gathers relevant information based on the query and any
        specific entity being discussed.
        """
        context = {
            'timestamp': datetime.utcnow().isoformat(),
            'business_summary': self.get_business_summary(),
            'recent_activity': self.get_recent_activity(hours=24, limit=10),
            'pending_items': self.get_pending_items(),
        }
        
        # Add entity-specific context if provided
        if entity_type and entity_id:
            context['entity_context'] = self.get_entity_context(entity_type, entity_id)
        
        return context


def get_ai_context_service(session: Session, organization_id: str) -> AIContextService:
    """Factory function to create an AIContextService instance."""
    return AIContextService(session, organization_id)

