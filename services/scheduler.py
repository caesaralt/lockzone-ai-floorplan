"""
Background Job Scheduler - Runs periodic tasks for reminders and notifications.

This service manages background jobs that:
- Check for items needing attention (reminders)
- Send notifications to users
- Log scheduled events for AI learning
- Clean up old data
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from functools import wraps

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler = None


class BackgroundScheduler:
    """Simple background scheduler for running periodic tasks."""
    
    def __init__(self):
        self.jobs: Dict[str, Dict] = {}
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
    
    def add_job(self, job_id: str, func: Callable, interval_seconds: int,
                run_immediately: bool = False, kwargs: Dict = None):
        """
        Add a job to the scheduler.
        
        Args:
            job_id: Unique identifier for the job
            func: Function to call
            interval_seconds: How often to run (in seconds)
            run_immediately: Whether to run once immediately
            kwargs: Keyword arguments to pass to the function
        """
        with self._lock:
            self.jobs[job_id] = {
                'func': func,
                'interval': interval_seconds,
                'kwargs': kwargs or {},
                'last_run': None,
                'next_run': datetime.utcnow() if run_immediately else datetime.utcnow() + timedelta(seconds=interval_seconds),
                'run_count': 0,
                'last_error': None,
                'enabled': True
            }
            logger.info(f"Added job '{job_id}' with interval {interval_seconds}s")
    
    def remove_job(self, job_id: str):
        """Remove a job from the scheduler."""
        with self._lock:
            if job_id in self.jobs:
                del self.jobs[job_id]
                logger.info(f"Removed job '{job_id}'")
    
    def enable_job(self, job_id: str):
        """Enable a job."""
        with self._lock:
            if job_id in self.jobs:
                self.jobs[job_id]['enabled'] = True
    
    def disable_job(self, job_id: str):
        """Disable a job without removing it."""
        with self._lock:
            if job_id in self.jobs:
                self.jobs[job_id]['enabled'] = False
    
    def get_job_status(self) -> Dict[str, Any]:
        """Get status of all jobs."""
        with self._lock:
            return {
                job_id: {
                    'interval': job['interval'],
                    'last_run': job['last_run'].isoformat() if job['last_run'] else None,
                    'next_run': job['next_run'].isoformat() if job['next_run'] else None,
                    'run_count': job['run_count'],
                    'last_error': job['last_error'],
                    'enabled': job['enabled']
                }
                for job_id, job in self.jobs.items()
            }
    
    def start(self):
        """Start the scheduler in a background thread."""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Background scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Background scheduler stopped")
    
    def _run_loop(self):
        """Main scheduler loop."""
        while self.running and not self._stop_event.is_set():
            now = datetime.utcnow()
            
            with self._lock:
                jobs_to_run = []
                for job_id, job in self.jobs.items():
                    if job['enabled'] and job['next_run'] and now >= job['next_run']:
                        jobs_to_run.append((job_id, job))
            
            for job_id, job in jobs_to_run:
                try:
                    logger.debug(f"Running job '{job_id}'")
                    job['func'](**job['kwargs'])
                    
                    with self._lock:
                        job['last_run'] = now
                        job['next_run'] = now + timedelta(seconds=job['interval'])
                        job['run_count'] += 1
                        job['last_error'] = None
                        
                except Exception as e:
                    logger.error(f"Job '{job_id}' failed: {e}")
                    with self._lock:
                        job['last_error'] = str(e)
                        job['next_run'] = now + timedelta(seconds=job['interval'])
            
            # Sleep for a bit before checking again
            self._stop_event.wait(timeout=10)
    
    def run_job_now(self, job_id: str) -> bool:
        """Manually trigger a job to run immediately."""
        with self._lock:
            if job_id not in self.jobs:
                return False
            job = self.jobs[job_id]
        
        try:
            job['func'](**job['kwargs'])
            with self._lock:
                job['last_run'] = datetime.utcnow()
                job['run_count'] += 1
                job['last_error'] = None
            return True
        except Exception as e:
            logger.error(f"Manual job run '{job_id}' failed: {e}")
            with self._lock:
                job['last_error'] = str(e)
            return False


def get_scheduler() -> BackgroundScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler


# =============================================================================
# SCHEDULED JOBS
# =============================================================================

def check_reminders_job():
    """Job to check for reminders and create notifications."""
    try:
        from database.connection import get_db_session, is_db_configured
        from database.seed import get_or_create_default_organization
        from services.reminder_service import ReminderService
        from services.notification_service import NotificationService
        
        if not is_db_configured():
            return
        
        with get_db_session() as session:
            org = get_or_create_default_organization(session)
            
            # Check reminders
            reminder_service = ReminderService(session, org.id)
            alerts = reminder_service.get_dashboard_alerts()
            
            if alerts:
                # Create notifications for urgent/high priority items
                notification_service = NotificationService(session, org.id)
                
                for alert in alerts:
                    if alert.get('priority') in ['urgent', 'high']:
                        notification_service.create_notification(
                            title=alert.get('title', 'Alert'),
                            message=alert.get('description', ''),
                            notification_type=alert.get('type', 'reminder'),
                            priority=alert.get('priority', 'normal'),
                            entity_type=alert.get('entity_type'),
                            entity_id=alert.get('entity_id'),
                            metadata=alert
                        )
                
                session.commit()
                logger.info(f"Processed {len(alerts)} reminder alerts")
    
    except Exception as e:
        logger.error(f"Error in check_reminders_job: {e}")


def cleanup_old_notifications_job():
    """Job to clean up old read notifications."""
    try:
        from database.connection import get_db_session, is_db_configured
        from database.seed import get_or_create_default_organization
        from services.notification_service import NotificationService
        
        if not is_db_configured():
            return
        
        with get_db_session() as session:
            org = get_or_create_default_organization(session)
            notification_service = NotificationService(session, org.id)
            
            # Delete read notifications older than 30 days
            deleted = notification_service.cleanup_old_notifications(days=30)
            session.commit()
            
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old notifications")
    
    except Exception as e:
        logger.error(f"Error in cleanup_old_notifications_job: {e}")


def log_daily_summary_job():
    """Job to log a daily activity summary for AI context."""
    try:
        from database.connection import get_db_session, is_db_configured
        from database.seed import get_or_create_default_organization
        from services.ai_context import AIContextService
        from database.models import EventLog
        import uuid
        
        if not is_db_configured():
            return
        
        with get_db_session() as session:
            org = get_or_create_default_organization(session)
            context_service = AIContextService(session, org.id)
            
            # Get business summary
            summary = context_service.get_business_summary()
            
            # Use a deterministic UUID for daily summary based on organization
            # This allows tracking daily summaries consistently
            daily_summary_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"daily_summary_{org.id}"))
            
            # Log as an event for AI to reference
            event = EventLog(
                organization_id=org.id,
                timestamp=datetime.utcnow(),
                actor_type='system',
                entity_type='system',
                entity_id=daily_summary_uuid,
                event_type='DAILY_SUMMARY',
                description='Daily business summary generated',
                extra_data=summary
            )
            session.add(event)
            session.commit()
            
            logger.info("Daily summary logged for AI context")
    
    except Exception as e:
        logger.error(f"Error in log_daily_summary_job: {e}")


def init_scheduler():
    """Initialize the scheduler with default jobs."""
    scheduler = get_scheduler()
    
    # Check reminders every 15 minutes
    scheduler.add_job(
        'check_reminders',
        check_reminders_job,
        interval_seconds=15 * 60,  # 15 minutes
        run_immediately=True
    )
    
    # Cleanup old notifications daily (every 24 hours)
    scheduler.add_job(
        'cleanup_notifications',
        cleanup_old_notifications_job,
        interval_seconds=24 * 60 * 60,  # 24 hours
        run_immediately=False
    )
    
    # Log daily summary every 24 hours
    scheduler.add_job(
        'daily_summary',
        log_daily_summary_job,
        interval_seconds=24 * 60 * 60,  # 24 hours
        run_immediately=True
    )
    
    scheduler.start()
    logger.info("Scheduler initialized with default jobs")
    
    return scheduler

