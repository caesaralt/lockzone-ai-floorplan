from __future__ import annotations

import copy
import json
<<<<<<< HEAD
import copy
=======
 codex/improve-floor-plan-analysis-accuracy-yrju1a
import os

import copy
 main
>>>>>>> 0b16d33a167d8415c0a81ab4c02a2135a12d60de
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from flask import Flask, jsonify, render_template, request, send_file
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
<<<<<<< HEAD
import tempfile
import traceback
import gc
=======
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

>>>>>>> 0b16d33a167d8415c0a81ab4c02a2135a12d60de

app = Flask(__name__)
CORS(app)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['DATA_FOLDER'] = 'data'
app.config['TRAINING_FOLDER'] = 'training_data'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

<<<<<<< HEAD
for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER'], 
               app.config['DATA_FOLDER'], app.config['TRAINING_FOLDER']]:
=======
for folder in (app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER'], app.config['DATA_FOLDER']):
>>>>>>> 0b16d33a167d8415c0a81ab4c02a2135a12d60de
    os.makedirs(folder, exist_ok=True)

DATA_FILE = os.path.join(app.config['DATA_FOLDER'], 'automation_data.json')
TRAINING_FILE = os.path.join(app.config['DATA_FOLDER'], 'training_data.json')

 codex/improve-floor-plan-analysis-accuracy-yrju1a
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

DEFAULT_DATA = {
    "automation_types": {
<<<<<<< HEAD
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
            "symbols": ["🌡️"],
            "base_cost_per_unit": {"basic": 400.0, "premium": 700.0, "deluxe": 1200.0},
            "labor_hours": {"basic": 5.0, "premium": 6.5, "deluxe": 8.5},
            "description": "Climate management system"
        },
        "hvac_energy": {
            "name": "HVAC & Energy",
            "symbols": ["⚡"],
            "base_cost_per_unit": {"basic": 420.0, "premium": 750.0, "deluxe": 1300.0},
            "labor_hours": {"basic": 5.5, "premium": 7.0, "deluxe": 9.0},
            "description": "HVAC and energy management"
        },
        "multiroom_audio": {
            "name": "Multiroom Audio",
            "symbols": ["🎶"],
            "base_cost_per_unit": {"basic": 360.0, "premium": 650.0, "deluxe": 1100.0},
            "labor_hours": {"basic": 3.5, "premium": 5.0, "deluxe": 7.0},
            "description": "Multi-room audio system"
        },
        "wellness_garden": {
            "name": "Wellness & Garden",
            "symbols": ["🌿"],
            "base_cost_per_unit": {"basic": 280.0, "premium": 500.0, "deluxe": 850.0},
            "labor_hours": {"basic": 3.0, "premium": 4.5, "deluxe": 6.0},
            "description": "Wellness and garden automation"
        }
=======
        "lighting": {"name": "Lighting Control", "symbols": ["💡"], "base_cost_per_unit": 150.0, "labor_hours": 2.0},
        "shading": {"name": "Shading Control", "symbols": ["🪟"], "base_cost_per_unit": 300.0, "labor_hours": 3.0},
        "security_access": {"name": "Security & Access", "symbols": ["🔐"], "base_cost_per_unit": 500.0, "labor_hours": 4.5},
        "climate": {"name": "Climate Control", "symbols": ["🌡️"], "base_cost_per_unit": 400.0, "labor_hours": 5.0},
        "hvac_energy": {"name": "HVAC & Energy", "symbols": ["⚡"], "base_cost_per_unit": 420.0, "labor_hours": 5.5},
        "multiroom_audio": {"name": "Multiroom Audio", "symbols": ["🎶"], "base_cost_per_unit": 360.0, "labor_hours": 3.5},
        "wellness_garden": {"name": "Wellness & Garden", "symbols": ["🌿"], "base_cost_per_unit": 280.0, "labor_hours": 3.0}
>>>>>>> 0b16d33a167d8415c0a81ab4c02a2135a12d60de
    },
main
    "labor_rate": 75.0,
    "markup_percentage": 20.0,
<<<<<<< HEAD
    "company_info": {
        "name": "Lock Zone Automation",
        "address": "",
        "phone": "",
        "email": ""
    },
    "tier_descriptions": {
        "basic": "Entry-level automation with essential features",
        "premium": "Advanced automation with premium features",
        "deluxe": "Top-tier automation with all premium features"
    }
=======
    "company_info": {"name": "Lock Zone Automation", "address": "", "phone": "", "email": ""},
>>>>>>> 0b16d33a167d8415c0a81ab4c02a2135a12d60de
}

 codex/improve-floor-plan-analysis-accuracy-yrju1a
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
 main

    return merged


 codex/improve-floor-plan-analysis-accuracy-yrju1a
