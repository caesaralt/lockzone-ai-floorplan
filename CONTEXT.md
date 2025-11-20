# CONTEXT.md - LockZone AI Floor Plan Analyzer

> **Purpose**: Complete technical context for understanding this application
> **Last Updated**: 2025-11-20
> **For**: Developers, AI assistants, and anyone working on this project

---

## What is This Application?

**LockZone AI Floor Plan Analyzer** is a business management and design tool for **home automation installation companies**. It combines:

1. **AI-powered floor plan analysis** - Upload a PDF floor plan, AI places automation components
2. **Electrical CAD Designer** - Draw electrical plans with NEC code compliance
3. **CRM System** - Manage customers, projects, quotes, and inventory
4. **Quote Generation** - Automatically generate quotes from floor plans
5. **Project Management** - Track installations with Kanban boards and room assignments

Think of it as: **"AI-powered Salesforce + AutoCAD for smart home installers"**

---

## The Problem It Solves

Home automation installers need to:
- Analyze floor plans and figure out where to place lights, sensors, keypads
- Generate quotes with multiple pricing tiers (Basic/Premium/Deluxe)
- Track which serial number goes in which room during installation
- Design electrical layouts that comply with building codes
- Manage customers, jobs, and inventory

Without this tool, they'd use:
- AutoCAD (expensive, complex) for electrical design
- Excel spreadsheets for quotes
- Pen and paper for room assignments
- Separate CRM software

This app combines everything in one place with AI assistance.

---

## Tech Stack

### Backend (Python/Flask)
- **Flask 3.0.0** - Web framework
- **Anthropic Claude API** - AI for floor plan analysis (vision + reasoning)
- **Tavily API** - Web search for building codes
- **PyPDF + PyMuPDF (fitz)** - PDF processing
- **ReportLab** - PDF generation for quotes
- **Pillow (PIL)** - Image processing
- **JSON files** - Data storage (database support exists but disabled)

### Frontend
- **Jinja2** - HTML templating
- **Tailwind CSS** - Styling (via CDN)
- **Vanilla JavaScript** - No frameworks, modern ES6+
- **Custom CAD engine** - Canvas-based electrical drawing

### External Services
- **Anthropic AI** (claude-sonnet-4-5) - AI analysis
- **Tavily** - Web search
- **Simpro** (optional) - CRM integration via API
- **Google Calendar/Gmail** (optional) - Via OAuth2

---

## File Structure (What's Actually Used)

