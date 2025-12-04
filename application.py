"""
Lockzone AI Floorplan Application
Million-dollar quality electrical automation platform with AI-powered features

MODULAR ARCHITECTURE:
This application uses a modular structure with Flask Blueprints.

Extracted Modules (in app/ package):
- app/api/pages.py: Page rendering routes (/, /apps, /crm, /quotes, etc.)
- app/api/auth_routes.py: Authentication (/login, /api/auth/*)
- app/api/admin.py: Admin panel (/admin, /api/admin/*)
- app/utils/: Shared utilities (helpers, image_utils, ai_tools)

Existing Services (in services/ directory):
- services/crm_repository.py: CRM data access
- services/ai_chat_service.py: AI chat functionality
- services/notification_service.py: Notifications
- services/scheduler.py: Background jobs
- etc.

Routes still in this file (to be extracted incrementally):
- /api/crm/*: CRM API routes
- /api/cad/*: Electrical CAD routes
- /api/board-builder/*: Loxone board builder
- /api/ai-mapping/*: AI mapping routes
- /api/simpro/*: Simpro integration
- /api/canvas/*: Canvas editor routes
- /api/analyze, /api/generate_quote: Quote automation

Data Layer:
- crm_data_layer.py / crm_db_layer.py: CRM data operations
- database/models.py: SQLAlchemy ORM models
"""
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, make_response, send_from_directory
from werkzeug.utils import secure_filename
import os
import json
import copy
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np
import uuid
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from PIL import Image, ImageDraw, ImageFont
import fitz  # PyMuPDF
import io
import traceback
import base64
import requests

# Base directory for file operations
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Authentication module
import auth

# CRM Integration module
import crm_integration

from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient
import logging

# CRM Data Layer - robust data operations
# Try database layer first, fall back to JSON if not available
import os as _os
if _os.environ.get('DATABASE_URL'):
    try:
        from crm_db_layer import CRMDatabaseLayer, get_crm_db_layer
        CRM_USE_DATABASE = True
        logging.info("DATABASE_URL detected - will use PostgreSQL for CRM data")
    except ImportError:
        from crm_data_layer import CRMDataLayer, get_crm_data_layer
        CRM_USE_DATABASE = False
        logging.warning("Database modules not available, using JSON file storage")
else:
    from crm_data_layer import CRMDataLayer, get_crm_data_layer
    CRM_USE_DATABASE = False
    logging.info("DATABASE_URL not set - using JSON file storage for CRM data")

# Import new infrastructure
from app_init import create_app, get_ai_service
from validators import (
    validate_quote_request,
    validate_ai_chat_request,
    validate_mapping_request,
    validate_image_upload,
    validate_document_upload,
    sanitize_string,
    format_validation_error,
    format_success_response
)

# Import modular utilities
from app.utils import (
    load_json_file,
    save_json_file,
    pdf_to_image_base64,
    image_to_base64,
    web_search,
    execute_tool,
    SEARCH_TOOL_SCHEMA,
)

# Try to import anthropic, but don't fail if not available
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logging.warning("anthropic package not installed. AI features will use fallback mode.")

# Try to import tavily for web search
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    logging.warning("tavily-python package not installed. Web search features will be limited.")

# Initialize Flask app with new infrastructure
app = create_app()
logger = logging.getLogger(__name__)

# Context processor to make user permissions available in all templates
@app.context_processor
def inject_user_permissions():
    """Make user permissions available in all templates"""
    return {
        'user_permissions': session.get('user_permissions', []),
        'crm_permissions': session.get('crm_permissions', []),
        'user_name': session.get('user_name', ''),
        'user_display_name': session.get('user_display_name', ''),
        'is_authenticated': auth.is_authenticated(),
        'has_permission': auth.has_permission
    }

# ============================================================================
# BLUEPRINT REGISTRATION
# ============================================================================
# Note: Blueprints are registered AFTER all app functions are defined
# See end of file for actual registration call

# Database configuration
USE_DATABASE = CRM_USE_DATABASE

if CRM_USE_DATABASE:
    logger.info("✅ Using PostgreSQL storage for CRM/operations data (DATABASE_URL detected)")
else:
    logger.info("📁 Using JSON file storage for all data")

# Note: KanbanTask model has been moved to database/models.py
# The operations board uses JSON files for now but will be migrated to PostgreSQL

DATA_FILE = os.path.join(app.config['DATA_FOLDER'], 'automation_data.json')
LEARNING_INDEX_FILE = os.path.join(app.config['LEARNING_FOLDER'], 'learning_index.json')
SIMPRO_CONFIG_FILE = os.path.join(app.config['SIMPRO_CONFIG_FOLDER'], 'simpro_config.json')
MAPPING_LEARNING_INDEX = os.path.join(app.config['MAPPING_LEARNING_FOLDER'], 'learning_index.json')

# CRM Data Files
CUSTOMERS_FILE = os.path.join(app.config['CRM_DATA_FOLDER'], 'customers.json')
PROJECTS_FILE = os.path.join(app.config['CRM_DATA_FOLDER'], 'projects.json')
COMMUNICATIONS_FILE = os.path.join(app.config['CRM_DATA_FOLDER'], 'communications.json')
CALENDAR_FILE = os.path.join(app.config['CRM_DATA_FOLDER'], 'calendar.json')
TECHNICIANS_FILE = os.path.join(app.config['CRM_DATA_FOLDER'], 'technicians.json')
INVENTORY_FILE = os.path.join(app.config['CRM_DATA_FOLDER'], 'inventory.json')
SUPPLIERS_FILE = os.path.join(app.config['CRM_DATA_FOLDER'], 'suppliers.json')
PRICE_CLASSES_FILE = os.path.join(app.config['CRM_DATA_FOLDER'], 'price_classes.json')
INTEGRATIONS_FILE = os.path.join(app.config['CRM_DATA_FOLDER'], 'integrations.json')
QUOTES_FILE = os.path.join(app.config['CRM_DATA_FOLDER'], 'quotes.json')
STOCK_FILE = os.path.join(app.config['CRM_DATA_FOLDER'], 'stock.json')

# Initialize CRM Data Layer for robust data operations
if CRM_USE_DATABASE:
    crm_data = get_crm_db_layer()
    logger.info("✅ CRM Database Layer initialized successfully")
else:
    crm_data = get_crm_data_layer(app.config['CRM_DATA_FOLDER'])
    logger.info("📁 CRM JSON Data Layer initialized")

DEFAULT_DATA = {
    "automation_types": {
        "lighting": {
            "name": "Lighting Control",
            "symbols": ["💡"],
            "base_cost_per_unit": {"basic": 150.0, "premium": 250.0, "deluxe": 400.0},
            "labor_hours": {"basic": 2.0, "premium": 3.0, "deluxe": 4.0}
        },
        "shading": {
            "name": "Shading Control",
            "symbols": ["🪟"],
            "base_cost_per_unit": {"basic": 300.0, "premium": 500.0, "deluxe": 800.0},
            "labor_hours": {"basic": 3.0, "premium": 4.0, "deluxe": 5.0}
        },
        "security_access": {
            "name": "Security & Access",
            "symbols": ["🔐"],
            "base_cost_per_unit": {"basic": 500.0, "premium": 900.0, "deluxe": 1500.0},
            "labor_hours": {"basic": 4.5, "premium": 6.0, "deluxe": 8.0}
        },
        "climate": {
            "name": "Climate Control",
            "symbols": ["🌡"],
            "base_cost_per_unit": {"basic": 400.0, "premium": 700.0, "deluxe": 1200.0},
            "labor_hours": {"basic": 5.0, "premium": 7.0, "deluxe": 9.0}
        },
        "audio": {
            "name": "Audio System",
            "symbols": ["🔊"],
            "base_cost_per_unit": {"basic": 350.0, "premium": 600.0, "deluxe": 1000.0},
            "labor_hours": {"basic": 3.5, "premium": 5.0, "deluxe": 7.0}
        }
    },
    "labor_rate": 75.0,
    "markup_percentage": 20.0,
    "company_info": {
        "name": "Integratd living",
        "phone": "+61 XXX XXX XXX",
        "email": "info@integratdliving.com.au",
        "address": "Sydney, Australia"
    }
}