def load_data() -> Dict[str, object]:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
<<<<<<< HEAD
                loaded = json.load(f)
                for key in DEFAULT_DATA:
                    if key not in loaded:
                        loaded[key] = DEFAULT_DATA[key]
                for auto_type in loaded.get('automation_types', {}).values():
                    if isinstance(auto_type.get('base_cost_per_unit'), (int, float)):
                        auto_type['base_cost_per_unit'] = {
                            "basic": auto_type['base_cost_per_unit'],
                            "premium": auto_type['base_cost_per_unit'] * 1.5,
                            "deluxe": auto_type['base_cost_per_unit'] * 2.5
                        }
                    if isinstance(auto_type.get('labor_hours'), (int, float)):
                        auto_type['labor_hours'] = {
                            "basic": auto_type['labor_hours'],
                            "premium": auto_type['labor_hours'] * 1.3,
                            "deluxe": auto_type['labor_hours'] * 1.7
                        }
                return loaded
        except Exception as e:
            print(f"Error loading data: {e}")
            return copy.deepcopy(DEFAULT_DATA)
    return copy.deepcopy(DEFAULT_DATA)

def save_data(data):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving data: {e}")

class AdvancedFloorPlanAnalyzer:
    def __init__(self):
        self.data = load_data()
        self.training_data = self.load_training_data()
    
    def load_training_data(self):
        if os.path.exists(TRAINING_FILE):
            try:
                with open(TRAINING_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {"examples": [], "patterns": {}}
        return {"examples": [], "patterns": {}}
    
    def save_training_data(self):
        try:
            with open(TRAINING_FILE, 'w') as f:
                json.dump(self.training_data, f, indent=2)
        except Exception as e:
            print(f"Error saving training data: {e}")
    
    def analyze_pdf(self, pdf_path, automation_types, tier="basic"):
        results = []
        try:
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            
            for page_number in range(1, total_pages + 1):
                try:
                    print(f"Processing page {page_number}/{total_pages}")
                    
                    images = convert_from_path(
                        pdf_path,
                        dpi=250,
                        first_page=page_number,
                        last_page=page_number,
                        fmt="png",
                        thread_count=1,
                    )
                    
                    if not images:
                        continue
                    
                    img = images[0]
                    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                    
                    analysis = self._advanced_analyze(img_cv, automation_types, tier)
                    analysis['page_number'] = page_number
                    analysis['image'] = img
                    results.append(analysis)
                    
                    del img_cv
                    del images
                    gc.collect()
                    
                except Exception as e:
                    print(f"Error on page {page_number}: {e}")
                    traceback.print_exc()
                    continue
            
            return results
            
        except Exception as e:
            print(f"Critical error in analyze_pdf: {e}")
            traceback.print_exc()
            return []
    
    def _advanced_analyze(self, image, automation_types, tier):
        height, width = image.shape[:2]
        
        rooms_edges = self._detect_rooms_enhanced_edges(image)
        rooms_contours = self._detect_rooms_ml_contours(image)
        rooms_lines = self._detect_rooms_advanced_lines(image)
        rooms_color = self._detect_rooms_color_segmentation(image)
        
        all_rooms = rooms_edges + rooms_contours + rooms_lines + rooms_color
        rooms = self._intelligent_merge(all_rooms, overlap_threshold=0.5)
        rooms = self._advanced_filter(rooms, width, height)
        
        rooms.sort(key=lambda r: r.get('confidence', 0), reverse=True)
        primary_rooms = rooms[:50]
        
        automation_points = self._generate_automation_points(
            primary_rooms, automation_types, tier
        )
        
=======
 main
                return _merge_with_defaults(json.load(f))
        except Exception:
            return copy.deepcopy(DEFAULT_DATA)
    return copy.deepcopy(DEFAULT_DATA)

 codex/improve-floor-plan-analysis-accuracy-yrju1a

def save_data(data: Dict[str, object]) -> None:
    with open(DATA_FILE, 'w', encoding='utf-8') as f:

def save_data(data):
    with open(DATA_FILE, 'w') as f:
 main
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
 codex/improve-floor-plan-analysis-accuracy-yrju1a
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
 main

            return results
        except Exception as exc:
            print(f"Error analyzing PDF: {exc}")
            return []

    def _analyze_image(self, image: np.ndarray, automation_types: List[str]) -> Dict[str, object]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
 codex/improve-floor-plan-analysis-accuracy-yrju1a
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)

        # Combine adaptive thresholding with edge reinforced masks so larger rooms stay intact.
        adaptive = cv2.adaptiveThreshold(
            denoised,

        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        adaptive = cv2.adaptiveThreshold(
            blurred,
 main
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            35,
            5,
        )

 codex/improve-floor-plan-analysis-accuracy-yrju1a
        canny = cv2.Canny(denoised, 40, 120)
        canny_dilated = cv2.dilate(canny, np.ones((3, 3), np.uint8), iterations=1)

        combined_mask = cv2.bitwise_or(adaptive, canny_dilated)
        closed = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=2)
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1)

        room_candidates, room_confidence = self._extract_rooms(opened, image.shape[:2])
        automation_points = self._generate_automation_points(room_candidates, automation_types)

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
            'rooms': room_candidates,
            'room_count': len(room_candidates),
            'automation_points': automation_points,
            'image_shape': image.shape,
            'text_annotations': text_annotations,
            'line_segments': line_segments,
            'room_detection_score': room_confidence,
        }

    def _extract_rooms(self, mask: np.ndarray, image_shape: Tuple[int, int]) -> Tuple[List[Dict[str, object]], float]:
        height, width = image_shape
        min_area = max(1500, int(0.0008 * height * width))
        max_area = int(0.5 * height * width)

        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)

        rooms: List[Dict[str, object]] = []
        confidences: List[float] = []

        for label in range(1, num_labels):
            area = stats[label, cv2.CC_STAT_AREA]
            if area < min_area or area > max_area:
                continue

            x = stats[label, cv2.CC_STAT_LEFT]
            y = stats[label, cv2.CC_STAT_TOP]
            w = stats[label, cv2.CC_STAT_WIDTH]
            h = stats[label, cv2.CC_STAT_HEIGHT]

            if w < 40 or h < 40:
                continue

            aspect_ratio = w / float(h) if h else 0
            if not (0.35 < aspect_ratio < 3.2):
                continue

            region = mask[y : y + h, x : x + w]
            fill_ratio = float(cv2.countNonZero(region)) / float(region.size)
            if fill_ratio < 0.35:
                continue

            cx, cy = centroids[label]
            rooms.append({
                'x': int(x),
                'y': int(y),
                'width': int(w),
                'height': int(h),
                'area': float(area),
                'center': (int(cx), int(cy)),
                'fill_ratio': round(fill_ratio, 3),
            })

            confidences.append(min(1.0, fill_ratio * 1.15))

        rooms.sort(key=lambda item: item['area'], reverse=True)
        top_rooms = rooms[:30]
        average_confidence = float(np.mean(confidences)) if confidences else 0.0
        return top_rooms, round(average_confidence, 3)

    def _generate_automation_points(self, rooms: List[Dict[str, object]], automation_types: List[str]) -> List[Dict[str, object]]:
        points: List[Dict[str, object]] = []

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