```
lockzone-ai-floorplan/
├── app.py                          # MAIN APPLICATION (8,871 lines)
│   └── All routes, business logic, AI integration
│
├── Supporting Python Files (Actually Used)
│   ├── app_init.py                 # App initialization
│   ├── auth.py                     # Authentication system
│   ├── security.py                 # Security headers, CORS
│   ├── health_checks.py            # /api/health endpoints
│   ├── logging_config.py           # Logging setup
│   ├── config.py                   # Configuration management
│   ├── validators.py               # Input validation
│   ├── crm_integration.py          # CRM utilities
│   ├── electrical_calculations.py  # NEC code calculations
│   └── dxf_exporter.py             # CAD file export
│
├── templates/ (Active Templates)
│   ├── template_unified.html       # Landing page (/)
│   ├── index.html                  # Quote Tool (/quotes)
│   ├── crm.html                    # CRM Dashboard (/crm)
│   ├── canvas.html                 # Interactive Canvas (/canvas)
│   ├── mapping.html                # Electrical Mapping (/mapping)
│   ├── cad_designer.html           # CAD Designer (/electrical-cad)
│   ├── board_builder.html          # Board Builder (/board-builder)
│   ├── kanban.html                 # Kanban Board (/kanban)
│   ├── learning.html               # AI Learning (/learning)
│   ├── simpro.html                 # Simpro Integration (/simpro)
│   ├── admin.html                  # Admin Panel (/admin)
│   ├── login.html                  # Login Page (/login)
│   ├── template_ai_mapping.html    # AI Mapping (/ai-mapping)
│   └── unified_editor.html         # Canvas Editor
│
├── static/ (JavaScript Libraries)
│   ├── cad-engine.js               # Core CAD drawing engine
│   ├── electrical-symbols.js       # Symbol library
│   ├── measurement-tools.js        # Measurement tools
│   ├── validation-engine.js        # NEC code validation
│   ├── panel-schedule.js           # Electrical panel schedules
│   ├── cable-schedule.js           # Cable/conduit schedules
│   ├── wire-labeling.js            # Wire labeling system
│   ├── hatching-patterns.js        # CAD hatching
│   ├── schematic-view.js           # Schematic diagrams
│   └── pdf-export.js               # PDF export
│
├── data/ (Runtime Data - JSON Files)
│   ├── automation_data.json        # Pricing configuration
│   ├── crm_data/                   # CRM data files
│   │   ├── customers.json
│   │   ├── projects.json
│   │   ├── quotes.json
│   │   ├── stock.json
│   │   ├── google_config.json
│   │   └── users.json
│   ├── cad_sessions/               # CAD session files
│   ├── session_data/               # Analysis session cache
│   ├── learning_data/              # AI learning corrections
│   ├── mapping_learning/           # Electrical mapping learning
│   ├── simpro_config/              # Simpro API config
│   ├── uploads/                    # Uploaded PDFs
│   ├── outputs/                    # Generated PDFs
│   └── ai_mapping/                 # Mapping outputs
│
├── Deployment Files
│   ├── requirements.txt            # Python dependencies
│   ├── runtime.txt                 # Python version (3.11.9)
│   ├── Procfile                    # Process definition
│   ├── gunicorn_config.py          # Server config
│   ├── render.yaml                 # Render.com deployment
│   └── build.sh                    # Build script
│
└── Utility Scripts
    ├── config_updater.py           # Update pricing config
    ├── migrate_kanban_to_db.py     # Database migration (unused)
    └── deploy.sh                   # Deployment helper
```

---

## Core Modules (What Each Does)

### 1. Quote Tool (`/quotes` - `index.html`)

**What it does**: Upload a floor plan PDF, AI analyzes it and places automation components, generates a quote.

**How it works**:
1. User uploads PDF floor plan
2. Converts PDF to image
3. Sends to Claude AI with vision
4. AI identifies rooms, walls, and places components (lights, sensors, keypads)
5. Generates annotated PDF + quote PDF with pricing

**AI Features**:
- Vision analysis of floor plan
- Web search for installation standards
- Extended thinking (8000 token budget)
- Places symbols based on room type and best practices

**API Endpoints**:
- `POST /api/analyze` - Analyze floor plan
- `POST /api/generate_quote` - Generate quote PDF
- `GET /api/data` - Get pricing configuration
- `POST /api/data` - Update pricing

**Files**: `app.py:1770-4509`, `templates/index.html`

---

### 2. CRM System (`/crm` - `crm.html`)

**What it does**: Complete business management - customers, projects, quotes, inventory, Google integration.

**Features**:
- **Customers**: Contact info, status tracking
- **Projects**: Job management with cost centres, room assignments
- **Quotes**: Generate quotes, convert to projects
- **Stock/Inventory**: Track products with serial numbers
- **Room Assignments**: Assign serial numbers to rooms for installation
- **Cost Centres**: Budget tracking with visual colors
- **Google Integration**: Calendar events, Gmail
- **AI Assistant**: Chat with AI about CRM data

**Key Workflows**:
1. **Quote → Project**: Create quote, convert to project, all data migrates
2. **Serial Number Tracking**: Add stock → assign to room → mark installed
3. **Cost Centres**: Create budget categories, add items, auto-calculate totals

