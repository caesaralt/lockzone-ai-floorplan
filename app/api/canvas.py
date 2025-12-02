"""
Canvas and Takeoffs Routes Blueprint

Handles canvas editor and takeoffs functionality:
- /api/canvas/upload: Upload floor plan for canvas
- /api/canvas/export: Export annotated canvas
- /api/takeoffs/export: Export takeoffs with quote generation
- /api/session/<session_id>: Get session data
"""

import os
import io
import base64
import traceback
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import logging

from app.utils import pdf_to_image_base64

logger = logging.getLogger(__name__)

# Create blueprint
canvas_bp = Blueprint('canvas_bp', __name__)


def get_app_functions():
    """Get functions from main app"""
    return current_app.config.get('APP_FUNCTIONS', {})


# ============================================================================
# CANVAS ROUTES
# ============================================================================

@canvas_bp.route('/api/canvas/upload', methods=['POST'])
def canvas_upload():
    """Upload floor plan for canvas editor"""
    try:
        if 'floorplan' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['floorplan']
        if file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        if filename.lower().endswith('.pdf'):
            img_base64 = pdf_to_image_base64(filepath)
        else:
            with open(filepath, 'rb') as f:
                img_base64 = base64.b64encode(f.read()).decode('utf-8')
        
        return jsonify({
            'success': True,
            'filename': filename,
            'image_data': f'data:image/png;base64,{img_base64}'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@canvas_bp.route('/api/canvas/export', methods=['POST'])
def canvas_export():
    """Export annotated canvas image"""
    try:
        data = request.json
        symbols = data.get('symbols', [])
        base_image = data.get('base_image', '')
        
        output_filename = f"annotated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        output_path = os.path.join(current_app.config['OUTPUT_FOLDER'], output_filename)
        
        if base_image.startswith('data:image'):
            img_data = base64.b64decode(base_image.split(',')[1])
            img = Image.open(io.BytesIO(img_data))
        else:
            return jsonify({'error': 'Invalid image data'}), 400
        
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        except:
            font = ImageFont.load_default()
        
        for symbol in symbols:
            x = symbol.get('x', 0)
            y = symbol.get('y', 0)
            text = symbol.get('symbol', '?')
            draw.text((x, y), text, fill='red', font=font)
        
        img.save(output_path)
        
        return send_file(output_path, as_attachment=True, download_name=output_filename)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# TAKEOFFS ROUTES
# ============================================================================

@canvas_bp.route('/api/takeoffs/export', methods=['POST'])
def takeoffs_export():
    """Export takeoffs data with updated symbols and generate final quote"""
    try:
        funcs = get_app_functions()
        load_session_data = funcs.get('load_session_data')
        save_session_data = funcs.get('save_session_data')
        get_session_id = funcs.get('get_session_id')
        load_data = funcs.get('load_data')
        generate_marked_up_image = funcs.get('generate_marked_up_image')
        
        data = request.json
        session_id = data.get('session_id')
        symbols = data.get('symbols', [])
        project_name = data.get('project_name', 'Untitled Project')
        tier = data.get('tier', 'basic')

        # Update session data with edited symbols
        session_data = load_session_data(session_id) if load_session_data else None

        # Create new session if it doesn't exist
        if not session_data:
            session_id = get_session_id() if get_session_id else f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            session_data = {
                'session_id': session_id,
                'project_name': project_name,
                'tier': tier,
                'symbols': symbols,
                'created_at': datetime.now().isoformat()
            }
            if save_session_data:
                save_session_data(session_id, session_data)
        else:
            session_data['symbols'] = symbols
            if save_session_data:
                save_session_data(session_id, session_data)

        # Load automation data for pricing
        data_config = load_data() if load_data else {'automation_types': {}, 'labor_rate': 75, 'markup_percentage': 20}

        # Calculate costs from edited symbols
        cost_items = []
        total_automation_points = len(symbols)

        for symbol in symbols:
            automation_key = symbol.get('automation_category') or symbol.get('type')
            if automation_key in data_config.get('automation_types', {}):
                automation_config = data_config['automation_types'][automation_key]
                unit_cost = automation_config.get('base_cost_per_unit', {}).get(tier, 0)
                labor_hours = automation_config.get('labor_hours', {}).get(tier, 0)
                labor_cost = labor_hours * data_config.get('labor_rate', 75)

                cost_items.append({
                    'type': automation_config.get('name', automation_key),
                    'quantity': 1,
                    'unit_cost': unit_cost,
                    'labor_cost': labor_cost,
                    'total': unit_cost + labor_cost,
                    'room': symbol.get('room', 'Unassigned')
                })

            # Add custom items with quantities
            if symbol.get('items'):
                for item in symbol['items']:
                    price = item.get('price', 0)
                    quantity = item.get('quantity', 1)
                    cost_items.append({
                        'type': item.get('name', 'Custom Item'),
                        'quantity': quantity,
                        'unit_cost': price,
                        'labor_cost': 0,
                        'total': price * quantity,
                        'room': symbol.get('room', 'Unassigned')
                    })

        subtotal = sum(item['total'] for item in cost_items)
        markup_pct = data_config.get('markup_percentage', 20)
        markup = subtotal * (markup_pct / 100)
        grand_total = subtotal + markup

        # Generate annotated floor plan with updated symbols
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        annotated_filename = f"takeoffs_{timestamp}.png"
        quote_filename = f"quote_{timestamp}.pdf"
        annotated_path = os.path.join(current_app.config['OUTPUT_FOLDER'], annotated_filename)
        quote_path = os.path.join(current_app.config['OUTPUT_FOLDER'], quote_filename)

        # Get original floor plan (may not exist for new sessions)
        original_pdf = session_data.get('original_pdf', '') or session_data.get('floorplan_image', '')
        original_pdf_path = os.path.join(current_app.config['UPLOAD_FOLDER'], original_pdf) if original_pdf else None

        # Generate marked-up image with edited symbols
        mapping_data = {
            'components': symbols,
            'analysis': {
                'scale': session_data.get('analysis_result', {}).get('scale', 'not detected'),
                'total_rooms': session_data.get('total_rooms', 0),
                'notes': 'Edited in Takeoffs'
            }
        }

        if original_pdf_path and os.path.exists(original_pdf_path) and generate_marked_up_image:
            generate_marked_up_image(original_pdf_path, mapping_data, annotated_path)
        else:
            # Fallback: use existing annotated image
            import shutil
            floorplan_image = session_data.get('floorplan_image', '')
            if floorplan_image:
                existing_annotated = os.path.join(current_app.config['OUTPUT_FOLDER'], floorplan_image)
                if os.path.exists(existing_annotated) and os.path.isfile(existing_annotated):
                    shutil.copy(existing_annotated, annotated_path)

        # Generate quote PDF
        try:
            doc = SimpleDocTemplate(quote_path, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#556B2F'),
                spaceAfter=30,
            )

            company_info = data_config.get('company_info', {})
            story.append(Paragraph(company_info.get('name', 'Integratd Living'), title_style))
            story.append(Paragraph(f"Final Quote for: {project_name}", styles['Heading2']))
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
            story.append(Paragraph(f"Tier: {tier.capitalize()}", styles['Normal']))
            story.append(Spacer(1, 0.5*inch))

            # Add cost breakdown table
            table_data = [['Item', 'Room', 'Quantity', 'Unit Cost', 'Labor', 'Total']]
            for item in cost_items:
                table_data.append([
                    item['type'],
                    item['room'],
                    str(item['quantity']),
                    f"${item['unit_cost']:,.2f}",
                    f"${item['labor_cost']:,.2f}",
                    f"${item['total']:,.2f}"
                ])

            table_data.append(['', '', '', '', 'Subtotal:', f"${subtotal:,.2f}"])
            table_data.append(['', '', '', '', f'Markup ({markup_pct}%):', f"${markup:,.2f}"])
            table_data.append(['', '', '', '', 'TOTAL:', f"${grand_total:,.2f}"])

            t = Table(table_data, colWidths=[2*inch, 1.5*inch, 0.8*inch, 1*inch, 1*inch, 1.2*inch])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#556B2F')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            story.append(t)
            doc.build(story)
        except Exception as e:
            print(f"Error creating quote PDF: {e}")

        return jsonify({
            'success': True,
            'session_id': session_id,
            'annotated_pdf': f'/api/download/{annotated_filename}',
            'quote_pdf': f'/api/download/{quote_filename}',
            'total': grand_total
        })

    except Exception as e:
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


# ============================================================================
# SESSION ROUTES
# ============================================================================

@canvas_bp.route('/api/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get session data for workflow integration"""
    try:
        funcs = get_app_functions()
        load_session_data = funcs.get('load_session_data')
        
        if not load_session_data:
            return jsonify({'error': 'Session loader not available'}), 500
        
        session_data = load_session_data(session_id)
        if session_data:
            return jsonify(session_data)
        else:
            return jsonify({'error': 'Session not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

