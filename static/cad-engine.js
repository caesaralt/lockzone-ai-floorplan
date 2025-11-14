// ============================================================================
// ELECTRICAL CAD DESIGNER ENGINE
// Professional-grade CAD system for electrical drawings
// ============================================================================

console.log('⚡ Initializing Electrical CAD Designer...');

// Global state
let canvas;
let currentTool = 'select';
let currentSession = null;
let symbols = {};
let layers = [];
let isDrawing = false;
let drawingObject = null;
let startX, startY;
let undoStack = [];
let redoStack = [];
let zoomLevel = 1;

// Multi-sheet support
let sheets = [];
let currentSheetIndex = 0;

// Advanced snapping
let snapEnabled = true;
let orthoMode = false;
let polarTrackingEnabled = false;
let objectSnapEnabled = true;
const SNAP_DISTANCE = 10; // pixels
const POLAR_ANGLES = [0, 45, 90, 135, 180, 225, 270, 315]; // degrees
let snapIndicator = null;

// Rendering throttle
let lastRenderTime = 0;
const RENDER_THROTTLE = 16; // Max 60fps
let renderScheduled = false;

// Prevent duplicate event listeners
let canvasDropListenersAdded = false;

// Default layers
const DEFAULT_LAYERS = [
    { name: 'WALLS-ARCHITECTURAL', color: '#2C3E50', visible: true, locked: false },
    { name: 'POWER-WIRING-RED', color: '#E74C3C', visible: true, locked: false },
    { name: 'NEUTRAL-WIRING-BLUE', color: '#3498DB', visible: true, locked: false },
    { name: 'GROUND-WIRING-GREEN', color: '#27AE60', visible: true, locked: false },
    { name: 'DEVICES-SYMBOLS', color: '#F39C12', visible: true, locked: false },
    { name: 'TEXT-LABELS', color: '#34495E', visible: true, locked: false },
];

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
    initializeCAD();
});

// ============================================================================
// INITIALIZATION
// ============================================================================

async function initializeCAD() {
    try {
        // Check if Fabric.js is loaded
        if (typeof fabric === 'undefined') {
            throw new Error('Fabric.js library not loaded');
        }

        // Initialize Fabric.js canvas
        canvas = new fabric.Canvas('cadCanvas', {
            width: Math.min(window.innerWidth - 400, 2000), // Account for sidebars, max 2000px
            height: Math.min(window.innerHeight - 120, 1200), // Account for header, max 1200px
            backgroundColor: '#ffffff',
            selection: true
        });

        // Initialize layers
        layers = [...DEFAULT_LAYERS];
        renderLayers();

        // Load symbols library (don't fail if this errors)
        try {
            await loadSymbols();
        } catch (e) {
            console.warn('Failed to load symbols:', e);
        }

        // Setup event listeners
        setupCanvasEvents();
        setupKeyboardShortcuts();

        // Enable grid (simplified)
        try {
            enableGrid();
        } catch (e) {
            console.warn('Failed to enable grid:', e);
        }

        // Auto-save disabled - user must save manually with Ctrl+S or Save button
        console.log('💾 Auto-save disabled. Use Ctrl+S or Save button to save your work.');

        // Create new session (don't fail if this errors - user can create manually)
        try {
            await createNewSession();
        } catch (e) {
            console.warn('Failed to auto-create session:', e);
            console.log('You can create a new project manually using the "New" button');
        }

        console.log('✅ CAD Designer initialized successfully');
    } catch (error) {
        console.error('❌ Initialization error:', error);
        document.body.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; font-family: system-ui;">
                <h2 style="color: #e74c3c;">⚠️ Failed to Initialize CAD Designer</h2>
                <p>Error: ${error.message}</p>
                <button onclick="window.location.reload()" style="padding: 12px 24px; background: #556B2F; color: white; border: none; border-radius: 8px; cursor: pointer; margin-top: 20px;">Refresh Page</button>
            </div>
        `;
    }
}

// ============================================================================
// SESSION MANAGEMENT
// ============================================================================

async function createNewSession() {
    try {
        const projectNameInput = document.getElementById('projectName');
        const projectName = projectNameInput ? projectNameInput.value : 'Untitled Project';

        const response = await fetch('/api/cad/new', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_name: projectName })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.success) {
            currentSession = data.session;
            console.log('✅ Session created:', currentSession.session_id);
            updateObjectCount();
        } else {
            throw new Error(data.error || 'Unknown error');
        }
    } catch (error) {
        console.error('Error creating session:', error);
        // Don't crash - user can still use the CAD designer
        throw error; // Re-throw so initializeCAD can catch it
    }
}

async function saveProject() {
    if (!currentSession) {
        alert('No active session');
        return;
    }

    try {
        // Serialize canvas data
        const canvasData = canvas.toJSON(['layer', 'customType', 'symbolId']);

        const sessionData = {
            session_id: currentSession.session_id,
            project_name: document.getElementById('projectName').value,
            metadata: {
                scale: document.getElementById('scale').value,
                paper_size: document.getElementById('paperSize').value,
                drawing_number: document.getElementById('drawingNumber').value,
                revision: document.getElementById('revision').value,
                units: 'mm'
            },
            layers: layers,
            objects: canvasData.objects,
            canvas_state: canvasData
        };

        const response = await fetch('/api/cad/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(sessionData)
        });

        const data = await response.json();

        if (data.success) {
            alert('✅ Project saved successfully!');
            console.log('Project saved');
        } else {
            alert('❌ Failed to save: ' + data.error);
        }
    } catch (error) {
        console.error('Save error:', error);
        alert('Failed to save project');
    }
}

async function loadProject() {
    try {
        const response = await fetch('/api/cad/list');
        const data = await response.json();

        if (data.success && data.sessions.length > 0) {
            const sessionList = data.sessions.map(s =>
                `${s.project_name} (${s.modified_date})`
            ).join('\n');

            const selection = prompt(`Select project:\n\n${sessionList}\n\nEnter project name:`);

            if (selection) {
                const session = data.sessions.find(s => s.project_name === selection);
                if (session) {
                    await loadSession(session.session_id);
                }
            }
        } else {
            alert('No saved projects found');
        }
    } catch (error) {
        console.error('Load error:', error);
    }
}

async function loadSession(sessionId) {
    try {
        const response = await fetch(`/api/cad/load/${sessionId}`);
        const data = await response.json();

        if (data.success) {
            currentSession = data.session;

            // Clear canvas
            canvas.clear();

            // Load canvas state
            if (data.session.canvas_state) {
                canvas.loadFromJSON(data.session.canvas_state, () => {
                    canvas.renderAll();
                    console.log('Canvas loaded');
                });
            }

            // Load metadata
            if (data.session.metadata) {
                document.getElementById('projectName').value = data.session.project_name;
                document.getElementById('scale').value = data.session.metadata.scale || '1:100';
                document.getElementById('paperSize').value = data.session.metadata.paper_size || 'A1';
                document.getElementById('drawingNumber').value = data.session.metadata.drawing_number || 'E-001';
                document.getElementById('revision').value = data.session.metadata.revision || 'A';
            }

            // Load layers
            if (data.session.layers && data.session.layers.length > 0) {
                layers = data.session.layers;
                renderLayers();
            }

            updateObjectCount();
            alert('✅ Project loaded successfully!');
        }
    } catch (error) {
        console.error('Load session error:', error);
    }
}

// Auto-save function removed - manual save only
// User can save with:
// - Ctrl+S keyboard shortcut
// - "💾 Save" button in header
// - saveProject() function

function newProject() {
    if (confirm('Create new project? Unsaved changes will be lost.')) {
        canvas.clear();
        createNewSession();
        document.getElementById('projectName').value = 'Untitled Project';
        updateObjectCount();
    }
}

// ============================================================================
// FILE UPLOAD (PDF/IMAGES)
// ============================================================================

async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    console.log('📎 Uploading file:', file.name, file.type);

    // Check file type
    const isPDF = file.type === 'application/pdf';
    const isImage = file.type.startsWith('image/');

    if (!isPDF && !isImage) {
        alert('Please upload a PDF or image file (.pdf, .png, .jpg, .jpeg, .gif, .bmp)');
        return;
    }

    try {
        if (isImage) {
            // Handle image upload
            await loadImageToCanvas(file);
        } else if (isPDF) {
            // Handle PDF upload
            await loadPDFToCanvas(file);
        }

        // Clear the file input so the same file can be uploaded again if needed
        event.target.value = '';

        console.log('✅ File uploaded successfully');
    } catch (error) {
        console.error('❌ Error uploading file:', error);
        alert('Failed to upload file: ' + error.message);
    }
}

function loadImageToCanvas(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();

        reader.onload = (e) => {
            fabric.Image.fromURL(e.target.result, (img) => {
                // Scale image to fit canvas if it's too large
                const maxWidth = canvas.width * 0.8;
                const maxHeight = canvas.height * 0.8;

                if (img.width > maxWidth || img.height > maxHeight) {
                    const scale = Math.min(maxWidth / img.width, maxHeight / img.height);
                    img.scale(scale);
                }

                // Center the image
                img.set({
                    left: (canvas.width - img.getScaledWidth()) / 2,
                    top: (canvas.height - img.getScaledHeight()) / 2,
                    selectable: true,
                    layer: 'WALLS-ARCHITECTURAL',
                    customType: 'uploaded-image'
                });

                canvas.add(img);
                canvas.setActiveObject(img);
                canvas.renderAll();

                addToUndoStack();
                updateObjectCount();

                resolve();
            }, { crossOrigin: 'anonymous' });
        };

        reader.onerror = () => reject(new Error('Failed to read image file'));
        reader.readAsDataURL(file);
    });
}

async function loadPDFToCanvas(file) {
    // For PDF files, we'll use a simple approach: send to backend to convert to image
    // Or use PDF.js library if available

    // For now, let's create a FormData and send to backend
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/cad/upload-pdf', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.success && data.image_url) {
            // Load the converted image onto canvas
            fabric.Image.fromURL(data.image_url, (img) => {
                // Scale image to fit canvas if it's too large
                const maxWidth = canvas.width * 0.8;
                const maxHeight = canvas.height * 0.8;

                if (img.width > maxWidth || img.height > maxHeight) {
                    const scale = Math.min(maxWidth / img.width, maxHeight / img.height);
                    img.scale(scale);
                }

                // Center the image
                img.set({
                    left: (canvas.width - img.getScaledWidth()) / 2,
                    top: (canvas.height - img.getScaledHeight()) / 2,
                    selectable: true,
                    layer: 'WALLS-ARCHITECTURAL',
                    customType: 'uploaded-pdf'
                });

                canvas.add(img);
                canvas.setActiveObject(img);
                canvas.renderAll();

                addToUndoStack();
                updateObjectCount();
            });
        } else {
            throw new Error(data.error || 'Failed to convert PDF');
        }
    } catch (error) {
        console.error('PDF upload error:', error);
        alert('PDF upload failed. You can still upload image files (.png, .jpg).');
    }
}

// ============================================================================
// DRAWING TOOLS
// ============================================================================

function selectTool(tool) {
    currentTool = tool;

    // Update UI
    document.querySelectorAll('.tool-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tool="${tool}"]`).classList.add('active');

    // Configure canvas based on tool
    if (tool === 'select') {
        canvas.selection = true;
        canvas.defaultCursor = 'default';
    } else if (tool === 'pan') {
        canvas.selection = false;
        canvas.defaultCursor = 'grab';
    } else {
        canvas.selection = false;
        canvas.defaultCursor = 'crosshair';
    }

    console.log('Tool selected:', tool);
}

