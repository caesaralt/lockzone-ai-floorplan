"""
AI Chat Service - Intelligent chatbot with database context.

This service provides:
- Context-aware AI responses using business data
- Tool/function calling for database operations
- Conversation history management
- Intelligent suggestions based on user role
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import os

logger = logging.getLogger(__name__)

# Check for Anthropic API
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic library not available")


class AIChatService:
    """Service for AI-powered chat with database context."""
    
    SYSTEM_PROMPT = """You are an intelligent AI assistant for LockZone, a home automation company. 
You have access to the company's CRM data, projects, quotes, inventory, and scheduling information.

Your capabilities:
- Answer questions about customers, projects, quotes, jobs, and inventory
- Provide insights and summaries about business performance
- Help with scheduling and task management
- Suggest actions based on pending items and reminders
- Assist with quote creation and project planning

Guidelines:
- Be concise and professional
- Use the provided context to give accurate, specific answers
- If you don't have enough information, say so
- Suggest relevant actions when appropriate
- Format responses clearly with bullet points or numbered lists when helpful

Current date: {current_date}
"""
    
    def __init__(self, session, organization_id: str, user_id: str = None):
        self.session = session
        self.organization_id = organization_id
        self.user_id = user_id
        self.api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        
        if ANTHROPIC_AVAILABLE and self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.client = None
    
    def chat(self, message: str, conversation_history: List[Dict] = None,
             include_context: bool = True) -> Dict[str, Any]:
        """
        Process a chat message and return AI response.
        
        Args:
            message: User's message
            conversation_history: Previous messages in conversation
            include_context: Whether to include business context
        
        Returns:
            Dict with response, context used, and any suggested actions
        """
        if not self.client:
            return {
                'success': False,
                'error': 'AI service not configured',
                'response': 'I apologize, but the AI service is not currently available.'
            }
        
        try:
            # Build context
            context = {}
            if include_context:
                context = self._build_context(message)
            
            # Build messages
            messages = self._build_messages(message, conversation_history, context)
            
            # Get system prompt
            system_prompt = self.SYSTEM_PROMPT.format(
                current_date=datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
            )
            
            # Add context summary to system prompt
            if context:
                system_prompt += f"\n\nCurrent Business Context:\n{self._format_context(context)}"
            
            # Call Anthropic API
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=system_prompt,
                messages=messages
            )
            
            # Extract response text
            response_text = response.content[0].text if response.content else ""
            
            # Log the interaction for AI learning
            self._log_interaction(message, response_text, context)
            
            # Extract any suggested actions from response
            suggested_actions = self._extract_actions(response_text, context)
            
            return {
                'success': True,
                'response': response_text,
                'context_used': bool(context),
                'suggested_actions': suggested_actions,
                'tokens_used': {
                    'input': response.usage.input_tokens if response.usage else 0,
                    'output': response.usage.output_tokens if response.usage else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error in AI chat: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': 'I encountered an error processing your request. Please try again.'
            }
    
    def _build_context(self, message: str) -> Dict[str, Any]:
        """Build relevant context based on the message."""
        try:
            from services.ai_context import AIContextService
            from services.reminder_service import ReminderService
            
            context_service = AIContextService(self.session, self.organization_id)
            reminder_service = ReminderService(self.session, self.organization_id)
            
            context = {
                'business_summary': context_service.get_business_summary(),
                'pending_items': context_service.get_pending_items(),
                'recent_activity': context_service.get_recent_activity(hours=24, limit=10),
                'alerts': reminder_service.get_dashboard_alerts()[:5]  # Top 5 alerts
            }
            
            # Check for entity-specific queries
            entity_info = self._detect_entity_query(message)
            if entity_info:
                context['entity_context'] = context_service.get_entity_context(
                    entity_info['type'], 
                    entity_info['id']
                )
            
            return context
            
        except Exception as e:
            logger.error(f"Error building context: {e}")
            return {}
    
    def _detect_entity_query(self, message: str) -> Optional[Dict]:
        """Detect if the message is asking about a specific entity."""
        message_lower = message.lower()
        
        # Simple keyword detection - could be enhanced with NLP
        entity_keywords = {
            'customer': ['customer', 'client'],
            'project': ['project'],
            'quote': ['quote', 'estimate', 'proposal'],
            'job': ['job', 'work order', 'task'],
            'inventory': ['inventory', 'stock', 'item', 'product']
        }
        
        for entity_type, keywords in entity_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    # Could extract ID from message if mentioned
                    return {'type': entity_type, 'id': None}
        
        return None
    
    def _build_messages(self, message: str, history: List[Dict], 
                        context: Dict) -> List[Dict]:
        """Build the messages array for the API call."""
        messages = []
        
        # Add conversation history
        if history:
            for msg in history[-10:]:  # Last 10 messages
                messages.append({
                    'role': msg.get('role', 'user'),
                    'content': msg.get('content', '')
                })
        
        # Add current message
        messages.append({
            'role': 'user',
            'content': message
        })
        
        return messages
    
    def _format_context(self, context: Dict) -> str:
        """Format context for the system prompt."""
        parts = []
        
        if context.get('business_summary'):
            summary = context['business_summary']
            parts.append(f"""Business Summary:
