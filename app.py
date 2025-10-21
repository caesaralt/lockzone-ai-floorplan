from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import json
import copy
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np
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
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER'], 
               app.config['DATA_FOLDER'], app.config['LEARNING_FOLDER'],
               app.config['SIMPRO_CONFIG_FOLDER']]:
    os.makedirs(folder, exist_ok=True)

DATA_FILE = os.path.join(app.config['DATA_FOLDER'], 'automation_data.json')
LEARNING_INDEX_FILE = os.path.join(app.config['LEARNING_FOLDER'], 'learning_index.json')
SIMPRO_CONFIG_FILE = os.path.join(app.config['SIMPRO_CONFIG_FOLDER'], 'simpro_config.json')

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

def analyze_floorplan_with_ai(pdf_path):
    """Use Claude Vision API to intelligently analyze floor plans"""
    
    # Check if API key is available and anthropic is installed
    if not ANTHROPIC_AVAILABLE:
        print("Anthropic package not available, using fallback")
        return analyze_floorplan_smart(pdf_path)
    
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("WARNING: No ANTHROPIC_API_KEY found, using fallback method")
        return analyze_floorplan_smart(pdf_path)
    
    print(f"✅ API key found: {api_key[:20]}...")
    print(f"✅ API key length: {len(api_key)}")
    
    try:
        print("🔄 Converting PDF to image...")
        # Convert PDF to image
        image_base64 = pdf_to_image_base64(pdf_path)
        print(f"✅ Image converted, base64 length: {len(image_base64)}")
        
        # Get learning context
        learning_context = get_learning_context()
        
        # Initialize Claude client
        client = anthropic.Anthropic(api_key=api_key)
        print("✅ Claude client initialized")
        
        # Create vision prompt
        prompt = f"""{learning_context}

Analyze this floor plan image and provide a detailed JSON response with the following structure:

{{
  "rooms": [
    {{
      "type": "living_room|bedroom|kitchen|bathroom|hallway|office|garage|etc",
      "center_x": <pixel x coordinate of room center>,
      "center_y": <pixel y coordinate of room center>,
      "area_estimate": <estimated square meters>,
      "confidence": <0-1 confidence score>
    }}
  ],
  "doors": [
    {{
      "x": <pixel x coordinate>,
      "y": <pixel y coordinate>,
      "type": "entry|interior|sliding|etc"
    }}
  ],
  "windows": [
    {{
      "x": <pixel x coordinate>,
      "y": <pixel y coordinate>,
      "width_estimate": <estimated width in pixels>
    }}
  ],
  "page_dimensions": {{
    "width": <image width in pixels>,
    "height": <image height in pixels>
  }},
  "notes": "<any relevant observations about the floor plan>"
}}

Be precise with coordinates. Identify all rooms, doors, and windows you can see. For room types, be specific (e.g., "master_bedroom", "powder_room", "walk_in_closet").

Respond ONLY with valid JSON, no other text."""

        print("🔄 Calling Claude Vision API...")
        # Call Claude Vision API
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )
        print("✅ API call successful!")
        print(f"Response usage: {message.usage}")
        
        # Parse Claude's response
        response_text = message.content[0].text
        print(f"✅ Got response, length: {len(response_text)}")
        
        # Clean up response (remove markdown code blocks if present)
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        analysis = json.loads(response_text)
        
        # Convert to expected format
        rooms = []
        for i, room in enumerate(analysis.get('rooms', [])):
            rooms.append({
                'center': (int(room['center_x']), int(room['center_y'])),
                'area': room.get('area_estimate', 50),
                'type': room.get('type', 'unknown'),
                'confidence': room.get('confidence', 0.8),
                'index': i
            })
        
        doors = [(int(d['x']), int(d['y'])) for d in analysis.get('doors', [])]
        windows = [(int(w['x']), int(w['y'])) for w in analysis.get('windows', [])]
        
        page_dims = analysis.get('page_dimensions', {})
        
        return {
            'rooms': rooms,
            'doors': doors,
            'windows': windows,
            'page_size': (page_dims.get('width', 1000), page_dims.get('height', 1000)),
            'ai_notes': analysis.get('notes', ''),
            'method': 'ai_vision'
        }
    
    except Exception as e:
        print(f"❌ AI analysis failed with error: {type(e).__name__}")
        print(f"❌ Error message: {str(e)}")
        print(f"❌ Full traceback:")
        traceback.print_exc()
        print("⚠️  Falling back to Smart Grid analysis")
        return analyze_floorplan_smart(pdf_path)

