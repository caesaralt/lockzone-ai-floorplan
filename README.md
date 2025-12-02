# Integratd Living - AI-Powered Business Automation Platform

A comprehensive business management and design tool for **home automation installation companies**. Combines AI-powered floor plan analysis, electrical CAD design, CRM, quote generation, and project management in one platform.

**Live App**: https://lockzone-ai-floorplan.onrender.com

---

## Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- PostgreSQL (optional for local dev - app falls back to JSON files)

### 1. Clone and Setup

```bash
git clone https://github.com/caesaralt/lockzone-ai-floorplan.git
cd lockzone-ai-floorplan

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file:

```bash
# Required for AI features
ANTHROPIC_API_KEY=sk-ant-...

# Optional - enables web search in AI
TAVILY_API_KEY=tvly-...

# Required for Flask security
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')

# Database (see Storage Policy below)
# For local dev: optional (JSON fallback if not set)
# For production: REQUIRED (app won't start without it)
DATABASE_URL=postgresql://user:password@localhost:5432/lockzone_dev

# Environment (optional, defaults to 'development')
APP_ENV=development  # or 'production'
```

### 3. Run the App

```bash
python app.py
# Open http://localhost:5000
```

### Storage Policy

| Environment | DATABASE_URL | CRM/Auth/Kanban Storage |
|-------------|--------------|-------------------------|
| **Production** | **Required** | Database only (JSON disabled) |
| **Development** | Optional | Database if set, JSON fallback if not |

- In **production** (`APP_ENV=production`), the app **fails to start** without `DATABASE_URL`
- Session/config JSON files (CAD sessions, PDF autosave, etc.) are always allowed

---

## Architecture Overview

This app uses a **modular Flask blueprint architecture**:

```
app.py                    # Thin entrypoint - NO routes, only app config
app/
├── __init__.py           # App factory, blueprint registration
├── api/                  # All HTTP route handlers (22 blueprint files)
│   ├── crm.py            # Core CRM (customers, projects, quotes, stock)
│   ├── crm_extended.py   # Extended CRM (people, jobs, materials, payments)
│   ├── crm_resources.py  # CRM resources (technicians, suppliers, inventory)
│   ├── crm_v2.py         # CRM v2 API (pagination, search)
│   ├── crm_google.py     # Google Calendar/Gmail integration
│   ├── crm_integration.py# CRM health checks and sync
│   ├── quote_automation.py # AI quote generation
│   ├── electrical_cad.py # CAD designer routes
│   ├── ai_mapping.py     # AI floor plan mapping
│   ├── board_builder.py  # Loxone board builder
│   ├── simpro.py         # Simpro CRM integration
│   ├── kanban.py         # Kanban task board
│   ├── dashboard.py      # Dashboard and notifications
│   ├── ai_chat.py        # AI chat assistant
│   └── ... (more blueprints)
├── utils/                # Shared utilities
└── services/             # New services (placeholder for future extraction)

services/                 # Business logic services (repository pattern)
├── crm_repository.py     # CRM database operations
├── inventory_repository.py
├── scheduler.py          # Background jobs
└── ...

database/                 # Database layer
├── models.py             # SQLAlchemy models
├── connection.py         # DB connection management
└── seed.py               # Default data seeding
```

### Data Storage

- **Production**: PostgreSQL database (configured via `DATABASE_URL`)
- **Local Development**: Falls back to JSON files in `crm_data/` if no database configured
- **Static Config**: `data/automation_data.json` for pricing configuration

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed documentation on where to modify each feature.

---

## Key Features

| Feature | Description | Route Prefix |
|---------|-------------|--------------|
| **CRM Dashboard** | Customers, projects, quotes, inventory | `/crm`, `/api/crm/*` |
| **Quote Automation** | AI analyzes floor plans, generates quotes | `/quotes`, `/api/analyze` |
| **Electrical CAD** | Draw electrical plans with NEC compliance | `/electrical-cad`, `/api/cad/*` |
| **AI Mapping** | Detect electrical components in plans | `/mapping`, `/api/ai-mapping/*` |
| **Board Builder** | Design automation equipment boards | `/board-builder`, `/api/board-builder/*` |
| **Kanban Board** | Project task management | `/kanban`, `/api/kanban/*` |
| **Canvas Editor** | Interactive floor plan editing | `/canvas`, `/api/canvas/*` |

---

## API Documentation

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/crm/customers` | GET, POST | Customer CRUD |
| `/api/crm/projects` | GET, POST | Project management |
| `/api/crm/quotes` | GET, POST | Quote management |
| `/api/crm/stats` | GET | Dashboard statistics |
| `/api/analyze` | POST | AI floor plan analysis |
| `/api/generate_quote` | POST | Generate quote PDF |
| `/api/health` | GET | Health check |

See individual blueprint files in `app/api/` for complete route documentation.

---

## Deployment (Render)

The app is configured for Render deployment via `render.yaml`:

1. Push to GitHub main branch
2. Render auto-deploys
3. Environment variables set in Render dashboard

Required env vars on Render:
- `DATABASE_URL` (from Render PostgreSQL)
- `ANTHROPIC_API_KEY`
- `SECRET_KEY`

---

## Development Guide

For detailed information on:
- Where to modify specific features
- How the data layer works
- House rules for development

See **[ARCHITECTURE.md](ARCHITECTURE.md)**

---

## Testing

```bash
# Run tests
pytest

# Test specific module
pytest tests/test_validators.py
```

---

## License

Proprietary - All rights reserved.
