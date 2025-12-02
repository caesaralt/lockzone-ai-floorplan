"""
AI Mapping Routes Blueprint

Handles AI-powered floor plan analysis and electrical mapping:
- /api/ai-mapping/analyze: Analyze floor plan with AI
- /api/ai-mapping/save-correction: Save user corrections as learning data
- /api/ai-mapping/learning-stats: Get learning statistics
- /api/ai-mapping/download/<filename>: Download marked-up floor plan
- /api/ai-mapping/history: Get analysis history
- /api/ai/mapping: AI-powered electrical component placement
- /api/mapping/export: Export electrical mapping
"""

import os
import re
import json
import uuid
import base64
import traceback
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
import requests
import logging

logger = logging.getLogger(__name__)

# Create blueprint
ai_mapping_bp = Blueprint('ai_mapping_bp', __name__)


def get_app_functions():
    """Get functions from main app"""
    return current_app.config.get('APP_FUNCTIONS', {})


# ============================================================================
# AI MAPPING ROUTES
# ============================================================================

@ai_mapping_bp.route('/api/ai-mapping/analyze', methods=['POST'])
def ai_mapping_analyze():
    """Analyze floor plan with AI learning"""
    try:
        funcs = get_app_functions()
        ai_map_floorplan = funcs.get('ai_map_floorplan')
        generate_marked_up_image = funcs.get('generate_marked_up_image')
        
        if 'floorplan' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['floorplan']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Empty filename'}), 400
        
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        file_path = os.path.join(current_app.config['AI_MAPPING_FOLDER'], unique_filename)
        file.save(file_path)
        
        is_pdf = filename.lower().endswith('.pdf')
        
        # Analyze with AI (includes learning context)
        if ai_map_floorplan:
            mapping_result = ai_map_floorplan(file_path, is_pdf)
        else:
            return jsonify({'success': False, 'error': 'AI mapping function not available'}), 500
        
        if 'error' in mapping_result:
            return jsonify({'success': False, 'error': mapping_result['error']})
        
        # Generate marked-up image
        output_filename = f"marked_{timestamp}_{os.path.splitext(filename)[0]}.png"
        output_path = os.path.join(current_app.config['AI_MAPPING_FOLDER'], output_filename)
        
        if generate_marked_up_image:
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


@ai_mapping_bp.route('/api/ai-mapping/save-correction', methods=['POST'])
def save_correction():
    """Save user corrections as learning data"""
    try:
        funcs = get_app_functions()
        load_mapping_learning_index = funcs.get('load_mapping_learning_index')
        save_mapping_learning_index = funcs.get('save_mapping_learning_index')
        
        if not all([load_mapping_learning_index, save_mapping_learning_index]):
            return jsonify({'success': False, 'error': 'Learning functions not available'}), 500
        
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


@ai_mapping_bp.route('/api/ai-mapping/learning-stats', methods=['GET'])
def get_learning_stats():
    """Get learning statistics"""
    try:
        funcs = get_app_functions()
        load_mapping_learning_index = funcs.get('load_mapping_learning_index')
        
        if not load_mapping_learning_index:
            return jsonify({'success': False, 'error': 'Learning function not available'}), 500
        
        index = load_mapping_learning_index()
        return jsonify({
            'success': True,
            'stats': index.get('stats', {}),
            'total_examples': len(index.get('examples', [])),
            'last_updated': index.get('last_updated')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@ai_mapping_bp.route('/api/ai-mapping/download/<filename>')
def ai_mapping_download(filename):
    """Download marked-up floor plan"""
    try:
        file_path = os.path.join(current_app.config['AI_MAPPING_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_mapping_bp.route('/api/ai-mapping/history', methods=['GET'])
def ai_mapping_history():
    """Get analysis history"""
    try:
        files = os.listdir(current_app.config['AI_MAPPING_FOLDER'])
        marked_files = [f for f in files if f.startswith('marked_')]
        
        history = []
        for f in sorted(marked_files, reverse=True)[:20]:
            history.append({
                'filename': f,
                'timestamp': f.split('_')[1] if '_' in f else 'unknown',
                'size': os.path.getsize(os.path.join(current_app.config['AI_MAPPING_FOLDER'], f))
            })
        
        return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@ai_mapping_bp.route('/api/ai/mapping', methods=['POST'])
def ai_mapping():
    """AI-powered electrical component placement on floor plans"""
    try:
        from PIL import Image as PILImage
        import io
        
        data = request.json
        floor_plan_image_data = data.get('floor_plan_image')
        canvas_width = data.get('canvas_width', 1400)
        canvas_height = data.get('canvas_height', 900)
        purpose = data.get('purpose', 'electrical')

        if not floor_plan_image_data:
            return jsonify({'success': False, 'error': 'No floor plan image provided'}), 200

        # Remove data URL prefix if present
        if ',' in floor_plan_image_data:
            floor_plan_image_data = floor_plan_image_data.split(',')[1]

        image_bytes = base64.b64decode(floor_plan_image_data)
        image = PILImage.open(io.BytesIO(image_bytes))

        # Save temporarily
        temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp_mapping.jpg')
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
            prompt = _get_automation_prompt()
        else:
            prompt = _get_electrical_prompt()

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
            return jsonify({'success': False, 'error': error_msg}), 200

        ai_response = response.json()
        ai_text = ai_response['content'][0]['text']

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
            return jsonify({'success': False, 'error': 'Could not parse AI response'}), 200

    except Exception as e:
        logger.error(f"AI mapping error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 200


@ai_mapping_bp.route('/api/mapping/export', methods=['POST'])
def mapping_export():
    """Export electrical mapping with wiring and circuits"""
    try:
        data = request.json
        components = data.get('components', [])
        wires = data.get('wires', [])
        circuits = data.get('circuits', [])
        project_name = data.get('project_name', 'Electrical Mapping')
        
        # Create export data structure
        export_data = {
            'project_name': project_name,
            'timestamp': datetime.now().isoformat(),
            'components': components,
            'wires': wires,
            'circuits': circuits,
            'summary': {
                'total_components': len(components),
                'total_wires': len(wires),
                'total_circuits': len(circuits)
            }
        }
        
        # Save to file
        filename = f"mapping_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(current_app.config['OUTPUT_FOLDER'], filename)
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'download_url': f'/api/download/{filename}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def _get_automation_prompt():
    """Get prompt for home automation analysis"""
    return """You are a home automation expert analyzing a floor plan for smart home automation placement.

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
    }
  ]
}

Place components logically based on room function and smart home best practices."""


def _get_electrical_prompt():
    """Get prompt for electrical installation analysis"""
    return """You are an expert electrician creating a comprehensive electrical installation plan for a building.

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
4. Label/description
5. Room/location name
6. Circuit suggestion

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
    }
  ]
}

Follow NEC requirements for proper electrical layout."""

