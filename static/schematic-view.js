/**
 * Schematic Diagram View (Single-Line Electrical)
 * Converts physical layout to electrical schematic representation
 * AS/NZS 3000 compliant single-line diagrams
 */

let schematicMode = false;
let originalCanvasState = null;
let schematicCanvas = null;

// Schematic symbol library (simplified representations)
const SCHEMATIC_SYMBOLS = {
    'mains': {
        symbol: '⚡',
        width: 40,
        height: 40,
        draw: (x, y) => createMainsSymbol(x, y)
    },
    'switchboard': {
        symbol: '⊞',
        width: 60,
        height: 80,
        draw: (x, y) => createSwitchboardSymbol(x, y)
    },
    'breaker': {
        symbol: '─┤├─',
        width: 30,
        height: 20,
        draw: (x, y) => createBreakerSymbol(x, y)
    },
    'rcd': {
        symbol: '─┤RCD├─',
        width: 50,
        height: 20,
        draw: (x, y) => createRCDSymbol(x, y)
    },
    'load': {
        symbol: '⊗',
        width: 30,
        height: 30,
        draw: (x, y) => createLoadSymbol(x, y)
    },
    'light': {
        symbol: '◯',
        width: 25,
        height: 25,
        draw: (x, y) => createLightLoadSymbol(x, y)
    }
};

/**
 * Toggle between physical and schematic view
 */
function toggleSchematicView() {
    if (schematicMode) {
        // Switch back to physical view
        restorePhysicalView();
    } else {
        // Switch to schematic view
        showSchematicView();
    }
}

/**
 * Generate and display schematic view
 */
function showSchematicView() {
    console.log('📊 Generating schematic diagram...');

    // Save current canvas state
    originalCanvasState = JSON.stringify(canvas.toJSON(['customType', 'symbolId', 'layer', 'circuitData']));

    // Analyze the physical layout
    const electricalSystem = analyzeElectricalSystem();

    if (electricalSystem.devices.length === 0) {
        alert('No electrical devices found to generate schematic!');
        return;
    }

    // Clear canvas
    canvas.clear();

    // Draw schematic diagram
    drawSchematicDiagram(electricalSystem);

    // Update mode
    schematicMode = true;
    updateSchematicButton(true);

    // Show notification
    showNotification('Switched to Schematic View (Single-Line Diagram)');
}

/**
 * Restore physical layout view
 */
function restorePhysicalView() {
    if (!originalCanvasState) return;

    // Restore canvas
    canvas.loadFromJSON(originalCanvasState, function() {
        canvas.renderAll();
    });

    // Update mode
    schematicMode = false;
    originalCanvasState = null;
    updateSchematicButton(false);

    showNotification('Switched back to Physical View');
}

/**
 * Analyze electrical system from physical layout
 */
function analyzeElectricalSystem() {
    const objects = canvas.getObjects();

    // Find all electrical components
    const switchboards = objects.filter(obj => obj.symbolId === 'switchboard');
    const outlets = objects.filter(obj => obj.symbolId && obj.symbolId.includes('outlet'));
    const lights = objects.filter(obj => obj.symbolId && obj.symbolId.includes('light'));
    const fans = objects.filter(obj => obj.symbolId === 'exhaust-fan');
    const safety = objects.filter(obj => obj.symbolId === 'smoke-detector');

    // Collect wires/connections
    const wires = objects.filter(obj => obj.customType === 'line' || obj.customType === 'wire');

    // Group devices by circuit (if circuit data available)
    const circuits = [];
    const allDevices = [...outlets, ...lights, ...fans, ...safety];

    allDevices.forEach(device => {
        const circuitNum = device.circuitData?.circuitNumber || 'Unknown';

        let circuit = circuits.find(c => c.number === circuitNum);
        if (!circuit) {
            circuit = {
                number: circuitNum,
                devices: [],
                type: determineCircuitType(device),
                protection: 'MCB' // Default
            };
            circuits.push(circuit);
        }

        circuit.devices.push(device);
    });

    return {
        switchboards: switchboards,
        circuits: circuits,
        devices: allDevices,
        wires: wires
    };
}

function determineCircuitType(device) {
    if (device.symbolId.includes('outlet')) return 'Power';
    if (device.symbolId.includes('light')) return 'Lighting';
    if (device.symbolId === 'exhaust-fan') return 'Ventilation';
    if (device.symbolId === 'smoke-detector') return 'Safety';
    return 'General';
}

/**
 * Draw single-line electrical schematic
 */
