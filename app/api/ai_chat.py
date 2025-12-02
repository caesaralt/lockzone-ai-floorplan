"""
AI Chat and Command Routes Blueprint

Handles AI-powered features:
- /api/ai-chat: Basic AI chat
- /api/ai/chat/contextual: Context-aware AI chat
- /api/ai/insights: AI-generated insights
- /api/ai/alerts: AI-generated alerts
- /api/ai/feedback: Feedback on AI responses
- /api/ai/correction: Corrections for AI learning
- /api/ai/command: Natural language commands
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app

logger = logging.getLogger(__name__)

# Create blueprint
ai_chat_bp = Blueprint('ai_chat_bp', __name__)


def get_app_config():
    """Get app configuration"""
    return {
        'CRM_USE_DATABASE': current_app.config.get('CRM_USE_DATABASE', False),
        'ANTHROPIC_AVAILABLE': current_app.config.get('ANTHROPIC_AVAILABLE', False),
        'anthropic': current_app.config.get('ANTHROPIC_CLIENT'),
    }


# ============================================================================
# AI CHAT (ENHANCED)
# ============================================================================

@ai_chat_bp.route('/api/ai/chat/contextual', methods=['POST'])
def ai_chat_contextual():
    """AI chat endpoint with full business context."""
    config = get_app_config()
    
    if not config['CRM_USE_DATABASE']:
        return jsonify({
            'success': False,
            'error': 'Database not configured',
            'response': 'AI chat requires database to be configured.'
        })
    
    try:
        from database.connection import get_db_session
        from database.seed import get_or_create_default_organization
        from services.ai_chat_service import AIChatService
        import auth
        
        data = request.json
        message = data.get('message', '')
        conversation_history = data.get('history', [])
        include_context = data.get('include_context', True)
        
        if not message:
            return jsonify({'success': False, 'error': 'Message is required'}), 400
        
        user_id = None
        try:
            current_user = auth.get_current_user()
            if current_user:
                user_id = current_user.get('id')
        except:
            pass
        
        with get_db_session() as session:
            org = get_or_create_default_organization(session)
            chat_service = AIChatService(session, org.id, user_id)
            
            result = chat_service.chat(
                message=message,
                conversation_history=conversation_history,
                include_context=include_context
            )
            
            session.commit()
            return jsonify(result)
            
    except Exception as e:
        logger.error(f"Error in contextual AI chat: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'response': 'An error occurred processing your request.'
        }), 500


@ai_chat_bp.route('/api/ai/insights', methods=['GET'])
def get_ai_insights():
    """Get AI-generated quick insights for dashboard."""
    config = get_app_config()
    
    if not config['CRM_USE_DATABASE']:
        return jsonify({'success': True, 'insights': []})
    
    try:
        from database.connection import get_db_session
        from database.seed import get_or_create_default_organization
        from services.ai_chat_service import AIChatService
        
        with get_db_session() as session:
            org = get_or_create_default_organization(session)
            chat_service = AIChatService(session, org.id)
            
            result = chat_service.get_quick_insights()
            
            insights = []
            suggestions = []
            
            for insight in result.get('insights', []):
                insights.append({
                    'type': insight.get('type', 'info'),
                    'title': insight.get('text', ''),
                    'message': '',
                    'action': 'view_' + insight.get('type', 'info') if insight.get('type') in ['warning', 'urgent'] else None,
                    'action_data': ''
                })
            
            summary = result.get('summary', {})
            if summary.get('quotes', {}).get('pending', 0) > 0:
                suggestions.append({
                    'text': '📋 Follow up on pending quotes to close deals faster',
                    'action': 'view_pending_quotes',
                    'action_data': ''
                })
            
            if summary.get('calendar', {}).get('upcoming_events_7_days', 0) == 0:
                suggestions.append({
                    'text': '📅 Schedule some meetings this week',
                    'action': 'schedule_event',
                    'action_data': ''
                })
            
            if summary.get('customers', {}).get('total', 0) < 5:
                suggestions.append({
                    'text': '👥 Add more customers to grow your business',
                    'action': 'create_customer',
                    'action_data': ''
                })
            
            return jsonify({
                'success': True,
                'insights': insights,
                'suggestions': suggestions,
                'summary': summary
            })
            
    except Exception as e:
        logger.error(f"Error getting AI insights: {e}")
        return jsonify({'success': False, 'insights': [], 'suggestions': [], 'error': str(e)}), 500


@ai_chat_bp.route('/api/ai/alerts', methods=['GET'])
def get_ai_alerts():
    """Get AI-generated alerts and reminders for dashboard."""
    config = get_app_config()
    
    if not config['CRM_USE_DATABASE']:
        return jsonify({'success': True, 'alerts': []})
    
    try:
        from database.connection import get_db_session
        from database.seed import get_or_create_default_organization
        from services.reminder_service import ReminderService
        
        with get_db_session() as session:
            org = get_or_create_default_organization(session)
            reminder_service = ReminderService(session, org.id)
            
            alerts = reminder_service.get_dashboard_alerts()
            
            formatted_alerts = []
            for alert in alerts[:10]:
                category = 'info'
                if 'payment' in alert.get('title', '').lower() or 'overdue' in alert.get('title', '').lower():
                    category = 'overdue_payment'
                elif 'job' in alert.get('title', '').lower():
                    category = 'overdue_job'
                elif 'stock' in alert.get('title', '').lower():
                    category = 'low_stock'
                elif 'quote' in alert.get('title', '').lower() or 'expir' in alert.get('title', '').lower():
                    category = 'expiring_quote'
                elif 'event' in alert.get('title', '').lower() or 'meeting' in alert.get('title', '').lower():
                    category = 'upcoming_event'
                
                formatted_alerts.append({
                    'id': alert.get('id', ''),
                    'title': alert.get('title', 'Alert'),
                    'message': alert.get('message', ''),
                    'category': category,
                    'priority': alert.get('priority', 'normal'),
                    'count': alert.get('count', 1),
                    'entity_type': alert.get('entity_type'),
                    'entity_id': alert.get('entity_id')
                })
            
            return jsonify({
                'success': True,
                'alerts': formatted_alerts,
                'total_count': len(alerts)
            })
            
    except Exception as e:
        logger.error(f"Error getting AI alerts: {e}")
        return jsonify({'success': False, 'alerts': [], 'error': str(e)}), 500


@ai_chat_bp.route('/api/ai/feedback', methods=['POST'])
def submit_ai_feedback():
    """Submit feedback on AI responses for learning."""
    try:
        import auth
        
        data = request.get_json() or {}
        response = data.get('response', '')
        is_positive = data.get('is_positive', True)
        user_message = data.get('user_message', '')
        
        config = get_app_config()
        if not config['CRM_USE_DATABASE']:
            return jsonify({'success': True, 'message': 'Feedback noted'})
        
        from database.connection import get_db_session
        from database.seed import get_or_create_default_organization
        from database.models import EventLog
        import uuid
        
        with get_db_session() as session:
            org = get_or_create_default_organization(session)
            
            current_user = auth.get_current_user()
            user_id = current_user.get('id') if current_user else None
            
            event = EventLog(
                organization_id=org.id,
                timestamp=datetime.utcnow(),
                actor_type='user',
                actor_id=user_id,
                entity_type='ai_feedback',
                entity_id=uuid.uuid4(),
                event_type='AI_FEEDBACK_POSITIVE' if is_positive else 'AI_FEEDBACK_NEGATIVE',
                description=f"User {'liked' if is_positive else 'disliked'} AI response",
                extra_data={
                    'user_message': user_message[:500] if user_message else '',
                    'ai_response': response[:500] if response else '',
                    'is_positive': is_positive
                }
            )
            session.add(event)
            session.commit()
        
        return jsonify({'success': True, 'message': 'Feedback recorded'})
        
    except Exception as e:
        logger.error(f"Error submitting AI feedback: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@ai_chat_bp.route('/api/ai/correction', methods=['POST'])
def submit_ai_correction():
    """Submit a correction to an AI response for learning."""
    try:
        import auth
        
        data = request.get_json() or {}
        original_response = data.get('original_response', '')
        corrected_response = data.get('corrected_response', '')
        user_message = data.get('user_message', '')
        context = data.get('context', '')
        
        if not corrected_response:
            return jsonify({'success': False, 'error': 'Correction is required'}), 400
        
        config = get_app_config()
        if not config['CRM_USE_DATABASE']:
            return jsonify({'success': True, 'message': 'Correction noted'})
        
        from database.connection import get_db_session
        from database.seed import get_or_create_default_organization
        from database.models import EventLog
        import uuid
        
        with get_db_session() as session:
            org = get_or_create_default_organization(session)
            
            current_user = auth.get_current_user()
            user_id = current_user.get('id') if current_user else None
            
            event = EventLog(
                organization_id=org.id,
                timestamp=datetime.utcnow(),
                actor_type='user',
                actor_id=user_id,
                entity_type='ai_correction',
                entity_id=uuid.uuid4(),
                event_type='AI_CORRECTION',
                description=f"User corrected AI response",
                extra_data={
                    'user_message': user_message[:500] if user_message else '',
                    'original_response': original_response[:1000] if original_response else '',
                    'corrected_response': corrected_response[:1000] if corrected_response else '',
                    'context': context
                }
            )
            session.add(event)
            session.commit()
        
        logger.info(f"AI correction recorded for learning")
        return jsonify({'success': True, 'message': 'Correction saved for AI learning'})
        
    except Exception as e:
        logger.error(f"Error submitting AI correction: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@ai_chat_bp.route('/api/ai/command', methods=['POST'])
def execute_ai_command():
    """Execute a natural language command (Jarvis-style)."""
    try:
        data = request.get_json() or {}
        command = data.get('command', '').strip().lower()
        
        if not command:
            return jsonify({'success': False, 'error': 'No command provided'}), 400
        
        action = None
        params = {}
        message = None
        
        # Navigation commands
        if any(word in command for word in ['show', 'go to', 'open', 'view']):
            if 'customer' in command:
                action = 'navigate'
                params = {'section': 'people-customers'}
                message = 'Opening customers...'
            elif 'quote' in command:
                action = 'navigate'
                params = {'section': 'quotes-open'}
                message = 'Opening quotes...'
            elif 'job' in command:
                action = 'navigate'
                params = {'section': 'jobs-in-progress'}
                message = 'Opening jobs...'
            elif 'calendar' in command or 'schedule' in command or 'event' in command:
                action = 'navigate'
                params = {'section': 'calendar'}
                message = 'Opening calendar...'
            elif 'payment' in command:
                action = 'navigate'
                params = {'section': 'payments-to-us'}
                message = 'Opening payments...'
            elif 'stock' in command or 'inventory' in command:
                action = 'navigate'
                params = {'section': 'materials-stock'}
                message = 'Opening stock...'
            elif 'dashboard' in command:
                action = 'navigate'
                params = {'section': 'dashboard'}
                message = 'Going to dashboard...'
            elif 'overdue' in command:
                if 'payment' in command:
                    action = 'navigate'
                    params = {'section': 'payments-to-us'}
                    message = 'Showing overdue payments...'
                else:
                    action = 'navigate'
                    params = {'section': 'jobs-in-progress'}
                    message = 'Showing overdue items...'
        
        # Create commands
        elif any(word in command for word in ['create', 'add', 'new', 'make']):
            if 'customer' in command:
                action = 'create_customer'
                name_match = None
                for phrase in ['for ', 'named ', 'called ']:
                    if phrase in command:
                        name_match = command.split(phrase)[-1].strip()
                        break
                params = {'name': name_match} if name_match else {}
                message = 'Opening new customer form...'
            elif 'quote' in command:
                action = 'create_quote'
                message = 'Opening new quote form...'
            elif 'job' in command:
                action = 'create_job'
                message = 'Opening new job form...'
            elif 'event' in command or 'meeting' in command:
                action = 'create_event'
                message = 'Opening new event form...'
        
        # Search commands
        elif 'search' in command or 'find' in command:
            search_term = command.replace('search', '').replace('find', '').replace('for', '').strip()
            if search_term:
                action = 'search'
                params = {'term': search_term}
                message = f'Searching for "{search_term}"...'
        
        # Summary/report commands
        elif any(word in command for word in ['summary', 'report', 'overview']):
            action = 'show_summary'
            message = 'Generating summary...'
        
        if action:
            return jsonify({
                'success': True,
                'action': action,
                'params': params,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': "I didn't understand that command. Try saying things like 'show customers', 'create quote', or 'go to calendar'."
            })
        
    except Exception as e:
        logger.error(f"Error executing AI command: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

