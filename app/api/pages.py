"""
Page Routes Blueprint

Handles all template rendering routes for the main application pages.
These are the navigation endpoints that serve HTML pages.
"""

from flask import Blueprint, render_template, redirect, url_for, request, make_response

# Create blueprint
pages_bp = Blueprint('pages', __name__)


def get_auth():
    """Get auth module - imported lazily to avoid circular imports"""
    import auth
    return auth


def get_app_functions():
    """Get functions from main app - imported lazily to avoid circular imports"""
    # These will be set by the main app when registering the blueprint
    from flask import current_app
    return current_app.config.get('APP_FUNCTIONS', {})


# ============================================================================
# MAIN PAGE ROUTES
# ============================================================================

@pages_bp.route('/')
def index():
    """Redirect to CRM as the main landing page after login"""
    auth = get_auth()
    if not auth.is_authenticated():
        return redirect(url_for('auth_bp.login_page'))
    return redirect(url_for('pages.crm_page'))


@pages_bp.route('/apps')
def apps_page():
    """Render apps/modules page"""
    auth = get_auth()
    if not auth.is_authenticated():
        return redirect(url_for('auth_bp.login_page'))
    
    funcs = get_app_functions()
    load_page_config = funcs.get('load_page_config')
    
    config = load_page_config() if load_page_config else {}
    user = auth.get_current_user()
    user_permissions = user.get('permissions', ['admin']) if user else ['admin']
    return render_template('template_unified.html', config=config, user_permissions=user_permissions)


@pages_bp.route('/crm')
def crm_page():
    """Render CRM dashboard"""
    return render_template('crm.html')


@pages_bp.route('/quotes')
def quotes_page():
    """Render quote automation page"""
    return render_template('index.html')


@pages_bp.route('/canvas')
def canvas_page():
    """Unified editor - same as takeoffs but standalone"""
    funcs = get_app_functions()
    load_data = funcs.get('load_data')
    
    automation_data = load_data() if load_data else {}
    response = make_response(render_template('unified_editor.html',
                         automation_data=automation_data,
                         initial_symbols=[],
                         tier='basic',
                         project_name='New Project',
                         session_data={}))
    # Prevent caching to ensure users always get the latest version
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@pages_bp.route('/learning')
def learning_page():
    """Render learning/training page"""
    return render_template('learning.html')


@pages_bp.route('/simpro')
def simpro_page():
    """Render Simpro integration page"""
    return render_template('simpro.html')


@pages_bp.route('/ai-mapping')
def ai_mapping_page():
    """Render AI mapping page"""
    return render_template('template_ai_mapping.html')


@pages_bp.route('/takeoffs/<session_id>')
def takeoffs_page(session_id):
    """Unified editor with AI analysis results loaded"""
    funcs = get_app_functions()
    load_session_data = funcs.get('load_session_data')
    load_data = funcs.get('load_data')
    
    session_data = load_session_data(session_id) if load_session_data else None
    if not session_data:
        return "Session not found", 404

    # Load automation data
    automation_data = load_data() if load_data else {}

    # Prepare symbols from AI analysis
    analysis_result = session_data.get('analysis_result', {})
    components = analysis_result.get('components', [])

    symbols = []
    for comp in components:
        symbols.append({
            'id': comp.get('id', ''),
            'type': comp.get('type', 'unknown'),
            'x': comp.get('location', {}).get('x', 0.5),
            'y': comp.get('location', {}).get('y', 0.5),
            'room': comp.get('room', ''),
            'automation_category': comp.get('automation_category', comp.get('type', 'unknown')),
            'label': comp.get('id', ''),
            'items': [],
            'custom_image_data': None
        })

    return render_template('unified_editor.html',
                         session_data=session_data,
                         automation_data=automation_data,
                         initial_symbols=symbols,
                         project_name=session_data.get('project_name', 'AI Analysis - Edit & Review'),
                         tier=session_data.get('tier', 'basic'))


@pages_bp.route('/mapping')
def mapping_page():
    """Vectorworks-style mapping tool"""
    funcs = get_app_functions()
    load_session_data = funcs.get('load_session_data')
    
    session_id = request.args.get('session')
    project_name = 'New Mapping Project'

    if session_id and load_session_data:
        session_data = load_session_data(session_id)
        if session_data:
            project_name = session_data.get('project_name', 'Mapping Project')

    response = make_response(render_template('mapping.html', project_name=project_name))
    # Prevent caching to ensure users always get the latest version
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@pages_bp.route('/board-builder')
def board_builder_page():
    """Loxone Board Builder interface"""
    funcs = get_app_functions()
    load_session_data = funcs.get('load_session_data')
    
    session_id = request.args.get('session')
    project_name = 'New Loxone Board'

    if session_id and load_session_data:
        session_data = load_session_data(session_id)
        if session_data:
            project_name = session_data.get('project_name', 'Loxone Board')

    response = make_response(render_template('board_builder.html', project_name=project_name))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@pages_bp.route('/electrical-cad')
def electrical_cad_page():
    """Electrical CAD editor page"""
    return render_template('cad_designer.html')


@pages_bp.route('/pdf-editor')
def pdf_editor_page():
    """PDF Editor page"""
    return render_template('quote_pdf_editor.html')


@pages_bp.route('/kanban')
def kanban_page():
    """Kanban board page"""
    return render_template('kanban.html')

