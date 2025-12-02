"""
Dashboard, Notifications, and Activity Routes Blueprint

Handles dashboard and notification functionality:
- /api/reminders: Get reminders and alerts
- /api/dashboard/alerts: Get prioritized alerts
- /api/dashboard/personalized: Get personalized dashboard
- /api/activity/recent: Get recent activity
- /api/notifications: CRUD for notifications
- /api/ai/context: Get AI context
"""

import logging
from flask import Blueprint, request, jsonify, current_app

logger = logging.getLogger(__name__)

# Create blueprint
dashboard_bp = Blueprint('dashboard_bp', __name__)


def get_app_config():
    """Get app configuration"""
    return {
        'CRM_USE_DATABASE': current_app.config.get('CRM_USE_DATABASE', False),
        'auth': current_app.config.get('AUTH_MODULE'),
    }


# ============================================================================
# REMINDERS & ALERTS
# ============================================================================

@dashboard_bp.route('/api/reminders', methods=['GET'])
def get_reminders():
    """Get all reminders and alerts that need attention."""
    config = get_app_config()
    
    if not config['CRM_USE_DATABASE']:
        return jsonify({'success': True, 'reminders': {}, 'alerts': []})
    
    try:
        from database.connection import get_db_session
        from database.seed import get_or_create_default_organization
        from services.reminder_service import ReminderService
        
        with get_db_session() as session:
            org = get_or_create_default_organization(session)
            service = ReminderService(session, org.id)
            
            return jsonify({
                'success': True,
                'reminders': service.check_all_reminders(),
                'summary': service.get_summary()
            })
    except Exception as e:
        logger.error(f"Error getting reminders: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/api/dashboard/alerts', methods=['GET'])
def get_dashboard_alerts():
    """Get prioritized alerts for the dashboard."""
    config = get_app_config()
    
    if not config['CRM_USE_DATABASE']:
        return jsonify({'success': True, 'alerts': []})
    
    try:
        from database.connection import get_db_session
        from database.seed import get_or_create_default_organization
        from services.reminder_service import ReminderService
        
        with get_db_session() as session:
            org = get_or_create_default_organization(session)
            service = ReminderService(session, org.id)
            
            return jsonify({
                'success': True,
                'alerts': service.get_dashboard_alerts()
            })
    except Exception as e:
        logger.error(f"Error getting dashboard alerts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/api/dashboard/personalized', methods=['GET'])
def get_personalized_dashboard():
    """Get personalized dashboard data based on user role and permissions."""
    config = get_app_config()
    
    if not config['CRM_USE_DATABASE']:
        return jsonify({'success': True, 'data': {}})
    
    try:
        from database.connection import get_db_session
        from database.seed import get_or_create_default_organization
        from services.ai_context import AIContextService
        from services.reminder_service import ReminderService
        from services.notification_service import NotificationService
        import auth
        
        # Get current user
        current_user = None
        user_id = None
        user_role = 'user'
        user_permissions = []
        
        try:
            current_user = auth.get_current_user()
            if current_user:
                user_id = current_user.get('id')
                user_role = current_user.get('role', 'user')
                user_permissions = current_user.get('permissions', [])
        except:
            pass
        
        with get_db_session() as session:
            org = get_or_create_default_organization(session)
            
            context_service = AIContextService(session, org.id)
            reminder_service = ReminderService(session, org.id)
            notification_service = NotificationService(session, org.id)
            
            dashboard_data = {
                'user': {
                    'id': user_id,
                    'role': user_role,
                    'display_name': current_user.get('display_name') if current_user else 'User'
                },
                'business_summary': context_service.get_business_summary(),
                'notifications': {
                    'unread_count': notification_service.get_unread_count(user_id),
                    'recent': notification_service.get_notifications(user_id, limit=5)
                },
                'alerts': [],
                'assigned_items': [],
                'quick_actions': []
            }
            
            all_alerts = reminder_service.get_dashboard_alerts()
            
            if user_role == 'admin':
                dashboard_data['alerts'] = all_alerts[:10]
            elif user_role == 'technician':
                dashboard_data['alerts'] = [
                    a for a in all_alerts 
                    if a.get('entity_type') in ['job', 'kanban_task', 'calendar_event']
                ][:10]
            else:
                dashboard_data['alerts'] = [
                    a for a in all_alerts 
                    if a.get('priority') in ['urgent', 'high']
                ][:5]
            
            quick_actions = []
            
            if 'crm' in user_permissions or user_role == 'admin':
                quick_actions.extend([
                    {'id': 'new_customer', 'label': 'New Customer', 'icon': '👤', 'section': 'people-customers'},
                    {'id': 'new_quote', 'label': 'New Quote', 'icon': '📝', 'section': 'quotes-open'},
                ])
            
            if 'canvas' in user_permissions or user_role == 'admin':
                quick_actions.append(
                    {'id': 'new_project', 'label': 'New Project', 'icon': '🏗️', 'section': 'jobs-in-progress'}
                )
            
            dashboard_data['quick_actions'] = quick_actions
            
            return jsonify({
                'success': True,
                'data': dashboard_data
            })
            
    except Exception as e:
        logger.error(f"Error getting personalized dashboard: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# AI CONTEXT
# ============================================================================

@dashboard_bp.route('/api/ai/context', methods=['GET'])
def get_ai_context():
    """Get AI context for intelligent assistance."""
    config = get_app_config()
    
    if not config['CRM_USE_DATABASE']:
        return jsonify({'success': True, 'context': {}})
    
    try:
        from database.connection import get_db_session
        from database.seed import get_or_create_default_organization
        from services.ai_context import AIContextService
        
        entity_type = request.args.get('entity_type')
        entity_id = request.args.get('entity_id')
        
        with get_db_session() as session:
            org = get_or_create_default_organization(session)
            service = AIContextService(session, org.id)
            
            context = service.build_ai_context(
                entity_type=entity_type,
                entity_id=entity_id
            )
            
            return jsonify({
                'success': True,
                'context': context
            })
    except Exception as e:
        logger.error(f"Error getting AI context: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# ACTIVITY
# ============================================================================

@dashboard_bp.route('/api/activity/recent', methods=['GET'])
def get_recent_activity():
    """Get recent activity from the event log."""
    config = get_app_config()
    
    if not config['CRM_USE_DATABASE']:
        return jsonify({'success': True, 'events': []})
    
    try:
        from database.connection import get_db_session
        from database.seed import get_or_create_default_organization
        from services.event_logger import EventLogger
        
        hours = int(request.args.get('hours', 24))
        limit = int(request.args.get('limit', 50))
        
        with get_db_session() as session:
            org = get_or_create_default_organization(session)
            logger_service = EventLogger(session, org.id)
            
            events = logger_service.get_recent_events(hours=hours, limit=limit)
            summary = logger_service.get_activity_summary(days=7)
            
            return jsonify({
                'success': True,
                'events': events,
                'summary': summary
            })
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# NOTIFICATIONS
# ============================================================================

@dashboard_bp.route('/api/notifications', methods=['GET', 'POST'])
def handle_notifications():
    """Get notifications or create a new notification."""
    config = get_app_config()
    
    if not config['CRM_USE_DATABASE']:
        return jsonify({'success': True, 'notifications': []})
    
    try:
        from database.connection import get_db_session
        from database.seed import get_or_create_default_organization
        from services.notification_service import NotificationService
        import auth
        
        with get_db_session() as session:
            org = get_or_create_default_organization(session)
            
            user_id = None
            try:
                current_user = auth.get_current_user()
                if current_user:
                    user_id = current_user.get('id')
            except:
                pass
            
            service = NotificationService(session, org.id)
            
            if request.method == 'GET':
                unread_only = request.args.get('unread_only') == 'true'
                limit = int(request.args.get('limit', 50))
                
                notifications = service.get_notifications(
                    user_id=user_id,
                    unread_only=unread_only,
                    limit=limit
                )
                unread_count = service.get_unread_count(user_id=user_id)
                
                return jsonify({
                    'success': True,
                    'notifications': notifications,
                    'unread_count': unread_count
                })
            
            else:  # POST
                data = request.json
                notification = service.create_notification(
                    title=data.get('title', 'Notification'),
                    message=data.get('message', ''),
                    notification_type=data.get('type', 'info'),
                    priority=data.get('priority', 'normal'),
                    user_id=data.get('user_id'),
                    entity_type=data.get('entity_type'),
                    entity_id=data.get('entity_id'),
                    metadata=data.get('metadata'),
                    send_email=data.get('send_email', False)
                )
                session.commit()
                
                if notification:
                    return jsonify({'success': True, 'notification': notification})
                return jsonify({'success': False, 'error': 'Failed to create notification'}), 400
                
    except Exception as e:
        logger.error(f"Error handling notifications: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/api/notifications/<notification_id>/read', methods=['POST'])
def mark_notification_read(notification_id):
    """Mark a notification as read."""
    config = get_app_config()
    
    if not config['CRM_USE_DATABASE']:
        return jsonify({'success': True})
    
    try:
        from database.connection import get_db_session
        from database.seed import get_or_create_default_organization
        from services.notification_service import NotificationService
        
        with get_db_session() as session:
            org = get_or_create_default_organization(session)
            service = NotificationService(session, org.id)
            
            if service.mark_as_read(notification_id):
                session.commit()
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Notification not found'}), 404
            
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/api/notifications/read-all', methods=['POST'])
def mark_all_notifications_read():
    """Mark all notifications as read."""
    config = get_app_config()
    
    if not config['CRM_USE_DATABASE']:
        return jsonify({'success': True, 'count': 0})
    
    try:
        from database.connection import get_db_session
        from database.seed import get_or_create_default_organization
        from services.notification_service import NotificationService
        import auth
        
        with get_db_session() as session:
            org = get_or_create_default_organization(session)
            
            user_id = None
            try:
                current_user = auth.get_current_user()
                if current_user:
                    user_id = current_user.get('id')
            except:
                pass
            
            service = NotificationService(session, org.id)
            count = service.mark_all_as_read(user_id=user_id)
            session.commit()
            
            return jsonify({'success': True, 'count': count})
            
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/api/notifications/<notification_id>', methods=['DELETE'])
def delete_notification(notification_id):
    """Delete a notification."""
    config = get_app_config()
    
    if not config['CRM_USE_DATABASE']:
        return jsonify({'success': True})
    
    try:
        from database.connection import get_db_session
        from database.seed import get_or_create_default_organization
        from services.notification_service import NotificationService
        
        with get_db_session() as session:
            org = get_or_create_default_organization(session)
            service = NotificationService(session, org.id)
            
            if service.delete_notification(notification_id):
                session.commit()
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Notification not found'}), 404
            
    except Exception as e:
        logger.error(f"Error deleting notification: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

