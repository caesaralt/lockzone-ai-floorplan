"""
Miscellaneous Routes Blueprint

Handles:
- /api/data: Automation data API
- /uploads/<filename>: Serve uploaded files
- /outputs/<filename>: Serve output files
- /api/download/<filename>: General download endpoint
"""

import os
from flask import Blueprint, request, jsonify, send_file, send_from_directory, current_app
import logging

logger = logging.getLogger(__name__)

# Create blueprint
misc_bp = Blueprint('misc_bp', __name__)


def get_app_functions():
    """Get functions from main app"""
    return current_app.config.get('APP_FUNCTIONS', {})


# ============================================================================
# AUTOMATION DATA API
# ============================================================================

@misc_bp.route('/api/data', methods=['GET'])
def get_automation_data():
    """Get automation catalog, pricing, and company info"""
    try:
        funcs = get_app_functions()
        load_data = funcs.get('load_data')
        if not load_data:
            return jsonify({'error': 'Data loader not available'}), 500
        data = load_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@misc_bp.route('/api/data', methods=['POST'])
def update_automation_data():
    """Update automation catalog and pricing"""
    try:
        funcs = get_app_functions()
        load_data = funcs.get('load_data')
        save_data = funcs.get('save_data')
        
        if not load_data or not save_data:
            return jsonify({'error': 'Data functions not available'}), 500
        
        new_data = request.get_json()
        if not new_data:
            return jsonify({'error': 'No data provided'}), 400

        # Load existing data and merge
        current_data = load_data()

        # Deep merge - update only provided fields
        if 'automation_types' in new_data:
            current_data['automation_types'].update(new_data['automation_types'])
        if 'labor_rate' in new_data:
            current_data['labor_rate'] = new_data['labor_rate']
        if 'markup_percentage' in new_data:
            current_data['markup_percentage'] = new_data['markup_percentage']
        if 'company_info' in new_data:
            current_data['company_info'].update(new_data['company_info'])

        save_data(current_data)
        return jsonify({'success': True, 'data': current_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# FILE SERVING
# ============================================================================

@misc_bp.route('/uploads/<path:filename>')
def serve_uploads(filename):
    """Serve uploaded files"""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


@misc_bp.route('/outputs/<path:filename>')
def serve_output_file(filename):
    """Serve files from the outputs folder"""
    return send_from_directory(current_app.config['OUTPUT_FOLDER'], filename)


@misc_bp.route('/api/download/<filename>')
def download_file(filename):
    """General download endpoint for generated files"""
    try:
        # Check in outputs folder first
        file_path = os.path.join(current_app.config['OUTPUT_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)

        # Check in exports folder (CAD exports)
        file_path = os.path.join('exports', filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)

        # Check in AI mapping folder
        file_path = os.path.join(current_app.config['AI_MAPPING_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)

        # Check in uploads folder
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)

        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# INVENTORY API
# ============================================================================

@misc_bp.route('/api/inventory', methods=['GET'])
def get_inventory():
    """Get inventory"""
    try:
        import json
        inventory_file = os.path.join(current_app.config.get('BASE_DIR', '.'), 'inventory.json')
        inventory = []
        if os.path.exists(inventory_file):
            with open(inventory_file, 'r') as f:
                inventory = json.load(f)
        
        automation_type = request.args.get('automation_type')
        tier = request.args.get('tier')
        filtered = inventory
        if automation_type:
            filtered = [i for i in filtered if i.get('automation_type') == automation_type]
        if tier:
            filtered = [i for i in filtered if i.get('tier') == tier]
        return jsonify({'success': True, 'inventory': filtered, 'total': len(inventory)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# AI CHAT
# ============================================================================

@misc_bp.route('/api/ai-chat', methods=['POST'])
def ai_chat():
    """
    AI Chat endpoint with vision capabilities and web search
    """
    try:
        import os
        import requests as req
        
        data = request.json
        user_message = data.get('message', '')
        agent_mode = data.get('agent_mode', False)
        conversation_history = data.get('conversation_history', [])
        project_id = data.get('project_id')
        current_page = data.get('current_page', 'unknown')
        images = data.get('images', [])

        if not user_message:
            return jsonify({'success': False, 'error': 'No message provided'}), 400

        # Use OpenAI for board builder page
        if current_page == '/board-builder':
            openai_api_key = os.environ.get('OPENAI_API_KEY')
            if not openai_api_key:
                return jsonify({
                    'success': False,
                    'error': 'OpenAI API key not configured',
                    'response': 'AI chat is not configured properly.'
                }), 503

            gpt_messages = [
                {
                    'role': 'system',
                    'content': 'You are an expert Loxone system designer and assistant. You help users design, understand, and troubleshoot Loxone automation systems.'
                }
            ]

            for msg in conversation_history:
                gpt_messages.append({
                    'role': msg.get('role', 'user'),
                    'content': msg.get('content', '')
                })

            gpt_messages.append({
                'role': 'user',
                'content': user_message
            })

            response = req.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {openai_api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'gpt-4',
                    'messages': gpt_messages,
                    'max_tokens': 4000,
                    'temperature': 0.7
                }
            )

            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content']
                return jsonify({
                    'success': True,
                    'response': ai_response,
                    'model': 'gpt-4'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'OpenAI API error: {response.status_code}'
                }), 500

        # Default: Use Anthropic Claude
        try:
            import anthropic
            client = anthropic.Anthropic()
        except:
            return jsonify({
                'success': False,
                'error': 'AI service not configured',
                'response': 'AI chat requires an Anthropic API key.'
            }), 503

        # Build messages
        messages = []
        for msg in conversation_history:
            messages.append({
                'role': msg.get('role', 'user'),
                'content': msg.get('content', '')
            })

        # Handle images if provided
        if images:
            content = []
            for img in images:
                if img.startswith('data:'):
                    media_type = img.split(';')[0].split(':')[1]
                    img_data = img.split(',')[1]
                    content.append({
                        'type': 'image',
                        'source': {
                            'type': 'base64',
                            'media_type': media_type,
                            'data': img_data
                        }
                    })
            content.append({'type': 'text', 'text': user_message})
            messages.append({'role': 'user', 'content': content})
        else:
            messages.append({'role': 'user', 'content': user_message})

        response = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=4000,
            system='You are an expert assistant for an electrical automation and CRM system. Help users with quotes, projects, floor plans, and technical questions.',
            messages=messages
        )

        ai_response = response.content[0].text

        return jsonify({
            'success': True,
            'response': ai_response,
            'model': 'claude-sonnet-4-20250514'
        })

    except Exception as e:
        logger.error(f"AI chat error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

