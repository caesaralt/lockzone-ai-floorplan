from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import json
import copy
from datetime import datetime
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
        "lighting": {"name": "Lighting Control", "symbols": ["💡"], "base_cost_per_unit": 150.0, "labor_hours": 2.0},
        "shading": {"name": "Shading Control", "symbols": ["🪟"], "base_cost_per_unit": 300.0, "labor_hours": 3.0},
        "security_access": {"name": "Security & Access", "symbols": ["🔐"], "base_cost_per_unit": 500.0, "labor_hours": 4.5},
        "climate": {"name": "Climate Control", "symbols": ["🌡️"], "base_cost_per_unit": 400.0, "labor_hours": 5.0},
        "hvac_energy": {"name": "HVAC & Energy", "symbols": ["⚡"], "base_cost_per_unit": 420.0, "labor_hours": 5.5},
        "multiroom_audio": {"name": "Multiroom Audio", "symbols": ["🎶"], "base_cost_per_unit": 360.0, "labor_hours": 3.5},
        "wellness_garden": {"name": "Wellness & Garden", "symbols": ["🌿"], "base_cost_per_unit": 280.0, "labor_hours": 3.0}
    },
    "labor_rate": 75.0,
    "markup_percentage": 20.0,
    "company_info": {"name": "Lock Zone Automation", "address": "", "phone": "", "email": ""}
}

def _merge_with_defaults(custom_data):
    if not isinstance(custom_data, dict):
        return copy.deepcopy(DEFAULT_DATA)

    base = copy.deepcopy(DEFAULT_DATA)

    def merge_dict(default, override):
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(default.get(key), dict):
                default[key] = merge_dict(default.get(key, {}), value)
            else:
                default[key] = value
        return default

    merged = merge_dict(base, custom_data)

    automation = merged.setdefault('automation_types', {})
    if 'security' in automation and 'security_access' not in automation:
        automation['security_access'] = automation.pop('security')
        automation['security_access']['name'] = 'Security & Access'
    if 'music' in automation and 'multiroom_audio' not in automation:
        automation['multiroom_audio'] = automation.pop('music')
        automation['multiroom_audio']['name'] = 'Multiroom Audio'

    for key, value in DEFAULT_DATA['automation_types'].items():
        automation.setdefault(key, copy.deepcopy(value))

    return merged


def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return _merge_with_defaults(json.load(f))
        except Exception:
            return copy.deepcopy(DEFAULT_DATA)
    return copy.deepcopy(DEFAULT_DATA)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

class FloorPlanAnalyzer:
    def __init__(self):
        self.data = load_data()
    
    def analyze_pdf(self, pdf_path, automation_types):
        try:
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            results = []

            for page_number in range(1, total_pages + 1):
                images = convert_from_path(
                    pdf_path,
                    dpi=200,
                    first_page=page_number,
                    last_page=page_number,
                    fmt="png",
                    thread_count=1,
                )

                if not images:
                    continue

                img = images[0]
                img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                analysis = self._analyze_image(img_cv, automation_types)
                analysis['page_number'] = page_number
                analysis['image'] = img
                results.append(analysis)

            return results
        except Exception as e:
            print(f"Error analyzing PDF: {e}")
            return []
    
    def _analyze_image(self, image, automation_types):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        adaptive = cv2.adaptiveThreshold(
            blurred,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            35,
            5,
        )

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(adaptive, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        rooms = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 1500:
                continue

            perimeter = cv2.arcLength(contour, True)
            if perimeter == 0:
                continue

            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
            if len(approx) < 4 or len(approx) > 12:
                continue

            x, y, w, h = cv2.boundingRect(approx)
            if w < 40 or h < 40:
                continue

            aspect_ratio = w / float(h) if h > 0 else 0
            if not (0.35 < aspect_ratio < 2.8):
                continue

            M = cv2.moments(approx)
            if M["m00"] == 0:
                continue
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])

            rooms.append(
                {
                    'x': int(x),
                    'y': int(y),
                    'width': int(w),
                    'height': int(h),
                    'area': float(area),
                    'center': (cx, cy),
                }
            )

        rooms.sort(key=lambda r: r['area'], reverse=True)
        primary_rooms = rooms[:20]
        automation_points = self._generate_automation_points(primary_rooms, automation_types)

        return {
            'rooms': primary_rooms,
            'room_count': len(rooms),
            'automation_points': automation_points,
            'image_shape': image.shape,
        }
    
    def _generate_automation_points(self, rooms, automation_types):
        points = []
        for room in rooms:
            for auto_type in automation_types:
                type_data = self.data['automation_types'].get(auto_type, {})
                symbol = type_data.get('symbols', ['⚙️'])[0]
                points.append({'type': auto_type, 'x': room['center'][0], 'y': room['center'][1], 
                             'room_area': room['area'], 'symbol': symbol})
        return points

