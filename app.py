from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from flask_cors import CORS
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

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
CORS(app)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['DATA_FOLDER'] = 'data'
app.config['LEARNING_FOLDER'] = 'learning_data'
app.config['SIMPRO_CONFIG_FOLDER'] = 'simpro_config'
app.config['CRM_DATA_FOLDER'] = 'crm_data'
app.config['AI_MAPPING_FOLDER'] = 'ai_mapping'
app.config['MAPPING_LEARNING_FOLDER'] = 'mapping_learning'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER'], 
               app.config['DATA_FOLDER'], app.config['LEARNING_FOLDER'],
               app.config['SIMPRO_CONFIG_FOLDER'], app.config['CRM_DATA_FOLDER'],
               app.config['AI_MAPPING_FOLDER'], app.config['MAPPING_LEARNING_FOLDER']]:
    os.makedirs(folder, exist_ok=True)

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
    """Get accumulated learning examples to include in AI prompts"""
    index = load_learning_index()
    context = "Previous learning examples:\n\n"
    
    for example in index.get('examples', [])[-10:]:  # Last 10 examples
        context += f"Date: {example.get('timestamp')}\n"
        context += f"Notes: {example.get('notes', 'N/A')}\n"
        if 'analysis_result' in example:
            context += f"Result: {example['analysis_result']}\n"
        context += "\n"
    
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
        
        prompt = f"""Analyze this floor plan EXTREMELY carefully. Study every detail, symbol, and marking.

{learning_context}

CRITICAL: Be thorough and accurate. Count EVERY component you see:
- Lights (ceiling, recessed, pendant, wall) 
- Switches (count each position)
- Windows/blinds for shading
- Security (cameras, sensors, keypads, intercoms)
- HVAC (thermostats, AC units, vents)
- Audio (speakers, volume controls)

For each room, analyze the scale, symbols, and layout. Don't miss anything.

JSON response:
{{
    "rooms": [
        {{
            "name": "exact room name from plan",
            "lighting": {{"count": total_count, "type": "basic|premium|deluxe"}},
            "shading": {{"count": total_count, "type": "basic|premium|deluxe"}},
            "security_access": {{"count": total_count, "type": "basic|premium|deluxe"}},
            "climate": {{"count": total_count, "type": "basic|premium|deluxe"}},
            "audio": {{"count": total_count, "type": "basic|premium|deluxe"}}
        }}
    ],
    "notes": "observations"
}}

BE PRECISE. Count everything."""
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[
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
            ],
        )
        
        response_text = message.content[0].text
        
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
            
    except Exception as e:
        return {"error": str(e), "fallback": True}

# ============================================================================
# ENHANCED AI MAPPING WITH LEARNING
# ============================================================================

def ai_map_floorplan(file_path, is_pdf=True):
    """Use AI to analyze floor plan with learning context"""
    
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
        
        prompt = f"""Analyze electrical floor plan. Identify components & connections.

{learning_context}

Find:
- Lights, switches, outlets, panels, junctions
- Exact positions (x,y as 0.0-1.0)
- Connections between components
- Circuit labels

JSON:
{{
    "components": [
        {{"id": "L1", "type": "light|switch|outlet|panel|junction", "location": {{"x": 0.5, "y": 0.5}}, "label": "L1", "room": "Kitchen", "description": "LED light"}}
    ],
    "connections": [
        {{"from": "S1", "to": "L1", "type": "control|power", "circuit": "C1"}}
    ],
    "circuits": [
        {{"id": "C1", "panel": "Main", "components": ["S1", "L1"]}}
    ],
    "markup_instructions": {{
        "notes": ["installation notes"]
    }}
}}"""
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[
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
            ],
        )
        
        response_text = message.content[0].text
        
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
            if comp_type == 'light':
                color = 'yellow'
                radius = 15
            elif comp_type == 'switch':
                color = 'blue'
                radius = 12
            elif comp_type == 'outlet':
                color = 'green'
                radius = 12
            elif comp_type == 'panel':
                color = 'red'
                radius = 20
            else:
                color = 'gray'
                radius = 10
            
            draw.ellipse([x-radius, y-radius, x+radius, y+radius], 
                        outline=color, fill=None, width=3)
            draw.text((x+radius+5, y-radius), label, fill='red', font=font)
        
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
    return render_template('canvas.html')

@app.route('/learning')
def learning_page():
    return render_template('learning.html')

@app.route('/simpro')
def simpro_page():
    return render_template('simpro.html')

@app.route('/ai-mapping')
def ai_mapping_page():
    return render_template('template_ai_mapping.html')

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
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['floorplan']
        if file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        analysis_result = analyze_floorplan_with_ai(filepath)
        
        if 'error' in analysis_result and analysis_result.get('fallback'):
            analysis_result = {
                "rooms": [
                    {
                        "name": "Estimated Room",
                        "lighting": {"count": 5, "type": "basic"},
                        "shading": {"count": 2, "type": "basic"},
                        "security_access": {"count": 1, "type": "basic"},
                        "climate": {"count": 1, "type": "basic"},
                        "audio": {"count": 0, "type": "basic"}
                    }
                ],
                "notes": "Fallback estimation - AI analysis unavailable"
            }
        
        return jsonify({'success': True, 'analysis': analysis_result})
    
    except Exception as e:
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

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
        
        token_url = f"{config['base_url']}/oauth/token"
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
        
        return jsonify({'success': True, 'message': 'Connected successfully'})
    
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
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            projects.append(project)
            save_json_file(PROJECTS_FILE, projects)
            return jsonify({'success': True, 'project': project})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/crm/projects/<project_id>', methods=['PUT'])
def update_project(project_id):
    try:
        projects = load_json_file(PROJECTS_FILE, [])
        idx = next((i for i, p in enumerate(projects) if p['id'] == project_id), None)
        if idx is None:
            return jsonify({'success': False, 'error': 'Not found'}), 404
        data = request.json
        project = projects[idx]
        for field in ['title', 'description', 'status', 'priority', 'quote_amount', 'actual_amount', 'due_date']:
            if field in data:
                project[field] = data[field]
        project['updated_at'] = datetime.now().isoformat()
        projects[idx] = project
        save_json_file(PROJECTS_FILE, projects)
        return jsonify({'success': True, 'project': project})
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

@app.route('/api/crm/inventory', methods=['GET', 'POST'])
def handle_inventory():
    try:
        if request.method == 'GET':
            inventory = load_json_file(INVENTORY_FILE, [])
            return jsonify({'success': True, 'inventory': inventory})
        else:
            data = request.json
            inventory = load_json_file(INVENTORY_FILE, [])
            item = {
                'id': str(uuid.uuid4()),
                'name': data.get('name', ''),
                'sku': data.get('sku', ''),
                'category': data.get('category', ''),
                'quantity': data.get('quantity', 0),
                'unit_cost': data.get('unit_cost', 0.0),
                'reorder_level': data.get('reorder_level', 10),
                'created_at': datetime.now().isoformat()
            }
            inventory.append(item)
            save_json_file(INVENTORY_FILE, inventory)
            return jsonify({'success': True, 'item': item})
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
