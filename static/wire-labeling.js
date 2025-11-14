/**
 * Automatic Wire Numbering and Labeling System
 * Professional wire identification for electrical installations
 * AS/NZS 3000 compliant wire marking
 */

let wireCounter = 1;
let wireLabels = new Map(); // Maps wire objects to their labels
let wireNumberingEnabled = true;
let labelPrefix = 'W';  // Default prefix (W1, W2, etc.)

/**
 * Auto-number all wires on the canvas
 */
function autoNumberWires() {
    console.log('🔢 Auto-numbering wires...');

    const wires = canvas.getObjects().filter(obj =>
        obj.customType === 'line' || obj.customType === 'wire'
    );

    if (wires.length === 0) {
        alert('No wires found on canvas!');
        return;
    }

    // Remove existing labels
    removeAllWireLabels();

    // Reset counter
    wireCounter = 1;
    wireLabels.clear();

    // Number each wire
    wires.forEach((wire, index) => {
        const wireNumber = `${labelPrefix}${wireCounter++}`;
        addWireLabelToObject(wire, wireNumber);
    });

    canvas.renderAll();
    showNotification(`Auto-numbered ${wires.length} wires`);
}

/**
 * Add a label to a specific wire object
 */
function addWireLabelToObject(wire, labelText) {
    // Calculate midpoint of wire
    const x1 = wire.x1 || wire.left || 0;
    const y1 = wire.y1 || wire.top || 0;
    const x2 = wire.x2 || (wire.left + (wire.width || 0));
    const y2 = wire.y2 || (wire.top + (wire.height || 0));

    const midX = (x1 + x2) / 2;
    const midY = (y1 + y2) / 2;

    // Calculate wire angle for label rotation
    const angle = Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI;
    const labelAngle = (angle > 90 || angle < -90) ? angle + 180 : angle;

    // Create wire label
    const label = new fabric.Text(labelText, {
        left: midX,
        top: midY - 10,
        fontSize: 10,
        fontFamily: 'Arial',
        fill: '#e74c3c',
        backgroundColor: 'rgba(255,255,255,0.8)',
        padding: 2,
        angle: labelAngle,
        originX: 'center',
        originY: 'center',
        selectable: true,
        hasControls: false,
        hasBorders: true,
        customType: 'wireLabel',
        wireReference: wire,
        lockScalingX: true,
        lockScalingY: true
    });

    // Store reference
    wireLabels.set(wire, label);
    wire.wireLabel = label;
    label.wireLabelFor = wire;

    canvas.add(label);
    return label;
}

/**
 * Label wires with custom text (circuit info, cable size, etc.)
 */
function labelSelectedWires() {
    const selected = canvas.getActiveObject();

    if (!selected) {
        alert('Please select a wire to label');
        return;
    }

    if (selected.customType !== 'line' && selected.customType !== 'wire') {
        alert('Please select a wire object');
        return;
    }

    // Prompt for label text
    const currentLabel = selected.wireLabel ? selected.wireLabel.text : '';
    const labelText = prompt('Enter wire label:', currentLabel);

    if (labelText === null) return; // User cancelled

    if (labelText === '') {
        // Remove label if empty
        removeWireLabelFromObject(selected);
    } else {
        // Update or add label
        if (selected.wireLabel) {
            selected.wireLabel.set('text', labelText);
        } else {
            addWireLabelToObject(selected, labelText);
        }
    }

    canvas.renderAll();
}

/**
 * Label wire with circuit information
 */
function labelWireWithCircuit() {
    const selected = canvas.getActiveObject();

    if (!selected || (selected.customType !== 'line' && selected.customType !== 'wire')) {
        alert('Please select a wire to label');
        return;
    }

    // Show dialog for circuit info
    showCircuitLabelDialog(selected);
}