function drawSchematicDiagram(system) {
    const canvasWidth = canvas.getWidth();
    const canvasHeight = canvas.getHeight();

    let yPos = 100; // Start position
    const xStart = 100;
    const xEnd = canvasWidth - 100;
    const verticalSpacing = 80;

    // Add title
    const title = new fabric.Text('SINGLE-LINE ELECTRICAL DIAGRAM', {
        left: canvasWidth / 2,
        top: 30,
        fontSize: 24,
        fontWeight: 'bold',
        fill: '#2C3E50',
        originX: 'center',
        selectable: false
    });
    canvas.add(title);

    // Draw mains supply
    const mainsSymbol = createMainsSymbol(xStart, yPos);
    canvas.add(mainsSymbol);

    const mainsLabel = new fabric.Text('230V AC\nMains Supply', {
        left: xStart,
        top: yPos + 50,
        fontSize: 10,
        fill: '#2C3E50',
        originX: 'center',
        textAlign: 'center',
        selectable: false
    });
    canvas.add(mainsLabel);

    yPos += 100;

    // Draw main switchboard(s)
    if (system.switchboards.length > 0) {
        const sbX = xStart + 150;

        // Main distribution line
        const mainLine = new fabric.Line([xStart + 20, yPos - 50, sbX, yPos], {
            stroke: '#2C3E50',
            strokeWidth: 3,
            selectable: false
        });
        canvas.add(mainLine);

        // Switchboard
        const switchboard = createSwitchboardSymbol(sbX, yPos);
        canvas.add(switchboard);

        const sbLabel = new fabric.Text('Main\nSwitchboard', {
            left: sbX,
            top: yPos + 50,
            fontSize: 11,
            fontWeight: 'bold',
            fill: '#2C3E50',
            originX: 'center',
            textAlign: 'center',
            selectable: false
        });
        canvas.add(sbLabel);

        yPos += 120;

        // Draw circuits from switchboard
        drawCircuitsFromSwitchboard(sbX, yPos, system.circuits, xEnd);
    } else {
        // No switchboard - draw circuits directly
        drawCircuitsFromSwitchboard(xStart + 150, yPos, system.circuits, xEnd);
    }

    // Add legend
    addSchematicLegend(canvasWidth - 150, 100);

    canvas.renderAll();
}

/**
 * Draw individual circuits from switchboard
 */
function drawCircuitsFromSwitchboard(sbX, startY, circuits, maxX) {
    let yPos = startY;
    const circuitSpacing = 60;
    const busbarX = sbX;

    circuits.forEach((circuit, index) => {
        // Vertical busbar line
        if (index === 0) {
            const busbar = new fabric.Line([busbarX, startY - 20, busbarX, startY + circuits.length * circuitSpacing], {
                stroke: '#2C3E50',
                strokeWidth: 4,
                selectable: false
            });
            canvas.add(busbar);
        }

        // Circuit takeoff line
        const takeoffLine = new fabric.Line([busbarX, yPos, busbarX + 50, yPos], {
            stroke: '#2C3E50',
            strokeWidth: 2,
            selectable: false
        });
        canvas.add(takeoffLine);

        // Circuit breaker
        const breakerX = busbarX + 80;
        const breaker = createBreakerSymbol(breakerX, yPos);
        canvas.add(breaker);

        // Breaker rating label
        const rating = estimateBreakerRating(circuit);
        const breakerLabel = new fabric.Text(`${rating}A\nMCB`, {
            left: breakerX,
            top: yPos - 25,
            fontSize: 9,
            fill: '#2C3E50',
            originX: 'center',
            textAlign: 'center',
            selectable: false
        });
        canvas.add(breakerLabel);

        // RCD if required (for power outlets)
        let nextX = breakerX + 40;
        if (circuit.type === 'Power') {
            const rcd = createRCDSymbol(nextX + 30, yPos);
            canvas.add(rcd);

            const rcdLabel = new fabric.Text('30mA\nRCD', {
                left: nextX + 30,
                top: yPos - 25,
                fontSize: 8,
                fill: '#e74c3c',
                originX: 'center',
                textAlign: 'center',
                selectable: false
            });
            canvas.add(rcdLabel);

            nextX += 70;
        }

        // Circuit line to loads
        const circuitLine = new fabric.Line([breakerX + 20, yPos, nextX + 50, yPos], {
            stroke: '#2C3E50',
            strokeWidth: 2,
            selectable: false
        });
        canvas.add(circuitLine);

        // Draw loads
        const loadX = nextX + 80;
        const loadSymbol = circuit.type === 'Lighting' ? createLightLoadSymbol(loadX, yPos) : createLoadSymbol(loadX, yPos);
        canvas.add(loadSymbol);

        // Load label
        const deviceCount = circuit.devices.length;
        const loadLabel = new fabric.Text(`${circuit.number}\n${circuit.type}\n(${deviceCount} devices)`, {
            left: loadX + 40,
            top: yPos - 15,
            fontSize: 9,
            fill: '#2C3E50',
            textAlign: 'left',
            selectable: false
        });
        canvas.add(loadLabel);

        // Cable info if available
        if (circuit.devices[0]?.circuitData?.cableSize) {
            const cableInfo = new fabric.Text(`${circuit.devices[0].circuitData.cableSize}mm² ${circuit.devices[0].circuitData.cableType}`, {
                left: breakerX + 20,
                top: yPos + 15,
                fontSize: 7,
                fill: '#7f8c8d',
                textAlign: 'center',
                originX: 'center',
                selectable: false
            });
            canvas.add(cableInfo);
        }

        yPos += circuitSpacing;
    });
}