**API Endpoints** (70+ endpoints):
- `/api/crm/customers` - Customer CRUD
- `/api/crm/projects` - Project management
- `/api/crm/quotes` - Quote management
- `/api/crm/stock` - Inventory tracking
- `/api/crm/projects/<id>/room-assignments` - Room assignments
- `/api/crm/projects/<id>/cost-centres` - Budget tracking
- `/api/crm/google/*` - Google Calendar/Gmail integration
- `/api/crm/stats` - Dashboard statistics

**Data Storage**:
- `crm_data/customers.json`
- `crm_data/projects.json`
- `crm_data/quotes.json`
- `crm_data/stock.json`

**Files**: `app.py:2516-7803`, `templates/crm.html`

---

### 3. Electrical Mapping Tool (`/mapping` - `mapping.html`)

**What it does**: AI-powered electrical plan analysis with NEC code compliance.

**How it works**:
1. Upload electrical floor plan image
2. AI detects outlets, switches, panels, circuits
3. Validates against NEC codes (210.52, GFCI requirements, etc.)
4. Generates marked-up image with annotations
5. Learning system improves from corrections

**AI Features**:
- Vision analysis of electrical symbols
- Web search for NEC codes
- Extended thinking (8000 tokens)
- Validates spacing, heights, GFCI requirements

**API Endpoints**:
- `POST /api/ai-mapping/analyze` - Analyze electrical plan
- `POST /api/ai-mapping/save-correction` - Save corrections
- `GET /api/ai-mapping/learning-stats` - Learning metrics
- `GET /api/ai-mapping/history` - Past analyses

**Files**: `app.py:979-1966`, `templates/mapping.html`

---

### 4. Electrical CAD Designer (`/electrical-cad` - `cad_designer.html`)

**What it does**: Full-featured electrical CAD system for drawing electrical plans.

**Features**:
- **Symbol Library**: Outlets, switches, panels, lighting
- **Wire Routing**: Draw and label wires
- **Panel Schedules**: Generate electrical panel schedules
- **Cable Schedules**: Track conduit and cable runs
- **NEC Validation**: Check code compliance
- **PDF/DXF Export**: Export to standard formats

**CAD Engine** (`static/cad-engine.js`):
- Canvas-based drawing
- Layers system
- Snap-to-grid
- Measurement tools
- Undo/redo

**API Endpoints**:
- `POST /api/cad/new` - Create session
- `POST /api/cad/save` - Save drawing
- `GET /api/cad/load/<id>` - Load session
- `GET /api/cad/symbols` - Get symbol library
- `POST /api/cad/calculate-circuit` - Circuit calculations
- `POST /api/cad/export` - Export PDF/DXF

**Files**: `app.py:2732-3936`, `templates/cad_designer.html`, `static/cad-engine.js`

---

### 5. Interactive Canvas (`/canvas` - `canvas.html`, `unified_editor.html`)

**What it does**: Drag-and-drop symbol placement on floor plans with real-time quote updates.

**Features**:
- Load floor plan image
- Drag symbols from palette
- Snap to grid
- Real-time cost calculation
- Export annotated PDF + quote

**Use Case**: Refine AI-generated quotes or manually create quotes.

**Files**: `app.py:1826-1871`, `templates/canvas.html`

---

### 6. Board Builder (`/board-builder` - `board_builder.html`)

**What it does**: Design automation equipment boards (Loxone, etc.) for home automation systems.

**Features**:
- Component selection (Miniserver, extensions, power supplies)
- Auto-layout based on selected automation types
- Connection validation
- Export to CRM

**API Endpoints**:
- `POST /api/board-builder/generate` - Generate board layout
- `GET /api/board-builder/available-sessions` - List sessions
- `POST /api/board-builder/export/crm` - Export to CRM

**Files**: `app.py:2013-2493`, `templates/board_builder.html`

---

### 7. Kanban Board (`/kanban` - `kanban.html`)

**What it does**: Project management with drag-and-drop task cards.

**Features**:
- Columns: To Do, In Progress, Done
- Task cards with notes, due dates, assignments
- Color coding
- Archive completed tasks

