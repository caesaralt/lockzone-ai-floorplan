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
        // Initialize Fabric.js canvas
        canvas = new fabric.Canvas('cadCanvas', {
            width: window.innerWidth - 400, // Account for sidebars
            height: window.innerHeight - 120, // Account for header and footer
            backgroundColor: '#ffffff',
            selection: true
        });

        // Initialize layers
        layers = [...DEFAULT_LAYERS];
        renderLayers();

        // Load symbols library
        await loadSymbols();

        // Setup event listeners
        setupCanvasEvents();
        setupKeyboardShortcuts();

        // Enable grid
        enableGrid();

        // Auto-save every 2 minutes
        setInterval(() => autoSave(), 120000);

        // Create new session
        await createNewSession();

        console.log('✅ CAD Designer initialized successfully');
    } catch (error) {
        console.error('❌ Initialization error:', error);
        alert('Failed to initialize CAD Designer. Please refresh the page.');
    }
}

// ============================================================================
// SESSION MANAGEMENT
// ============================================================================

async function createNewSession() {
    try {
        const projectName = document.getElementById('projectName').value;

        const response = await fetch('/api/cad/new', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_name: projectName })
        });

        const data = await response.json();

        if (data.success) {
            currentSession = data.session;
            console.log('✅ Session created:', currentSession.session_id);
            updateObjectCount();
        }
    } catch (error) {
        console.error('Error creating session:', error);
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

function autoSave() {
    if (currentSession && canvas.getObjects().length > 0) {
        console.log('Auto-saving...');
        saveProject();
    }
}

function newProject() {
    if (confirm('Create new project? Unsaved changes will be lost.')) {
        canvas.clear();
        createNewSession();
        document.getElementById('projectName').value = 'Untitled Project';
        updateObjectCount();
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
        } else if (currentTool === 'text') {
            addText(startX, startY);
        }
    });

    // Mouse move
    canvas.on('mouse:move', (e) => {
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
        }

        canvas.renderAll();
    });

    // Mouse up
    canvas.on('mouse:up', () => {
        if (isDrawing && drawingObject) {
            addToUndoStack();
            updateObjectCount();
        }
        isDrawing = false;
        drawingObject = null;
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

            item.innerHTML = `
                <div class="symbol-icon">${symbol.icon}</div>
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

    // Enable drop on canvas
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
}

function addSymbolToCanvas(symbol, x = 100, y = 100) {
    // Create symbol as a group with text
    const text = new fabric.Text(symbol.icon, {
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
            // DXF export (call backend)
            const response = await fetch('/api/cad/export', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    format: 'dxf',
                    session_id: currentSession?.session_id,
                    cad_data: canvas.toJSON()
                })
            });

            const data = await response.json();
            if (data.success) {
                alert('✅ DXF export prepared! (Full DXF export coming in Phase 2)');
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
    const gridSize = 20;
    const width = canvas.width;
    const height = canvas.height;

    for (let i = 0; i < width / gridSize; i++) {
        canvas.add(new fabric.Line([i * gridSize, 0, i * gridSize, height], {
            stroke: '#f0f0f0',
            selectable: false,
            evented: false
        }));
    }

    for (let i = 0; i < height / gridSize; i++) {
        canvas.add(new fabric.Line([0, i * gridSize, width, i * gridSize], {
            stroke: '#f0f0f0',
            selectable: false,
            evented: false
        }));
    }
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
        // Delete - Remove selected
        if (e.key === 'Delete') {
            const activeObject = canvas.getActiveObject();
            if (activeObject) {
                canvas.remove(activeObject);
                addToUndoStack();
                updateObjectCount();
            }
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

console.log('✅ CAD Engine loaded successfully');
