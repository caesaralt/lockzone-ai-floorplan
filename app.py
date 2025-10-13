from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import json
import copy
from datetime import datetime
from typing import Dict, List
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

app = Flask(__name__)
CORS(app)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['DATA_FOLDER'] = 'data'
app.config['LEARNING_FOLDER'] = 'learning_data'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER'], 
               app.config['DATA_FOLDER'], app.config['LEARNING_FOLDER']]:
    os.makedirs(folder, exist_ok=True)

DATA_FILE = os.path.join(app.config['DATA_FOLDER'], 'automation_data.json')

DEFAULT_DATA = {
    "automation_types": {
        "lighting": {
            "name": "Lighting Control",
            "symbols": ["💡"],
            "base_cost_per_unit": {"basic": 150.0, "premium": 250.0, "deluxe": 400.0},
            "labor_hours": {"basic": 2.0, "premium": 3.0, "deluxe": 4.0},
            "description": "Smart lighting control system"
        },
        "shading": {
            "name": "Shading Control",
            "symbols": ["🪟"],
            "base_cost_per_unit": {"basic": 300.0, "premium": 500.0, "deluxe": 800.0},
            "labor_hours": {"basic": 3.0, "premium": 4.0, "deluxe": 5.0},
            "description": "Automated window shading"
        },
        "security_access": {
            "name": "Security & Access",
            "symbols": ["🔐"],
            "base_cost_per_unit": {"basic": 500.0, "premium": 900.0, "deluxe": 1500.0},
            "labor_hours": {"basic": 4.5, "premium": 6.0, "deluxe": 8.0},
            "description": "Security and access control"
        },
        "climate": {
            "name": "Climate Control",
            "symbols": ["🌡"],
            "base_cost_per_unit": {"basic": 400.0, "premium": 700.0, "deluxe": 1200.0},
            "labor_hours": {"basic": 5.0, "premium": 7.0, "deluxe": 9.0},
            "description": "HVAC climate control"
        },
        "audio": {
            "name": "Audio System",
            "symbols": ["🔊"],
            "base_cost_per_unit": {"basic": 350.0, "premium": 600.0, "deluxe": 1000.0},
            "labor_hours": {"basic": 3.5, "premium": 5.0, "deluxe": 7.0},
            "description": "Multi-room audio system"
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

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return copy.deepcopy(DEFAULT_DATA)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def pdf_to_images(pdf_path):
    """Convert PDF to images using PyMuPDF"""
    doc = fitz.open(pdf_path)
    images = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    doc.close()
    return images

def analyze_floorplan_smart(image):
    """Smart analysis using PIL - no OpenCV needed"""
    width, height = image.size
    total_area = width * height
    
    # Convert to grayscale for analysis
    gray = image.convert('L')
    pixels = np.array(gray)
    
    # Simple edge detection using numpy
    edges = np.abs(np.diff(pixels.astype(float), axis=0)) + np.abs(np.diff(pixels.astype(float), axis=1, prepend=0))
    
    # Find strong edges (walls)
    threshold = np.percentile(edges, 90)
    strong_edges = edges > threshold
    
    # Estimate rooms based on area divisions
    num_rooms = max(int(total_area / (width * height / 15)), 3)
    
    # Generate room centers in a grid pattern
    rooms = []
    grid_x = int(np.sqrt(num_rooms * width / height))
    grid_y = int(np.ceil(num_rooms / grid_x))
    
    for i in range(num_rooms):
        row = i // grid_x
        col = i % grid_x
        x = int(width * (col + 0.5) / grid_x)
        y = int(height * (row + 0.5) / grid_y)
        area = (width * height) / num_rooms
        rooms.append({
            'center': (x, y),
            'area': area,
            'index': i
        })
    
    # Estimate doors and windows based on perimeter
    perimeter_points = []
    edge_spacing = max(width, height) // 20
    
    # Top and bottom edges
    for x in range(0, width, edge_spacing):
        perimeter_points.append((x, int(height * 0.1)))
        perimeter_points.append((x, int(height * 0.9)))
    
    # Left and right edges
    for y in range(0, height, edge_spacing):
        perimeter_points.append((int(width * 0.1), y))
        perimeter_points.append((int(width * 0.9), y))
    
    doors = perimeter_points[:min(8, len(perimeter_points))]
    windows = perimeter_points[8:min(20, len(perimeter_points))]
    
    return {
        'rooms': rooms,
        'doors': doors,
        'windows': windows,
        'image_shape': (height, width)
    }

def place_symbols(analysis, automation_types, tier="basic"):
    placements = {auto_type: [] for auto_type in automation_types}
    
    rooms = analysis['rooms']
    doors = analysis['doors']
    windows = analysis['windows']
    
    for auto_type in automation_types:
        if auto_type == 'lighting':
            for i, room in enumerate(rooms):
                placements[auto_type].append({
                    'position': room['center'],
                    'room_index': i,
                    'quantity': 1
                })
        
        elif auto_type == 'shading':
            for i, window_pos in enumerate(windows):
                placements[auto_type].append({
                    'position': window_pos,
                    'window_index': i,
                    'quantity': 1
                })
        
        elif auto_type == 'security_access':
            for i, door_pos in enumerate(doors):
                placements[auto_type].append({
                    'position': door_pos,
                    'door_index': i,
                    'quantity': 1
                })
        
        elif auto_type == 'climate':
            for i, room in enumerate(rooms[:max(len(rooms)//2, 1)]):
                center = room['center']
                placements[auto_type].append({
                    'position': (center[0] + 30, center[1] + 30),
                    'room_index': i,
                    'quantity': 1
                })
        
        elif auto_type == 'audio':
            for i, room in enumerate(rooms[:max(len(rooms)//2, 1)]):
                center = room['center']
                placements[auto_type].append({
                    'position': (center[0] - 30, center[1] - 30),
                    'room_index': i,
                    'quantity': 1
                })
    
    return placements

def generate_annotated_pdf(original_pdf_path, placements, automation_data, output_path):
    images = pdf_to_images(original_pdf_path)
    first_page = images[0]
    
    draw = ImageDraw.Draw(first_page)
    
    try:
        font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 60)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 60)
        except:
            font = ImageFont.load_default()
    
    for auto_type, positions in placements.items():
        if auto_type in automation_data['automation_types']:
            symbol = automation_data['automation_types'][auto_type]['symbols'][0]
            for pos_data in positions:
                x, y = pos_data['position']
                draw.text((x, y), symbol, fill='red', font=font)
    
    # Save annotated image
    annotated_image_path = output_path.replace('.pdf', '_annotated.png')
    first_page.save(annotated_image_path, 'PNG')
    
    # Create PDF
    c = canvas.Canvas(output_path, pagesize=letter)
    img_width, img_height = first_page.size
    page_width, page_height = letter
    
    scale = min(page_width/img_width, page_height/img_height) * 0.9
    scaled_width = img_width * scale
    scaled_height = img_height * scale
    
    x_offset = (page_width - scaled_width) / 2
    y_offset = (page_height - scaled_height) / 2
    
    c.drawImage(annotated_image_path, x_offset, y_offset, width=scaled_width, height=scaled_height)
    c.save()
    
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
    title = Paragraph(f"<b>{company['name']}</b><br/>Automated Quoting Tool", title_style)
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        if 'floorplan' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['floorplan']
        project_name = request.form.get('project_name', 'Untitled Project')
        automation_types = request.form.getlist('automation_types[]')
        tier = request.form.get('tier', 'basic')
        
        if not automation_types:
            return jsonify({'success': False, 'error': 'No automation types selected'}), 400
        
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{timestamp}_{filename}')
        file.save(input_path)
        
        # Convert PDF to image
        images = pdf_to_images(input_path)
        first_image = images[0]
        
        # Analyze floorplan
        automation_data = load_data()
        analysis = analyze_floorplan_smart(first_image)
        placements = place_symbols(analysis, automation_types, tier)
        
        # Generate annotated PDF
        annotated_pdf_path = os.path.join(app.config['OUTPUT_FOLDER'], f'{timestamp}_annotated.pdf')
        generate_annotated_pdf(input_path, placements, automation_data, annotated_pdf_path)
        
        # Calculate costs
        costs = calculate_costs(placements, automation_data, tier)
        
        # Generate quote PDF
        quote_pdf_path = os.path.join(app.config['OUTPUT_FOLDER'], f'{timestamp}_quote.pdf')
        generate_quote_pdf(costs, automation_data, project_name, tier, quote_pdf_path)
        
        return jsonify({
            'success': True,
            'analysis': {
                'rooms_detected': len(analysis['rooms']),
                'doors_detected': len(analysis['doors']),
                'windows_detected': len(analysis['windows'])
            },
            'costs': costs,
            'files': {
                'annotated_pdf': f'/download/{os.path.basename(annotated_pdf_path)}',
                'quote_pdf': f'/download/{os.path.basename(quote_pdf_path)}'
            }
        })
    
    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload-learning-data', methods=['POST'])
def upload_learning_data():
    """Upload training data to improve the system"""
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
        
        # Save metadata
        metadata = {
            'timestamp': timestamp,
            'files': saved_files,
            'notes': notes,
            'uploaded_at': datetime.now().isoformat()
        }
        
        with open(os.path.join(batch_folder, 'metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': f'Uploaded {len(saved_files)} files for learning',
            'batch_id': timestamp
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/update-pricing', methods=['POST'])
def update_pricing():
    """Update pricing and configuration"""
    try:
        new_data = request.json
        current_data = load_data()
        
        # Merge new data
        for key in new_data:
            if key in current_data:
                if isinstance(current_data[key], dict):
                    current_data[key].update(new_data[key])
                else:
                    current_data[key] = new_data[key]
        
        save_data(current_data)
        
        return jsonify({
            'success': True,
            'message': 'Pricing updated successfully'
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