function showCircuitLabelDialog(wire) {
    const modal = document.createElement('div');
    modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 10000; display: flex; align-items: center; justify-content: center;';

    const content = document.createElement('div');
    content.style.cssText = 'background: white; padding: 30px; border-radius: 8px; max-width: 500px; color: black;';

    content.innerHTML = `
        <h2 style="margin: 0 0 20px 0; color: #2C3E50;">🏷️ Wire Circuit Label</h2>

        <div style="margin-bottom: 15px;">
            <label style="display: block; margin-bottom: 5px; font-weight: bold;">Circuit Number:</label>
            <input type="text" id="circuitNumber" placeholder="e.g., C1, L1, P1" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
        </div>

        <div style="margin-bottom: 15px;">
            <label style="display: block; margin-bottom: 5px; font-weight: bold;">Cable Size (mm²):</label>
            <select id="cableSize" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                <option value="1.5">1.5mm²</option>
                <option value="2.5" selected>2.5mm²</option>
                <option value="4">4mm²</option>
                <option value="6">6mm²</option>
                <option value="10">10mm²</option>
                <option value="16">16mm²</option>
            </select>
        </div>

        <div style="margin-bottom: 15px;">
            <label style="display: block; margin-bottom: 5px; font-weight: bold;">Cable Type:</label>
            <select id="cableType" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                <option value="3C+E">3C+E (Active, Neutral, Earth)</option>
                <option value="2C+E">2C+E (Two Core + Earth)</option>
                <option value="Active">Active Only</option>
                <option value="Neutral">Neutral Only</option>
                <option value="Earth">Earth Only</option>
            </select>
        </div>

        <div style="margin-bottom: 20px;">
            <label style="display: block; margin-bottom: 5px; font-weight: bold;">Additional Info:</label>
            <input type="text" id="additionalInfo" placeholder="e.g., To Kitchen, 20A" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
        </div>

        <div style="display: flex; gap: 10px; justify-content: flex-end;">
            <button onclick="closeCircuitLabelDialog()" style="padding: 10px 20px; background: #95a5a6; color: white; border: none; border-radius: 4px; cursor: pointer;">Cancel</button>
            <button onclick="applyCircuitLabel()" style="padding: 10px 20px; background: #27ae60; color: white; border: none; border-radius: 4px; cursor: pointer;">Apply Label</button>
        </div>
    `;

    modal.appendChild(content);
    modal.id = 'circuitLabelModal';
    document.body.appendChild(modal);

    // Store wire reference
    window.currentLabelWire = wire;
}

function applyCircuitLabel() {
    const wire = window.currentLabelWire;
    const circuitNum = document.getElementById('circuitNumber').value;
    const cableSize = document.getElementById('cableSize').value;
    const cableType = document.getElementById('cableType').value;
    const additionalInfo = document.getElementById('additionalInfo').value;

    // Build label text
    let labelText = '';
    if (circuitNum) labelText += circuitNum + ' - ';
    labelText += `${cableSize}mm² ${cableType}`;
    if (additionalInfo) labelText += `\n${additionalInfo}`;

    // Apply label
    if (wire.wireLabel) {
        wire.wireLabel.set('text', labelText);
    } else {
        addWireLabelToObject(wire, labelText);
    }

    // Store circuit data on wire
    wire.circuitData = {
        circuitNumber: circuitNum,
        cableSize: cableSize,
        cableType: cableType,
        additionalInfo: additionalInfo
    };

    canvas.renderAll();
    closeCircuitLabelDialog();
}

function closeCircuitLabelDialog() {
    const modal = document.getElementById('circuitLabelModal');
    if (modal) modal.remove();
    window.currentLabelWire = null;
}

/**
 * Remove label from a wire object
 */
function removeWireLabelFromObject(wire) {
    if (wire.wireLabel) {
        canvas.remove(wire.wireLabel);
        wireLabels.delete(wire);
        wire.wireLabel = null;
    }
}

/**
 * Remove all wire labels
 */
function removeAllWireLabels() {
    const labels = canvas.getObjects().filter(obj => obj.customType === 'wireLabel');
    labels.forEach(label => canvas.remove(label));
    wireLabels.clear();
}

/**
 * Toggle wire label visibility
 */
function toggleWireLabels() {
    const labels = canvas.getObjects().filter(obj => obj.customType === 'wireLabel');

    if (labels.length === 0) {
        alert('No wire labels found. Use "Auto Number Wires" first.');
        return;
    }

    const allVisible = labels.every(label => label.visible);
    labels.forEach(label => label.set('visible', !allVisible));

    canvas.renderAll();
    showNotification(allVisible ? 'Wire labels hidden' : 'Wire labels visible');
}

/**
 * Change label prefix (W, C, L, etc.)
 */
function changeLabelPrefix() {
    const newPrefix = prompt('Enter label prefix (e.g., W, C, L, PWR):', labelPrefix);

    if (newPrefix && newPrefix.trim()) {
        labelPrefix = newPrefix.trim().toUpperCase();
        showNotification(`Label prefix changed to: ${labelPrefix}`);
    }
}