>>>>>>> 0b16d33a167d8415c0a81ab4c02a2135a12d60de
        return {
            'rooms': primary_rooms,
            'room_count': len(rooms),
            'automation_points': automation_points,
            'image_shape': image.shape,
<<<<<<< HEAD
            'confidence': np.mean([r.get('confidence', 0.5) for r in primary_rooms]) if primary_rooms else 0.0
=======
>>>>>>> 0b16d33a167d8415c0a81ab4c02a2135a12d60de
        }
    
    def _detect_rooms_enhanced_edges(self, image):
        rooms = []
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            denoised = cv2.fastNlMeansDenoising(gray, None, h=15, templateWindowSize=7, searchWindowSize=21)
            
            edges = np.zeros_like(gray)
            for low, high in [(20, 80), (40, 120), (60, 160)]:
                edge = cv2.Canny(denoised, low, high)
                edges = cv2.bitwise_or(edges, edge)
            
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            dilated = cv2.dilate(edges, kernel, iterations=3)
            closed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel, iterations=4)
            
            contours, hierarchy = cv2.findContours(closed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                if area < 500:
                    continue
                
                x, y, w, h = cv2.boundingRect(contour)
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                else:
                    cx, cy = x + w // 2, y + h // 2
                
                confidence = 0.7
                if hierarchy is not None and hierarchy[0][i][3] == -1:
                    confidence = 0.9
                
                rooms.append({
                    'x': int(x), 'y': int(y), 'width': int(w), 'height': int(h),
                    'area': float(area), 'center': (cx, cy),
                    'method': 'edge', 'confidence': confidence
                })
        except Exception as e:
            print(f"Edge detection error: {e}")
        
        return rooms
    
    def _detect_rooms_ml_contours(self, image):
        rooms = []
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            bilateral = cv2.bilateralFilter(gray, 11, 85, 85)
            
            _, thresh1 = cv2.threshold(bilateral, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            thresh2 = cv2.adaptiveThreshold(bilateral, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY_INV, 25, 10)
            
            combined = cv2.bitwise_or(thresh1, thresh2)
            
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
            cleaned = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=3)
            cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel, iterations=1)
            
            contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 800:
                    continue
                
                perimeter = cv2.arcLength(contour, True)
                if perimeter == 0:
                    continue
                
                approx = cv2.approxPolyDP(contour, 0.015 * perimeter, True)
                
                x, y, w, h = cv2.boundingRect(approx)
                M = cv2.moments(approx)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                else:
                    cx, cy = x + w // 2, y + h // 2
                
                vertices = len(approx)
                confidence = 0.8 if 4 <= vertices <= 12 else 0.6
                
                rooms.append({
                    'x': int(x), 'y': int(y), 'width': int(w), 'height': int(h),
                    'area': float(area), 'center': (cx, cy),
                    'method': 'contour', 'confidence': confidence
                })
        except Exception as e:
            print(f"Contour detection error: {e}")
        
        return rooms
    
    def _detect_rooms_advanced_lines(self, image):
        rooms = []
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 40, 120, apertureSize=3)
            
            lines = cv2.HoughLinesP(edges, rho=1, theta=np.pi/180, threshold=80,
                                   minLineLength=40, maxLineGap=15)
            
            if lines is not None:
                line_image = np.zeros_like(gray)
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    cv2.line(line_image, (x1, y1), (x2, y2), 255, 3)
                
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
                closed = cv2.morphologyEx(line_image, cv2.MORPH_CLOSE, kernel, iterations=6)
                
                contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area < 1000:
                        continue
                    
                    x, y, w, h = cv2.boundingRect(contour)
                    cx, cy = x + w // 2, y + h // 2
                    
                    rooms.append({
                        'x': int(x), 'y': int(y), 'width': int(w), 'height': int(h),
                        'area': float(area), 'center': (cx, cy),
                        'method': 'line', 'confidence': 0.85
                    })
        except Exception as e:
            print(f"Line detection error: {e}")
        
        return rooms
    
    def _detect_rooms_color_segmentation(self, image):
        rooms = []
        try:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            pixels = lab.reshape((-1, 3))
            pixels = np.float32(pixels)
            
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            k = 5
            _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_PP_CENTERS)
            
            labels = labels.reshape(image.shape[:2])
            
            for i in range(k):
                mask = (labels == i).astype(np.uint8) * 255
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area < 1500:
                        continue
                    
                    x, y, w, h = cv2.boundingRect(contour)
                    cx, cy = x + w // 2, y + h // 2
                    
                    rooms.append({
                        'x': int(x), 'y': int(y), 'width': int(w), 'height': int(h),
                        'area': float(area), 'center': (cx, cy),
                        'method': 'color', 'confidence': 0.75
                    })
        except Exception as e:
            print(f"Color segmentation error: {e}")
        
        return rooms
    
    def _intelligent_merge(self, rooms, overlap_threshold=0.5):
        if not rooms:
            return []
        
        merged = []
        used = set()
        
        rooms.sort(key=lambda r: r.get('confidence', 0), reverse=True)
        
        for i, room1 in enumerate(rooms):
            if i in used:
                continue
            
            current = room1.copy()
            votes = [current['confidence']]
            used.add(i)
            
            for j, room2 in enumerate(rooms[i+1:], start=i+1):
                if j in used:
                    continue
                
                overlap = self._calculate_overlap(room1, room2)
                
                if overlap > overlap_threshold:
                    x_min = min(current['x'], room2['x'])
                    y_min = min(current['y'], room2['y'])
                    x_max = max(current['x'] + current['width'], room2['x'] + room2['width'])
                    y_max = max(current['y'] + current['height'], room2['y'] + room2['height'])
                    
                    current['x'] = x_min
                    current['y'] = y_min
                    current['width'] = x_max - x_min
                    current['height'] = y_max - y_min
                    current['area'] = current['width'] * current['height']
                    current['center'] = (x_min + current['width'] // 2, y_min + current['height'] // 2)
                    current['confidence'] = (current['confidence'] + room2['confidence']) / 2
                    
                    votes.append(room2['confidence'])
                    used.add(j)
            
            if len(votes) > 1:
                current['confidence'] = min(0.99, current['confidence'] * 1.2)
            
            merged.append(current)
        
        return merged
    
    def _calculate_overlap(self, room1, room2):
        x1_min, y1_min = room1['x'], room1['y']
        x1_max, y1_max = x1_min + room1['width'], y1_min + room1['height']
        
        x2_min, y2_min = room2['x'], room2['y']
        x2_max, y2_max = x2_min + room2['width'], y2_min + room2['height']
        
        x_int_min = max(x1_min, x2_min)
        y_int_min = max(y1_min, y2_min)
        x_int_max = min(x1_max, x2_max)
        y_int_max = min(y1_max, y2_max)
        
        if x_int_max < x_int_min or y_int_max < y_int_min:
            return 0.0
        
        intersection = (x_int_max - x_int_min) * (y_int_max - y_int_min)
        union = room1['area'] + room2['area'] - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _advanced_filter(self, rooms, image_width, image_height):
        filtered = []
        
        image_area = image_width * image_height
        min_area = image_area * 0.0003
        max_area = image_area * 0.45
        
        for room in rooms:
            if room['area'] < min_area or room['area'] > max_area:
                continue
            
            if room['width'] < 25 or room['height'] < 25:
                continue
            
            aspect = room['width'] / float(room['height']) if room['height'] > 0 else 0
            if not (0.15 < aspect < 6.5):
                continue
            
            if room.get('confidence', 0) < 0.4:
                continue
            
            filtered.append(room)
        
        return filtered
    
    def _generate_automation_points(self, rooms, automation_types, tier):
        points = []
 main
        for room in rooms:
<<<<<<< HEAD
            for auto_type in automation_types:
                type_data = self.data['automation_types'].get(auto_type, {})
                symbol = type_data.get('symbols', ['⚙️'])[0]
                
                cost_per_unit = type_data.get('base_cost_per_unit', {}).get(tier, 100.0)
                labor_hours = type_data.get('labor_hours', {}).get(tier, 1.0)
                
                points.append({
                    'type': auto_type,
=======
            for automation_type in automation_types:
                type_data = self.data['automation_types'].get(automation_type, {})  # type: ignore[index]
                symbol = type_data.get('symbols', ['⚙️'])[0] if isinstance(type_data, dict) else '⚙️'
                points.append({
                    'type': automation_type,
>>>>>>> 0b16d33a167d8415c0a81ab4c02a2135a12d60de
                    'x': room['center'][0],
                    'y': room['center'][1],
                    'room_area': room['area'],
                    'symbol': symbol,
<<<<<<< HEAD
                    'tier': tier,
                    'cost_per_unit': cost_per_unit,
                    'labor_hours': labor_hours,
                    'confidence': room.get('confidence', 0.8)
=======
>>>>>>> 0b16d33a167d8415c0a81ab4c02a2135a12d60de
                })
        return points


def create_annotated_pdf(original_pdf_path: str, analysis_results: List[Dict[str, object]], project_name: str) -> Optional[str]:
    try:
<<<<<<< HEAD
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], 
                                   f"{project_name}_annotated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        
        reader = PdfReader(original_pdf_path)
        writer = PdfWriter()
        
        for page_idx, page_result in enumerate(analysis_results):
            try:
                if page_idx >= len(reader.pages):
                    continue
                
                img = page_result['image'].copy()
                draw = ImageDraw.Draw(img)
                
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 35)
                except:
                    try:
                        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 35)
                    except:
                        font = None
                
                for point in page_result['automation_points']:
                    x, y = point['x'], point['y']
                    draw.ellipse([x-25, y-25, x+25, y+25], fill='#556B2F', outline='white', width=3)
                    if font:
                        draw.text((x, y), point['symbol'], fill='white', font=font, anchor='mm')
                
                temp_img = os.path.join(app.config['OUTPUT_FOLDER'], f'temp_img_{page_idx}.png')
                img.save(temp_img, 'PNG', quality=95)
                
                temp_pdf = os.path.join(app.config['OUTPUT_FOLDER'], f'temp_pdf_{page_idx}.pdf')
                c = canvas.Canvas(temp_pdf, pagesize=(img.width, img.height))
                c.drawImage(temp_img, 0, 0, width=img.width, height=img.height)
                c.save()
                
                temp_reader = PdfReader(temp_pdf)
                writer.add_page(temp_reader.pages[0])
                
                if os.path.exists(temp_img):
                    os.remove(temp_img)
                if os.path.exists(temp_pdf):
                    os.remove(temp_pdf)
                    
            except Exception as e:
                print(f"Error annotating page {page_idx}: {e}")
                continue
        
        with open(output_path, 'wb') as f:
            writer.write(f)
        
        return output_path
        
    except Exception as e:
        print(f"Critical error in create_annotated_pdf: {e}")
        traceback.print_exc()
        return None