# ============================================================================
# DATA MANAGEMENT FUNCTIONS
# ============================================================================

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return copy.deepcopy(DEFAULT_DATA)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load_learning_index():
    """Load the learning index that tracks all training examples"""
    if os.path.exists(LEARNING_INDEX_FILE):
        with open(LEARNING_INDEX_FILE, 'r') as f:
            return json.load(f)
    return {"examples": [], "last_updated": None}

def save_learning_index(index):
    """Save the learning index"""
    index['last_updated'] = datetime.now().isoformat()
    with open(LEARNING_INDEX_FILE, 'w') as f:
        json.dump(index, f, indent=2)

def get_learning_context():
    """Get accumulated learning examples to include in AI prompts - Enhanced for extended thinking"""
    index = load_learning_index()
    examples = index.get('examples', [])

    if not examples:
        return ""

    context = "\n\n═══════════════════════════════════════════════════════════\n"
    context += "LEARNING DATABASE - Apply These Verified Examples\n"
    context += "═══════════════════════════════════════════════════════════\n\n"
    context += "You have access to verified training examples. Use your extended thinking to:\n"
    context += "1. Identify patterns across these examples\n"
    context += "2. Apply learned symbol placements and standards\n"
    context += "3. Follow custom markup requirements\n"
    context += "4. Adapt counting methods based on past corrections\n\n"

    # Group examples by type
    symbol_examples = []
    correction_examples = []
    instruction_examples = []

    for example in examples[-20:]:  # Last 20 examples
        if example.get('type') == 'instruction':
            instruction_examples.append(example)
        elif example.get('corrections'):
            correction_examples.append(example)
        else:
            symbol_examples.append(example)

    # Add custom symbol standards
    if symbol_examples:
        context += "📐 CUSTOM SYMBOL STANDARDS:\n"
        context += "─" * 60 + "\n"
        for ex in symbol_examples[-5:]:  # Last 5 symbol examples
            context += f"\n▸ Example from {ex.get('timestamp', 'N/A')[:10]}:\n"
            if ex.get('notes'):
                context += f"  Standard: {ex['notes']}\n"
            if ex.get('symbol_definitions'):
                context += f"  Symbols: {json.dumps(ex['symbol_definitions'], indent=4)}\n"
        context += "\n"

    # Add correction patterns
    if correction_examples:
        context += "🔧 CORRECTION PATTERNS:\n"
        context += "─" * 60 + "\n"
        for ex in correction_examples[-5:]:
            context += f"\n▸ Correction from {ex.get('timestamp', 'N/A')[:10]}:\n"
            if ex.get('notes'):
                context += f"  Issue: {ex['notes']}\n"
            corrections = ex.get('corrections', {})
            if isinstance(corrections, dict):
                if corrections.get('missed_components'):
                    context += f"  ⚠ Commonly missed: {corrections['missed_components']}\n"
                if corrections.get('incorrect_counts'):
                    context += f"  ⚠ Count errors: {corrections['incorrect_counts']}\n"
        context += "\n"

    # Add natural language instructions
    if instruction_examples:
        context += "📝 CUSTOM INSTRUCTIONS:\n"
        context += "─" * 60 + "\n"
        for ex in instruction_examples[-10:]:  # Last 10 instructions
            if ex.get('instruction'):
                context += f"  • {ex['instruction']}\n"
        context += "\n"

    context += "═" * 60 + "\n"
    context += "APPLY ALL LEARNINGS ABOVE TO YOUR ANALYSIS\n"
    context += "Use your reasoning to understand patterns and apply them consistently.\n"
    context += "═" * 60 + "\n\n"

    return context

def load_mapping_learning_index():
    """Load mapping-specific learning index"""
    if os.path.exists(MAPPING_LEARNING_INDEX):
        with open(MAPPING_LEARNING_INDEX, 'r') as f:
            return json.load(f)
    return {
        "examples": [],
        "stats": {
            "total_corrections": 0,
            "avg_accuracy": 0,
            "improvement_rate": 0
        },
        "last_updated": None
    }

def save_mapping_learning_index(index):
    """Save mapping learning index"""
    index['last_updated'] = datetime.now().isoformat()
    with open(MAPPING_LEARNING_INDEX, 'w') as f:
        json.dump(index, f, indent=2)

def get_mapping_learning_context():
    """Get mapping learning examples for AI context"""
    index = load_mapping_learning_index()
    examples = index.get('examples', [])
    
    # Get top rated examples (score >= 4)
    top_examples = [e for e in examples if e.get('rating', 0) >= 4][-15:]
    
    if not top_examples:
        return ""
    
    context = "\n\nLEARNING FROM PAST CORRECTIONS:\n"
    context += "Use these verified examples to improve accuracy:\n\n"
    
    for ex in top_examples:
        context += f"Example {ex.get('id', 'unknown')}:\n"
        context += f"Original prediction accuracy: {ex.get('rating', 0)}/5\n"
        
        if 'corrections' in ex:
            corrections = ex['corrections']
            if corrections.get('components_added'):
                context += f"- Missing components that should be detected: {len(corrections['components_added'])} items\n"
                for comp in corrections['components_added'][:3]:
                    context += f"  * {comp.get('type', 'unknown')} at {comp.get('room', 'unknown location')}\n"
            
            if corrections.get('connections_added'):
                context += f"- Missing connections: {len(corrections['connections_added'])} connections\n"
            
            if corrections.get('feedback'):
                context += f"- User feedback: {corrections['feedback']}\n"
        
        context += "\n"
    
    context += "Apply these learnings to the current analysis.\n\n"
    return context

def load_simpro_config():
    """Load Simpro configuration"""
    if os.path.exists(SIMPRO_CONFIG_FILE):
        with open(SIMPRO_CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        "connected": False,
        "base_url": "",
        "company_id": "0",
        "client_id": "",
        "client_secret": "",
        "access_token": None,
        "refresh_token": None,
        "token_expires_at": None
    }

def save_simpro_config(config):
    """Save Simpro configuration"""
    with open(SIMPRO_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# load_json_file and save_json_file moved to app/utils/helpers.py
# Imported at top of file from app.utils

# ============================================================================
# SIMPRO BULK IMPORT HELPERS
# ============================================================================

def make_simpro_api_request(endpoint, method='GET', params=None, data=None):
    """Make authenticated Simpro API request"""
    config = load_simpro_config()
    if not config.get('connected') or not config.get('access_token'):
        return {'error': 'Not connected to Simpro'}
    
    # Build URL - ensure trailing slash for collections
    if not endpoint.endswith('/') and method == 'GET':
        endpoint = endpoint + '/'
    
    url = f"{config['base_url']}/api/v1.0/companies/{config['company_id']}{endpoint}"
    headers = {
        'Authorization': f"Bearer {config['access_token']}",
        'Content-Type': 'application/json'
    }
    
    print(f"  📡 {method} {url}")
    if params:
        print(f"     Params: {params}")
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, params=params, timeout=60)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data, timeout=60)
        else:
            return {'error': f'Unsupported method: {method}'}
        
        # Log response status
        print(f"  📥 Status: {response.status_code}")
        
        # Check for errors
        if response.status_code == 404:
            return {'error': f'404 Not Found - endpoint may not exist: {endpoint}'}
        elif response.status_code == 422:
            try:
                error_data = response.json()
                return {'error': f'422 Unprocessable - {error_data}'}
            except:
                return {'error': f'422 Unprocessable Entity - check parameters'}
        elif response.status_code >= 400:
            return {'error': f'{response.status_code} {response.reason}'}
        
        response.raise_for_status()
        
        # Parse response
        result = response.json()
        return result
    
    except requests.exceptions.HTTPError as e:
        error_msg = f'{e.response.status_code} {e.response.reason}'
        try:
            error_detail = e.response.json()
            if 'errors' in error_detail:
                error_msg += f": {error_detail['errors']}"
        except:
            pass
        print(f"  ❌ HTTP Error: {error_msg}")
        return {'error': error_msg}
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return {'error': str(e)}

