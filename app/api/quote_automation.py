"""
Quote Automation Routes Blueprint

Handles AI-powered floor plan analysis and quote generation:
- /api/analyze: Analyze floor plan with AI
- /api/generate_quote: Generate quote from analysis
- /api/export_pdf: Export quote to PDF
- /api/generate-floorplan-pdf: Generate PDF from floorplan canvas
"""

import os
import io
import json
import uuid
import base64
import traceback
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import letter, A3, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from PIL import Image as PILImage
import fitz
import logging

logger = logging.getLogger(__name__)

# Create blueprint
quote_automation_bp = Blueprint('quote_automation_bp', __name__)


def get_app_functions():
    """Get functions from main app"""
    return current_app.config.get('APP_FUNCTIONS', {})


# ============================================================================
# FLOORPLAN PDF GENERATION
# ============================================================================

@quote_automation_bp.route('/api/generate-floorplan-pdf', methods=['POST'])
def generate_floorplan_pdf():
    """Generate a PDF from floorplan canvas image"""
    try:
        data = request.get_json()
        
        if not data or 'image_data' not in data:
            return jsonify({'success': False, 'error': 'No image data provided'}), 400
        
        image_data = data['image_data']
        project_name = data.get('project_name', 'Floorplan')
        components = data.get('components', [])
        
        # Remove data URL prefix if present
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decode base64 image
        image_bytes = base64.b64decode(image_data)
        
        # Save image temporarily
        temp_img_path = os.path.join(current_app.config['OUTPUT_FOLDER'], f'temp_floorplan_{uuid.uuid4()}.png')
        with open(temp_img_path, 'wb') as f:
            f.write(image_bytes)
        
        # Create PDF
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(A3), 
                               leftMargin=0.5*inch, rightMargin=0.5*inch,
                               topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = styles['Heading1']
        title_style.fontSize = 24
        title_style.spaceAfter = 20
        story.append(Paragraph(f"{project_name} - Floorplan", title_style))
        story.append(Spacer(1, 10))
        
        # Add the floorplan image - fit to page width
        pil_img = PILImage.open(temp_img_path)
        img_width, img_height = pil_img.size
        
        # Calculate dimensions to fit on page (A3 landscape is roughly 16.5 x 11.7 inches)
        max_width = 15 * inch
        max_height = 9 * inch
        
        aspect = img_width / img_height
        if img_width > img_height:
            display_width = min(max_width, img_width / 72 * inch)
            display_height = display_width / aspect
        else:
            display_height = min(max_height, img_height / 72 * inch)
            display_width = display_height * aspect
        
        # Ensure it fits
        if display_width > max_width:
            display_width = max_width
            display_height = display_width / aspect
        if display_height > max_height:
            display_height = max_height
            display_width = display_height * aspect
        
        rl_image = RLImage(temp_img_path, width=display_width, height=display_height)
        story.append(rl_image)
        
        # Add components summary if available
        if components and len(components) > 0:
            story.append(Spacer(1, 20))
            story.append(Paragraph("Components Summary", styles['Heading2']))
            
            table_data = [['Type', 'Room', 'Price']]
            total_price = 0
            for comp in components:
                comp_type = comp.get('type', 'Unknown')
                room = comp.get('room', 'N/A')
                price = comp.get('totalPrice', 0)
                total_price += price
                table_data.append([comp_type, room, f"${price:.2f}"])
            
            table_data.append(['', 'TOTAL', f"${total_price:.2f}"])
            
            table = Table(table_data, colWidths=[3*inch, 3*inch, 2*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#556B2F')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0f0f0')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(table)
        
        # Build PDF
        doc.build(story)
        
        # Clean up temp file
        try:
            os.remove(temp_img_path)
        except:
            pass
        
        # Return PDF
        pdf_buffer.seek(0)
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'floorplan_{project_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )
        
    except Exception as e:
        logger.error(f"Error generating floorplan PDF: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# FLOOR PLAN ANALYSIS
# ============================================================================

@quote_automation_bp.route('/api/analyze', methods=['POST'])
def analyze_floorplan():
    """Analyze floor plan with AI and generate quote"""
    try:
        funcs = get_app_functions()
        analyze_floorplan_with_ai = funcs.get('analyze_floorplan_with_ai')
        load_data = funcs.get('load_data')
        generate_marked_up_image = funcs.get('generate_marked_up_image')
        get_session_id = funcs.get('get_session_id')
        save_session_data = funcs.get('save_session_data')
        
        if 'floorplan' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400

        file = request.files['floorplan']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Empty filename'}), 400

        # Get form data
        project_name = request.form.get('project_name', 'Untitled Project')
        tier = request.form.get('tier', 'basic')
        automation_types = request.form.getlist('automation_types') or request.form.getlist('automation_types[]')
        
        # Check if manual mode is enabled (skip AI analysis)
        manual_mode = request.form.get('manual_mode') == 'on' or request.form.get('manual_mode') == 'true'

        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Run AI analysis only if manual mode is NOT enabled
        if manual_mode:
            print("Manual mode enabled - skipping AI analysis")
            analysis_result = {
                "rooms": [],
                "components": [],
                "notes": "Manual mode - AI analysis skipped. Add symbols manually using the editor.",
                "manual_mode": True
            }
        else:
            # Run AI analysis
            if analyze_floorplan_with_ai:
                analysis_result = analyze_floorplan_with_ai(filepath)
            else:
                analysis_result = {"rooms": [], "components": [], "notes": "AI analysis not available"}

        # Log AI analysis result for debugging
        if 'error' in analysis_result:
            print(f"AI Analysis Error: {analysis_result.get('error')}")

        if 'error' in analysis_result and analysis_result.get('fallback'):
            print("Using fallback estimation mode")
            analysis_result = {
                "rooms": [
                    {
                        "name": "Estimated Room",
                        "lighting": {"count": 5, "type": tier},
                        "shading": {"count": 2, "type": tier},
                        "security_access": {"count": 1, "type": tier},
                        "climate": {"count": 1, "type": tier},
                        "audio": {"count": 0, "type": tier}
                    }
                ],
                "notes": "Fallback estimation - AI analysis unavailable"
            }
        else:
            print(f"AI Analysis successful: {len(analysis_result.get('rooms', []))} rooms detected")

        # Calculate costs
        data_config = load_data() if load_data else {'automation_types': {}, 'labor_rate': 75, 'markup_percentage': 20}
        rooms = analysis_result.get('rooms', [])

        total_rooms = len(rooms)
        total_automation_points = 0
        cost_items = []

        for room in rooms:
            for automation_key in ['lighting', 'shading', 'security_access', 'climate', 'audio']:
                automation_data = room.get(automation_key, {})
                count = automation_data.get('count', 0)
                room_tier = automation_data.get('type', tier)

                if count > 0 and automation_key in automation_types:
                    total_automation_points += count
                    automation_config = data_config.get('automation_types', {}).get(automation_key, {})
                    unit_cost = automation_config.get('base_cost_per_unit', {}).get(room_tier, 0)
                    labor_hours = automation_config.get('labor_hours', {}).get(room_tier, 0)
                    labor_cost = labor_hours * data_config.get('labor_rate', 75)
                    total_cost = (unit_cost + labor_cost) * count

                    cost_items.append({
                        'type': automation_config.get('name', automation_key),
                        'quantity': count,
                        'unit_cost': unit_cost,
                        'labor_cost': labor_cost,
                        'total': total_cost
                    })

        subtotal = sum(item['total'] for item in cost_items)
        markup_pct = data_config.get('markup_percentage', 20)
        markup = subtotal * (markup_pct / 100)
        grand_total = subtotal + markup

        # Generate output filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        annotated_filename = f"annotated_{timestamp}.png"
        quote_filename = f"quote_{timestamp}.pdf"
        annotated_path = os.path.join(current_app.config['OUTPUT_FOLDER'], annotated_filename)
        quote_path = os.path.join(current_app.config['OUTPUT_FOLDER'], quote_filename)

        # Generate annotated floor plan with symbol markings
        try:
            components = analysis_result.get('components', [])

            if components and generate_marked_up_image:
                mapping_data = {
                    'components': components,
                    'analysis': {
                        'scale': analysis_result.get('scale', 'not detected'),
                        'total_rooms': total_rooms,
                        'notes': analysis_result.get('notes', '')
                    }
                }

                success = generate_marked_up_image(filepath, mapping_data, annotated_path)

                if success:
                    print(f"Generated annotated floor plan with {len(components)} symbols marked")
                else:
                    _create_fallback_image(filepath, annotated_path)
            else:
                _create_fallback_image(filepath, annotated_path)

        except Exception as e:
            print(f"Error creating annotated floor plan: {e}")
            traceback.print_exc()

        # Generate quote PDF
        _generate_quote_pdf(quote_path, project_name, cost_items, subtotal, markup, grand_total, markup_pct, data_config)

        # Save session data for takeoffs editor
        session_id = get_session_id() if get_session_id else f"session_{timestamp}"
        session_data = {
            'session_id': session_id,
            'project_name': project_name,
            'tier': tier,
            'automation_types': automation_types,
            'analysis_result': analysis_result,
            'floorplan_image': annotated_filename,
            'original_pdf': filename,
            'total_rooms': total_rooms,
            'total_automation_points': total_automation_points,
            'costs': {
                'items': cost_items,
                'subtotal': subtotal,
                'markup': markup,
                'grand_total': grand_total
            },
            'timestamp': datetime.now().isoformat()
        }
        if save_session_data:
            save_session_data(session_id, session_data)

        response = {
            'success': True,
            'session_id': session_id,
            'project_name': project_name,
            'total_rooms': total_rooms,
            'total_automation_points': total_automation_points,
            'confidence': '85%',
            'total_cost': f'${grand_total:,.2f}',
            'annotated_pdf': annotated_filename,
            'quote_pdf': quote_filename,
            'analysis': analysis_result,
            'costs': {
                'items': cost_items,
                'subtotal': subtotal,
                'markup': markup,
                'grand_total': grand_total
            },
            'files': {
                'annotated_pdf': f'/api/download/{annotated_filename}',
                'quote_pdf': f'/api/download/{quote_filename}'
            },
            'takeoffs_url': f'/takeoffs/{session_id}'
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}), 500


@quote_automation_bp.route('/api/generate_quote', methods=['POST'])
def generate_quote():
    """Generate quote from analysis data"""
    try:
        funcs = get_app_functions()
        load_data = funcs.get('load_data')
        
        data = request.json
        analysis = data.get('analysis', {})
        data_config = load_data() if load_data else {'automation_types': {}, 'labor_rate': 75, 'markup_percentage': 20, 'company_info': {}}
        
        line_items = []
        rooms = analysis.get('rooms', [])
        
        for room in rooms:
            room_name = room.get('name', 'Unknown Room')
            
            for automation_key in ['lighting', 'shading', 'security_access', 'climate', 'audio']:
                automation_data = room.get(automation_key, {})
                count = automation_data.get('count', 0)
                tier = automation_data.get('type', 'basic')
                
                if count > 0:
                    automation_config = data_config.get('automation_types', {}).get(automation_key, {})
                    unit_cost = automation_config.get('base_cost_per_unit', {}).get(tier, 0)
                    labor_hours = automation_config.get('labor_hours', {}).get(tier, 0)
                    labor_cost = labor_hours * data_config.get('labor_rate', 75)
                    total_cost = (unit_cost + labor_cost) * count
                    
                    line_items.append({
                        'room': room_name,
                        'category': automation_config.get('name', automation_key),
                        'quantity': count,
                        'tier': tier,
                        'unit_cost': unit_cost,
                        'labor_hours': labor_hours,
                        'labor_cost': labor_cost,
                        'total': total_cost
                    })
        
        subtotal = sum(item['total'] for item in line_items)
        markup_pct = data_config.get('markup_percentage', 20)
        markup = subtotal * (markup_pct / 100)
        total = subtotal + markup
        
        quote_data = {
            'line_items': line_items,
            'subtotal': subtotal,
            'markup': markup,
            'markup_percentage': markup_pct,
            'total': total,
            'company_info': data_config.get('company_info', {}),
            'generated_at': datetime.now().isoformat()
        }
        
        return jsonify({'success': True, 'quote': quote_data})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@quote_automation_bp.route('/api/export_pdf', methods=['POST'])
def export_pdf():
    """Export quote to PDF"""
    try:
        data = request.json
        quote = data.get('quote', {})
        
        output_filename = f"quote_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        output_path = os.path.join(current_app.config['OUTPUT_FOLDER'], output_filename)
        
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#556B2F'),
            spaceAfter=30,
        )
        
        company_info = quote.get('company_info', {})
        story.append(Paragraph(company_info.get('name', 'Company Name'), title_style))
        story.append(Paragraph(f"Phone: {company_info.get('phone', 'N/A')}", styles['Normal']))
        story.append(Paragraph(f"Email: {company_info.get('email', 'N/A')}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        story.append(Paragraph(f"Quote Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 0.5*inch))
        
        table_data = [['Room', 'Category', 'Qty', 'Tier', 'Unit Cost', 'Labor', 'Total']]
        
        for item in quote.get('line_items', []):
            table_data.append([
                item['room'],
                item['category'],
                str(item['quantity']),
                item['tier'].capitalize(),
                f"${item['unit_cost']:.2f}",
                f"${item['labor_cost']:.2f}",
                f"${item['total']:.2f}"
            ])
        
        table = Table(table_data, colWidths=[1.2*inch, 1.5*inch, 0.6*inch, 0.8*inch, 0.9*inch, 0.9*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#556B2F')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.5*inch))
        
        summary_data = [
            ['Subtotal:', f"${quote['subtotal']:.2f}"],
            [f"Markup ({quote['markup_percentage']}%):", f"${quote['markup']:.2f}"],
            ['Total:', f"${quote['total']:.2f}"]
        ]
        
        summary_table = Table(summary_data, colWidths=[5*inch, 1.5*inch])
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 14),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
            ('LINEBELOW', (0, -1), (-1, -1), 2, colors.black),
        ]))
        
        story.append(summary_table)
        doc.build(story)
        
        return send_file(output_path, as_attachment=True, download_name=output_filename)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _create_fallback_image(filepath, output_path):
    """Create a fallback image when AI marking fails"""
    try:
        if filepath.endswith('.pdf'):
            doc = fitz.open(filepath)
            page = doc[0]
            mat = fitz.Matrix(300/72, 300/72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            pix.save(output_path)
            doc.close()
        else:
            img = PILImage.open(filepath)
            img.save(output_path, 'PNG')
    except Exception as e:
        print(f"Error creating fallback image: {e}")


def _generate_quote_pdf(quote_path, project_name, cost_items, subtotal, markup, grand_total, markup_pct, data_config):
    """Generate quote PDF"""
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
        story.append(Paragraph(f"Quote for: {project_name}", styles['Heading2']))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 0.5*inch))

        # Add cost breakdown table
        table_data = [['Item', 'Quantity', 'Unit Cost', 'Labor', 'Total']]
        for item in cost_items:
            table_data.append([
                item['type'],
                str(item['quantity']),
                f"${item['unit_cost']:,.2f}",
                f"${item['labor_cost']:,.2f}",
                f"${item['total']:,.2f}"
            ])

        table_data.append(['', '', '', 'Subtotal:', f"${subtotal:,.2f}"])
        table_data.append(['', '', '', f'Markup ({markup_pct}%):', f"${markup:,.2f}"])
        table_data.append(['', '', '', 'TOTAL:', f"${grand_total:,.2f}"])

        t = Table(table_data, colWidths=[3*inch, 1*inch, 1*inch, 1*inch, 1.5*inch])
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