// Throttled render function to prevent infinite loops
function throttledRender() {
    const now = Date.now();

    // If already scheduled or rendered recently, skip
    if (renderScheduled || (now - lastRenderTime) < RENDER_THROTTLE) {
        return;
    }

    renderScheduled = true;

    requestAnimationFrame(() => {
        if (canvas) {
            canvas.renderAll();
        }
        lastRenderTime = Date.now();
        renderScheduled = false;
    });
}

function setupCanvasEvents() {
    // Mouse down
    canvas.on('mouse:down', (e) => {
        if (currentTool === 'select' || currentTool === 'pan') return;

        isDrawing = true;
        const pointer = canvas.getPointer(e.e);
        startX = pointer.x;
        startY = pointer.y;

        // Start drawing based on tool
        if (currentTool === 'line') {
            startDrawingLine(startX, startY);
        } else if (currentTool === 'rectangle') {
            startDrawingRectangle(startX, startY);
        } else if (currentTool === 'circle') {
            startDrawingCircle(startX, startY);
        } else if (currentTool === 'wire') {
            startDrawingWire(startX, startY);
        } else if (currentTool === 'dimension') {
            startDrawingDimension(startX, startY);
        } else if (currentTool === 'text') {
            addText(startX, startY);
        }
    });

    // Mouse move with throttling
    canvas.on('mouse:move', (e) => {
        // CRITICAL: Only process if actively drawing
        if (!isDrawing || !drawingObject) return;

        const pointer = canvas.getPointer(e.e);

        if (currentTool === 'line') {
            drawingObject.set({ x2: pointer.x, y2: pointer.y });
        } else if (currentTool === 'rectangle') {
            const width = pointer.x - startX;
            const height = pointer.y - startY;
            drawingObject.set({ width: Math.abs(width), height: Math.abs(height) });
            if (width < 0) drawingObject.set({ left: pointer.x });
            if (height < 0) drawingObject.set({ top: pointer.y });
        } else if (currentTool === 'circle') {
            const radius = Math.sqrt(Math.pow(pointer.x - startX, 2) + Math.pow(pointer.y - startY, 2));
            drawingObject.set({ radius: radius });
        } else if (currentTool === 'dimension') {
            updateDimension(drawingObject, startX, startY, pointer.x, pointer.y);
        }

        // Use throttled render instead of direct renderAll()
        throttledRender();
    });

    // Mouse up - CRITICAL: Always reset isDrawing
    canvas.on('mouse:up', () => {
        if (isDrawing && drawingObject) {
            addToUndoStack();
            updateObjectCount();
        }
        // CRITICAL: Always reset these, even if no object
        isDrawing = false;
        drawingObject = null;
    });

    // Mouse leave canvas - CRITICAL: Reset drawing state
    canvas.on('mouse:out', () => {
        if (isDrawing) {
            console.log('Mouse left canvas, resetting drawing state');
            isDrawing = false;
            drawingObject = null;
        }
    });

    // Object selected
    canvas.on('selection:created', updatePropertiesPanel);
    canvas.on('selection:updated', updatePropertiesPanel);
    canvas.on('selection:cleared', () => {
        // Reset properties panel
    });
}

