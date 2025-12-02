"""
CRM Extended Routes Blueprint

Extended CRM functionality:
- Jobs: assign-item
- Quotes: save-from-automation, floorplan, canvas-state, update-from-canvas, stock-items, labour, convert-to-project, pdf
- Markups: projects & quotes markups
- Documents: quotes & jobs documents
- Cost Centres: projects & quotes cost centres
- Room Assignments: projects room assignments
- Inventory search, stock serial numbers
- Link session to project
"""

import os
import io
import json
import uuid
import base64
import traceback
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import logging

logger = logging.getLogger(__name__)

# Create blueprint
crm_extended_bp = Blueprint('crm_extended_bp', __name__)


# ============================================================================
# STORAGE POLICY HELPERS
# ============================================================================

def use_database():
    """Check if database should be used for CRM data."""
    from config import has_database
    return has_database()


def use_json_fallback():
    """Check if JSON fallback is allowed for CRM data."""
    from config import allow_json_persistence
    return allow_json_persistence()


def get_db_layer():
    """Get the database layer if database is configured."""
    if not use_database():
        return None
    try:
        from crm_db_layer import CRMDatabaseLayer
        return CRMDatabaseLayer()
    except Exception as e:
        logger.error(f"Failed to initialize database layer: {e}")
        return None


# ============================================================================
# JSON FILE HELPERS (with storage policy enforcement)
# ============================================================================

def load_json_file(filepath, default=None):
    """
    Load JSON file with default fallback.
    Raises StoragePolicyError if called in production without database.
    """
    from config import is_production, StoragePolicyError
    
    if is_production() and not use_database():
        raise StoragePolicyError(
            "JSON persistence is disabled in production. DATABASE_URL must be configured."
        )
    
    if default is None:
        default = []
    try:
        if filepath and os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
    except StoragePolicyError:
        raise
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
    return default


def save_json_file(filepath, data):
    """
    Save data to JSON file.
    Raises StoragePolicyError if called in production without database.
    """
    from config import is_production, StoragePolicyError
    
    if is_production() and not use_database():
        raise StoragePolicyError(
            "JSON persistence is disabled in production. DATABASE_URL must be configured."
        )
    
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except StoragePolicyError:
        raise
    except Exception as e:
        logger.error(f"Error saving {filepath}: {e}")
        return False


def get_file_paths():
    """Get file paths from app config"""
    return {
        'QUOTES_FILE': current_app.config.get('QUOTES_FILE'),
        'PROJECTS_FILE': current_app.config.get('PROJECTS_FILE'),
        'STOCK_FILE': current_app.config.get('STOCK_FILE'),
        'JOBS_FILE': current_app.config.get('JOBS_FILE'),
        'CRM_DATA_FOLDER': current_app.config.get('CRM_DATA_FOLDER'),
        'BASE_DIR': current_app.config.get('BASE_DIR'),
        'UPLOAD_FOLDER': current_app.config.get('UPLOAD_FOLDER'),
    }


def generate_quote_number(existing_quotes, is_supplier=False):
    """Generate quote number in format: 1 letter + 3 numbers (e.g., A001, B123)"""
    import re
    
    if is_supplier:
        supplier_quotes = [q for q in existing_quotes if q.get('quote_number', '').startswith('S')]
        max_num = 0
        for q in supplier_quotes:
            match = re.match(r'S(\d+)', q.get('quote_number', ''))
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
        return f"S{str(max_num + 1).zfill(3)}"
    
    pattern = re.compile(r'^([A-Z])(\d{3})$')
    letter_counts = {}
    
    for q in existing_quotes:
        qn = q.get('quote_number', '')
        match = pattern.match(qn)
        if match:
            letter = match.group(1)
            num = int(match.group(2))
            if letter not in letter_counts or num > letter_counts[letter]:
                letter_counts[letter] = num
    
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        if letter == 'S':
            continue
        current_max = letter_counts.get(letter, 0)
        if current_max < 999:
            return f"{letter}{str(current_max + 1).zfill(3)}"
    
    return f"Q{datetime.now().strftime('%H%M%S')}"


# ============================================================================
# JOBS - ASSIGN ITEM
# ============================================================================

