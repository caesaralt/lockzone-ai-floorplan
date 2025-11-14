/**
 * Professional Measurement Tools
 * Distance, Area, and Angle measurement for CAD
 * AS/NZS 1100.101 compliant annotations
 */

let measurementMode = null; // 'distance', 'area', 'angle'
let measurementPoints = [];
let tempMeasurementLine = null;
let measurements = []; // Store all measurements

/**
 * Start distance measurement mode
 */
function startDistanceMeasurement() {
    console.log('📏 Starting distance measurement...');

    measurementMode = 'distance';
    measurementPoints = [];
    canvas.defaultCursor = 'crosshair';

    showMeasurementInstruction('Click two points to measure distance');
}

/**
 * Start area measurement mode
 */
function startAreaMeasurement() {
    console.log('📐 Starting area measurement...');

    measurementMode = 'area';
    measurementPoints = [];
    canvas.defaultCursor = 'crosshair';

    showMeasurementInstruction('Click points to define area. Double-click to complete.');
}

/**
 * Start angle measurement mode
 */
function startAngleMeasurement() {
    console.log('📐 Starting angle measurement...');

    measurementMode = 'angle';
    measurementPoints = [];
    canvas.defaultCursor = 'crosshair';

    showMeasurementInstruction('Click three points to measure angle');
}

/**
 * Cancel measurement mode
 */
function cancelMeasurement() {
    measurementMode = null;
    measurementPoints = [];
    canvas.defaultCursor = 'default';

    if (tempMeasurementLine) {
        canvas.remove(tempMeasurementLine);
        tempMeasurementLine = null;
    }

    // Remove instruction
    const instruction = document.getElementById('measurementInstruction');
    if (instruction) instruction.remove();

    canvas.renderAll();
}

/**
 * Handle canvas clicks for measurements
 */
function handleMeasurementClick(x, y) {
    if (!measurementMode) return;

    // Apply snap to point
    const snappedPoint = getSnapPoint(x, y);
    x = snappedPoint.x;
    y = snappedPoint.y;

    measurementPoints.push({ x, y });

    // Add visual marker
    addMeasurementPoint(x, y);

    // Handle different measurement types
    if (measurementMode === 'distance') {
        handleDistanceMeasurement(x, y);
    } else if (measurementMode === 'angle') {
        handleAngleMeasurement(x, y);
    } else if (measurementMode === 'area') {
        handleAreaMeasurement(x, y);
    }
}

/**
 * Distance measurement logic
 */
function handleDistanceMeasurement(x, y) {
    if (measurementPoints.length === 1) {
        // First point - show temporary line
        tempMeasurementLine = new fabric.Line([x, y, x, y], {
            stroke: '#3498db',
            strokeWidth: 2,
            strokeDashArray: [5, 5],
            selectable: false,
            evented: false,
            customType: 'tempMeasurement'
        });
        canvas.add(tempMeasurementLine);

    } else if (measurementPoints.length === 2) {
        // Second point - complete measurement
        const p1 = measurementPoints[0];
        const p2 = measurementPoints[1];

        const distance = calculateDistance(p1.x, p1.y, p2.x, p2.y);
        createDistanceAnnotation(p1, p2, distance);

        // Store measurement
        measurements.push({
            type: 'distance',
            points: [p1, p2],
            value: distance,
            unit: 'm'
        });

        // Reset
        cancelMeasurement();
        showMeasurementResult(`Distance: ${distance.toFixed(3)}m`);
    }
}

/**
 * Angle measurement logic
 */
function handleAngleMeasurement(x, y) {
    if (measurementPoints.length === 2) {
        // Show second temporary line
        const p1 = measurementPoints[0];
        const line2 = new fabric.Line([p1.x, p1.y, x, y], {
            stroke: '#3498db',
            strokeWidth: 2,
            strokeDashArray: [5, 5],
            selectable: false,
            evented: false,
            customType: 'tempMeasurement'
        });
        canvas.add(line2);

    } else if (measurementPoints.length === 3) {
        // Third point - complete angle measurement
        const p1 = measurementPoints[0]; // Vertex
        const p2 = measurementPoints[1]; // First ray
        const p3 = measurementPoints[2]; // Second ray

        const angle = calculateAngle(p1, p2, p3);
        createAngleAnnotation(p1, p2, p3, angle);

        // Store measurement
        measurements.push({
            type: 'angle',
            points: [p1, p2, p3],
            value: angle,
            unit: '°'
        });

        // Reset
        cancelMeasurement();
        showMeasurementResult(`Angle: ${angle.toFixed(2)}°`);
    }
}