- Customers: {summary.get('customers', {}).get('total', 0)}
- Active Projects: {summary.get('projects', {}).get('active', 0)}
- Pending Quotes: {summary.get('quotes', {}).get('pending', 0)} (${summary.get('quotes', {}).get('pending_value', 0):,.2f})
- Low Stock Items: {summary.get('inventory', {}).get('low_stock_items', 0)}
- Pending Tasks: {summary.get('tasks', {}).get('pending', 0)}""")
        
        if context.get('alerts'):
            alerts = context['alerts'][:5]
            if alerts:
                alert_text = "\n".join([f"- [{a.get('priority', 'normal').upper()}] {a.get('title', 'Alert')}" for a in alerts])
                parts.append(f"Current Alerts:\n{alert_text}")
        
        if context.get('entity_context'):
            ec = context['entity_context']
            if 'error' not in ec:
                parts.append(f"Entity Details: {json.dumps(ec, default=str)[:500]}...")
        
        return "\n\n".join(parts)
    
    def _log_interaction(self, message: str, response: str, context: Dict):
        """Log the chat interaction for AI learning."""
        try:
            from database.models import EventLog
            
            event = EventLog(
                organization_id=self.organization_id,
                timestamp=datetime.utcnow(),
                actor_type='user' if self.user_id else 'system',
                actor_id=self.user_id,
                entity_type='ai_chat',
                entity_id=self.user_id or 'anonymous',
                event_type='AI_CHAT',
                description=f"AI chat interaction",
                extra_data={
                    'message_preview': message[:200],
                    'response_preview': response[:200],
                    'context_keys': list(context.keys()) if context else []
                }
            )
            self.session.add(event)
            # Don't commit here - let the caller handle transaction
            
        except Exception as e:
            logger.warning(f"Failed to log AI interaction: {e}")
    
    def _extract_actions(self, response: str, context: Dict) -> List[Dict]:
        """Extract suggested actions from the response."""
        actions = []
        
        # Check for action keywords in response
        response_lower = response.lower()
        
        if 'follow up' in response_lower or 'contact' in response_lower:
            actions.append({
                'type': 'follow_up',
                'label': 'Schedule Follow-up',
                'icon': '📅'
            })
        
        if 'quote' in response_lower and ('create' in response_lower or 'new' in response_lower):
            actions.append({
                'type': 'create_quote',
                'label': 'Create Quote',
                'icon': '📝'
            })
        
        if 'low stock' in response_lower or 'reorder' in response_lower:
            actions.append({
                'type': 'check_inventory',
                'label': 'Check Inventory',
                'icon': '📦'
            })
        
        # Add pending items as potential actions
        if context.get('alerts'):
            for alert in context['alerts'][:3]:
                if alert.get('priority') in ['urgent', 'high']:
                    actions.append({
                        'type': alert.get('type', 'alert'),
                        'label': alert.get('title', 'View Alert')[:50],
                        'icon': '⚠️',
                        'entity_type': alert.get('entity_type'),
                        'entity_id': alert.get('entity_id')
                    })
        
        return actions[:5]  # Max 5 actions
    
    def get_quick_insights(self) -> Dict[str, Any]:
        """Get quick AI-generated insights for the dashboard."""
        try:
            from services.ai_context import AIContextService
            from services.reminder_service import ReminderService
            
            context_service = AIContextService(self.session, self.organization_id)
            reminder_service = ReminderService(self.session, self.organization_id)
            
            summary = context_service.get_business_summary()
            alerts = reminder_service.get_dashboard_alerts()
            
            insights = []
            
            # Generate insights based on data
            if summary.get('quotes', {}).get('pending', 0) > 0:
                pending_value = summary['quotes'].get('pending_value', 0)
                insights.append({
                    'type': 'opportunity',
                    'icon': '💰',
                    'text': f"You have {summary['quotes']['pending']} pending quotes worth ${pending_value:,.2f}"
                })
            
            if summary.get('inventory', {}).get('low_stock_items', 0) > 0:
                insights.append({
                    'type': 'warning',
                    'icon': '📦',
                    'text': f"{summary['inventory']['low_stock_items']} items are low on stock"
                })
            
            if summary.get('tasks', {}).get('pending', 0) > 5:
                insights.append({
                    'type': 'info',
                    'icon': '📋',
                    'text': f"You have {summary['tasks']['pending']} pending tasks"
                })
            
            urgent_alerts = [a for a in alerts if a.get('priority') == 'urgent']
            if urgent_alerts:
                insights.append({
                    'type': 'urgent',
                    'icon': '🚨',
                    'text': f"{len(urgent_alerts)} urgent items need your attention"
                })
            
            return {
                'success': True,
                'insights': insights,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Error getting quick insights: {e}")
            return {'success': False, 'insights': [], 'error': str(e)}


def get_ai_chat_service(session, organization_id: str, user_id: str = None) -> AIChatService:
    """Factory function to create an AIChatService instance."""
    return AIChatService(session, organization_id, user_id)

