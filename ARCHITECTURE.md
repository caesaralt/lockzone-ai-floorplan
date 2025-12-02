# ARCHITECTURE.md - Developer Guide

> **Purpose**: Detailed guide for developers and AI agents on where to find and modify code
> **Last Updated**: December 2024

---

## Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [Blueprint Reference](#blueprint-reference)
3. [Where to Modify What](#where-to-modify-what)
4. [Data Layer](#data-layer)
5. [House Rules for Development](#house-rules-for-development)

---

## High-Level Architecture

### Entry Point: `app.py`

**Role**: Thin entrypoint that creates the Flask app and registers blueprints.

- **Lines**: ~1,750
- **Routes**: **ZERO** - All routes are in blueprints
- **Contains**: Flask app creation, configuration loading, logging setup, blueprint imports

```python
# app.py structure (simplified)
from app import create_app
app = create_app()

if __name__ == '__main__':
    app.run()
```

### App Factory: `app/__init__.py`

**Role**: Creates Flask app instance and registers all 22 blueprints.

```python
# Registers blueprints like:
app.register_blueprint(pages_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(crm_bp)
# ... etc
```

### Route Handlers: `app/api/*.py`

**Role**: ALL HTTP routes live here as Flask Blueprints.

Each blueprint file:
- Defines a `Blueprint` object
- Contains route handlers (`@blueprint.route(...)`)
- Imports from data layer and services as needed

---

## Blueprint Reference

| File | Blueprint Name | Route Prefix | Domain |
|------|---------------|--------------|--------|
| `pages.py` | `pages_bp` | `/`, `/crm`, `/quotes`, etc. | Page rendering |
| `auth_routes.py` | `auth_bp` | `/login`, `/api/auth/*` | Authentication |
| `admin.py` | `admin_bp` | `/admin/*`, `/api/admin/*` | Admin panel |
| `crm.py` | `crm_bp` | `/api/crm/customers`, `/api/crm/projects`, `/api/crm/quotes`, `/api/crm/stock`, `/api/crm/stats` | Core CRM |
| `crm_extended.py` | `crm_extended_bp` | `/api/crm/people/*`, `/api/crm/jobs/*`, `/api/crm/materials/*`, `/api/crm/payments/*`, `/api/crm/calendar/*` | Extended CRM |
| `crm_resources.py` | `crm_resources_bp` | `/api/crm/technicians`, `/api/crm/suppliers`, `/api/crm/price-classes`, `/api/crm/inventory` | CRM resources |
| `crm_v2.py` | `crm_v2_bp` | `/api/v2/crm/*` | CRM v2 with pagination |
| `crm_google.py` | `crm_google_bp` | `/api/crm/google/*` | Google Calendar/Gmail |
| `crm_integration.py` | `crm_integration_bp` | `/api/crm/integration/*` | CRM health/sync |
| `quote_automation.py` | `quote_automation_bp` | `/api/analyze`, `/api/generate_quote`, `/api/export_pdf`, `/api/generate-floorplan-pdf` | Quote automation |
| `electrical_cad.py` | `electrical_cad_bp` | `/api/cad/*` | CAD designer |
| `ai_mapping.py` | `ai_mapping_bp` | `/api/ai-mapping/*`, `/api/ai/mapping` | AI floor plan mapping |
| `board_builder.py` | `board_builder_bp` | `/api/board-builder/*` | Loxone board builder |
| `canvas.py` | `canvas_bp` | `/api/canvas/*`, `/api/takeoffs/*`, `/api/session/*` | Canvas editor |
| `simpro.py` | `simpro_bp` | `/api/simpro/*` | Simpro integration |
| `kanban.py` | `kanban_bp` | `/api/kanban/*` | Kanban board |
| `pdf_editor.py` | `pdf_editor_bp` | `/api/pdf-editor/*`, `/api/pdf-forms/*` | PDF forms |
| `learning.py` | `learning_bp` | `/api/learning/*` | AI learning system |
| `dashboard.py` | `dashboard_bp` | `/api/reminders`, `/api/dashboard/*`, `/api/notifications/*`, `/api/activity/*` | Dashboard |
| `ai_chat.py` | `ai_chat_bp` | `/api/ai/chat/*`, `/api/ai/insights`, `/api/ai/alerts`, `/api/ai/feedback`, `/api/ai/command` | AI chat |
| `scheduler.py` | `scheduler_bp` | `/api/scheduler/*` | Scheduler status |
| `misc.py` | `misc_bp` | `/api/data`, `/api/download/*`, `/api/inventory`, `/api/ai-chat` | Misc utilities |

---

## Where to Modify What

### CRM - Customers

**"I need to change how customers are created/updated"**

| Layer | File | What to modify |
|-------|------|----------------|
| Routes | `app/api/crm.py` | `@crm_bp.route('/api/crm/customers', ...)` |
| Business Logic | `crm_db_layer.py` | `CRMDatabaseLayer.create_customer()`, `update_customer()` |
| Repository | `services/crm_repository.py` | `CRMRepository.create_customer()` |
| Model | `database/models.py` | `class Customer` |

### CRM - Projects

**"I need to modify project management"**

| Layer | File | What to modify |
|-------|------|----------------|
| Routes | `app/api/crm.py` | `/api/crm/projects/*` routes |
| Business Logic | `crm_db_layer.py` | Project-related methods |
| Repository | `services/crm_repository.py` | `CRMRepository.create_project()`, etc. |
| Model | `database/models.py` | `class Project` |

### CRM - Quotes

**"I need to change quote handling"**

| Layer | File | What to modify |
|-------|------|----------------|
| Routes | `app/api/crm.py` | `/api/crm/quotes/*` routes |
| Extended Routes | `app/api/crm_extended.py` | Quote stock items, labour, cost centres |
| Business Logic | `crm_db_layer.py` | Quote methods |
| Model | `database/models.py` | `class Quote` |

### CRM - Jobs

**"I need to modify job management"**

| Layer | File | What to modify |
|-------|------|----------------|
| Routes | `app/api/crm_extended.py` | `/api/crm/jobs/*` routes |
| Business Logic | `crm_extended.py` | `load_jobs()`, `create_job()`, etc. |
| Repository | `services/crm_repository.py` | `CRMRepository.create_job()` |
| Model | `database/models.py` | `class Job` |

### CRM - People (Employees, Contractors, Contacts)

**"I need to modify people management"**

| Layer | File | What to modify |
|-------|------|----------------|
| Routes | `app/api/crm_extended.py` | `/api/crm/people/*` routes |
| Business Logic | `crm_extended.py` | `load_people()`, `create_person()` |

### CRM - Inventory / Stock

**"I need to change inventory handling"**

| Layer | File | What to modify |
|-------|------|----------------|
| Routes | `app/api/crm.py` | `/api/crm/stock/*` routes |
| Routes | `app/api/crm_resources.py` | `/api/crm/inventory` |
| Repository | `services/inventory_repository.py` | `InventoryRepository` |
| Model | `database/models.py` | `class InventoryItem` |

### CRM - Technicians, Suppliers, Price Classes

**"I need to modify technicians/suppliers/price classes"**

| Layer | File | What to modify |
|-------|------|----------------|
| Routes | `app/api/crm_resources.py` | `/api/crm/technicians`, `/api/crm/suppliers`, `/api/crm/price-classes` |
| Business Logic | `crm_db_layer.py` | Technician/supplier methods |
| Repository | `services/crm_repository.py` | Related methods |
| Model | `database/models.py` | `class Technician`, `class Supplier`, `class PriceClass` |

### CRM - Calendar Events

**"I need to modify calendar/scheduling"**

| Layer | File | What to modify |
|-------|------|----------------|
| Routes | `app/api/crm_extended.py` | `/api/crm/calendar/*` routes |
| Google Routes | `app/api/crm_google.py` | Google Calendar integration |
| Business Logic | `crm_extended.py` | Calendar event functions |
| Model | `database/models.py` | `class CalendarEvent` |

### Quote PDF Generation

**"I need to change how quote PDFs are generated"**

| Layer | File | What to modify |
|-------|------|----------------|
| Routes | `app/api/quote_automation.py` | `/api/generate_quote`, `/api/export_pdf`, `/api/generate-floorplan-pdf` |
| PDF Logic | `app/api/quote_automation.py` | PDF generation code within route handlers |
| Libraries | ReportLab, PyMuPDF | See imports in quote_automation.py |

### AI Floor Plan Analysis

**"I need to change AI analysis behavior"**

| Layer | File | What to modify |
|-------|------|----------------|
| Routes | `app/api/quote_automation.py` | `/api/analyze` route |
| AI Logic | `app.py` | `analyze_floorplan_with_ai()` function |
| AI Service | `ai_service.py` | AI abstraction layer |

### Electrical CAD Designer

**"I need to modify CAD functionality"**

| Layer | File | What to modify |
|-------|------|----------------|
| Routes | `app/api/electrical_cad.py` | `/api/cad/*` routes |
| Symbols | `app/api/electrical_cad.py` | `symbols` dictionary |
| Calculations | `electrical_calculations.py` | NEC code calculations |
| DXF Export | `dxf_exporter.py` | DXF file generation |
| Frontend | `static/cad-engine.js` | Canvas drawing engine |

### AI Mapping

**"I need to change AI mapping behavior"**

| Layer | File | What to modify |
|-------|------|----------------|
| Routes | `app/api/ai_mapping.py` | `/api/ai-mapping/*` routes |
| AI Logic | `app.py` | `ai_map_floorplan()` function |
| Learning | `app/api/learning.py` | Learning system routes |

### Board Builder

**"I need to modify board builder"**

| Layer | File | What to modify |
|-------|------|----------------|
| Routes | `app/api/board_builder.py` | `/api/board-builder/*` routes |
| Logic | `app/api/board_builder.py` | Board generation within handlers |

### Simpro Integration

**"I need to debug/modify Simpro sync"**

| Layer | File | What to modify |
|-------|------|----------------|
| Routes | `app/api/simpro.py` | `/api/simpro/*` routes |
| Config | `simpro_config/` | Simpro configuration files |

### Kanban Board

**"I need to modify task management"**

| Layer | File | What to modify |
|-------|------|----------------|
| Routes | `app/api/kanban.py` | `/api/kanban/*` routes |
| Repository | `services/kanban_repository.py` | `KanbanRepository` |
| Model | `database/models.py` | `class KanbanTask` |

### Dashboard & Notifications

**"I need to modify dashboard/notifications"**

| Layer | File | What to modify |
|-------|------|----------------|
| Routes | `app/api/dashboard.py` | `/api/dashboard/*`, `/api/notifications/*`, `/api/reminders` |
| Services | `services/notification_service.py` | `NotificationService` |
| Services | `services/reminder_service.py` | `ReminderService` |

### AI Chat Assistant

**"I need to modify AI chat behavior"**

| Layer | File | What to modify |
|-------|------|----------------|
| Routes | `app/api/ai_chat.py` | `/api/ai/chat/*`, `/api/ai/insights`, etc. |
| Service | `services/ai_chat_service.py` | `AIChatService` |
| Context | `services/ai_context.py` | `AIContextService` |

### Authentication

**"I need to modify login/auth"**

| Layer | File | What to modify |
|-------|------|----------------|
| Routes | `app/api/auth_routes.py` | `/login`, `/api/auth/*` routes |
| Logic | `auth.py` | Authentication functions, `login_required` decorator |
| Repository | `services/users_repository.py` | User database operations |
| Model | `database/models.py` | `class User` |

### Admin Panel

**"I need to modify admin settings"**

| Layer | File | What to modify |
|-------|------|----------------|
| Routes | `app/api/admin.py` | `/admin/*`, `/api/admin/*` routes |
| Template | `templates/admin.html` | Admin UI |

---

## Data Layer

### Database (Production)

```
database/
├── models.py       # All SQLAlchemy models
├── connection.py   # get_db_session(), is_db_configured()
└── seed.py         # get_or_create_default_organization()
```

**Key Models**: `Organization`, `User`, `Customer`, `Project`, `Quote`, `Job`, `InventoryItem`, `Technician`, `Supplier`, `CalendarEvent`, `Payment`, `KanbanTask`, `EventLog`, `Notification`

### Repository Pattern

```
services/
├── crm_repository.py       # CRMRepository - customers, projects, quotes, jobs
├── inventory_repository.py # InventoryRepository - stock items
├── kanban_repository.py    # KanbanRepository - tasks
├── users_repository.py     # UsersRepository - users
```

### Data Layer Modules

| Module | Purpose |
|--------|---------|
| `crm_db_layer.py` | Database-backed CRM operations (production) |
| `crm_data_layer.py` | JSON-backed CRM operations (local dev fallback) |
| `crm_extended.py` | People, jobs, materials, payments, calendar |
| `crm_integration.py` | CRM health checks, data aggregation |

---

## Storage Policy

### Environment-Based Storage Behavior

The app uses a **centralized storage policy** defined in `config.py`:

| Environment | DATABASE_URL | CRM/Auth/Kanban Storage | Behavior |
|-------------|--------------|-------------------------|----------|
| **Production** | Required | Database ONLY | App fails to start without DB |
| **Development** | Set | Database | Uses PostgreSQL |
| **Development** | Not set | JSON fallback | Uses local JSON files |

### Key Functions in `config.py`

```python
from config import (
    is_production,        # True if APP_ENV/FLASK_ENV == 'production'
    has_database,         # True if DATABASE_URL is set
    allow_json_persistence,  # True only in dev without DB
    validate_storage_config, # Raises error if prod without DB
    StoragePolicyError    # Exception for policy violations
)
```

### Startup Validation

On app startup (`app/__init__.py`):
- If `is_production() == True` AND `has_database() == False`:
  - App **FAILS TO START** with error:
    `"DATABASE_URL is required in production; JSON persistence is disabled."`

### What This Means for CRM/Auth/Kanban

| Data Type | Production | Development (with DB) | Development (no DB) |
|-----------|------------|----------------------|---------------------|
| Customers | Database | Database | JSON files |
| Projects | Database | Database | JSON files |
| Quotes | Database | Database | JSON files |
| Jobs | Database | Database | JSON files |
| Users/Auth | Database | Database | JSON files |
| Kanban Tasks | Database | Database | JSON files |
| Technicians | Database | Database | JSON files |
| Suppliers | Database | Database | JSON files |
| Calendar | Database | Database | JSON files |

### Session/Config JSON (ALWAYS ALLOWED)

These JSON files are **NOT affected** by the storage policy and work in all environments:

- `cad_sessions/*.json` - CAD session state
- `session_data/*.json` - Analysis session data
- `pdf_editor_autosave/*.json` - PDF editor autosave
- `pdf_templates.json`, `pdf_forms.json` - PDF templates
- `data/automation_data.json` - Pricing configuration
- `simpro_config/*.json` - Simpro OAuth config
- `google_config.json` - Google OAuth config
- `outputs/*.json` - Export files

---

## House Rules for Development

### 1. No Routes in `app.py`

**NEVER** add `@app.route()` decorators to `app.py`. All routes must be in `app/api/*.py` blueprints.

### 2. New Endpoints Go in Appropriate Blueprint

- CRM customer routes → `app/api/crm.py`
- CRM extended features → `app/api/crm_extended.py`
- New CRM resources → `app/api/crm_resources.py`
- New AI features → `app/api/ai_chat.py` or `ai_mapping.py`
- New integrations → Create new blueprint if needed

### 3. Heavy Logic Belongs in Services/Data Layer

Route handlers should be thin. Complex business logic goes in:
- `services/*.py` for new services
- `crm_db_layer.py` / `crm_data_layer.py` for CRM operations
- Existing modules for related functionality

### 4. No Live JSON Storage in Production

- **Database** is the source of truth for all persistent data
- JSON files for CRM/auth/kanban are **disabled in production**
- The app will fail to start in production without `DATABASE_URL`
- JSON files are ONLY for:
  - Static configuration (`data/automation_data.json`)
  - Session/state data (CAD, PDF autosave, etc.)
  - Local development fallback (when no `DATABASE_URL`)

### 5. No Duplicate Implementations

- Don't create "shadow" versions of existing features
- Check existing modules before creating new ones
- Reuse existing repository/service methods

### 6. Register New Blueprints in `app/__init__.py`

If you create a new blueprint:

```python
# In app/__init__.py
from app.api.new_feature import new_feature_bp
app.register_blueprint(new_feature_bp)
```

### 7. Database Changes Need Migrations

If you modify `database/models.py`:

```bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### 8. Test After Changes

```bash
# Start app
python app.py

# Test affected routes
curl http://localhost:5000/api/crm/stats
```

---

## Quick Reference: File Locations

| I want to... | Look in... |
|--------------|------------|
| Add a new CRM route | `app/api/crm.py` or `crm_extended.py` |
| Modify database models | `database/models.py` |
| Change how customers are stored | `services/crm_repository.py`, `crm_db_layer.py` |
| Add a new page | `app/api/pages.py`, `templates/` |
| Modify AI behavior | `app.py` (AI functions), `ai_service.py` |
| Change quote PDF format | `app/api/quote_automation.py` |
| Add background job | `services/scheduler.py` |
| Modify authentication | `auth.py`, `app/api/auth_routes.py` |
| Add new API endpoint | Create/modify appropriate blueprint in `app/api/` |

---

## Services Directory Note

There are two `services/` directories:

| Directory | Purpose | Status |
|-----------|---------|--------|
| `/services/` (root) | Main services - repositories, AI, scheduler | **Active - Use this** |
| `/app/services/` | Placeholder for future extraction | Empty (placeholder) |

When adding new services, add them to the root `/services/` directory.