def analyze_floorplan_smart(pdf_path):
    """Fallback method - smart analysis without AI"""
    reader = PdfReader(pdf_path)
    first_page = reader.pages[0]
    
    page_box = first_page.mediabox
    width = float(page_box.width)
    height = float(page_box.height)
    total_area = width * height
    
    text = first_page.extract_text()
    words = text.split() if text else []
    
    if width > 1000 or height > 1000:
        num_rooms = 12
    elif width > 700 or height > 700:
        num_rooms = 8
    elif width > 500 or height > 500:
        num_rooms = 6
    else:
        num_rooms = 4
    
    rooms = []
    grid_x = int(np.sqrt(num_rooms * width / height))
    grid_y = int(np.ceil(num_rooms / grid_x))
    
    for i in range(num_rooms):
        row = i // grid_x
        col = i % grid_x
        x = width * (col + 0.5) / grid_x
        y = height * (row + 0.5) / grid_y
        area = total_area / num_rooms
        rooms.append({
            'center': (int(x), int(y)),
            'area': area,
            'type': 'generic',
            'index': i
        })
    
    num_doors = max(4, num_rooms // 2)
    num_windows = max(8, num_rooms)
    
    doors = []
    windows = []
    
    for i in range(num_doors):
        side = i % 4
        if side == 0:
            doors.append((int(width * (i + 1) / (num_doors + 1)), int(height * 0.1)))
        elif side == 1:
            doors.append((int(width * 0.9), int(height * (i + 1) / (num_doors + 1))))
        elif side == 2:
            doors.append((int(width * (i + 1) / (num_doors + 1)), int(height * 0.9)))
        else:
            doors.append((int(width * 0.1), int(height * (i + 1) / (num_doors + 1))))
    
    for i in range(num_windows):
        side = i % 4
        offset = (i // 4 + 1) * 0.15
        if side == 0:
            windows.append((int(width * offset), int(height * 0.1)))
        elif side == 1:
            windows.append((int(width * 0.9), int(height * offset)))
        elif side == 2:
            windows.append((int(width * offset), int(height * 0.9)))
        else:
            windows.append((int(width * 0.1), int(height * offset)))
    
    return {
        'rooms': rooms[:num_rooms],
        'doors': doors,
        'windows': windows,
        'page_size': (width, height),
        'method': 'fallback'
    }

def place_symbols_intelligently(analysis, automation_types, tier="basic"):
    """Intelligently place symbols based on room types and AI analysis"""
    placements = {auto_type: [] for auto_type in automation_types}
    
    rooms = analysis['rooms']
    doors = analysis['doors']
    windows = analysis['windows']
    
    # Room type mappings for intelligent placement
    lighting_rooms = ['living_room', 'bedroom', 'kitchen', 'bathroom', 'hallway', 
                      'office', 'dining_room', 'master_bedroom', 'generic']
    audio_rooms = ['living_room', 'bedroom', 'master_bedroom', 'office', 'media_room']
    climate_rooms = ['living_room', 'bedroom', 'master_bedroom', 'office', 'dining_room']
    
    for auto_type in automation_types:
        if auto_type == 'lighting':
            # Place lights in all rooms
            for i, room in enumerate(rooms):
                if room.get('type', 'generic') in lighting_rooms:
                    placements[auto_type].append({
                        'position': room['center'],
                        'room_index': i,
                        'room_type': room.get('type', 'generic'),
                        'quantity': 1,
                        'confidence': room.get('confidence', 0.8)
                    })
        
        elif auto_type == 'shading':
            # Place at windows
            for i, window_pos in enumerate(windows):
                placements[auto_type].append({
                    'position': window_pos,
                    'window_index': i,
                    'quantity': 1,
                    'confidence': 0.9
                })
        
        elif auto_type == 'security_access':
            # Place at doors
            for i, door_pos in enumerate(doors):
                placements[auto_type].append({
                    'position': door_pos,
                    'door_index': i,
                    'quantity': 1,
                    'confidence': 0.9
                })
        
        elif auto_type == 'climate':
            # Place in main living spaces
            for i, room in enumerate(rooms):
                if room.get('type', 'generic') in climate_rooms:
                    center = room['center']
                    placements[auto_type].append({
                        'position': (center[0] + 30, center[1] + 30),
                        'room_index': i,
                        'room_type': room.get('type', 'generic'),
                        'quantity': 1,
                        'confidence': room.get('confidence', 0.7)
                    })
        
        elif auto_type == 'audio':
            # Place in entertainment/living spaces
            for i, room in enumerate(rooms):
                if room.get('type', 'generic') in audio_rooms:
                    center = room['center']
                    placements[auto_type].append({
                        'position': (center[0] - 30, center[1] - 30),
                        'room_index': i,
                        'room_type': room.get('type', 'generic'),
                        'quantity': 1,
                        'confidence': room.get('confidence', 0.7)
                    })
    
    return placements

def place_symbols_with_ai(analysis, automation_types, tier="basic"):
    """
    Use Claude AI to intelligently place automation symbols based on floor plan analysis.
    Uses the room coordinates from the AI vision analysis directly.
    """
    
    # Check if AI is available
    if not ANTHROPIC_AVAILABLE:
        print("⚠️  AI not available, using standard intelligent placement")
        return place_symbols_intelligently(analysis, automation_types, tier)
    
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("⚠️  No API key, using standard intelligent placement")
        return place_symbols_intelligently(analysis, automation_types, tier)
    
    try:
        print("🤖 Using AI to determine optimal symbol placement...")
        
        # Get learning context from past projects
        learning_index = load_learning_index()
        learning_context = ""
        if learning_index.get('examples'):
            learning_context = "\n\nLearning from past projects:\n"
            for ex in learning_index.get('examples', [])[-5:]:  # Last 5 examples
                if 'placement_feedback' in ex:
                    learning_context += f"- {ex.get('placement_feedback')}\n"
        
        # Initialize Claude client
        client = anthropic.Anthropic(api_key=api_key)
        
        # Prepare room data
        rooms_info = []
        for i, room in enumerate(analysis['rooms']):
            rooms_info.append({
                'index': i,
                'type': room.get('type', 'unknown'),
                'area': room.get('area', 0),
                'center': room.get('center', (0, 0))
            })
        
        # Create detailed prompt for placement decision
        prompt = f"""You are an expert home automation installer analyzing a floor plan to determine optimal placement quantities.

Floor Plan Analysis:
- Total Rooms: {len(analysis['rooms'])}
- Rooms: {json.dumps(rooms_info, indent=2)}
- Doors: {len(analysis['doors'])}
- Windows: {len(analysis['windows'])}

Automation Types Requested: {', '.join(automation_types)}
Pricing Tier: {tier}
{learning_context}

PLACEMENT RULES:
1. **Lighting Control**: 
   - Master bedrooms: 3 lights
   - Regular bedrooms: 2 lights
   - Living rooms: 4 lights
   - Kitchens: 4 lights
   - Bathrooms: 2 lights
   - Hallways/corridors: 1 light
   - Office/study: 3 lights

2. **Shading Control**: 1 per window
3. **Security & Access**: 1 at main entrance + 1 per additional door
4. **Climate Control**: 1-2 per floor (zones)
5. **Audio System**: Living room + master bedroom

For each automation type requested, tell me:
- Which rooms should get devices
- How many devices per room

Respond with ONLY valid JSON:
{{
  "placement_plan": {{
    "lighting": [
      {{"room_index": 0, "quantity": 3, "reason": "master bedroom"}},
      {{"room_index": 1, "quantity": 2, "reason": "bedroom"}},
      ...
    ],
    "shading": [
      {{"quantity": {len(analysis['windows'])}, "reason": "one per window"}}
    ],
    "security_access": [
      {{"quantity": {max(1, len(analysis['doors']))}, "reason": "doors and entry points"}}
    ],
    "climate": [
      {{"quantity": 1, "reason": "main zone control"}}
    ],
    "audio": [
      {{"room_index": 0, "quantity": 2, "reason": "living room speakers"}}
    ]
  }},
  "strategy": "Brief explanation"
}}

Use room_index to reference rooms from the list above."""

        print("🔄 Asking Claude AI for optimal placement strategy...")
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = message.content[0].text
        print("✅ Received AI placement strategy")
        
        # Clean up response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        ai_plan = json.loads(response_text)
        print(f"📊 AI Strategy: {ai_plan.get('strategy', 'N/A')}")
        
        # Convert AI plan to actual placements using room coordinates from analysis
        placements = {auto_type: [] for auto_type in automation_types}
        rooms = analysis['rooms']
        doors = analysis['doors']
        windows = analysis['windows']
        
        print(f"🏠 Using room data from analysis:")
        print(f"   Rooms: {len(rooms)}")
        if rooms:
            print(f"   First room center: {rooms[0].get('center')}")
        print(f"   Doors: {len(doors)}")
        if doors:
            print(f"   First door: {doors[0]}")
        print(f"   Windows: {len(windows)}")
        if windows:
            print(f"   First window: {windows[0]}")
        
        # Process each automation type
        for auto_type in automation_types:
            if auto_type not in ai_plan.get('placement_plan', {}):
                continue
                
            plan_items = ai_plan['placement_plan'][auto_type]
            
            if auto_type == 'lighting':
                # Place lights in specified rooms
                for item in plan_items:
                    room_idx = item.get('room_index')
                    quantity = item.get('quantity', 1)
                    if room_idx is not None and room_idx < len(rooms):
                        room = rooms[room_idx]
                        center = room.get('center', (0, 0))
                        
                        # Add multiple lights for the same room with slight offset
                        for q in range(quantity):
                            offset_x = (q - quantity//2) * 30
                            placements[auto_type].append({
                                'position': (center[0] + offset_x, center[1]),
                                'room_index': room_idx,
                                'quantity': 1,
                                'confidence': 0.95
                            })
            
            elif auto_type == 'shading':
                # Place at windows
                for i, window_pos in enumerate(windows):
                    placements[auto_type].append({
                        'position': window_pos,
                        'window_index': i,
                        'quantity': 1,
                        'confidence': 0.9
                    })
            
            elif auto_type == 'security_access':
                # Place at doors
                for i, door_pos in enumerate(doors):
                    placements[auto_type].append({
                        'position': door_pos,
                        'door_index': i,
                        'quantity': 1,
                        'confidence': 0.9
                    })
            
            elif auto_type == 'climate':
                # Place in first major room (usually living room)
                if rooms:
                    center = rooms[0].get('center', (0, 0))
                    placements[auto_type].append({
                        'position': (center[0] + 30, center[1] + 30),
                        'room_index': 0,
                        'quantity': 1,
                        'confidence': 0.8
                    })
            
            elif auto_type == 'audio':
                # Place in living spaces
                for item in plan_items:
                    room_idx = item.get('room_index')
                    if room_idx is not None and room_idx < len(rooms):
                        room = rooms[room_idx]
                        center = room.get('center', (0, 0))
                        placements[auto_type].append({
                            'position': (center[0] - 30, center[1] - 30),
                            'room_index': room_idx,
                            'quantity': 1,
                            'confidence': 0.8
                        })
        
        # Log results
        for auto_type, items in placements.items():
            print(f"  ✅ {auto_type}: {len(items)} items placed")
        
        return placements
        
    except Exception as e:
        print(f"❌ AI placement failed: {str(e)}")
        print("⚠️  Falling back to standard intelligent placement")
        traceback.print_exc()
        return place_symbols_intelligently(analysis, automation_types, tier)

# ============================================================================
# PDF AND QUOTE GENERATION
# ============================================================================

def create_annotated_pdf(original_pdf_path, placements, automation_data, output_path):
    """Create annotated PDF with symbols - coordinates are scaled correctly"""
    reader = PdfReader(original_pdf_path)
    writer = PdfWriter()
    
    first_page = reader.pages[0]
    page_box = first_page.mediabox
    pdf_width = float(page_box.width)
    pdf_height = float(page_box.height)
    
    print(f"📐 PDF Dimensions: {pdf_width} x {pdf_height}")
    
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(pdf_width, pdf_height))
    
    c.setFont("Helvetica", 24)
    c.setFillColorRGB(1, 0, 0)
    
    # CRITICAL: Coordinates from AI analysis are in image space (2x zoom)
    # We need to scale them down to PDF space
    SCALE_FACTOR = 0.5  # Because image was rendered at 2x zoom
    
    symbol_count = 0
    for auto_type, positions in placements.items():
        if auto_type in automation_data['automation_types']:
            symbol = automation_data['automation_types'][auto_type]['symbols'][0]
            for pos_data in positions:
                x_image, y_image = pos_data['position']
                
                # Convert image coordinates to PDF coordinates
                x_pdf = x_image * SCALE_FACTOR
                y_pdf = y_image * SCALE_FACTOR
                
                # PDF coordinate system: (0,0) is bottom-left, but image is top-left
                # So we need to flip Y coordinate
                y_pdf_flipped = pdf_height - y_pdf
                
                # DEBUG: Print first few coordinates
                if symbol_count < 5:
                    print(f"🔍 Symbol {symbol_count}: {symbol}")
                    print(f"   Image coords: ({x_image}, {y_image})")
                    print(f"   PDF coords: ({x_pdf}, {y_pdf})")
                    print(f"   Flipped: ({x_pdf}, {y_pdf_flipped})")
                symbol_count += 1
                
                c.drawString(x_pdf, y_pdf_flipped, symbol)
    
    print(f"📊 Total symbols placed: {symbol_count}")
    
    c.save()
    
    packet.seek(0)
    overlay_reader = PdfReader(packet)
    first_page.merge_page(overlay_reader.pages[0])
    
    writer.add_page(first_page)
    
    for page_num in range(1, len(reader.pages)):
        writer.add_page(reader.pages[page_num])
    
    with open(output_path, 'wb') as f:
        writer.write(f)
    
    return output_path

def calculate_costs(placements, automation_data, tier="basic"):
    total_cost = 0
    total_labor_hours = 0
    items = []
    
    for auto_type, positions in placements.items():
        if auto_type in automation_data['automation_types']:
            type_data = automation_data['automation_types'][auto_type]
            quantity = len(positions)
            
            unit_cost = type_data['base_cost_per_unit'][tier]
            labor_hours_per_unit = type_data['labor_hours'][tier]
            
            subtotal = unit_cost * quantity
            labor_hours = labor_hours_per_unit * quantity
            labor_cost = labor_hours * automation_data['labor_rate']
            
            total_cost += subtotal + labor_cost
            total_labor_hours += labor_hours
            
            items.append({
                'type': type_data['name'],
                'quantity': quantity,
                'unit_cost': unit_cost,
                'subtotal': subtotal,
                'labor_hours': labor_hours,
                'labor_cost': labor_cost,
                'total': subtotal + labor_cost
            })
    
    markup = total_cost * (automation_data['markup_percentage'] / 100)
    grand_total = total_cost + markup
    
    return {
        'items': items,
        'subtotal': total_cost,
        'labor_hours': total_labor_hours,
        'markup': markup,
        'grand_total': grand_total
    }

def generate_quote_pdf(costs, automation_data, project_name, tier, output_path):
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#556B2F'),
        spaceAfter=30,
        alignment=1
    )
    
    company = automation_data['company_info']
    title = Paragraph(f"<b>{company['name']}</b><br/>AI-Powered Quoting Tool", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.3*inch))
    
    header_data = [
        ['Project:', project_name],
        ['Date:', datetime.now().strftime('%Y-%m-%d')],
        ['Tier:', tier.capitalize()],
        ['Contact:', f"{company['phone']} | {company['email']}"]
    ]
    header_table = Table(header_data, colWidths=[1.5*inch, 4*inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#556B2F')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.5*inch))
    
    quote_data = [['Description', 'Qty', 'Unit Cost', 'Labor Hrs', 'Total']]
    for item in costs['items']:
        quote_data.append([
            item['type'],
            str(item['quantity']),
            f"${item['unit_cost']:.2f}",
            f"{item['labor_hours']:.1f}",
            f"${item['total']:.2f}"
        ])
    
    quote_data.append(['', '', '', 'Subtotal:', f"${costs['subtotal']:.2f}"])
    quote_data.append(['', '', '', f'Markup ({automation_data["markup_percentage"]}%):', f"${costs['markup']:.2f}"])
    quote_data.append(['', '', '', 'GRAND TOTAL:', f"${costs['grand_total']:.2f}"])
    
    quote_table = Table(quote_data, colWidths=[2.5*inch, 0.7*inch, 1*inch, 1*inch, 1.3*inch])
    quote_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#556B2F')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -4), 1, colors.grey),
        ('FONTNAME', (3, -3), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (3, -1), (-1, -1), colors.HexColor('#556B2F')),
        ('TEXTCOLOR', (3, -1), (-1, -1), colors.white),
    ]))
    elements.append(quote_table)
    
    doc.build(elements)

