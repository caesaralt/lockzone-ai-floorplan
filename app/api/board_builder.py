"""
Board Builder Routes Blueprint

Handles Loxone board design tool:
- /api/board-builder/generate: AI-powered board generation
- /api/board-builder/available-sessions: Get available sessions
- /api/board-builder/import/mapping/<session_id>: Import from mapping
- /api/board-builder/import/canvas/<session_id>: Import from canvas
- /api/board-builder/export/crm: Export board to CRM
"""

import os
import re
import json
import traceback
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
import requests as http_requests
import logging

logger = logging.getLogger(__name__)

# Create blueprint
board_builder_bp = Blueprint('board_builder_bp', __name__)


def get_app_functions():
    """Get functions from main app"""
    return current_app.config.get('APP_FUNCTIONS', {})


def get_base_dir():
    """Get base directory"""
    return current_app.config.get('BASE_DIR', os.getcwd())


# ============================================================================
# BOARD BUILDER ROUTES
# ============================================================================

@board_builder_bp.route('/api/board-builder/generate', methods=['POST'])
def generate_board_with_ai():
    """AI-powered Loxone board generation"""
    try:
        data = request.get_json()
        requirements = data.get('requirements', '')
        automation_types = data.get('automationTypes', [])
        existing_components = data.get('existingComponents', [])

        prompt = f"""You are an expert Loxone system designer. Generate a complete Loxone board configuration based on these requirements:

REQUIREMENTS:
{requirements}

AUTOMATION TYPES:
{', '.join(automation_types)}

Generate a professional Loxone board layout with:
1. Appropriate Miniserver (Gen 2 or Go based on scale)
2. Required extensions (Relay, Dimmer, Air Base, etc.)
3. Input/output modules as needed
4. Power supplies and communication infrastructure
5. Proper connections between components

Consider:
- Typical component counts for each automation type
- Standard Loxone architecture best practices
- Cost-effective component selection
- Proper power distribution
- Scalability

Return a JSON configuration with components array containing:
- type (component type like 'miniserver', 'relay-extension', etc.)
- x, y (position coordinates, distributed evenly)
- properties (name, notes)

Example component types: miniserver, miniserver-go, extension, relay-extension, dimmer-extension, digital-input, analog-input, relay-output, power-supply, air-base, dmx-extension, modbus

Format response as JSON with structure:
{{
    "components": [
        {{"type": "miniserver", "x": 100, "y": 100, "properties": {{"name": "Main Controller", "notes": "Central hub"}}}},
        ...
    ],
    "connections": [],
    "reasoning": "Explanation of design choices"
}}"""

        openai_api_key = os.environ.get('OPENAI_API_KEY')

        if not openai_api_key:
            return _generate_basic_board(automation_types)

        response = http_requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {openai_api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'gpt-4',
                'messages': [
                    {'role': 'system', 'content': 'You are a Loxone system design expert. Always respond with valid JSON.'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.7,
                'max_tokens': 2000
            },
            timeout=30
        )

        if response.status_code == 200:
            ai_response = response.json()
            content = ai_response['choices'][0]['message']['content']

            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
            else:
                json_match = re.search(r'```\s*(.*?)\s*```', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)

            board_data = json.loads(content)

            return jsonify({
                'success': True,
                'boardData': board_data,
                'reasoning': board_data.get('reasoning', '')
            })
        else:
            return _generate_basic_board(automation_types)

    except Exception as e:
        print(f"Error generating board: {e}")
        traceback.print_exc()
        return _generate_basic_board(automation_types)


def _generate_basic_board(automation_types):
    """Generate a basic Loxone board based on automation types (fallback)"""
    components = []
    y_offset = 100
    x_base = 200

    components.append({
        'type': 'miniserver',
        'x': x_base,
        'y': y_offset,
        'properties': {
            'name': 'Miniserver Gen 2',
            'notes': 'Main controller'
        }
    })

    y_offset += 150

    if 'lighting' in automation_types:
        components.append({
            'type': 'dimmer-extension',
            'x': x_base + 300,
            'y': y_offset,
            'properties': {'name': 'Lighting Dimmer', 'notes': 'Main lighting control'}
        })
        components.append({
            'type': 'relay-extension',
            'x': x_base + 500,
            'y': y_offset,
            'properties': {'name': 'Lighting Relay', 'notes': 'On/off lighting'}
        })
        y_offset += 120

    if 'hvac' in automation_types:
        components.append({
            'type': 'air-base',
            'x': x_base + 300,
            'y': y_offset,
            'properties': {'name': 'HVAC Controller', 'notes': 'Climate control'}
        })
        y_offset += 120

    if 'blinds' in automation_types:
        components.append({
            'type': 'relay-extension',
            'x': x_base + 300,
            'y': y_offset,
            'properties': {'name': 'Blinds Control', 'notes': 'Motorized blinds'}
        })
        y_offset += 120

    if 'security' in automation_types:
        components.append({
            'type': 'digital-input',
            'x': x_base + 300,
            'y': y_offset,
            'properties': {'name': 'Security Inputs', 'notes': 'Door/window sensors'}
        })
        y_offset += 120

    if 'audio' in automation_types:
        components.append({
            'type': 'extension',
            'x': x_base + 300,
            'y': y_offset,
            'properties': {'name': 'Audio Zone Extension', 'notes': 'Multi-room audio'}
        })
        y_offset += 120

    if 'energy' in automation_types:
        components.append({
            'type': 'modbus',
            'x': x_base + 300,
            'y': y_offset,
            'properties': {'name': 'Energy Meter', 'notes': 'Power monitoring'}
        })
        y_offset += 120

    components.append({
        'type': 'power-supply',
        'x': x_base,
        'y': y_offset,
        'properties': {'name': '24V Power Supply', 'notes': 'Main power'}
    })

    return jsonify({
        'success': True,
        'boardData': {
            'components': components,
            'connections': [],
            'reasoning': 'Generated basic board layout based on selected automation types'
        }
    })


@board_builder_bp.route('/api/board-builder/available-sessions', methods=['GET'])
def get_available_sessions():
    """Get list of available sessions from mapping and canvas tools"""
    try:
        sessions = []
        base_dir = get_base_dir()
        session_folder = current_app.config.get('SESSION_DATA_FOLDER', os.path.join(base_dir, 'session_data'))

        if os.path.exists(session_folder):
            for filename in os.listdir(session_folder):
                if filename.endswith('.json'):
                    session_id = filename.replace('.json', '')
                    session_file = os.path.join(session_folder, filename)

                    try:
                        with open(session_file, 'r') as f:
                            session_data = json.load(f)

                            session_type = 'unknown'
                            if 'automation_data' in session_data or 'symbols' in session_data:
                                session_type = 'mapping'
                            elif 'canvas_data' in session_data or 'elements' in session_data:
                                session_type = 'canvas'

                            sessions.append({
                                'id': session_id,
                                'type': session_type,
                                'project_name': session_data.get('project_name', 'Unnamed Project'),
                                'created': session_data.get('timestamp', session_data.get('created', 'Unknown')),
                                'component_count': len(session_data.get('automation_data', {}).get('symbols', [])) if session_type == 'mapping' else len(session_data.get('canvas_data', {}).get('elements', []))
                            })
                    except Exception as e:
                        print(f"Error reading session {filename}: {e}")
                        continue

        return jsonify({
            'success': True,
            'sessions': sessions,
            'mapping_sessions': [s for s in sessions if s['type'] == 'mapping'],
            'canvas_sessions': [s for s in sessions if s['type'] == 'canvas']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@board_builder_bp.route('/api/board-builder/import/mapping/<session_id>', methods=['GET'])
def import_from_mapping(session_id):
    """Import electrical mapping data into board builder"""
    try:
        funcs = get_app_functions()
        load_session_data = funcs.get('load_session_data')
        
        if not load_session_data:
            return jsonify({'success': False, 'error': 'Session loader not available'})
        
        session_data = load_session_data(session_id)

        if not session_data:
            return jsonify({'success': False, 'error': 'Session not found'})

        components = []
        automation_data = session_data.get('automation_data', {})

        x_offset = 150
        y_offset = 100

        light_count = sum(1 for item in automation_data.get('symbols', []) if 'light' in item.get('type', '').lower())
        switch_count = sum(1 for item in automation_data.get('symbols', []) if 'switch' in item.get('type', '').lower())
        outlet_count = sum(1 for item in automation_data.get('symbols', []) if 'outlet' in item.get('type', '').lower())

        components.append({
            'type': 'miniserver',
            'x': x_offset,
            'y': y_offset,
            'properties': {
                'name': 'Miniserver',
                'notes': f'Project: {session_data.get("project_name", "Imported")}'
            }
        })

        y_offset += 150

        if light_count > 8:
            components.append({
                'type': 'dimmer-extension',
                'x': x_offset + 250,
                'y': y_offset,
                'properties': {
                    'name': f'Dimmer Extension',
                    'notes': f'For {light_count} lights'
                }
            })
            y_offset += 120

        if switch_count > 0 or outlet_count > 0:
            components.append({
                'type': 'relay-extension',
                'x': x_offset + 250,
                'y': y_offset,
                'properties': {
                    'name': 'Relay Extension',
                    'notes': f'{switch_count} switches, {outlet_count} outlets'
                }
            })
            y_offset += 120

        if switch_count > 0:
            components.append({
                'type': 'digital-input',
                'x': x_offset + 250,
                'y': y_offset,
                'properties': {
                    'name': 'Digital Inputs',
                    'notes': f'{switch_count} switch inputs'
                }
            })

        return jsonify({
            'success': True,
            'boardData': {
                'components': components,
                'connections': [],
                'sourceSession': session_id,
                'sourceType': 'mapping'
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@board_builder_bp.route('/api/board-builder/import/canvas/<session_id>', methods=['GET'])
def import_from_canvas(session_id):
    """Import canvas automation data into board builder"""
    try:
        funcs = get_app_functions()
        load_session_data = funcs.get('load_session_data')
        
        if not load_session_data:
            return jsonify({'success': False, 'error': 'Session loader not available'})
        
        session_data = load_session_data(session_id)

        if not session_data:
            return jsonify({'success': False, 'error': 'Session not found'})

        components = []
        automation_data = session_data.get('automation_data', {})
        automation_types = session_data.get('automation_types', [])

        x_offset = 150
        y_offset = 100

        components.append({
            'type': 'miniserver',
            'x': x_offset,
            'y': y_offset,
            'properties': {
                'name': 'Miniserver',
                'notes': f'Project: {session_data.get("project_name", "Canvas Import")}'
            }
        })

        y_offset += 150

        for auto_type in automation_types:
            if auto_type == 'lighting':
                components.append({
                    'type': 'dimmer-extension',
                    'x': x_offset + 250,
                    'y': y_offset,
                    'properties': {'name': 'Lighting Control', 'notes': 'From Canvas'}
                })
                y_offset += 120

            elif auto_type == 'hvac':
                components.append({
                    'type': 'air-base',
                    'x': x_offset + 250,
                    'y': y_offset,
                    'properties': {'name': 'HVAC Extension', 'notes': 'Climate control'}
                })
                y_offset += 120

            elif auto_type == 'blinds':
                components.append({
                    'type': 'relay-extension',
                    'x': x_offset + 250,
                    'y': y_offset,
                    'properties': {'name': 'Blinds Extension', 'notes': 'Motorized blinds'}
                })
                y_offset += 120

        return jsonify({
            'success': True,
            'boardData': {
                'components': components,
                'connections': [],
                'sourceSession': session_id,
                'sourceType': 'canvas'
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@board_builder_bp.route('/api/board-builder/export/crm', methods=['POST'])
def export_board_to_crm():
    """Export Loxone board to CRM (create job and add components to stock)"""
    try:
        base_dir = get_base_dir()
        data = request.get_json()
        job_name = data.get('jobName', 'Loxone Board')
        components = data.get('components', [])
        total_cost = data.get('totalCost', 0)
        board_data = data.get('boardData', {})

        crm_file = os.path.join(base_dir, 'crm_data.json')
        if os.path.exists(crm_file):
            with open(crm_file, 'r') as f:
                crm_data = json.load(f)
        else:
            crm_data = {'jobs': [], 'stock': [], 'customers': []}

        job_id = f"JOB-{len(crm_data.get('jobs', [])) + 1:04d}"
        new_job = {
            'id': job_id,
            'name': job_name,
            'customer': 'Board Builder Export',
            'status': 'planned',
            'total': total_cost,
            'components': components,
            'boardData': board_data,
            'created': datetime.now().strftime('%Y-%m-%d'),
            'type': 'loxone_installation'
        }

        if 'jobs' not in crm_data:
            crm_data['jobs'] = []
        crm_data['jobs'].append(new_job)

        if 'stock' not in crm_data:
            crm_data['stock'] = []

        for comp in components:
            existing = next((s for s in crm_data['stock'] if s.get('name') == comp['name']), None)

            if existing:
                existing['quantity'] = existing.get('quantity', 0) + comp.get('quantity', 1)
            else:
                crm_data['stock'].append({
                    'sku': f"LXN-{len(crm_data['stock']) + 1:04d}",
                    'name': comp['name'],
                    'category': 'Loxone Components',
                    'quantity': comp.get('quantity', 1),
                    'price': comp.get('cost', 0),
                    'supplier': 'Loxone',
                    'type': comp.get('type', 'component')
                })

        with open(crm_file, 'w') as f:
            json.dump(crm_data, f, indent=2)

        return jsonify({
            'success': True,
            'jobId': job_id,
            'componentsAdded': len(components),
            'message': f'Job {job_id} created with {len(components)} components'
        })

    except Exception as e:
        print(f"CRM export error: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

