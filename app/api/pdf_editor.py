"""
PDF Editor Routes Blueprint

Handles PDF editor functionality:
- /api/pdf-editor/templates: Template management
- /api/pdf-editor/templates/<id>: Single template operations
- /api/pdf-editor/templates/last: Get last template
- /api/pdf-editor/autosave: Autosave state
- /api/pdf-editor/save-to-crm: Save and sync with CRM
- /api/pdf-editor/export-pdf: Export to PDF
- /api/pdf-forms: Form management
- /api/pdf-forms/<id>: Single form operations
- /api/pdf-templates/<id>: Get template by ID
- /api/pdf-to-image: Convert PDF to image
"""

import os
import io
import re
import json
import uuid
import base64
import traceback
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file, url_for, current_app
from werkzeug.utils import secure_filename
import logging

from app.utils import load_json_file, save_json_file

logger = logging.getLogger(__name__)

# Create blueprint
pdf_editor_bp = Blueprint('pdf_editor_bp', __name__)


def get_file_paths():
    """Get file paths for PDF editor data"""
    crm_folder = current_app.config.get('CRM_DATA_FOLDER', 'crm_data')
    return {
        'templates': os.path.join(crm_folder, 'pdf_templates.json'),
        'forms': os.path.join(crm_folder, 'pdf_forms.json'),
        'autosave_dir': os.path.join(crm_folder, 'pdf_editor_autosave'),
        'quotes': os.path.join(crm_folder, 'quotes.json'),
    }


# ============================================================================
# PDF TEMPLATES
# ============================================================================