def generate_quote_pdf(analysis_results, automation_types, project_name, tier="basic"):
    try:
        data = load_data()
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], 
                                   f"{project_name}_quote_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'],
                                    fontSize=24, textColor=colors.HexColor('#556B2F'),
                                    spaceAfter=30, alignment=1)
        
        story.append(Paragraph(data['company_info'].get('name', 'Lock Zone Automation'), title_style))
        story.append(Paragraph(f"Project: {project_name}", styles['Heading2']))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
        story.append(Paragraph(f"Automation Tier: {tier.upper()}", styles['Heading3']))
        story.append(Spacer(1, 20))
        
        total_rooms = sum(r['room_count'] for r in analysis_results)
        total_points = sum(len(r['automation_points']) for r in analysis_results)
        avg_confidence = np.mean([r.get('confidence', 0) for r in analysis_results])
        
        system_names = []
        for system_key in automation_types:
            type_info = data['automation_types'].get(system_key, {})
            system_names.append(type_info.get('name', system_key.replace('_', ' ').title()))
        
=======
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

codex/improve-floor-plan-analysis-accuracy-yrju1a

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
        average_room_score = round(
            sum(page.get('room_detection_score', 0.0) for page in analysis_results) / len(analysis_results),
            3,
        ) if analysis_results else 0.0

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