**API Endpoints**:
- `GET /api/kanban/tasks` - List tasks
- `POST /api/kanban/tasks` - Create task
- `PUT /api/kanban/tasks/<id>` - Update task
- `DELETE /api/kanban/tasks/<id>` - Delete task

**Files**: `app.py:8635-8783`, `templates/kanban.html`

---

### 8. Learning System (`/learning` - `learning.html`)

**What it does**: AI improvement through human feedback - save corrections to improve future analyses.

**How it works**:
1. AI makes analysis
2. User corrects mistakes
3. System saves correction
4. Future prompts include learning examples
5. AI improves over time

**Files**: `app.py:190-483`, `templates/learning.html`

---

### 9. Simpro Integration (`/simpro` - `simpro.html`)

**What it does**: Optional integration with Simpro CRM software via API.

**Features**:
- OAuth2 authentication
- Import customers, sites, catalog
- Sync jobs and quotes

**API Endpoints**:
- `POST /api/simpro/connect` - OAuth connect
- `POST /api/simpro/sync` - Sync data
- `GET /api/simpro/customers` - Get customers

**Files**: `app.py:5006-5363`, `templates/simpro.html`

---

### 10. Admin & Auth System (`/admin`, `/login`)

**What it does**: User management and authentication.

**Features**:
- Login/logout
- User CRUD
- Role-based permissions
- Session management

**API Endpoints**:
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET/POST /api/auth/users`

**Files**: `auth.py`, `templates/login.html`, `templates/admin.html`

---

## Data Flow Example

### Complete Business Workflow

```
1. Upload Floor Plan (Quote Tool)
   ↓
2. AI Analyzes → Places Components
   ↓
3. Generate Quote (Quote Tool)
   ↓
4. Create Quote in CRM
   ↓
5. Add Cost Centres with Budget Items
   ↓
6. Customer Accepts Quote
   ↓
7. Convert Quote → Project (all data migrates)
   ↓
8. Add Stock Items with Serial Numbers
   ↓
9. Assign Serial Numbers to Rooms
   ↓
10. Installers Use Room Assignments
   ↓
11. Mark Items as Installed
   ↓
12. Track Progress in Kanban
   ↓
13. Project Complete
```

---

## AI Integration (How AI Works)

### 1. Quote Analysis AI

**Location**: `app.py:685-979` (`analyze_floorplan_with_ai`)

**What it does**:
- Takes PDF floor plan image
- Identifies rooms, walls, doors, windows
- Places automation components intelligently
- Returns symbol positions

**How it works**:
```python
# 1. Convert PDF to image
image = convert_pdf_to_image(pdf_path)

# 2. Send to Claude with vision
response = anthropic.messages.create(
    model="claude-sonnet-4-5",
    messages=[{
        "role": "user",
        "content": [
            {"type": "image", "source": {"data": base64_image}},
            {"type": "text", "text": "Analyze this floor plan..."}
        ]
    }],
    tools=[web_search_tool],  # Can search for building codes
    thinking={"type": "enabled", "budget_tokens": 8000},
    max_tokens=4000
)

# 3. Extract symbol placements from response
symbols = extract_symbols(response)
```

**AI Capabilities**:
- **Vision**: Sees floor plan layout
- **Web Search**: Looks up "typical living room lighting placement"
- **Extended Thinking**: 8000 token reasoning budget
- **Agentic Loop**: Can iterate up to 10 times

---

### 2. Electrical Mapping AI

**Location**: `app.py:979-1332` (`ai_map_floorplan`)

**What it does**:
- Analyzes electrical plans
- Detects outlets, switches, panels
- Validates NEC code compliance
- Generates markup annotations

**AI searches for**:
- "NEC code 210.52 outlet spacing requirements"
- "GFCI requirements kitchen bathroom"
- "Arc-fault circuit requirements bedrooms"

---

### 3. AI Chat Assistant

**Location**: `app.py:7981-8453` (`ai_chat`)

**Available on**: All pages with chat widget

**Can do**:
- Answer questions about data
- Analyze attached images
- Search web for information
- 10000 token thinking budget (highest!)

---

## API Keys Required

```bash
# Required for AI features
ANTHROPIC_API_KEY=sk-ant-...