/**
 * Export wire list with all labels and circuit data
 */
function exportWireList() {
    console.log('📋 Exporting wire list...');

    const wires = canvas.getObjects().filter(obj =>
        obj.customType === 'line' || obj.customType === 'wire'
    );

    if (wires.length === 0) {
        alert('No wires found on canvas!');
        return;
    }

    const wireList = [];

    wires.forEach((wire, index) => {
        const label = wire.wireLabel ? wire.wireLabel.text : 'Unlabeled';
        const layer = wire.layer || 'Default';
        const length = calculateWireLength(wire);

        wireList.push({
            number: index + 1,
            label: label,
            layer: layer,
            length: length.toFixed(2),
            circuitData: wire.circuitData || null
        });
    });

    displayWireList(wireList);
}

function calculateWireLength(wire) {
    const x1 = wire.x1 || wire.left || 0;
    const y1 = wire.y1 || wire.top || 0;
    const x2 = wire.x2 || (wire.left + (wire.width || 0));
    const y2 = wire.y2 || (wire.top + (wire.height || 0));

    const dx = x2 - x1;
    const dy = y2 - y1;
    const lengthPixels = Math.sqrt(dx * dx + dy * dy);

    // Convert to meters (100px = 1m)
    return lengthPixels / 100;
}

function displayWireList(wireList) {
    const modal = document.createElement('div');
    modal.id = 'wireListModal';
    modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 10000; display: flex; align-items: center; justify-content: center;';

    const content = document.createElement('div');
    content.style.cssText = 'background: white; padding: 30px; border-radius: 8px; max-width: 90%; max-height: 90%; overflow: auto; color: black;';

    const header = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h2 style="margin: 0; color: #2C3E50;">📋 Wire List</h2>
            <button onclick="closeWireList()" style="background: #e74c3c; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">Close</button>
        </div>
    `;

    const summary = `
        <div style="background: #f8f9fa; padding: 15px; border-radius: 4px; margin-bottom: 20px;">
            <p style="margin: 5px 0;"><strong>Total Wires:</strong> ${wireList.length}</p>
            <p style="margin: 5px 0;"><strong>Total Length:</strong> ${wireList.reduce((sum, w) => sum + parseFloat(w.length), 0).toFixed(2)}m</p>
        </div>
    `;

    const table = `
        <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
            <thead>
                <tr style="background: #2C3E50; color: white;">
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">#</th>
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Label</th>
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Layer</th>
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: right;">Length (m)</th>
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Circuit Info</th>
                </tr>
            </thead>
            <tbody>
                ${wireList.map((wire, idx) => {
                    const circuitInfo = wire.circuitData
                        ? `${wire.circuitData.cableSize}mm² ${wire.circuitData.cableType}`
                        : '—';

                    return `
                        <tr style="background: ${idx % 2 === 0 ? '#f8f9fa' : 'white'};">
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${wire.number}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">${wire.label}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">${wire.layer}</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">${wire.length}</td>
                            <td style="padding: 8px; border: 1px solid #ddd; font-size: 11px;">${circuitInfo}</td>
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;

    content.innerHTML = header + summary + table;
    modal.appendChild(content);
    document.body.appendChild(modal);
}

function closeWireList() {
    const modal = document.getElementById('wireListModal');
    if (modal) modal.remove();
}

/**
 * Update wire labels when wires are moved
 */
function updateWireLabelPositions() {
    wireLabels.forEach((label, wire) => {
        const x1 = wire.x1 || wire.left || 0;
        const y1 = wire.y1 || wire.top || 0;
        const x2 = wire.x2 || (wire.left + (wire.width || 0));
        const y2 = wire.y2 || (wire.top + (wire.height || 0));

        const midX = (x1 + x2) / 2;
        const midY = (y1 + y2) / 2;

        label.set({
            left: midX,
            top: midY - 10
        });
    });
}

// Auto-update label positions when objects move
if (typeof canvas !== 'undefined') {
    canvas.on('object:modified', function(e) {
        if (e.target && (e.target.customType === 'line' || e.target.customType === 'wire')) {
            updateWireLabelPositions();
            canvas.renderAll();
        }
    });
}

/**
 * Show notification message
 */
function showNotification(message) {
    const notification = document.createElement('div');
    notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #27ae60; color: white; padding: 15px 20px; border-radius: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 10001; font-size: 14px;';
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 3000);
}