>>>>>>> 0b16d33a167d8415c0a81ab4c02a2135a12d60de
        summary_data = [
            ['Total Pages', str(len(analysis_results))],
            ['Detected Rooms', str(total_rooms)],
            ['Automation Points', str(total_points)],
<<<<<<< HEAD
            ['Detection Confidence', f"{avg_confidence*100:.1f}%"],
            ['Systems', ', '.join(system_names) if system_names else '—'],
            ['Tier', tier.upper()]
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
=======
            ['Recognized Text Entries', str(total_text)],
            ['Detected Structural Lines', str(total_lines)],
            ['Room Detection Confidence', f"{average_room_score:.2f}"],
            ['Systems', ', '.join(system_names) if system_names else '—'],
            ['Automation Tier', tier_name],
        ]

        summary_table = Table(summary_data, colWidths=[3 * inch, 3 * inch])
>>>>>>> 0b16d33a167d8415c0a81ab4c02a2135a12d60de
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#556B2F')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
<<<<<<< HEAD
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10)
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        cost_data = [['System', 'Units', 'Cost/Unit', 'Labor Hrs', 'Subtotal']]
        total_cost = 0
        
        for auto_type in automation_types:
            type_data = data['automation_types'].get(auto_type, {})
            units = sum(1 for r in analysis_results for p in r['automation_points'] 
                       if p['type'] == auto_type)
            
            if units > 0:
                cost_per_unit = type_data.get('base_cost_per_unit', {}).get(tier, 100.0)
                labor_hours_per = type_data.get('labor_hours', {}).get(tier, 1.0)
                labor_hours = labor_hours_per * units
                subtotal = (cost_per_unit * units) + (labor_hours * data['labor_rate'])
                total_cost += subtotal
                
                cost_data.append([
                    type_data.get('name', auto_type.title()),
                    str(units),
                    f"${cost_per_unit:,.2f}",
                    f"{labor_hours:.1f}",
                    f"${subtotal:,.2f}"
                ])
        
        cost_table = Table(cost_data, colWidths=[2*inch, 0.8*inch, 1.2*inch, 1*inch, 1.2*inch])
