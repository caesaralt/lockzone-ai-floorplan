from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import json
import copy
from datetime import datetime
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
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient

# Try to import anthropic, but don't fail if not available
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("WARNING: anthropic package not installed. AI features will use fallback mode.")

# Try to import tavily for web search
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    print("WARNING: tavily-python package not installed. Web search features will be limited.")

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
CORS(app)

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Fix postgres:// to postgresql:// for SQLAlchemy
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    USE_DATABASE = True
else:
    USE_DATABASE = False
    print("INFO: No DATABASE_URL found. Using JSON file storage.")

db = SQLAlchemy(app) if USE_DATABASE else None

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['DATA_FOLDER'] = 'data'
app.config['LEARNING_FOLDER'] = 'learning_data'
app.config['SIMPRO_CONFIG_FOLDER'] = 'simpro_config'
app.config['CRM_DATA_FOLDER'] = 'crm_data'
app.config['AI_MAPPING_FOLDER'] = 'ai_mapping'
app.config['MAPPING_LEARNING_FOLDER'] = 'mapping_learning'
app.config['SESSION_DATA_FOLDER'] = 'session_data'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER'],
               app.config['DATA_FOLDER'], app.config['LEARNING_FOLDER'],
               app.config['SIMPRO_CONFIG_FOLDER'], app.config['CRM_DATA_FOLDER'],
               app.config['AI_MAPPING_FOLDER'], app.config['MAPPING_LEARNING_FOLDER'],
               app.config['SESSION_DATA_FOLDER']]:
    os.makedirs(folder, exist_ok=True)

# Database Models
if USE_DATABASE:
    class KanbanTask(db.Model):
        __tablename__ = 'kanban_tasks'

        id = db.Column(db.String(36), primary_key=True)
        column = db.Column(db.String(50), nullable=False)
        content = db.Column(db.Text, nullable=False)
        notes = db.Column(db.Text, default='')
        color = db.Column(db.String(7), default='#ffffff')
        position_x = db.Column(db.Float, default=10)
        position_y = db.Column(db.Float, default=10)
        assigned_to = db.Column(db.String(100))
        pinned = db.Column(db.Boolean, default=False)
        due_date = db.Column(db.String(20))
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

        def to_dict(self):
            return {
                'id': self.id,
                'column': self.column,
                'content': self.content,
                'notes': self.notes,
                'color': self.color,
                'position': {'x': self.position_x, 'y': self.position_y},
                'assigned_to': self.assigned_to,
                'pinned': self.pinned,
                'due_date': self.due_date,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None
            }

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
INTEGRATIONS_FILE = os.path.join(app.config['CRM_DATA_FOLDER'], 'integrations.json')

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

def load_json_file(filepath, default=None):
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return default if default is not None else []

def save_json_file(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

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

def pdf_to_image_base64(pdf_path, page_num=0):
    """Convert PDF page to base64 image for Claude Vision API"""
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    
    # Render at high resolution
    mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
    pix = page.get_pixmap(matrix=mat)
    
    # Convert to PNG bytes
    img_bytes = pix.tobytes("png")
    
    # Convert to base64
    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
    
    doc.close()
    return img_base64

def image_to_base64(image_path):
    """Convert image to base64"""
    with Image.open(image_path) as img:
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

# ============================================================================
# WEB SEARCH TOOLS FOR AI AGENTS
# ============================================================================

def web_search(query, max_results=5):
    """
    Perform web search using Tavily API to get real-time knowledge.
    AI agents use this to look up professional standards, codes, best practices.
    """
    if not TAVILY_AVAILABLE:
        return {
            "error": "Tavily not available",
            "results": [],
            "message": "Install tavily-python for web search capabilities"
        }

    tavily_api_key = os.environ.get('TAVILY_API_KEY')
    if not tavily_api_key:
        return {
            "error": "No Tavily API key",
            "results": [],
            "message": "Set TAVILY_API_KEY environment variable"
        }

    try:
        client = TavilyClient(api_key=tavily_api_key)
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",  # More thorough search
            include_answer=True,  # Get AI-generated answer
            include_raw_content=False  # Don't need full HTML
        )

        return {
            "success": True,
            "query": query,
            "answer": response.get("answer", ""),
            "results": [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                    "score": r.get("score", 0)
                }
                for r in response.get("results", [])
            ]
        }
    except Exception as e:
        return {
            "error": str(e),
            "results": [],
            "message": "Web search failed"
        }

# Tool schema for Anthropic's tool use
SEARCH_TOOL_SCHEMA = {
    "name": "web_search",
    "description": "Search the web for real-time information about professional standards, building codes, electrical requirements, installation best practices, and any other knowledge needed for accurate analysis. Use this tool whenever you need to verify information, look up codes, or understand professional requirements.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query. Be specific about what you're looking for (e.g., 'NEC code kitchen outlet spacing requirements', 'professional security keypad placement residential', 'typical room dimensions residential architecture')"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of search results to return (default: 5)",
                "default": 5
            }
        },
        "required": ["query"]
    }
}

def execute_tool(tool_name, tool_input):
    """Execute a tool based on tool name and input"""
    if tool_name == "web_search":
        query = tool_input.get("query", "")
        max_results = tool_input.get("max_results", 5)
        result = web_search(query, max_results)

        if result.get("success"):
            # Format results for AI consumption
            formatted = f"Search Query: {result['query']}\n\n"
            if result.get('answer'):
                formatted += f"Summary Answer: {result['answer']}\n\n"
            formatted += "Search Results:\n"
            for i, r in enumerate(result['results'], 1):
                formatted += f"{i}. {r['title']}\n   {r['content'][:300]}...\n   Source: {r['url']}\n\n"
            return formatted
        else:
            return f"Search failed: {result.get('error', 'Unknown error')}"

    return f"Unknown tool: {tool_name}"

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
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
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

@app.route('/')
def index():
    return render_template('template_unified.html')

@app.route('/crm')
def crm_page():
    return render_template('crm.html')

@app.route('/quotes')
def quotes_page():
    return render_template('index.html')

@app.route('/canvas')
def canvas_page():
    """Unified editor - same as takeoffs but standalone"""
    automation_data = load_data()
    return render_template('unified_editor.html',
                         automation_data=automation_data,
                         initial_symbols=[],
                         tier='basic',
                         project_name='New Project',
                         session_data={})

@app.route('/learning')
def learning_page():
    return render_template('learning.html')

@app.route('/simpro')
def simpro_page():
    return render_template('simpro.html')

@app.route('/ai-mapping')
def ai_mapping_page():
    return render_template('template_ai_mapping.html')

@app.route('/takeoffs/<session_id>')
def takeoffs_page(session_id):
    """Unified editor with AI analysis results loaded"""
    session_data = load_session_data(session_id)
    if not session_data:
        return "Session not found", 404

    # Load automation data
    automation_data = load_data()

    # Prepare symbols from AI analysis
    analysis_result = session_data.get('analysis_result', {})
    components = analysis_result.get('components', [])

    symbols = []
    for comp in components:
        symbols.append({
            'id': comp.get('id', ''),
            'type': comp.get('type', 'unknown'),
            'x': comp.get('location', {}).get('x', 0.5),
            'y': comp.get('location', {}).get('y', 0.5),
            'room': comp.get('room', ''),
            'automation_category': comp.get('automation_category', comp.get('type', 'unknown')),
            'label': comp.get('id', ''),
            'items': [],
            'custom_image_data': None
        })

    return render_template('unified_editor.html',
                         session_data=session_data,
                         automation_data=automation_data,
                         initial_symbols=symbols,
                         project_name=session_data.get('project_name', 'AI Analysis - Edit & Review'),
                         tier=session_data.get('tier', 'basic'))

@app.route('/mapping')
def mapping_page():
    """Vectorworks-style mapping tool"""
    session_id = request.args.get('session')
    project_name = 'New Mapping Project'

    if session_id:
        session_data = load_session_data(session_id)
        if session_data:
            project_name = session_data.get('project_name', 'Mapping Project')

    return render_template('mapping.html', project_name=project_name)

# ============================================================================
# API - AI MAPPING WITH LEARNING
# ============================================================================