/**
 * Area measurement logic
 */
function handleAreaMeasurement(x, y) {
    // Add temporary lines between points
    if (measurementPoints.length > 1) {
        const prevPoint = measurementPoints[measurementPoints.length - 2];
        const line = new fabric.Line([prevPoint.x, prevPoint.y, x, y], {
            stroke: '#3498db',
            strokeWidth: 2,
            strokeDashArray: [5, 5],
            selectable: false,
            evented: false,
            customType: 'tempMeasurement'
        });
        canvas.add(line);
    }
}

/**
 * Complete area measurement (called on double-click)
 */
function completeAreaMeasurement() {
    if (measurementMode !== 'area' || measurementPoints.length < 3) {
        return;
    }

    // Close the polygon
    const firstPoint = measurementPoints[0];
    const lastPoint = measurementPoints[measurementPoints.length - 1];

    const closingLine = new fabric.Line([lastPoint.x, lastPoint.y, firstPoint.x, firstPoint.y], {
        stroke: '#3498db',
        strokeWidth: 2,
        strokeDashArray: [5, 5],
        selectable: false,
        evented: false,
        customType: 'tempMeasurement'
    });
    canvas.add(closingLine);

    // Calculate area
    const area = calculatePolygonArea(measurementPoints);
    const perimeter = calculatePolygonPerimeter(measurementPoints);

    createAreaAnnotation(measurementPoints, area, perimeter);

    // Store measurement
    measurements.push({
        type: 'area',
        points: [...measurementPoints],
        value: area,
        perimeter: perimeter,
        unit: 'm²'
    });

    // Reset
    cancelMeasurement();
    showMeasurementResult(`Area: ${area.toFixed(2)}m² | Perimeter: ${perimeter.toFixed(2)}m`);
}

/**
 * Create distance annotation on canvas
 */
function createDistanceAnnotation(p1, p2, distance) {
    // Create measurement line
    const line = new fabric.Line([p1.x, p1.y, p2.x, p2.y], {
        stroke: '#27ae60',
        strokeWidth: 2,
        selectable: true,
        customType: 'measurement',
        measurementType: 'distance'
    });

    // Create text label
    const midX = (p1.x + p2.x) / 2;
    const midY = (p1.y + p2.y) / 2;

    const angle = Math.atan2(p2.y - p1.y, p2.x - p1.x) * 180 / Math.PI;
    const labelAngle = (angle > 90 || angle < -90) ? angle + 180 : angle;

    const label = new fabric.Text(`${distance.toFixed(3)}m`, {
        left: midX,
        top: midY - 15,
        fontSize: 12,
        fontFamily: 'Arial',
        fill: '#27ae60',
        backgroundColor: 'rgba(255,255,255,0.9)',
        padding: 4,
        angle: labelAngle,
        originX: 'center',
        originY: 'center',
        selectable: true,
        customType: 'measurementLabel'
    });

    // Add arrows
    const arrow1 = createMeasurementArrow(p1.x, p1.y, angle + 180);
    const arrow2 = createMeasurementArrow(p2.x, p2.y, angle);

    // Group all elements
    const group = new fabric.Group([line, arrow1, arrow2, label], {
        selectable: true,
        hasControls: true,
        hasBorders: true,
        customType: 'measurementGroup',
        lockScalingX: true,
        lockScalingY: true
    });

    canvas.add(group);

    // Remove temporary elements
    removeTemporaryMeasurements();
}

/**
 * Create angle annotation
 */
function createAngleAnnotation(vertex, p2, p3, angle) {
    // Create two lines
    const line1 = new fabric.Line([vertex.x, vertex.y, p2.x, p2.y], {
        stroke: '#e67e22',
        strokeWidth: 2,
        selectable: false
    });

    const line2 = new fabric.Line([vertex.x, vertex.y, p3.x, p3.y], {
        stroke: '#e67e22',
        strokeWidth: 2,
        selectable: false
    });

    // Create arc to show angle
    const angle1 = Math.atan2(p2.y - vertex.y, p2.x - vertex.x);
    const angle2 = Math.atan2(p3.y - vertex.y, p3.x - vertex.x);
    const radius = 30;

    const arc = new fabric.Circle({
        left: vertex.x - radius,
        top: vertex.y - radius,
        radius: radius,
        fill: '',
        stroke: '#e67e22',
        strokeWidth: 2,
        startAngle: angle1,
        endAngle: angle2,
        selectable: false
    });

    // Angle label
    const labelAngle = (angle1 + angle2) / 2;
    const labelX = vertex.x + Math.cos(labelAngle) * (radius + 20);
    const labelY = vertex.y + Math.sin(labelAngle) * (radius + 20);

    const label = new fabric.Text(`${angle.toFixed(2)}°`, {
        left: labelX,
        top: labelY,
        fontSize: 12,
        fontFamily: 'Arial',
        fill: '#e67e22',
        backgroundColor: 'rgba(255,255,255,0.9)',
        padding: 4,
        originX: 'center',
        originY: 'center',
        selectable: false,
        customType: 'measurementLabel'
    });

    const group = new fabric.Group([line1, line2, arc, label], {
        selectable: true,
        hasControls: true,
        hasBorders: true,
        customType: 'measurementGroup',
        lockScalingX: true,
        lockScalingY: true
    });

    canvas.add(group);
    removeTemporaryMeasurements();
}

