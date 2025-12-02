"""
App Services Package (Placeholder)

STATUS: This directory is a PLACEHOLDER for future service extraction.
        Currently empty - all active services are in the root /services/ directory.

ACTIVE SERVICES LOCATION: /services/ (project root)
The main services are already well-organized in the root services/ directory:
- ai_chat_service.py: AI chat functionality
- ai_context.py: AI context management  
- crm_repository.py: CRM data access layer
- event_logger.py: Event logging service
- inventory_repository.py: Inventory data access
- kanban_repository.py: Kanban task management
- notification_service.py: Notification handling
- reminder_service.py: Reminder scheduling
- scheduler.py: Background job scheduling
- users_repository.py: User data access

DO NOT duplicate services here - import from root /services/ instead.

FUTURE USE:
If extracting heavy business logic from route handlers, new services could go here:
- quote_service.py: Quote generation, pricing, PDF
- floorplan_service.py: AI floorplan analysis
- cad_service.py: CAD generation logic
- etc.

See ARCHITECTURE.md for guidance on where to add new code.
"""

__all__ = []
