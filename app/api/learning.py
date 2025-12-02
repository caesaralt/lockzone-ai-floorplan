"""
Learning Routes Blueprint

Handles AI learning data management:
- /api/learning/examples: Get learning examples
- /api/learning/upload: Upload learning example
- /api/learning/history: Get learning history
- /api/upload-learning-data: Enhanced multi-file upload
- /api/process-instructions: Process natural language instructions
"""

import os
import json
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import logging

logger = logging.getLogger(__name__)

# Create blueprint
learning_bp = Blueprint('learning_bp', __name__)


def get_app_functions():
    """Get functions from main app"""
    return current_app.config.get('APP_FUNCTIONS', {})


# ============================================================================
# LEARNING API ROUTES
# ============================================================================

@learning_bp.route('/api/learning/examples', methods=['GET'])
def get_learning_examples():
    """Get all learning examples"""
    try:
        funcs = get_app_functions()
        load_learning_index = funcs.get('load_learning_index')
        if not load_learning_index:
            return jsonify({'success': False, 'error': 'Learning index loader not available'}), 500
        
        index = load_learning_index()
        return jsonify({'success': True, 'examples': index.get('examples', [])})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@learning_bp.route('/api/learning/upload', methods=['POST'])
def upload_learning_example():
    """Upload a single learning example with analysis"""
    try:
        funcs = get_app_functions()
        load_learning_index = funcs.get('load_learning_index')
        save_learning_index = funcs.get('save_learning_index')
        analyze_floorplan_with_ai = funcs.get('analyze_floorplan_with_ai')
        
        if not all([load_learning_index, save_learning_index]):
            return jsonify({'success': False, 'error': 'Learning functions not available'}), 500
        
        if 'floorplan' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['floorplan']
        notes = request.form.get('notes', '')
        corrections = request.form.get('corrections', '{}')
        
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"learning_{timestamp}_{filename}"
        filepath = os.path.join(current_app.config['LEARNING_FOLDER'], unique_filename)
        file.save(filepath)
        
        analysis_result = None
        if analyze_floorplan_with_ai:
            analysis_result = analyze_floorplan_with_ai(filepath)
        
        index = load_learning_index()
        example = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            'filename': unique_filename,
            'notes': notes,
            'corrections': json.loads(corrections) if corrections else {},
            'analysis_result': analysis_result
        }
        
        if 'examples' not in index:
            index['examples'] = []
        index['examples'].append(example)
        save_learning_index(index)
        
        return jsonify({'success': True, 'example': example})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@learning_bp.route('/api/upload-learning-data', methods=['POST'])
def upload_learning_data():
    """Enhanced learning endpoint supporting multiple files and custom symbols"""
    try:
        funcs = get_app_functions()
        load_learning_index = funcs.get('load_learning_index')
        save_learning_index = funcs.get('save_learning_index')
        analyze_floorplan_with_ai = funcs.get('analyze_floorplan_with_ai')
        
        if not all([load_learning_index, save_learning_index]):
            return jsonify({'success': False, 'error': 'Learning functions not available'}), 500
        
        files = request.files.getlist('files')
        notes = request.form.get('notes', '')

        if not files:
            return jsonify({'success': False, 'error': 'No files uploaded'}), 400

        index = load_learning_index()
        if 'examples' not in index:
            index['examples'] = []

        uploaded_examples = []

        for file in files:
            if file.filename == '':
                continue

            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"learning_{timestamp}_{filename}"
            filepath = os.path.join(current_app.config['LEARNING_FOLDER'], unique_filename)
            file.save(filepath)

            # Analyze the uploaded example with AI
            analysis_result = None
            if filename.lower().endswith('.pdf') and analyze_floorplan_with_ai:
                analysis_result = analyze_floorplan_with_ai(filepath)

            example = {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.now().isoformat(),
                'filename': unique_filename,
                'notes': notes,
                'type': 'upload',
                'analysis_result': analysis_result
            }

            index['examples'].append(example)
            uploaded_examples.append(example)

        save_learning_index(index)

        return jsonify({
            'success': True,
            'message': f'Successfully uploaded {len(uploaded_examples)} training example(s)',
            'examples': uploaded_examples
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@learning_bp.route('/api/process-instructions', methods=['POST'])
def process_instructions():
    """Save natural language instructions for AI to follow"""
    try:
        funcs = get_app_functions()
        load_learning_index = funcs.get('load_learning_index')
        save_learning_index = funcs.get('save_learning_index')
        
        if not all([load_learning_index, save_learning_index]):
            return jsonify({'success': False, 'error': 'Learning functions not available'}), 500
        
        data = request.json
        instructions = data.get('instructions', '')

        if not instructions:
            return jsonify({'success': False, 'error': 'No instructions provided'}), 400

        index = load_learning_index()
        if 'examples' not in index:
            index['examples'] = []

        instruction_entry = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            'type': 'instruction',
            'instruction': instructions,
            'notes': f"User instruction: {instructions[:100]}..."
        }

        index['examples'].append(instruction_entry)
        save_learning_index(index)

        return jsonify({
            'success': True,
            'message': 'Instructions saved successfully. AI will apply these rules in future analyses.',
            'instruction': instruction_entry
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@learning_bp.route('/api/learning/history', methods=['GET'])
def learning_history():
    """Get learning history for the learning page"""
    try:
        funcs = get_app_functions()
        load_learning_index = funcs.get('load_learning_index')
        
        if not load_learning_index:
            return jsonify({'success': False, 'error': 'Learning index loader not available'}), 500
        
        index = load_learning_index()
        examples = index.get('examples', [])

        return jsonify({
            'success': True,
            'examples': examples
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

