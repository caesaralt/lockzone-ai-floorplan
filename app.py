from __future__ import annotations

import copy
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

import cv2
import numpy as np
from flask import Flask, jsonify, render_template, request, send_file
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle, Paragraph
from werkzeug.utils import secure_filename

from pdf2image import convert_from_path

try:  # pragma: no cover - optional dependency for hosted environments
    import fitz  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - optional dependency for hosted environments
    fitz = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency for hosted environments
    import pytesseract  # type: ignore[import-not-found]
    from pytesseract import Output as TesseractOutput  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - optional dependency for hosted environments
    pytesseract = None  # type: ignore[assignment]
    TesseractOutput = None  # type: ignore[assignment]


app = Flask(__name__)
CORS(app)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['DATA_FOLDER'] = 'data'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

for folder in (app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER'], app.config['DATA_FOLDER']):
    os.makedirs(folder, exist_ok=True)

DATA_FILE = os.path.join(app.config['DATA_FOLDER'], 'automation_data.json')

DEFAULT_AUTOMATION_TYPES: Dict[str, Dict[str, object]] = {
    "lighting": {"name": "Lighting Control", "symbols": ["💡"], "base_cost_per_unit": 150.0, "labor_hours": 2.0},
    "shading": {"name": "Shading Control", "symbols": ["🪟"], "base_cost_per_unit": 300.0, "labor_hours": 3.0},
    "security_access": {"name": "Security & Access", "symbols": ["🔐"], "base_cost_per_unit": 500.0, "labor_hours": 4.5},
    "climate": {"name": "Climate Control", "symbols": ["🌡️"], "base_cost_per_unit": 400.0, "labor_hours": 5.0},
    "hvac_energy": {"name": "HVAC & Energy", "symbols": ["⚡"], "base_cost_per_unit": 420.0, "labor_hours": 5.5},
    "multiroom_audio": {"name": "Multiroom Audio", "symbols": ["🎶"], "base_cost_per_unit": 360.0, "labor_hours": 3.5},
    "wellness_garden": {"name": "Wellness & Garden", "symbols": ["🌿"], "base_cost_per_unit": 280.0, "labor_hours": 3.0},
}

DEFAULT_AUTOMATION_TIERS: Dict[str, Dict[str, object]] = {
    "basic": {"name": "Basic", "price_multiplier": 1.0},
    "premium": {"name": "Premium", "price_multiplier": 1.2},
    "deluxe": {"name": "Deluxe", "price_multiplier": 1.4},
}

DEFAULT_DATA: Dict[str, object] = {
    "automation_types": DEFAULT_AUTOMATION_TYPES,
    "automation_tiers": DEFAULT_AUTOMATION_TIERS,
    "labor_rate": 75.0,
    "markup_percentage": 20.0,
    "company_info": {"name": "Lock Zone Automation", "address": "", "phone": "", "email": ""},
}

LEGACY_TYPE_KEYS = {
    "security": "security_access",
    "music": "multiroom_audio",
}


def _deep_merge(target: Dict[str, object], incoming: Dict[str, object]) -> Dict[str, object]:
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            target[key] = _deep_merge(target.get(key, {}), value)  # type: ignore[arg-type]
        else:
            target[key] = value
    return target


def _merge_with_defaults(custom_data: object) -> Dict[str, object]:
    if not isinstance(custom_data, dict):
        return copy.deepcopy(DEFAULT_DATA)

    merged: Dict[str, object] = copy.deepcopy(DEFAULT_DATA)

    merged = _deep_merge(merged, custom_data)

    automation = merged.setdefault('automation_types', {})
    if isinstance(automation, dict):
        for old_key, new_key in LEGACY_TYPE_KEYS.items():
            if old_key in automation and new_key not in automation:
                automation[new_key] = automation.pop(old_key)
                if isinstance(automation[new_key], dict):
                    automation[new_key]['name'] = DEFAULT_AUTOMATION_TYPES[new_key]['name']
        for key, default_value in DEFAULT_AUTOMATION_TYPES.items():
            automation.setdefault(key, copy.deepcopy(default_value))

    tiers = merged.setdefault('automation_tiers', {})
    if isinstance(tiers, dict):
        for key, default_value in DEFAULT_AUTOMATION_TIERS.items():
            tiers.setdefault(key, copy.deepcopy(default_value))

    return merged


def load_data() -> Dict[str, object]:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return _merge_with_defaults(json.load(f))
        except Exception:
            return copy.deepcopy(DEFAULT_DATA)
    return copy.deepcopy(DEFAULT_DATA)


def save_data(data: Dict[str, object]) -> None:
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def error_response(message: str, status_code: int = 400):
    return jsonify({'success': False, 'error': message}), status_code


class FloorPlanAnalyzer:
    def __init__(self) -> None:
        self.data = load_data()

    def analyze_pdf(self, pdf_path: str, automation_types: List[str]) -> List[Dict[str, object]]:
        try:
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            results: List[Dict[str, object]] = []
            pdf_doc = None
            use_pdf2image = True

            for page_index in range(total_pages):
                image = None

                if use_pdf2image:
                    try:
                        images = convert_from_path(
                            pdf_path,
                            dpi=200,
                            first_page=page_index + 1,
                            last_page=page_index + 1,
                            fmt='png',
                            thread_count=1,
                        )
                        if images:
                            image = images[0]
                    except Exception as exc:
                        use_pdf2image = False
                        print(f"pdf2image conversion failed on page {page_index + 1}: {exc}")

                if image is None and fitz is not None:
                    try:
                        if pdf_doc is None:
                            pdf_doc = fitz.open(pdf_path)  # type: ignore[call-arg]
                        page = pdf_doc.load_page(page_index)
                        matrix = fitz.Matrix(2, 2)
                        pix = page.get_pixmap(matrix=matrix, alpha=False)
                        image = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
                    except Exception as exc:
                        print(f"PyMuPDF conversion failed on page {page_index + 1}: {exc}")

                if image is None:
                    print(f"Skipping page {page_index + 1}: unable to render image")
                    continue

                img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                page_result = self._analyze_image(img_cv, automation_types)
                page_result['page_number'] = page_index + 1
                page_result['image'] = image
                results.append(page_result)

            if pdf_doc is not None:
                pdf_doc.close()

            return results
        except Exception as exc:
            print(f"Error analyzing PDF: {exc}")
            return []

    def _analyze_image(self, image: np.ndarray, automation_types: List[str]) -> Dict[str, object]:
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

        rooms: List[Dict[str, object]] = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 1500:
                continue

            perimeter = cv2.arcLength(contour, True)
            if perimeter == 0:
                continue

            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
            if not (4 <= len(approx) <= 12):
                continue

            x, y, w, h = cv2.boundingRect(approx)
            if w < 40 or h < 40:
                continue

            aspect_ratio = w / float(h) if h else 0
            if not (0.35 < aspect_ratio < 2.8):
                continue

            moments = cv2.moments(approx)
            if moments['m00'] == 0:
                continue

            cx = int(moments['m10'] / moments['m00'])
            cy = int(moments['m01'] / moments['m00'])

            rooms.append({
                'x': int(x),
                'y': int(y),
                'width': int(w),
                'height': int(h),
                'area': float(area),
                'center': (cx, cy),
            })

        rooms.sort(key=lambda item: item['area'], reverse=True)
        primary_rooms = rooms[:20]
        automation_points = self._generate_automation_points(primary_rooms, automation_types)

        text_annotations: List[Dict[str, object]] = []
        if pytesseract is not None and TesseractOutput is not None:
            try:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                ocr_data = pytesseract.image_to_data(rgb_image, output_type=TesseractOutput.DICT)
                for i in range(len(ocr_data.get('text', []))):
                    text = ocr_data['text'][i].strip()
                    if not text:
                        continue
                    x = int(ocr_data['left'][i])
                    y = int(ocr_data['top'][i])
                    w = int(ocr_data['width'][i])
                    h = int(ocr_data['height'][i])
                    confidence = float(ocr_data.get('conf', [0])[i]) if ocr_data.get('conf') else 0.0
                    if confidence < 30:
                        continue
                    text_annotations.append({
                        'text': text,
                        'confidence': confidence,
                        'x': x,
                        'y': y,
                        'width': w,
                        'height': h,
                    })
            except Exception as exc:  # pragma: no cover - optional safeguard
                print(f"OCR failed: {exc}")

        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=120, minLineLength=80, maxLineGap=12)
        line_segments: List[Dict[str, int]] = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                line_segments.append({
                    'x1': int(x1),
                    'y1': int(y1),
                    'x2': int(x2),
                    'y2': int(y2),
                })

        return {
            'rooms': primary_rooms,
            'room_count': len(rooms),
            'automation_points': automation_points,
            'image_shape': image.shape,
            'text_annotations': text_annotations,
            'line_segments': line_segments,
        }

    def _generate_automation_points(self, rooms: List[Dict[str, object]], automation_types: List[str]) -> List[Dict[str, object]]:
        points: List[Dict[str, object]] = []
        for room in rooms:
            for automation_type in automation_types:
                type_data = self.data['automation_types'].get(automation_type, {})  # type: ignore[index]
                symbol = type_data.get('symbols', ['⚙️'])[0] if isinstance(type_data, dict) else '⚙️'
                points.append({
                    'type': automation_type,
                    'x': room['center'][0],
                    'y': room['center'][1],
                    'room_area': room['area'],
                    'symbol': symbol,
                })
        return points


