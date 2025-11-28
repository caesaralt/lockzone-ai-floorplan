"""
Notification Service - Manages in-app and email notifications.

This service handles:
- Creating notifications for users
- Marking notifications as read
- Sending email notifications (when configured)
- Managing notification preferences
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import os

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing notifications."""
    
    def __init__(self, session, organization_id: str):
        self.session = session
        self.organization_id = organization_id
        
        # Email configuration from environment
        self.smtp_host = os.environ.get('SMTP_HOST', '')
        self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
        self.smtp_user = os.environ.get('SMTP_USER', '')
        self.smtp_password = os.environ.get('SMTP_PASSWORD', '')
        self.from_email = os.environ.get('FROM_EMAIL', 'noreply@lockzone.com')
        self.email_enabled = bool(self.smtp_host and self.smtp_user)
    
    def create_notification(self, title: str, message: str, 
                           notification_type: str = 'info',
                           priority: str = 'normal',
                           user_id: str = None,
                           entity_type: str = None,
                           entity_id: str = None,
                           metadata: Dict = None,
                           send_email: bool = False) -> Optional[Dict]:
        """
        Create a new notification.
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: Type (info, warning, alert, reminder, etc.)
            priority: Priority level (low, normal, high, urgent)
            user_id: Specific user to notify (None = all users)
            entity_type: Related entity type
            entity_id: Related entity ID
            metadata: Additional data
            send_email: Whether to also send email notification
        
        Returns:
            Created notification dict or None on failure
        """
        try:
            from database.models import Notification
            
            notification = Notification(
                organization_id=self.organization_id,
                user_id=user_id,
                title=title,
                message=message,
                notification_type=notification_type,
                priority=priority,
                entity_type=entity_type,
                entity_id=entity_id,
                extra_data=metadata or {},
                is_read=False,
                sent_email=False
            )
            
            self.session.add(notification)
            self.session.flush()
            
            # Send email if requested and configured
            if send_email and self.email_enabled and user_id:
                self._send_email_notification(notification)
            
            logger.info(f"Created notification: {title}")
            return notification.to_dict()
            
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            return None
    
    def get_notifications(self, user_id: str = None, unread_only: bool = False,
                         limit: int = 50) -> List[Dict]:
        """Get notifications for a user or all users."""
        try:
            from database.models import Notification
            
            query = self.session.query(Notification).filter(
                Notification.organization_id == self.organization_id
            )
            
            if user_id:
                # Get notifications for specific user OR broadcast notifications
                query = query.filter(
                    (Notification.user_id == user_id) | 
                    (Notification.user_id == None)
                )
            
            if unread_only:
                query = query.filter(Notification.is_read == False)
            
            notifications = query.order_by(
                Notification.created_at.desc()
            ).limit(limit).all()
            
            return [n.to_dict() for n in notifications]
            
        except Exception as e:
            logger.error(f"Error getting notifications: {e}")
            return []
    
    def get_unread_count(self, user_id: str = None) -> int:
        """Get count of unread notifications."""
        try:
            from database.models import Notification
            from sqlalchemy import func
            
            query = self.session.query(func.count(Notification.id)).filter(
                Notification.organization_id == self.organization_id,
                Notification.is_read == False
            )
            
            if user_id:
                query = query.filter(
                    (Notification.user_id == user_id) | 
                    (Notification.user_id == None)
                )
            
            return query.scalar() or 0
            
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0
    
    def mark_as_read(self, notification_id: str, user_id: str = None) -> bool:
        """Mark a notification as read."""
        try:
            from database.models import Notification
            
            notification = self.session.query(Notification).filter(
                Notification.id == notification_id,
                Notification.organization_id == self.organization_id
            ).first()
            
            if not notification:
                return False
            
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            self.session.flush()
            
            return True
            
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            return False
    
    def mark_all_as_read(self, user_id: str = None) -> int:
        """Mark all notifications as read for a user."""
        try:
            from database.models import Notification
            
            query = self.session.query(Notification).filter(
                Notification.organization_id == self.organization_id,
                Notification.is_read == False
            )
            
            if user_id:
                query = query.filter(
                    (Notification.user_id == user_id) | 
                    (Notification.user_id == None)
                )
            
            count = 0
            for notification in query.all():
                notification.is_read = True
                notification.read_at = datetime.utcnow()
                count += 1
            
            self.session.flush()
            return count
            
        except Exception as e:
            logger.error(f"Error marking all as read: {e}")
            return 0
    
    def delete_notification(self, notification_id: str) -> bool:
        """Delete a notification."""
        try:
            from database.models import Notification
            
            notification = self.session.query(Notification).filter(
                Notification.id == notification_id,
                Notification.organization_id == self.organization_id
            ).first()
            
            if not notification:
                return False
            
            self.session.delete(notification)
            self.session.flush()
            return True
            
        except Exception as e:
            logger.error(f"Error deleting notification: {e}")
            return False
    
    def cleanup_old_notifications(self, days: int = 30) -> int:
        """Delete read notifications older than specified days."""
        try:
            from database.models import Notification
            
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            query = self.session.query(Notification).filter(
                Notification.organization_id == self.organization_id,
                Notification.is_read == True,
                Notification.created_at < cutoff
            )
            
            count = query.count()
            query.delete()
            self.session.flush()
            
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up notifications: {e}")
            return 0
    
    def _send_email_notification(self, notification) -> bool:
        """Send email notification."""
        if not self.email_enabled:
            return False
        
        try:
            from database.models import User
            
            # Get user email
            user = self.session.query(User).filter(
                User.id == notification.user_id
            ).first()
            
            if not user or not user.email:
                return False
            
            # Create email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[LockZone] {notification.title}"
            msg['From'] = self.from_email
            msg['To'] = user.email
            
            # Plain text version
            text = f"""
{notification.title}

{notification.message}

---
This is an automated notification from LockZone.
            """
            
            # HTML version
            html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #556B2F; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
        .footer {{ font-size: 12px; color: #666; padding: 10px; text-align: center; }}
        .priority-urgent {{ border-left: 4px solid #dc3545; }}
        .priority-high {{ border-left: 4px solid #ffc107; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2 style="margin: 0;">🔔 {notification.title}</h2>
        </div>
        <div class="content priority-{notification.priority}">
            <p>{notification.message}</p>
        </div>
        <div class="footer">
            <p>This is an automated notification from LockZone.</p>
        </div>
    </div>
</body>
</html>
            """
            
            msg.attach(MIMEText(text, 'plain'))
            msg.attach(MIMEText(html, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            notification.sent_email = True
            self.session.flush()
            
            logger.info(f"Sent email notification to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            return False
    
    def send_bulk_email(self, subject: str, message: str, user_ids: List[str] = None) -> int:
        """Send email to multiple users."""
        if not self.email_enabled:
            return 0
        
        try:
            from database.models import User
            
            query = self.session.query(User).filter(
                User.organization_id == self.organization_id,
                User.is_active == True,
                User.email != None
            )
            
            if user_ids:
                query = query.filter(User.id.in_(user_ids))
            
            users = query.all()
            sent_count = 0
            
            for user in users:
                try:
                    msg = MIMEMultipart('alternative')
                    msg['Subject'] = f"[LockZone] {subject}"
                    msg['From'] = self.from_email
                    msg['To'] = user.email
                    
                    msg.attach(MIMEText(message, 'plain'))
                    
                    with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                        server.starttls()
                        server.login(self.smtp_user, self.smtp_password)
                        server.send_message(msg)
                    
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send email to {user.email}: {e}")
            
            return sent_count
            
        except Exception as e:
            logger.error(f"Error in bulk email: {e}")
            return 0


def get_notification_service(session, organization_id: str) -> NotificationService:
    """Factory function to create a NotificationService instance."""
    return NotificationService(session, organization_id)