# ============================================================================
# SIMPRO API INTEGRATION
# ============================================================================

def make_simpro_request(endpoint, method='GET', data=None, params=None):
    """Make authenticated request to Simpro API"""
    config = load_simpro_config()
    
    if not config.get('connected') or not config.get('access_token'):
        return {'error': 'Not connected to Simpro'}
    
    headers = {
        'Authorization': f"Bearer {config['access_token']}",
        'Content-Type': 'application/json'
    }
    
    url = f"{config['base_url']}/api/v1.0/companies/{config['company_id']}{endpoint}"
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, params=params, timeout=30)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method == 'PUT':
            response = requests.put(url, headers=headers, json=data, timeout=30)
        else:
            return {'error': f'Unsupported method: {method}'}
        
        response.raise_for_status()
        
        # Try to parse JSON, handle cases where response might not be JSON
        try:
            return response.json()
        except ValueError:
            return {'error': 'Invalid JSON response from Simpro', 'status_code': response.status_code, 'text': response.text[:200]}
    
    except requests.exceptions.RequestException as e:
        print(f"Simpro API error: {str(e)}")
        # Try to get more details from the response
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                error_msg = f"{error_msg}: {error_details}"
            except:
                error_msg = f"{error_msg} (Status: {e.response.status_code})"
        return {'error': error_msg}

# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Main analysis endpoint - uses AI if available"""
    try:
        if 'floorplan' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['floorplan']
        project_name = request.form.get('project_name', 'Untitled Project')
        automation_types = request.form.getlist('automation_types')
        tier = request.form.get('tier', 'basic')
        
        if not automation_types:
            return jsonify({'success': False, 'error': 'No automation types selected'}), 400
        
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{timestamp}_{filename}')
        file.save(input_path)
        
        # Use AI analysis (or fallback)
        automation_data = load_data()
        analysis = analyze_floorplan_with_ai(input_path)
        
        # Use AI-powered placement (with fallback to intelligent placement)
        placements = place_symbols_with_ai(analysis, automation_types, tier)
        
        # Store analysis result and placements in learning index
        learning_index = load_learning_index()
        learning_index['examples'].append({
            'timestamp': timestamp,
            'project_name': project_name,
            'automation_types': automation_types,
            'tier': tier,
            'pdf_path': input_path,
            'placements': placements,
            'analysis_result': {
                'rooms': len(analysis['rooms']),
                'doors': len(analysis['doors']),
                'windows': len(analysis['windows']),
                'method': analysis.get('method', 'unknown'),
                'ai_notes': analysis.get('ai_notes', '')
            }
        })
        save_learning_index(learning_index)
        
        # Calculate costs for display
        costs = calculate_costs(placements, automation_data, tier)
        
        # Return redirect to editor
        return jsonify({
            'success': True,
            'redirect': f'/editor/{timestamp}',
            'analysis': {
                'rooms_detected': len(analysis['rooms']),
                'doors_detected': len(analysis['doors']),
                'windows_detected': len(analysis['windows']),
                'method': analysis.get('method', 'unknown'),
                'ai_notes': analysis.get('ai_notes', '')
            },
            'costs': costs
        })
    
    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload-learning-data', methods=['POST'])
