# CONTEXT.md - Integratd Living Platform

> **Purpose**: Technical context for developers and AI agents working on this codebase
> **Last Updated**: December 2024
> **Architecture**: Modular Flask Blueprints + PostgreSQL

---

## What is This Application?

**Integratd Living** (formerly LockZone AI Floor Plan Analyzer) is a business management platform for **home automation installation companies**. It provides:

1. **AI-powered floor plan analysis** - Upload PDF, AI places automation components
2. **Electrical CAD Designer** - Draw electrical plans with NEC code compliance
3. **CRM System** - Manage customers, projects, quotes, inventory, calendar
4. **Quote Generation** - Automatically generate quotes from floor plans
5. **Project Management** - Kanban boards, job tracking, room assignments

Think of it as: **"AI-powered Salesforce + AutoCAD for smart home installers"**

---

## Architecture Summary

### Backend Structure

```
app.py                      # ~1,750 lines - Thin entrypoint, NO routes
                            # Only handles: Flask app creation, config, blueprint registration

app/
├── __init__.py             # App factory, registers all 22 blueprints
├── api/                    # ALL HTTP routes live here (22 blueprint files)
│   ├── pages.py            # Page rendering (/, /crm, /quotes, etc.)
│   ├── auth_routes.py      # Authentication (/login, /api/auth/*)
│   ├── admin.py            # Admin panel (/admin/*)
│   ├── crm.py              # Core CRM routes
│   ├── crm_extended.py     # Extended CRM (people, jobs, materials)
│   ├── crm_resources.py    # CRM resources (technicians, suppliers)
│   ├── crm_v2.py           # CRM v2 API with pagination
│   ├── crm_google.py       # Google Calendar/Gmail
│   ├── crm_integration.py  # CRM health and sync
│   ├── quote_automation.py # AI quote generation
│   ├── electrical_cad.py   # CAD designer
│   ├── ai_mapping.py       # AI floor plan mapping
│   ├── board_builder.py    # Loxone board builder
│   ├── canvas.py           # Canvas editor
│   ├── simpro.py           # Simpro integration
│   ├── kanban.py           # Kanban board
│   ├── pdf_editor.py       # PDF forms editor
│   ├── learning.py         # AI learning system
│   ├── dashboard.py        # Dashboard/notifications
│   ├── ai_chat.py          # AI chat assistant
│   ├── scheduler.py        # Scheduler status
│   └── misc.py             # Misc utilities
├── utils/                  # Shared utility functions
│   ├── helpers.py          # JSON file operations
│   ├── image_utils.py      # Image/PDF conversion
│   └── ai_tools.py         # AI tool schemas
└── services/               # Placeholder for future service extraction
```

### Data Layer

```
services/                   # Business logic services (at project root)
├── crm_repository.py       # CRM database operations
├── inventory_repository.py # Inventory operations
├── kanban_repository.py    # Kanban operations
├── users_repository.py     # User operations
├── ai_chat_service.py      # AI chat logic
├── ai_context.py           # AI context building
├── event_logger.py         # Activity logging
├── notification_service.py # Notifications
├── reminder_service.py     # Reminders
└── scheduler.py            # Background jobs

crm_data_layer.py           # JSON-based data access (local dev fallback)
crm_db_layer.py             # Database-backed data access (production)
crm_extended.py             # Extended CRM operations
crm_integration.py          # CRM health checks

database/
├── models.py               # SQLAlchemy models (~1,070 lines)
├── connection.py           # Database connection management
└── seed.py                 # Default organization/user seeding
```

### Data Storage Policy

| Environment | DATABASE_URL | CRM/Auth/Kanban | Session/Config JSON |
|-------------|--------------|-----------------|---------------------|
| **Production** | **REQUIRED** | Database only | Allowed |
| **Development** | Set | Database | Allowed |
| **Development** | Not set | JSON fallback | Allowed |

**Critical Rules**:
- In **production**, `DATABASE_URL` is **mandatory**. App fails to start without it.
- JSON persistence for CRM/auth/kanban is **disabled in production**.
- Session/config JSON files (CAD sessions, PDF autosave, automation_data.json) are always allowed.
- See `config.py` for the centralized storage policy helpers.

**Static Config**: `data/automation_data.json` - Pricing, tiers (always allowed)

---

## Tech Stack

### Backend
- **Flask 3.0.0** - Web framework with Blueprints
- **SQLAlchemy** - ORM for PostgreSQL
- **Anthropic Claude API** - AI for floor plan analysis
- **Tavily API** - Web search for building codes
- **PyMuPDF (fitz)** - PDF processing
- **ReportLab** - PDF generation
- **Pillow** - Image processing

### Frontend
- **Jinja2** - HTML templating
- **Tailwind CSS** - Styling (via CDN)
- **Vanilla JavaScript** - No frameworks

### External Services
- **Anthropic AI** (claude-sonnet-4-5) - Vision analysis
- **Tavily** - Web search
- **Simpro** (optional) - CRM integration
- **Google Calendar/Gmail** (optional) - OAuth2

---

## Key Modules

### 1. CRM System (`/crm`)
- **Routes**: `app/api/crm.py`, `crm_extended.py`, `crm_resources.py`, `crm_v2.py`
- **Data**: `crm_db_layer.py`, `services/crm_repository.py`
- **Features**: Customers, projects, quotes, jobs, inventory, calendar

### 2. Quote Automation (`/quotes`)
- **Routes**: `app/api/quote_automation.py`
- **Features**: Upload floor plan → AI analysis → Generate quote PDF

### 3. Electrical CAD (`/electrical-cad`)
- **Routes**: `app/api/electrical_cad.py`
- **Features**: Draw electrical plans, NEC validation, DXF export

### 4. AI Mapping (`/mapping`)
- **Routes**: `app/api/ai_mapping.py`
- **Features**: Detect outlets, switches, panels in floor plans

### 5. Board Builder (`/board-builder`)
- **Routes**: `app/api/board_builder.py`
- **Features**: Design automation equipment boards

### 6. Kanban (`/kanban`)
- **Routes**: `app/api/kanban.py`
- **Features**: Task management with drag-and-drop

---

## Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...     # AI features
SECRET_KEY=<random hex>          # Flask security

# Production
DATABASE_URL=postgresql://...    # PostgreSQL connection

# Optional
TAVILY_API_KEY=tvly-...          # Web search
OPENAI_API_KEY=sk-...            # Alternative AI
SIMPRO_API_KEY=...               # Simpro integration
GOOGLE_CLIENT_ID=...             # Google OAuth
GOOGLE_CLIENT_SECRET=...         # Google OAuth
```

---

## Development Notes

### Adding New Features

1. **New routes** → Create/modify blueprint in `app/api/`
2. **Business logic** → Add to `services/` or data layer modules
3. **Database changes** → Update `database/models.py`, create Alembic migration
4. **No routes in app.py** → All routes must be in blueprints

### Testing Locally

```bash
# Start app
python app.py

# Test endpoints
curl http://localhost:5000/api/health
curl http://localhost:5000/api/crm/stats
```

### Deployment

Push to GitHub main branch → Render auto-deploys

---

## For AI Agents

When asked to modify code:

1. **Read this file first** to understand architecture
2. **Check ARCHITECTURE.md** for specific file locations
3. **Routes are in `app/api/`**, not `app.py`
4. **Database models in `database/models.py`**
5. **Don't create duplicate implementations**

See **[ARCHITECTURE.md](ARCHITECTURE.md)** for detailed "where to modify what" guide.