def create_annotated_pdf(original_pdf_path: str, analysis_results: List[Dict[str, object]], project_name: str) -> Optional[str]:
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{project_name}_annotated_{timestamp}.pdf")

        reader = PdfReader(original_pdf_path)
        writer = PdfWriter()

        for page_index, page_result in enumerate(analysis_results):
            if page_index >= len(reader.pages):
                continue

            image: Image.Image = page_result['image']  # type: ignore[assignment]
            draw = ImageDraw.Draw(image)

            try:
                font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 30)
            except Exception:
                font = ImageFont.load_default()

            for point in page_result['automation_points']:
                x, y = point['x'], point['y']
                draw.ellipse([x - 20, y - 20, x + 20, y + 20], fill='#556B2F', outline='white', width=2)
                draw.text((x, y), point['symbol'], fill='white', font=font, anchor='mm')

            for text_info in page_result.get('text_annotations', []):
                x = text_info['x']
                y = text_info['y']
                w = text_info['width']
                h = text_info['height']
                draw.rectangle([x, y, x + w, y + h], outline='#2F4F4F', width=2)
                draw.text((x + w / 2, y - 5), text_info['text'], fill='#2F4F4F', font=font, anchor='mb')

            for line in page_result.get('line_segments', []):
                draw.line([line['x1'], line['y1'], line['x2'], line['y2']], fill='#8FBC8F', width=3)

            temp_img_path = os.path.join(app.config['OUTPUT_FOLDER'], f'temp_{page_index}.png')
            temp_pdf_path = os.path.join(app.config['OUTPUT_FOLDER'], f'temp_{page_index}.pdf')

            image.save(temp_img_path)
            pdf_canvas = canvas.Canvas(temp_pdf_path, pagesize=(image.width, image.height))
            pdf_canvas.drawImage(temp_img_path, 0, 0, width=image.width, height=image.height)
            pdf_canvas.save()

            temp_reader = PdfReader(temp_pdf_path)
            writer.add_page(temp_reader.pages[0])

            if os.path.exists(temp_img_path):
                os.remove(temp_img_path)
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)

        with open(output_path, 'wb') as output_file:
            writer.write(output_file)

        return output_path
    except Exception as exc:
        print(f"Error creating annotated PDF: {exc}")
        return None