function startDrawingLine(x, y) {
    const currentLayer = getCurrentLayer();
    drawingObject = new fabric.Line([x, y, x, y], {
        stroke: currentLayer.color,
        strokeWidth: 2,
        selectable: true,
        layer: currentLayer.name,
        customType: 'line'
    });
    canvas.add(drawingObject);
}

function startDrawingRectangle(x, y) {
    const currentLayer = getCurrentLayer();
    drawingObject = new fabric.Rect({
        left: x,
        top: y,
        width: 0,
        height: 0,
        fill: 'transparent',
        stroke: currentLayer.color,
        strokeWidth: 2,
        layer: currentLayer.name,
        customType: 'rectangle'
    });
    canvas.add(drawingObject);
}

function startDrawingCircle(x, y) {
    const currentLayer = getCurrentLayer();
    drawingObject = new fabric.Circle({
        left: x,
        top: y,
        radius: 0,
        fill: 'transparent',
        stroke: currentLayer.color,
        strokeWidth: 2,
        layer: currentLayer.name,
        customType: 'circle'
    });
    canvas.add(drawingObject);
}

function startDrawingWire(x, y) {
    const wireColor = '#E74C3C'; // Red for power wire
    drawingObject = new fabric.Line([x, y, x, y], {
        stroke: wireColor,
        strokeWidth: 3,
        selectable: true,
        layer: 'POWER-WIRING-RED',
        customType: 'wire'
    });
    canvas.add(drawingObject);
}

function addText(x, y) {
    const text = prompt('Enter text:');
    if (text) {
        const currentLayer = getCurrentLayer();
        const textObject = new fabric.IText(text, {
            left: x,
            top: y,
            fontSize: 16,
            fill: currentLayer.color,
            layer: currentLayer.name,
            customType: 'text'
        });
        canvas.add(textObject);
        canvas.setActiveObject(textObject);
        addToUndoStack();
        updateObjectCount();
    }
    isDrawing = false;
}

// ============================================================================
// DIMENSION TOOLS
// ============================================================================

function startDrawingDimension(x, y) {
    const currentLayer = getCurrentLayer();

    // Create dimension as a group with line, arrows, and text
    const dimensionLine = new fabric.Line([x, y, x, y], {
        stroke: currentLayer.color || '#2C3E50',
        strokeWidth: 1,
        selectable: false
    });

    const dimensionText = new fabric.Text('0.00m', {
        fontSize: 12,
        left: x,
        top: y - 15,
        fill: currentLayer.color || '#2C3E50',
        selectable: false,
        backgroundColor: 'white',
        padding: 2
    });

    // Create arrow heads
    const arrow1 = createArrowHead(x, y, 0, currentLayer.color);
    const arrow2 = createArrowHead(x, y, 180, currentLayer.color);

    // Group all dimension elements
    const group = new fabric.Group([dimensionLine, arrow1, arrow2, dimensionText], {
        layer: currentLayer.name,
        customType: 'dimension',
        selectable: true,
        dimensionStart: { x, y },
        dimensionEnd: { x, y }
    });

    drawingObject = group;
    canvas.add(group);
}

function updateDimension(dimensionGroup, x1, y1, x2, y2) {
    if (!dimensionGroup || !dimensionGroup._objects) return;

    // Calculate distance and angle
    const dx = x2 - x1;
    const dy = y2 - y1;
    const distance = Math.sqrt(dx * dx + dy * dy);
    const angle = Math.atan2(dy, dx) * 180 / Math.PI;

    // Convert pixels to meters (assuming 1 meter = 100 pixels for display)
    const distanceMeters = (distance / 100).toFixed(2);

    // Update dimension line
    const line = dimensionGroup._objects[0];
    line.set({
        x1: 0,
        y1: 0,
        x2: dx,
        y2: dy
    });

    // Update arrows
    const arrow1 = dimensionGroup._objects[1];
    const arrow2 = dimensionGroup._objects[2];

    arrow1.set({
        left: 0,
        top: 0,
        angle: angle
    });

    arrow2.set({
        left: dx,
        top: dy,
        angle: angle + 180
    });

    // Update text
    const text = dimensionGroup._objects[3];
    const midX = dx / 2;
    const midY = dy / 2;

    // Offset text perpendicular to dimension line
    const textAngle = angle * Math.PI / 180;
    const offsetX = -Math.sin(textAngle) * 15;
    const offsetY = Math.cos(textAngle) * 15;

    text.set({
        left: midX + offsetX,
        top: midY + offsetY,
        text: `${distanceMeters}m`,
        angle: (Math.abs(angle) > 90 && Math.abs(angle) < 270) ? angle + 180 : angle
    });

    dimensionGroup.set({
        left: x1,
        top: y1,
        dimensionEnd: { x: x2, y: y2 }
    });

    dimensionGroup.setCoords();
}

function createArrowHead(x, y, angle, color) {
    // Create triangle arrow head
    const arrowSize = 8;
    const arrow = new fabric.Triangle({
        left: x,
        top: y,
        width: arrowSize,
        height: arrowSize,
        fill: color || '#2C3E50',
        angle: angle,
        originX: 'center',
        originY: 'center',
        selectable: false
    });
    return arrow;
}

// Add angular dimension between two lines
function addAngularDimension(line1, line2) {
    // Calculate angle between two lines
    const angle1 = Math.atan2(line1.y2 - line1.y1, line1.x2 - line1.x1);
    const angle2 = Math.atan2(line2.y2 - line2.y1, line2.x2 - line2.x1);
    let angleDiff = (angle2 - angle1) * 180 / Math.PI;

    // Normalize angle to 0-360
    if (angleDiff < 0) angleDiff += 360;
    if (angleDiff > 180) angleDiff = 360 - angleDiff;

    // Create arc to show angle
    const radius = 30;
    const startAngle = angle1;
    const endAngle = angle2;

    const arc = new fabric.Circle({
        left: line1.x1,
        top: line1.y1,
        radius: radius,
        startAngle: startAngle,
        endAngle: endAngle,
        stroke: '#2C3E50',
        strokeWidth: 1,
        fill: 'transparent',
        selectable: true
    });

    const angleText = new fabric.Text(`${angleDiff.toFixed(1)}°`, {
        left: line1.x1 + radius + 10,
        top: line1.y1 - 10,
        fontSize: 12,
        fill: '#2C3E50'
    });

    const group = new fabric.Group([arc, angleText], {
        selectable: true,
        customType: 'angular-dimension'
    });

    canvas.add(group);
    addToUndoStack();
    updateObjectCount();
}

// Add radius dimension for circles
function addRadiusDimension(circle) {
    const radius = circle.radius;
    const centerX = circle.left + radius;
    const centerY = circle.top + radius;

    // Create radius line
    const radiusLine = new fabric.Line([centerX, centerY, centerX + radius, centerY], {
        stroke: '#2C3E50',
        strokeWidth: 1,
        selectable: false
    });

    const radiusText = new fabric.Text(`R ${(radius / 100).toFixed(2)}m`, {
        left: centerX + radius / 2,
        top: centerY - 15,
        fontSize: 12,
        fill: '#2C3E50',
        backgroundColor: 'white',
        padding: 2
    });

    const group = new fabric.Group([radiusLine, radiusText], {
        selectable: true,
        customType: 'radius-dimension'
    });

    canvas.add(group);
    addToUndoStack();
    updateObjectCount();
}