def categorize_with_ai(item, item_type):
    """Categorize with AI or fallback"""
    if not ANTHROPIC_AVAILABLE:
        name = str(item.get('Name', '')).lower()
        if any(w in name for w in ['light', 'led']):
            return {'automation_type': 'lighting', 'tier': 'basic', 'notes': 'Keyword'}
        elif any(w in name for w in ['blind', 'shade']):
            return {'automation_type': 'shading', 'tier': 'basic', 'notes': 'Keyword'}
        elif any(w in name for w in ['camera', 'lock']):
            return {'automation_type': 'security_access', 'tier': 'basic', 'notes': 'Keyword'}
        elif any(w in name for w in ['hvac', 'climate']):
            return {'automation_type': 'climate', 'tier': 'basic', 'notes': 'Keyword'}
        elif any(w in name for w in ['speaker', 'audio']):
            return {'automation_type': 'audio', 'tier': 'basic', 'notes': 'Keyword'}
        return {'automation_type': 'other', 'tier': 'basic', 'notes': 'No match'}
    
    try:
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            return {'automation_type': 'other', 'tier': 'basic', 'notes': 'No key'}
        
        client = anthropic.Anthropic(api_key=api_key)
        item_json = json.dumps(item, indent=2)[:400]
        prompt = ("Categorize into: lighting, shading, security_access, climate, audio, networking, power, other. "
                  "Set tier: basic/premium/deluxe. Item: " + item_json + ". "
                  'JSON only: {"automation_type": "x", "tier": "y", "notes": "z"}')
        
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        
        text = msg.content[0].text.strip()
        if text.startswith('```'):
            text = '\n'.join(l for l in text.split('\n') if not l.strip().startswith('```')).strip()
        
        result = json.loads(text)
        valid_types = ['lighting', 'shading', 'security_access', 'climate', 'audio', 'networking', 'power', 'other']
        if result.get('automation_type') not in valid_types:
            result['automation_type'] = 'other'
        if result.get('tier') not in ['basic', 'premium', 'deluxe']:
            result['tier'] = 'basic'
        return result
    except Exception as e:
        print(f"AI error: {e}")
        return {'automation_type': 'other', 'tier': 'basic', 'notes': 'Error'}

def import_all_simpro_data():
    """Import ALL Simpro data using CORRECT API endpoints"""
    config = load_simpro_config()
    if not config.get('connected'):
        return {'success': False, 'error': 'Not connected'}
    
    results = {'customers': [], 'jobs': [], 'quotes': [], 'catalog': [], 'staff': [], 'sites': []}
    errors = []
    
    # Try to get actual company ID first
    company_id = config.get('company_id', '0')
    
    # CORRECT Simpro API endpoints based on documentation
    endpoints = [
        ('/customers/companies/', 'customers', 250, 'display=all'),  # Company customers
        ('/jobs/', 'jobs', 250, 'display=all'),                      # Jobs
        ('/quotes/', 'quotes', 250, 'display=all'),                  # Quotes
        ('/catalogs/', 'catalog', 500, ''),                          # Catalog items (NOT catalogue)
        ('/employees/', 'staff', 200, ''),                           # Staff
        ('/sites/', 'sites', 250, '')                                # Sites
    ]
    
    for endpoint, key, size, extra_params in endpoints:
        try:
            print(f"Fetching {key}...")
            params = {'pageSize': size}
            if extra_params:
                # Add display parameter
                params['display'] = 'all'
            
            resp = make_simpro_api_request(endpoint, params=params)
            if 'error' not in resp:
                # Simpro returns Results array
                if isinstance(resp, dict) and resp.get('Results'):
                    results[key] = resp['Results']
                    print(f"  ✓ Got {len(resp['Results'])} {key}")
                elif isinstance(resp, list):
                    results[key] = resp
                    print(f"  ✓ Got {len(resp)} {key}")
                else:
                    print(f"  ⚠ No data for {key}: {str(resp)[:100]}")
            elif 'error' in resp:
                error_msg = f"{key}: {resp['error']}"
                errors.append(error_msg)
                print(f"  ✗ {error_msg}")
        except Exception as e:
            error_msg = f"{key}: {str(e)}"
            errors.append(error_msg)
            print(f"  ✗ {error_msg}")
    
    total = sum(len(v) for v in results.values())
    print(f"Total items fetched: {total}")
    
    return {
        'success': True,
        'data': results,
        'errors': errors,
        'total_imported': total
    }

# ============================================================================
# AI ANALYSIS FUNCTIONS
# ============================================================================

# pdf_to_image_base64 and image_to_base64 moved to app/utils/image_utils.py
# Imported at top of file from app.utils

# ============================================================================
# WEB SEARCH TOOLS FOR AI AGENTS
# ============================================================================
# web_search, SEARCH_TOOL_SCHEMA, and execute_tool moved to app/utils/ai_tools.py
# Imported at top of file from app.utils

# ============================================================================
# SESSION MANAGEMENT FOR WORKFLOW
# ============================================================================

def save_session_data(session_id, data):
    """Save analysis session data for takeoffs editor"""
    session_file = os.path.join(app.config['SESSION_DATA_FOLDER'], f'{session_id}.json')
    with open(session_file, 'w') as f:
        json.dump(data, f, indent=2)
    return session_file

def load_session_data(session_id):
    """Load analysis session data"""
    session_file = os.path.join(app.config['SESSION_DATA_FOLDER'], f'{session_id}.json')
    if os.path.exists(session_file):
        with open(session_file, 'r') as f:
            return json.load(f)
    return None

def get_session_id():
    """Generate unique session ID"""
    return str(uuid.uuid4())

# ============================================================================
# AI ANALYSIS WITH VISION
# ============================================================================