def create_annotated_pdf(original_pdf_path, analysis_results, project_name):
    try:
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], 
                                   f"{project_name}_annotated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        reader = PdfReader(original_pdf_path)
        writer = PdfWriter()
        
        for page_idx, page_result in enumerate(analysis_results):
            if page_idx < len(reader.pages):
                img = page_result['image']
                draw = ImageDraw.Draw(img)
                
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
                except:
                    font = ImageFont.load_default()
                
                for point in page_result['automation_points']:
                    x, y = point['x'], point['y']
                    draw.ellipse([x-20, y-20, x+20, y+20], fill='#556B2F', outline='white', width=2)
                    draw.text((x, y), point['symbol'], fill='white', font=font, anchor='mm')
                
                temp_img_path = os.path.join(app.config['OUTPUT_FOLDER'], f'temp_{page_idx}.png')
                img.save(temp_img_path)
                
                temp_pdf = os.path.join(app.config['OUTPUT_FOLDER'], f'temp_{page_idx}.pdf')
                c = canvas.Canvas(temp_pdf, pagesize=(img.width, img.height))
                c.drawImage(temp_img_path, 0, 0, width=img.width, height=img.height)
                c.save()
                
                temp_reader = PdfReader(temp_pdf)
                writer.add_page(temp_reader.pages[0])
                
                if os.path.exists(temp_img_path): os.remove(temp_img_path)
                if os.path.exists(temp_pdf): os.remove(temp_pdf)
        
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
        return output_path
    except Exception as e:
        print(f"Error creating annotated PDF: {e}")
        return None

def generate_quote_pdf(analysis_results, automation_types, project_name):
    data = load_data()
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], 
                               f"{project_name}_quote_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
    
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, 
                                textColor=colors.HexColor('#556B2F'), spaceAfter=30, alignment=1)
    
    story.append(Paragraph(data['company_info'].get('name', 'Lock Zone Automation'), title_style))
    story.append(Paragraph(f"Project: {project_name}", styles['Heading2']))
    story.append(Paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    total_rooms = sum(r['room_count'] for r in analysis_results)
    total_points = sum(len(r['automation_points']) for r in analysis_results)
    
    system_names = []
    for system_key in automation_types:
        type_info = data['automation_types'].get(system_key, {})
        system_names.append(type_info.get('name', system_key.replace('_', ' ').title()))

    summary_data = [
        ['Total Pages', str(len(analysis_results))],
        ['Detected Rooms', str(total_rooms)],
        ['Automation Points', str(total_points)],
        ['Systems', ', '.join(system_names) if system_names else '—']
    ]
    
    summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#556B2F')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 20))
    
    cost_data = [['System', 'Units', 'Cost/Unit', 'Labor Hrs', 'Subtotal']]
    total_cost = 0
    
    for auto_type in automation_types:
        type_data = data['automation_types'].get(auto_type, {})
        units = sum(1 for r in analysis_results for p in r['automation_points'] if p['type'] == auto_type)
        if units > 0:
            cost_per_unit = type_data.get('base_cost_per_unit', 100)
            labor_hours = type_data.get('labor_hours', 1) * units
            subtotal = (cost_per_unit * units) + (labor_hours * data['labor_rate'])
            total_cost += subtotal
            cost_data.append([type_data.get('name', auto_type.title()), str(units), 
                            f"${cost_per_unit:,.2f}", f"{labor_hours:.1f}", f"${subtotal:,.2f}"])
    
    cost_table = Table(cost_data, colWidths=[2*inch, 0.8*inch, 1.2*inch, 1*inch, 1.2*inch])
    cost_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#556B2F')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(cost_table)
    story.append(Spacer(1, 20))
    
    markup = total_cost * (data['markup_percentage'] / 100)
    final_total = total_cost + markup
    
    totals_data = [
        ['Subtotal', f"${total_cost:,.2f}"],
        ['Markup ({:.0f}%)'.format(data['markup_percentage']), f"${markup:,.2f}"],
        ['TOTAL', f"${final_total:,.2f}"]
    ]
    
    totals_table = Table(totals_data, colWidths=[4*inch, 2*inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 14),
        ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#556B2F'))
    ]))
    story.append(totals_table)
    
    doc.build(story)
    return output_path

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_floor_plan():
    try:
        if 'floorplan' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['floorplan']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        project_name = request.form.get('project_name', 'Untitled')
        automation_types = request.form.getlist('automation_types[]')
        
        if not automation_types:
            return jsonify({'error': 'No automation types selected'}), 400
        
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{timestamp}_{filename}")
        file.save(upload_path)
        
        analyzer = FloorPlanAnalyzer()
        analysis_results = analyzer.analyze_pdf(upload_path, automation_types)
        
        if not analysis_results:
            return jsonify({'error': 'Could not analyze floor plan'}), 400
        
        annotated_pdf = create_annotated_pdf(upload_path, analysis_results, project_name)
        quote_pdf = generate_quote_pdf(analysis_results, automation_types, project_name)
        
        total_rooms = sum(r['room_count'] for r in analysis_results)
        total_points = sum(len(r['automation_points']) for r in analysis_results)
        
        data = load_data()
        total_cost = 0
        for auto_type in automation_types:
            type_data = data['automation_types'].get(auto_type, {})
            units = sum(1 for r in analysis_results for p in r['automation_points'] if p['type'] == auto_type)
            cost_per_unit = type_data.get('base_cost_per_unit', 100)
            labor_hours = type_data.get('labor_hours', 1) * units
            total_cost += (cost_per_unit * units) + (labor_hours * data['labor_rate'])
        
        markup = total_cost * (data['markup_percentage'] / 100)
        final_total = total_cost + markup
        
        return jsonify({
            'success': True,
            'project_name': project_name,
            'total_rooms': total_rooms,
            'total_automation_points': total_points,
            'total_cost': f"${final_total:,.2f}",
            'annotated_pdf': os.path.basename(annotated_pdf) if annotated_pdf else None,
            'quote_pdf': os.path.basename(quote_pdf) if quote_pdf else None
        })
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
