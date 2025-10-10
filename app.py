from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import json
import copy
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import cv2
import numpy as np
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from pdf2image import convert_from_path
from PIL import Image, ImageDraw, ImageFont
import tempfile
import traceback

app = Flask(__name__)
CORS(app)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['DATA_FOLDER'] = 'data'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER'], app.config['DATA_FOLDER']]:
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

def analyze_floorplan_advanced(image_path: str) -> Dict:
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Could not read image")
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    kernel = np.ones((3,3), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=2)
    eroded = cv2.erode(dilated, kernel, iterations=1)
    
    contours, _ = cv2.findContours(eroded, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    valid_rooms = []
    h, w = img.shape[:2]
    min_area = (w * h) * 0.001
    max_area = (w * h) * 0.3
    
    for contour in contours:
        area = cv2.contourArea(contour)
        if min_area < area < max_area:
            x, y, width, height = cv2.boundingRect(contour)
            aspect_ratio = float(width) / height if height > 0 else 0
            if 0.3 < aspect_ratio < 3.0:
                valid_rooms.append({
                    'contour': contour,
                    'bbox': (x, y, width, height),
                    'area': area,
                    'center': (x + width//2, y + height//2)
                })
    
    valid_rooms.sort(key=lambda r: r['area'], reverse=True)
    valid_rooms = valid_rooms[:15]
    
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=50, maxLineGap=10)
    doors = []
    windows = []
    
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
            angle = np.abs(np.arctan2(y2-y1, x2-x1) * 180 / np.pi)
            
            if 30 < length < 150:
                if angle < 20 or angle > 160:
                    doors.append(((x1+x2)//2, (y1+y2)//2))
            elif 150 < length < 400:
                if 70 < angle < 110:
                    windows.append(((x1+x2)//2, (y1+y2)//2))
    
    return {
        'rooms': valid_rooms,
        'doors': doors[:10],
        'windows': windows[:15],
        'image_shape': img.shape
    }

def place_symbols(analysis: Dict, automation_types: List[str], tier: str = "basic") -> Dict:
    placements = {auto_type: [] for auto_type in automation_types}
    
    rooms = analysis['rooms']
    doors = analysis['doors']
    windows = analysis['windows']
    
    for auto_type in automation_types:
        if auto_type == 'lighting':
            for i, room in enumerate(rooms):
                center = room['center']
                placements[auto_type].append({
                    'position': center,
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

def generate_annotated_pdf(original_pdf_path: str, placements: Dict, automation_data: Dict, output_path: str):
    images = convert_from_path(original_pdf_path, dpi=200)
    first_page = images[0]
    
    draw = ImageDraw.Draw(first_page)
    
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
    
    annotated_image_path = output_path.replace('.pdf', '_annotated.png')
    first_page.save(annotated_image_path, 'PNG')
    
    pdf_writer = PdfWriter()
    reader = PdfReader(original_pdf_path)
    
    c = canvas.Canvas(output_path.replace('.pdf', '_temp.pdf'), pagesize=letter)
    img_width, img_height = first_page.size
    page_width, page_height = letter
    
    scale = min(page_width/img_width, page_height/img_height) * 0.9
    scaled_width = img_width * scale
    scaled_height = img_height * scale
    
    x_offset = (page_width - scaled_width) / 2
    y_offset = (page_height - scaled_height) / 2
    
    c.drawImage(annotated_image_path, x_offset, y_offset, width=scaled_width, height=scaled_height)
    c.save()
    
    return output_path.replace('.pdf', '_temp.pdf')

def calculate_costs(placements: Dict, automation_data: Dict, tier: str = "basic") -> Dict:
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

def generate_quote_pdf(costs: Dict, automation_data: Dict, project_name: str, tier: str, output_path: str):
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
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['floorplan']
        project_name = request.form.get('project_name', 'Untitled Project')
        automation_types = request.form.getlist('automation_types[]')
        tier = request.form.get('tier', 'basic')
        
        if not automation_types:
            return jsonify({'error': 'No automation types selected'}), 400
        
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{timestamp}_{filename}')
        file.save(input_path)
        
        images = convert_from_path(input_path, dpi=200)
        image_path = input_path.replace('.pdf', '.png')
        images[0].save(image_path, 'PNG')
        
        automation_data = load_data()
        analysis = analyze_floorplan_advanced(image_path)
        placements = place_symbols(analysis, automation_types, tier)
        
        annotated_pdf_path = os.path.join(app.config['OUTPUT_FOLDER'], f'{timestamp}_annotated.pdf')
        generate_annotated_pdf(input_path, placements, automation_data, annotated_pdf_path)
        
        costs = calculate_costs(placements, automation_data, tier)
        
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
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download(filename):
    return send_file(
        os.path.join(app.config['OUTPUT_FOLDER'], filename),
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