def analyze_floorplan_with_ai(pdf_path):
    """Enhanced AI analysis for quoting - uses learning from corrections"""
    
    if not ANTHROPIC_AVAILABLE:
        return {
            "error": "Anthropic package not installed",
            "fallback": True,
            "message": "Using fallback estimation mode"
        }
    
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return {
            "error": "No API key found",
            "fallback": True,
            "message": "Set ANTHROPIC_API_KEY environment variable"
        }
    
    try:
        img_base64 = pdf_to_image_base64(pdf_path)
        learning_context = get_learning_context()
        client = anthropic.Anthropic(api_key=api_key)
        
        prompt = f"""You are an AI with VISION analyzing a floor plan image. You can SEE the image - use your eyes!

{learning_context}

🔍 WEB SEARCH AVAILABLE - Use when you need to verify codes/standards

👁️ CRITICAL: YOU ARE LOOKING AT AN IMAGE - USE YOUR VISION!

STEP 1: LOOK AT THE IMAGE - VISUAL ANALYSIS FIRST
================================================

STOP and LOOK at what you're seeing:

1. Visually identify EVERY room by tracing walls with your eyes
2. For each room, note its visual boundaries:
   - Where are the walls? (dark lines)
   - Where are the doors? (openings in walls)
   - Where are the windows? (marked on walls)
   - What's the room shape? (rectangular, L-shaped, etc.)

3. Measure each room's position in the IMAGE:
   - Look at the leftmost wall of the room - what % across the image? (x_start)
   - Look at the rightmost wall - what % across? (x_end)
   - Look at the topmost wall - what % down? (y_start)
   - Look at the bottommost wall - what % down? (y_end)

4. Calculate room center by LOOKING:
   - Visual center x = (x_start + x_end) / 2
   - Visual center y = (y_start + y_end) / 2

EXAMPLE - If you SEE a bedroom:
- Left wall at 20% across image = x_start: 0.20
- Right wall at 40% across image = x_end: 0.40
- Top wall at 30% down image = y_start: 0.30
- Bottom wall at 50% down image = y_end: 0.50
- Center = x: 0.30, y: 0.40

STEP 2: IDENTIFY EXISTING SYMBOLS VISUALLY
==========================================

LOOK at the floor plan image:
- Do you SEE any symbols already placed? (dots, icons, markers)
- Where exactly are they in the image?
- Measure their pixel positions relative to image size
- Note which room each symbol is IN

STEP 3: UNDERSTAND SCALE (if needed)
====================================

- Look for scale bar (usually bottom corner)
- Note scale ratio (e.g., "1:100")
- Use this to understand real-world dimensions
- Validate: Do room sizes make sense? (bedrooms 10-15', living rooms 15-20')

STEP 4: PLAN COMPONENT PLACEMENT VISUALLY
=========================================

For EACH room you identified visually:

1. Look at the room's visual boundaries (x_start to x_end, y_start to y_end)

2. Plan where components should go INSIDE those boundaries:
   - Ceiling light → room visual center (x_center, y_center)
   - Switch → beside door opening (look for door location)
   - Keypad → beside entry door (visually locate the door)
   - Outlets → along walls (stay within room bounds)

3. When placing, ensure coordinates are INSIDE the room:
   - x must be between x_start and x_end
   - y must be between y_start and y_end
   - DON'T place outside the room you're looking at!

EXAMPLE - Placing light in the bedroom from above:
- Bedroom bounds: x: 0.20-0.40, y: 0.30-0.50
- Light at center: x: 0.30, y: 0.40 ✓ (inside bounds)
- NOT at x: 0.80, y: 0.20 ✗ (that's in a different room!)

STEP 5: PLACEMENT RULES (USE YOUR EYES!)
========================================

🔐 SECURITY KEYPADS:
- LOOK for the main entry door
- Place keypad ON THE WALL next to it (within 1-2 feet)
- If door is at x: 0.15, keypad goes at x: 0.17 (slightly to the side)

💡 CEILING LIGHTS:
- LOOK at the room shape
- Place at visual center of the room
- For L-shaped rooms, place in each section

🔘 SWITCHES:
- LOOK for door openings
- Place on wall BESIDE the door (latch side)
- Height: 3.5-4 feet (doesn't affect x,y coordinates)

🪟 WINDOW CONTROLS:
- LOOK for windows (marked on walls)
- Place controls BESIDE each window

STEP 6: GENERATE RESPONSE
=========================

Return JSON with:

{{
    "scale_analysis": {{
        "detected_scale": "what scale you found visually",
        "visual_validation": "do room sizes look realistic?"
    }},
    "rooms": [
        {{
            "name": "room name you read from image",
            "visual_boundaries": {{
                "x_start": 0.XX,
                "x_end": 0.XX,
                "y_start": 0.XX,
                "y_end": 0.XX
            }},
            "center": {{"x": 0.XX, "y": 0.XX}},
            "dimensions_estimated": "width x length based on scale",
            "lighting": {{"count": X, "type": "basic|premium|deluxe"}},
            "shading": {{"count": X, "type": "basic|premium|deluxe"}},
            "security_access": {{"count": X, "type": "basic|premium|deluxe"}},
            "climate": {{"count": X, "type": "basic|premium|deluxe"}},
            "audio": {{"count": X, "type": "basic|premium|deluxe"}}
        }}
    ],
    "components": [
        {{
            "id": "L1",
            "type": "light|switch|shading|security|climate|audio",
            "location": {{
                "x": 0.XX,  // MUST be between room's x_start and x_end
                "y": 0.XX   // MUST be between room's y_start and y_end
            }},
            "room": "which room this is IN (based on visual boundaries)",
            "visual_placement": "describe WHERE in the room you placed this (center, near door, beside window, etc.)",
            "placement_reasoning": "why this position makes sense"
        }}
    ],
    "visual_validation": "Confirm you LOOKED at the image, identified rooms visually, and placed components INSIDE the rooms you saw."
}}

CRITICAL REQUIREMENTS:
======================

✓ USE YOUR VISION - Look at the image first!
✓ IDENTIFY each room by visually tracing its walls
✓ MEASURE room boundaries from what you SEE
✓ PLACE components INSIDE the room boundaries
✓ DON'T place components outside room bounds
✓ DON'T cluster everything at (0,0) or corners
✓ VALIDATE each position is inside the correct room

✗ DON'T hallucinate room positions
✗ DON'T ignore what you can SEE in the image
✗ DON'T place symbols outside the rooms
✗ DON'T guess - LOOK at the image!

Use your VISION. Look at the image. See the rooms. Place components where you SEE them or where they SHOULD be based on what you SEE."""

        # AGENTIC LOOP - AI can search, think, search more, then respond
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": img_base64,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ],
            }
        ]

        max_iterations = 10  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=16000,
                thinking={
                    "type": "enabled",
                    "budget_tokens": 8000
                },
                tools=[SEARCH_TOOL_SCHEMA],  # Give AI access to web search
                messages=messages
            )

            # Check if AI wants to use tools
            if message.stop_reason == "tool_use":
                # AI wants to search for information
                tool_uses = [block for block in message.content if hasattr(block, 'type') and block.type == "tool_use"]

                # Add AI's message to conversation
                messages.append({
                    "role": "assistant",
                    "content": message.content
                })

                # Execute all tool calls
                tool_results = []
                for tool_use in tool_uses:
                    tool_name = tool_use.name
                    tool_input = tool_use.input
                    tool_id = tool_use.id

                    print(f"🔍 AI searching: {tool_input.get('query', 'unknown')}")

                    result = execute_tool(tool_name, tool_input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result
                    })

                # Send tool results back to AI
                messages.append({
                    "role": "user",
                    "content": tool_results
                })

                # AI will continue thinking with the new information
                continue

            elif message.stop_reason == "end_turn":
                # AI is done - extract the final response
                response_text = ""
                for block in message.content:
                    if hasattr(block, 'type') and block.type == "text":
                        response_text = block.text
                        break

                if not response_text:
                    return {"error": "No text response from AI after tool use"}

                try:
                    start_idx = response_text.find('{')
                    end_idx = response_text.rfind('}') + 1
                    if start_idx != -1 and end_idx > start_idx:
                        json_str = response_text[start_idx:end_idx]
                        result = json.loads(json_str)
                        return result
                    else:
                        return {"error": "No JSON found in response", "raw_response": response_text}
                except json.JSONDecodeError as e:
                    return {"error": f"JSON parse error: {str(e)}", "raw_response": response_text}

            else:
                # Unexpected stop reason
                return {"error": f"Unexpected stop reason: {message.stop_reason}"}

        return {"error": "Max iterations reached in agentic loop"}
            
    except Exception as e:
        return {"error": str(e), "fallback": True}