/**
 * Create area annotation
 */
function createAreaAnnotation(points, area, perimeter) {
    // Create polygon outline
    const polygonPoints = points.map(p => ({ x: p.x, y: p.y }));

    const polygon = new fabric.Polygon(polygonPoints, {
        fill: 'rgba(52, 152, 219, 0.1)',
        stroke: '#3498db',
        strokeWidth: 2,
        selectable: true,
        customType: 'measurement',
        measurementType: 'area'
    });

    // Calculate centroid for label placement
    const centroid = calculateCentroid(points);

    const label = new fabric.Text(`Area: ${area.toFixed(2)}m²\nPerim: ${perimeter.toFixed(2)}m`, {
        left: centroid.x,
        top: centroid.y,
        fontSize: 12,
        fontFamily: 'Arial',
        fill: '#3498db',
        backgroundColor: 'rgba(255,255,255,0.9)',
        padding: 6,
        originX: 'center',
        originY: 'center',
        selectable: true,
        customType: 'measurementLabel',
        textAlign: 'center'
    });

    const group = new fabric.Group([polygon, label], {
        selectable: true,
        hasControls: true,
        hasBorders: true,
        customType: 'measurementGroup'
    });

    canvas.add(group);
    removeTemporaryMeasurements();
}

/**
 * Calculation functions
 */
function calculateDistance(x1, y1, x2, y2) {
    const dx = x2 - x1;
    const dy = y2 - y1;
    const pixels = Math.sqrt(dx * dx + dy * dy);
    return pixels / 100; // Convert to meters (100px = 1m)
}

function calculateAngle(vertex, p2, p3) {
    const angle1 = Math.atan2(p2.y - vertex.y, p2.x - vertex.x);
    const angle2 = Math.atan2(p3.y - vertex.y, p3.x - vertex.x);

    let angle = (angle2 - angle1) * 180 / Math.PI;

    // Normalize to 0-360
    if (angle < 0) angle += 360;
    if (angle > 180) angle = 360 - angle; // Get acute angle

    return angle;
}

function calculatePolygonArea(points) {
    let area = 0;
    const n = points.length;

    for (let i = 0; i < n; i++) {
        const j = (i + 1) % n;
        area += points[i].x * points[j].y;
        area -= points[j].x * points[i].y;
    }

    area = Math.abs(area) / 2;

    // Convert from pixels² to m² (100px = 1m, so 10000px² = 1m²)
    return area / 10000;
}

function calculatePolygonPerimeter(points) {
    let perimeter = 0;
    const n = points.length;

    for (let i = 0; i < n; i++) {
        const j = (i + 1) % n;
        const distance = calculateDistance(points[i].x, points[i].y, points[j].x, points[j].y);
        perimeter += distance;
    }

    return perimeter;
}

function calculateCentroid(points) {
    let x = 0, y = 0;

    points.forEach(p => {
        x += p.x;
        y += p.y;
    });

    return {
        x: x / points.length,
        y: y / points.length
    };
}

/**
 * Helper functions
 */
function addMeasurementPoint(x, y) {
    const point = new fabric.Circle({
        left: x - 3,
        top: y - 3,
        radius: 3,
        fill: '#e74c3c',
        selectable: false,
        evented: false,
        customType: 'tempMeasurement'
    });

    canvas.add(point);
}

function createMeasurementArrow(x, y, angle) {
    const arrowSize = 8;
    const angleRad = angle * Math.PI / 180;

    const points = [
        { x: x, y: y },
        { x: x - arrowSize * Math.cos(angleRad - Math.PI / 6), y: y - arrowSize * Math.sin(angleRad - Math.PI / 6) },
        { x: x - arrowSize * Math.cos(angleRad + Math.PI / 6), y: y - arrowSize * Math.sin(angleRad + Math.PI / 6) }
    ];

    return new fabric.Polygon(points, {
        fill: '#27ae60',
        selectable: false
    });
}