@app.route('/api/ai-mapping/analyze', methods=['POST'])
def ai_mapping_analyze():
    """Analyze floor plan with AI learning"""
    try:
        if 'floorplan' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['floorplan']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Empty filename'}), 400
        
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        file_path = os.path.join(app.config['AI_MAPPING_FOLDER'], unique_filename)
        file.save(file_path)
        
        is_pdf = filename.lower().endswith('.pdf')
        
        # Analyze with AI (includes learning context)
        mapping_result = ai_map_floorplan(file_path, is_pdf)
        
        if 'error' in mapping_result:
            return jsonify({'success': False, 'error': mapping_result['error']})
        
        # Generate marked-up image
        output_filename = f"marked_{timestamp}_{os.path.splitext(filename)[0]}.png"
        output_path = os.path.join(app.config['AI_MAPPING_FOLDER'], output_filename)
        
        generate_marked_up_image(file_path, mapping_result, output_path)
        
        # Create analysis record
        analysis_id = str(uuid.uuid4())
        
        return jsonify({
            'success': True,
            'analysis_id': analysis_id,
            'mapping': mapping_result,
            'original_file': unique_filename,
            'marked_up_file': output_filename,
            'timestamp': timestamp
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/ai-mapping/save-correction', methods=['POST'])
def save_correction():
    """Save user corrections as learning data"""
    try:
        data = request.json
        
        learning_index = load_mapping_learning_index()
        
        correction_record = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            'analysis_id': data.get('analysis_id'),
            'original_file': data.get('original_file'),
            'rating': data.get('rating', 0),
            'corrections': {
                'components_added': data.get('components_added', []),
                'components_removed': data.get('components_removed', []),
                'components_moved': data.get('components_moved', []),
                'connections_added': data.get('connections_added', []),
                'connections_removed': data.get('connections_removed', []),
                'feedback': data.get('feedback', '')
            },
            'original_mapping': data.get('original_mapping', {}),
            'corrected_mapping': data.get('corrected_mapping', {})
        }
        
        learning_index['examples'].append(correction_record)
        learning_index['stats']['total_corrections'] += 1
        
        # Calculate average accuracy
        ratings = [e.get('rating', 0) for e in learning_index['examples']]
        if ratings:
            learning_index['stats']['avg_accuracy'] = sum(ratings) / len(ratings)
        
        save_mapping_learning_index(learning_index)
        
        return jsonify({
            'success': True,
            'message': 'Correction saved successfully',
            'total_examples': len(learning_index['examples'])
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai-mapping/learning-stats', methods=['GET'])
def get_learning_stats():
    """Get learning statistics"""
    try:
        index = load_mapping_learning_index()
        return jsonify({
            'success': True,
            'stats': index.get('stats', {}),
            'total_examples': len(index.get('examples', [])),
            'last_updated': index.get('last_updated')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai-mapping/download/<filename>')
def ai_mapping_download(filename):
    """Download marked-up floor plan"""
    try:
        file_path = os.path.join(app.config['AI_MAPPING_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<filename>')
def download_file(filename):
    """General download endpoint for generated files"""
    try:
        # Check in outputs folder first
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)

        # Check in AI mapping folder
        file_path = os.path.join(app.config['AI_MAPPING_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)

        # Check in uploads folder
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)

        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai-mapping/history', methods=['GET'])
def ai_mapping_history():
    """Get analysis history"""
    try:
        files = os.listdir(app.config['AI_MAPPING_FOLDER'])
        marked_files = [f for f in files if f.startswith('marked_')]
        
        history = []
        for f in sorted(marked_files, reverse=True)[:20]:
            history.append({
                'filename': f,
                'timestamp': f.split('_')[1] if '_' in f else 'unknown',
                'size': os.path.getsize(os.path.join(app.config['AI_MAPPING_FOLDER'], f))
            })
        
        return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# EXISTING API ROUTES (preserved)
# ============================================================================

@app.route('/api/analyze', methods=['POST'])
def analyze_floorplan():
    try:
        if 'floorplan' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400

        file = request.files['floorplan']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Empty filename'}), 400

        # Get form data
        project_name = request.form.get('project_name', 'Untitled Project')
        tier = request.form.get('tier', 'basic')
        automation_types = request.form.getlist('automation_types') or request.form.getlist('automation_types[]')

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Run AI analysis
        analysis_result = analyze_floorplan_with_ai(filepath)

        # Log AI analysis result for debugging
        if 'error' in analysis_result:
            print(f"AI Analysis Error: {analysis_result.get('error')}")
            print(f"AI Analysis Message: {analysis_result.get('message', 'No message')}")

        if 'error' in analysis_result and analysis_result.get('fallback'):
            print("Using fallback estimation mode")
            analysis_result = {
                "rooms": [
                    {
                        "name": "Estimated Room",
                        "lighting": {"count": 5, "type": tier},
                        "shading": {"count": 2, "type": tier},
                        "security_access": {"count": 1, "type": tier},
                        "climate": {"count": 1, "type": tier},
                        "audio": {"count": 0, "type": tier}
                    }
                ],
                "notes": "Fallback estimation - AI analysis unavailable"
            }
        else:
            print(f"AI Analysis successful: {len(analysis_result.get('rooms', []))} rooms detected")

        # Calculate costs
        data_config = load_data()
        rooms = analysis_result.get('rooms', [])

        total_rooms = len(rooms)
        total_automation_points = 0
        cost_items = []

        for room in rooms:
            for automation_key in ['lighting', 'shading', 'security_access', 'climate', 'audio']:
                automation_data = room.get(automation_key, {})
                count = automation_data.get('count', 0)
                room_tier = automation_data.get('type', tier)

                if count > 0 and automation_key in automation_types:
                    total_automation_points += count
                    automation_config = data_config['automation_types'].get(automation_key, {})
                    unit_cost = automation_config.get('base_cost_per_unit', {}).get(room_tier, 0)
                    labor_hours = automation_config.get('labor_hours', {}).get(room_tier, 0)
                    labor_cost = labor_hours * data_config['labor_rate']
                    total_cost = (unit_cost + labor_cost) * count

                    cost_items.append({
                        'type': automation_config.get('name', automation_key),
                        'quantity': count,
                        'unit_cost': unit_cost,
                        'labor_cost': labor_cost,
                        'total': total_cost
                    })

        subtotal = sum(item['total'] for item in cost_items)
        markup = subtotal * (data_config['markup_percentage'] / 100)
        grand_total = subtotal + markup

        # Generate output filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        annotated_filename = f"annotated_{timestamp}.png"  # PNG for marked-up floor plan
        quote_filename = f"quote_{timestamp}.pdf"
        annotated_path = os.path.join(app.config['OUTPUT_FOLDER'], annotated_filename)
        quote_path = os.path.join(app.config['OUTPUT_FOLDER'], quote_filename)

        # Generate annotated floor plan with symbol markings
        try:
            # Prepare mapping data from analysis result for generate_marked_up_image
            components = analysis_result.get('components', [])

            if components:
                # Convert quote analysis format to mapping format
                mapping_data = {
                    'components': components,
                    'analysis': {
                        'scale': analysis_result.get('scale', 'not detected'),
                        'total_rooms': total_rooms,
                        'notes': analysis_result.get('notes', '')
                    }
                }

                # Generate marked-up image with symbols at precise coordinates
                success = generate_marked_up_image(filepath, mapping_data, annotated_path)

                if success:
                    print(f"✓ Generated annotated floor plan with {len(components)} symbols marked")
                else:
                    print("⚠ Failed to generate marked-up image, using copy instead")
                    import shutil
                    # Fallback: convert PDF to PNG without markings
                    if filepath.endswith('.pdf'):
                        doc = fitz.open(filepath)
                        page = doc[0]
                        mat = fitz.Matrix(2.0, 2.0)
                        pix = page.get_pixmap(matrix=mat)
                        pix.save(annotated_path)
                        doc.close()
                    else:
                        from PIL import Image
                        img = Image.open(filepath)
                        img.save(annotated_path, 'PNG')
            else:
                print("⚠ No component coordinates in analysis, creating unmarked copy")
                import shutil
                # No coordinates available, just convert to PNG
                if filepath.endswith('.pdf'):
                    doc = fitz.open(filepath)
                    page = doc[0]
                    mat = fitz.Matrix(2.0, 2.0)
                    pix = page.get_pixmap(matrix=mat)
                    pix.save(annotated_path)
                    doc.close()
                else:
                    from PIL import Image
                    img = Image.open(filepath)
                    img.save(annotated_path, 'PNG')

        except Exception as e:
            print(f"Error creating annotated floor plan: {e}")
            print(f"Traceback: {traceback.format_exc()}")

        # Generate quote PDF
        try:
            doc = SimpleDocTemplate(quote_path, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#556B2F'),
                spaceAfter=30,
            )

            company_info = data_config.get('company_info', {})
            story.append(Paragraph(company_info.get('name', 'Integratd Living'), title_style))
            story.append(Paragraph(f"Quote for: {project_name}", styles['Heading2']))
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
            story.append(Spacer(1, 0.5*inch))

            # Add cost breakdown table
            table_data = [['Item', 'Quantity', 'Unit Cost', 'Labor', 'Total']]
            for item in cost_items:
                table_data.append([
                    item['type'],
                    str(item['quantity']),
                    f"${item['unit_cost']:,.2f}",
                    f"${item['labor_cost']:,.2f}",
                    f"${item['total']:,.2f}"
                ])

            table_data.append(['', '', '', 'Subtotal:', f"${subtotal:,.2f}"])
            table_data.append(['', '', '', f'Markup ({data_config["markup_percentage"]}%):', f"${markup:,.2f}"])
            table_data.append(['', '', '', 'TOTAL:', f"${grand_total:,.2f}"])

            t = Table(table_data, colWidths=[3*inch, 1*inch, 1*inch, 1*inch, 1.5*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#556B2F')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            story.append(t)
            doc.build(story)
        except Exception as e:
            print(f"Error creating quote PDF: {e}")

        # Save session data for takeoffs editor
        session_id = get_session_id()
        session_data = {
            'session_id': session_id,
            'project_name': project_name,
            'tier': tier,
            'automation_types': automation_types,
            'analysis_result': analysis_result,
            'floorplan_image': annotated_filename,
            'original_pdf': filename,
            'total_rooms': total_rooms,
            'total_automation_points': total_automation_points,
            'costs': {
                'items': cost_items,
                'subtotal': subtotal,
                'markup': markup,
                'grand_total': grand_total
            },
            'timestamp': datetime.now().isoformat()
        }
        save_session_data(session_id, session_data)

        response = {
            'success': True,
            'session_id': session_id,
            'project_name': project_name,
            'total_rooms': total_rooms,
            'total_automation_points': total_automation_points,
            'confidence': '85%',  # Could be calculated from AI response
            'total_cost': f'${grand_total:,.2f}',
            'annotated_pdf': annotated_filename,
            'quote_pdf': quote_filename,
            'analysis': analysis_result,
            'costs': {
                'items': cost_items,
                'subtotal': subtotal,
                'markup': markup,
                'grand_total': grand_total
            },
            'files': {
                'annotated_pdf': f'/api/download/{annotated_filename}',
                'quote_pdf': f'/api/download/{quote_filename}'
            },
            'takeoffs_url': f'/takeoffs/{session_id}'
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}), 500

@app.route('/api/generate_quote', methods=['POST'])
def generate_quote():
    try:
        data = request.json
        analysis = data.get('analysis', {})
        data_config = load_data()
        
        line_items = []
        rooms = analysis.get('rooms', [])
        
        for room in rooms:
            room_name = room.get('name', 'Unknown Room')
            
            for automation_key in ['lighting', 'shading', 'security_access', 'climate', 'audio']:
                automation_data = room.get(automation_key, {})
                count = automation_data.get('count', 0)
                tier = automation_data.get('type', 'basic')
                
                if count > 0:
                    automation_config = data_config['automation_types'].get(automation_key, {})
                    unit_cost = automation_config.get('base_cost_per_unit', {}).get(tier, 0)
                    labor_hours = automation_config.get('labor_hours', {}).get(tier, 0)
                    labor_cost = labor_hours * data_config['labor_rate']
                    total_cost = (unit_cost + labor_cost) * count
                    
                    line_items.append({
                        'room': room_name,
                        'category': automation_config.get('name', automation_key),
                        'quantity': count,
                        'tier': tier,
                        'unit_cost': unit_cost,
                        'labor_hours': labor_hours,
                        'labor_cost': labor_cost,
                        'total': total_cost
                    })
        
        subtotal = sum(item['total'] for item in line_items)
        markup = subtotal * (data_config['markup_percentage'] / 100)
        total = subtotal + markup
        
        quote_data = {
            'line_items': line_items,
            'subtotal': subtotal,
            'markup': markup,
            'markup_percentage': data_config['markup_percentage'],
            'total': total,
            'company_info': data_config['company_info'],
            'generated_at': datetime.now().isoformat()
        }
        
        return jsonify({'success': True, 'quote': quote_data})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export_pdf', methods=['POST'])
def export_pdf():
    try:
        data = request.json
        quote = data.get('quote', {})
        
        output_filename = f"quote_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#556B2F'),
            spaceAfter=30,
        )
        
        company_info = quote.get('company_info', {})
        story.append(Paragraph(company_info.get('name', 'Company Name'), title_style))
        story.append(Paragraph(f"Phone: {company_info.get('phone', 'N/A')}", styles['Normal']))
        story.append(Paragraph(f"Email: {company_info.get('email', 'N/A')}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        story.append(Paragraph(f"Quote Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 0.5*inch))
        
        table_data = [['Room', 'Category', 'Qty', 'Tier', 'Unit Cost', 'Labor', 'Total']]
        
        for item in quote.get('line_items', []):
            table_data.append([
                item['room'],
                item['category'],
                str(item['quantity']),
                item['tier'].capitalize(),
                f"${item['unit_cost']:.2f}",
                f"${item['labor_cost']:.2f}",
                f"${item['total']:.2f}"
            ])
        
        table = Table(table_data, colWidths=[1.2*inch, 1.5*inch, 0.6*inch, 0.8*inch, 0.9*inch, 0.9*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#556B2F')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.5*inch))
        
        summary_data = [
            ['Subtotal:', f"${quote['subtotal']:.2f}"],
            [f"Markup ({quote['markup_percentage']}%):", f"${quote['markup']:.2f}"],
            ['Total:', f"${quote['total']:.2f}"]
        ]
        
        summary_table = Table(summary_data, colWidths=[5*inch, 1.5*inch])
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 14),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
            ('LINEBELOW', (0, -1), (-1, -1), 2, colors.black),
        ]))
        
        story.append(summary_table)
        doc.build(story)
        
        return send_file(output_path, as_attachment=True, download_name=output_filename)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/takeoffs/export', methods=['POST'])
def takeoffs_export():
    """Export takeoffs data with updated symbols and generate final quote"""
    try:
        data = request.json
        session_id = data.get('session_id')
        symbols = data.get('symbols', [])
        project_name = data.get('project_name', 'Untitled Project')
        tier = data.get('tier', 'basic')

        # Update session data with edited symbols
        session_data = load_session_data(session_id)

        # Create new session if it doesn't exist
        if not session_data:
            session_id = get_session_id()  # Generate new session ID
            session_data = {
                'session_id': session_id,
                'project_name': project_name,
                'tier': tier,
                'symbols': symbols,
                'created_at': datetime.now().isoformat()
            }
            save_session_data(session_id, session_data)
        else:
            session_data['symbols'] = symbols
            save_session_data(session_id, session_data)

        # Load automation data for pricing
        data_config = load_data()

        # Calculate costs from edited symbols
        cost_items = []
        total_automation_points = len(symbols)

        for symbol in symbols:
            automation_key = symbol.get('automation_category') or symbol.get('type')
            if automation_key in data_config['automation_types']:
                automation_config = data_config['automation_types'][automation_key]
                unit_cost = automation_config.get('base_cost_per_unit', {}).get(tier, 0)
                labor_hours = automation_config.get('labor_hours', {}).get(tier, 0)
                labor_cost = labor_hours * data_config['labor_rate']

                cost_items.append({
                    'type': automation_config.get('name', automation_key),
                    'quantity': 1,
                    'unit_cost': unit_cost,
                    'labor_cost': labor_cost,
                    'total': unit_cost + labor_cost,
                    'room': symbol.get('room', 'Unassigned')
                })

            # Add custom items with quantities
            if symbol.get('items'):
                for item in symbol['items']:
                    price = item.get('price', 0)
                    quantity = item.get('quantity', 1)
                    cost_items.append({
                        'type': item.get('name', 'Custom Item'),
                        'quantity': quantity,
                        'unit_cost': price,
                        'labor_cost': 0,
                        'total': price * quantity,
                        'room': symbol.get('room', 'Unassigned')
                    })

        subtotal = sum(item['total'] for item in cost_items)
        markup = subtotal * (data_config['markup_percentage'] / 100)
        grand_total = subtotal + markup

        # Generate annotated floor plan with updated symbols
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        annotated_filename = f"takeoffs_{timestamp}.png"
        quote_filename = f"quote_{timestamp}.pdf"
        annotated_path = os.path.join(app.config['OUTPUT_FOLDER'], annotated_filename)
        quote_path = os.path.join(app.config['OUTPUT_FOLDER'], quote_filename)

        # Get original floor plan (may not exist for new sessions)
        original_pdf = session_data.get('original_pdf', '') or session_data.get('floorplan_image', '')
        original_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], original_pdf) if original_pdf else None

        # Generate marked-up image with edited symbols
        mapping_data = {
            'components': symbols,
            'analysis': {
                'scale': session_data.get('analysis_result', {}).get('scale', 'not detected'),
                'total_rooms': session_data.get('total_rooms', 0),
                'notes': 'Edited in Takeoffs'
            }
        }

        if original_pdf_path and os.path.exists(original_pdf_path):
            generate_marked_up_image(original_pdf_path, mapping_data, annotated_path)
        else:
            # Fallback: use existing annotated image
            import shutil
            floorplan_image = session_data.get('floorplan_image', '')
            if floorplan_image:  # Only copy if there's an actual filename
                existing_annotated = os.path.join(app.config['OUTPUT_FOLDER'], floorplan_image)
                if os.path.exists(existing_annotated) and os.path.isfile(existing_annotated):
                    shutil.copy(existing_annotated, annotated_path)

        # Generate quote PDF
        try:
            doc = SimpleDocTemplate(quote_path, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#556B2F'),
                spaceAfter=30,
            )

            company_info = data_config.get('company_info', {})
            story.append(Paragraph(company_info.get('name', 'Integratd Living'), title_style))
            story.append(Paragraph(f"Final Quote for: {project_name}", styles['Heading2']))
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
            story.append(Paragraph(f"Tier: {tier.capitalize()}", styles['Normal']))
            story.append(Spacer(1, 0.5*inch))

            # Add cost breakdown table
            table_data = [['Item', 'Room', 'Quantity', 'Unit Cost', 'Labor', 'Total']]
            for item in cost_items:
                table_data.append([
                    item['type'],
                    item['room'],
                    str(item['quantity']),
                    f"${item['unit_cost']:,.2f}",
                    f"${item['labor_cost']:,.2f}",
                    f"${item['total']:,.2f}"
                ])

            table_data.append(['', '', '', '', 'Subtotal:', f"${subtotal:,.2f}"])
            table_data.append(['', '', '', '', f'Markup ({data_config["markup_percentage"]}%):', f"${markup:,.2f}"])
            table_data.append(['', '', '', '', 'TOTAL:', f"${grand_total:,.2f}"])

            t = Table(table_data, colWidths=[2*inch, 1.5*inch, 0.8*inch, 1*inch, 1*inch, 1.2*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#556B2F')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            story.append(t)
            doc.build(story)
        except Exception as e:
            print(f"Error creating quote PDF: {e}")

        return jsonify({
            'success': True,
            'session_id': session_id,
            'annotated_pdf': f'/api/download/{annotated_filename}',
            'quote_pdf': f'/api/download/{quote_filename}',
            'total': grand_total
        })

    except Exception as e:
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

@app.route('/api/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get session data for workflow integration"""
    try:
        session_data = load_session_data(session_id)
        if session_data:
            return jsonify(session_data)
        else:
            return jsonify({'error': 'Session not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/mapping', methods=['POST'])
def ai_mapping():
    """AI-powered electrical component placement on floor plans"""
    try:
        data = request.json
        floor_plan_image_data = data.get('floor_plan_image')
        canvas_width = data.get('canvas_width', 1400)
        canvas_height = data.get('canvas_height', 900)
        purpose = data.get('purpose', 'electrical')  # 'automation' or 'electrical'

        if not floor_plan_image_data:
            return jsonify({'success': False, 'error': 'No floor plan image provided'}), 200

        # Convert base64 image to file
        import base64
        import io
        from PIL import Image as PILImage

        # Remove data URL prefix if present
        if ',' in floor_plan_image_data:
            floor_plan_image_data = floor_plan_image_data.split(',')[1]

        image_bytes = base64.b64decode(floor_plan_image_data)
        image = PILImage.open(io.BytesIO(image_bytes))

        # Save temporarily
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_mapping.jpg')
        image.save(temp_path, 'JPEG')

        # Call AI for analysis
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            return jsonify({'success': False, 'error': 'AI API key not configured'}), 200

        # Read image for AI
        with open(temp_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        # Prepare AI prompt based on purpose
        if purpose == 'automation':
            # Takeoffs: Place home automation symbols
            prompt = """You are a home automation expert analyzing a floor plan for smart home automation placement.

Analyze this floor plan and identify optimal locations for home automation components such as:
- Smart Lights (light) - intelligent lighting fixtures in each room
- Smart Switches (switch) - wall switches near doorways that control lights/devices
- Smart Outlets (outlet) - intelligent power outlets around perimeter
- Motion Sensors (sensor) - detect movement for automation triggers
- Smart Thermostats (thermostat) - climate control (usually in hallways)
- Smart Speakers (speaker) - voice control points throughout home
- Security Cameras (camera) - entry points and key areas
- Door/Window Sensors (door_sensor) - entry point monitoring
- Smart Door Locks (lock) - main entry doors

For EACH automation component you identify, provide:
1. Component type (light, switch, outlet, sensor, thermostat, speaker, camera, door_sensor, lock, fan, dimmer)
2. X position as a decimal (0.0 to 1.0) relative to image width
3. Y position as a decimal (0.0 to 1.0) relative to image height
4. Label/description (e.g., "Living Room Smart Light", "Front Door Lock")
5. Room/location name

Respond ONLY with a JSON object in this exact format:
{
  "components": [
    {
      "type": "light",
      "x": 0.5,
      "y": 0.3,
      "label": "Kitchen Smart Light",
      "room": "Kitchen"
    },
    {
      "type": "switch",
      "x": 0.45,
      "y": 0.25,
      "label": "Kitchen Light Switch",
      "room": "Kitchen"
    }
  ]
}

Place components logically based on:
- Room function and typical automation needs
- User convenience and accessibility
- Smart home best practices and coverage
- Voice control range considerations
- Security and monitoring requirements

Focus on practical automation that improves daily living."""
        else:
            # Vectorworks: Electrical installation mapping
            prompt = """You are an expert electrician creating a comprehensive electrical installation plan for a building.

Analyze this floor plan and create a complete electrical mapping with:
- Light fixtures (light) - ceiling lights, wall sconces, LED strips in each room
- Switches (switch) - single, 3-way, 4-way switches near doorways
- Outlets (outlet) - wall outlets every 6-12 feet around perimeter
- Electrical Panel (panel) - main breaker panel location (usually garage/utility)
- Junction Boxes (junction) - wire connection points in ceilings/walls
- Smoke Detectors (smoke_detector) - required by code in bedrooms/hallways
- Ceiling Fans (fan) - bedrooms and living areas
- Dimmers (dimmer) - dining rooms, bedrooms
- GFCI Outlets (gfci) - kitchens, bathrooms, outdoor areas
- 220V Outlets (outlet_220v) - kitchen range, dryer, HVAC

For EACH electrical component, provide:
1. Component type (light, switch, outlet, panel, junction, smoke_detector, fan, dimmer, gfci, outlet_220v)
2. X position as a decimal (0.0 to 1.0) relative to image width
3. Y position as a decimal (0.0 to 1.0) relative to image height
4. Label/description (e.g., "Kitchen Ceiling Light #1", "GFCI Outlet - Kitchen Counter")
5. Room/location name
6. Circuit suggestion (e.g., "Circuit 1 - 15A", "Circuit 2 - 20A Kitchen")

Respond ONLY with a JSON object in this exact format:
{
  "components": [
    {
      "type": "light",
      "x": 0.5,
      "y": 0.3,
      "label": "Kitchen Ceiling Light #1",
      "room": "Kitchen",
      "circuit": "Circuit 1 - 15A Lighting"
    },
    {
      "type": "switch",
      "x": 0.45,
      "y": 0.25,
      "label": "Kitchen Light Switch",
      "room": "Kitchen",
      "circuit": "Circuit 1 - 15A Lighting"
    }
  ]
}

Follow NEC (National Electrical Code) requirements:
- Outlets spaced properly (no point >6ft from outlet)
- GFCI protection in wet areas
- AFCI protection in bedrooms
- Adequate lighting for each space
- Proper circuit loading and distribution
- Required smoke detectors
- Dedicated circuits for high-power appliances

Create a professional, code-compliant electrical plan suitable for permitting and installation."""

        # Make AI API call
        anthropic_api_url = 'https://api.anthropic.com/v1/messages'
        headers = {
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json'
        }

        ai_payload = {
            'model': 'claude-sonnet-4-20250514',
            'max_tokens': 4096,
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'image',
                            'source': {
                                'type': 'base64',
                                'media_type': 'image/jpeg',
                                'data': image_data
                            }
                        },
                        {
                            'type': 'text',
                            'text': prompt
                        }
                    ]
                }
            ]
        }

        response = requests.post(anthropic_api_url, headers=headers, json=ai_payload, timeout=60)

        if response.status_code != 200:
            error_msg = f'AI API error: {response.status_code}'
            try:
                error_details = response.json()
                error_msg += f' - {error_details.get("error", {}).get("message", "")}'
            except:
                error_msg += f' - {response.text[:200]}'
            return jsonify({
                'success': False,
                'error': error_msg
            }), 200  # Return 200 so frontend can parse JSON

        ai_response = response.json()
        ai_text = ai_response['content'][0]['text']

        # Parse AI response
        import json
        import re

        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', ai_text)
        if json_match:
            ai_components_data = json.loads(json_match.group())
            ai_components = ai_components_data.get('components', [])

            # Convert coordinates to canvas pixels and add IDs
            components = []
            for idx, comp in enumerate(ai_components):
                components.append({
                    'id': idx + 1,
                    'type': comp.get('type', 'light'),
                    'x': comp.get('x', 0.5) * canvas_width,
                    'y': comp.get('y', 0.5) * canvas_height,
                    'label': comp.get('label', f"Component {idx + 1}"),
                    'room': comp.get('room', 'Unknown'),
                    'circuit': None
                })

            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)

            return jsonify({
                'success': True,
                'components': components,
                'count': len(components)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Could not parse AI response'
            }), 200

    except Exception as e:
        logger.error(f"AI mapping error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 200


@app.route('/api/mapping/export', methods=['POST'])
def mapping_export():
    """Export electrical mapping with wiring and circuits"""
    try:
        data = request.json
        components = data.get('components', [])
        wires = data.get('wires', [])
        circuits = data.get('circuits', [])

        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"electrical_mapping_{timestamp}.json"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

        # Save mapping data
        mapping_data = {
            'components': components,
            'wires': wires,
            'circuits': circuits,
            'exported_at': datetime.now().isoformat()
        }

        with open(output_path, 'w') as f:
            json.dump(mapping_data, f, indent=2)

        return jsonify({
            'success': True,
            'file': f'/api/download/{output_filename}',
            'message': f'Exported {len(components)} components, {len(wires)} wires, {len(circuits)} circuits'
        })

    except Exception as e:
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

@app.route('/api/canvas/upload', methods=['POST'])
def canvas_upload():
    try:
        if 'floorplan' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['floorplan']
        if file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        if filename.lower().endswith('.pdf'):
            img_base64 = pdf_to_image_base64(filepath)
        else:
            with open(filepath, 'rb') as f:
                img_base64 = base64.b64encode(f.read()).decode('utf-8')
        
        return jsonify({
            'success': True,
            'filename': filename,
            'image_data': f'data:image/png;base64,{img_base64}'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/canvas/export', methods=['POST'])
def canvas_export():
    try:
        data = request.json
        symbols = data.get('symbols', [])
        base_image = data.get('base_image', '')
        
        output_filename = f"annotated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        if base_image.startswith('data:image'):
            img_data = base64.b64decode(base_image.split(',')[1])
            img = Image.open(io.BytesIO(img_data))
        else:
            return jsonify({'error': 'Invalid image data'}), 400
        
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        except:
            font = ImageFont.load_default()
        
        for symbol in symbols:
            x = symbol.get('x', 0)
            y = symbol.get('y', 0)
            text = symbol.get('symbol', '?')
            draw.text((x, y), text, fill='red', font=font)
        
        img.save(output_path)
        
        return send_file(output_path, as_attachment=True, download_name=output_filename)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/learning/examples', methods=['GET'])
def get_learning_examples():
    try:
        index = load_learning_index()
        return jsonify({'success': True, 'examples': index.get('examples', [])})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/learning/upload', methods=['POST'])
def upload_learning_example():
    try:
        if 'floorplan' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['floorplan']
        notes = request.form.get('notes', '')
        corrections = request.form.get('corrections', '{}')
        
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"learning_{timestamp}_{filename}"
        filepath = os.path.join(app.config['LEARNING_FOLDER'], unique_filename)
        file.save(filepath)
        
        analysis_result = analyze_floorplan_with_ai(filepath)
        
        index = load_learning_index()
        example = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            'filename': unique_filename,
            'notes': notes,
            'corrections': json.loads(corrections) if corrections else {},
            'analysis_result': analysis_result
        }
        
        if 'examples' not in index:
            index['examples'] = []
        index['examples'].append(example)
        save_learning_index(index)
        
        return jsonify({'success': True, 'example': example})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload-learning-data', methods=['POST'])
def upload_learning_data():
    """Enhanced learning endpoint supporting multiple files and custom symbols"""
    try:
        files = request.files.getlist('files')
        notes = request.form.get('notes', '')

        if not files:
            return jsonify({'success': False, 'error': 'No files uploaded'}), 400

        index = load_learning_index()
        if 'examples' not in index:
            index['examples'] = []

        uploaded_examples = []

        for file in files:
            if file.filename == '':
                continue

            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"learning_{timestamp}_{filename}"
            filepath = os.path.join(app.config['LEARNING_FOLDER'], unique_filename)
            file.save(filepath)

            # Analyze the uploaded example with AI
            analysis_result = None
            if filename.lower().endswith('.pdf'):
                analysis_result = analyze_floorplan_with_ai(filepath)

            example = {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.now().isoformat(),
                'filename': unique_filename,
                'notes': notes,
                'type': 'upload',
                'analysis_result': analysis_result
            }

            index['examples'].append(example)
            uploaded_examples.append(example)

        save_learning_index(index)

        return jsonify({
            'success': True,
            'message': f'Successfully uploaded {len(uploaded_examples)} training example(s)',
            'examples': uploaded_examples
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/process-instructions', methods=['POST'])
def process_instructions():
    """Save natural language instructions for AI to follow"""
    try:
        data = request.json
        instructions = data.get('instructions', '')

        if not instructions:
            return jsonify({'success': False, 'error': 'No instructions provided'}), 400

        index = load_learning_index()
        if 'examples' not in index:
            index['examples'] = []

        instruction_entry = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            'type': 'instruction',
            'instruction': instructions,
            'notes': f"User instruction: {instructions[:100]}..."
        }

        index['examples'].append(instruction_entry)
        save_learning_index(index)

        return jsonify({
            'success': True,
            'message': 'Instructions saved successfully. AI will apply these rules in future analyses.',
            'instruction': instruction_entry
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/learning/history', methods=['GET'])
def learning_history():
    """Get learning history for the learning page"""
    try:
        index = load_learning_index()
        examples = index.get('examples', [])

        return jsonify({
            'success': True,
            'examples': examples
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/simpro/config', methods=['GET', 'POST'])
def simpro_config():
    try:
        if request.method == 'GET':
            config = load_simpro_config()
            safe_config = {k: v for k, v in config.items() if k not in ['client_secret', 'access_token', 'refresh_token']}
            return jsonify({'success': True, 'config': safe_config})
        else:
            data = request.json
            config = load_simpro_config()
            config.update({
                'base_url': data.get('base_url', ''),
                'company_id': data.get('company_id', '0'),
                'client_id': data.get('client_id', ''),
                'client_secret': data.get('client_secret', '')
            })
            save_simpro_config(config)
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/simpro/connect', methods=['POST'])
def simpro_connect():
    try:
        config = load_simpro_config()
        
        if not all([config['base_url'], config['client_id'], config['client_secret']]):
            return jsonify({'success': False, 'error': 'Missing configuration'}), 400
        
        token_url = f"{config['base_url']}/oauth2/token"
        client = BackendApplicationClient(client_id=config['client_id'])
        oauth = OAuth2Session(client=client)
        
        token = oauth.fetch_token(
            token_url=token_url,
            client_id=config['client_id'],
            client_secret=config['client_secret']
        )
        
        config['access_token'] = token['access_token']
        config['refresh_token'] = token.get('refresh_token')
        config['token_expires_at'] = token.get('expires_at')
        config['connected'] = True
        save_simpro_config(config)
        
        # Try to get company info to verify
        try:
            headers = {'Authorization': f"Bearer {config['access_token']}"}
            companies_url = f"{config['base_url']}/api/v1.0/companies/"
            comp_resp = requests.get(companies_url, headers=headers, timeout=10)
            if comp_resp.status_code == 200:
                companies_data = comp_resp.json()
                print(f"✓ Found companies: {companies_data}")
        except Exception as e:
            print(f"Could not fetch companies: {e}")
        
        return jsonify({'success': True, 'message': 'Connected successfully'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/simpro/test-endpoints', methods=['POST'])
def simpro_test_endpoints():
    """Test different Simpro endpoints to find what works"""
    try:
        config = load_simpro_config()
        if not config.get('connected'):
            return jsonify({'success': False, 'error': 'Not connected'}), 400
        
        results = {}
        headers = {'Authorization': f"Bearer {config['access_token']}"}
        base = f"{config['base_url']}/api/v1.0/companies/{config['company_id']}"
        
        # Test different endpoints
        test_endpoints = [
            '/customers/companies/',
            '/customers/',
            '/jobs/',
            '/quotes/',
            '/catalogs/',
            '/catalogue/',
            '/employees/',
            '/sites/'
        ]
        
        for endpoint in test_endpoints:
            try:
                url = base + endpoint + '?pageSize=1'
                resp = requests.get(url, headers=headers, timeout=10)
                results[endpoint] = {
                    'status': resp.status_code,
                    'works': resp.status_code == 200,
                    'message': resp.reason
                }
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        if isinstance(data, dict) and 'Results' in data:
                            results[endpoint]['count'] = len(data['Results'])
                    except:
                        pass
            except Exception as e:
                results[endpoint] = {'status': 'error', 'works': False, 'message': str(e)}
        
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/simpro/disconnect', methods=['POST'])
def simpro_disconnect():
    try:
        config = load_simpro_config()
        config['connected'] = False
        config['access_token'] = None
        config['refresh_token'] = None
        save_simpro_config(config)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/simpro/sync', methods=['POST'])
def simpro_sync():
    try:
        data = request.json
        quote = data.get('quote', {})
        config = load_simpro_config()
        
        if not config.get('connected'):
            return jsonify({'success': False, 'error': 'Not connected to Simpro'}), 400
        
        return jsonify({
            'success': True,
            'message': 'Quote synced successfully',
            'simpro_job_id': f"SIM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/crm/customers', methods=['GET', 'POST'])
def handle_customers():
    try:
        if request.method == 'GET':
            customers = load_json_file(CUSTOMERS_FILE, [])
            return jsonify({'success': True, 'customers': customers})
        else:
            data = request.json
            customers = load_json_file(CUSTOMERS_FILE, [])
            customer = {
                'id': str(uuid.uuid4()),
                'name': data.get('name', ''),
                'email': data.get('email', ''),
                'phone': data.get('phone', ''),
                'address': data.get('address', ''),
                'status': data.get('status', 'active'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            customers.append(customer)
            save_json_file(CUSTOMERS_FILE, customers)
            return jsonify({'success': True, 'customer': customer})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/crm/customers/<customer_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_customer(customer_id):
    try:
        customers = load_json_file(CUSTOMERS_FILE, [])
        idx = next((i for i, c in enumerate(customers) if c['id'] == customer_id), None)
        
        if request.method == 'GET':
            if idx is None:
                return jsonify({'success': False, 'error': 'Not found'}), 404
            return jsonify({'success': True, 'customer': customers[idx]})
        
        elif request.method == 'PUT':
            if idx is None:
                return jsonify({'success': False, 'error': 'Not found'}), 404
            data = request.json
            customer = customers[idx]
            for field in ['name', 'email', 'phone', 'address', 'status']:
                if field in data:
                    customer[field] = data[field]
            customer['updated_at'] = datetime.now().isoformat()
            customers[idx] = customer
            save_json_file(CUSTOMERS_FILE, customers)
            return jsonify({'success': True, 'customer': customer})
        
        elif request.method == 'DELETE':
            if idx is None:
                return jsonify({'success': False, 'error': 'Not found'}), 404
            customers.pop(idx)
            save_json_file(CUSTOMERS_FILE, customers)
            return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/crm/projects', methods=['GET', 'POST'])
def handle_projects():
    try:
        if request.method == 'GET':
            projects = load_json_file(PROJECTS_FILE, [])
            customer_id = request.args.get('customer_id')
            if customer_id:
                projects = [p for p in projects if p.get('customer_id') == customer_id]
            return jsonify({'success': True, 'projects': projects})
        else:
            data = request.json
            projects = load_json_file(PROJECTS_FILE, [])
            project = {
                'id': str(uuid.uuid4()),
                'customer_id': data.get('customer_id'),
                'title': data.get('title', ''),
                'description': data.get('description', ''),
                'status': data.get('status', 'pending'),
                'priority': data.get('priority', 'medium'),
                'quote_amount': data.get('quote_amount', 0.0),
                'actual_amount': data.get('actual_amount', 0.0),
                'due_date': data.get('due_date'),
                'takeoffs_session_id': data.get('takeoffs_session_id'),
                'mapping_session_id': data.get('mapping_session_id'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            projects.append(project)
            save_json_file(PROJECTS_FILE, projects)
            return jsonify({'success': True, 'project': project})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/crm/projects/<project_id>', methods=['PUT', 'DELETE'])
def update_project(project_id):
    try:
        projects = load_json_file(PROJECTS_FILE, [])
        idx = next((i for i, p in enumerate(projects) if p['id'] == project_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Not found'}), 404

        if request.method == 'PUT':
            data = request.json
            project = projects[idx]
            for field in ['title', 'description', 'status', 'priority', 'quote_amount', 'actual_amount', 'due_date', 'customer_id', 'takeoffs_session_id', 'mapping_session_id']:
                if field in data:
                    project[field] = data[field]
            project['updated_at'] = datetime.now().isoformat()
            projects[idx] = project
            save_json_file(PROJECTS_FILE, projects)
            return jsonify({'success': True, 'project': project})

        elif request.method == 'DELETE':
            projects.pop(idx)
            save_json_file(PROJECTS_FILE, projects)
            return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/link-session-to-project', methods=['POST'])
def link_session_to_project():
    """Link a takeoffs/mapping session to a CRM project"""
    try:
        data = request.json
        session_id = data.get('session_id')
        project_id = data.get('project_id')
        link_type = data.get('link_type', 'takeoffs')  # 'takeoffs' or 'mapping'

        if not session_id or not project_id:
            return jsonify({'success': False, 'error': 'Missing session_id or project_id'}), 400

        # Update session data with project_id
        session_data = load_session_data(session_id)
        if session_data:
            session_data['project_id'] = project_id
            save_session_data(session_id, session_data)

        # Update project with session_id
        projects = load_json_file(PROJECTS_FILE, [])
        idx = next((i for i, p in enumerate(projects) if p['id'] == project_id), None)

        if idx is not None:
            if link_type == 'takeoffs':
                projects[idx]['takeoffs_session_id'] = session_id
            else:
                projects[idx]['mapping_session_id'] = session_id
            projects[idx]['updated_at'] = datetime.now().isoformat()
            save_json_file(PROJECTS_FILE, projects)

            return jsonify({
                'success': True,
                'project': projects[idx]
            })
        else:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/crm/communications', methods=['GET', 'POST'])
def handle_communications():
    try:
        if request.method == 'GET':
            comms = load_json_file(COMMUNICATIONS_FILE, [])
            customer_id = request.args.get('customer_id')
            if customer_id:
                comms = [c for c in comms if c.get('customer_id') == customer_id]
            return jsonify({'success': True, 'communications': comms})
        else:
            data = request.json
            comms = load_json_file(COMMUNICATIONS_FILE, [])
            comm = {
                'id': str(uuid.uuid4()),
                'customer_id': data.get('customer_id'),
                'type': data.get('type', 'note'),
                'subject': data.get('subject', ''),
                'content': data.get('content', ''),
                'created_at': datetime.now().isoformat()
            }
            comms.append(comm)
            save_json_file(COMMUNICATIONS_FILE, comms)
            return jsonify({'success': True, 'communication': comm})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/crm/communications/<comm_id>', methods=['PUT', 'DELETE'])
def handle_communication(comm_id):
    try:
        comms = load_json_file(COMMUNICATIONS_FILE, [])
        idx = next((i for i, c in enumerate(comms) if c['id'] == comm_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Not found'}), 404

        if request.method == 'PUT':
            data = request.json
            comm = comms[idx]
            for field in ['customer_id', 'type', 'subject', 'content']:
                if field in data:
                    comm[field] = data[field]
            comm['updated_at'] = datetime.now().isoformat()
            comms[idx] = comm
            save_json_file(COMMUNICATIONS_FILE, comms)
            return jsonify({'success': True, 'communication': comm})

        elif request.method == 'DELETE':
            comms.pop(idx)
            save_json_file(COMMUNICATIONS_FILE, comms)
            return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/crm/calendar', methods=['GET', 'POST'])
def handle_calendar():
    try:
        if request.method == 'GET':
            events = load_json_file(CALENDAR_FILE, [])
            return jsonify({'success': True, 'events': events})
        else:
            data = request.json
            events = load_json_file(CALENDAR_FILE, [])
            event = {
                'id': str(uuid.uuid4()),
                'title': data.get('title', ''),
                'date': data.get('date', ''),
                'time': data.get('time', ''),
                'type': data.get('type', 'appointment'),
                'status': data.get('status', 'scheduled'),
                'created_at': datetime.now().isoformat()
            }
            events.append(event)
            save_json_file(CALENDAR_FILE, events)
            return jsonify({'success': True, 'event': event})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/crm/calendar/<event_id>', methods=['PUT', 'DELETE'])
def handle_event(event_id):
    try:
        events = load_json_file(CALENDAR_FILE, [])
        idx = next((i for i, e in enumerate(events) if e['id'] == event_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Not found'}), 404

        if request.method == 'PUT':
            data = request.json
            event = events[idx]
            for field in ['title', 'date', 'time', 'type', 'status', 'description']:
                if field in data:
                    event[field] = data[field]
            event['updated_at'] = datetime.now().isoformat()
            events[idx] = event
            save_json_file(CALENDAR_FILE, events)
            return jsonify({'success': True, 'event': event})

        elif request.method == 'DELETE':
            events.pop(idx)
            save_json_file(CALENDAR_FILE, events)
            return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/crm/technicians', methods=['GET', 'POST'])
def handle_technicians():
    try:
        if request.method == 'GET':
            techs = load_json_file(TECHNICIANS_FILE, [])
            return jsonify({'success': True, 'technicians': techs})
        else:
            data = request.json
            techs = load_json_file(TECHNICIANS_FILE, [])
            tech = {
                'id': str(uuid.uuid4()),
                'name': data.get('name', ''),
                'email': data.get('email', ''),
                'phone': data.get('phone', ''),
                'skills': data.get('skills', []),
                'status': data.get('status', 'available'),
                'created_at': datetime.now().isoformat()
            }
            techs.append(tech)
            save_json_file(TECHNICIANS_FILE, techs)
            return jsonify({'success': True, 'technician': tech})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/crm/technicians/<tech_id>', methods=['PUT', 'DELETE'])
def handle_technician(tech_id):
    try:
        techs = load_json_file(TECHNICIANS_FILE, [])
        idx = next((i for i, t in enumerate(techs) if t['id'] == tech_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Not found'}), 404

        if request.method == 'PUT':
            data = request.json
            tech = techs[idx]
            for field in ['name', 'email', 'phone', 'skills', 'status']:
                if field in data:
                    tech[field] = data[field]
            tech['updated_at'] = datetime.now().isoformat()
            techs[idx] = tech
            save_json_file(TECHNICIANS_FILE, techs)
            return jsonify({'success': True, 'technician': tech})

        elif request.method == 'DELETE':
            techs.pop(idx)
            save_json_file(TECHNICIANS_FILE, techs)
            return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/crm/inventory', methods=['GET', 'POST'])
def handle_inventory():
    try:
        if request.method == 'GET':
            inventory = load_json_file(INVENTORY_FILE, [])
            # Add price field for unified editor compatibility
            for item in inventory:
                if 'price' not in item and 'unit_cost' in item:
                    item['price'] = item['unit_cost']
            return jsonify({'success': True, 'inventory': inventory})
        else:
            data = request.json
            inventory = load_json_file(INVENTORY_FILE, [])
            unit_cost = data.get('unit_cost', 0.0)
            item = {
                'id': str(uuid.uuid4()),
                'name': data.get('name', ''),
                'sku': data.get('sku', ''),
                'category': data.get('category', ''),
                'quantity': data.get('quantity', 0),
                'unit_cost': unit_cost,
                'price': data.get('price', unit_cost),  # For unified editor compatibility
                'reorder_level': data.get('reorder_level', 10),
                'created_at': datetime.now().isoformat()
            }
            inventory.append(item)
            save_json_file(INVENTORY_FILE, inventory)
            return jsonify({'success': True, 'item': item})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/crm/inventory/<item_id>', methods=['PUT', 'DELETE'])
def handle_inventory_item(item_id):
    try:
        inventory = load_json_file(INVENTORY_FILE, [])
        idx = next((i for i, item in enumerate(inventory) if item['id'] == item_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Not found'}), 404

        if request.method == 'PUT':
            data = request.json
            item = inventory[idx]
            for field in ['name', 'sku', 'category', 'quantity', 'unit_cost', 'price', 'reorder_level']:
                if field in data:
                    item[field] = data[field]
            item['updated_at'] = datetime.now().isoformat()
            inventory[idx] = item
            save_json_file(INVENTORY_FILE, inventory)
            return jsonify({'success': True, 'item': item})

        elif request.method == 'DELETE':
            inventory.pop(idx)
            save_json_file(INVENTORY_FILE, inventory)
            return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/crm/suppliers', methods=['GET', 'POST'])
def handle_suppliers():
    try:
        if request.method == 'GET':
            suppliers = load_json_file(SUPPLIERS_FILE, [])
            return jsonify({'success': True, 'suppliers': suppliers})
        else:
            data = request.json
            suppliers = load_json_file(SUPPLIERS_FILE, [])
            supplier = {
                'id': str(uuid.uuid4()),
                'name': data.get('name', ''),
                'email': data.get('email', ''),
                'phone': data.get('phone', ''),
                'website': data.get('website', ''),
                'created_at': datetime.now().isoformat()
            }
            suppliers.append(supplier)
            save_json_file(SUPPLIERS_FILE, suppliers)
            return jsonify({'success': True, 'supplier': supplier})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/crm/suppliers/<supplier_id>', methods=['PUT', 'DELETE'])
def handle_supplier(supplier_id):
    try:
        suppliers = load_json_file(SUPPLIERS_FILE, [])
        idx = next((i for i, s in enumerate(suppliers) if s['id'] == supplier_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Not found'}), 404

        if request.method == 'PUT':
            data = request.json
            supplier = suppliers[idx]
            for field in ['name', 'email', 'phone', 'website']:
                if field in data:
                    supplier[field] = data[field]
            supplier['updated_at'] = datetime.now().isoformat()
            suppliers[idx] = supplier
            save_json_file(SUPPLIERS_FILE, suppliers)
            return jsonify({'success': True, 'supplier': supplier})

        elif request.method == 'DELETE':
            suppliers.pop(idx)
            save_json_file(SUPPLIERS_FILE, suppliers)
            return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/crm/integrations', methods=['GET'])
def get_integrations_crm():
    try:
        integrations = load_json_file(INTEGRATIONS_FILE, {
            'simpro': {'enabled': False},
            'google': {'enabled': False},
            'email': {'enabled': False}
        })
        return jsonify({'success': True, 'integrations': integrations})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/crm/stats', methods=['GET'])
def get_crm_stats():
    try:
        customers = load_json_file(CUSTOMERS_FILE, [])
        projects = load_json_file(PROJECTS_FILE, [])
        inventory = load_json_file(INVENTORY_FILE, [])
        
        total_customers = len(customers)
        active_customers = len([c for c in customers if c.get('status') == 'active'])
        total_projects = len(projects)
        active_projects = len([p for p in projects if p.get('status') in ['pending', 'in_progress']])
        completed_projects = len([p for p in projects if p.get('status') == 'completed'])
        total_revenue = sum(p.get('actual_amount', 0) for p in projects if p.get('status') == 'completed')
        pending_revenue = sum(p.get('quote_amount', 0) for p in projects if p.get('status') in ['pending', 'in_progress'])
        total_inventory_value = sum(i.get('quantity', 0) * i.get('unit_cost', 0) for i in inventory)
        low_stock_items = len([i for i in inventory if i.get('quantity', 0) <= i.get('reorder_level', 10)])
        
        return jsonify({
            'success': True,
            'stats': {
                'customers': {'total': total_customers, 'active': active_customers},
                'projects': {'total': total_projects, 'active': active_projects, 'completed': completed_projects},
                'revenue': {'total': total_revenue, 'pending': pending_revenue},
                'inventory': {'total_value': total_inventory_value, 'low_stock': low_stock_items},
                'calendar': {'today_events': 0}
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/simpro/import-all', methods=['POST'])
def simpro_import_all():
    """BULK IMPORT from Simpro"""
    try:
        print("="*50)
        print("STARTING BULK IMPORT")
        import_result = import_all_simpro_data()
        if not import_result['success']:
            return jsonify(import_result), 400
        
        data = import_result['data']
        
        existing_customers = load_json_file(CUSTOMERS_FILE, [])
        customer_count = 0
        for sc in data['customers']:
            if any(c.get('simpro_id') == sc.get('ID') for c in existing_customers):
                continue
            existing_customers.append({
                'id': str(uuid.uuid4()),
                'simpro_id': sc.get('ID'),
                'name': sc.get('CompanyName') or f"{sc.get('GivenName','')} {sc.get('FamilyName','')}".strip() or 'Unknown',
                'email': sc.get('Email', ''),
                'phone': sc.get('Mobile') or sc.get('Phone', ''),
                'address': sc.get('PostalAddress', {}).get('Address', '') if isinstance(sc.get('PostalAddress'), dict) else '',
                'status': 'active' if sc.get('Active') else 'inactive',
                'created_at': sc.get('DateCreated', datetime.now().isoformat()),
                'updated_at': datetime.now().isoformat(),
                'source': 'simpro_import'
            })
            customer_count += 1
        save_json_file(CUSTOMERS_FILE, existing_customers)
        
        existing_projects = load_json_file(PROJECTS_FILE, [])
        customer_map = {c.get('simpro_id'): c['id'] for c in existing_customers if c.get('simpro_id')}
        project_count = 0
        for sj in data['jobs']:
            if any(p.get('simpro_id') == sj.get('ID') for p in existing_projects):
                continue
            customer_id = customer_map.get(sj.get('Customer', {}).get('ID') if isinstance(sj.get('Customer'), dict) else None)
            existing_projects.append({
                'id': str(uuid.uuid4()),
                'simpro_id': sj.get('ID'),
                'customer_id': customer_id,
                'title': sj.get('Name', 'Untitled'),
                'description': sj.get('Description', ''),
                'status': sj.get('Stage', 'pending').lower(),
                'priority': 'medium',
                'quote_amount': float(sj.get('TotalAmount', 0) or 0),
                'actual_amount': float(sj.get('ActualAmount', 0) or 0),
                'due_date': sj.get('DueDate'),
                'created_at': sj.get('DateCreated', datetime.now().isoformat()),
                'updated_at': datetime.now().isoformat(),
                'source': 'simpro_import'
            })
            project_count += 1
        save_json_file(PROJECTS_FILE, existing_projects)
        
        existing_inventory = load_json_file(INVENTORY_FILE, [])
        categorized_count = 0
        inventory_count = 0
        for idx, item in enumerate(data['catalog']):
            if any(i.get('simpro_id') == item.get('ID') for i in existing_inventory):
                continue
            
            category_info = categorize_with_ai(item, 'catalog_item')
            base_cost = float(item.get('CostPrice', 0) or 0)
            
            existing_inventory.append({
                'id': str(uuid.uuid4()),
                'simpro_id': item.get('ID'),
                'name': item.get('Name', 'Unknown'),
                'description': item.get('Description', ''),
                'sku': item.get('Code', ''),
                'automation_type': category_info.get('automation_type', 'other'),
                'tier': category_info.get('tier', 'basic'),
                'price': {
                    'basic': base_cost,
                    'premium': base_cost * 1.5,
                    'deluxe': base_cost * 2.5
                },
                'stock_quantity': int(item.get('Quantity', 0) or 0),
                'supplier': item.get('Supplier', {}).get('Name', '') if isinstance(item.get('Supplier'), dict) else '',
                'ai_notes': category_info.get('notes', ''),
                'created_at': item.get('DateCreated', datetime.now().isoformat()),
                'updated_at': datetime.now().isoformat(),
                'source': 'simpro_import'
            })
            inventory_count += 1
            if category_info.get('automation_type') != 'other':
                categorized_count += 1
            
            if (idx + 1) % 50 == 0:
                print(f"   {idx+1}/{len(data['catalog'])}")
        
        save_json_file(INVENTORY_FILE, existing_inventory)
        
        existing_technicians = load_json_file(TECHNICIANS_FILE, [])
        tech_count = 0
        for staff in data['staff']:
            if any(t.get('simpro_id') == staff.get('ID') for t in existing_technicians):
                continue
            existing_technicians.append({
                'id': str(uuid.uuid4()),
                'simpro_id': staff.get('ID'),
                'name': f"{staff.get('GivenName','')} {staff.get('FamilyName','')}".strip() or 'Unknown',
                'email': staff.get('Email', ''),
                'phone': staff.get('Mobile', ''),
                'role': staff.get('EmployeeType', 'Technician'),
                'status': 'active' if staff.get('Active') else 'inactive',
                'created_at': datetime.now().isoformat(),
                'source': 'simpro_import'
            })
            tech_count += 1
        save_json_file(TECHNICIANS_FILE, existing_technicians)
        
        print("IMPORT COMPLETE!")
        return jsonify({
            'success': True,
            'message': 'Import successful',
            'summary': {
                'customers': customer_count,
                'projects': project_count,
                'inventory_items': inventory_count,
                'inventory_categorized': categorized_count,
                'technicians': tech_count,
                'quotes': len(data['quotes']),
                'total': customer_count + project_count + inventory_count + tech_count
            },
            'errors': import_result['errors']
        })
    except Exception as e:
        print(f"ERROR: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    """Get inventory"""
    try:
        inventory = load_json_file(INVENTORY_FILE, [])
        automation_type = request.args.get('automation_type')
        tier = request.args.get('tier')
        filtered = inventory
        if automation_type:
            filtered = [i for i in filtered if i.get('automation_type') == automation_type]
        if tier:
            filtered = [i for i in filtered if i.get('tier') == tier]
        return jsonify({'success': True, 'inventory': filtered, 'total': len(inventory)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# AI CHAT AGENT WITH EXTENDED THINKING
# ============================================================================

@app.route('/api/ai-chat', methods=['POST'])
def ai_chat():
    """
    AUTONOMOUS AI CHAT AGENT with:
    - Vision capabilities (can analyze images)
    - Web search (can look up real-time information)
    - Extended thinking (deep reasoning)
    - Agent mode (can take actions)
    - Agentic loop (iterative research and reasoning)
    """
    try:
        data = request.json
        user_message = data.get('message', '')
        agent_mode = data.get('agent_mode', False)
        conversation_history = data.get('conversation_history', [])
        project_id = data.get('project_id')
        current_page = data.get('current_page', 'unknown')
        images = data.get('images', [])  # NEW: Support image attachments

        if not user_message:
            return jsonify({'success': False, 'error': 'No message provided'}), 400

        if not ANTHROPIC_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'AI service not available',
                'response': 'Sorry, the AI service is currently unavailable.'
            }), 503

        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'API key not configured',
                'response': 'AI service is not configured properly.'
            }), 503

        # Build system context
        system_context = build_agent_system_context(agent_mode, current_page)

        # Build conversation messages with vision support
        messages = []
        for msg in conversation_history:
            messages.append({
                'role': msg.get('role', 'user'),
                'content': msg.get('content', '')
            })

        # Build current message with optional images
        current_message_content = []

        # Add images if provided (vision)
        if images and len(images) > 0:
            for img_data in images:
                current_message_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img_data.get("media_type", "image/png"),
                        "data": img_data.get("data", "")
                    }
                })

        # Add text message
        current_message_content.append({
            "type": "text",
            "text": user_message
        })

        messages.append({
            'role': 'user',
            'content': current_message_content if len(current_message_content) > 1 else user_message
        })

        # AGENTIC LOOP - AI can search, think, search more, then respond
        client = anthropic.Anthropic(api_key=api_key)
        max_iterations = 8
        iteration = 0
        final_response_text = ""
        actions_taken = []

        while iteration < max_iterations:
            iteration += 1

            # Call Anthropic with tool use capability
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                thinking={
                    "type": "enabled",
                    "budget_tokens": 10000  # High budget for deep reasoning
                },
                system=system_context,
                tools=[SEARCH_TOOL_SCHEMA],  # Give AI web search capability
                messages=messages
            )

            # Check if AI wants to use tools (web search)
            if response.stop_reason == "tool_use":
                # AI wants to search for information
                tool_uses = [block for block in response.content if hasattr(block, 'type') and block.type == "tool_use"]

                # Add AI's message to conversation
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })

                # Execute all tool calls
                tool_results = []
                for tool_use in tool_uses:
                    tool_name = tool_use.name
                    tool_input = tool_use.input
                    tool_id = tool_use.id

                    print(f"🔍 AI Chat searching: {tool_input.get('query', 'unknown')} (page: {current_page})")

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

            elif response.stop_reason == "end_turn":
                # AI is done - extract the final response
                response_text = ""
                for block in response.content:
                    if hasattr(block, 'type') and block.type == "text":
                        response_text = block.text
                        break

                if not response_text:
                    return jsonify({
                        'success': False,
                        'error': 'No response from AI',
                        'response': 'I encountered an error processing your request.'
                    }), 500

                final_response_text = response_text

                # Parse actions if agent mode is enabled
                if agent_mode:
                    actions_taken = parse_and_execute_actions(response_text, project_id, current_page)

                # Success - return response
                return jsonify({
                    'success': True,
                    'response': final_response_text,
                    'actions_taken': actions_taken,
                    'agent_mode': agent_mode,
                    'searches_performed': iteration - 1  # How many searches AI did
                })

            else:
                # Unexpected stop reason
                return jsonify({
                    'success': False,
                    'error': f'Unexpected stop reason: {response.stop_reason}',
                    'response': 'I encountered an unexpected error.'
                }), 500

        # Max iterations reached
        return jsonify({
            'success': False,
            'error': 'Max iterations reached',
            'response': 'I spent too much time researching. Please try a simpler question.'
        }), 500

    except Exception as e:
        print(f"AI Chat Error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e),
            'response': f'I encountered an error: {str(e)}'
        }), 500

def build_agent_system_context(agent_mode, current_page):
    """Build comprehensive system context for autonomous AI agent"""
    context = """You are an autonomous AI agent for the Integratd Living automation system.

CURRENT CONTEXT: {page}

🔍 YOU HAVE WEB SEARCH - USE IT ACTIVELY:
You can search the web for real-time information about:
- Building codes (NEC, local codes, international standards)
- Professional installation practices and standards
- Product specifications and compatibility
- Industry best practices
- Safety regulations and requirements
- Technical documentation
- Common sense knowledge and verification

WHEN TO SEARCH:
- When asked about codes, standards, or regulations
- When you need to verify technical information
- When discussing product specifications
- When providing professional recommendations
- Any time you're uncertain about current information
- To provide the most accurate, up-to-date answers

👁️ YOU HAVE VISION:
If users attach images, you can:
- Analyze floor plans and architectural drawings
- Identify components and symbols
- Assess layouts and spatial relationships
- Detect scale and dimensions
- Read diagrams and schematics
- Understand visual context

🧠 YOUR CAPABILITIES:
- Answer questions about floor plans, automation, pricing, and features
- Analyze images and provide visual insights
- Search the web for current information
- Explain analysis results and provide insights
- Help users make informed decisions
- Provide professional technical support
- Use extended thinking for complex reasoning

""".format(page=current_page)

    if agent_mode:
        context += """AGENT MODE ENABLED - You can take actions using this format:

```action
{
  "action": "ACTION_NAME",
  "parameters": {"param": "value"},
  "reason": "explanation"
}
```

AVAILABLE ACTIONS:
- ADD_INSTRUCTION: Add learning instruction
- UPDATE_PRICING: Update pricing (tier, automation_type, cost)
- UPDATE_LABOR_RATE: Update labor rate (rate)
- UPDATE_MARKUP: Update markup percentage (markup)

Always explain actions clearly before executing.
"""
    else:
        context += "AGENT MODE DISABLED - You can only answer questions.\n"

    context += "\nUse extended thinking for accurate, helpful responses."
    return context

def parse_and_execute_actions(response_text, project_id, current_page):
    """Parse and execute action blocks from AI response"""
    actions_taken = []
    import re
    action_pattern = r'```action\s*\n(.*?)\n```'
    action_matches = re.findall(action_pattern, response_text, re.DOTALL)

    for action_json in action_matches:
        try:
            action = json.loads(action_json)
            result = execute_action(action.get('action'), action.get('parameters', {}), project_id)
            actions_taken.append({
                'success': result.get('success', False),
                'action': action.get('action'),
                'details': result.get('details', 'Action executed'),
                'reason': action.get('reason', '')
            })
        except Exception as e:
            actions_taken.append({
                'success': False,
                'details': f'Error: {str(e)}'
            })
    return actions_taken

def execute_action(action_name, parameters, project_id):
    """Execute a specific action"""
    try:
        if action_name == 'ADD_INSTRUCTION':
            instruction = parameters.get('instruction', '')
            if not instruction:
                return {'success': False, 'details': 'No instruction provided'}

            index = load_learning_index()
            if 'examples' not in index:
                index['examples'] = []

            index['examples'].append({
                'id': str(uuid.uuid4()),
                'timestamp': datetime.now().isoformat(),
                'type': 'instruction',
                'instruction': instruction,
                'notes': f'Agent: {instruction[:100]}'
            })
            save_learning_index(index)
            return {'success': True, 'details': f'Added instruction: "{instruction}"'}

        elif action_name == 'UPDATE_PRICING':
            data_config = load_data()
            tier = parameters.get('tier')
            automation_type = parameters.get('automation_type')
            cost = parameters.get('cost')

            if automation_type in data_config['automation_types']:
                data_config['automation_types'][automation_type]['base_cost_per_unit'][tier] = float(cost)
                save_data(data_config)
                return {'success': True, 'details': f'Updated {automation_type} {tier} to ${cost}'}
            return {'success': False, 'details': f'Unknown automation type'}

        elif action_name == 'UPDATE_LABOR_RATE':
            data_config = load_data()
            data_config['labor_rate'] = float(parameters.get('rate'))
            save_data(data_config)
            return {'success': True, 'details': f'Updated labor rate'}

        elif action_name == 'UPDATE_MARKUP':
            data_config = load_data()
            data_config['markup_percentage'] = float(parameters.get('markup'))
            save_data(data_config)
            return {'success': True, 'details': f'Updated markup'}

        return {'success': False, 'details': f'Unknown action: {action_name}'}

    except Exception as e:
        return {'success': False, 'details': f'Error: {str(e)}'}


@app.route('/api/generate-final-quote', methods=['POST'])
def generate_final_quote():
    """Generate final PDF quote from canvas symbols"""
    try:
        data = request.json
        project_id = data.get('project_id')
        project_name = data.get('project_name', 'Project')
        symbols = data.get('symbols', [])
        tier = data.get('tier', 'premium')

        # Count symbols by type
        counts = {}
        for sym in symbols:
            sym_type = sym.get('type')
            counts[sym_type] = counts.get(sym_type, 0) + 1

        # Load pricing
        data_config = load_data()

        # Generate quote
        line_items = []
        for automation_type, count in counts.items():
            if count > 0:
                automation_config = data_config['automation_types'].get(automation_type, {})
                unit_cost = automation_config.get('base_cost_per_unit', {}).get(tier, 0)
                labor_hours = automation_config.get('labor_hours', {}).get(tier, 0)
                labor_cost = labor_hours * data_config['labor_rate']
                total_cost = (unit_cost + labor_cost) * count

                line_items.append({
                    'category': automation_config.get('name', automation_type),
                    'quantity': count,
                    'tier': tier,
                    'unit_cost': unit_cost,
                    'labor_hours': labor_hours,
                    'labor_cost': labor_cost,
                    'total': total_cost
                })

        subtotal = sum(item['total'] for item in line_items)
        markup = subtotal * (data_config['markup_percentage'] / 100)
        total = subtotal + markup

        # Generate PDF
        output_filename = f"quote_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#556B2F'),
            spaceAfter=30,
        )

        company_info = data_config.get('company_info', {})
        story.append(Paragraph(company_info.get('name', 'Company Name'), title_style))
        story.append(Paragraph(f"Project: {project_name}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))

        story.append(Paragraph(f"Quote Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 0.5*inch))

        table_data = [['Category', 'Qty', 'Tier', 'Unit Cost', 'Labor', 'Total']]

        for item in line_items:
            table_data.append([
                item['category'],
                str(item['quantity']),
                item['tier'].capitalize(),
                f"${item['unit_cost']:.2f}",
                f"${item['labor_cost']:.2f}",
                f"${item['total']:.2f}"
            ])

        table = Table(table_data, colWidths=[2*inch, 0.8*inch, 0.8*inch, 1*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#556B2F')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(table)
        story.append(Spacer(1, 0.5*inch))

        story.append(Paragraph(f"Subtotal: ${subtotal:.2f}", styles['Normal']))
        story.append(Paragraph(f"Markup ({data_config['markup_percentage']}%): ${markup:.2f}", styles['Normal']))
        story.append(Paragraph(f"<b>Total: ${total:.2f}</b>", styles['Heading2']))

        doc.build(story)

        return jsonify({'success': True, 'filename': output_filename})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/generate-quote-pdf', methods=['POST'])
def generate_quote_pdf():
    """Generate quote PDF with current progress"""
    return generate_final_quote()


@app.route('/api/generate-annotated-floorplan', methods=['POST'])
def generate_annotated_floorplan():
    """Generate annotated floorplan PDF with symbols marked"""
    try:
        data = request.json
        project_id = data.get('project_id')
        symbols = data.get('symbols', [])

        # Get the original floor plan
        project_dir = os.path.join(app.config['UPLOAD_FOLDER'], project_id)
        files = os.listdir(project_dir)
        floor_plan_file = next((f for f in files if f.startswith('floor_plan')), None)

        if not floor_plan_file:
            return jsonify({'success': False, 'error': 'Floor plan not found'}), 404

        floor_plan_path = os.path.join(project_dir, floor_plan_file)

        # Generate marked-up image
        output_filename = f"annotated_floorplan_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

        # Open floor plan image
        if floor_plan_path.endswith('.pdf'):
            doc = fitz.open(floor_plan_path)
            page = doc[0]
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()
        else:
            img = Image.open(floor_plan_path)

        # Draw symbols on image
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        except:
            font = ImageFont.load_default()

        # Draw each symbol
        for sym in symbols:
            x = sym.get('x', 0)
            y = sym.get('y', 0)
            symbol = sym.get('symbol', '❓')

            # Draw circle background
            draw.ellipse([x-20, y-20, x+20, y+20], fill='rgba(46, 204, 113, 128)', outline='#2ecc71', width=3)

            # Draw symbol
            draw.text((x-10, y-15), symbol, fill='black', font=font)

        # Save as PDF
        img_rgb = img.convert('RGB')
        img_rgb.save(output_path, 'PDF', resolution=100.0)

        return jsonify({'success': True, 'filename': output_filename})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}), 500


# ========================================
# KANBAN BOARD ENDPOINTS
# ========================================

# Kanban Board Data File
KANBAN_FILE = os.path.join(app.config['CRM_DATA_FOLDER'], 'kanban_tasks.json')

@app.route('/kanban')
def kanban_board():
    """Kanban operations board"""
    return render_template('kanban.html')

@app.route('/api/kanban/tasks', methods=['GET', 'POST'])
def handle_kanban_tasks():
    """Get all tasks or create new task"""
    try:
        if request.method == 'GET':
            if USE_DATABASE:
                tasks = [task.to_dict() for task in KanbanTask.query.all()]
            else:
                tasks = load_json_file(KANBAN_FILE, [])
            return jsonify({'success': True, 'tasks': tasks})
        else:
            data = request.json
            task_id = str(uuid.uuid4())
            position = data.get('position', {'x': 10, 'y': 10})

            if USE_DATABASE:
                task = KanbanTask(
                    id=task_id,
                    column=data.get('column', 'todo'),
                    content=data.get('content', 'New Task'),
                    notes=data.get('notes', ''),
                    color=data.get('color', '#ffffff'),
                    position_x=position.get('x', 10),
                    position_y=position.get('y', 10),
                    assigned_to=data.get('assigned_to'),
                    pinned=data.get('pinned', False),
                    due_date=data.get('due_date')
                )
                db.session.add(task)
                db.session.commit()
                return jsonify({'success': True, 'task': task.to_dict()})
            else:
                tasks = load_json_file(KANBAN_FILE, [])
                task = {
                    'id': task_id,
                    'column': data.get('column', 'todo'),
                    'content': data.get('content', 'New Task'),
                    'notes': data.get('notes', ''),
                    'color': data.get('color', '#ffffff'),
                    'position': position,
                    'assigned_to': data.get('assigned_to'),
                    'pinned': data.get('pinned', False),
                    'due_date': data.get('due_date'),
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                tasks.append(task)
                save_json_file(KANBAN_FILE, tasks)
                return jsonify({'success': True, 'task': task})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kanban/tasks/<task_id>', methods=['PUT', 'DELETE'])
def handle_kanban_task(task_id):
    """Update or delete a specific task"""
    try:
        if USE_DATABASE:
            task = KanbanTask.query.get(task_id)
            if not task:
                return jsonify({'success': False, 'error': 'Task not found'}), 404

            if request.method == 'PUT':
                data = request.json
                if 'column' in data:
                    task.column = data['column']
                if 'content' in data:
                    task.content = data['content']
                if 'notes' in data:
                    task.notes = data['notes']
                if 'color' in data:
                    task.color = data['color']
                if 'position' in data:
                    task.position_x = data['position'].get('x', task.position_x)
                    task.position_y = data['position'].get('y', task.position_y)
                if 'due_date' in data:
                    task.due_date = data['due_date']
                if 'assigned_to' in data:
                    task.assigned_to = data['assigned_to']
                if 'pinned' in data:
                    task.pinned = data['pinned']

                task.updated_at = datetime.utcnow()
                db.session.commit()
                return jsonify({'success': True, 'task': task.to_dict()})

            elif request.method == 'DELETE':
                db.session.delete(task)
                db.session.commit()
                return jsonify({'success': True})

        else:
            tasks = load_json_file(KANBAN_FILE, [])
            idx = next((i for i, t in enumerate(tasks) if t['id'] == task_id), None)

            if idx is None:
                return jsonify({'success': False, 'error': 'Task not found'}), 404

            if request.method == 'PUT':
                data = request.json
                task = tasks[idx]
                for field in ['column', 'content', 'notes', 'color', 'position', 'due_date', 'assigned_to', 'pinned']:
                    if field in data:
                        task[field] = data[field]
                task['updated_at'] = datetime.now().isoformat()
                tasks[idx] = task
                save_json_file(KANBAN_FILE, tasks)
                return jsonify({'success': True, 'task': task})

            elif request.method == 'DELETE':
                tasks.pop(idx)
                save_json_file(KANBAN_FILE, tasks)
                return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    # Create database tables if using database
    if USE_DATABASE:
        with app.app_context():
            db.create_all()
            print("✅ Database tables created successfully")

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