# ============================================================================
# ENHANCED AI MAPPING WITH LEARNING
# ============================================================================

def ai_map_floorplan(file_path, is_pdf=True):
    """Enhanced AI with scale detection and accurate component mapping"""
    
    if not ANTHROPIC_AVAILABLE:
        return {
            "error": "Anthropic package not installed",
            "message": "Please install anthropic package"
        }
    
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return {
            "error": "No API key found",
            "message": "Set ANTHROPIC_API_KEY environment variable"
        }
    
    try:
        # Convert to base64
        if is_pdf:
            img_base64 = pdf_to_image_base64(file_path)
            media_type = "image/png"
        else:
            img_base64 = image_to_base64(file_path)
            media_type = "image/png"
        
        # Get learning context from past corrections
        learning_context = get_mapping_learning_context()
        
        client = anthropic.Anthropic(api_key=api_key)
        
        prompt = f"""You are an autonomous AI agent acting as a licensed professional electrician analyzing a floor plan. You have access to web search to look up ANY codes, standards, or professional knowledge you need in real-time.

{learning_context}

🔍 YOU HAVE WEB SEARCH - USE IT ACTIVELY:
Search for:
- NEC electrical code requirements (specific articles)
- Local building codes and regulations
- Professional electrical installation standards
- Outlet spacing, switch placement codes
- GFCI requirements and locations
- Arc-fault breaker requirements
- Circuit load calculations
- Electrical symbol standards
- Common sense electrician practices

WHEN TO SEARCH:
- Before placing any component that has code requirements
- When determining outlet spacing (search "NEC outlet spacing")
- When unsure about GFCI requirements (search "NEC GFCI requirements")
- To verify switch heights and positions
- To check circuit breaker sizing
- To understand electrical symbols on the plan
- Any time you need professional electrician knowledge

EXAMPLE SEARCHES:
- "NEC code 210.52 outlet spacing requirements"
- "NEC GFCI requirements kitchen bathroom"
- "electrical switch height ADA code"
- "arc fault breaker requirements 2023 NEC"
- "electrical panel clearance requirements"
- "typical residential circuit breaker sizes"

REFERENCE KNOWLEDGE (but VERIFY with search when placing components):

⚡ ELECTRICAL PANELS & DISTRIBUTION:
- Main distribution board: Near main entry, easily accessible, not in bathrooms/closets
- Sub-panels: Central to areas they serve, 30" clear working space in front
- Service entrance: Typically at one edge of building
- Never obstruct panels with furniture or in tight spaces

💡 LIGHTING PLACEMENT:
- Ceiling lights: Center of rooms for general illumination
- Recessed lights: 4-6 feet apart in grid pattern, 2-3 feet from walls
- Pendant lights: Over islands, tables, workspaces at 28-34" above surface
- Task lighting: Under cabinets, over sinks, workbenches
- Outdoor lights: All entry doors, pathways, building perimeter
- Emergency/egress lighting: Exit paths, stairwells (commercial)

🔘 SWITCH LOCATIONS (CRITICAL FOR CODE COMPLIANCE):
- Height: 42-48 inches from finished floor (ADA: 48" max)
- Position: On latch side of door, 4-6" from door frame
- Multi-way switches: At each entry point for rooms with multiple doors
- 3-way/4-way: Stairs (top and bottom), long hallways, large rooms
- NEVER behind doors or in inaccessible locations
- NEVER in closets controlling closet lights (fire code)

🔌 OUTLET REQUIREMENTS (NEC CODE):
- Spacing: Max 12 feet apart on walls, no point more than 6 feet from outlet
- Kitchen counters: Every 4 feet, GFCI protected within 6 feet of sink
- Bathrooms: GFCI protected, at least one per sink
- Outdoor: GFCI protected, weatherproof covers
- Height: 12-18" above finished floor (standard), 15" min (ADA)
- Dedicated circuits: Refrigerator, dishwasher, garbage disposal, microwave

🏗️ SPECIAL LOCATIONS:
- Wet areas (bathroom/kitchen): GFCI protection mandatory
- Garage: GFCI outlets, overhead lighting
- Basement/unfinished areas: GFCI, appropriate for environment
- Laundry: 240V outlet for dryer, dedicated 20A circuit for washer
- HVAC: Dedicated circuits, disconnect switches

📋 CIRCUIT ORGANIZATION:
- Lighting circuits: Typically 15A, multiple rooms per circuit
- Outlet circuits: 15A or 20A, room-based or area-based
- Kitchen: Multiple 20A circuits for appliances
- Dedicated circuits: A/C, heat pump, water heater, range
- Load balancing: Distribute across phases evenly

ANALYSIS PROCESS:

STEP 1: SCALE DETECTION & MEASUREMENT
MANDATORY - Professional plans always have scale:
1. Look for scale bar in: title block, bottom-left, bottom-right corners
2. Standard architectural scales: 1:50, 1:100, 1:200, 1/4"=1'-0", 1/8"=1'-0"
3. Electrical plan scales often match architectural plans
4. Measure scale bar length in pixels and calculate pixels per unit
5. Use scale to determine room dimensions and component spacing
6. Verify dimensions make sense (bedrooms 10-15', living rooms 15-20', etc.)

STEP 2: IDENTIFY PLAN TYPE & SYMBOLS
Determine what you're looking at:
- Existing electrical plan with symbols already placed? → Map what you see
- Architectural plan without electrical? → Suggest proper electrical placement
- Note symbol legend if present (plans use different symbol standards)

Standard electrical symbols:
- ⊕ or ● = Ceiling light fixture
- ◐ = Wall-mounted light
- $ = Switch (single)
- $$ = Double switch, $$$ = Triple switch
- S₃ = 3-way switch, S₄ = 4-way switch
- ⊗ or ▢ = Outlet/receptacle (duplex)
- ⊗GFCI = GFCI outlet
- □ = Junction box
- ■ = Distribution board/panel
- ━━ = Circuit/wire run

STEP 3: MAP EVERY COMPONENT WITH EXACT COORDINATES
For EVERY symbol on the plan:
1. Identify component type and specifications
2. Note its ACTUAL position in the image
3. Measure from image edges, convert to normalized 0-1 coordinates
4. Verify the position makes professional sense:
   - Switches near doors (not behind them)
   - Outlets spaced per code (not clustered)
   - Lights centered or properly distributed
   - Panels accessible with clearance

VALIDATION QUESTIONS (Ask yourself for EACH component):
- "Is this where a professional electrician would place this?"
- "Does this meet electrical code requirements?"
- "Is this position accessible and functional?"
- "Am I seeing this symbol in the image, or am I guessing?"
- "Would an inspector approve this placement?"

STEP 4: TRACE CIRCUIT PATHS
- Follow circuit lines from panels to components
- Identify which breaker/circuit each component belongs to
- Map 3-way switch pairs (they control same lights)
- Note home runs (circuits going back to panel)
- Identify junction boxes where circuits split

STEP 5: VERIFY CODE COMPLIANCE
- Kitchen: Sufficient counter outlets (every 4'), GFCI near sink
- Bathroom: GFCI outlets, proper lighting, ventilation switch
- Bedrooms: Adequate outlets (12' spacing), switched lighting
- Hallways: Lighting with 3-way switches if long
- Outdoor: GFCI outlets, entry lighting
- Safety: Arc-fault protection (bedrooms), proper grounding

RESPONSE FORMAT (JSON):
{{
    "analysis": {{
        "scale": "detected scale with confidence (e.g., '1:100 - found in title block')",
        "scale_bar_location": "where scale was found",
        "total_rooms": count,
        "plan_type": "residential|commercial|industrial",
        "existing_electrical": true|false,
        "building_dimensions": "estimated size based on scale",
        "notes": "Professional observations about the plan and electrical system"
    }},
    "components": [
        {{
            "id": "unique_id (DB1, L1, S1, O1, J1, etc)",
            "type": "light|switch|outlet|panel|junction|gfci|other",
            "location": {{
                "x": precise_x_0_to_1,
                "y": precise_y_0_to_1
            }},
            "label": "label from plan or generated (e.g., 'S1', 'DB-MAIN')",
            "room": "room name",
            "description": "detailed description (e.g., 'recessed LED ceiling fixture 6-inch', 'single-pole switch 15A', 'GFCI duplex outlet 20A')",
            "circuit": "circuit ID if visible or determinable",
            "specifications": "voltage, amperage, special requirements",
            "placement_reasoning": "why this position meets code/standards (e.g., 'beside door per NEC', 'within 6 feet of sink - GFCI required', 'centered for even light distribution')",
            "code_compliant": "yes|no|uncertain - with brief explanation"
        }}
    ],
    "connections": [
        {{
            "from": "component_id",
            "to": "component_id",
            "type": "power|control|3-way|4-way|data",
            "circuit": "circuit_label",
            "path": "description of wire path and routing",
            "wire_type": "cable type if visible (e.g., '14/2 NM-B', '12/3 NM-B')"
        }}
    ],
    "circuits": [
        {{
            "id": "circuit_id (e.g., 'A1', 'B3', 'Circuit-1')",
            "panel": "distribution board ID",
            "breaker_size": "amperage (e.g., '15A', '20A')",
            "components": ["component_id_1", "component_id_2"],
            "load_estimate": "estimated load in watts/amps",
            "circuit_type": "lighting|outlet|dedicated|HVAC|appliance"
        }}
    ],
    "code_compliance": {{
        "kitchen": "compliance notes for kitchen electrical",
        "bathrooms": "compliance notes for bathrooms",
        "bedrooms": "compliance notes for bedrooms",
        "outdoor": "compliance notes for outdoor electrical",
        "overall": "general code compliance assessment"
    }},
    "validation_notes": "Explain how you verified each position is accurate (from plan or per professional standards). Note any assumptions. Confirm you used extended thinking to validate placement logic."
}}

ABSOLUTE REQUIREMENTS:
✓ USE extended thinking to reason through every component position
✓ DETECT and USE the scale for accurate measurements
✓ MAP components where they ACTUALLY are on the plan
✓ If no electrical symbols exist, SUGGEST proper placement per NEC/professional standards
✓ FOLLOW electrical code requirements (NEC)
✓ INCLUDE placement_reasoning for every component
✓ VERIFY outlet spacing, switch heights, GFCI requirements
✓ ENSURE clearances around panels and equipment
✗ DO NOT hallucinate component positions
✗ DO NOT cluster everything at (0,0) or image corners
✗ DO NOT place switches behind doors
✗ DO NOT violate code requirements (outlet spacing, GFCI locations, etc.)
✗ DO NOT guess randomly - use professional judgment
✗ DO NOT ignore scale information

This electrical plan will be used for actual installation. Accuracy is critical. Search for codes. Think. Verify. Be precise."""

        # AGENTIC LOOP - AI can search codes, verify standards, then analyze
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": img_base64,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ],
            }
        ]

        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=16000,
                thinking={
                    "type": "enabled",
                    "budget_tokens": 8000
                },
                tools=[SEARCH_TOOL_SCHEMA],  # Give AI access to web search
                messages=messages
            )

            # Check if AI wants to use tools
            if message.stop_reason == "tool_use":
                # AI wants to search for codes/standards
                tool_uses = [block for block in message.content if hasattr(block, 'type') and block.type == "tool_use"]

                # Add AI's message to conversation
                messages.append({
                    "role": "assistant",
                    "content": message.content
                })

                # Execute all tool calls
                tool_results = []
                for tool_use in tool_uses:
                    tool_name = tool_use.name
                    tool_input = tool_use.input
                    tool_id = tool_use.id

                    print(f"🔍 AI searching electrical codes: {tool_input.get('query', 'unknown')}")

                    result = execute_tool(tool_name, tool_input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result
                    })

                # Send tool results back to AI
                messages.append({
                    "role": "user",
                    "content": tool_results
                })

                # AI will continue with the new knowledge
                continue

            elif message.stop_reason == "end_turn":
                # AI is done - extract final response
                response_text = ""
                for block in message.content:
                    if hasattr(block, 'type') and block.type == "text":
                        response_text = block.text
                        break

                if not response_text:
                    return {"error": "No text response from AI after tool use"}

                try:
                    start_idx = response_text.find('{')
                    end_idx = response_text.rfind('}') + 1
                    if start_idx != -1 and end_idx > start_idx:
                        json_str = response_text[start_idx:end_idx]
                        result = json.loads(json_str)
                        return result
                    else:
                        return {"error": "No JSON found in response", "raw_response": response_text}
                except json.JSONDecodeError as e:
                    return {"error": f"JSON parse error: {str(e)}", "raw_response": response_text}

            else:
                # Unexpected stop reason
                return {"error": f"Unexpected stop reason: {message.stop_reason}"}

        return {"error": "Max iterations reached in agentic loop"}
            
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}

