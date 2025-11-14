/**
 * Hatching Patterns and Area Fills
 * Professional CAD hatching for indicating materials, zones, and areas
 * AS/NZS 1100.101 compliant patterns
 */

let hatchMode = false;
let hatchPoints = [];
let currentHatchPattern = 'diagonal';
let currentHatchColor = '#000000';
let currentHatchScale = 1.0;
let currentHatchAngle = 45;
let currentHatchSpacing = 5;

// Standard hatch patterns library
const HATCH_PATTERNS = {
    'solid': {
        name: 'Solid Fill',
        type: 'solid',
        icon: '⬛',
        description: 'Solid color fill'
    },
    'diagonal': {
        name: 'Diagonal Lines',
        type: 'pattern',
        icon: '╱',
        description: 'Diagonal line pattern',
        angle: 45
    },
    'cross': {
        name: 'Cross-Hatch',
        type: 'pattern',
        icon: '✖',
        description: 'Perpendicular crossing lines',
        angle: 45
    },
    'horizontal': {
        name: 'Horizontal Lines',
        type: 'pattern',
        icon: '▬',
        description: 'Horizontal line pattern',
        angle: 0
    },
    'vertical': {
        name: 'Vertical Lines',
        type: 'pattern',
        icon: '▌',
        description: 'Vertical line pattern',
        angle: 90
    },
    'brick': {
        name: 'Brick Pattern',
        type: 'pattern',
        icon: '🧱',
        description: 'Brick wall pattern'
    },
    'concrete': {
        name: 'Concrete',
        type: 'pattern',
        icon: '▓',
        description: 'Concrete/masonry pattern'
    },
    'insulation': {
        name: 'Insulation',
        type: 'pattern',
        icon: '≋',
        description: 'Thermal insulation pattern'
    },
    'earth': {
        name: 'Earth/Ground',
        type: 'pattern',
        icon: '▒',
        description: 'Earth/ground fill pattern'
    },
    'steel': {
        name: 'Steel',
        type: 'pattern',
        icon: '▩',
        description: 'Steel/metal pattern'
    },
    'wood': {
        name: 'Wood Grain',
        type: 'pattern',
        icon: '≡',
        description: 'Wood grain pattern'
    },
    'dots': {
        name: 'Dots',
        type: 'pattern',
        icon: '⋯',
        description: 'Dot pattern'
    }
};

/**
 * Show hatch pattern selection dialog
 */
