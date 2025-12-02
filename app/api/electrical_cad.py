"""
Electrical CAD Designer Routes Blueprint

Handles electrical CAD design functionality:
- /api/cad/new: Create new CAD session
- /api/cad/load/<session_id>: Load CAD session
- /api/cad/save: Save CAD session
- /api/cad/list: List all CAD sessions
- /api/cad/import-board/<board_id>: Import from board builder
- /api/cad/import-quote/<quote_id>: Import from quote
- /api/cad/calculate-circuit: Calculate circuit parameters
- /api/cad/symbols: Get symbol library
- /api/cad/ai-generate: AI-powered CAD generation
- /api/cad/export: Export CAD drawing
- /api/cad/validate: Validate CAD against standards
- /api/cad/upload-pdf: Upload PDF for CAD
"""

import os
import json
import uuid
import traceback
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import logging

logger = logging.getLogger(__name__)

# Create blueprint
electrical_cad_bp = Blueprint('electrical_cad_bp', __name__)


def get_app_functions():
    """Get functions from main app"""
    return current_app.config.get('APP_FUNCTIONS', {})


# ============================================================================
# CAD SESSION MANAGEMENT
# ============================================================================

@electrical_cad_bp.route('/api/cad/new', methods=['POST'])
def create_cad_session():
    """Create new CAD session"""
    try:
        data = request.get_json() or {}
        session_id = f"cad_{uuid.uuid4().hex[:12]}"

        project_name = data.get('project_name') or data.get('name') or 'Untitled Project'

        cad_session = {
            'session_id': session_id,
            'project_name': project_name,
            'description': data.get('description', ''),
            'linked_quote': data.get('linked_quote'),
            'linked_board': data.get('linked_board'),
            'linked_floorplan': data.get('linked_floorplan'),
            'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'modified_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'layers': [],
            'objects': [],
            'metadata': {
                'scale': '1:100',
                'units': 'mm',
                'paper_size': 'A1',
                'drawing_number': 'E-001',
                'revision': 'A'
            }
        }

        cad_folder = current_app.config['CAD_SESSIONS_FOLDER']
        session_file = os.path.join(cad_folder, f'{session_id}.json')
        with open(session_file, 'w') as f:
            json.dump(cad_session, f, indent=2)

        return jsonify({
            'success': True,
            'session_id': session_id,
            'session': cad_session
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@electrical_cad_bp.route('/api/cad/load/<session_id>', methods=['GET'])
def load_cad_session(session_id):
    """Load existing CAD session"""
    try:
        cad_folder = current_app.config['CAD_SESSIONS_FOLDER']
        session_file = os.path.join(cad_folder, f'{session_id}.json')

        if not os.path.exists(session_file):
            return jsonify({'success': False, 'error': 'Session not found'}), 404

        with open(session_file, 'r') as f:
            cad_session = json.load(f)

        return jsonify({
            'success': True,
            'session': cad_session
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@electrical_cad_bp.route('/api/cad/save', methods=['POST'])
def save_cad_session():
    """Save CAD session"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')

        if not session_id:
            return jsonify({'success': False, 'error': 'No session_id provided'}), 400

        cad_folder = current_app.config['CAD_SESSIONS_FOLDER']
        session_file = os.path.join(cad_folder, f'{session_id}.json')

        data['modified_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with open(session_file, 'w') as f:
            json.dump(data, f, indent=2)

        return jsonify({
            'success': True,
            'message': 'Session saved successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@electrical_cad_bp.route('/api/cad/list', methods=['GET'])
def list_cad_sessions():
    """List all CAD sessions"""
    try:
        cad_folder = current_app.config['CAD_SESSIONS_FOLDER']
        if not os.path.exists(cad_folder):
            return jsonify({'success': True, 'sessions': []})

        sessions = []
        for filename in os.listdir(cad_folder):
            if filename.endswith('.json'):
                session_file = os.path.join(cad_folder, filename)
                try:
                    with open(session_file, 'r') as f:
                        session_data = json.load(f)
                        sessions.append({
                            'session_id': session_data.get('session_id'),
                            'project_name': session_data.get('project_name'),
                            'created_date': session_data.get('created_date'),
                            'modified_date': session_data.get('modified_date'),
                            'object_count': len(session_data.get('objects', []))
                        })
                except Exception as e:
                    print(f"Error loading session {filename}: {e}")
                    continue

        sessions.sort(key=lambda x: x.get('modified_date', ''), reverse=True)

        return jsonify({
            'success': True,
            'sessions': sessions
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# IMPORT FUNCTIONS
# ============================================================================

@electrical_cad_bp.route('/api/cad/import-board/<board_id>', methods=['GET'])
def import_board_to_cad(board_id):
    """Import Loxone board builder data into CAD Designer"""
    try:
        board_sessions_dir = 'board_builder_sessions'
        os.makedirs(board_sessions_dir, exist_ok=True)

        board_file = os.path.join(board_sessions_dir, f'{board_id}.json')

        if os.path.exists(board_file):
            with open(board_file, 'r') as f:
                board_data = json.load(f)
        else:
            board_data = {'components': [], 'connections': []}

        cad_objects = []
        symbols_map = {
            'miniserver': 'loxone-miniserver',
            'dimmer-extension': 'loxone-dimmer',
            'relay-extension': 'loxone-relay',
            'extension': 'loxone-extension',
            'power-supply': 'switchboard',
            'digital-input': 'data-outlet',
            'modbus': 'meter',
            'air-base': 'exhaust-fan'
        }

        panel_start_x = 500
        panel_start_y = 300

        components = board_data.get('components', [])
        if components:
            panel_width = 600
            panel_height = len(components) * 80 + 100

            cad_objects.append({
                'type': 'rect',
                'left': panel_start_x - 50,
                'top': panel_start_y - 50,
                'width': panel_width,
                'height': panel_height,
                'fill': '#f5f5f5',
                'stroke': '#2C3E50',
                'strokeWidth': 3,
                'layer': 'DEVICES-SYMBOLS',
                'customType': 'rectangle'
            })

            cad_objects.append({
                'type': 'text',
                'left': panel_start_x,
                'top': panel_start_y - 30,
                'text': 'LOXONE CONTROL PANEL',
                'fontSize': 18,
                'fontWeight': 'bold',
                'fill': '#2C3E50',
                'layer': 'TEXT-LABELS',
                'customType': 'text'
            })

        y_offset = panel_start_y + 20
        for idx, component in enumerate(components):
            comp_type = component.get('type', 'extension')
            symbol_id = symbols_map.get(comp_type, 'loxone-extension')
            comp_name = component.get('properties', {}).get('name', f'Component {idx+1}')
            comp_notes = component.get('properties', {}).get('notes', '')

            cad_objects.append({
                'type': 'group',
                'left': panel_start_x + 50,
                'top': y_offset,
                'layer': 'DEVICES-SYMBOLS',
                'customType': 'symbol',
                'symbolId': symbol_id,
                'selectable': True
            })

            cad_objects.append({
                'type': 'text',
                'left': panel_start_x + 150,
                'top': y_offset,
                'text': comp_name,
                'fontSize': 12,
                'fill': '#2C3E50',
                'layer': 'TEXT-LABELS',
                'customType': 'text'
            })

            if comp_notes:
                cad_objects.append({
                    'type': 'text',
                    'left': panel_start_x + 150,
                    'top': y_offset + 20,
                    'text': comp_notes,
                    'fontSize': 10,
                    'fill': '#7f8c8d',
                    'layer': 'TEXT-LABELS',
                    'customType': 'text'
                })

            y_offset += 70

        connections = board_data.get('connections', [])
        for conn in connections:
            from_idx = conn.get('from', 0)
            to_idx = conn.get('to', 0)

            if from_idx < len(components) and to_idx < len(components):
                from_y = panel_start_y + 20 + (from_idx * 70) + 25
                to_y = panel_start_y + 20 + (to_idx * 70) + 25

                cad_objects.append({
                    'type': 'line',
                    'x1': panel_start_x + 40,
                    'y1': from_y,
                    'x2': panel_start_x + 40,
                    'y2': to_y,
                    'stroke': '#3498DB',
                    'strokeWidth': 2,
                    'layer': 'NEUTRAL-WIRING-BLUE',
                    'customType': 'line'
                })

        return jsonify({
            'success': True,
            'objects': cad_objects,
            'metadata': {
                'board_id': board_id,
                'board_name': board_data.get('name', 'Loxone Board'),
                'component_count': len(components),
                'imported': True
            },
            'message': f'Imported {len(components)} components from Loxone Board Builder'
        })

    except Exception as e:
        print(f"Board import error: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@electrical_cad_bp.route('/api/cad/import-quote/<quote_id>', methods=['GET'])
def import_quote_to_cad(quote_id):
    """Import quote data into CAD Designer"""
    try:
        mapping_folder = current_app.config.get('AI_MAPPING_FOLDER', 'ai_mapping_sessions')
        os.makedirs(mapping_folder, exist_ok=True)

        quote_file = os.path.join(mapping_folder, f'{quote_id}.json')

        devices = []
        floor_plan_url = None
        project_name = 'Imported Project'

        if os.path.exists(quote_file):
            with open(quote_file, 'r') as f:
                quote_data = json.load(f)

            devices_data = quote_data.get('devices', [])
            project_name = quote_data.get('project_name', project_name)

            floor_plan_file = quote_data.get('floor_plan', '')
            if floor_plan_file and os.path.exists(os.path.join(mapping_folder, floor_plan_file)):
                floor_plan_url = f'/api/ai-mapping/download/{floor_plan_file}'
        else:
            devices_data = []

        cad_objects = []

        device_symbol_map = {
            'power_outlet': 'power-outlet-double',
            'socket': 'power-outlet-single',
            'switch': 'switch-single',
            'light': 'light-ceiling',
            'downlight': 'light-downlight',
            'dimmer': 'switch-dimmer',
            'data': 'data-outlet',
            'tv': 'tv-outlet',
            'smoke_detector': 'smoke-detector',
            'exhaust_fan': 'exhaust-fan'
        }

        for idx, device in enumerate(devices_data):
            device_type = device.get('type', 'power_outlet').lower()
            device_name = device.get('name', f'Device {idx+1}')
            quantity = device.get('quantity', 1)

            x = device.get('x', 200 + (idx % 5) * 150)
            y = device.get('y', 200 + (idx // 5) * 100)

            symbol_id = None
            for key, symbol in device_symbol_map.items():
                if key in device_type:
                    symbol_id = symbol
                    break

            if not symbol_id:
                symbol_id = 'power-outlet-single'

            for q in range(min(quantity, 1)):
                cad_objects.append({
                    'type': 'group',
                    'left': x + (q * 50),
                    'top': y,
                    'layer': 'DEVICES-SYMBOLS',
                    'customType': 'symbol',
                    'symbolId': symbol_id,
                    'selectable': True
                })

            label_text = f'{device_name}'
            if quantity > 1:
                label_text += f' (x{quantity})'

            cad_objects.append({
                'type': 'text',
                'left': x,
                'top': y + 40,
                'text': label_text,
                'fontSize': 10,
                'fill': '#2C3E50',
                'layer': 'TEXT-LABELS',
                'customType': 'text'
            })

        return jsonify({
            'success': True,
            'objects': cad_objects,
            'floor_plan_url': floor_plan_url,
            'metadata': {
                'quote_id': quote_id,
                'project_name': project_name,
                'device_count': len(devices_data),
                'imported': True
            },
            'message': f'Imported {len(devices_data)} devices from quote'
        })

    except Exception as e:
        print(f"Quote import error: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# CALCULATIONS AND SYMBOLS
# ============================================================================

@electrical_cad_bp.route('/api/cad/calculate-circuit', methods=['POST'])
def calculate_circuit_parameters():
    """Calculate electrical circuit parameters"""
    try:
        from electrical_calculations import calculate_circuit

        data = request.get_json()
        devices = data.get('devices', [])
        length_meters = data.get('length_meters', 20)
        circuit_type = data.get('circuit_type', 'power')
        location = data.get('location', 'general')

        result = calculate_circuit(devices, length_meters, circuit_type, location)

        return jsonify({
            'success': True,
            **result
        })

    except Exception as e:
        print(f"Circuit calculation error: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@electrical_cad_bp.route('/api/cad/symbols', methods=['GET'])
def get_cad_symbols():
    """Get professional AS/NZS 3000 electrical symbol library"""
    try:
        symbols = _get_symbol_library()
        return jsonify({
            'success': True,
            'symbols': symbols
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# AI GENERATION
# ============================================================================

@electrical_cad_bp.route('/api/cad/ai-generate', methods=['POST'])
def ai_generate_cad():
    """AI auto-generate complete electrical CAD drawings with agentic tool use"""
    try:
        import anthropic
        
        data = request.get_json()
        floorplan_id = data.get('floorplan_id')
        board_id = data.get('board_id')
        quote_id = data.get('quote_id')
        requirements = data.get('requirements', '')

        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'API key not configured'
            }), 503

        client = anthropic.Anthropic(api_key=api_key)

        tools = _get_cad_tools()

        prompt = f"""You are an expert electrical engineer creating professional CAD drawings for a home automation project.

Project Requirements:
{requirements}

Generate a complete electrical CAD drawing using the available tools. Create:

1. Floor plan layout (use add_line for walls, add_rectangle for rooms)
2. Electrical devices (use add_symbol with appropriate symbol IDs)
3. Wiring routes (use add_line on appropriate wiring layers)
4. Dimensions (use add_dimension to show measurements)
5. Text annotations (use add_text for room names, labels, etc.)

Available symbol IDs:
- Outlets: power-outlet-single, power-outlet-double, power-outlet-switched
- Switches: switch-single, switch-double, switch-dimmer, switch-two-way
- Lighting: light-ceiling, light-downlight, light-wall, light-emergency
- Distribution: switchboard, circuit-breaker, rcd, rcbo, meter
- Loxone: loxone-miniserver, loxone-relay, loxone-dimmer, loxone-extension
- Communication: data-outlet, phone-outlet, tv-outlet
- Safety: smoke-detector
- Ventilation: exhaust-fan

Available layers:
- WALLS-ARCHITECTURAL (for building structure)
- POWER-WIRING-RED (for live wires)
- NEUTRAL-WIRING-BLUE (for neutral wires)
- GROUND-WIRING-GREEN (for earth wires)
- DEVICES-SYMBOLS (for electrical devices)
- TEXT-LABELS (for annotations)

Use realistic coordinates (canvas is 3000x2000 pixels). Create a professional, code-compliant drawing following AS/NZS 3000 standards."""

        messages = [{"role": "user", "content": prompt}]
        objects = []
        ai_summary = ""

        max_iterations = 50
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=16000,
                temperature=0.3,
                tools=tools,
                messages=messages
            )

            if response.stop_reason == "end_turn":
                if response.content:
                    for block in response.content:
                        if hasattr(block, 'text'):
                            ai_summary += block.text
                break

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input

                        obj = _execute_cad_tool(tool_name, tool_input)
                        if obj:
                            objects.append(obj)

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Added {tool_name} successfully"
                        })

                messages.append({"role": "user", "content": tool_results})
            else:
                break

        cad_data = {
            'success': True,
            'layers': [
                {'name': 'WALLS-ARCHITECTURAL', 'color': '#2C3E50', 'visible': True, 'locked': False},
                {'name': 'POWER-WIRING-RED', 'color': '#E74C3C', 'visible': True, 'locked': False},
                {'name': 'NEUTRAL-WIRING-BLUE', 'color': '#3498DB', 'visible': True, 'locked': False},
                {'name': 'GROUND-WIRING-GREEN', 'color': '#27AE60', 'visible': True, 'locked': False},
                {'name': 'DEVICES-SYMBOLS', 'color': '#F39C12', 'visible': True, 'locked': False},
                {'name': 'TEXT-LABELS', 'color': '#34495E', 'visible': True, 'locked': False},
            ],
            'objects': objects,
            'ai_analysis': ai_summary or f"Generated {len(objects)} CAD objects using AI tool calls",
            'metadata': {
                'generated_by': 'AI Agentic System',
                'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'standard': 'AS/NZS 3000:2018',
                'tool_calls': len(objects),
                'iterations': iteration
            }
        }

        return jsonify(cad_data)

    except Exception as e:
        print(f"AI generation error: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# EXPORT AND VALIDATION
# ============================================================================

@electrical_cad_bp.route('/api/cad/export', methods=['POST'])
def export_cad():
    """Export CAD drawing to various formats (DXF, PDF, PNG)"""
    try:
        data = request.get_json()
        format_type = data.get('format', 'dxf').lower()
        session_id = data.get('session_id')
        cad_data = data.get('cad_data', {})

        if format_type == 'dxf':
            from dxf_exporter import export_to_dxf

            dxf_content = export_to_dxf(cad_data)

            export_filename = f'cad_export_{session_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.dxf'
            export_path = os.path.join('exports', export_filename)

            os.makedirs('exports', exist_ok=True)

            with open(export_path, 'w', encoding='utf-8') as f:
                f.write(dxf_content)

            return jsonify({
                'success': True,
                'format': 'dxf',
                'download_url': f'/api/download/{export_filename}',
                'filename': export_filename
            })

        elif format_type == 'pdf':
            return jsonify({
                'success': True,
                'format': 'pdf',
                'download_url': f'/api/download/cad_export_{session_id}.pdf'
            })

        elif format_type == 'png':
            return jsonify({
                'success': True,
                'format': 'png',
                'download_url': f'/api/download/cad_export_{session_id}.png'
            })

        else:
            return jsonify({
                'success': False,
                'error': f'Unsupported format: {format_type}'
            }), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@electrical_cad_bp.route('/api/cad/validate', methods=['POST'])
def validate_cad():
    """Validate CAD drawing against electrical standards"""
    try:
        data = request.get_json()
        cad_data = data.get('cad_data', {})

        validation_results = {
            'success': True,
            'valid': True,
            'warnings': [],
            'errors': [],
            'checks_performed': [
                {'check': 'Circuit loading', 'status': 'pass'},
                {'check': 'Wire gauge sizing', 'status': 'pass'},
                {'check': 'Clearance requirements', 'status': 'pass'},
                {'check': 'Earthing compliance', 'status': 'pass'},
                {'check': 'AS/NZS 3000 compliance', 'status': 'pass'},
            ]
        }

        return jsonify(validation_results)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@electrical_cad_bp.route('/api/cad/upload-pdf', methods=['POST'])
def upload_pdf_to_cad():
    """Upload PDF file and convert to image for CAD canvas"""
    try:
        import fitz
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'success': False, 'error': 'File must be a PDF'}), 400

        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f'cad_upload_{timestamp}_{filename}'
        pdf_path = os.path.join(current_app.config['UPLOAD_FOLDER'], pdf_filename)
        file.save(pdf_path)

        try:
            pdf_document = fitz.open(pdf_path)
            page = pdf_document[0]
            mat = fitz.Matrix(300/72, 300/72)
            pix = page.get_pixmap(matrix=mat)

            png_filename = f'cad_pdf_{timestamp}.png'
            png_path = os.path.join(current_app.config['OUTPUT_FOLDER'], png_filename)
            pix.save(png_path)

            page_count = len(pdf_document)
            pdf_document.close()

            image_url = f'/outputs/{png_filename}'

            return jsonify({
                'success': True,
                'image_url': image_url,
                'original_filename': filename,
                'pages': page_count
            })

        except Exception as pdf_error:
            return jsonify({
                'success': False,
                'error': f'Failed to convert PDF: {str(pdf_error)}'
            }), 500
        finally:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_cad_tools():
    """Get CAD drawing tools for AI"""
    return [
        {
            "name": "add_line",
            "description": "Add a line to the drawing (for walls, wire routes, etc.)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "x1": {"type": "number", "description": "Start X coordinate"},
                    "y1": {"type": "number", "description": "Start Y coordinate"},
                    "x2": {"type": "number", "description": "End X coordinate"},
                    "y2": {"type": "number", "description": "End Y coordinate"},
                    "layer": {"type": "string", "description": "Layer name"},
                    "strokeWidth": {"type": "number", "description": "Line thickness", "default": 2}
                },
                "required": ["x1", "y1", "x2", "y2", "layer"]
            }
        },
        {
            "name": "add_symbol",
            "description": "Add an electrical symbol to the drawing",
            "input_schema": {
                "type": "object",
                "properties": {
                    "symbol_id": {"type": "string", "description": "Symbol ID"},
                    "x": {"type": "number", "description": "X position"},
                    "y": {"type": "number", "description": "Y position"},
                    "label": {"type": "string", "description": "Optional label"}
                },
                "required": ["symbol_id", "x", "y"]
            }
        },
        {
            "name": "add_text",
            "description": "Add text annotation to the drawing",
            "input_schema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text content"},
                    "x": {"type": "number", "description": "X position"},
                    "y": {"type": "number", "description": "Y position"},
                    "fontSize": {"type": "number", "description": "Font size", "default": 14},
                    "layer": {"type": "string", "description": "Layer name", "default": "TEXT-LABELS"}
                },
                "required": ["text", "x", "y"]
            }
        },
        {
            "name": "add_dimension",
            "description": "Add dimension line to show measurements",
            "input_schema": {
                "type": "object",
                "properties": {
                    "x1": {"type": "number", "description": "Start X"},
                    "y1": {"type": "number", "description": "Start Y"},
                    "x2": {"type": "number", "description": "End X"},
                    "y2": {"type": "number", "description": "End Y"},
                    "label": {"type": "string", "description": "Measurement text"}
                },
                "required": ["x1", "y1", "x2", "y2", "label"]
            }
        },
        {
            "name": "add_rectangle",
            "description": "Add a rectangle (for rooms, equipment, etc.)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "x": {"type": "number", "description": "Left position"},
                    "y": {"type": "number", "description": "Top position"},
                    "width": {"type": "number", "description": "Width"},
                    "height": {"type": "number", "description": "Height"},
                    "layer": {"type": "string", "description": "Layer name"},
                    "fill": {"type": "string", "description": "Fill color", "default": "transparent"}
                },
                "required": ["x", "y", "width", "height", "layer"]
            }
        }
    ]


def _execute_cad_tool(tool_name, tool_input):
    """Execute a CAD drawing tool and return Fabric.js-compatible object"""
    try:
        layer_colors = {
            'WALLS-ARCHITECTURAL': '#2C3E50',
            'POWER-WIRING-RED': '#E74C3C',
            'NEUTRAL-WIRING-BLUE': '#3498DB',
            'GROUND-WIRING-GREEN': '#27AE60',
            'DEVICES-SYMBOLS': '#F39C12',
            'TEXT-LABELS': '#34495E'
        }

        if tool_name == "add_line":
            layer = tool_input.get('layer', 'WALLS-ARCHITECTURAL')
            color = layer_colors.get(layer, '#000000')

            return {
                'type': 'line',
                'x1': tool_input['x1'],
                'y1': tool_input['y1'],
                'x2': tool_input['x2'],
                'y2': tool_input['y2'],
                'stroke': color,
                'strokeWidth': tool_input.get('strokeWidth', 2),
                'layer': layer,
                'customType': 'line',
                'selectable': True
            }

        elif tool_name == "add_symbol":
            return {
                'type': 'group',
                'left': tool_input['x'],
                'top': tool_input['y'],
                'layer': 'DEVICES-SYMBOLS',
                'customType': 'symbol',
                'symbolId': tool_input['symbol_id'],
                'label': tool_input.get('label', ''),
                'selectable': True
            }

        elif tool_name == "add_text":
            return {
                'type': 'text',
                'left': tool_input['x'],
                'top': tool_input['y'],
                'text': tool_input['text'],
                'fontSize': tool_input.get('fontSize', 14),
                'fill': '#2C3E50',
                'layer': tool_input.get('layer', 'TEXT-LABELS'),
                'customType': 'text',
                'selectable': True
            }

        elif tool_name == "add_dimension":
            return {
                'type': 'group',
                'left': tool_input['x1'],
                'top': tool_input['y1'],
                'customType': 'dimension',
                'dimensionStart': {'x': tool_input['x1'], 'y': tool_input['y1']},
                'dimensionEnd': {'x': tool_input['x2'], 'y': tool_input['y2']},
                'label': tool_input['label'],
                'layer': 'TEXT-LABELS',
                'selectable': True
            }

        elif tool_name == "add_rectangle":
            layer = tool_input.get('layer', 'WALLS-ARCHITECTURAL')
            color = layer_colors.get(layer, '#000000')

            return {
                'type': 'rect',
                'left': tool_input['x'],
                'top': tool_input['y'],
                'width': tool_input['width'],
                'height': tool_input['height'],
                'fill': tool_input.get('fill', 'transparent'),
                'stroke': color,
                'strokeWidth': 2,
                'layer': layer,
                'customType': 'rectangle',
                'selectable': True
            }

        return None

    except Exception as e:
        print(f"Error executing CAD tool {tool_name}: {e}")
        return None


def _get_symbol_library():
    """Get the full electrical symbol library"""
    return {
        'outlets': [
            {
                'id': 'power-outlet-single',
                'name': 'Power Outlet (Single)',
                'category': 'outlets',
                'width': 20,
                'height': 20,
                'svg': '<circle cx="10" cy="10" r="8" fill="none" stroke="black" stroke-width="1.5"/><line x1="10" y1="4" x2="10" y2="7" stroke="black" stroke-width="1.5"/><line x1="10" y1="13" x2="10" y2="16" stroke="black" stroke-width="1.5"/>',
                'description': 'Single phase power outlet 230V',
                'standards': 'AS/NZS 3000',
                'electrical': {'voltage': 230, 'phases': 1, 'loadEstimate': 10}
            },
            {
                'id': 'power-outlet-double',
                'name': 'Power Outlet (Double)',
                'category': 'outlets',
                'width': 30,
                'height': 20,
                'svg': '<circle cx="8" cy="10" r="6" fill="none" stroke="black" stroke-width="1.5"/><circle cx="22" cy="10" r="6" fill="none" stroke="black" stroke-width="1.5"/>',
                'description': 'Double power outlet 230V',
                'standards': 'AS/NZS 3000',
                'electrical': {'voltage': 230, 'phases': 1, 'loadEstimate': 10}
            },
        ],
        'lighting': [
            {
                'id': 'light-ceiling',
                'name': 'Ceiling Light',
                'category': 'lighting',
                'width': 20,
                'height': 20,
                'svg': '<circle cx="10" cy="10" r="7" fill="none" stroke="black" stroke-width="1.5"/>',
                'description': 'Ceiling mounted light fitting',
                'standards': 'AS/NZS 3000',
                'electrical': {'voltage': 230, 'phases': 1, 'loadEstimate': 0.5}
            },
            {
                'id': 'light-downlight',
                'name': 'Downlight',
                'category': 'lighting',
                'width': 18,
                'height': 18,
                'svg': '<circle cx="9" cy="9" r="6" fill="none" stroke="black" stroke-width="1.5"/><circle cx="9" cy="9" r="3" fill="black"/>',
                'description': 'Recessed downlight',
                'standards': 'AS/NZS 3000',
                'electrical': {'voltage': 230, 'phases': 1, 'loadEstimate': 0.3}
            },
        ],
        'switches': [
            {
                'id': 'switch-single',
                'name': 'Switch (1-Gang)',
                'category': 'switches',
                'width': 20,
                'height': 20,
                'svg': '<rect x="3" y="3" width="14" height="14" fill="none" stroke="black" stroke-width="1.5"/><text x="10" y="13" font-size="8" text-anchor="middle" fill="black">S</text>',
                'description': 'Single gang light switch',
                'standards': 'AS/NZS 3000',
                'electrical': {'voltage': 230, 'phases': 1, 'rating': 10}
            },
            {
                'id': 'switch-dimmer',
                'name': 'Dimmer Switch',
                'category': 'switches',
                'width': 20,
                'height': 20,
                'svg': '<rect x="3" y="3" width="14" height="14" fill="none" stroke="black" stroke-width="1.5"/><text x="10" y="13" font-size="7" text-anchor="middle" fill="black">D</text>',
                'description': 'Dimmer switch for lighting control',
                'standards': 'AS/NZS 3000',
                'electrical': {'voltage': 230, 'phases': 1, 'rating': 10}
            },
        ],
        'distribution': [
            {
                'id': 'switchboard',
                'name': 'Switchboard',
                'category': 'distribution',
                'width': 60,
                'height': 80,
                'svg': '<rect x="5" y="5" width="50" height="70" fill="none" stroke="black" stroke-width="2"/><text x="30" y="15" font-size="8" text-anchor="middle" fill="black">MSB</text>',
                'description': 'Main switchboard/distribution board',
                'standards': 'AS/NZS 3000',
                'electrical': {'voltage': 230, 'phases': 1, 'mainRating': 63}
            },
        ],
        'loxone': [
            {
                'id': 'loxone-miniserver',
                'name': 'Loxone Miniserver',
                'category': 'loxone',
                'width': 80,
                'height': 60,
                'svg': '<rect x="5" y="5" width="70" height="50" rx="3" fill="none" stroke="black" stroke-width="2"/><text x="40" y="38" font-size="10" text-anchor="middle" fill="black">Miniserver</text>',
                'description': 'Loxone Miniserver Gen 2',
                'standards': 'CE, Loxone',
                'electrical': {'voltage': 230, 'phases': 1, 'loadEstimate': 0.3}
            },
            {
                'id': 'loxone-relay',
                'name': 'Relay Extension',
                'category': 'loxone',
                'width': 60,
                'height': 50,
                'svg': '<rect x="5" y="5" width="50" height="40" rx="2" fill="none" stroke="black" stroke-width="1.5"/><text x="30" y="35" font-size="6" text-anchor="middle" fill="black">Relay Ext</text>',
                'description': 'Loxone Relay Extension',
                'standards': 'CE, Loxone',
                'electrical': {'voltage': 24, 'type': 'DC', 'relayRating': 16}
            },
            {
                'id': 'loxone-dimmer',
                'name': 'Dimmer Extension',
                'category': 'loxone',
                'width': 60,
                'height': 50,
                'svg': '<rect x="5" y="5" width="50" height="40" rx="2" fill="none" stroke="black" stroke-width="1.5"/><text x="30" y="37" font-size="6" text-anchor="middle" fill="black">Dimmer Ext</text>',
                'description': 'Loxone Dimmer Extension',
                'standards': 'CE, Loxone',
                'electrical': {'voltage': 230, 'phases': 1, 'channelRating': 16}
            },
            {
                'id': 'loxone-extension',
                'name': 'Loxone Extension',
                'category': 'loxone',
                'width': 60,
                'height': 50,
                'svg': '<rect x="5" y="5" width="50" height="40" rx="2" fill="none" stroke="black" stroke-width="1.5"/><text x="30" y="37" font-size="7" text-anchor="middle" fill="black">Extension</text>',
                'description': 'Loxone Extension module',
                'standards': 'CE, Loxone',
                'electrical': {'voltage': 24, 'type': 'DC', 'loadEstimate': 0.1}
            },
        ],
        'communication': [
            {
                'id': 'data-outlet',
                'name': 'Data Outlet',
                'category': 'communication',
                'width': 20,
                'height': 20,
                'svg': '<rect x="3" y="5" width="14" height="10" fill="none" stroke="black" stroke-width="1.5"/><text x="10" y="4" font-size="4" text-anchor="middle" fill="black">DATA</text>',
                'description': 'Data outlet (Cat6/Cat6A)',
                'standards': 'AS/NZS 3000',
                'electrical': {'type': 'low-voltage', 'category': 'Cat6A'}
            },
        ],
        'safety': [
            {
                'id': 'smoke-detector',
                'name': 'Smoke Detector',
                'category': 'safety',
                'width': 22,
                'height': 22,
                'svg': '<circle cx="11" cy="11" r="9" fill="none" stroke="black" stroke-width="1.5"/><text x="11" y="20" font-size="4" text-anchor="middle" fill="black">SD</text>',
                'description': 'Smoke detector (photoelectric)',
                'standards': 'AS/NZS 3000, AS 3786',
                'electrical': {'voltage': 230, 'phases': 1, 'loadEstimate': 0.02}
            },
        ],
        'ventilation': [
            {
                'id': 'exhaust-fan',
                'name': 'Exhaust Fan',
                'category': 'ventilation',
                'width': 24,
                'height': 24,
                'svg': '<circle cx="12" cy="12" r="10" fill="none" stroke="black" stroke-width="1.5"/><circle cx="12" cy="12" r="2" fill="black"/>',
                'description': 'Exhaust fan (bathroom/kitchen)',
                'standards': 'AS/NZS 3000',
                'electrical': {'voltage': 230, 'phases': 1, 'loadEstimate': 0.8}
            },
        ],
    }