// ============================================================================
// TITLE BLOCK & TEMPLATES (AS/NZS Standards)
// ============================================================================

function addTitleBlock(position = 'bottom-right') {
    const canvasWidth = canvas.width;
    const canvasHeight = canvas.height;

    // Title block dimensions (AS/NZS standard for A1 sheet)
    const tbWidth = 400;
    const tbHeight = 150;

    // Position calculation
    let left, top;
    if (position === 'bottom-right') {
        left = canvasWidth - tbWidth - 20;
        top = canvasHeight - tbHeight - 20;
    } else {
        left = 20;
        top = canvasHeight - tbHeight - 20;
    }

    // Main border
    const border = new fabric.Rect({
        left: 0,
        top: 0,
        width: tbWidth,
        height: tbHeight,
        fill: 'white',
        stroke: '#000000',
        strokeWidth: 2,
        selectable: false
    });

    // Horizontal dividers
    const div1 = new fabric.Line([0, 30, tbWidth, 30], {
        stroke: '#000000',
        strokeWidth: 1,
        selectable: false
    });

    const div2 = new fabric.Line([0, 70, tbWidth, 70], {
        stroke: '#000000',
        strokeWidth: 1,
        selectable: false
    });

    const div3 = new fabric.Line([0, 110, tbWidth, 110], {
        stroke: '#000000',
        strokeWidth: 1,
        selectable: false
    });

    // Vertical dividers
    const divV1 = new fabric.Line([200, 30, 200, tbHeight], {
        stroke: '#000000',
        strokeWidth: 1,
        selectable: false
    });

    const divV2 = new fabric.Line([300, 30, 300, tbHeight], {
        stroke: '#000000',
        strokeWidth: 1,
        selectable: false
    });

    // Company/Project header
    const companyText = new fabric.Text('INTEGRATED LIVING', {
        left: 10,
        top: 8,
        fontSize: 14,
        fontWeight: 'bold',
        fill: '#000000',
        selectable: false
    });

    // Drawing title
    const titleLabel = new fabric.Text('DRAWING TITLE:', {
        left: 10,
        top: 38,
        fontSize: 10,
        fill: '#666666',
        selectable: false
    });

    const titleText = new fabric.IText(currentSession?.project_name || 'Electrical Layout', {
        left: 10,
        top: 52,
        fontSize: 16,
        fontWeight: 'bold',
        fill: '#000000',
        selectable: true
    });

    // Drawing number
    const dwgNumLabel = new fabric.Text('DWG NO:', {
        left: 210,
        top: 38,
        fontSize: 10,
        fill: '#666666',
        selectable: false
    });

    const dwgNumText = new fabric.IText(currentSession?.metadata?.drawing_number || 'E-001', {
        left: 210,
        top: 52,
        fontSize: 14,
        fontWeight: 'bold',
        fill: '#000000',
        selectable: true
    });

    // Scale
    const scaleLabel = new fabric.Text('SCALE:', {
        left: 310,
        top: 38,
        fontSize: 10,
        fill: '#666666',
        selectable: false
    });

    const scaleText = new fabric.IText(currentSession?.metadata?.scale || '1:100', {
        left: 310,
        top: 52,
        fontSize: 14,
        fill: '#000000',
        selectable: true
    });

    // Date
    const dateLabel = new fabric.Text('DATE:', {
        left: 210,
        top: 78,
        fontSize: 10,
        fill: '#666666',
        selectable: false
    });

    const dateText = new fabric.Text(new Date().toLocaleDateString(), {
        left: 210,
        top: 92,
        fontSize: 12,
        fill: '#000000',
        selectable: false
    });

    // Revision
    const revLabel = new fabric.Text('REV:', {
        left: 310,
        top: 78,
        fontSize: 10,
        fill: '#666666',
        selectable: false
    });

    const revText = new fabric.IText(currentSession?.metadata?.revision || 'A', {
        left: 310,
        top: 92,
        fontSize: 14,
        fontWeight: 'bold',
        fill: '#000000',
        selectable: true
    });

    // Designer/Engineer
    const designerLabel = new fabric.Text('DESIGNED:', {
        left: 10,
        top: 78,
        fontSize: 10,
        fill: '#666666',
        selectable: false
    });

    const designerText = new fabric.IText('Engineer Name', {
        left: 10,
        top: 92,
        fontSize: 12,
        fill: '#000000',
        selectable: true
    });

    // Standards compliance notice
    const standardsText = new fabric.Text('Designed in accordance with AS/NZS 3000:2018', {
        left: 10,
        top: 118,
        fontSize: 9,
        fill: '#666666',
        selectable: false
    });

    // Sheet number
    const sheetLabel = new fabric.Text('SHEET:', {
        left: 310,
        top: 118,
        fontSize: 10,
        fill: '#666666',
        selectable: false
    });

    const sheetText = new fabric.IText('1 of 1', {
        left: 350,
        top: 118,
        fontSize: 10,
        fill: '#000000',
        selectable: true
    });

    // Create group
    const titleBlock = new fabric.Group([
        border, div1, div2, div3, divV1, divV2,
        companyText, titleLabel, titleText,
        dwgNumLabel, dwgNumText, scaleLabel, scaleText,
        dateLabel, dateText, revLabel, revText,
        designerLabel, designerText, standardsText,
        sheetLabel, sheetText
    ], {
        left: left,
        top: top,
        selectable: true,
        customType: 'titleBlock',
        lockRotation: true,
        hasControls: false
    });

    canvas.add(titleBlock);
    canvas.sendToBack(titleBlock); // Keep title block behind other objects
    addToUndoStack();
    updateObjectCount();

    console.log('✅ Professional title block added');
    return titleBlock;
}

// Add border/frame for professional drawings
function addDrawingFrame(paperSize = 'A1') {
    // Paper sizes in mm (at 1:1 scale)
    const paperSizes = {
        'A0': { width: 841, height: 1189 },
        'A1': { width: 594, height: 841 },
        'A2': { width: 420, height: 594 },
        'A3': { width: 297, height: 420 },
        'A4': { width: 210, height: 297 }
    };

    const size = paperSizes[paperSize] || paperSizes['A1'];

    // Convert mm to pixels (assuming 96 DPI, 1mm = 3.78 pixels)
    const scale = 3.78;
    const width = size.width * scale;
    const height = size.height * scale;

    // Outer border (page edge)
    const outerBorder = new fabric.Rect({
        left: 20,
        top: 20,
        width: width,
        height: height,
        fill: 'transparent',
        stroke: '#000000',
        strokeWidth: 3,
        selectable: false,
        customType: 'frame-outer'
    });

    // Inner border (drawing area - 10mm inside)
    const margin = 10 * scale;
    const innerBorder = new fabric.Rect({
        left: 20 + margin,
        top: 20 + margin,
        width: width - (margin * 2),
        height: height - (margin * 2),
        fill: 'transparent',
        stroke: '#000000',
        strokeWidth: 1,
        selectable: false,
        customType: 'frame-inner'
    });

    canvas.add(outerBorder);
    canvas.add(innerBorder);
    canvas.sendToBack(innerBorder);
    canvas.sendToBack(outerBorder);

    console.log(`✅ ${paperSize} drawing frame added`);
}