function removeTemporaryMeasurements() {
    const tempObjects = canvas.getObjects().filter(obj => obj.customType === 'tempMeasurement');
    tempObjects.forEach(obj => canvas.remove(obj));
    canvas.renderAll();
}

/**
 * UI helper functions
 */
function showMeasurementInstruction(text) {
    // Remove existing instruction
    const existing = document.getElementById('measurementInstruction');
    if (existing) existing.remove();

    const instruction = document.createElement('div');
    instruction.id = 'measurementInstruction';
    instruction.style.cssText = 'position: fixed; top: 100px; left: 50%; transform: translateX(-50%); background: #3498db; color: white; padding: 12px 24px; border-radius: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 1000; font-size: 14px;';
    instruction.innerHTML = `
        ${text}
        <button onclick="cancelMeasurement()" style="margin-left: 15px; background: #e74c3c; color: white; border: none; padding: 4px 12px; border-radius: 3px; cursor: pointer; font-size: 12px;">Cancel (ESC)</button>
    `;

    document.body.appendChild(instruction);
}

function showMeasurementResult(text) {
    const result = document.createElement('div');
    result.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #27ae60; color: white; padding: 15px 20px; border-radius: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 10001; font-size: 14px;';
    result.textContent = text;

    document.body.appendChild(result);

    setTimeout(() => result.remove(), 4000);
}

/**
 * Clear all measurements from canvas
 */
function clearAllMeasurements() {
    if (!confirm('Remove all measurements from the drawing?')) return;

    const measurementObjects = canvas.getObjects().filter(obj =>
        obj.customType === 'measurement' ||
        obj.customType === 'measurementLabel' ||
        obj.customType === 'measurementGroup'
    );

    measurementObjects.forEach(obj => canvas.remove(obj));
    measurements = [];

    canvas.renderAll();
    showMeasurementResult('All measurements cleared');
}

/**
 * List all measurements
 */
function showMeasurementsList() {
    if (measurements.length === 0) {
        alert('No measurements recorded yet!');
        return;
    }

    const modal = document.createElement('div');
    modal.id = 'measurementsListModal';
    modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 10000; display: flex; align-items: center; justify-content: center;';

    const content = document.createElement('div');
    content.style.cssText = 'background: white; padding: 30px; border-radius: 8px; max-width: 600px; max-height: 80%; overflow: auto; color: black;';

    const header = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h2 style="margin: 0; color: #2C3E50;">📏 Measurements List</h2>
            <button onclick="closeMeasurementsList()" style="background: #e74c3c; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">Close</button>
        </div>
    `;

    const list = measurements.map((m, idx) => {
        let valueText = '';
        if (m.type === 'distance') {
            valueText = `${m.value.toFixed(3)}m`;
        } else if (m.type === 'angle') {
            valueText = `${m.value.toFixed(2)}°`;
        } else if (m.type === 'area') {
            valueText = `${m.value.toFixed(2)}m² (Perimeter: ${m.perimeter.toFixed(2)}m)`;
        }

        return `
            <div style="padding: 12px; margin-bottom: 10px; background: ${idx % 2 === 0 ? '#f8f9fa' : 'white'}; border-radius: 4px; border-left: 4px solid #3498db;">
                <div style="font-weight: bold; color: #2C3E50; margin-bottom: 5px;">
                    ${idx + 1}. ${m.type.charAt(0).toUpperCase() + m.type.slice(1)} Measurement
                </div>
                <div style="color: #7f8c8d; font-size: 14px;">
                    Value: <strong>${valueText}</strong>
                </div>
            </div>
        `;
    }).join('');

    content.innerHTML = header + list;
    modal.appendChild(content);
    document.body.appendChild(modal);
}

function closeMeasurementsList() {
    const modal = document.getElementById('measurementsListModal');
    if (modal) modal.remove();
}

// Keyboard shortcut - ESC to cancel measurement
if (typeof document !== 'undefined') {
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && measurementMode) {
            cancelMeasurement();
        }
    });
}

// Handle canvas events for measurements
if (typeof canvas !== 'undefined') {
    canvas.on('mouse:down', function(e) {
        if (!measurementMode) return;

        const pointer = canvas.getPointer(e.e);
        handleMeasurementClick(pointer.x, pointer.y);
    });

    canvas.on('mouse:dblclick', function(e) {
        if (measurementMode === 'area') {
            completeAreaMeasurement();
        }
    });
}