=======
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
 main
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
>>>>>>> 0b16d33a167d8415c0a81ab4c02a2135a12d60de
        cost_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#556B2F')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
<<<<<<< HEAD
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9)
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
=======
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
>>>>>>> 0b16d33a167d8415c0a81ab4c02a2135a12d60de
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 14),
<<<<<<< HEAD
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#556B2F'))
        ]))
        story.append(totals_table)
        
        doc.build(story)
        return output_path
        
    except Exception as e:
        print(f"Critical error in generate_quote_pdf: {e}")
        traceback.print_exc()
        return None
=======
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#556B2F')),
        ]))

        story.append(totals_table)
        doc.build(story)
        return output_path
    except Exception as exc:
        print(f"Error creating quote PDF: {exc}")
        return None

>>>>>>> 0b16d33a167d8415c0a81ab4c02a2135a12d60de

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
<<<<<<< HEAD
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['floorplan']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        project_name = request.form.get('project_name', 'Untitled')
        automation_types = request.form.getlist('automation_types[]')
        tier = request.form.get('tier', 'basic')
        
        if not automation_types:
            return jsonify({'success': False, 'error': 'No automation types selected'}), 400
        
        if tier not in ['basic', 'premium', 'deluxe']:
            tier = 'basic'
        
=======
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