// ============================================================================
// SYMBOLS LIBRARY
// ============================================================================

async function loadSymbols() {
    try {
        const response = await fetch('/api/cad/symbols');
        const data = await response.json();

        if (data.success) {
            symbols = data.symbols;
            renderSymbols();
            console.log('✅ Symbols loaded');
        }
    } catch (error) {
        console.error('Error loading symbols:', error);
    }
}

function renderSymbols() {
    const symbolsPanel = document.getElementById('symbolsPanel');
    symbolsPanel.innerHTML = '';

    Object.keys(symbols).forEach(category => {
        const categoryDiv = document.createElement('div');
        categoryDiv.className = 'symbol-category';

        const title = document.createElement('div');
        title.className = 'category-title';
        title.textContent = category.toUpperCase();
        categoryDiv.appendChild(title);

        const grid = document.createElement('div');
        grid.className = 'symbol-grid';

        symbols[category].forEach(symbol => {
            const item = document.createElement('div');
            item.className = 'symbol-item';
            item.draggable = true;
            item.dataset.symbolId = symbol.id;
            item.dataset.symbolData = JSON.stringify(symbol);

            // Render SVG symbol if available, otherwise fallback to icon
            const symbolDisplay = symbol.svg
                ? `<div class="symbol-icon-svg" style="width: ${symbol.width * 2}px; height: ${symbol.height * 2}px;">${symbol.svg.replace(/stroke="black"/g, 'stroke="currentColor"').replace(/fill="black"/g, 'fill="currentColor"')}</div>`
                : `<div class="symbol-icon">${symbol.icon || '⚡'}</div>`;

            item.innerHTML = `
                ${symbolDisplay}
                <div class="symbol-name">${symbol.name}</div>
            `;

            // Drag and drop
            item.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('symbol', JSON.stringify(symbol));
            });

            item.addEventListener('click', () => {
                addSymbolToCanvas(symbol);
            });

            grid.appendChild(item);
        });

        categoryDiv.appendChild(grid);
        symbolsPanel.appendChild(categoryDiv);
    });

    // CRITICAL: Only add drop listeners ONCE to prevent event listener accumulation
    if (!canvasDropListenersAdded) {
        const canvasEl = document.getElementById('cadCanvas');
        canvasEl.addEventListener('dragover', (e) => e.preventDefault());
        canvasEl.addEventListener('drop', (e) => {
            e.preventDefault();
            const symbolData = e.dataTransfer.getData('symbol');
            if (symbolData) {
                const symbol = JSON.parse(symbolData);
                const rect = canvasEl.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                addSymbolToCanvas(symbol, x, y);
            }
        });
        canvasDropListenersAdded = true;
        console.log('✅ Canvas drop listeners added (one-time)');
    }
}

function addSymbolToCanvas(symbol, x = 100, y = 100) {
    // If symbol has SVG, load and render it professionally
    if (symbol.svg) {
        // Wrap SVG in proper container with viewBox
        const svgString = `<svg width="${symbol.width}" height="${symbol.height}" viewBox="0 0 ${symbol.width} ${symbol.height}" xmlns="http://www.w3.org/2000/svg">${symbol.svg}</svg>`;

        fabric.loadSVGFromString(svgString, (objects, options) => {
            const svgGroup = fabric.util.groupSVGElements(objects, options);

            // Add label below symbol
            const label = new fabric.Text(symbol.name, {
                fontSize: 10,
                originX: 'center',
                originY: 'top',
                top: symbol.height / 2 + 10,
                fill: '#2C3E50'
            });

            // Create group with symbol and label
            const group = new fabric.Group([svgGroup, label], {
                left: x,
                top: y,
                layer: 'DEVICES-SYMBOLS',
                customType: 'symbol',
                symbolId: symbol.id,
                symbolData: symbol
            });

            canvas.add(group);
            canvas.setActiveObject(group);
            addToUndoStack();
            updateObjectCount();

            console.log('✅ Professional symbol added:', symbol.name);
        });
    } else {
        // Fallback for old emoji-based symbols
        const text = new fabric.Text(symbol.icon || '⚡', {
            fontSize: 40,
            originX: 'center',
            originY: 'center'
        });

        const rect = new fabric.Rect({
            width: symbol.width || 60,
            height: symbol.height || 60,
            fill: 'transparent',
            stroke: '#556B2F',
            strokeWidth: 2,
            originX: 'center',
            originY: 'center'
        });

        const label = new fabric.Text(symbol.name, {
            fontSize: 10,
            originX: 'center',
            originY: 'top',
            top: (symbol.height || 60) / 2 + 5
        });

        const group = new fabric.Group([rect, text, label], {
            left: x,
            top: y,
            layer: 'DEVICES-SYMBOLS',
            customType: 'symbol',
            symbolId: symbol.id,
            symbolData: symbol
        });

        canvas.add(group);
        canvas.setActiveObject(group);
        addToUndoStack();
        updateObjectCount();

        console.log('Symbol added:', symbol.name);
    }
}

// ============================================================================
// LAYERS
// ============================================================================

function renderLayers() {
    const layersList = document.getElementById('layersList');
    const currentLayerSelect = document.getElementById('currentLayer');

    layersList.innerHTML = '';
    currentLayerSelect.innerHTML = '';

    layers.forEach((layer, index) => {
        // Layer item
        const item = document.createElement('div');
        item.className = 'layer-item';
        item.style.borderLeftColor = layer.color;

        item.innerHTML = `
            <div class="layer-name">${layer.name}</div>
            <div class="layer-controls">
                <button class="layer-btn" onclick="toggleLayerVisibility(${index})">
                    ${layer.visible ? '👁️' : '🚫'}
                </button>
                <button class="layer-btn" onclick="toggleLayerLock(${index})">
                    ${layer.locked ? '🔒' : '🔓'}
                </button>
            </div>
        `;

        layersList.appendChild(item);

        // Current layer selector
        const option = document.createElement('option');
        option.value = layer.name;
        option.textContent = layer.name;
        currentLayerSelect.appendChild(option);
    });
}

function getCurrentLayer() {
    const currentLayerName = document.getElementById('currentLayer').value;
    return layers.find(l => l.name === currentLayerName) || layers[0];
}

function toggleLayerVisibility(index) {
    layers[index].visible = !layers[index].visible;
    renderLayers();

    // Hide/show objects on this layer
    canvas.getObjects().forEach(obj => {
        if (obj.layer === layers[index].name) {
            obj.visible = layers[index].visible;
        }
    });
    canvas.renderAll();
}

function toggleLayerLock(index) {
    layers[index].locked = !layers[index].locked;
    renderLayers();
}

function addLayer() {
    const name = prompt('Enter layer name:');
    if (name) {
        const color = prompt('Enter layer color (hex):', '#34495E');
        layers.push({
            name: name,
            color: color,
            visible: true,
            locked: false
        });
        renderLayers();
    }
}

// ============================================================================
// AI GENERATION
// ============================================================================

function openAIModal() {
    document.getElementById('aiModal').classList.add('active');
}

function closeAIModal() {
    document.getElementById('aiModal').classList.remove('active');
}