# ============================================================================
# FINAL QUOTE GENERATION
# ============================================================================

@quote_automation_bp.route('/api/generate-final-quote', methods=['POST'])
def generate_final_quote():
    """Generate final PDF quote from canvas symbols"""
    try:
        funcs = get_app_functions()
        load_data = funcs.get('load_data')
        
        data = request.json
        project_id = data.get('project_id')
        project_name = data.get('project_name', 'Project')
        symbols = data.get('symbols', [])
        tier = data.get('tier', 'premium')

        # Count symbols by type
        counts = {}
        for sym in symbols:
            sym_type = sym.get('type')
            counts[sym_type] = counts.get(sym_type, 0) + 1

        # Load pricing
        data_config = load_data() if load_data else {}

        # Generate quote
        line_items = []
        automation_types = data_config.get('automation_types', {})
        labor_rate = data_config.get('labor_rate', 85)
        
        for automation_type, count in counts.items():
            if count > 0:
                automation_config = automation_types.get(automation_type, {})
                unit_cost = automation_config.get('base_cost_per_unit', {}).get(tier, 0)
                labor_hours = automation_config.get('labor_hours', {}).get(tier, 0)
                labor_cost = labor_hours * labor_rate
                total_cost = (unit_cost + labor_cost) * count

                line_items.append({
                    'category': automation_config.get('name', automation_type),
                    'quantity': count,
                    'tier': tier,
                    'unit_cost': unit_cost,
                    'labor_hours': labor_hours,
                    'labor_cost': labor_cost,
                    'total': total_cost
                })

        subtotal = sum(item['total'] for item in line_items)
        markup_pct = data_config.get('markup_percentage', 20)
        markup = subtotal * (markup_pct / 100)
        total = subtotal + markup

        # Generate PDF
        output_filename = f"quote_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        output_path = os.path.join(current_app.config['OUTPUT_FOLDER'], output_filename)

        doc = SimpleDocTemplate(output_path, pagesize=letter)
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
        story.append(Paragraph(company_info.get('name', 'Company Name'), title_style))
        story.append(Paragraph(f"Project: {project_name}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))

        story.append(Paragraph(f"Quote Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 0.5*inch))

        table_data = [['Category', 'Qty', 'Tier', 'Unit Cost', 'Labor', 'Total']]

        for item in line_items:
            table_data.append([
                item['category'],
                str(item['quantity']),
                item['tier'].capitalize(),
                f"${item['unit_cost']:.2f}",
                f"${item['labor_cost']:.2f}",
                f"${item['total']:.2f}"
            ])

        table = Table(table_data, colWidths=[2*inch, 0.8*inch, 0.8*inch, 1*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#556B2F')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(table)
        story.append(Spacer(1, 0.5*inch))

        story.append(Paragraph(f"Subtotal: ${subtotal:.2f}", styles['Normal']))
        story.append(Paragraph(f"Markup ({markup_pct}%): ${markup:.2f}", styles['Normal']))
        story.append(Paragraph(f"<b>Total: ${total:.2f}</b>", styles['Heading2']))

        doc.build(story)

        return jsonify({'success': True, 'filename': output_filename})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# ANNOTATED FLOORPLAN
# ============================================================================

@quote_automation_bp.route('/api/generate-annotated-floorplan', methods=['POST'])
def generate_annotated_floorplan():
    """Generate annotated floorplan PDF with symbols marked"""
    try:
        from PIL import ImageDraw, ImageFont
        
        data = request.json
        project_id = data.get('project_id')
        symbols = data.get('symbols', [])

        # Get the original floor plan
        project_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], project_id)
        
        if not os.path.exists(project_dir):
            return jsonify({'success': False, 'error': 'Project directory not found'}), 404
            
        files = os.listdir(project_dir)
        floor_plan_file = next((f for f in files if f.startswith('floor_plan')), None)

        if not floor_plan_file:
            return jsonify({'success': False, 'error': 'Floor plan not found'}), 404

        floor_plan_path = os.path.join(project_dir, floor_plan_file)

        # Generate marked-up image
        output_filename = f"annotated_floorplan_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        output_path = os.path.join(current_app.config['OUTPUT_FOLDER'], output_filename)

        # Open floor plan image
        if floor_plan_path.endswith('.pdf'):
            doc = fitz.open(floor_plan_path)
            page = doc[0]
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            img = PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()
        else:
            img = PILImage.open(floor_plan_path)

        # Draw symbols on image
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        except:
            font = ImageFont.load_default()

        # Draw each symbol
        for sym in symbols:
            x = sym.get('x', 0)
            y = sym.get('y', 0)
            symbol = sym.get('symbol', '❓')

            # Draw circle background
            draw.ellipse([x-20, y-20, x+20, y+20], fill='#2ecc71', outline='#27ae60', width=3)

            # Draw symbol
            draw.text((x-10, y-15), symbol, fill='black', font=font)

        # Save as PDF
        img_rgb = img.convert('RGB')
        img_rgb.save(output_path, 'PDF', resolution=100.0)

        return jsonify({'success': True, 'filename': output_filename})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}), 500