@crm_extended_bp.route('/api/crm/jobs/<job_id>/assign-item', methods=['POST'])
def assign_item_to_job(job_id):
    """Assign component or cable to a job"""
    try:
        paths = get_file_paths()
        item_data = request.get_json()

        crm_file = os.path.join(paths['BASE_DIR'], 'crm_data.json')
        if os.path.exists(crm_file):
            with open(crm_file, 'r') as f:
                crm_data = json.load(f)
        else:
            crm_data = {'jobs': [], 'stock': [], 'customers': []}

        job = next((j for j in crm_data.get('jobs', []) if j.get('id') == job_id), None)

        if not job:
            return jsonify({'success': False, 'error': 'Job not found'})

        if 'components' not in job:
            job['components'] = []

        job['components'].append({
            'name': item_data.get('name'),
            'category': item_data.get('category'),
            'type': item_data.get('type'),
            'quantity': item_data.get('quantity', 1),
            'cost': item_data.get('cost', 0),
            'notes': item_data.get('notes', ''),
            'specifications': item_data.get('specifications', {}),
            'assignedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        if 'total' in job:
            job['total'] += item_data.get('cost', 0) * item_data.get('quantity', 1)
        else:
            job['total'] = item_data.get('cost', 0) * item_data.get('quantity', 1)

        with open(crm_file, 'w') as f:
            json.dump(crm_data, f, indent=2)

        return jsonify({
            'success': True,
            'message': f"Item assigned to job {job.get('name')}"
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ============================================================================
# QUOTES - SAVE FROM AUTOMATION
# ============================================================================

@crm_extended_bp.route('/api/crm/quotes/save-from-automation', methods=['POST'])
def save_quote_from_automation():
    """Save a quote from Quote Automation to CRM with floorplan"""
    try:
        paths = get_file_paths()
        quote_data = request.get_json()

        if not quote_data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        quote_id = str(uuid.uuid4())
        quotes = load_json_file(paths['QUOTES_FILE'], [])
        quote_number = generate_quote_number(quotes)

        total_amount = quote_data.get('total_amount')
        materials_cost = 0
        labor_cost = 0
        
        if quote_data.get('costs'):
            costs = quote_data['costs']
            materials_cost = costs.get('materials') if costs.get('materials') is not None else costs.get('total_materials', 0)
            labor_cost = costs.get('labor') if costs.get('labor') is not None else costs.get('total_labor', 0)
            
            if total_amount is None:
                cost_total = costs.get('total')
                if cost_total is not None:
                    total_amount = cost_total
                elif materials_cost or labor_cost:
                    total_amount = materials_cost + labor_cost
        
        if total_amount is None:
            total_amount = 0

        new_quote = {
            'id': quote_id,
            'quote_number': quote_number,
            'customer_id': quote_data.get('customer_id'),
            'title': quote_data.get('title', 'Untitled Quote'),
            'description': quote_data.get('description', ''),
            'status': quote_data.get('status', 'draft'),
            'quote_amount': float(total_amount),
            'materials_cost': float(materials_cost),
            'labor_cost': float(labor_cost),
            'markup_percentage': 20.0,
            'valid_until': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'notes': f"Generated from Quote Automation tool",
            'source': 'quote-automation',
            'automation_data': {
                'costs': quote_data.get('costs', {}),
                'analysis': quote_data.get('analysis', {}),
                'components': quote_data.get('components', [])
            },
            'markups': [],
            'stock_items': [],
            'takeoffs_session_id': None,
            'mapping_session_id': None,
            'cad_session_id': None,
            'board_session_id': None,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        floorplan_image = quote_data.get('floorplan_image')
        if floorplan_image:
            floorplans_dir = os.path.join(paths['CRM_DATA_FOLDER'], 'floorplans')
            os.makedirs(floorplans_dir, exist_ok=True)

            image_filename = f"{quote_id}.png"
            image_path = os.path.join(floorplans_dir, image_filename)

            if ',' in floorplan_image:
                floorplan_image = floorplan_image.split(',')[1]

            with open(image_path, 'wb') as f:
                f.write(base64.b64decode(floorplan_image))

            new_quote['floorplan_image'] = f"/api/crm/quotes/{quote_id}/floorplan"

        canvas_state = quote_data.get('canvas_state')
        if canvas_state:
            canvas_dir = os.path.join(paths['CRM_DATA_FOLDER'], 'canvas_states')
            os.makedirs(canvas_dir, exist_ok=True)

            canvas_filename = f"{quote_id}.json"
            canvas_path = os.path.join(canvas_dir, canvas_filename)

            with open(canvas_path, 'w') as f:
                json.dump(canvas_state, f, indent=2)

            new_quote['canvas_state_file'] = canvas_filename

        quotes.append(new_quote)
        save_json_file(paths['QUOTES_FILE'], quotes)

        logger.info(f"Quote saved from automation: {quote_id} - {new_quote['title']}")

        return jsonify({
            'success': True,
            'quote_id': quote_id,
            'quote': new_quote,
            'message': 'Quote saved successfully to CRM'
        })

    except Exception as e:
        logger.error(f"Error saving quote from automation: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/quotes/<quote_id>/floorplan')
def get_quote_floorplan(quote_id):
    """Get the floorplan image for a specific quote"""
    try:
        paths = get_file_paths()
        floorplans_dir = os.path.join(paths['CRM_DATA_FOLDER'], 'floorplans')
        image_path = os.path.join(floorplans_dir, f"{quote_id}.png")

        if not os.path.exists(image_path):
            return jsonify({'error': 'Floorplan not found'}), 404

        return send_file(image_path, mimetype='image/png')

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/quotes/<quote_id>/canvas-state')
def get_quote_canvas_state(quote_id):
    """Get the canvas state for a specific quote to enable editing"""
    try:
        paths = get_file_paths()
        quotes = load_json_file(paths['QUOTES_FILE'], [])
        quote = next((q for q in quotes if q['id'] == quote_id), None)

        if not quote:
            return jsonify({'success': False, 'error': 'Quote not found'}), 404

        canvas_state = None
        canvas_dir = os.path.join(paths['CRM_DATA_FOLDER'], 'canvas_states')
        
        possible_canvas_files = []
        if quote.get('canvas_state_file'):
            possible_canvas_files.append(quote['canvas_state_file'])
        possible_canvas_files.append(f"{quote_id}.json")
        
        floorplan_path_str = quote.get('floorplan_image', '')
        if '/quotes/' in floorplan_path_str:
            parts = floorplan_path_str.split('/')
            for i, part in enumerate(parts):
                if part == 'quotes' and i + 1 < len(parts):
                    possible_canvas_files.append(f"{parts[i+1]}.json")
                    break
        
        for canvas_filename in possible_canvas_files:
            canvas_path = os.path.join(canvas_dir, canvas_filename)
            if os.path.exists(canvas_path):
                try:
                    with open(canvas_path, 'r') as f:
                        canvas_state = json.load(f)
                        break
                except Exception as e:
                    logger.error(f"Error reading canvas state {canvas_filename}: {e}")

        floorplan_image = quote.get('floorplan_image', '')
        floorplan_loaded = False
        
        if floorplan_image:
            floorplan_dir = os.path.join(paths['CRM_DATA_FOLDER'], 'floorplans')
            
            possible_filenames = [f"{quote_id}.png"]
            
            if '/floorplan' in floorplan_image:
                parts = floorplan_image.split('/')
                for i, part in enumerate(parts):
                    if part == 'quotes' and i + 1 < len(parts):
                        possible_filenames.append(f"{parts[i+1]}.png")
                        break
            
            for filename in possible_filenames:
                floorplan_path = os.path.join(floorplan_dir, filename)
                if os.path.exists(floorplan_path):
                    try:
                        with open(floorplan_path, 'rb') as f:
                            image_data = base64.b64encode(f.read()).decode('utf-8')
                            floorplan_image = f"data:image/png;base64,{image_data}"
                            floorplan_loaded = True
                            break
                    except Exception as e:
                        logger.error(f"Error reading floorplan {filename}: {e}")
        
        automation_data = quote.get('automation_data', {})
        components = quote.get('components') if quote.get('components') is not None else automation_data.get('components', [])
        costs = quote.get('costs') if quote.get('costs') is not None else automation_data.get('costs', {})
        analysis = quote.get('analysis') if quote.get('analysis') is not None else automation_data.get('analysis', {})
        
        return jsonify({
            'success': True,
            'quote': {
                'id': quote['id'],
                'title': quote.get('title', ''),
                'description': quote.get('description', ''),
                'total_amount': quote.get('total_amount', 0),
                'quote_amount': quote.get('quote_amount', quote.get('total_amount', 0)),
                'components': components,
                'costs': costs,
                'analysis': analysis,
                'floorplan_image': floorplan_image,
                'customer_id': quote.get('customer_id', ''),
                'status': quote.get('status', 'draft')
            },
            'canvas_state': canvas_state
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/quotes/<quote_id>/update-from-canvas', methods=['POST'])
def update_quote_from_canvas(quote_id):
    """Update a quote with new components and canvas state from canvas editor"""
    try:
        paths = get_file_paths()
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        quotes = load_json_file(paths['QUOTES_FILE'], [])
        idx = next((i for i, q in enumerate(quotes) if q['id'] == quote_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Quote not found'}), 404

        quote = quotes[idx]

        if 'components' in data:
            quote['components'] = data['components']

        if 'total_amount' in data:
            quote['total_amount'] = data['total_amount']

        if 'canvas_state' in data:
            canvas_dir = os.path.join(paths['CRM_DATA_FOLDER'], 'canvas_states')
            os.makedirs(canvas_dir, exist_ok=True)

            canvas_filename = quote.get('canvas_state_file', f"{quote_id}.json")
            canvas_path = os.path.join(canvas_dir, canvas_filename)

            with open(canvas_path, 'w') as f:
                json.dump(data['canvas_state'], f, indent=2)

            quote['canvas_state_file'] = canvas_filename

        if 'floorplan_image' in data:
            floorplans_dir = os.path.join(paths['CRM_DATA_FOLDER'], 'floorplans')
            os.makedirs(floorplans_dir, exist_ok=True)

            image_filename = f"{quote_id}.png"
            image_path = os.path.join(floorplans_dir, image_filename)

            floorplan_image = data['floorplan_image']
            if ',' in floorplan_image:
                floorplan_image = floorplan_image.split(',')[1]

            with open(image_path, 'wb') as f:
                f.write(base64.b64decode(floorplan_image))

            quote['floorplan_image'] = f"/api/crm/quotes/{quote_id}/floorplan"

        quote['updated_at'] = datetime.now().isoformat()
        quotes[idx] = quote
        save_json_file(paths['QUOTES_FILE'], quotes)

        return jsonify({
            'success': True,
            'message': 'Quote updated successfully',
            'quote': quote
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# LINK SESSION TO PROJECT
# ============================================================================

@crm_extended_bp.route('/api/link-session-to-project', methods=['POST'])
def link_session_to_project():
    """Link a takeoffs/mapping session to a CRM project"""
    try:
        paths = get_file_paths()
        app_funcs = current_app.config.get('APP_FUNCTIONS', {})
        load_session_data = app_funcs.get('load_session_data')
        save_session_data = app_funcs.get('save_session_data')
        
        data = request.json
        session_id = data.get('session_id')
        project_id = data.get('project_id')
        link_type = data.get('link_type', 'takeoffs')

        if not session_id or not project_id:
            return jsonify({'success': False, 'error': 'Missing session_id or project_id'}), 400

        if load_session_data and save_session_data:
            session_data = load_session_data(session_id)
            if session_data:
                session_data['project_id'] = project_id
                save_session_data(session_id, session_data)

        projects = load_json_file(paths['PROJECTS_FILE'], [])
        idx = next((i for i, p in enumerate(projects) if p['id'] == project_id), None)

        if idx is not None:
            if link_type == 'takeoffs':
                projects[idx]['takeoffs_session_id'] = session_id
            else:
                projects[idx]['mapping_session_id'] = session_id
            projects[idx]['updated_at'] = datetime.now().isoformat()
            save_json_file(paths['PROJECTS_FILE'], projects)

            return jsonify({
                'success': True,
                'project': projects[idx]
            })
        else:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# PROJECT MARKUPS
# ============================================================================

@crm_extended_bp.route('/api/crm/projects/<project_id>/markups', methods=['GET', 'POST'])
def handle_project_markups(project_id):
    """Manage markups attached to a project"""
    try:
        paths = get_file_paths()
        projects = load_json_file(paths['PROJECTS_FILE'], [])
        idx = next((i for i, p in enumerate(projects) if p['id'] == project_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        project = projects[idx]

        if 'markups' not in project:
            project['markups'] = []

        if request.method == 'GET':
            return jsonify({
                'success': True,
                'markups': project['markups'],
                'project_id': project_id
            })

        else:
            data = request.json
            markup = {
                'id': str(uuid.uuid4()),
                'type': data.get('type', 'general'),
                'name': data.get('name', 'Unnamed Markup'),
                'filename': data.get('filename', ''),
                'session_id': data.get('session_id', ''),
                'description': data.get('description', ''),
                'created_at': datetime.now().isoformat(),
                'created_by': data.get('created_by', 'system')
            }

            project['markups'].append(markup)
            project['updated_at'] = datetime.now().isoformat()
            projects[idx] = project
            save_json_file(paths['PROJECTS_FILE'], projects)

            return jsonify({
                'success': True,
                'markup': markup,
                'project': project
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/projects/<project_id>/markups/<markup_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_project_markup(project_id, markup_id):
    """Manage a specific markup on a project"""
    try:
        paths = get_file_paths()
        projects = load_json_file(paths['PROJECTS_FILE'], [])
        idx = next((i for i, p in enumerate(projects) if p['id'] == project_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        project = projects[idx]
        markups = project.get('markups', [])
        markup_idx = next((i for i, m in enumerate(markups) if m['id'] == markup_id), None)

        if markup_idx is None:
            return jsonify({'success': False, 'error': 'Markup not found'}), 404

        if request.method == 'GET':
            return jsonify({
                'success': True,
                'markup': markups[markup_idx]
            })

        elif request.method == 'PUT':
            data = request.json
            markup = markups[markup_idx]
            for field in ['name', 'description', 'filename', 'type']:
                if field in data:
                    markup[field] = data[field]
            markup['updated_at'] = datetime.now().isoformat()
            markups[markup_idx] = markup
            project['markups'] = markups
            project['updated_at'] = datetime.now().isoformat()
            projects[idx] = project
            save_json_file(paths['PROJECTS_FILE'], projects)

            return jsonify({
                'success': True,
                'markup': markup
            })

        elif request.method == 'DELETE':
            markups.pop(markup_idx)
            project['markups'] = markups
            project['updated_at'] = datetime.now().isoformat()
            projects[idx] = project
            save_json_file(paths['PROJECTS_FILE'], projects)

            return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/projects/<project_id>/markups/<markup_id>/open', methods=['GET'])
def open_project_markup(project_id, markup_id):
    """Open/redirect to appropriate editor for a markup"""
    try:
        paths = get_file_paths()
        projects = load_json_file(paths['PROJECTS_FILE'], [])
        project = next((p for p in projects if p['id'] == project_id), None)

        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        markup = next((m for m in project.get('markups', []) if m['id'] == markup_id), None)

        if not markup:
            return jsonify({'success': False, 'error': 'Markup not found'}), 404

        markup_type = markup.get('type', 'general')
        session_id = markup.get('session_id', '')

        redirect_urls = {
            'takeoffs': f'/canvas?session={session_id}' if session_id else '/canvas',
            'mapping': f'/mapping?session={session_id}' if session_id else '/mapping',
            'cad': f'/electrical-cad?session={session_id}' if session_id else '/electrical-cad',
            'quote': f'/quotes?session={session_id}' if session_id else '/quotes',
            'general': f'/canvas?session={session_id}' if session_id else '/canvas'
        }

        return jsonify({
            'success': True,
            'redirect_url': redirect_urls.get(markup_type, '/canvas'),
            'markup': markup
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# QUOTE MARKUPS
# ============================================================================

@crm_extended_bp.route('/api/crm/quotes/<quote_id>/markups', methods=['GET', 'POST'])
def handle_quote_markups(quote_id):
    """Manage markups attached to a quote"""
    try:
        paths = get_file_paths()
        quotes = load_json_file(paths['QUOTES_FILE'], [])
        idx = next((i for i, q in enumerate(quotes) if q['id'] == quote_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Quote not found'}), 404

        quote = quotes[idx]

        if 'markups' not in quote:
            quote['markups'] = []

        if request.method == 'GET':
            return jsonify({
                'success': True,
                'markups': quote['markups'],
                'quote_id': quote_id
            })

        else:
            data = request.json
            markup = {
                'id': str(uuid.uuid4()),
                'type': data.get('type', 'general'),
                'name': data.get('name', 'Unnamed Markup'),
                'filename': data.get('filename', ''),
                'session_id': data.get('session_id', ''),
                'description': data.get('description', ''),
                'created_at': datetime.now().isoformat(),
                'created_by': data.get('created_by', 'system')
            }

            quote['markups'].append(markup)
            quote['updated_at'] = datetime.now().isoformat()
            quotes[idx] = quote
            save_json_file(paths['QUOTES_FILE'], quotes)

            return jsonify({
                'success': True,
                'markup': markup,
                'quote': quote
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/quotes/<quote_id>/markups/<markup_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_quote_markup(quote_id, markup_id):
    """Manage a specific markup on a quote"""
    try:
        paths = get_file_paths()
        quotes = load_json_file(paths['QUOTES_FILE'], [])
        idx = next((i for i, q in enumerate(quotes) if q['id'] == quote_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Quote not found'}), 404

        quote = quotes[idx]
        markups = quote.get('markups', [])
        markup_idx = next((i for i, m in enumerate(markups) if m['id'] == markup_id), None)

        if markup_idx is None:
            return jsonify({'success': False, 'error': 'Markup not found'}), 404

        if request.method == 'GET':
            return jsonify({
                'success': True,
                'markup': markups[markup_idx]
            })

        elif request.method == 'PUT':
            data = request.json
            markup = markups[markup_idx]
            for field in ['name', 'description', 'filename', 'type']:
                if field in data:
                    markup[field] = data[field]
            markup['updated_at'] = datetime.now().isoformat()
            markups[markup_idx] = markup
            quote['markups'] = markups
            quote['updated_at'] = datetime.now().isoformat()
            quotes[idx] = quote
            save_json_file(paths['QUOTES_FILE'], quotes)

            return jsonify({
                'success': True,
                'markup': markup
            })

        elif request.method == 'DELETE':
            markups.pop(markup_idx)
            quote['markups'] = markups
            quote['updated_at'] = datetime.now().isoformat()
            quotes[idx] = quote
            save_json_file(paths['QUOTES_FILE'], quotes)

            return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/quotes/<quote_id>/markups/<markup_id>/open', methods=['GET'])
def open_quote_markup(quote_id, markup_id):
    """Open/redirect to appropriate editor for a quote markup"""
    try:
        paths = get_file_paths()
        quotes = load_json_file(paths['QUOTES_FILE'], [])
        quote = next((q for q in quotes if q['id'] == quote_id), None)

        if not quote:
            return jsonify({'success': False, 'error': 'Quote not found'}), 404

        markup = next((m for m in quote.get('markups', []) if m['id'] == markup_id), None)

        if not markup:
            return jsonify({'success': False, 'error': 'Markup not found'}), 404

        markup_type = markup.get('type', 'general')
        session_id = markup.get('session_id', '')

        redirect_urls = {
            'takeoffs': f'/canvas?session={session_id}' if session_id else '/canvas',
            'mapping': f'/mapping?session={session_id}' if session_id else '/mapping',
            'cad': f'/electrical-cad?session={session_id}' if session_id else '/electrical-cad',
            'quote': f'/quotes?quote_id={quote_id}',
            'general': f'/canvas?session={session_id}' if session_id else '/canvas'
        }

        return jsonify({
            'success': True,
            'redirect_url': redirect_urls.get(markup_type, '/canvas'),
            'markup': markup
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# QUOTE DOCUMENTS
# ============================================================================

@crm_extended_bp.route('/api/crm/quotes/documents', methods=['POST'])
def upload_quote_documents():
    """Upload documents to a quote"""
    try:
        paths = get_file_paths()
        quote_id = request.form.get('quote_id')
        if not quote_id:
            return jsonify({'success': False, 'error': 'Quote ID required'}), 400
        
        quotes = load_json_file(paths['QUOTES_FILE'], [])
        idx = next((i for i, q in enumerate(quotes) if q['id'] == quote_id), None)
        
        if idx is None:
            return jsonify({'success': False, 'error': 'Quote not found'}), 404
        
        quote = quotes[idx]
        if 'documents' not in quote:
            quote['documents'] = []
        
        files = request.files.getlist('documents')
        uploaded = []
        
        docs_folder = os.path.join(paths['CRM_DATA_FOLDER'], 'documents', 'quotes', quote_id)
        os.makedirs(docs_folder, exist_ok=True)
        
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                doc_id = str(uuid.uuid4())
                filepath = os.path.join(docs_folder, f"{doc_id}_{filename}")
                file.save(filepath)
                
                doc = {
                    'id': doc_id,
                    'filename': filename,
                    'filepath': filepath,
                    'url': f'/api/crm/quotes/{quote_id}/documents/{doc_id}/download',
                    'size': os.path.getsize(filepath),
                    'uploaded_at': datetime.now().isoformat()
                }
                quote['documents'].append(doc)
                uploaded.append(doc)
        
        quote['updated_at'] = datetime.now().isoformat()
        quotes[idx] = quote
        save_json_file(paths['QUOTES_FILE'], quotes)
        
        return jsonify({'success': True, 'documents': uploaded})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/quotes/<quote_id>/documents', methods=['GET'])
def get_quote_documents(quote_id):
    """Get all documents for a quote"""
    try:
        paths = get_file_paths()
        quotes = load_json_file(paths['QUOTES_FILE'], [])
        quote = next((q for q in quotes if q['id'] == quote_id), None)
        
        if not quote:
            return jsonify({'success': False, 'error': 'Quote not found'}), 404
        
        return jsonify({'success': True, 'documents': quote.get('documents', [])})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/quotes/<quote_id>/documents/<doc_id>/download', methods=['GET'])
def download_quote_document(quote_id, doc_id):
    """Download a quote document"""
    try:
        paths = get_file_paths()
        quotes = load_json_file(paths['QUOTES_FILE'], [])
        quote = next((q for q in quotes if q['id'] == quote_id), None)
        
        if not quote:
            return jsonify({'success': False, 'error': 'Quote not found'}), 404
        
        doc = next((d for d in quote.get('documents', []) if d['id'] == doc_id), None)
        if not doc:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        
        if os.path.exists(doc['filepath']):
            return send_file(doc['filepath'], as_attachment=True, download_name=doc['filename'])
        else:
            return jsonify({'success': False, 'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/quotes/<quote_id>/documents/<doc_id>', methods=['DELETE'])
def delete_quote_document(quote_id, doc_id):
    """Delete a quote document"""
    try:
        paths = get_file_paths()
        quotes = load_json_file(paths['QUOTES_FILE'], [])
        idx = next((i for i, q in enumerate(quotes) if q['id'] == quote_id), None)
        
        if idx is None:
            return jsonify({'success': False, 'error': 'Quote not found'}), 404
        
        quote = quotes[idx]
        doc_idx = next((i for i, d in enumerate(quote.get('documents', [])) if d['id'] == doc_id), None)
        
        if doc_idx is None:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        
        doc = quote['documents'][doc_idx]
        
        if os.path.exists(doc['filepath']):
            os.remove(doc['filepath'])
        
        quote['documents'].pop(doc_idx)
        quote['updated_at'] = datetime.now().isoformat()
        quotes[idx] = quote
        save_json_file(paths['QUOTES_FILE'], quotes)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# JOB DOCUMENTS
# ============================================================================

@crm_extended_bp.route('/api/crm/jobs/documents', methods=['POST'])
def upload_job_documents():
    """Upload documents to a job"""
    try:
        import crm_extended as crm_ext
        paths = get_file_paths()
        
        job_id = request.form.get('job_id')
        if not job_id:
            return jsonify({'success': False, 'error': 'Job ID required'}), 400
        
        jobs = crm_ext.get_all_jobs()
        job = next((j for j in jobs if j['id'] == job_id), None)
        
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
        
        if 'documents' not in job:
            job['documents'] = []
        
        files = request.files.getlist('documents')
        uploaded = []
        
        docs_folder = os.path.join(paths['CRM_DATA_FOLDER'], 'documents', 'jobs', job_id)
        os.makedirs(docs_folder, exist_ok=True)
        
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                doc_id = str(uuid.uuid4())
                filepath = os.path.join(docs_folder, f"{doc_id}_{filename}")
                file.save(filepath)
                
                doc = {
                    'id': doc_id,
                    'filename': filename,
                    'filepath': filepath,
                    'url': f'/api/crm/jobs/{job_id}/documents/{doc_id}/download',
                    'size': os.path.getsize(filepath),
                    'uploaded_at': datetime.now().isoformat()
                }
                job['documents'].append(doc)
                uploaded.append(doc)
        
        job['updated_at'] = datetime.now().isoformat()
        crm_ext.save_job(job)
        
        return jsonify({'success': True, 'documents': uploaded})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/jobs/<job_id>/documents', methods=['GET'])
def get_job_documents(job_id):
    """Get all documents for a job"""
    try:
        import crm_extended as crm_ext
        jobs = crm_ext.get_all_jobs()
        job = next((j for j in jobs if j['id'] == job_id), None)
        
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
        
        return jsonify({'success': True, 'documents': job.get('documents', [])})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/jobs/<job_id>/documents/<doc_id>/download', methods=['GET'])
def download_job_document(job_id, doc_id):
    """Download a job document"""
    try:
        import crm_extended as crm_ext
        jobs = crm_ext.get_all_jobs()
        job = next((j for j in jobs if j['id'] == job_id), None)
        
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
        
        doc = next((d for d in job.get('documents', []) if d['id'] == doc_id), None)
        if not doc:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        
        if os.path.exists(doc['filepath']):
            return send_file(doc['filepath'], as_attachment=True, download_name=doc['filename'])
        else:
            return jsonify({'success': False, 'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/jobs/<job_id>/documents/<doc_id>', methods=['DELETE'])
def delete_job_document(job_id, doc_id):
    """Delete a job document"""
    try:
        import crm_extended as crm_ext
        jobs = crm_ext.get_all_jobs()
        job = next((j for j in jobs if j['id'] == job_id), None)
        
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
        
        doc_idx = next((i for i, d in enumerate(job.get('documents', [])) if d['id'] == doc_id), None)
        
        if doc_idx is None:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        
        doc = job['documents'][doc_idx]
        
        if os.path.exists(doc['filepath']):
            os.remove(doc['filepath'])
        
        job['documents'].pop(doc_idx)
        job['updated_at'] = datetime.now().isoformat()
        crm_ext.save_job(job)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# QUOTE STOCK ITEMS & LABOUR
# ============================================================================

@crm_extended_bp.route('/api/crm/quotes/<quote_id>/stock-items', methods=['GET', 'POST'])
def handle_quote_stock_items(quote_id):
    """Manage stock items linked to a quote"""
    try:
        paths = get_file_paths()
        quotes = load_json_file(paths['QUOTES_FILE'], [])
        idx = next((i for i, q in enumerate(quotes) if q['id'] == quote_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Quote not found'}), 404

        quote = quotes[idx]

        if 'stock_items' not in quote:
            quote['stock_items'] = []

        if request.method == 'GET':
            return jsonify({
                'success': True,
                'stock_items': quote['stock_items'],
                'quote_id': quote_id
            })

        else:
            data = request.json
            stock_item = {
                'id': str(uuid.uuid4()),
                'inventory_id': data.get('inventory_id', ''),
                'name': data.get('name', ''),
                'quantity': data.get('quantity', 1),
                'unit_price': data.get('unit_price', 0.0),
                'total_price': data.get('quantity', 1) * data.get('unit_price', 0.0),
                'notes': data.get('notes', ''),
                'added_at': datetime.now().isoformat()
            }

            quote['stock_items'].append(stock_item)
            quote['updated_at'] = datetime.now().isoformat()
            quotes[idx] = quote
            save_json_file(paths['QUOTES_FILE'], quotes)

            return jsonify({
                'success': True,
                'stock_item': stock_item,
                'quote': quote
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/quotes/<quote_id>/stock-items/<item_id>', methods=['DELETE'])
def delete_quote_stock_item(quote_id, item_id):
    """Remove a stock item from a quote"""
    try:
        paths = get_file_paths()
        quotes = load_json_file(paths['QUOTES_FILE'], [])
        idx = next((i for i, q in enumerate(quotes) if q['id'] == quote_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Quote not found'}), 404

        quote = quotes[idx]

        if 'stock_items' not in quote:
            return jsonify({'success': False, 'error': 'No stock items on this quote'}), 404

        item_idx = next((i for i, s in enumerate(quote['stock_items']) if s['id'] == item_id), None)

        if item_idx is None:
            return jsonify({'success': False, 'error': 'Stock item not found'}), 404

        quote['stock_items'].pop(item_idx)
        quote['updated_at'] = datetime.now().isoformat()
        quotes[idx] = quote
        save_json_file(paths['QUOTES_FILE'], quotes)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/quotes/<quote_id>/labour', methods=['GET', 'POST'])
def handle_quote_labour(quote_id):
    """Manage labour items linked to a quote"""
    try:
        paths = get_file_paths()
        quotes = load_json_file(paths['QUOTES_FILE'], [])
        idx = next((i for i, q in enumerate(quotes) if q['id'] == quote_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Quote not found'}), 404

        quote = quotes[idx]

        if 'labour_items' not in quote:
            quote['labour_items'] = []

        if request.method == 'GET':
            total_cost = sum(item.get('total', 0) for item in quote['labour_items'])
            total_hours = sum(item.get('hours', 0) for item in quote['labour_items'])

            return jsonify({
                'success': True,
                'labour_items': quote['labour_items'],
                'total': total_cost,
                'total_hours': total_hours,
                'quote_id': quote_id
            })

        else:
            data = request.json
            labour_item = {
                'id': str(uuid.uuid4()),
                'description': data.get('description', ''),
                'hours': float(data.get('hours', 0)),
                'rate': float(data.get('rate', 0)),
                'total': float(data.get('total', 0)),
                'added_at': datetime.now().isoformat()
            }

            quote['labour_items'].append(labour_item)
            quote['updated_at'] = datetime.now().isoformat()
            quotes[idx] = quote
            save_json_file(paths['QUOTES_FILE'], quotes)

            return jsonify({
                'success': True,
                'labour_item': labour_item,
                'quote': quote
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/quotes/<quote_id>/labour/<labour_id>', methods=['DELETE'])
def delete_quote_labour(quote_id, labour_id):
    """Remove a labour item from a quote"""
    try:
        paths = get_file_paths()
        quotes = load_json_file(paths['QUOTES_FILE'], [])
        idx = next((i for i, q in enumerate(quotes) if q['id'] == quote_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Quote not found'}), 404

        quote = quotes[idx]

        if 'labour_items' not in quote:
            return jsonify({'success': False, 'error': 'No labour items on this quote'}), 404

        item_idx = next((i for i, l in enumerate(quote['labour_items']) if l['id'] == labour_id), None)

        if item_idx is None:
            return jsonify({'success': False, 'error': 'Labour item not found'}), 404

        quote['labour_items'].pop(item_idx)
        quote['updated_at'] = datetime.now().isoformat()
        quotes[idx] = quote
        save_json_file(paths['QUOTES_FILE'], quotes)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/quotes/<quote_id>/convert-to-project', methods=['POST'])
def convert_quote_to_project(quote_id):
    """Convert an accepted quote into a project"""
    try:
        paths = get_file_paths()
        quotes = load_json_file(paths['QUOTES_FILE'], [])
        quote_idx = next((i for i, q in enumerate(quotes) if q['id'] == quote_id), None)

        if quote_idx is None:
            return jsonify({'success': False, 'error': 'Quote not found'}), 404

        quote = quotes[quote_idx]

        projects = load_json_file(paths['PROJECTS_FILE'], [])
        project = {
            'id': str(uuid.uuid4()),
            'customer_id': quote.get('customer_id'),
            'title': quote.get('title', 'Converted from Quote'),
            'description': f"Converted from Quote {quote.get('quote_number', quote_id)}\n\n{quote.get('description', '')}",
            'status': 'pending',
            'priority': 'medium',
            'quote_amount': quote.get('quote_amount', 0.0),
            'actual_amount': 0.0,
            'due_date': None,
            'takeoffs_session_id': quote.get('takeoffs_session_id'),
            'mapping_session_id': quote.get('mapping_session_id'),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'markups': quote.get('markups', []).copy(),
            'source_quote_id': quote_id
        }

        projects.append(project)
        save_json_file(paths['PROJECTS_FILE'], projects)

        quote['status'] = 'accepted'
        quote['converted_to_project_id'] = project['id']
        quote['converted_at'] = datetime.now().isoformat()
        quote['updated_at'] = datetime.now().isoformat()
        quotes[quote_idx] = quote
        save_json_file(paths['QUOTES_FILE'], quotes)

        return jsonify({
            'success': True,
            'project': project,
            'quote': quote,
            'message': f"Quote converted to project successfully"
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# COST CENTRES - PROJECTS
# ============================================================================

COST_CENTRE_COLORS = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#F44336', '#00BCD4', '#795548', '#607D8B']


@crm_extended_bp.route('/api/crm/projects/<project_id>/cost-centres', methods=['GET', 'POST'])
def handle_project_cost_centres(project_id):
    """Manage cost centres for a project"""
    try:
        paths = get_file_paths()
        projects = load_json_file(paths['PROJECTS_FILE'], [])
        idx = next((i for i, p in enumerate(projects) if p['id'] == project_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        project = projects[idx]

        if 'cost_centres' not in project:
            project['cost_centres'] = []

        if request.method == 'GET':
            total = sum(cc.get('subtotal', 0) for cc in project['cost_centres'])
            return jsonify({
                'success': True,
                'cost_centres': project['cost_centres'],
                'total': total,
                'project_id': project_id
            })

        else:
            data = request.json
            color_idx = len(project['cost_centres']) % len(COST_CENTRE_COLORS)
            cost_centre = {
                'id': str(uuid.uuid4()),
                'name': data.get('name', 'New Cost Centre'),
                'description': data.get('description', ''),
                'color': data.get('color', COST_CENTRE_COLORS[color_idx]),
                'items': [],
                'subtotal': 0.0,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            project['cost_centres'].append(cost_centre)
            project['updated_at'] = datetime.now().isoformat()
            projects[idx] = project
            save_json_file(paths['PROJECTS_FILE'], projects)

            return jsonify({
                'success': True,
                'cost_centre': cost_centre,
                'project': project
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/projects/<project_id>/cost-centres/<centre_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_project_cost_centre(project_id, centre_id):
    """Manage a specific cost centre"""
    try:
        paths = get_file_paths()
        projects = load_json_file(paths['PROJECTS_FILE'], [])
        idx = next((i for i, p in enumerate(projects) if p['id'] == project_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        project = projects[idx]

        if 'cost_centres' not in project:
            return jsonify({'success': False, 'error': 'No cost centres'}), 404

        cc_idx = next((i for i, cc in enumerate(project['cost_centres']) if cc['id'] == centre_id), None)

        if cc_idx is None:
            return jsonify({'success': False, 'error': 'Cost centre not found'}), 404

        if request.method == 'GET':
            return jsonify({
                'success': True,
                'cost_centre': project['cost_centres'][cc_idx]
            })

        elif request.method == 'PUT':
            data = request.json
            cc = project['cost_centres'][cc_idx]
            for field in ['name', 'description', 'color']:
                if field in data:
                    cc[field] = data[field]
            cc['updated_at'] = datetime.now().isoformat()
            project['cost_centres'][cc_idx] = cc
            project['updated_at'] = datetime.now().isoformat()
            projects[idx] = project
            save_json_file(paths['PROJECTS_FILE'], projects)

            return jsonify({
                'success': True,
                'cost_centre': cc
            })

        elif request.method == 'DELETE':
            project['cost_centres'].pop(cc_idx)
            project['updated_at'] = datetime.now().isoformat()
            projects[idx] = project
            save_json_file(paths['PROJECTS_FILE'], projects)

            return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/projects/<project_id>/cost-centres/<centre_id>/items', methods=['POST'])
def add_project_cost_centre_item(project_id, centre_id):
    """Add item to a cost centre"""
    try:
        paths = get_file_paths()
        projects = load_json_file(paths['PROJECTS_FILE'], [])
        idx = next((i for i, p in enumerate(projects) if p['id'] == project_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        project = projects[idx]
        cc_idx = next((i for i, cc in enumerate(project.get('cost_centres', [])) if cc['id'] == centre_id), None)

        if cc_idx is None:
            return jsonify({'success': False, 'error': 'Cost centre not found'}), 404

        data = request.json
        quantity = data.get('quantity', 1)
        unit_price = data.get('unit_price', 0.0)

        item = {
            'id': str(uuid.uuid4()),
            'name': data.get('name', ''),
            'description': data.get('description', ''),
            'quantity': quantity,
            'unit_price': unit_price,
            'total': quantity * unit_price,
            'inventory_id': data.get('inventory_id', ''),
            'sku': data.get('sku', ''),
            'notes': data.get('notes', ''),
            'added_at': datetime.now().isoformat()
        }

        project['cost_centres'][cc_idx]['items'].append(item)
        project['cost_centres'][cc_idx]['subtotal'] = sum(
            i.get('total', 0) for i in project['cost_centres'][cc_idx]['items']
        )
        project['cost_centres'][cc_idx]['updated_at'] = datetime.now().isoformat()
        project['updated_at'] = datetime.now().isoformat()
        projects[idx] = project
        save_json_file(paths['PROJECTS_FILE'], projects)

        return jsonify({
            'success': True,
            'item': item,
            'cost_centre': project['cost_centres'][cc_idx]
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/projects/<project_id>/cost-centres/<centre_id>/items/<item_id>', methods=['PUT', 'DELETE'])
def handle_project_cost_centre_item(project_id, centre_id, item_id):
    """Update or delete an item in a cost centre"""
    try:
        paths = get_file_paths()
        projects = load_json_file(paths['PROJECTS_FILE'], [])
        idx = next((i for i, p in enumerate(projects) if p['id'] == project_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        project = projects[idx]
        cc_idx = next((i for i, cc in enumerate(project.get('cost_centres', [])) if cc['id'] == centre_id), None)

        if cc_idx is None:
            return jsonify({'success': False, 'error': 'Cost centre not found'}), 404

        item_idx = next((i for i, it in enumerate(project['cost_centres'][cc_idx]['items']) if it['id'] == item_id), None)

        if item_idx is None:
            return jsonify({'success': False, 'error': 'Item not found'}), 404

        if request.method == 'PUT':
            data = request.json
            item = project['cost_centres'][cc_idx]['items'][item_idx]
            for field in ['name', 'description', 'quantity', 'unit_price', 'inventory_id', 'sku', 'notes']:
                if field in data:
                    item[field] = data[field]
            item['total'] = item.get('quantity', 1) * item.get('unit_price', 0)
            item['updated_at'] = datetime.now().isoformat()
            project['cost_centres'][cc_idx]['items'][item_idx] = item

        elif request.method == 'DELETE':
            project['cost_centres'][cc_idx]['items'].pop(item_idx)

        project['cost_centres'][cc_idx]['subtotal'] = sum(
            i.get('total', 0) for i in project['cost_centres'][cc_idx]['items']
        )
        project['cost_centres'][cc_idx]['updated_at'] = datetime.now().isoformat()
        project['updated_at'] = datetime.now().isoformat()
        projects[idx] = project
        save_json_file(paths['PROJECTS_FILE'], projects)

        if request.method == 'PUT':
            return jsonify({
                'success': True,
                'item': project['cost_centres'][cc_idx]['items'][item_idx],
                'cost_centre': project['cost_centres'][cc_idx]
            })
        else:
            return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# COST CENTRES - QUOTES
# ============================================================================

@crm_extended_bp.route('/api/crm/quotes/<quote_id>/cost-centres', methods=['GET', 'POST'])
def handle_quote_cost_centres(quote_id):
    """Manage cost centres for a quote"""
    try:
        paths = get_file_paths()
        quotes = load_json_file(paths['QUOTES_FILE'], [])
        idx = next((i for i, q in enumerate(quotes) if q['id'] == quote_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Quote not found'}), 404

        quote = quotes[idx]

        if 'cost_centres' not in quote:
            quote['cost_centres'] = []

        if request.method == 'GET':
            total = sum(cc.get('subtotal', 0) for cc in quote['cost_centres'])
            return jsonify({
                'success': True,
                'cost_centres': quote['cost_centres'],
                'total': total,
                'quote_id': quote_id
            })

        else:
            data = request.json
            color_idx = len(quote['cost_centres']) % len(COST_CENTRE_COLORS)
            cost_centre = {
                'id': str(uuid.uuid4()),
                'name': data.get('name', 'New Cost Centre'),
                'description': data.get('description', ''),
                'color': data.get('color', COST_CENTRE_COLORS[color_idx]),
                'items': [],
                'subtotal': 0.0,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            quote['cost_centres'].append(cost_centre)
            quote['updated_at'] = datetime.now().isoformat()
            quotes[idx] = quote
            save_json_file(paths['QUOTES_FILE'], quotes)

            return jsonify({
                'success': True,
                'cost_centre': cost_centre,
                'quote': quote
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/quotes/<quote_id>/cost-centres/<centre_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_quote_cost_centre(quote_id, centre_id):
    """Manage a specific cost centre on a quote"""
    try:
        paths = get_file_paths()
        quotes = load_json_file(paths['QUOTES_FILE'], [])
        idx = next((i for i, q in enumerate(quotes) if q['id'] == quote_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Quote not found'}), 404

        quote = quotes[idx]

        if 'cost_centres' not in quote:
            return jsonify({'success': False, 'error': 'No cost centres'}), 404

        cc_idx = next((i for i, cc in enumerate(quote['cost_centres']) if cc['id'] == centre_id), None)

        if cc_idx is None:
            return jsonify({'success': False, 'error': 'Cost centre not found'}), 404

        if request.method == 'GET':
            return jsonify({
                'success': True,
                'cost_centre': quote['cost_centres'][cc_idx]
            })

        elif request.method == 'PUT':
            data = request.json
            cc = quote['cost_centres'][cc_idx]
            for field in ['name', 'description', 'color']:
                if field in data:
                    cc[field] = data[field]
            cc['updated_at'] = datetime.now().isoformat()
            quote['cost_centres'][cc_idx] = cc
            quote['updated_at'] = datetime.now().isoformat()
            quotes[idx] = quote
            save_json_file(paths['QUOTES_FILE'], quotes)

            return jsonify({
                'success': True,
                'cost_centre': cc
            })

        elif request.method == 'DELETE':
            quote['cost_centres'].pop(cc_idx)
            quote['updated_at'] = datetime.now().isoformat()
            quotes[idx] = quote
            save_json_file(paths['QUOTES_FILE'], quotes)

            return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/quotes/<quote_id>/cost-centres/<centre_id>/items', methods=['POST'])
def add_quote_cost_centre_item(quote_id, centre_id):
    """Add item to a quote cost centre"""
    try:
        paths = get_file_paths()
        quotes = load_json_file(paths['QUOTES_FILE'], [])
        idx = next((i for i, q in enumerate(quotes) if q['id'] == quote_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Quote not found'}), 404

        quote = quotes[idx]
        cc_idx = next((i for i, cc in enumerate(quote.get('cost_centres', [])) if cc['id'] == centre_id), None)

        if cc_idx is None:
            return jsonify({'success': False, 'error': 'Cost centre not found'}), 404

        data = request.json
        quantity = data.get('quantity', 1)
        unit_price = data.get('unit_price', 0.0)

        item = {
            'id': str(uuid.uuid4()),
            'name': data.get('name', ''),
            'description': data.get('description', ''),
            'quantity': quantity,
            'unit_price': unit_price,
            'total': quantity * unit_price,
            'inventory_id': data.get('inventory_id', ''),
            'sku': data.get('sku', ''),
            'notes': data.get('notes', ''),
            'added_at': datetime.now().isoformat()
        }

        quote['cost_centres'][cc_idx]['items'].append(item)
        quote['cost_centres'][cc_idx]['subtotal'] = sum(
            i.get('total', 0) for i in quote['cost_centres'][cc_idx]['items']
        )
        quote['cost_centres'][cc_idx]['updated_at'] = datetime.now().isoformat()
        quote['updated_at'] = datetime.now().isoformat()
        quotes[idx] = quote
        save_json_file(paths['QUOTES_FILE'], quotes)

        return jsonify({
            'success': True,
            'item': item,
            'cost_centre': quote['cost_centres'][cc_idx]
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/quotes/<quote_id>/cost-centres/<centre_id>/items/<item_id>', methods=['PUT', 'DELETE'])
def handle_quote_cost_centre_item(quote_id, centre_id, item_id):
    """Update or delete an item in a quote cost centre"""
    try:
        paths = get_file_paths()
        quotes = load_json_file(paths['QUOTES_FILE'], [])
        idx = next((i for i, q in enumerate(quotes) if q['id'] == quote_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Quote not found'}), 404

        quote = quotes[idx]
        cc_idx = next((i for i, cc in enumerate(quote.get('cost_centres', [])) if cc['id'] == centre_id), None)

        if cc_idx is None:
            return jsonify({'success': False, 'error': 'Cost centre not found'}), 404

        item_idx = next((i for i, it in enumerate(quote['cost_centres'][cc_idx]['items']) if it['id'] == item_id), None)

        if item_idx is None:
            return jsonify({'success': False, 'error': 'Item not found'}), 404

        if request.method == 'PUT':
            data = request.json
            item = quote['cost_centres'][cc_idx]['items'][item_idx]
            for field in ['name', 'description', 'quantity', 'unit_price', 'inventory_id', 'sku', 'notes']:
                if field in data:
                    item[field] = data[field]
            item['total'] = item.get('quantity', 1) * item.get('unit_price', 0)
            item['updated_at'] = datetime.now().isoformat()
            quote['cost_centres'][cc_idx]['items'][item_idx] = item

        elif request.method == 'DELETE':
            quote['cost_centres'][cc_idx]['items'].pop(item_idx)

        quote['cost_centres'][cc_idx]['subtotal'] = sum(
            i.get('total', 0) for i in quote['cost_centres'][cc_idx]['items']
        )
        quote['cost_centres'][cc_idx]['updated_at'] = datetime.now().isoformat()
        quote['updated_at'] = datetime.now().isoformat()
        quotes[idx] = quote
        save_json_file(paths['QUOTES_FILE'], quotes)

        if request.method == 'PUT':
            return jsonify({
                'success': True,
                'item': quote['cost_centres'][cc_idx]['items'][item_idx],
                'cost_centre': quote['cost_centres'][cc_idx]
            })
        else:
            return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# ROOM ASSIGNMENTS
# ============================================================================

@crm_extended_bp.route('/api/crm/projects/<project_id>/room-assignments', methods=['GET', 'POST'])
def handle_project_room_assignments(project_id):
    """Manage room assignments for a project"""
    try:
        paths = get_file_paths()
        projects = load_json_file(paths['PROJECTS_FILE'], [])
        idx = next((i for i, p in enumerate(projects) if p['id'] == project_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        project = projects[idx]

        if 'room_assignments' not in project:
            project['room_assignments'] = []

        if request.method == 'GET':
            return jsonify({
                'success': True,
                'room_assignments': project['room_assignments'],
                'project_id': project_id
            })

        else:
            data = request.json
            assignment = {
                'id': str(uuid.uuid4()),
                'room_name': data.get('room_name', ''),
                'room_type': data.get('room_type', ''),
                'components': data.get('components', []),
                'notes': data.get('notes', ''),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            project['room_assignments'].append(assignment)
            project['updated_at'] = datetime.now().isoformat()
            projects[idx] = project
            save_json_file(paths['PROJECTS_FILE'], projects)

            return jsonify({
                'success': True,
                'room_assignment': assignment,
                'project': project
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/projects/<project_id>/room-assignments/<assignment_id>', methods=['PUT', 'DELETE'])
def handle_project_room_assignment(project_id, assignment_id):
    """Update or delete a room assignment"""
    try:
        paths = get_file_paths()
        projects = load_json_file(paths['PROJECTS_FILE'], [])
        idx = next((i for i, p in enumerate(projects) if p['id'] == project_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        project = projects[idx]
        ra_idx = next((i for i, ra in enumerate(project.get('room_assignments', [])) if ra['id'] == assignment_id), None)

        if ra_idx is None:
            return jsonify({'success': False, 'error': 'Room assignment not found'}), 404

        if request.method == 'PUT':
            data = request.json
            assignment = project['room_assignments'][ra_idx]
            for field in ['room_name', 'room_type', 'components', 'notes']:
                if field in data:
                    assignment[field] = data[field]
            assignment['updated_at'] = datetime.now().isoformat()
            project['room_assignments'][ra_idx] = assignment
            project['updated_at'] = datetime.now().isoformat()
            projects[idx] = project
            save_json_file(paths['PROJECTS_FILE'], projects)

            return jsonify({
                'success': True,
                'room_assignment': assignment
            })

        elif request.method == 'DELETE':
            project['room_assignments'].pop(ra_idx)
            project['updated_at'] = datetime.now().isoformat()
            projects[idx] = project
            save_json_file(paths['PROJECTS_FILE'], projects)

            return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# SERIAL NUMBERS
# ============================================================================

@crm_extended_bp.route('/api/crm/stock/<item_id>/serial-numbers', methods=['GET', 'POST'])
def handle_stock_serial_numbers(item_id):
    """Manage serial numbers for a stock item"""
    try:
        paths = get_file_paths()
        stock = load_json_file(paths['STOCK_FILE'], [])
        idx = next((i for i, s in enumerate(stock) if s['id'] == item_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Stock item not found'}), 404

        item = stock[idx]

        if 'serial_numbers' not in item:
            item['serial_numbers'] = []

        if request.method == 'GET':
            return jsonify({
                'success': True,
                'serial_numbers': item['serial_numbers'],
                'item_id': item_id
            })

        else:
            data = request.json
            serial = {
                'serial_number': data.get('serial_number', ''),
                'status': data.get('status', 'available'),
                'location': data.get('location', ''),
                'notes': data.get('notes', ''),
                'added_at': datetime.now().isoformat()
            }

            item['serial_numbers'].append(serial)
            item['updated_at'] = datetime.now().isoformat()
            stock[idx] = item
            save_json_file(paths['STOCK_FILE'], stock)

            return jsonify({
                'success': True,
                'serial_number': serial,
                'item': item
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@crm_extended_bp.route('/api/crm/stock/<item_id>/serial-numbers/<serial_index>', methods=['PUT', 'DELETE'])
def handle_stock_serial_number(item_id, serial_index):
    """Update or delete a serial number"""
    try:
        paths = get_file_paths()
        stock = load_json_file(paths['STOCK_FILE'], [])
        idx = next((i for i, s in enumerate(stock) if s['id'] == item_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Stock item not found'}), 404

        item = stock[idx]
        serial_idx = int(serial_index)

        if serial_idx >= len(item.get('serial_numbers', [])):
            return jsonify({'success': False, 'error': 'Serial number not found'}), 404

        if request.method == 'PUT':
            data = request.json
            serial = item['serial_numbers'][serial_idx]
            for field in ['serial_number', 'status', 'location', 'notes']:
                if field in data:
                    serial[field] = data[field]
            serial['updated_at'] = datetime.now().isoformat()
            item['serial_numbers'][serial_idx] = serial
            item['updated_at'] = datetime.now().isoformat()
            stock[idx] = item
            save_json_file(paths['STOCK_FILE'], stock)

            return jsonify({
                'success': True,
                'serial_number': serial
            })

        elif request.method == 'DELETE':
            item['serial_numbers'].pop(serial_idx)
            item['updated_at'] = datetime.now().isoformat()
            stock[idx] = item
            save_json_file(paths['STOCK_FILE'], stock)

            return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# QUOTE PDF GENERATION
# ============================================================================

@crm_extended_bp.route('/api/crm/quotes/<quote_id>/pdf', methods=['POST'])
def generate_quote_pdf(quote_id):
    """Generate a PDF for a quote with custom formatting"""
    try:
        paths = get_file_paths()
        quotes = load_json_file(paths['QUOTES_FILE'], [])
        quote = next((q for q in quotes if q['id'] == quote_id), None)

        if not quote:
            return jsonify({'success': False, 'error': 'Quote not found'}), 404

        # Get customer details
        customers_file = os.path.join(os.path.dirname(paths['QUOTES_FILE']), 'customers.json')
        customers = load_json_file(customers_file, [])
        customer = next((c for c in customers if c['id'] == quote.get('customer_id')), None)

        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2196F3'),
            spaceAfter=30,
            alignment=1
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1976D2'),
            spaceAfter=12
        )

        # Title
        story.append(Paragraph("QUOTE", title_style))
        story.append(Spacer(1, 0.2*inch))

        # Quote details
        quote_info = [
            ['Quote Number:', quote.get('quote_number', 'N/A')],
            ['Date:', datetime.now().strftime('%B %d, %Y')],
            ['Valid Until:', quote.get('valid_until', 'N/A')],
            ['Status:', quote.get('status', 'draft').upper()]
        ]

        info_table = Table(quote_info, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.3*inch))

        # Customer Information
        if customer:
            story.append(Paragraph("Customer Information", heading_style))
            customer_info = [
                ['Name:', customer.get('name', 'N/A')],
                ['Email:', customer.get('email', 'N/A')],
                ['Phone:', customer.get('phone', 'N/A')],
                ['Address:', customer.get('address', 'N/A')]
            ]
            customer_table = Table(customer_info, colWidths=[2*inch, 4*inch])
            customer_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(customer_table)
            story.append(Spacer(1, 0.3*inch))

        # Quote Details
        story.append(Paragraph("Quote Details", heading_style))
        story.append(Paragraph(f"<b>Title:</b> {quote.get('title', 'N/A')}", styles['Normal']))
        story.append(Spacer(1, 0.1*inch))
        if quote.get('description'):
            story.append(Paragraph(f"<b>Description:</b><br/>{quote.get('description', '')}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))

        # Items (Stock Items)
        stock_items = quote.get('stock_items', [])
        if stock_items:
            story.append(Paragraph("Items", heading_style))
            items_data = [['Item', 'Quantity', 'Unit Price', 'Total']]
            for item in stock_items:
                qty = item.get('quantity', 1)
                price = item.get('price', item.get('unit_price', 0))
                total = qty * price
                items_data.append([
                    item.get('name', 'N/A'),
                    str(qty),
                    f"${price:.2f}",
                    f"${total:.2f}"
                ])

            items_table = Table(items_data, colWidths=[3*inch, 1*inch, 1.2*inch, 1.2*inch])
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2196F3')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(items_table)
            story.append(Spacer(1, 0.3*inch))

        # Pricing Summary
        story.append(Paragraph("Pricing Summary", heading_style))
        materials_cost = quote.get('materials_cost', 0)
        labor_cost = quote.get('labor_cost', 0)
        subtotal = materials_cost + labor_cost
        markup_pct = quote.get('markup_percentage', 0)
        markup_amount = subtotal * (markup_pct / 100)
        total = subtotal + markup_amount

        if stock_items:
            stock_total = sum(item.get('quantity', 1) * item.get('price', item.get('unit_price', 0)) for item in stock_items)
            subtotal = max(subtotal, stock_total)
            markup_amount = subtotal * (markup_pct / 100)
            total = subtotal + markup_amount

        pricing_data = [
            ['Materials Cost:', f"${materials_cost:.2f}"],
            ['Labor Cost:', f"${labor_cost:.2f}"],
            ['Subtotal:', f"${subtotal:.2f}"],
            [f'Markup ({markup_pct}%):', f"${markup_amount:.2f}"],
            ['TOTAL:', f"${total:.2f}"]
        ]

        pricing_table = Table(pricing_data, colWidths=[4*inch, 2*inch])
        pricing_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -2), 'Helvetica'),
            ('FONTNAME', (1, 0), (1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 14),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#2196F3')),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#2196F3')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(pricing_table)
        story.append(Spacer(1, 0.5*inch))

        # Footer
        story.append(Paragraph("Terms & Conditions", heading_style))
        story.append(Paragraph(
            "This quote is valid until the date specified above. "
            "Payment terms and conditions apply. Thank you for your business!",
            styles['Normal']
        ))

        # Build PDF
        doc.build(story)
        buffer.seek(0)

        from flask import make_response
        response = make_response(buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=quote_{quote.get("quote_number", quote_id)}.pdf'
        return response

    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