async function generateWithAI() {
    const requirements = document.getElementById('aiRequirements').value;

    if (!requirements) {
        alert('Please describe your project requirements');
        return;
    }

    closeAIModal();
    document.getElementById('loadingOverlay').classList.add('active');

    try {
        const response = await fetch('/api/cad/ai-generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                requirements: requirements,
                floorplan_id: null,
                board_id: null,
                quote_id: null
            })
        });

        const data = await response.json();

        if (data.success) {
            // Clear canvas
            canvas.clear();

            // Apply generated layers
            if (data.layers) {
                layers = data.layers;
                renderLayers();
            }

            // TODO: Parse and render AI-generated objects
            // For now, add a sample floor plan

            alert('✅ AI generation complete! Drawing created.');
            console.log('AI Response:', data.ai_analysis);
        } else {
            alert('❌ AI generation failed: ' + data.error);
        }
    } catch (error) {
        console.error('AI generation error:', error);
        alert('Failed to generate drawing');
    } finally {
        document.getElementById('loadingOverlay').classList.remove('active');
    }
}

// ============================================================================
// MULTI-SHEET SUPPORT
// ============================================================================

function initializeSheets() {
    // Initialize with one default sheet
    if (sheets.length === 0) {
        sheets.push({
            id: 'sheet1',
            name: 'Sheet 1 - Main Floor Plan',
            canvasState: canvas.toJSON(),
            metadata: {
                drawing_number: 'E-001',
                title: 'Main Floor Plan'
            }
        });
    }
    updateSheetNavigation();
}

function addNewSheet() {
    // Save current sheet
    saveCurrentSheet();

    // Create new sheet
    const newSheetNum = sheets.length + 1;
    const newSheet = {
        id: `sheet${newSheetNum}`,
        name: `Sheet ${newSheetNum}`,
        canvasState: null,
        metadata: {
            drawing_number: `E-${String(newSheetNum).padStart(3, '0')}`,
            title: `Sheet ${newSheetNum}`
        }
    };

    sheets.push(newSheet);
    currentSheetIndex = sheets.length - 1;

    // Clear canvas for new sheet
    canvas.clear();
    canvas.backgroundColor = '#ffffff';

    updateSheetNavigation();
    console.log(`✅ Added new sheet: ${newSheet.name}`);
}

function switchToSheet(index) {
    if (index < 0 || index >= sheets.length) return;

    // Save current sheet
    saveCurrentSheet();

    // Switch to new sheet
    currentSheetIndex = index;
    const sheet = sheets[index];

    // Clear and load sheet canvas
    canvas.clear();
    if (sheet.canvasState) {
        canvas.loadFromJSON(sheet.canvasState, () => {
            canvas.renderAll();
            console.log(`✅ Switched to ${sheet.name}`);
        });
    } else {
        canvas.backgroundColor = '#ffffff';
        canvas.renderAll();
    }

    updateSheetNavigation();
}

function saveCurrentSheet() {
    if (currentSheetIndex >= 0 && currentSheetIndex < sheets.length) {
        sheets[currentSheetIndex].canvasState = canvas.toJSON();
    }
}

function deleteSheet(index) {
    if (sheets.length === 1) {
        alert('Cannot delete the last sheet!');
        return;
    }

    const sheet = sheets[index];
    if (confirm(`Delete "${sheet.name}"?`)) {
        sheets.splice(index, 1);

        // Adjust current index if needed
        if (currentSheetIndex >= sheets.length) {
            currentSheetIndex = sheets.length - 1;
        }

        switchToSheet(currentSheetIndex);
        console.log(`✅ Deleted sheet: ${sheet.name}`);
    }
}

function renameSheet(index) {
    const sheet = sheets[index];
    const newName = prompt('Enter new sheet name:', sheet.name);

    if (newName && newName.trim()) {
        sheet.name = newName.trim();
        updateSheetNavigation();
        console.log(`✅ Renamed sheet to: ${newName}`);
    }
}

function updateSheetNavigation() {
    // Update sheet tabs UI (if exists)
    const sheetNav = document.getElementById('sheetNavigation');
    if (!sheetNav) return;

    sheetNav.innerHTML = '';

    sheets.forEach((sheet, index) => {
        const tab = document.createElement('div');
        tab.className = `sheet-tab ${index === currentSheetIndex ? 'active' : ''}`;
        tab.innerHTML = `
            <span onclick="switchToSheet(${index})">${sheet.name}</span>
            <button onclick="renameSheet(${index})" title="Rename">✏️</button>
            <button onclick="deleteSheet(${index})" title="Delete">🗑️</button>
        `;
        sheetNav.appendChild(tab);
    });

    // Add new sheet button
    const addBtn = document.createElement('button');
    addBtn.className = 'add-sheet-btn';
    addBtn.innerHTML = '➕ Add Sheet';
    addBtn.onclick = addNewSheet;
    sheetNav.appendChild(addBtn);
}

function exportAllSheets() {
    // Export all sheets to a multi-page PDF or separate DXF files
    saveCurrentSheet();

    const exportData = {
        project: currentSession?.project_name || 'Multi-Sheet Project',
        sheets: sheets.map((sheet, idx) => ({
            sheet_number: idx + 1,
            name: sheet.name,
            drawing_number: sheet.metadata.drawing_number,
            canvas_state: sheet.canvasState
        }))
    };

    console.log('Exporting all sheets:', exportData);
    alert(`Ready to export ${sheets.length} sheets (feature coming soon)`);
}

// ============================================================================
// EXPORT
// ============================================================================

function exportDrawing() {
    document.getElementById('exportModal').classList.add('active');
}

function closeExportModal() {
    document.getElementById('exportModal').classList.remove('active');
}

async function executeExport() {
    const format = document.getElementById('exportFormat').value;

    try {
        if (format === 'png') {
            // Export as PNG
            const dataURL = canvas.toDataURL({
                format: 'png',
                quality: 1,
                multiplier: 3 // High resolution
            });

            const link = document.createElement('a');
            link.download = `cad_export_${Date.now()}.png`;
            link.href = dataURL;
            link.click();

            alert('✅ PNG exported successfully!');
        } else if (format === 'pdf') {
            // Export as PDF using jsPDF
            const { jsPDF } = window.jspdf;
            const pdf = new jsPDF({
                orientation: 'landscape',
                unit: 'mm',
                format: 'a1'
            });

            const imgData = canvas.toDataURL('image/png');
            pdf.addImage(imgData, 'PNG', 10, 10, 280, 180);

            // Add title block
            pdf.setFontSize(12);
            pdf.text(document.getElementById('projectName').value, 15, 200);
            pdf.text(`Drawing: ${document.getElementById('drawingNumber').value}`, 15, 210);
            pdf.text(`Scale: ${document.getElementById('scale').value}`, 15, 220);

            pdf.save(`cad_export_${Date.now()}.pdf`);

            alert('✅ PDF exported successfully!');
        } else if (format === 'svg') {
            // Export as SVG
            const svg = canvas.toSVG();
            const blob = new Blob([svg], { type: 'image/svg+xml' });
            const url = URL.createObjectURL(blob);

            const link = document.createElement('a');
            link.download = `cad_export_${Date.now()}.svg`;
            link.href = url;
            link.click();

            alert('✅ SVG exported successfully!');
        } else if (format === 'dxf') {
            // DXF export (call backend with full CAD data)
            const cadData = {
                canvas_state: canvas.toJSON(),
                layers: layers,
                metadata: currentSession?.metadata || {},
                project_name: currentSession?.project_name || 'Electrical Layout'
            };

            const response = await fetch('/api/cad/export', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    format: 'dxf',
                    session_id: currentSession?.session_id || 'temp',
                    cad_data: cadData
                })
            });

            const data = await response.json();
            if (data.success) {
                // Download the DXF file
                window.location.href = data.download_url;
                alert('✅ DXF file exported successfully! Compatible with AutoCAD.');
            }
        }

        closeExportModal();
    } catch (error) {
        console.error('Export error:', error);
        alert('Export failed: ' + error.message);
    }
}