def upload_learning_data():
    """Upload training data for learning system"""
    try:
        files = request.files.getlist('files[]')
        notes = request.form.get('notes', '')
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        batch_folder = os.path.join(app.config['LEARNING_FOLDER'], timestamp)
        os.makedirs(batch_folder, exist_ok=True)
        
        saved_files = []
        for file in files:
            if file:
                filename = secure_filename(file.filename)
                filepath = os.path.join(batch_folder, filename)
                file.save(filepath)
                saved_files.append(filename)
        
        metadata = {
            'timestamp': timestamp,
            'files': saved_files,
            'notes': notes,
            'uploaded_at': datetime.now().isoformat()
        }
        
        with open(os.path.join(batch_folder, 'metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Add to learning index
        learning_index = load_learning_index()
        learning_index['examples'].append({
            'timestamp': timestamp,
            'batch_folder': batch_folder,
            'files': saved_files,
            'notes': notes,
            'type': 'training_data'
        })
        save_learning_index(learning_index)
        
        return jsonify({
            'success': True,
            'message': f'Uploaded {len(saved_files)} files - System will use this data in future analysis',
            'batch_id': timestamp
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/process-instructions', methods=['POST'])
def process_instructions():
    """Save natural language instructions for learning"""
    try:
        instructions = request.json.get('instructions', '')
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Add to learning index
        learning_index = load_learning_index()
        learning_index['examples'].append({
            'timestamp': timestamp,
            'instructions': instructions,
            'type': 'user_instruction',
            'created_at': datetime.now().isoformat()
        })
        save_learning_index(learning_index)
        
        return jsonify({
            'success': True,
            'message': 'Instructions saved and will be used in future AI analysis'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/placement-feedback', methods=['POST'])
def placement_feedback():
    """
    Save feedback about symbol placement to improve future AI decisions.
    Example: "Add 2 more lights in bedrooms", "Remove security from interior doors"
    """
    try:
        feedback = request.json.get('feedback', '')
        project_name = request.json.get('project_name', 'Unknown')
        timestamp = request.json.get('timestamp', datetime.now().strftime('%Y%m%d_%H%M%S'))
        
        if not feedback:
            return jsonify({'success': False, 'error': 'No feedback provided'}), 400
        
        # Add to learning index
        learning_index = load_learning_index()
        learning_index['examples'].append({
            'timestamp': timestamp,
            'project_name': project_name,
            'placement_feedback': feedback,
            'type': 'placement_feedback',
            'created_at': datetime.now().isoformat()
        })
        save_learning_index(learning_index)
        
        return jsonify({
            'success': True,
            'message': 'Feedback saved! Future placements will reflect this guidance.',
            'feedback': feedback
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download/<filename>')
def download(filename):
    return send_file(
        os.path.join(app.config['OUTPUT_FOLDER'], filename),
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/api/update-pricing', methods=['POST'])
def update_pricing():
    """Update pricing configuration"""
    try:
        new_data = request.json
        current_data = load_data()
        
        if 'labor_rate' in new_data:
            current_data['labor_rate'] = new_data['labor_rate']
        if 'markup_percentage' in new_data:
            current_data['markup_percentage'] = new_data['markup_percentage']
        
        if 'automation_types' in new_data:
            for auto_type, config in new_data['automation_types'].items():
                if auto_type in current_data['automation_types']:
                    if 'base_cost_per_unit' in config:
                        current_data['automation_types'][auto_type]['base_cost_per_unit'].update(
                            config['base_cost_per_unit']
                        )
        
        save_data(current_data)
        
        return jsonify({
            'success': True,
            'message': 'Pricing updated successfully'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# SIMPRO INTEGRATION ROUTES
# ============================================================================

@app.route('/api/simpro/config', methods=['GET', 'POST'])
def simpro_config():
    """Get or update Simpro configuration"""
    if request.method == 'GET':
        config = load_simpro_config()
        # Don't send sensitive data to frontend
        safe_config = {
            'connected': config.get('connected', False),
            'base_url': config.get('base_url', ''),
            'company_id': config.get('company_id', '0')
        }
        return jsonify(safe_config)
    
    else:  # POST
        try:
            data = request.json
            config = load_simpro_config()
            
            config['base_url'] = data.get('base_url', '').rstrip('/')
            config['company_id'] = data.get('company_id', '0')
            config['client_id'] = data.get('client_id', '')
            config['client_secret'] = data.get('client_secret', '')
            config['connected'] = False  # Will be set to True after successful auth
            
            save_simpro_config(config)
            
            return jsonify({'success': True, 'message': 'Configuration saved'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/simpro/connect', methods=['POST'])
def simpro_connect():
    """Test connection and get access token"""
    try:
        config = load_simpro_config()
        
        # OAuth2 token request
        token_url = f"{config['base_url']}/oauth2/token"
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': config['client_id'],
            'client_secret': config['client_secret']
        }
        
        response = requests.post(token_url, data=data, timeout=30)
        response.raise_for_status()
        
        token_data = response.json()
        
        config['access_token'] = token_data.get('access_token')
        config['refresh_token'] = token_data.get('refresh_token')
        config['token_expires_at'] = datetime.now().timestamp() + token_data.get('expires_in', 3600)
        config['connected'] = True
        
        save_simpro_config(config)
        
        return jsonify({'success': True, 'message': 'Successfully connected to Simpro'})
    
    except Exception as e:
        print(f"Simpro connection error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/simpro/catalogs', methods=['GET'])
def simpro_catalogs():
    """Fetch catalog items from Simpro"""
    try:
        params = {
            'pageSize': request.args.get('pageSize', 100),
            'page': request.args.get('page', 1)
        }
        
        result = make_simpro_request('/catalogs/', params=params)
        
        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']}), 400
        
        return jsonify({'success': True, 'data': result})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/simpro/labor-rates', methods=['GET'])
def simpro_labor_rates():
    """Fetch labor rates from Simpro"""
    try:
        result = make_simpro_request('/laborRates/')
        
        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']}), 400
        
        return jsonify({'success': True, 'data': result})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/simpro/jobs', methods=['GET'])
def simpro_jobs():
    """Fetch jobs from Simpro"""
    try:
        params = {
            'pageSize': request.args.get('pageSize', 50),
            'page': request.args.get('page', 1)
        }
        
        result = make_simpro_request('/jobs/', params=params)
        
        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']}), 400
        
        return jsonify({'success': True, 'data': result})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/simpro/customers', methods=['GET'])
def simpro_customers():
    """Fetch customers from Simpro"""
    try:
        params = {
            'pageSize': request.args.get('pageSize', 50),
            'page': request.args.get('page', 1)
        }
        
        result = make_simpro_request('/customers/', params=params)
        
        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']}), 400
        
        return jsonify({'success': True, 'data': result})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/simpro/quotes', methods=['GET', 'POST'])
def simpro_quotes():
    """Get or create quotes in Simpro"""
    if request.method == 'GET':
        try:
            params = {
                'pageSize': request.args.get('pageSize', 50),
                'page': request.args.get('page', 1)
            }
            
            result = make_simpro_request('/quotes/', params=params)
            
            if 'error' in result:
                return jsonify({'success': False, 'error': result['error']}), 400
            
            return jsonify({'success': True, 'data': result})
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    else:  # POST - Create new quote
        try:
            quote_data = request.json
            result = make_simpro_request('/quotes/', method='POST', data=quote_data)
            
            if 'error' in result:
                return jsonify({'success': False, 'error': result['error']}), 400
            
            return jsonify({'success': True, 'message': 'Quote created in Simpro', 'data': result})
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# INTERACTIVE EDITOR ROUTES
# ============================================================================

@app.route('/editor/<project_id>')
def editor(project_id):
    """Interactive floor plan editor"""
    try:
        # Load project data
        learning_index = load_learning_index()
        project = None
        
        for example in learning_index.get('examples', []):
            if example.get('timestamp') == project_id:
                project = example
                break
        
        if not project:
            return "Project not found", 404
        
        # Get initial symbol placement
        placements = project.get('placements', {})
        
        # Convert placements to symbols array for editor
        symbols = []
        for auto_type, positions in placements.items():
            for pos_data in positions:
                symbols.append({
                    'type': auto_type,
                    'symbol': get_symbol_for_type(auto_type),
                    'x': pos_data['position'][0],
                    'y': pos_data['position'][1],
                    'id': len(symbols)
                })
        
        # Load floor plan image (base64)
        pdf_path = project.get('pdf_path', '')
        floor_plan_image = ''
        if pdf_path and os.path.exists(pdf_path):
            floor_plan_image = '/api/floor-plan-image/' + project_id
        
        # Load pricing config
        automation_data = load_data()
        pricing_dict = {}
        for auto_type, data in automation_data['automation_types'].items():
            pricing_dict[auto_type] = data['base_cost_per_unit']
        
        return render_template('editor.html',
            project_id=project_id,
            project_name=project.get('project_name', 'Unnamed Project'),
            tier=project.get('tier', 'basic'),
            initial_symbols=symbols,
            floor_plan_image=floor_plan_image,
            pricing=pricing_dict
        )
    
    except Exception as e:
        print(f"Editor error: {str(e)}")
        traceback.print_exc()
        return f"Error loading editor: {str(e)}", 500

@app.route('/api/floor-plan-image/<project_id>')
def floor_plan_image(project_id):
    """Serve floor plan image for editor"""
    try:
        learning_index = load_learning_index()
        project = None
        
        for example in learning_index.get('examples', []):
            if example.get('timestamp') == project_id:
                project = example
                break
        
        if not project:
            return "Project not found", 404
        
        pdf_path = project.get('pdf_path', '')
        if not pdf_path or not os.path.exists(pdf_path):
            return "Floor plan not found", 404
        
        # Convert PDF to PNG
        image_base64 = pdf_to_image_base64(pdf_path)
        import base64
        image_bytes = base64.b64decode(image_base64)
        
        from io import BytesIO
        return send_file(BytesIO(image_bytes), mimetype='image/png')
    
    except Exception as e:
        print(f"Floor plan image error: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/api/generate-final-quote', methods=['POST'])
def generate_final_quote():
    """Generate final PDF with user-edited symbol placement"""
    try:
        data = request.json
        project_id = data.get('project_id')
        project_name = data.get('project_name', 'Project')
        symbols = data.get('symbols', [])
        tier = data.get('tier', 'basic')
        
        # Find original project
        learning_index = load_learning_index()
        project = None
        
        for example in learning_index.get('examples', []):
            if example.get('timestamp') == project_id:
                project = example
                break
        
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        original_pdf = project.get('pdf_path', '')
        if not os.path.exists(original_pdf):
            return jsonify({'success': False, 'error': 'Original PDF not found'}), 404
        
        # Convert symbols array to placements format
        placements = {}
        automation_data = load_data()
        
        for auto_type in automation_data['automation_types'].keys():
            placements[auto_type] = []
        
        for sym in symbols:
            auto_type = sym['type']
            if auto_type in placements:
                placements[auto_type].append({
                    'position': (sym['x'], sym['y']),
                    'quantity': 1,
                    'confidence': 1.0,
                    'user_placed': True
                })
        
        # Generate annotated PDF
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f'{timestamp}_final_annotated.pdf'
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        create_annotated_pdf(original_pdf, placements, automation_data, output_path)
        
        # Generate quote PDF
        costs = calculate_costs(placements, automation_data, tier)
        quote_filename = f'{timestamp}_final_quote.pdf'
        quote_path = os.path.join(app.config['OUTPUT_FOLDER'], quote_filename)
        
        create_quote_pdf(
            project_name=project_name,
            costs=costs,
            placements=placements,
            output_path=quote_path,
            annotated_pdf_path=output_filename
        )
        
        return jsonify({
            'success': True,
            'filename': quote_filename,
            'annotated_filename': output_filename
        })
    
    except Exception as e:
        print(f"Generate final quote error: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload-placement-knowledge', methods=['POST'])
def upload_placement_knowledge():
    """Upload corrected placement to AI knowledge base"""
    try:
        data = request.json
        project_id = data.get('project_id')
        project_name = data.get('project_name')
        symbols = data.get('symbols', [])
        feedback = data.get('feedback', '')
        tier = data.get('tier', 'basic')
        
        # Save to learning index
        learning_index = load_learning_index()
        
        # Convert symbols to placement format
        placement_summary = {}
        for sym in symbols:
            auto_type = sym['type']
            if auto_type not in placement_summary:
                placement_summary[auto_type] = 0
            placement_summary[auto_type] += 1
        
        learning_index['examples'].append({
            'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'project_id': project_id,
            'project_name': project_name,
            'type': 'user_corrected_placement',
            'symbols': symbols,
            'placement_summary': placement_summary,
            'placement_feedback': feedback,
            'tier': tier,
            'created_at': datetime.now().isoformat()
        })
        
        save_learning_index(learning_index)
        
        print(f"✅ Knowledge uploaded: {feedback}")
        print(f"   Placement: {placement_summary}")
        
        return jsonify({
            'success': True,
            'message': 'Placement knowledge saved! AI will learn from this for future projects.'
        })
    
    except Exception as e:
        print(f"Upload knowledge error: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

def get_symbol_for_type(auto_type):
    """Get emoji symbol for automation type"""
    symbols = {
        'lighting': '💡',
        'shading': '🪟',
        'security_access': '🔐',
        'climate': '🌡',
        'audio': '🔊'
    }
    return symbols.get(auto_type, '❓')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
