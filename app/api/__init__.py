"""
API Blueprints Package

All HTTP route handlers for the application, organized by domain.
Each module defines a Flask Blueprint registered in app/__init__.py.

BLUEPRINT REFERENCE:
====================

CRM Domain:
- crm.py            : Core CRM (customers, projects, quotes, stock, stats)
- crm_extended.py   : Extended CRM (jobs, markups, documents, cost centres)
- crm_resources.py  : CRM resources (technicians, suppliers, price classes, inventory)
- crm_v2.py         : CRM v2 API with pagination and search
- crm_google.py     : Google Calendar/Gmail integration
- crm_integration.py: CRM health checks and sync

Quote & Analysis:
- quote_automation.py: AI quote generation, PDF export
- canvas.py          : Canvas editor, takeoffs, session management

Design Tools:
- electrical_cad.py : CAD designer routes
- ai_mapping.py     : AI floor plan mapping
- board_builder.py  : Loxone board builder

Other:
- pages.py          : Page rendering (/, /crm, /quotes, etc.)
- auth_routes.py    : Authentication (/login, /api/auth/*)
- admin.py          : Admin panel (/admin/*)
- dashboard.py      : Dashboard, notifications, reminders
- ai_chat.py        : AI chat assistant
- kanban.py         : Kanban task board
- simpro.py         : Simpro integration
- pdf_editor.py     : PDF forms editor
- learning.py       : AI learning system
- scheduler.py      : Scheduler status
- misc.py           : Misc utilities (data API, uploads)

See ARCHITECTURE.md for detailed "where to modify what" guide.
"""

# All blueprints are imported and registered in app/__init__.py
# This file serves as documentation only

__all__ = []