// ============================================================================
// UTILITIES
// ============================================================================

function zoomIn() {
    zoomLevel = Math.min(zoomLevel * 1.2, 5);
    canvas.setZoom(zoomLevel);
    updateZoomDisplay();
}

function zoomOut() {
    zoomLevel = Math.max(zoomLevel / 1.2, 0.1);
    canvas.setZoom(zoomLevel);
    updateZoomDisplay();
}

function updateZoomDisplay() {
    document.getElementById('zoomLevel').textContent = Math.round(zoomLevel * 100) + '%';
}

function enableGrid() {
    const gridSize = 50; // Larger grid = fewer lines
    const width = canvas.width;
    const height = canvas.height;
    const maxLines = 100; // Limit total grid lines for performance

    // Calculate number of lines
    const verticalLines = Math.min(Math.floor(width / gridSize), maxLines / 2);
    const horizontalLines = Math.min(Math.floor(height / gridSize), maxLines / 2);

    // Add vertical lines
    for (let i = 0; i <= verticalLines; i++) {
        canvas.add(new fabric.Line([i * gridSize, 0, i * gridSize, height], {
            stroke: '#e8e8e8',
            strokeWidth: 1,
            selectable: false,
            evented: false,
            hoverCursor: 'default'
        }));
    }

    // Add horizontal lines
    for (let i = 0; i <= horizontalLines; i++) {
        canvas.add(new fabric.Line([0, i * gridSize, width, i * gridSize], {
            stroke: '#e8e8e8',
            strokeWidth: 1,
            selectable: false,
            evented: false,
            hoverCursor: 'default'
        }));
    }

    console.log(`Grid enabled: ${verticalLines + horizontalLines} lines`);
}

function toggleGrid() {
    // Toggle grid visibility
    console.log('Grid toggled');
}

function updateObjectCount() {
    const count = canvas.getObjects().filter(obj => obj.selectable !== false).length;
    document.getElementById('objectCount').textContent = count;
}

function updatePropertiesPanel(e) {
    // Update properties panel with selected object details
    console.log('Object selected:', e.selected);
}

function updateMetadata() {
    // Metadata changed
    console.log('Metadata updated');
}

function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Prevent delete when editing text
        const activeElement = document.activeElement;
        const isTextInput = activeElement.tagName === 'INPUT' ||
                           activeElement.tagName === 'TEXTAREA' ||
                           activeElement.isContentEditable;

        // Ctrl+Z - Undo
        if (e.ctrlKey && e.key === 'z') {
            e.preventDefault();
            undo();
        }
        // Ctrl+Y - Redo
        if (e.ctrlKey && e.key === 'y') {
            e.preventDefault();
            redo();
        }
        // Ctrl+S - Save
        if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            saveProject();
        }
        // Delete or Backspace - Remove selected object (but not when typing)
        if ((e.key === 'Delete' || e.key === 'Backspace') && !isTextInput) {
            e.preventDefault(); // Prevent browser back navigation
            const activeObject = canvas.getActiveObject();
            if (activeObject) {
                // Check if it's a group selection
                if (activeObject.type === 'activeSelection') {
                    // Delete all objects in selection
                    activeObject.forEachObject((obj) => {
                        canvas.remove(obj);
                    });
                    canvas.discardActiveObject();
                } else {
                    // Delete single object
                    canvas.remove(activeObject);
                }
                addToUndoStack();
                updateObjectCount();
                canvas.renderAll();
            }
        }
        // F8 - Toggle Ortho Mode
        if (e.key === 'F8') {
            e.preventDefault();
            toggleOrtho();
        }
    });
}

function addToUndoStack() {
    undoStack.push(JSON.stringify(canvas.toJSON()));
    redoStack = []; // Clear redo stack
    if (undoStack.length > 50) undoStack.shift(); // Limit stack size
}

function undo() {
    if (undoStack.length > 0) {
        redoStack.push(JSON.stringify(canvas.toJSON()));
        const state = undoStack.pop();
        canvas.loadFromJSON(state, () => {
            canvas.renderAll();
            updateObjectCount();
        });
    }
}

function redo() {
    if (redoStack.length > 0) {
        undoStack.push(JSON.stringify(canvas.toJSON()));
        const state = redoStack.pop();
        canvas.loadFromJSON(state, () => {
            canvas.renderAll();
            updateObjectCount();
        });
    }
}