function showHatchDialog() {
    const modal = document.createElement('div');
    modal.id = 'hatchDialog';
    modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 10000; display: flex; align-items: center; justify-content: center;';

    const content = document.createElement('div');
    content.style.cssText = 'background: white; padding: 30px; border-radius: 8px; max-width: 700px; max-height: 90%; overflow: auto; color: black;';

    const header = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h2 style="margin: 0; color: #2C3E50;">🎨 Hatch Patterns & Fills</h2>
            <button onclick="closeHatchDialog()" style="background: #e74c3c; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">Close</button>
        </div>
    `;

    // Pattern selection grid
    const patterns = Object.entries(HATCH_PATTERNS).map(([id, pattern]) => {
        const isSelected = id === currentHatchPattern;
        return `
            <div onclick="selectHatchPattern('${id}')" style="background: ${isSelected ? '#3498db' : '#f8f9fa'}; padding: 15px; border-radius: 8px; cursor: pointer; text-align: center; border: 2px solid ${isSelected ? '#2980b9' : '#ddd'}; transition: all 0.3s;">
                <div style="font-size: 2em; margin-bottom: 5px;">${pattern.icon}</div>
                <div style="font-weight: bold; font-size: 12px; color: ${isSelected ? 'white' : '#2C3E50'};">${pattern.name}</div>
                <div style="font-size: 10px; color: ${isSelected ? '#ecf0f1' : '#7f8c8d'}; margin-top: 3px;">${pattern.description}</div>
            </div>
        `;
    }).join('');

    const patternGrid = `
        <div style="margin-bottom: 25px;">
            <h3 style="margin-bottom: 15px; color: #2C3E50;">Select Pattern</h3>
            <div id="patternGrid" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
                ${patterns}
            </div>
        </div>
    `;

    // Settings
    const settings = `
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <h3 style="margin-bottom: 15px; color: #2C3E50;">Pattern Settings</h3>

            <div style="margin-bottom: 15px;">
                <label style="display: block; margin-bottom: 5px; font-weight: bold;">Color:</label>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <input type="color" id="hatchColor" value="${currentHatchColor}" onchange="updateHatchColor(this.value)" style="width: 60px; height: 35px; border: 1px solid #ddd; border-radius: 4px; cursor: pointer;">
                    <span id="hatchColorValue">${currentHatchColor}</span>
                    <label style="margin-left: 20px;"><input type="checkbox" id="hatchTransparent" onchange="updateHatchTransparency(this.checked)"> Semi-transparent</label>
                </div>
            </div>

            <div style="margin-bottom: 15px;">
                <label style="display: block; margin-bottom: 5px; font-weight: bold;">Pattern Scale: <span id="scaleValue">${currentHatchScale.toFixed(1)}</span>x</label>
                <input type="range" id="hatchScale" min="0.5" max="3" step="0.1" value="${currentHatchScale}" oninput="updateHatchScale(this.value)" style="width: 100%;">
            </div>

            <div style="margin-bottom: 15px;">
                <label style="display: block; margin-bottom: 5px; font-weight: bold;">Angle: <span id="angleValue">${currentHatchAngle}°</span></label>
                <input type="range" id="hatchAngle" min="0" max="180" step="15" value="${currentHatchAngle}" oninput="updateHatchAngle(this.value)" style="width: 100%;">
            </div>

            <div style="margin-bottom: 15px;">
                <label style="display: block; margin-bottom: 5px; font-weight: bold;">Spacing: <span id="spacingValue">${currentHatchSpacing}px</span></label>
                <input type="range" id="hatchSpacing" min="2" max="20" step="1" value="${currentHatchSpacing}" oninput="updateHatchSpacing(this.value)" style="width: 100%;">
            </div>
        </div>
    `;

    // Buttons
    const buttons = `
        <div style="display: flex; gap: 10px;">
            <button onclick="startHatchSelection()" style="flex: 1; padding: 12px 20px; background: #27ae60; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">✓ Apply to Area</button>
            <button onclick="hatchSelectedObject()" style="flex: 1; padding: 12px 20px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">Apply to Selected</button>
        </div>
    `;

    content.innerHTML = header + patternGrid + settings + buttons;
    modal.appendChild(content);
    document.body.appendChild(modal);
}

function closeHatchDialog() {
    const dialog = document.getElementById('hatchDialog');
    if (dialog) dialog.remove();
}

function selectHatchPattern(patternId) {
    currentHatchPattern = patternId;

    // Update pattern grid to show selection
    const grid = document.getElementById('patternGrid');
    if (grid) {
        const patterns = Object.entries(HATCH_PATTERNS).map(([id, pattern]) => {
            const isSelected = id === patternId;
            return `
                <div onclick="selectHatchPattern('${id}')" style="background: ${isSelected ? '#3498db' : '#f8f9fa'}; padding: 15px; border-radius: 8px; cursor: pointer; text-align: center; border: 2px solid ${isSelected ? '#2980b9' : '#ddd'}; transition: all 0.3s;">
                    <div style="font-size: 2em; margin-bottom: 5px;">${pattern.icon}</div>
                    <div style="font-weight: bold; font-size: 12px; color: ${isSelected ? 'white' : '#2C3E50'};">${pattern.name}</div>
                    <div style="font-size: 10px; color: ${isSelected ? '#ecf0f1' : '#7f8c8d'}; margin-top: 3px;">${pattern.description}</div>
                </div>
            `;
        }).join('');

        grid.innerHTML = patterns;
    }
}

function updateHatchColor(color) {
    currentHatchColor = color;
    document.getElementById('hatchColorValue').textContent = color;
}

function updateHatchTransparency(isTransparent) {
    // Will be applied when creating the hatch
}

function updateHatchScale(scale) {
    currentHatchScale = parseFloat(scale);
    document.getElementById('scaleValue').textContent = scale;
}

function updateHatchAngle(angle) {
    currentHatchAngle = parseInt(angle);
    document.getElementById('angleValue').textContent = angle + '°';
}

function updateHatchSpacing(spacing) {
    currentHatchSpacing = parseInt(spacing);
    document.getElementById('spacingValue').textContent = spacing + 'px';
}

/**
 * Start area selection for hatching
 */
function startHatchSelection() {
    closeHatchDialog();
    hatchMode = true;
    hatchPoints = [];
    canvas.defaultCursor = 'crosshair';

    showHatchInstruction('Click points to define area for hatching. Double-click to complete.');
}

/**
 * Apply hatch to currently selected object
 */
function hatchSelectedObject() {
    const selected = canvas.getActiveObject();

    if (!selected) {
        alert('Please select an object to apply hatching');
        return;
    }

    // Get object bounds
    const bounds = selected.getBoundingRect();

    // Create hatch for the object's area
    const hatch = createHatchPattern(
        bounds.left,
        bounds.top,
        bounds.width,
        bounds.height
    );

    if (hatch) {
        canvas.add(hatch);
        canvas.sendToBack(hatch); // Send hatch behind the object
        canvas.renderAll();
    }

    closeHatchDialog();
}

/**
 * Handle canvas clicks for hatch area selection
 */
function handleHatchClick(x, y) {
    if (!hatchMode) return;

    // Apply snap to point
    const snappedPoint = getSnapPoint(x, y);
    x = snappedPoint.x;
    y = snappedPoint.y;

    hatchPoints.push({ x, y });

    // Add visual marker
    addHatchPoint(x, y);

    // Draw temporary lines
    if (hatchPoints.length > 1) {
        const prevPoint = hatchPoints[hatchPoints.length - 2];
        const line = new fabric.Line([prevPoint.x, prevPoint.y, x, y], {
            stroke: '#3498db',
            strokeWidth: 2,
            strokeDashArray: [5, 5],
            selectable: false,
            evented: false,
            customType: 'tempHatch'
        });
        canvas.add(line);
    }

    canvas.renderAll();
}

/**
 * Complete hatch area selection (double-click)
 */
function completeHatchArea() {
    if (!hatchMode || hatchPoints.length < 3) {
        return;
    }

    // Calculate bounds of the area
    const minX = Math.min(...hatchPoints.map(p => p.x));
    const minY = Math.min(...hatchPoints.map(p => p.y));
    const maxX = Math.max(...hatchPoints.map(p => p.x));
    const maxY = Math.max(...hatchPoints.map(p => p.y));

    const width = maxX - minX;
    const height = maxY - minY;

    // Create polygon shape
    const polygon = new fabric.Polygon(hatchPoints, {
        left: minX,
        top: minY,
        fill: 'transparent',
        stroke: 'transparent',
        selectable: true,
        customType: 'hatchBoundary'
    });

    // Create hatch pattern
    const hatch = createHatchPattern(minX, minY, width, height, hatchPoints);

    if (hatch) {
        // Group polygon and hatch pattern
        const group = new fabric.Group([polygon, hatch], {
            selectable: true,
            hasControls: true,
            hasBorders: true,
            customType: 'hatchGroup'
        });

        canvas.add(group);
    }

    // Clean up
    removeTemporaryHatchElements();
    hatchMode = false;
    hatchPoints = [];
    canvas.defaultCursor = 'default';

    const instruction = document.getElementById('hatchInstruction');
    if (instruction) instruction.remove();

    canvas.renderAll();
}

/**
 * Create hatch pattern based on selected type
 */
function createHatchPattern(x, y, width, height, boundaryPoints = null) {
    const pattern = HATCH_PATTERNS[currentHatchPattern];
    const isTransparent = document.getElementById('hatchTransparent')?.checked || false;
    const opacity = isTransparent ? 0.5 : 1.0;

    if (pattern.type === 'solid') {
        // Solid fill
        return new fabric.Rect({
            left: x,
            top: y,
            width: width,
            height: height,
            fill: currentHatchColor,
            opacity: opacity,
            selectable: false,
            customType: 'hatch'
        });

    } else {
        // Pattern fill
        return createLineHatchPattern(x, y, width, height, pattern);
    }
}

/**
 * Create line-based hatch patterns
 */
function createLineHatchPattern(x, y, width, height, pattern) {
    const lines = [];
    const spacing = currentHatchSpacing * currentHatchScale;
    const angle = currentHatchAngle;

    // Create lines based on pattern
    if (currentHatchPattern === 'diagonal' || currentHatchPattern === 'horizontal' || currentHatchPattern === 'vertical') {
        // Single direction lines
        const angleRad = angle * Math.PI / 180;
        const count = Math.ceil(Math.max(width, height) / spacing) * 2;

        for (let i = -count; i <= count; i++) {
            const offset = i * spacing;

            const x1 = x + offset * Math.cos(angleRad + Math.PI / 2);
            const y1 = y + offset * Math.sin(angleRad + Math.PI / 2);
            const x2 = x1 + Math.max(width, height) * 2 * Math.cos(angleRad);
            const y2 = y1 + Math.max(width, height) * 2 * Math.sin(angleRad);

            const line = new fabric.Line([x1, y1, x2, y2], {
                stroke: currentHatchColor,
                strokeWidth: 1,
                selectable: false,
                evented: false
            });

            lines.push(line);
        }

    } else if (currentHatchPattern === 'cross') {
        // Cross-hatch (two directions)
        const count = Math.ceil(Math.max(width, height) / spacing) * 2;

        // First direction
        for (let i = -count; i <= count; i++) {
            const offset = i * spacing;
            const angleRad = angle * Math.PI / 180;

            const x1 = x + offset * Math.cos(angleRad + Math.PI / 2);
            const y1 = y + offset * Math.sin(angleRad + Math.PI / 2);
            const x2 = x1 + Math.max(width, height) * 2 * Math.cos(angleRad);
            const y2 = y1 + Math.max(width, height) * 2 * Math.sin(angleRad);

            lines.push(new fabric.Line([x1, y1, x2, y2], {
                stroke: currentHatchColor,
                strokeWidth: 1,
                selectable: false,
                evented: false
            }));
        }

        // Second direction (perpendicular)
        for (let i = -count; i <= count; i++) {
            const offset = i * spacing;
            const angleRad = (angle + 90) * Math.PI / 180;

            const x1 = x + offset * Math.cos(angleRad + Math.PI / 2);
            const y1 = y + offset * Math.sin(angleRad + Math.PI / 2);
            const x2 = x1 + Math.max(width, height) * 2 * Math.cos(angleRad);
            const y2 = y1 + Math.max(width, height) * 2 * Math.sin(angleRad);

            lines.push(new fabric.Line([x1, y1, x2, y2], {
                stroke: currentHatchColor,
                strokeWidth: 1,
                selectable: false,
                evented: false
            }));
        }

    } else if (currentHatchPattern === 'dots') {
        // Dot pattern
        const rows = Math.ceil(height / spacing);
        const cols = Math.ceil(width / spacing);

        for (let row = 0; row <= rows; row++) {
            for (let col = 0; col <= cols; col++) {
                const dotX = x + col * spacing;
                const dotY = y + row * spacing;

                const dot = new fabric.Circle({
                    left: dotX - 1,
                    top: dotY - 1,
                    radius: 1.5,
                    fill: currentHatchColor,
                    selectable: false,
                    evented: false
                });

                lines.push(dot);
            }
        }
    }

    // Create group of all lines
    if (lines.length > 0) {
        // Clip to boundary rectangle
        const clipPath = new fabric.Rect({
            left: x - x,
            top: y - y,
            width: width,
            height: height,
            absolutePositioned: true
        });

        const group = new fabric.Group(lines, {
            left: x,
            top: y,
            selectable: false,
            evented: false,
            clipPath: clipPath,
            customType: 'hatch'
        });

        return group;
    }

    return null;
}

/**
 * Helper functions
 */
function addHatchPoint(x, y) {
    const point = new fabric.Circle({
        left: x - 3,
        top: y - 3,
        radius: 3,
        fill: '#e74c3c',
        selectable: false,
        evented: false,
        customType: 'tempHatch'
    });

    canvas.add(point);
}

function removeTemporaryHatchElements() {
    const tempObjects = canvas.getObjects().filter(obj => obj.customType === 'tempHatch');
    tempObjects.forEach(obj => canvas.remove(obj));
    canvas.renderAll();
}

function showHatchInstruction(text) {
    // Remove existing instruction
    const existing = document.getElementById('hatchInstruction');
    if (existing) existing.remove();

    const instruction = document.createElement('div');
    instruction.id = 'hatchInstruction';
    instruction.style.cssText = 'position: fixed; top: 100px; left: 50%; transform: translateX(-50%); background: #9b59b6; color: white; padding: 12px 24px; border-radius: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 1000; font-size: 14px;';
    instruction.innerHTML = `
        ${text}
        <button onclick="cancelHatch()" style="margin-left: 15px; background: #e74c3c; color: white; border: none; padding: 4px 12px; border-radius: 3px; cursor: pointer; font-size: 12px;">Cancel (ESC)</button>
    `;

    document.body.appendChild(instruction);
}

function cancelHatch() {
    hatchMode = false;
    hatchPoints = [];
    canvas.defaultCursor = 'default';

    removeTemporaryHatchElements();

    const instruction = document.getElementById('hatchInstruction');
    if (instruction) instruction.remove();
}

/**
 * Remove hatch from selected object
 */
function removeHatch() {
    const selected = canvas.getActiveObject();

    if (!selected) {
        alert('Please select a hatched object');
        return;
    }

    if (selected.customType === 'hatchGroup') {
        canvas.remove(selected);
        canvas.renderAll();
    } else {
        alert('Selected object is not a hatch');
    }
}

// Handle canvas events for hatching
if (typeof canvas !== 'undefined') {
    canvas.on('mouse:down', function(e) {
        if (!hatchMode) return;

        const pointer = canvas.getPointer(e.e);
        handleHatchClick(pointer.x, pointer.y);
    });

    canvas.on('mouse:dblclick', function(e) {
        if (hatchMode) {
            completeHatchArea();
        }
    });
}

// Keyboard shortcut - ESC to cancel hatch
if (typeof document !== 'undefined') {
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && hatchMode) {
            cancelHatch();
        }
    });
}