def generate_quote_pdf(
    analysis_results: List[Dict[str, object]],
    automation_types: List[str],
    project_name: str,
    automation_tier_key: str,
) -> Optional[str]:
    try:
        data = load_data()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{project_name}_quote_{timestamp}.pdf")

        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story: List[Paragraph] = []

        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#556B2F'),
            spaceAfter=30,
            alignment=1,
        )

        story.append(Paragraph(data['company_info'].get('name', 'Lock Zone Automation'), title_style))  # type: ignore[index]
        story.append(Paragraph(f"Project: {project_name}", styles['Heading2']))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
        story.append(Spacer(1, 20))

        total_rooms = sum(page['room_count'] for page in analysis_results)
        total_points = sum(len(page['automation_points']) for page in analysis_results)
        total_text = sum(len(page.get('text_annotations', [])) for page in analysis_results)
        total_lines = sum(len(page.get('line_segments', [])) for page in analysis_results)

        default_tier = DEFAULT_AUTOMATION_TIERS.get('basic', {"name": "Basic", "price_multiplier": 1.0})
        tier_info = data.get('automation_tiers', {}).get(automation_tier_key, default_tier)  # type: ignore[index]
        tier_name = tier_info.get('name', automation_tier_key.title())

        system_names: List[str] = []
        for system_key in automation_types:
            type_info = data['automation_types'].get(system_key, {})  # type: ignore[index]
            if isinstance(type_info, dict):
                system_names.append(type_info.get('name', system_key.replace('_', ' ').title()))
            else:
                system_names.append(system_key.replace('_', ' ').title())

        summary_data = [
            ['Total Pages', str(len(analysis_results))],
            ['Detected Rooms', str(total_rooms)],
            ['Automation Points', str(total_points)],
            ['Recognized Text Entries', str(total_text)],
            ['Detected Structural Lines', str(total_lines)],
            ['Systems', ', '.join(system_names) if system_names else '—'],
            ['Automation Tier', tier_name],
        ]

        summary_table = Table(summary_data, colWidths=[3 * inch, 3 * inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#556B2F')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))

        story.append(summary_table)
        story.append(Spacer(1, 20))

        cost_data: List[List[str]] = [['System', 'Units', 'Cost/Unit', 'Labor Hrs', 'Subtotal']]
        total_cost = 0.0

        for automation_type in automation_types:
            type_data = data['automation_types'].get(automation_type, {})  # type: ignore[index]
            if not isinstance(type_data, dict):
                continue

            units = sum(1 for page in analysis_results for point in page['automation_points'] if point['type'] == automation_type)
            if units == 0:
                continue

            cost_per_unit = type_data.get('base_cost_per_unit', 100)
            labor_hours_per_unit = type_data.get('labor_hours', 1)
            labor_hours = labor_hours_per_unit * units if isinstance(labor_hours_per_unit, (int, float)) else units

            subtotal = (cost_per_unit * units) + (labor_hours * data['labor_rate'])  # type: ignore[index]
            total_cost += subtotal

            cost_data.append([
                type_data.get('name', automation_type.replace('_', ' ').title()),
                str(units),
                f"${float(cost_per_unit):,.2f}",
                f"{float(labor_hours):.1f}",
                f"${float(subtotal):,.2f}",
            ])

        cost_table = Table(cost_data, colWidths=[2 * inch, 0.8 * inch, 1.2 * inch, 1 * inch, 1.2 * inch])
        cost_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#556B2F')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))

        story.append(cost_table)
        story.append(Spacer(1, 20))

        markup = total_cost * (data['markup_percentage'] / 100)  # type: ignore[index]
        base_total = total_cost + markup
        tier_multiplier = tier_info.get('price_multiplier', 1.0)
        tier_adjustment = base_total * (tier_multiplier - 1)
        final_total = base_total + tier_adjustment

        totals_data = [
            ['Subtotal', f"${total_cost:,.2f}"],
            [f"Markup ({data['markup_percentage']:.0f}%)", f"${markup:,.2f}"],  # type: ignore[index]
            [f"Tier Adjustment ({tier_name})", f"${tier_adjustment:,.2f}"],
            ['TOTAL', f"${final_total:,.2f}"],
        ]

        totals_table = Table(totals_data, colWidths=[4 * inch, 2 * inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 14),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#556B2F')),
        ]))

        story.append(totals_table)
        doc.build(story)
        return output_path
    except Exception as exc:
        print(f"Error creating quote PDF: {exc}")
        return None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/data', methods=['GET', 'POST'])