function switchTab(tab) {
    // Hide all panels
    document.getElementById('propertiesPanel').style.display = 'none';
    document.getElementById('symbolsPanel').style.display = 'none';
    document.getElementById('layersPanel').style.display = 'none';

    // Show selected panel
    document.getElementById(tab + 'Panel').style.display = 'block';

    // Update tab styling
    document.querySelectorAll('.panel-tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
}

// ============================================================================
// ADVANCED SNAPPING SYSTEM
// ============================================================================

function toggleSnap() {
    snapEnabled = !snapEnabled;
    console.log(`Snap: ${snapEnabled ? 'ON' : 'OFF'}`);
    updateSnapUI();
}

function toggleOrtho() {
    orthoMode = !orthoMode;
    console.log(`Ortho Mode: ${orthoMode ? 'ON' : 'OFF'}`);
    updateSnapUI();
}

function togglePolarTracking() {
    polarTrackingEnabled = !polarTrackingEnabled;
    console.log(`Polar Tracking: ${polarTrackingEnabled ? 'ON' : 'OFF'}`);
    updateSnapUI();
}

function toggleObjectSnap() {
    objectSnapEnabled = !objectSnapEnabled;
    console.log(`Object Snap: ${objectSnapEnabled ? 'ON' : 'OFF'}`);
    updateSnapUI();
}

function getSnapPoint(x, y) {
    if (!snapEnabled) return { x, y };

    let snapPoint = { x, y };
    let snapType = null;

    // 1. Grid snap (if grid is visible)
    if (canvas.backgroundImage) {
        const gridSize = 20; // Grid spacing in pixels
        snapPoint.x = Math.round(x / gridSize) * gridSize;
        snapPoint.y = Math.round(y / gridSize) * gridSize;
        snapType = 'grid';
    }

    // 2. Object snap (endpoint, midpoint, center)
    if (objectSnapEnabled) {
        const objectSnap = findNearestObjectSnapPoint(x, y);
        if (objectSnap) {
            snapPoint = objectSnap.point;
            snapType = objectSnap.type;
        }
    }

    // 3. Ortho mode (force horizontal or vertical)
    if (orthoMode && isDrawing && startX !== undefined && startY !== undefined) {
        const dx = Math.abs(snapPoint.x - startX);
        const dy = Math.abs(snapPoint.y - startY);

        if (dx > dy) {
            // Lock to horizontal
            snapPoint.y = startY;
            snapType = 'ortho-h';
        } else {
            // Lock to vertical
            snapPoint.x = startX;
            snapType = 'ortho-v';
        }
    }

    // 4. Polar tracking (snap to polar angles)
    if (polarTrackingEnabled && isDrawing && startX !== undefined && startY !== undefined) {
        const polarSnap = snapToPolarAngle(startX, startY, snapPoint.x, snapPoint.y);
        if (polarSnap) {
            snapPoint = polarSnap.point;
            snapType = `polar-${polarSnap.angle}°`;
        }
    }

    // Show snap indicator
    showSnapIndicator(snapPoint.x, snapPoint.y, snapType);

    return snapPoint;
}

function findNearestObjectSnapPoint(x, y) {
    const objects = canvas.getObjects();
    let nearest = null;
    let minDistance = SNAP_DISTANCE;

    objects.forEach(obj => {
        // Get snap points for this object
        const snapPoints = getObjectSnapPoints(obj);

        snapPoints.forEach(sp => {
            const dx = sp.x - x;
            const dy = sp.y - y;
            const distance = Math.sqrt(dx * dx + dy * dy);

            if (distance < minDistance) {
                minDistance = distance;
                nearest = {
                    point: { x: sp.x, y: sp.y },
                    type: sp.type
                };
            }
        });
    });

    return nearest;
}

function getObjectSnapPoints(obj) {
    const points = [];

    if (obj.type === 'line') {
        // Endpoint snap
        points.push({ x: obj.x1, y: obj.y1, type: 'endpoint' });
        points.push({ x: obj.x2, y: obj.y2, type: 'endpoint' });

        // Midpoint snap
        points.push({
            x: (obj.x1 + obj.x2) / 2,
            y: (obj.y1 + obj.y2) / 2,
            type: 'midpoint'
        });
    } else if (obj.type === 'rect') {
        // Corner snaps
        points.push({ x: obj.left, y: obj.top, type: 'corner' });
        points.push({ x: obj.left + obj.width, y: obj.top, type: 'corner' });
        points.push({ x: obj.left, y: obj.top + obj.height, type: 'corner' });
        points.push({ x: obj.left + obj.width, y: obj.top + obj.height, type: 'corner' });

        // Center snap
        points.push({
            x: obj.left + obj.width / 2,
            y: obj.top + obj.height / 2,
            type: 'center'
        });
    } else if (obj.type === 'circle') {
        // Center snap
        points.push({ x: obj.left + obj.radius, y: obj.top + obj.radius, type: 'center' });

        // Quadrant snaps
        const cx = obj.left + obj.radius;
        const cy = obj.top + obj.radius;
        const r = obj.radius;
        points.push({ x: cx + r, y: cy, type: 'quadrant' }); // Right
        points.push({ x: cx - r, y: cy, type: 'quadrant' }); // Left
        points.push({ x: cx, y: cy + r, type: 'quadrant' }); // Bottom
        points.push({ x: cx, y: cy - r, type: 'quadrant' }); // Top
    } else if (obj.type === 'group') {
        // Center of group
        points.push({ x: obj.left, y: obj.top, type: 'center' });
    }

    return points;
}

function snapToPolarAngle(x1, y1, x2, y2) {
    const dx = x2 - x1;
    const dy = y2 - y1;
    const distance = Math.sqrt(dx * dx + dy * dy);
    const currentAngle = Math.atan2(dy, dx) * 180 / Math.PI;

    // Find nearest polar angle
    let nearestAngle = POLAR_ANGLES[0];
    let minDiff = 360;

    POLAR_ANGLES.forEach(angle => {
        const diff = Math.abs(currentAngle - angle);
        const altDiff = Math.abs(currentAngle - angle + 360);
        const minAngleDiff = Math.min(diff, altDiff);

        if (minAngleDiff < minDiff && minAngleDiff < 5) { // 5 degree tolerance
            minDiff = minAngleDiff;
            nearestAngle = angle;
        }
    });

    if (minDiff < 5) {
        const radAngle = nearestAngle * Math.PI / 180;
        return {
            point: {
                x: x1 + distance * Math.cos(radAngle),
                y: y1 + distance * Math.sin(radAngle)
            },
            angle: nearestAngle
        };
    }

    return null;
}

function showSnapIndicator(x, y, type) {
    // Remove previous indicator
    if (snapIndicator) {
        canvas.remove(snapIndicator);
        snapIndicator = null;
    }

    if (!type) return;

    // Create snap indicator
    const indicators = {
        'endpoint': { symbol: '□', color: '#00ff00' },
        'midpoint': { symbol: '△', color: '#00ffff' },
        'center': { symbol: '○', color: '#ff00ff' },
        'corner': { symbol: '□', color: '#ffff00' },
        'quadrant': { symbol: '◇', color: '#ff8800' },
        'grid': { symbol: '+', color: '#888888' },
        'ortho-h': { symbol: '—', color: '#0088ff' },
        'ortho-v': { symbol: '|', color: '#0088ff' }
    };

    const indicator = indicators[type] || { symbol: '+', color: '#888888' };

    snapIndicator = new fabric.Text(indicator.symbol, {
        left: x,
        top: y - 10,
        fontSize: 16,
        fill: indicator.color,
        selectable: false,
        evented: false,
        opacity: 0.8
    });

    canvas.add(snapIndicator);
    canvas.renderAll();

    // Auto-remove after 500ms
    setTimeout(() => {
        if (snapIndicator) {
            canvas.remove(snapIndicator);
            snapIndicator = null;
            canvas.renderAll();
        }
    }, 500);
}

function updateSnapUI() {
    // Update snap status indicators (if UI elements exist)
    const snapBtn = document.getElementById('snapToggle');
    const orthoBtn = document.getElementById('orthoToggle');
    const polarBtn = document.getElementById('polarToggle');
    const objSnapBtn = document.getElementById('objSnapToggle');

    if (snapBtn) snapBtn.classList.toggle('active', snapEnabled);
    if (orthoBtn) orthoBtn.classList.toggle('active', orthoMode);
    if (polarBtn) polarBtn.classList.toggle('active', polarTrackingEnabled);
    if (objSnapBtn) objSnapBtn.classList.toggle('active', objectSnapEnabled);
}

// Integrate snapping into mouse move event
const originalMouseMove = canvas.on;
canvas.on('mouse:move', function(e) {
    if (isDrawing && drawingObject) {
        const pointer = canvas.getPointer(e.e);
        const snapped = getSnapPoint(pointer.x, pointer.y);

        // Update drawing object with snapped coordinates
        if (currentTool === 'line' || currentTool === 'wire') {
            drawingObject.set({ x2: snapped.x, y2: snapped.y });
        } else if (currentTool === 'rectangle') {
            const width = snapped.x - startX;
            const height = snapped.y - startY;
            drawingObject.set({ width: Math.abs(width), height: Math.abs(height) });
            if (width < 0) drawingObject.set({ left: snapped.x });
            if (height < 0) drawingObject.set({ top: snapped.y });
        } else if (currentTool === 'dimension') {
            updateDimension(drawingObject, startX, startY, snapped.x, snapped.y);
        }

        throttledRender();
    }
});

console.log('✅ CAD Engine loaded successfully');