# Optional for web search (1000 free searches/month)
TAVILY_API_KEY=tvly-...

# Required for Flask security
SECRET_KEY=<random hex string>

# Optional
SIMPRO_API_KEY=...
SIMPRO_API_URL=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

---

## What's NOT Working / Needs Improvement

### 1. Database Support (Disabled)
- App uses JSON files for all data
- Database code exists but is disabled (`USE_DATABASE = False`)
- **Why**: JSON is simpler, more portable, no migration issues
- **Risk**: Not scalable beyond ~1000 records per file

### 2. PDF Upload in Quote Tool
- Frontend exists but AI analysis might fail on complex PDFs
- **Issue**: Need better PDF → image conversion
- **Workaround**: Use high-quality vector PDFs

### 3. Simpro Integration
- OAuth flow exists but not fully tested
- **Status**: Basic structure ready, needs real Simpro account to test

### 4. Google Integration
- OAuth flow exists
- Calendar/Gmail endpoints exist
- **Status**: Not tested with real Google account

### 5. No Real-Time Collaboration
- Multiple users can't edit same session simultaneously
- **Why**: JSON file locking issues

### 6. No Automated Backups
- Data is in JSON files
- **Risk**: File corruption = data loss
- **Needed**: Automated backup script

### 7. File Uploads Not Cleaned Up
- `uploads/` and `outputs/` folders grow indefinitely
- **Needed**: Cleanup job for old files

---

## Deployment

### Current: Render.com
```yaml
# render.yaml
services:
  - type: web
    name: lockzone-ai-floorplan
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    envVars:
      - key: ANTHROPIC_API_KEY
      - key: TAVILY_API_KEY
      - key: SECRET_KEY
```

### To Deploy:
```bash
git push origin main
# Render auto-deploys from main branch
```

### Environment Variables on Render:
1. Dashboard → Service → Environment
2. Add: `ANTHROPIC_API_KEY`, `TAVILY_API_KEY`, `SECRET_KEY`
3. Save → Auto-redeploy

---

## Development Setup

```bash
# 1. Clone
git clone https://github.com/caesaralt/lockzone-ai-floorplan.git
cd lockzone-ai-floorplan

# 2. Virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install
pip install -r requirements.txt

# 4. Environment variables
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
echo "TAVILY_API_KEY=tvly-..." >> .env
echo "SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')" >> .env

# 5. Run
python app.py
# Open http://localhost:5000
```

---

## Testing the App

### 1. Test Quote Tool
```bash
# Upload PDF at /quotes
# Check console for:
🔍 AI searching: home automation lighting placement best practices
```

### 2. Test CRM
```bash
curl http://localhost:5000/api/crm/stats
# Should show customers, projects, stock value
```

### 3. Test Validation
```bash
# All should return errors:
curl -X POST http://localhost:5000/api/crm/customers -d '{}'
curl -X POST http://localhost:5000/api/crm/quotes -d '{}'
curl -X POST http://localhost:5000/api/crm/projects -d '{}'
```

---

## Common Issues & Solutions

### Issue: "ANTHROPIC_API_KEY not set"
**Solution**: Add to environment variables or `.env` file

### Issue: "ModuleNotFoundError: No module named 'X'"
**Solution**: `pip install -r requirements.txt`

### Issue: "Port 5000 already in use"
**Solution**: `pkill -f "python.*app.py"` or change port in `app.py`

### Issue: JSON file corrupted
**Solution**: Check `data/` folder, restore from backup or reset to `{}`

### Issue: AI returns empty results
**Solution**: Check API key, check logs for errors, verify PDF quality

---

## Code Organization

### app.py Structure (8,871 lines)