def manage_data():
    if request.method == 'GET':
        return jsonify({'success': True, 'data': load_data()})

    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return error_response('Invalid JSON payload provided for automation data update.')

    if not isinstance(payload, dict):
        return error_response('Automation data updates must be provided as a JSON object.')

    existing = load_data()
    updated = _deep_merge(copy.deepcopy(existing), payload)
    updated = _merge_with_defaults(updated)
    save_data(updated)

    return jsonify({'success': True, 'data': updated})


@app.route('/api/analyze', methods=['POST'])
def analyze_floor_plan():
    try:
        if 'floorplan' not in request.files:
            return error_response('No file uploaded')

        file = request.files['floorplan']
        if not file.filename:
            return error_response('No file selected')

        project_name = request.form.get('project_name', 'Untitled')
        automation_types = request.form.getlist('automation_types[]')
        automation_tier = request.form.get('automation_tier', 'basic')

        if not automation_types:
            return error_response('No automation types selected')

        data = load_data()
        default_tier = DEFAULT_AUTOMATION_TIERS.get('basic', {"name": "Basic", "price_multiplier": 1.0})
        tiers = data.get('automation_tiers', {})  # type: ignore[index]
        tier_key = automation_tier if automation_tier in tiers else 'basic'
        tier_info = tiers.get(tier_key, default_tier)
        tier_multiplier = tier_info.get('price_multiplier', 1.0)
        tier_name = tier_info.get('name', tier_key.title())

        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{timestamp}_{filename}")
        file.save(upload_path)

        analyzer = FloorPlanAnalyzer()
        analysis_results = analyzer.analyze_pdf(upload_path, automation_types)

        if not analysis_results:
            return error_response('Could not analyze floor plan. Please verify the PDF quality and try again.')

        annotated_pdf = create_annotated_pdf(upload_path, analysis_results, project_name)
        quote_pdf = generate_quote_pdf(analysis_results, automation_types, project_name, tier_key)

        total_rooms = sum(page['room_count'] for page in analysis_results)
        total_points = sum(len(page['automation_points']) for page in analysis_results)
        total_text = sum(len(page.get('text_annotations', [])) for page in analysis_results)
        total_lines = sum(len(page.get('line_segments', [])) for page in analysis_results)

        total_cost = 0.0
        for automation_type in automation_types:
            type_data = data['automation_types'].get(automation_type, {})  # type: ignore[index]
            if not isinstance(type_data, dict):
                continue

            units = sum(1 for page in analysis_results for point in page['automation_points'] if point['type'] == automation_type)
            cost_per_unit = type_data.get('base_cost_per_unit', 100)
            labor_hours_per_unit = type_data.get('labor_hours', 1)
            labor_hours = labor_hours_per_unit * units if isinstance(labor_hours_per_unit, (int, float)) else units
            total_cost += (cost_per_unit * units) + (labor_hours * data['labor_rate'])  # type: ignore[index]

        markup = total_cost * (data['markup_percentage'] / 100)  # type: ignore[index]
        base_total = total_cost + markup
        tier_adjustment = base_total * (tier_multiplier - 1)
        final_total = base_total + tier_adjustment

        return jsonify({
            'success': True,
            'project_name': project_name,
            'total_rooms': total_rooms,
            'total_automation_points': total_points,
            'recognized_text_entries': total_text,
            'detected_structural_lines': total_lines,
            'total_cost': f"${final_total:,.2f}",
            'base_cost': f"${base_total:,.2f}",
            'tier_adjustment': f"${tier_adjustment:,.2f}",
            'automation_tier': tier_name,
            'annotated_pdf': os.path.basename(annotated_pdf) if annotated_pdf else None,
            'quote_pdf': os.path.basename(quote_pdf) if quote_pdf else None,
        })
    except Exception as exc:
        print(f"Error during analysis: {exc}")
        return error_response('An unexpected error occurred while generating the quote. Please try again.', 500)


@app.route('/api/download/<path:filename>')
def download_file(filename: str):
    try:
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        return error_response('File not found', 404)
    except Exception as exc:
        print(f"Download error: {exc}")
        return error_response('Failed to download the requested file.', 500)


@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
