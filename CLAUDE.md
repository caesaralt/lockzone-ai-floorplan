# CLAUDE.md - AI Assistant Guide for LockZone AI Floor Plan Analyzer

> **Last Updated**: November 2025
> **Repository**: https://github.com/caesaralt/lockzone-ai-floorplan
> **Live App**: https://lockzone-ai-floorplan.onrender.com

This document provides comprehensive guidance for AI assistants (like Claude) working on this codebase. It covers architecture, conventions, workflows, and key implementation details.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture & Tech Stack](#architecture--tech-stack)
3. [Directory Structure](#directory-structure)
4. [Core Components](#core-components)
5. [API Endpoints](#api-endpoints)
6. [AI Capabilities](#ai-capabilities)
7. [Development Workflow](#development-workflow)
8. [Configuration & Environment](#configuration--environment)
9. [Deployment](#deployment)
10. [Code Conventions](#code-conventions)
11. [Common Development Tasks](#common-development-tasks)
12. [Git Branching Strategy](#git-branching-strategy)
13. [Troubleshooting](#troubleshooting)

---

## Project Overview

**LockZone AI Floor Plan Analyzer v2.0** is an intelligent floor plan analysis and quote generation system for home automation installations. The application uses AI vision and web search capabilities to analyze architectural floor plans, automatically place automation components (lighting, security, shading), and generate professional quotes with tiered pricing.

### Key Features

- **AI-Powered Floor Plan Analysis**: Uses Claude AI with vision capabilities to detect rooms, walls, and optimal component placement
- **Multi-Tier Pricing System**: Basic, Premium, and Deluxe tiers with different pricing structures
- **Electrical CAD Designer**: Full-featured electrical planning tool with NEC code compliance
- **Interactive Canvas**: Drag-and-drop symbol placement with real-time quote updates
- **CRM Integration**: Job management, stock tracking, and Simpro API integration
- **Learning System**: AI-powered self-improvement through correction tracking
- **Quote Automation**: Generates annotated floor plans and detailed quote PDFs
- **Web Search Integration**: Real-time lookup of building codes, standards, and best practices

### Business Domain

Home automation and electrical system installation, including:
- Lighting control systems
- Automated shading/blinds
- Security systems (cameras, keypads, access control)
- Climate control integration
- Electrical outlet and switch placement

---

## Architecture & Tech Stack

### Backend

- **Framework**: Flask 3.0.0 (Python web framework)
- **AI Engine**: Anthropic Claude API (claude-sonnet-4-5)
  - Vision capabilities for floor plan analysis
  - Extended thinking (8000-10000 token budgets)
  - Tool use for web search integration
- **Web Search**: Tavily API for real-time information lookup
- **PDF Processing**:
  - PyPDF for PDF reading/writing
  - PyMuPDF (fitz) for advanced PDF operations
  - pdf2image for rasterization
- **Image Processing**: Pillow (PIL) for image manipulation
- **PDF Generation**: ReportLab for quote PDF creation
- **Data Storage**: JSON file-based (database support disabled for stability)
- **Server**: Gunicorn for production deployment

### Frontend

- **Templates**: Jinja2 templating engine
- **UI Framework**: Tailwind CSS 3.x (via CDN)
- **JavaScript**: Vanilla JS with modern ES6+ features
- **Canvas Libraries**:
  - Custom CAD engine for electrical design (`static/cad-engine.js`)
  - Interactive symbol placement system
- **Component Architecture**: Modular HTML templates with embedded JS

### External Services

- **Anthropic API**: AI vision and reasoning
- **Tavily API**: Web search for building codes and standards
- **Simpro API**: Optional CRM integration
- **OAuth2**: For Simpro authentication

### Storage Architecture

Currently using **JSON file storage** for all data (database support temporarily disabled):
- `data/automation_data.json` - Automation catalog, pricing, tiers
- `crm_data/*.json` - Stock inventory and job data
- `learning_data/*.json` - AI learning and correction data
- `mapping_learning/*.json` - Electrical mapping learning data
- `session_data/*.json` - Analysis session data
- `cad_sessions/*.json` - CAD designer sessions

---

## Directory Structure

```
lockzone-ai-floorplan/
├── app.py                          # Main Flask application (6000+ lines)
├── electrical_calculations.py      # NEC code calculations and validations
├── dxf_exporter.py                # DXF file export for CAD integration
├── config_updater.py              # CLI tool for updating pricing config
├── migrate_kanban_to_db.py        # Database migration script
│
├── static/                        # Frontend JavaScript libraries
│   ├── cad-engine.js             # Core CAD drawing engine
│   ├── electrical-symbols.js     # Electrical symbol library
│   ├── measurement-tools.js      # Measurement and scaling tools
│   ├── validation-engine.js      # NEC code validation
│   ├── panel-schedule.js         # Electrical panel schedule generator
│   ├── cable-schedule.js         # Cable and conduit scheduling
│   ├── wire-labeling.js          # Wire labeling system
│   ├── hatching-patterns.js      # CAD hatching patterns
│   ├── schematic-view.js         # Schematic diagram view
│   └── pdf-export.js             # PDF export functionality
│
├── templates/                     # Jinja2 HTML templates
│   ├── index.html                # Main quote automation page
│   ├── crm.html                  # CRM/job management
│   ├── canvas.html               # Interactive symbol canvas
│   ├── mapping.html              # Electrical mapping tool
│   ├── learning.html             # AI learning interface
│   ├── simpro.html               # Simpro integration
│   ├── kanban.html               # Kanban project board
│   ├── board_builder.html        # Board builder utility
│   ├── cad_designer.html         # Electrical CAD designer
│   ├── takeoffs.html             # Material takeoffs
│   └── [various templates]
│
├── data/                          # Configuration and catalog data
│   └── automation_data.json      # Pricing, symbols, tiers
│
├── uploads/                       # Uploaded PDF floor plans
├── outputs/                       # Generated annotated PDFs and quotes
├── ai_mapping/                    # Electrical mapping outputs
├── learning_data/                 # AI learning corrections
├── mapping_learning/              # Electrical mapping learning
├── simpro_config/                 # Simpro API configuration
├── crm_data/                      # CRM stock and jobs
├── session_data/                  # Analysis session cache
├── cad_sessions/                  # CAD designer sessions
│
├── requirements.txt               # Python dependencies
├── runtime.txt                    # Python version (3.11.9)
├── render.yaml                    # Render deployment config
├── Procfile                       # Heroku/Render process config
├── gunicorn_config.py            # Gunicorn server config
├── build.sh                       # Build script
├── deploy.sh                      # Deployment automation script
│
└── [Documentation Files]
    ├── README.md                  # Project readme
    ├── CLAUDE.md                  # This file
    ├── AI_CAPABILITIES.md         # Detailed AI feature documentation
    ├── SIMPLE_INSTRUCTIONS.md     # User deployment guide
    ├── DEPLOY_NOW.md              # Quick deployment instructions
    ├── LEARNING_GUIDE.md          # AI learning system guide
    ├── LEARNING_SYSTEM.md         # Learning system architecture
    ├── KANBAN_DATABASE_SETUP.md   # Database setup guide
    ├── WEB_SEARCH_SETUP.md        # Web search integration guide
    └── FINAL_SUMMARY.md           # Project summary
```

### Important Files to Know

| File | Purpose | When to Modify |
|------|---------|----------------|
| `app.py:685-979` | AI Quote Analysis (`analyze_floorplan_with_ai`) | Improving quote AI logic |
| `app.py:979-1332` | AI Electrical Mapping (`ai_map_floorplan`) | Improving electrical analysis |
| `app.py:2796-2981` | AI Chat Endpoint (`/api/ai-chat`) | Adding chat features |
| `app.py:172-178` | Data Loading (`load_data`) | Changing data structure |
| `templates/index.html` | Main quote UI | UI/UX changes for quotes |
| `templates/mapping.html` | Electrical CAD UI | CAD interface changes |
| `data/automation_data.json` | Pricing & catalog | Adding products/pricing |
| `static/cad-engine.js` | CAD core logic | CAD functionality |
| `electrical_calculations.py` | NEC calculations | Code compliance logic |

---

## Core Components

### 1. Quote Automation System (`/` route)

**File**: `templates/index.html`
**Backend**: `app.py:1485-1489`
**Analysis Function**: `app.py:685-979` (`analyze_floorplan_with_ai`)

**Flow**:
1. User uploads PDF floor plan
2. User selects automation types and tier (Basic/Premium/Deluxe)
3. AI analyzes floor plan with vision + web search
4. System generates annotated floor plan + quote PDF
5. User can refine on interactive canvas

**AI Capabilities**:
- Vision: Detects rooms, walls, doors, windows
- Web Search: Looks up installation standards, typical dimensions
- Extended Thinking: 8000 token reasoning budget
- Agentic Loop: Up to 10 iterations of research

### 2. Electrical Mapping Tool (`/mapping` route)

**File**: `templates/mapping.html`
**Backend**: `app.py:1560-1582`
**Analysis Function**: `app.py:979-1332` (`ai_map_floorplan`)

**Flow**:
1. User uploads electrical floor plan or image
2. AI analyzes with NEC code knowledge
3. Maps outlets, switches, panels, circuits
4. Generates code-compliant markup
5. Provides learning feedback loop

**AI Capabilities**:
- Vision: Detects electrical symbols and components
- Web Search: Looks up NEC codes (210.52, GFCI requirements, etc.)
- Extended Thinking: 8000 token reasoning budget
- Code Compliance: Validates against electrical codes

### 3. Interactive Canvas (`/canvas` route)

**File**: `templates/canvas.html`
**Backend**: `app.py:1497-1512`

**Features**:
- Drag-and-drop symbol placement
- Real-time quote updates
- Symbol customization (product, pricing, images)
- Zoom and pan controls
- PDF export (annotated floor plan + quote)

### 4. CRM System (`/crm` route)

**File**: `templates/crm.html`
**Backend**: `app.py:1489-1493`

**Features**:
- Stock inventory management
- Job tracking and assignment
- Simpro API integration
- Material import from analysis sessions
- AI chat assistant for CRM questions

### 5. Electrical CAD Designer (`/electrical-cad` route)

**File**: `templates/cad_designer.html`
**Backend**: `app.py:2399-2403`
**Engine**: `static/cad-engine.js`

**Features**:
- Full-featured electrical CAD system
- Symbol libraries (outlets, switches, panels)
- Wire routing and labeling
- Panel schedule generation
- Cable schedule creation
- NEC code validation
- PDF/DXF export

### 6. Learning System (`/learning` route)

**File**: `templates/learning.html`
**Backend**: `app.py:1513-1516`

**Features**:
- AI correction tracking
- Learning analytics
- Prompt engineering interface
- Performance metrics
- Context management

---

## API Endpoints

### Quote Analysis

#### `POST /api/analyze`
Analyzes floor plan and generates quote.

**Request**:
```json
{
  "file": "<file upload>",
  "automation_types": ["lighting", "shading", "security"],
  "tier": "Premium"
}
```

**Response**:
```json
{
  "success": true,
  "symbols": [...],
  "total_cost": 15000,
  "annotated_pdf": "/api/download/annotated_12345.pdf",
  "quote_pdf": "/api/download/quote_12345.pdf"
}
```

**Implementation**: `app.py:1582-1632`

### Data Management

#### `GET /api/data`
Returns current automation catalog, tiers, and pricing.

**Response**:
```json
{
  "automation_types": {...},
  "tiers": {...},
  "labor_rate": 85,
  "markup_percentage": 35
}
```

#### `POST /api/data`
Updates automation catalog and pricing (deep merge with defaults).

**Request**: Full or partial automation_data.json structure

**Implementation**: `app.py` (data loading/saving functions)

### AI Mapping

#### `POST /api/ai-mapping/analyze`
Analyzes electrical floor plan with AI.

**Request**:
```json
{
  "file": "<file upload>",
  "format": "pdf"
}
```

**Response**:
```json
{
  "success": true,
  "mapping": {...},
  "marked_up_image": "base64...",
  "session_id": "uuid"
}
```

**Implementation**: `app.py:1582-1632`

#### `POST /api/ai-mapping/save-correction`
Saves user corrections for learning.

**Implementation**: `app.py:1632-1677`

### AI Chat

#### `POST /api/ai-chat`
General-purpose AI chat with vision and web search.

**Request**:
```json
{
  "message": "What are NEC requirements for kitchen outlets?",
  "image": "base64..." // optional
}
```

**Response**:
```json
{
  "response": "According to NEC 210.52...",
  "searches_performed": 2
}
```

**Implementation**: `app.py:2796-2981`

### CRM Endpoints

- `GET /api/crm/stock` - Get stock inventory
- `POST /api/crm/stock/add` - Add stock item
- `GET /api/crm/jobs` - Get all jobs
- `POST /api/crm/jobs/<job_id>/assign-item` - Assign item to job

### Simpro Integration

#### `POST /api/simpro/import/<data_type>`
Imports data from Simpro API (customers, sites, catalog).

**Parameters**: `data_type` ∈ {`customers`, `sites`, `catalog`, `costcentres`}

**Implementation**: `app.py:472-536` (`import_all_simpro_data`)

### File Downloads

#### `GET /api/download/<filename>`
Downloads generated PDFs and images.

**Implementation**: `app.py:2367-2399`

---

## AI Capabilities

The application uses **Anthropic Claude API** with advanced capabilities across three main AI functions. See `AI_CAPABILITIES.md` for detailed documentation.

### 1. Quote Tool AI (`analyze_floorplan_with_ai`)

**Location**: `app.py:685-979`

**Capabilities**:
- Vision analysis of floor plans
- Web search for installation standards
- 8000 token extended thinking
- Agentic loop (up to 10 iterations)
- Automatic symbol placement

**What it searches**:
- Home automation placement standards
- Typical room dimensions
- Security component placement
- Professional installer best practices

### 2. Electrical Mapping AI (`ai_map_floorplan`)

**Location**: `app.py:979-1332`

**Capabilities**:
- Vision analysis of electrical plans
- Web search for NEC codes
- 8000 token extended thinking
- Agentic loop (up to 10 iterations)
- Code-compliant component mapping

**What it searches**:
- NEC electrical codes (210.52, GFCI, arc-fault)
- Outlet spacing requirements
- Switch placement codes
- Panel clearance requirements
- Electrical symbol standards

### 3. AI Chat (All Pages)

**Location**: `app.py:2796-2981`

**Capabilities**:
- Vision analysis of attached images
- Web search for any information
- 10000 token extended thinking (highest!)
- Agentic loop (up to 8 iterations)
- Agent mode (can take actions in Learning Mode)

**Available on**: CRM, Canvas, Learning, Mapping, Quote Tool, AI Mapping

### AI Architecture Pattern

All AI functions follow this pattern:

```python
def ai_function(input_data):
    # 1. Prepare image if present
    image_data = prepare_image(input_data)

    # 2. Initial message with vision
    messages = [{
        "role": "user",
        "content": [
            {"type": "image", "source": {"type": "base64", "data": image_data}},
            {"type": "text", "text": "Analyze this floor plan..."}
        ]
    }]

    # 3. Agentic loop with web search
    max_iterations = 10
    for iteration in range(max_iterations):
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            messages=messages,
            tools=[web_search_tool],
            thinking={"type": "enabled", "budget_tokens": 8000},
            max_tokens=4000
        )

        # 4. Handle tool use (web search)
        if response.stop_reason == "tool_use":
            for tool_use in response.content:
                if tool_use.type == "tool_use":
                    search_results = tavily_search(tool_use.input["query"])
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": [{"type": "tool_result", ...}]})
            continue

        # 5. Final response
        return extract_analysis(response)
```

### Web Search Integration

**Provider**: Tavily API
**Free Tier**: 1,000 searches/month
**Expected Usage**: ~780 searches/month

Search queries are logged:
```bash
🔍 AI searching: NEC code outlet spacing requirements residential
🔍 AI searching electrical codes: light switch height ADA code
```

### Environment Variables for AI

```bash
ANTHROPIC_API_KEY=sk-ant-...    # Required for all AI features
TAVILY_API_KEY=tvly-...         # Required for web search
```

---

## Development Workflow

### Setting Up Development Environment

1. **Clone the repository**:
   ```bash
   git clone https://github.com/caesaralt/lockzone-ai-floorplan.git
   cd lockzone-ai-floorplan
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   # Create .env file
   echo "ANTHROPIC_API_KEY=your-key-here" > .env
   echo "TAVILY_API_KEY=your-key-here" >> .env
   echo "SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')" >> .env
   ```

5. **Create necessary directories**:
   ```bash
   mkdir -p uploads outputs data learning_data ai_mapping \
            mapping_learning simpro_config crm_data session_data cad_sessions
   ```

6. **Run development server**:
   ```bash
   python3 app.py
   # Or with auto-reload:
   FLASK_ENV=development python3 app.py
   ```

7. **Access the application**:
   ```
   http://localhost:5000
   ```

### Development Tools

#### Config Updater
Update pricing and configuration:
```bash
python3 config_updater.py
```

#### Database Migration
Migrate from JSON to database (when enabled):
```bash
python3 migrate_kanban_to_db.py
```

### Testing AI Features

1. **Test quote analysis**:
   - Upload a sample floor plan PDF
   - Select automation types
   - Choose tier
   - Check console for search queries
   - Verify symbol placement accuracy

2. **Test electrical mapping**:
   - Upload electrical plan
   - Review NEC code compliance
   - Check search queries for code lookups
   - Verify component placement

3. **Test AI chat**:
   - Ask technical questions
   - Attach images for analysis
   - Verify web search integration
   - Check response accuracy

### Debugging

**Enable debug mode**:
```python
# In app.py, at bottom:
if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

**Check logs**:
- Render logs: https://dashboard.render.com
- Local logs: Console output

**Common debug tasks**:
- Print AI responses: Add `print(response)` in AI functions
- Trace search queries: Look for `🔍 AI searching:` in logs
- Inspect session data: Check `session_data/*.json`
- Review corrections: Check `learning_data/*.json`

---

## Configuration & Environment

### Environment Variables

| Variable | Required | Purpose | Example |
|----------|----------|---------|---------|
| `ANTHROPIC_API_KEY` | Yes | Claude AI access | `sk-ant-...` |
| `TAVILY_API_KEY` | Optional | Web search | `tvly-...` |
| `SECRET_KEY` | Yes | Flask session security | Random hex string |
| `SIMPRO_API_KEY` | Optional | Simpro integration | From Simpro |
| `SIMPRO_API_URL` | Optional | Simpro endpoint | `https://api.simpro.com` |
| `SIMPRO_TENANT_ID` | Optional | Simpro tenant | Company ID |

### Automation Data Configuration

**File**: `data/automation_data.json`

**Structure**:
```json
{
  "automation_types": {
    "lighting": {
      "name": "Lighting Control",
      "symbols": {
        "wall_switch": "💡",
        "dimmer": "🎚️"
      },
      "tiers": {
        "Basic": {
          "unit_price": 150,
          "labor_hours": 2,
          "description": "Basic lighting control"
        },
        "Premium": {
          "unit_price": 250,
          "labor_hours": 3,
          "description": "Advanced lighting"
        },
        "Deluxe": {
          "unit_price": 400,
          "labor_hours": 4,
          "description": "Premium system"
        }
      }
    }
  },
  "labor_rate": 85,
  "markup_percentage": 35
}
```

### Updating Configuration

**Via API**:
```bash
curl -X POST http://localhost:5000/api/data \
  -H "Content-Type: application/json" \
  -d @new_config.json
```

**Via CLI tool**:
```bash
python3 config_updater.py
```

**Direct edit**:
Edit `data/automation_data.json` and restart server.

---

## Deployment

### Render Deployment (Recommended)

The app is configured for **Render.com** deployment.

**Quick Deploy**:
```bash
chmod +x deploy.sh
./deploy.sh
```

**Manual Deploy**:
1. Ensure all changes are committed
2. Push to GitHub: `git push origin main`
3. Render auto-deploys from `main` branch
4. Monitor: https://dashboard.render.com

**Configuration**: `render.yaml`
```yaml
services:
  - type: web
    name: lockzone-ai-floorplan
    runtime: python
    buildCommand: "pip install --upgrade pip && pip install -r requirements.txt"
    startCommand: "gunicorn app:app"
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.9
      - key: WEB_CONCURRENCY
        value: 2
      - key: ANTHROPIC_API_KEY
        sync: false
```

**Environment Variables on Render**:
1. Go to Dashboard > Service > Environment
2. Add:
   - `ANTHROPIC_API_KEY`
   - `TAVILY_API_KEY`
   - `SECRET_KEY`
3. Save and redeploy

### Build Process

**Build command**: `pip install --upgrade pip && pip install -r requirements.txt`

**Build script** (`build.sh`):
```bash
#!/bin/bash
# System dependencies (if needed)
# Currently using pure Python packages
```

### Server Configuration

**Gunicorn** (`gunicorn_config.py`):
```python
bind = "0.0.0.0:5000"
workers = 2
worker_class = "sync"
timeout = 120
```

**Procfile** (Heroku-compatible):
```
web: gunicorn app:app
```

### Post-Deployment Checklist

- [ ] App accessible at URL
- [ ] Can upload PDF files
- [ ] Quote generation works
- [ ] AI analysis returns results
- [ ] Web search queries visible in logs
- [ ] PDFs download correctly
- [ ] CRM pages load
- [ ] Electrical CAD loads

---

## Code Conventions

### Python Style

- **PEP 8**: Follow Python style guide
- **Line length**: ~100 characters (flexible)
- **Indentation**: 4 spaces
- **Naming**:
  - Functions: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_CASE`
  - Private: `_leading_underscore`

### Function Documentation

```python
def analyze_floorplan_with_ai(pdf_path):
    """
    Analyzes floor plan using Claude AI with vision and web search.

    Args:
        pdf_path (str): Path to uploaded PDF file

    Returns:
        dict: Analysis results with symbols and placements
        {
            'symbols': [...],
            'total_components': 25,
            'confidence': 0.85,
            'searches_performed': 3
        }
    """
```

### Error Handling

**Always use try-except** for external calls:

```python
try:
    response = anthropic_client.messages.create(...)
except Exception as e:
    print(f"❌ AI Error: {str(e)}")
    traceback.print_exc()
    return {"error": "AI analysis failed", "details": str(e)}
```

### JSON File Operations

**Use helper functions**:

```python
# Loading
data = load_json_file('data/config.json', default={})

# Saving
save_json_file('data/config.json', data)
```

### Flask Route Patterns

```python
@app.route('/api/resource', methods=['POST'])
def create_resource():
    try:
        data = request.get_json()
        result = process_data(data)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
```

### Frontend JavaScript

- **Modern ES6+**: Use arrow functions, const/let, template literals
- **No jQuery**: Vanilla JavaScript preferred
- **Fetch API**: For AJAX requests
- **Async/Await**: For asynchronous operations

```javascript
async function analyzeFloorplan() {
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        // Handle response
    } catch (error) {
        console.error('Analysis failed:', error);
    }
}
```

### Tailwind CSS Classes

**Consistent patterns**:
```html
<!-- Buttons -->
<button class="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg">

<!-- Cards -->
<div class="bg-white rounded-lg shadow-md p-6">

<!-- Forms -->
<input class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
```

---

## Common Development Tasks

### Adding a New Automation Type

1. **Update `data/automation_data.json`**:
   ```json
   {
     "automation_types": {
       "climate": {
         "name": "Climate Control",
         "symbols": {"thermostat": "🌡️"},
         "tiers": {
           "Basic": {"unit_price": 200, "labor_hours": 2},
           "Premium": {"unit_price": 350, "labor_hours": 3},
           "Deluxe": {"unit_price": 600, "labor_hours": 4}
         }
       }
     }
   }
   ```

2. **Update UI** (`templates/index.html`):
   ```html
   <input type="checkbox" name="automation_types" value="climate">
   Climate Control
   ```

3. **Test**: Upload floor plan with new type selected

### Adding a New API Endpoint

1. **Define route** in `app.py`:
   ```python
   @app.route('/api/my-endpoint', methods=['POST'])
   def my_endpoint():
       data = request.get_json()
       result = process(data)
       return jsonify({"success": True, "result": result})
   ```

2. **Add error handling**:
   ```python
   try:
       # Logic here
   except Exception as e:
       return jsonify({"success": False, "error": str(e)}), 400
   ```

3. **Document** in this file under API Endpoints

### Improving AI Prompts

**Quote Analysis** (`app.py:685-979`):
```python
# Find the prompt construction around line 700-750
prompt = f"""
Analyze this floor plan and place {', '.join(automation_types)} components.

IMPORTANT GUIDELINES:
- Your new guideline here
- Another important point
"""
```

**Electrical Mapping** (`app.py:979-1332`):
```python
# Find prompt around line 1000-1050
prompt = """
Analyze this electrical plan for NEC compliance.
- Your new NEC requirement
"""
```

### Adding Web Search Capabilities

Already integrated! AI automatically searches when uncertain.

**To add new search patterns**:
```python
# In AI prompt, add examples:
"""
If uncertain about:
- Building codes: Search "NEC code [specific requirement]"
- Standards: Search "[component] installation standard residential"
- Your new pattern: Search "..."
"""
```

### Creating a New Page

1. **Create template** (`templates/mypage.html`):
   ```html
   <!DOCTYPE html>
   <html>
   <head>
       <title>My Page</title>
       <script src="https://cdn.tailwindcss.com"></script>
   </head>
   <body class="bg-gray-100">
       <!-- Content -->
   </body>
   </html>
   ```

2. **Add route** (`app.py`):
   ```python
   @app.route('/mypage')
   def mypage():
       return render_template('mypage.html')
   ```

3. **Add navigation** (update other templates):
   ```html
   <a href="/mypage">My Page</a>
   ```

### Modifying Electrical CAD

**Core engine**: `static/cad-engine.js`

**Adding symbols**: `static/electrical-symbols.js`
```javascript
const newSymbol = {
    type: 'my-component',
    label: 'My Component',
    draw: (ctx, x, y) => {
        // Canvas drawing code
    }
};
```

**Adding validation**: `static/validation-engine.js`
```javascript
function validateMyRule(drawing) {
    // NEC compliance check
}
```

---

## Git Branching Strategy

### Branch Naming Convention

The project uses a **feature branch** workflow with specific naming:

**AI Assistant Branches** (for Claude Code sessions):
```
claude/claude-md-<session-id>
```
Example: `claude/claude-md-mi2bxhddfzuih0wv-01Un3iMVyesRbyvKdkXhtWye`

**Feature Branches**:
```
feature/<feature-name>
```

**Bug Fix Branches**:
```
fix/<bug-description>
```

**Main Branches**:
- `main` - Production code, auto-deploys to Render
- `develop` - Development integration (if used)

### Workflow

1. **Start work**: Create branch from `main`
   ```bash
   git checkout -b claude/my-feature-branch
   ```

2. **Make changes**: Commit frequently with clear messages
   ```bash
   git add .
   git commit -m "Add: Comprehensive CLAUDE.md documentation"
   ```

3. **Push changes**: Push to origin
   ```bash
   git push -u origin claude/my-feature-branch
   ```

4. **Create PR**: Merge into `main` when ready
   ```bash
   # Via GitHub UI or gh CLI
   gh pr create --title "Add CLAUDE.md" --body "Comprehensive AI assistant guide"
   ```

5. **Deploy**: Merge to `main` triggers auto-deployment

### Commit Message Guidelines

**Format**: `<Type>: <Brief description>`

**Types**:
- `Add:` - New feature or file
- `Update:` - Modify existing feature
- `Fix:` - Bug fix
- `Refactor:` - Code restructuring
- `Docs:` - Documentation changes
- `Style:` - Formatting, no code change
- `Test:` - Add or update tests
- `Chore:` - Maintenance tasks

**Examples**:
```bash
git commit -m "Add: CLAUDE.md comprehensive guide"
git commit -m "Fix: AI analysis timeout on large PDFs"
git commit -m "Update: Increase thinking budget to 10000 tokens"
git commit -m "Docs: Update API endpoint documentation"
```

### Important Git Notes

**Never commit**:
- `.env` files (API keys)
- `uploads/*.pdf` (user uploads)
- `outputs/*.pdf` (generated files)
- `__pycache__/` (Python cache)
- Virtual environments (`venv/`)

**Always commit**:
- Code changes
- Template updates
- Configuration changes (data/automation_data.json)
- Documentation updates
- Dependency updates (requirements.txt)

---

## Troubleshooting

### AI Analysis Issues

**Problem**: AI returns empty symbols
- **Check**: ANTHROPIC_API_KEY is set
- **Check**: PDF converted to image successfully
- **Check**: Logs for AI errors
- **Solution**: Verify API key, check PDF format

**Problem**: No web searches performed
- **Check**: TAVILY_API_KEY is set
- **Check**: Search quota (1000/month)
- **Solution**: Add API key or upgrade plan

**Problem**: Low accuracy on floor plan
- **Check**: PDF quality (vector vs raster)
- **Check**: Wall clarity in image
- **Solution**: Use higher quality CAD exports

### Deployment Issues

**Problem**: Build fails on Render
- **Check**: requirements.txt has all dependencies
- **Check**: Python version (3.11.9)
- **Solution**: Review build logs, fix dependencies

**Problem**: App crashes after deploy
- **Check**: Environment variables set on Render
- **Check**: Memory limits
- **Solution**: Add ANTHROPIC_API_KEY, increase resources

**Problem**: Static files not loading
- **Check**: Static folder exists
- **Check**: Template references correct paths
- **Solution**: Ensure `static/` folder committed

### Data Issues

**Problem**: Pricing not updating
- **Check**: `data/automation_data.json` format
- **Check**: API endpoint called correctly
- **Solution**: Use config_updater.py or validate JSON

**Problem**: Sessions not persisting
- **Check**: `session_data/` folder exists
- **Check**: File permissions
- **Solution**: Create folder, check write access

**Problem**: CRM data lost
- **Check**: `crm_data/` folder backed up
- **Check**: JSON file corruption
- **Solution**: Restore from backup, validate JSON

### Performance Issues

**Problem**: Slow AI analysis
- **Expected**: 30-90 seconds for complex floor plans
- **Check**: PDF size (100MB limit)
- **Solution**: Optimize PDF, reduce page count

**Problem**: Timeout errors
- **Check**: Gunicorn timeout (120s)
- **Check**: Request size
- **Solution**: Increase timeout, optimize processing

---

## Additional Resources

### Internal Documentation

- **AI_CAPABILITIES.md**: Detailed AI feature documentation
- **LEARNING_GUIDE.md**: AI learning system guide
- **WEB_SEARCH_SETUP.md**: Web search integration guide
- **SIMPLE_INSTRUCTIONS.md**: User deployment guide

### External Links

- **Anthropic Claude API**: https://docs.anthropic.com
- **Tavily Search API**: https://tavily.com/docs
- **Flask Documentation**: https://flask.palletsprojects.com
- **Tailwind CSS**: https://tailwindcss.com/docs
- **Render Deployment**: https://render.com/docs

### Code References

When referencing code locations in discussions or issues:

**Format**: `file_path:line_number`

**Examples**:
- Quote AI analysis: `app.py:685-979`
- Electrical mapping: `app.py:979-1332`
- AI chat endpoint: `app.py:2796-2981`
- Main route: `app.py:1485-1489`

---

## Contact & Support

**Repository**: https://github.com/caesaralt/lockzone-ai-floorplan
**Live App**: https://lockzone-ai-floorplan.onrender.com
**Render Dashboard**: https://dashboard.render.com

For AI assistants: Use this document as primary reference for all development tasks. Always commit changes with clear messages and test thoroughly before deployment.

---

**Document Version**: 1.0
**Last Updated**: November 2025
**Maintained For**: AI assistants working on LockZone AI Floor Plan Analyzer