/**
 * Create schematic symbols
 */
function createMainsSymbol(x, y) {
    const lines = [
        new fabric.Line([x - 15, y, x + 15, y], { stroke: '#2C3E50', strokeWidth: 3 }),
        new fabric.Line([x - 10, y - 15, x, y], { stroke: '#e74c3c', strokeWidth: 2 }),
        new fabric.Line([x, y, x + 10, y - 15], { stroke: '#e74c3c', strokeWidth: 2 })
    ];

    const circle = new fabric.Circle({
        radius: 20,
        fill: '',
        stroke: '#e74c3c',
        strokeWidth: 2
    });

    return new fabric.Group([circle, ...lines], {
        left: x,
        top: y,
        originX: 'center',
        originY: 'center',
        selectable: false
    });
}

function createSwitchboardSymbol(x, y) {
    const rect = new fabric.Rect({
        width: 60,
        height: 80,
        fill: '#ecf0f1',
        stroke: '#2C3E50',
        strokeWidth: 2
    });

    const text = new fabric.Text('SB', {
        fontSize: 16,
        fontWeight: 'bold',
        fill: '#2C3E50',
        originX: 'center',
        originY: 'center'
    });

    return new fabric.Group([rect, text], {
        left: x,
        top: y,
        originX: 'center',
        originY: 'center',
        selectable: false
    });
}

function createBreakerSymbol(x, y) {
    const rect = new fabric.Rect({
        width: 20,
        height: 30,
        fill: 'white',
        stroke: '#2C3E50',
        strokeWidth: 2
    });

    const line1 = new fabric.Line([x - 15, y, x - 10, y], { stroke: '#2C3E50', strokeWidth: 2 });
    const line2 = new fabric.Line([x + 10, y, x + 15, y], { stroke: '#2C3E50', strokeWidth: 2 });

    return new fabric.Group([line1, rect, line2], {
        left: x,
        top: y,
        originX: 'center',
        originY: 'center',
        selectable: false
    });
}

function createRCDSymbol(x, y) {
    const rect = new fabric.Rect({
        width: 30,
        height: 25,
        fill: 'white',
        stroke: '#e74c3c',
        strokeWidth: 2,
        rx: 3,
        ry: 3
    });

    const circle = new fabric.Circle({
        radius: 5,
        fill: '',
        stroke: '#e74c3c',
        strokeWidth: 1.5
    });

    return new fabric.Group([rect, circle], {
        left: x,
        top: y,
        originX: 'center',
        originY: 'center',
        selectable: false
    });
}

function createLoadSymbol(x, y) {
    const circle = new fabric.Circle({
        radius: 15,
        fill: 'white',
        stroke: '#3498db',
        strokeWidth: 2
    });

    const cross1 = new fabric.Line([x - 8, y - 8, x + 8, y + 8], { stroke: '#3498db', strokeWidth: 2 });
    const cross2 = new fabric.Line([x - 8, y + 8, x + 8, y - 8], { stroke: '#3498db', strokeWidth: 2 });

    return new fabric.Group([circle, cross1, cross2], {
        left: x,
        top: y,
        originX: 'center',
        originY: 'center',
        selectable: false
    });
}

function createLightLoadSymbol(x, y) {
    const circle = new fabric.Circle({
        radius: 12,
        fill: 'white',
        stroke: '#f39c12',
        strokeWidth: 2
    });

    return new fabric.Group([circle], {
        left: x,
        top: y,
        originX: 'center',
        originY: 'center',
        selectable: false
    });
}