def generate_marked_up_image(original_image_path, mapping_data, output_path):
    """Generate marked-up floor plan with components and connections"""
    
    try:
        if original_image_path.endswith('.pdf'):
            doc = fitz.open(original_image_path)
            page = doc[0]
            # Use 300 DPI for high quality output (300/72 = 4.17x zoom)
            mat = fitz.Matrix(300/72, 300/72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()
        else:
            img = Image.open(original_image_path)
        
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except:
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        width, height = img.size
        
        components = mapping_data.get('components', [])
        component_positions = {}
        
        for comp in components:
            comp_id = comp.get('id', '')
            label = comp.get('label', comp_id)
            location = comp.get('location', {})
            
            x = int(location.get('x', 0.5) * width)
            y = int(location.get('y', 0.5) * height)
            
            component_positions[comp_id] = (x, y)
            
            comp_type = comp.get('type', 'unknown')
            automation_category = comp.get('automation_category', comp_type)

            # Map automation categories to visual styles
            if comp_type == 'light' or automation_category == 'lighting':
                color = '#FFD700'  # Gold for lighting
                radius = 15
                symbol = '💡'
            elif comp_type == 'switch':
                color = '#4169E1'  # Royal blue for switches
                radius = 12
                symbol = '🔘'
            elif automation_category == 'shading':
                color = '#8B4513'  # Saddle brown for shading
                radius = 14
                symbol = '🪟'
            elif automation_category == 'security_access' or automation_category == 'security':
                color = '#DC143C'  # Crimson for security
                radius = 16
                symbol = '🔐'
            elif automation_category == 'climate':
                color = '#00CED1'  # Dark turquoise for climate
                radius = 14
                symbol = '🌡️'
            elif automation_category == 'audio':
                color = '#9370DB'  # Medium purple for audio
                radius = 14
                symbol = '🔊'
            elif comp_type == 'outlet':
                color = '#32CD32'  # Lime green for outlets
                radius = 12
                symbol = '⚡'
            elif comp_type == 'panel':
                color = '#FF4500'  # Orange red for panels
                radius = 20
                symbol = '⚙️'
            else:
                color = '#808080'  # Gray for unknown
                radius = 10
                symbol = '•'
            
            # Draw circle with color
            draw.ellipse([x-radius, y-radius, x+radius, y+radius],
                        outline=color, fill=None, width=3)

            # Draw label with emoji for clarity
            label_text = f"{label}"
            draw.text((x+radius+5, y-radius), label_text, fill=color, font=font)
        
        connections = mapping_data.get('connections', [])
        for conn in connections:
            from_id = conn.get('from')
            to_id = conn.get('to')
            
            if from_id in component_positions and to_id in component_positions:
                from_pos = component_positions[from_id]
                to_pos = component_positions[to_id]
                
                conn_type = conn.get('type', 'power')
                if conn_type == 'power':
                    line_color = 'red'
                    width = 3
                elif conn_type == 'control':
                    line_color = 'blue'
                    width = 2
                else:
                    line_color = 'green'
                    width = 2
                
                draw.line([from_pos, to_pos], fill=line_color, width=width)
                
                mid_x = (from_pos[0] + to_pos[0]) // 2
                mid_y = (from_pos[1] + to_pos[1]) // 2
                circuit = conn.get('circuit', '')
                if circuit:
                    draw.text((mid_x, mid_y), str(circuit), fill='purple', font=small_font)

        # Add legend and scale information at bottom for clarity
        legend_y = height - 140
        legend_items = [
            ('💡 Lighting', '#FFD700'),
            ('🔘 Switch', '#4169E1'),
            ('🪟 Shading', '#8B4513'),
            ('🔐 Security', '#DC143C'),
            ('🌡️ Climate', '#00CED1'),
            ('🔊 Audio', '#9370DB'),
        ]

        # Draw semi-transparent background for legend
        draw.rectangle([10, legend_y-10, 300, height-10], fill='white', outline='black', width=2)

        # Add scale information at top of legend if available
        scale_info = mapping_data.get('analysis', {}).get('scale', 'not detected')
        if scale_info and scale_info != 'not detected':
            draw.text((20, legend_y-5), f"Scale: {scale_info}", fill='black', font=font)
            legend_y += 20

        # Draw legend items
        for idx, (text, color) in enumerate(legend_items):
            y_pos = legend_y + (idx * 18)
            draw.ellipse([20, y_pos, 30, y_pos+10], outline=color, fill=None, width=2)
            draw.text((40, y_pos-2), text, fill='black', font=small_font)

        img.save(output_path, 'PNG')
        return True
        
    except Exception as e:
        print(f"Error generating marked-up image: {str(e)}")
        print(traceback.format_exc())
        return False

# ============================================================================
# ROUTES
# ============================================================================

# ============================================================================
# ADMIN PAGE EDITOR
# ============================================================================

# Define customizations file path before it's used in load_page_config()
CUSTOMIZATIONS_FILE = os.path.join(app.config['CRM_DATA_FOLDER'], 'customizations.json')

def load_page_config():
    """Load the landing page configuration, merging in admin customizations"""
    config_file = os.path.join(app.config['DATA_FOLDER'], 'page_config.json')
    default_config = {
        'logo_icon': '🏠',
        'logo_text': 'Integratd Living',
        'logo_color': '#556B2F',
        'welcome_title': 'Welcome to Integratd Living',
        'welcome_subtitle': 'Your complete business automation platform',
        'background_color': '#f5f5f7',
        'modules': [
            {'href': '/crm', 'icon': '📊', 'title': 'CRM Dashboard', 'description': 'Manage customers, projects, scheduling, inventory, and more in one place.'},
            {'href': '/quotes', 'icon': '💰', 'title': 'Quote Automation', 'description': 'Upload floor plans and let AI generate accurate quotes automatically.'},
            {'href': '/canvas', 'icon': '🎨', 'title': 'Canvas Editor', 'description': 'Professional floor plan editor with zoom, pan, and symbol management.'},
            {'href': '/mapping', 'icon': '⚡', 'title': 'Electrical Mapping', 'description': 'Professional electrical mapping with wiring, circuits, and component management.'},
            {'href': '/board-builder', 'icon': '🔌', 'title': 'Loxone Board Builder', 'description': 'Design professional Loxone boards with AI generation and integration with mapping data.'},
            {'href': '/electrical-cad', 'icon': '📟', 'title': 'Electrical CAD Designer', 'description': 'Professional-grade CAD drawings with AI generation, DXF export, and full electrical standards compliance.'},
            {'href': '/learning', 'icon': '🧠', 'title': 'AI Learning', 'description': 'Train the system with examples to improve accuracy over time.'},
            {'href': '/kanban', 'icon': '📋', 'title': 'Operations Board', 'description': 'Kanban task management system for team workflow and project tracking.'},
            {'href': '/admin', 'icon': '👤', 'title': 'Admin Panel', 'description': 'Manage users, assign permissions, and configure system access controls.'}
        ]
    }

    # Load base config - always start with default and merge
    config = default_config.copy()
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                saved_config = json.load(f)
                # Merge saved config into default, preserving modules if not in saved
                for key, value in saved_config.items():
                    config[key] = value
                # Ensure modules always exists
                if 'modules' not in config:
                    config['modules'] = default_config['modules']
        except:
            pass
    
    # Merge in admin customizations
    try:
        customizations = load_json_file(CUSTOMIZATIONS_FILE, {})
        
        # Apply app settings
        if 'settings' in customizations:
            settings = customizations['settings']
            if settings.get('app_name'):
                config['logo_text'] = settings['app_name']
                config['welcome_title'] = f"Welcome to {settings['app_name']}"
            if settings.get('tagline'):
                config['welcome_subtitle'] = settings['tagline']
            if settings.get('primary_color'):
                config['logo_color'] = settings['primary_color']
        
        # Apply module customizations
        if 'modules' in customizations:
            module_customs = customizations['modules']
            # Map module IDs to href paths
            id_to_href = {
                'crm': '/crm', 'quotes': '/quotes', 'canvas': '/canvas',
                'mapping': '/mapping', 'board_builder': '/board-builder',
                'electrical_cad': '/electrical-cad', 'learning': '/learning',
                'kanban': '/kanban', 'ai_mapping': '/ai-mapping', 'simpro': '/simpro'
            }
            
            for module in config.get('modules', []):
                # Find matching customization by href
                for mod_id, customs in module_customs.items():
                    if id_to_href.get(mod_id) == module.get('href'):
                        if customs.get('icon'):
                            module['icon'] = customs['icon']
                        if customs.get('label'):
                            module['title'] = customs['label']
                        if customs.get('description'):
                            module['description'] = customs['description']
                        break
    except Exception as e:
        logger.warning(f"Could not load admin customizations: {e}")
    
    return config

def save_page_config(config):
    """Save the landing page configuration"""
    config_file = os.path.join(app.config['DATA_FOLDER'], 'page_config.json')
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

# ============================================================================
# ADMIN ROUTES - MOVED TO app/api/admin.py
# ============================================================================
# The following routes are now handled by the admin blueprint:
# - /admin
# - /admin/page-editor
# - /api/admin/page-config (GET, POST)
# - /api/admin/customizations (GET, POST)
# - /api/admin/branding (POST)
# - /api/admin/settings (GET, POST)

# ============================================================================
# STORAGE POLICY VALIDATION
# ============================================================================
# Validate storage configuration BEFORE any CRM/auth/kanban operations.
# In production, DATABASE_URL is required and JSON persistence is disabled.
from config import validate_storage_config, get_storage_mode, is_production, has_database
try:
    validate_storage_config()
    storage_mode = get_storage_mode()
    logger.info(f"🔧 Storage policy: {storage_mode}")
    if is_production():
        logger.info("🏭 Production mode: Database required for CRM/auth/kanban")
    else:
        if has_database():
            logger.info("💾 Development mode: Using database")
        else:
            logger.info("📁 Development mode: Using JSON fallback")
except RuntimeError as e:
    logger.error(f"❌ Storage policy error: {e}")
    raise

# Initialize users file on startup (only if JSON fallback is allowed)
if not has_database():
    auth.init_users_file()

# Keep BRANDING_DIR for backwards compatibility with existing code
BRANDING_DIR = os.path.join(app.config['UPLOAD_FOLDER'], 'branding')
os.makedirs(BRANDING_DIR, exist_ok=True)

# Route /uploads/<path:filename> moved to app/api/misc.py

# ============================================================================
# PAGE ROUTES - MOVED TO app/api/pages.py
# ============================================================================
# The following routes are now handled by the pages blueprint:
# - / (index)
# - /apps
# - /crm
# - /quotes
# - /canvas
# - /learning
# - /simpro
# - /ai-mapping
# - /takeoffs/<session_id>
# - /mapping
# - /board-builder
# - /electrical-cad
# - /pdf-editor
# - /kanban

# ============================================================================
# AUTOMATION DATA API ENDPOINTS - MOVED TO app/api/misc.py
# ============================================================================
# Routes /api/data (GET, POST) moved to app/api/misc.py

# ============================================================================
# API - AI MAPPING WITH LEARNING - MOVED TO app/api/ai_mapping.py
# ============================================================================
# Routes moved:
# - /api/ai-mapping/analyze
# - /api/ai-mapping/save-correction
# - /api/ai-mapping/learning-stats
# - /api/ai-mapping/download/<filename>
# - /api/ai-mapping/history
# - /api/ai/mapping
# - /api/mapping/export

# ============================================================================
# BOARD BUILDER - LOXONE BOARD DESIGN TOOL - MOVED TO app/api/board_builder.py
# ============================================================================
# Routes moved:
# - /api/board-builder/generate
# - /api/board-builder/available-sessions
# - /api/board-builder/import/mapping/<session_id>
# - /api/board-builder/import/canvas/<session_id>
# - /api/board-builder/export/crm

# Route /api/crm/stock GET/POST moved to app/api/crm.py

# Route /api/crm/stock/add moved to app/api/crm.py

# ============================================================================
# ELECTRICAL CAD DESIGNER MODULE - MOVED TO app/api/electrical_cad.py
# ============================================================================
# Routes moved:
# - /api/cad/new
# - /api/cad/load/<session_id>
# - /api/cad/save
# - /api/cad/list
# - /api/cad/import-board/<board_id>
# - /api/cad/import-quote/<quote_id>
# - /api/cad/calculate-circuit
# - /api/cad/symbols
# - /api/cad/ai-generate
# - /api/cad/export
# - /api/cad/validate
# - /api/cad/upload-pdf

# Route /api/ai-mapping/history moved to app/api/ai_mapping.py

# ============================================================================
# QUOTE AUTOMATION ROUTES - MOVED TO app/api/quote_automation.py
# ============================================================================
# Routes moved:
# - /api/generate-floorplan-pdf
# - /api/analyze
# - /api/generate_quote
# - /api/export_pdf

# Routes moved to app/api/canvas.py:
# - /api/takeoffs/export
# - /api/session/<session_id>
# - /api/canvas/upload
# - /api/canvas/export

# ============================================================================
# LEARNING ROUTES - MOVED TO app/api/learning.py
# ============================================================================
# Routes moved:
# - /api/learning/examples
# - /api/learning/upload
# - /api/learning/history
# - /api/upload-learning-data
# - /api/process-instructions

# ============================================================================
# SIMPRO ROUTES - MOVED TO app/api/simpro.py
# ============================================================================
# Routes moved:
# - /api/simpro/config
# - /api/simpro/connect
# - /api/simpro/disconnect
# - /api/simpro/sync
# - /api/simpro/test-endpoints
# - /api/simpro/customers
# - /api/simpro/jobs
# - /api/simpro/quotes
# - /api/simpro/catalogs
# - /api/simpro/labor-rates
# - /api/simpro/import-all

# Route /api/crm/customers GET/POST moved to app/api/crm.py

# Route /api/crm/customers/<id> moved to app/api/crm.py

# Route /api/crm/projects GET/POST moved to app/api/crm.py

# Route /api/crm/projects/<id> moved to app/api/crm.py

# ============================================================================
# QUOTES MANAGEMENT ENDPOINTS
# ============================================================================

# Route /api/crm/quotes GET/POST moved to app/api/crm.py

# Route /api/crm/quotes/<id> moved to app/api/crm.py


# ============================================================================
# ALL ROUTES HAVE BEEN MOVED TO BLUEPRINTS IN app/api/
# ============================================================================
# Routes are now organized in the following blueprint files:
# - app/api/pages.py - Page rendering routes
# - app/api/auth_routes.py - Authentication routes
# - app/api/admin.py - Admin routes
# - app/api/misc.py - Misc utility routes
# - app/api/learning.py - Learning routes
# - app/api/simpro.py - Simpro integration routes
# - app/api/kanban.py - Kanban routes
# - app/api/pdf_editor.py - PDF editor routes
# - app/api/ai_mapping.py - AI mapping routes
# - app/api/board_builder.py - Board builder routes
# - app/api/canvas.py - Canvas routes
# - app/api/electrical_cad.py - Electrical CAD routes
# - app/api/quote_automation.py - Quote automation routes
# - app/api/crm.py - Core CRM routes
# - app/api/crm_extended.py - Extended CRM routes
# - app/api/dashboard.py - Dashboard routes
# - app/api/ai_chat.py - AI chat routes
# - app/api/scheduler.py - Scheduler routes

# ============================================================================
# APPLICATION STARTUP
# ============================================================================

def start_background_services():
    """Start background services when the app starts."""
    if CRM_USE_DATABASE:
        try:
            from services.scheduler import init_scheduler
            init_scheduler()
            logger.info("Background scheduler started")
        except Exception as e:
            logger.error(f"Failed to start background scheduler: {e}")


# Start background services when module loads (for production)
if CRM_USE_DATABASE and os.environ.get('FLASK_ENV') != 'development':
    start_background_services()


# ============================================================================
# BLUEPRINT REGISTRATION
# ============================================================================
# Register modular blueprints with app functions they need

from app import register_blueprints

# Provide app functions that blueprints need access to
app_functions = {
    'load_data': load_data,
    'save_data': save_data,
    'load_session_data': load_session_data,
    'load_page_config': load_page_config,
    'save_page_config': save_page_config,
    'load_learning_index': load_learning_index,
    'save_learning_index': save_learning_index,
    'analyze_floorplan_with_ai': analyze_floorplan_with_ai,
    'import_all_simpro_data': import_all_simpro_data,
    'categorize_with_ai': categorize_with_ai,
    'ai_map_floorplan': ai_map_floorplan,
    'generate_marked_up_image': generate_marked_up_image,
    'load_mapping_learning_index': load_mapping_learning_index,
    'save_mapping_learning_index': save_mapping_learning_index,
    'save_session_data': save_session_data,
    'get_session_id': get_session_id,
}

register_blueprints(app, app_functions)
logger.info("✅ Registered modular blueprints")


if __name__ == '__main__':
    # Database tables are now created via Alembic migrations
    # Run: alembic upgrade head
    if CRM_USE_DATABASE:
        print("✅ Using PostgreSQL database (run 'alembic upgrade head' for migrations)")
        # Start background services for development
        start_background_services()
    else:
        print("📁 Using JSON file storage")

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