@pdf_editor_bp.route('/api/pdf-editor/templates', methods=['GET', 'POST'])
def handle_pdf_templates():
    """Get all templates or create a new template"""
    try:
        paths = get_file_paths()
        
        if request.method == 'GET':
            templates = load_json_file(paths['templates'], [])
            quote_id = request.args.get('quote_id')
            if quote_id:
                templates = [t for t in templates if t.get('quote_id') == quote_id]
            return jsonify(templates)

        elif request.method == 'POST':
            data = request.json
            templates = load_json_file(paths['templates'], [])

            template = {
                'id': str(uuid.uuid4()),
                'quote_id': data.get('quote_id'),
                'name': data.get('name'),
                'description': data.get('description', ''),
                'canvas_data': data.get('canvas_data'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            templates.append(template)
            save_json_file(paths['templates'], templates)

            return jsonify({'success': True, 'template': template})

    except Exception as e:
        logger.error(f"Error handling PDF templates: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@pdf_editor_bp.route('/api/pdf-editor/templates/<template_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_pdf_template(template_id):
    """Get, update, or delete a specific template"""
    try:
        paths = get_file_paths()
        templates = load_json_file(paths['templates'], [])
        idx = next((i for i, t in enumerate(templates) if t['id'] == template_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Template not found'}), 404

        if request.method == 'GET':
            return jsonify(templates[idx])

        elif request.method == 'PUT':
            data = request.json
            template = templates[idx]

            for field in ['name', 'description', 'canvas_data']:
                if field in data:
                    template[field] = data[field]

            template['updated_at'] = datetime.now().isoformat()
            templates[idx] = template
            save_json_file(paths['templates'], templates)

            return jsonify({'success': True, 'template': template})

        elif request.method == 'DELETE':
            templates.pop(idx)
            save_json_file(paths['templates'], templates)
            return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error handling PDF template: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@pdf_editor_bp.route('/api/pdf-editor/templates/last', methods=['GET'])
def get_last_template():
    """Get the last saved template for a quote"""
    try:
        paths = get_file_paths()
        quote_id = request.args.get('quote_id')
        if not quote_id:
            return jsonify({'success': False, 'error': 'quote_id required'}), 400

        # Check autosave first
        autosave_file = os.path.join(paths['autosave_dir'], f'{quote_id}.json')
        if os.path.exists(autosave_file):
            with open(autosave_file, 'r') as f:
                autosave_data = json.load(f)
                return jsonify({
                    'id': 'autosave',
                    'name': 'Autosaved',
                    'canvas_data': autosave_data.get('canvas_data'),
                    'updated_at': autosave_data.get('updated_at')
                })

        # Otherwise, get last template for this quote
        templates = load_json_file(paths['templates'], [])
        quote_templates = [t for t in templates if t.get('quote_id') == quote_id]

        if quote_templates:
            quote_templates.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
            return jsonify(quote_templates[0])

        return jsonify({'success': False, 'error': 'No templates found'}), 404

    except Exception as e:
        logger.error(f"Error getting last template: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@pdf_editor_bp.route('/api/pdf-editor/autosave', methods=['POST'])
def autosave_pdf_editor():
    """Autosave PDF editor state"""
    try:
        paths = get_file_paths()
        os.makedirs(paths['autosave_dir'], exist_ok=True)
        
        data = request.json
        quote_id = data.get('quote_id')
        form_id = data.get('form_id')
        canvas_data = data.get('canvas_data')

        save_id = quote_id or form_id or 'standalone_' + str(uuid.uuid4())[:8]

        autosave_file = os.path.join(paths['autosave_dir'], f'{save_id}.json')
        autosave_data = {
            'id': save_id,
            'quote_id': quote_id,
            'form_id': form_id,
            'canvas_data': canvas_data,
            'updated_at': datetime.now().isoformat()
        }

        with open(autosave_file, 'w') as f:
            json.dump(autosave_data, f)

        return jsonify({'success': True, 'save_id': save_id})

    except Exception as e:
        logger.error(f"Error autosaving PDF editor: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# PDF FORMS
# ============================================================================

@pdf_editor_bp.route('/api/pdf-forms', methods=['GET', 'POST'])
def handle_pdf_forms():
    """Get all forms or create a new form"""
    try:
        paths = get_file_paths()
        
        if request.method == 'GET':
            forms = load_json_file(paths['forms'], [])
            return jsonify({'success': True, 'forms': forms})

        elif request.method == 'POST':
            data = request.json
            forms = load_json_file(paths['forms'], [])

            form = {
                'id': str(uuid.uuid4()),
                'name': data.get('name', 'Untitled Form'),
                'quote_id': data.get('quote_id'),
                'canvas_data': data.get('canvas_data'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            forms.append(form)
            save_json_file(paths['forms'], forms)

            return jsonify({'success': True, 'form': form})

    except Exception as e:
        logger.error(f"Error handling PDF forms: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@pdf_editor_bp.route('/api/pdf-forms/<form_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_pdf_form(form_id):
    """Get, update, or delete a specific form"""
    try:
        paths = get_file_paths()
        forms = load_json_file(paths['forms'], [])
        idx = next((i for i, f in enumerate(forms) if f['id'] == form_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Form not found'}), 404

        if request.method == 'GET':
            return jsonify({'success': True, 'form': forms[idx]})

        elif request.method == 'PUT':
            data = request.json
            form = forms[idx]

            for field in ['name', 'canvas_data', 'quote_id']:
                if field in data:
                    form[field] = data[field]

            form['updated_at'] = datetime.now().isoformat()
            forms[idx] = form
            save_json_file(paths['forms'], forms)

            return jsonify({'success': True, 'form': form})

        elif request.method == 'DELETE':
            forms.pop(idx)
            save_json_file(paths['forms'], forms)
            return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error handling PDF form: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@pdf_editor_bp.route('/api/pdf-templates/<template_id>', methods=['GET'])
def get_pdf_template_by_id(template_id):
    """Get a specific PDF template by ID"""
    try:
        paths = get_file_paths()
        templates = load_json_file(paths['templates'], [])
        template = next((t for t in templates if t['id'] == template_id), None)
        
        if template:
            return jsonify(template)
        return jsonify({'success': False, 'error': 'Template not found'}), 404
        
    except Exception as e:
        logger.error(f"Error getting PDF template: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@pdf_editor_bp.route('/api/pdf-to-image', methods=['POST'])
def convert_pdf_to_image_api():
    """Convert uploaded PDF to image for use as background"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
            
        filename = secure_filename(file.filename)
        temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f'temp_{uuid.uuid4()}_{filename}')
        file.save(temp_path)
        
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(temp_path)
            page = doc[0]
            
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            output_filename = f'pdf_bg_{uuid.uuid4()}.png'
            output_path = os.path.join(current_app.config['UPLOAD_FOLDER'], output_filename)
            pix.save(output_path)
            
            doc.close()
            os.remove(temp_path)
            
            image_url = f'/uploads/{output_filename}'
            
            return jsonify({
                'success': True,
                'image_url': image_url
            })
            
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e
            
    except Exception as e:
        logger.error(f"Error converting PDF to image: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@pdf_editor_bp.route('/api/pdf-editor/save-to-crm', methods=['POST'])
def save_pdf_editor_to_crm():
    """Save PDF editor state and sync with CRM"""
    try:
        paths = get_file_paths()
        os.makedirs(paths['autosave_dir'], exist_ok=True)
        
        data = request.json
        quote_id = data.get('quote_id')
        canvas_data = data.get('canvas_data')

        if not quote_id:
            return jsonify({'success': False, 'error': 'quote_id required'}), 400

        canvas_obj = json.loads(canvas_data)

        quotes = load_json_file(paths['quotes'], [])
        idx = next((i for i, q in enumerate(quotes) if q['id'] == quote_id), None)

        if idx is None:
            return jsonify({'success': False, 'error': 'Quote not found'}), 404

        quote = quotes[idx]
        updates_made = []

        if 'objects' in canvas_obj:
            for obj in canvas_obj['objects']:
                if 'dataBinding' in obj:
                    binding = obj['dataBinding']
                    field_key = binding.get('field')
                    binding_type = binding.get('type', 'text')

                    if binding_type == 'text':
                        text_content = obj.get('text', '')

                        if field_key and text_content:
                            numbers = re.findall(r'\d+(?:\.\d+)?', text_content)

                            if numbers:
                                value = float(numbers[0])

                                if 'materials_cost' in field_key:
                                    if quote.get('materials_cost') != value:
                                        quote['materials_cost'] = value
                                        updates_made.append(f"Materials cost updated to ${value}")
                                elif 'labor_cost' in field_key or 'labour_cost' in field_key:
                                    if quote.get('labor_cost') != value:
                                        quote['labor_cost'] = value
                                        updates_made.append(f"Labor cost updated to ${value}")
                                elif 'markup_percentage' in field_key:
                                    if quote.get('markup_percentage') != value:
                                        quote['markup_percentage'] = value
                                        updates_made.append(f"Markup updated to {value}%")
                                elif 'quote_amount' in field_key:
                                    if quote.get('quote_amount') != value:
                                        quote['quote_amount'] = value
                                        updates_made.append(f"Quote amount updated to ${value}")

                            elif 'title' in field_key:
                                title_match = re.search(r'Title:\s*(.+)', text_content)
                                if title_match and quote.get('title') != title_match.group(1):
                                    quote['title'] = title_match.group(1)
                                    updates_made.append(f"Title updated")
                            elif 'description' in field_key:
                                desc_match = re.search(r'Description:\s*(.+)', text_content)
                                if desc_match and quote.get('description') != desc_match.group(1):
                                    quote['description'] = desc_match.group(1)
                                    updates_made.append(f"Description updated")

                    elif binding_type == 'table':
                        logger.info(f"Table binding detected for field: {field_key}")

        if any('cost' in u or 'markup' in u for u in updates_made):
            materials = float(quote.get('materials_cost', 0))
            labor = float(quote.get('labor_cost', 0))
            markup_pct = float(quote.get('markup_percentage', 20))

            subtotal = materials + labor
            markup_amount = subtotal * (markup_pct / 100)
            total = subtotal + markup_amount

            quote['quote_amount'] = round(total, 2)
            updates_made.append(f"Total recalculated to ${total:.2f}")

        quote['updated_at'] = datetime.now().isoformat()
        quotes[idx] = quote
        save_json_file(paths['quotes'], quotes)

        autosave_file = os.path.join(paths['autosave_dir'], f'{quote_id}.json')
        with open(autosave_file, 'w') as f:
            json.dump({
                'quote_id': quote_id,
                'canvas_data': canvas_data,
                'updated_at': datetime.now().isoformat()
            }, f)

        return jsonify({
            'success': True,
            'quote': quote,
            'updates_made': updates_made,
            'message': f"{len(updates_made)} update(s) applied to CRM" if updates_made else "Saved to CRM (no changes detected)"
        })

    except Exception as e:
        logger.error(f"Error saving PDF editor to CRM: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@pdf_editor_bp.route('/api/pdf-editor/export-pdf', methods=['POST'])
def export_pdf_from_editor():
    """Export PDF from editor canvas"""
    try:
        import fitz  # PyMuPDF
        from PIL import Image
        
        data = request.json
        quote_id = data.get('quote_id')
        image_data = data.get('image_data')
        quote_data = data.get('quote_data', {})
        form_name = data.get('form_name', 'Form')

        if not image_data:
            return jsonify({'success': False, 'error': 'Missing image data'}), 400

        if ',' in image_data:
            image_data = image_data.split(',')[1]

        image_bytes = base64.b64decode(image_data)

        if quote_id:
            pdf_filename = f"Quote_{quote_data.get('quote_number', quote_id)}.pdf"
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pdf_filename = f"{form_name.replace(' ', '_')}_{timestamp}.pdf"
        pdf_path = os.path.join(current_app.config['OUTPUT_FOLDER'], pdf_filename)

        img = Image.open(io.BytesIO(image_bytes))

        if img.mode != 'RGB':
            img = img.convert('RGB')

        pdf_doc = fitz.open()

        img_width, img_height = img.size
        aspect_ratio = img_width / img_height

        page_width = 595
        page_height = 842

        page = pdf_doc.new_page(width=page_width, height=page_height)

        if aspect_ratio > page_width / page_height:
            fit_width = page_width - 40
            fit_height = fit_width / aspect_ratio
        else:
            fit_height = page_height - 40
            fit_width = fit_height * aspect_ratio

        x = (page_width - fit_width) / 2
        y = (page_height - fit_height) / 2

        img_rect = fitz.Rect(x, y, x + fit_width, y + fit_height)
        page.insert_image(img_rect, stream=image_bytes)

        pdf_doc.save(pdf_path)
        pdf_doc.close()

        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=pdf_filename
        )

    except Exception as e:
        logger.error(f"Error exporting PDF: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