/**
 * Add legend to schematic
 */
function addSchematicLegend(x, y) {
    const legendBg = new fabric.Rect({
        left: x - 120,
        top: y - 20,
        width: 130,
        height: 180,
        fill: '#f8f9fa',
        stroke: '#2C3E50',
        strokeWidth: 1,
        rx: 5,
        ry: 5,
        selectable: false
    });
    canvas.add(legendBg);

    const title = new fabric.Text('LEGEND', {
        left: x - 55,
        top: y - 10,
        fontSize: 12,
        fontWeight: 'bold',
        fill: '#2C3E50',
        originX: 'center',
        selectable: false
    });
    canvas.add(title);

    const legendItems = [
        { symbol: '⚡', text: 'Mains Supply' },
        { symbol: '⊞', text: 'Switchboard' },
        { symbol: '─┤├─', text: 'MCB Breaker' },
        { symbol: 'RCD', text: 'RCD 30mA' },
        { symbol: '⊗', text: 'Power Load' },
        { symbol: '◯', text: 'Light Load' }
    ];

    let itemY = y + 15;
    legendItems.forEach(item => {
        const itemText = new fabric.Text(`${item.symbol}  ${item.text}`, {
            left: x - 110,
            top: itemY,
            fontSize: 10,
            fill: '#2C3E50',
            selectable: false
        });
        canvas.add(itemText);
        itemY += 20;
    });
}

/**
 * Estimate breaker rating based on circuit
 */
function estimateBreakerRating(circuit) {
    if (circuit.type === 'Lighting') return 10;
    if (circuit.type === 'Power') return 16;
    if (circuit.type === 'Ventilation') return 10;
    return 10;
}

/**
 * Update schematic button state
 */
function updateSchematicButton(isSchematic) {
    const button = document.getElementById('schematicToggle');
    if (button) {
        button.textContent = isSchematic ? '🏗️ Physical' : '📊 Schematic';
        button.style.background = isSchematic ? '#27ae60' : 'rgba(255,255,255,0.2)';
    }
}

/**
 * Export schematic to PDF
 */
function exportSchematicToPDF() {
    if (!schematicMode) {
        alert('Please switch to Schematic View first!');
        return;
    }

    if (typeof jsPDF === 'undefined') {
        alert('PDF library not loaded. Please refresh the page.');
        return;
    }

    try {
        const { jsPDF } = window.jspdf;
        const pdf = new jsPDF({
            orientation: 'landscape',
            unit: 'mm',
            format: 'a3'
        });

        const pageWidth = pdf.internal.pageSize.getWidth();
        const pageHeight = pdf.internal.pageSize.getHeight();

        // Title
        pdf.setFontSize(16);
        pdf.setFont(undefined, 'bold');
        pdf.text('SINGLE-LINE ELECTRICAL DIAGRAM', pageWidth / 2, 15, { align: 'center' });

        // Project info
        pdf.setFontSize(10);
        pdf.setFont(undefined, 'normal');
        const projectName = document.getElementById('projectName')?.value || 'Untitled Project';
        pdf.text(projectName, 15, 25);

        const today = new Date().toLocaleDateString();
        pdf.text(`Date: ${today}`, pageWidth - 15, 25, { align: 'right' });

        // Canvas export
        const dataURL = canvas.toDataURL({
            format: 'png',
            quality: 1.0,
            multiplier: 2
        });

        const margin = 20;
        const availableWidth = pageWidth - (margin * 2);
        const availableHeight = pageHeight - (margin * 3);

        pdf.addImage(dataURL, 'PNG', margin, margin + 20, availableWidth, availableHeight - 20);

        // Footer
        pdf.setFontSize(8);
        pdf.setTextColor(128, 128, 128);
        pdf.text('AS/NZS 3000:2018 Compliant Single-Line Diagram', pageWidth / 2, pageHeight - 10, { align: 'center' });

        // Save
        const fileName = `${projectName.replace(/[^a-z0-9]/gi, '_')}_Schematic.pdf`;
        pdf.save(fileName);

        showNotification(`✅ Schematic exported: ${fileName}`);

    } catch (error) {
        console.error('Schematic export error:', error);
        alert('Error exporting schematic: ' + error.message);
    }
}

/**
 * Show notification
 */
function showNotification(message) {
    const notification = document.createElement('div');
    notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #27ae60; color: white; padding: 15px 20px; border-radius: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 10001; font-size: 14px;';
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 4000);
}