>>>>>>> 0b16d33a167d8415c0a81ab4c02a2135a12d60de
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{timestamp}_{filename}")
        file.save(upload_path)
<<<<<<< HEAD
        
        print(f"Analyzing {filename} with tier {tier}")
        
        analyzer = AdvancedFloorPlanAnalyzer()
        analysis_results = analyzer.analyze_pdf(upload_path, automation_types, tier)
        
        if not analysis_results:
            return jsonify({'success': False, 'error': 'Could not analyze floor plan'}), 400
        
        print(f"Analysis complete. Found {len(analysis_results)} pages")
        
        annotated_pdf = create_annotated_pdf(upload_path, analysis_results, project_name)
        quote_pdf = generate_quote_pdf(analysis_results, automation_types, project_name, tier)
        
        total_rooms = sum(r['room_count'] for r in analysis_results)
        total_points = sum(len(r['automation_points']) for r in analysis_results)
        avg_confidence = np.mean([r.get('confidence', 0) for r in analysis_results])
        
        data = load_data()
        total_cost = 0
        
        for auto_type in automation_types:
            type_data = data['automation_types'].get(auto_type, {})
            units = sum(1 for r in analysis_results for p in r['automation_points'] 
                       if p['type'] == auto_type)
            cost_per_unit = type_data.get('base_cost_per_unit', {}).get(tier, 100.0)
            labor_hours = type_data.get('labor_hours', {}).get(tier, 1.0) * units
            total_cost += (cost_per_unit * units) + (labor_hours * data['labor_rate'])
        
        markup = total_cost * (data['markup_percentage'] / 100)
        final_total = total_cost + markup
        
        print(f"Quote generated. Total: ${final_total:,.2f}")
        