```python
# Lines 1-131: Imports & Configuration
# Lines 133-175: DEFAULT_DATA (pricing config)
# Lines 176-483: Data & Learning Functions
# Lines 485-1532: Simpro Integration
# Lines 1534-1820: Main Routes (pages)
# Lines 1821-2731: API Endpoints (analyze, quotes, etc.)
# Lines 2732-3936: CAD Designer
# Lines 3937-5502: CRM System (core)
# Lines 5503-6763: CRM Advanced (room assignments, cost centres)
# Lines 6764-7302: Google Integration
# Lines 7303-7802: CRM Integration Endpoints
# Lines 7803-8632: AI Chat & Quote Generation
# Lines 8633-8871: Kanban & File Serving
```

**Why one big file?**: Historical reasons. Was modular at first, then combined for easier deployment. Should be split into:
- `routes/` - Route handlers
- `services/` - Business logic
- `ai/` - AI functions

---

## Security Considerations

### What's Implemented:
- CORS headers
- Content Security Policy
- XSS protection headers
- Authentication required for admin
- Input validation on all create endpoints

### What's Missing:
- Rate limiting (Flask-Limiter exists but not configured)
- SQL injection protection (not using SQL)
- File upload size limits (should add)
- CSRF tokens (should add for forms)

---

## Performance Considerations

### Current Performance:
- AI analysis: 30-90 seconds per floor plan
- CRM operations: <100ms
- File uploads: Limited by PDF size

### Bottlenecks:
1. AI API calls (can't parallelize easily)
2. PDF → image conversion (CPU intensive)
3. JSON file I/O (not cached)

### Optimizations Possible:
1. Cache automation_data.json in memory
2. Use Redis for session data
3. Background task queue for AI analysis
4. CDN for static files

---

## Next Steps / Roadmap

### Short Term:
1. Split app.py into modules
2. Add automated backups
3. Add file cleanup job
4. Improve error messages
5. Add request logging

### Medium Term:
1. Enable database support
2. Add real-time collaboration (WebSockets)
3. Mobile-responsive design
4. Offline mode (PWA)
5. Export to Excel/CSV

### Long Term:
1. Multi-tenant support
2. White-label capabilities
3. API for third-party integrations
4. Mobile app (React Native)
5. AI model fine-tuning

---

## How to Understand This Codebase

### For New Developers:

1. **Start here**: Read this CONTEXT.md
2. **Next**: Look at `templates/` to see the UI
3. **Then**: Read `app.py` route by route
4. **Finally**: Test each module hands-on

### For AI Assistants:

When asked to modify code:
1. Check this CONTEXT.md for architecture
2. Find the relevant section in app.py
3. Test the change
4. Update this file if behavior changes

### Key Files to Know:

| File | Purpose | Size |
|------|---------|------|
| `app.py` | Everything | 8,871 lines |
| `templates/crm.html` | CRM UI | 4,074 lines |
| `templates/cad_designer.html` | CAD UI | 2,349 lines |
| `static/cad-engine.js` | CAD logic | ~1,500 lines |
| `data/automation_data.json` | Pricing config | ~50 lines |

---

## Glossary

- **Floor Plan**: Architectural drawing showing room layout
- **Automation Types**: Categories like lighting, shading, security
- **Tier**: Pricing level (Basic/Premium/Deluxe)
- **Markup**: Annotated floor plan or electrical diagram
- **Takeoffs**: Quantity estimates from plans
- **Cost Centre**: Budget category in a project
- **Room Assignment**: Linking serial number to specific room
- **Session**: Temporary work instance (CAD, analysis, etc.)
- **Symbol**: Icon representing component (light, outlet, etc.)
- **NEC**: National Electrical Code (US building code)

---

## Support & Resources

- **Repository**: https://github.com/caesaralt/lockzone-ai-floorplan
- **Live App**: https://lockzone-ai-floorplan.onrender.com
- **Anthropic Docs**: https://docs.anthropic.com
- **Tavily Docs**: https://tavily.com/docs

---

**This is a living document. Update it when you change the architecture.**