=======

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
        average_room_score = round(
            sum(page.get('room_detection_score', 0.0) for page in analysis_results) / len(analysis_results),
            3,
        ) if analysis_results else 0.0

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

>>>>>>> 0b16d33a167d8415c0a81ab4c02a2135a12d60de
        return jsonify({
            'success': True,
            'project_name': project_name,
            'total_rooms': total_rooms,
            'total_automation_points': total_points,
            'recognized_text_entries': total_text,
            'detected_structural_lines': total_lines,
            'room_detection_score': average_room_score,
            'total_cost': f"${final_total:,.2f}",
<<<<<<< HEAD
            'confidence': f"{avg_confidence*100:.1f}%",
            'tier': tier.upper(),
=======
            'base_cost': f"${base_total:,.2f}",
            'tier_adjustment': f"${tier_adjustment:,.2f}",
            'automation_tier': tier_name,
>>>>>>> 0b16d33a167d8415c0a81ab4c02a2135a12d60de
            'annotated_pdf': os.path.basename(annotated_pdf) if annotated_pdf else None,
            'quote_pdf': os.path.basename(quote_pdf) if quote_pdf else None,
        })
<<<<<<< HEAD
        
    except Exception as e:
        error_msg = str(e)
        print(f"ERROR in analyze_floor_plan: {error_msg}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Analysis failed: {error_msg}'}), 500
=======
    except Exception as exc:
        print(f"Error during analysis: {exc}")
        return error_response('An unexpected error occurred while generating the quote. Please try again.', 500)
>>>>>>> 0b16d33a167d8415c0a81ab4c02a2135a12d60de


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


@app.route('/api/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        try:
            new_data = request.json
            save_data(new_data)
            return jsonify({'success': True, 'message': 'Configuration updated'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        return jsonify(load_data())

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'version': '2.0'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
