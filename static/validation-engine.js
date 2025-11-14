/**
 * Real-Time Validation Engine
 * AS/NZS 3000:2018 compliance checking
 * Provides warnings and errors during design
 */

let validationResults = {
    errors: [],
    warnings: [],
    info: []
};

let validationEnabled = true;
let validationInterval = null;

// Start real-time validation
function startValidation() {
    console.log('✅ Starting real-time validation engine...');
    validationEnabled = true;

    // Run validation every 5 seconds
    if (validationInterval) {
        clearInterval(validationInterval);
    }

    validationInterval = setInterval(() => {
        if (validationEnabled && canvas) {
            runValidation();
        }
    }, 5000);

    // Run initial validation
    runValidation();
}

function stopValidation() {
    validationEnabled = false;
    if (validationInterval) {
        clearInterval(validationInterval);
    }
}

function runValidation() {
    // Clear previous results
    validationResults = {
        errors: [],
        warnings: [],
        info: []
    };

    // Run all validation checks
    validateDevicePlacement();
    validateCircuitLoading();
    validateWiring();
    validateClearances();
    validateEarthing();
    validateRCDProtection();
    validateDocumentation();

    // Update validation UI
    updateValidationUI();
}

function validateDevicePlacement() {
    const objects = canvas.getObjects();
    const devices = objects.filter(obj => obj.customType === 'symbol');

    // Check for overlapping devices
    for (let i = 0; i < devices.length; i++) {
        for (let j = i + 1; j < devices.length; j++) {
            if (devicesOverlap(devices[i], devices[j])) {
                validationResults.warnings.push({
                    type: 'overlap',
                    severity: 'warning',
                    message: `Devices overlap at (${Math.round(devices[i].left)}, ${Math.round(devices[i].top)})`,
                    code: 'W001',
                    fix: 'Separate overlapping devices'
                });
            }
        }
    }

    // Check outlet spacing in bathrooms/wet areas
    const outlets = devices.filter(d => d.symbolId && d.symbolId.includes('outlet'));
    outlets.forEach(outlet => {
        // Simple check - in real app would check room type
        validationResults.info.push({
            type: 'spacing',
            severity: 'info',
            message: 'Verify outlet placement complies with wet area requirements',
            code: 'I001',
            standard: 'AS/NZS 3000 Clause 2.5.3'
        });
    });
}

function validateCircuitLoading() {
    const devices = canvas.getObjects().filter(obj => obj.customType === 'symbol');

    // Count devices by type
    const outletCount = devices.filter(d => d.symbolId && d.symbolId.includes('outlet')).length;
    const lightCount = devices.filter(d => d.symbolId && d.symbolId.includes('light')).length;

    // AS/NZS 3000 - Max 10 outlets per circuit (recommended)
    if (outletCount > 10) {
        validationResults.warnings.push({
            type: 'loading',
            severity: 'warning',
            message: `${outletCount} power outlets detected. Consider splitting into multiple circuits (max 10 per circuit recommended)`,
            code: 'W002',
            standard: 'AS/NZS 3000 guidance',
            fix: 'Add additional power circuits'
        });
    }

    // Max 15 lighting points per circuit (recommended)
    if (lightCount > 15) {
        validationResults.warnings.push({
            type: 'loading',
            severity: 'warning',
            message: `${lightCount} lighting points detected. Consider splitting into multiple circuits (max 15 recommended)`,
            code: 'W003',
            standard: 'AS/NZS 3000 guidance',
            fix: 'Add additional lighting circuits'
        });
    }
}

function validateWiring() {
    const wires = canvas.getObjects().filter(obj => obj.customType === 'line' || obj.customType === 'wire');

    // Check for extremely long wire runs
    wires.forEach(wire => {
        const length = calculateLineLength(wire);

        if (length > 50) {  // 50 meters
            validationResults.warnings.push({
                type: 'voltage_drop',
                severity: 'warning',
                message: `Long cable run detected (${length.toFixed(1)}m). Verify voltage drop is within 5% limit`,
                code: 'W004',
                standard: 'AS/NZS 3000 Clause 2.2.2',
                fix: 'Check voltage drop calculation or use larger cable'
            });
        }
    });

    // Check for wires without proper layer
    wires.forEach(wire => {
        if (!wire.layer || wire.layer === '0') {
            validationResults.errors.push({
                type: 'layer',
                severity: 'error',
                message: 'Wire found on incorrect layer',
                code: 'E001',
                fix: 'Move wire to appropriate wiring layer (POWER-WIRING-RED, etc.)'
            });
        }
    });
}

function validateClearances() {
    const objects = canvas.getObjects();

    // Check for devices near high-voltage areas
    const switchboards = objects.filter(obj => obj.symbolId === 'switchboard');
    const devices = objects.filter(obj => obj.customType === 'symbol' && obj.symbolId !== 'switchboard');

    switchboards.forEach(sb => {
        devices.forEach(device => {
            const distance = calculateDistance(sb, device);

            // AS/NZS 3000 - Minimum working space around switchboards
            if (distance < 100) {  // 1 meter in pixels (100px = 1m)
                validationResults.warnings.push({
                    type: 'clearance',
                    severity: 'warning',
                    message: 'Device too close to switchboard. Maintain minimum 1m working clearance',
                    code: 'W005',
                    standard: 'AS/NZS 3000 Clause 2.11',
                    fix: 'Move device away from switchboard'
                });
            }
        });
    });
}

function validateEarthing() {
    const objects = canvas.getObjects();
    const earthWires = objects.filter(obj => obj.layer === 'GROUND-WIRING-GREEN');
    const devices = objects.filter(obj => obj.customType === 'symbol');

    // Check if earth wiring exists
    if (devices.length > 0 && earthWires.length === 0) {
        validationResults.errors.push({
            type: 'earthing',
            severity: 'error',
            message: 'No earth wiring detected. All circuits must have earth conductor',
            code: 'E002',
            standard: 'AS/NZS 3000 Clause 5.4',
            fix: 'Add earth wiring on GROUND-WIRING-GREEN layer'
        });
    }
}

function validateRCDProtection() {
    const objects = canvas.getObjects();
    const rcds = objects.filter(obj => obj.symbolId === 'rcd' || obj.symbolId === 'rcbo');
    const outlets = objects.filter(obj => obj.symbolId && obj.symbolId.includes('outlet'));

    // AS/NZS 3000 - RCD protection required for socket outlets
    if (outlets.length > 0 && rcds.length === 0) {
        validationResults.errors.push({
            type: 'rcd',
            severity: 'error',
            message: 'RCD protection required for socket outlets',
            code: 'E003',
            standard: 'AS/NZS 3000 Clause 2.5.2',
            fix: 'Add RCD or RCBO to protect socket outlets'
        });
    }
}

function validateDocumentation() {
    const objects = canvas.getObjects();
    const titleBlocks = objects.filter(obj => obj.customType === 'titleBlock');

    // Check for title block
    if (titleBlocks.length === 0) {
        validationResults.warnings.push({
            type: 'documentation',
            severity: 'warning',
            message: 'No title block found. Add title block for professional documentation',
            code: 'W006',
            fix: 'Click "📋 Title Block" button to add'
        });
    }

    // Check for dimensions
    const dimensions = objects.filter(obj => obj.customType === 'dimension');
    if (dimensions.length === 0) {
        validationResults.info.push({
            type: 'documentation',
            severity: 'info',
            message: 'Consider adding dimensions for installation reference',
            code: 'I002'
        });
    }
}

// Helper functions
function calculateLineLength(lineObj) {
    const x1 = lineObj.x1 || lineObj.left || 0;
    const y1 = lineObj.y1 || lineObj.top || 0;
    const x2 = lineObj.x2 || (lineObj.left + (lineObj.width || 0));
    const y2 = lineObj.y2 || (lineObj.top + (lineObj.height || 0));

    const dx = x2 - x1;
    const dy = y2 - y1;
    const lengthPixels = Math.sqrt(dx * dx + dy * dy);

    // Convert pixels to meters (assuming 100 pixels = 1 meter)
    const lengthMeters = lengthPixels / 100;

    return lengthMeters;
}

function devicesOverlap(dev1, dev2) {
    const threshold = 20; // pixels
    const dx = dev1.left - dev2.left;
    const dy = dev1.top - dev2.top;
    const distance = Math.sqrt(dx * dx + dy * dy);
    return distance < threshold;
}

function calculateDistance(obj1, obj2) {
    const dx = obj1.left - obj2.left;
    const dy = obj1.top - obj2.top;
    return Math.sqrt(dx * dx + dy * dy);
}

function updateValidationUI() {
    const errorCount = validationResults.errors.length;
    const warningCount = validationResults.warnings.length;
    const infoCount = validationResults.info.length;

    // Update validation badge
    let badge = document.getElementById('validationBadge');
    if (!badge) {
        badge = document.createElement('div');
        badge.id = 'validationBadge';
        badge.style.cssText = 'position: fixed; bottom: 20px; right: 20px; background: white; padding: 15px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); cursor: pointer; z-index: 1000; min-width: 150px;';
        badge.onclick = showValidationPanel;
        document.body.appendChild(badge);
    }

    let badgeColor = '#27ae60'; // Green
    let statusText = 'All Good';
    let statusIcon = '✅';

    if (errorCount > 0) {
        badgeColor = '#e74c3c'; // Red
        statusText = 'Errors Found';
        statusIcon = '❌';
    } else if (warningCount > 0) {
        badgeColor = '#f39c12'; // Orange
        statusText = 'Warnings';
        statusIcon = '⚠️';
    }

    badge.style.borderLeft = `5px solid ${badgeColor}`;
    badge.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px; color: #2C3E50;">
            <span style="font-size: 24px;">${statusIcon}</span>
            <div>
                <div style="font-weight: bold; font-size: 14px;">${statusText}</div>
                <div style="font-size: 11px; color: #7f8c8d;">
                    ${errorCount} errors, ${warningCount} warnings
                </div>
            </div>
        </div>
        <div style="font-size: 10px; color: #95a5a6; margin-top: 5px;">Click to view details</div>
    `;
}

function showValidationPanel() {
    // Create validation panel modal
    const modal = document.createElement('div');
    modal.id = 'validationPanel';
    modal.className = 'modal active';
    modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 10000; display: flex; align-items: center; justify-content: center;';

    const content = document.createElement('div');
    content.style.cssText = 'background: white; padding: 30px; border-radius: 8px; max-width: 800px; max-height: 80%; overflow: auto; color: black;';

    // Header
    const header = document.createElement('div');
    header.style.cssText = 'display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;';
    header.innerHTML = `
        <h2 style="margin: 0; color: #2C3E50;">🔍 Validation Results</h2>
        <button onclick="closeValidationPanel()" style="background: #e74c3c; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">Close</button>
    `;
    content.appendChild(header);

    // Errors
    if (validationResults.errors.length > 0) {
        const errorSection = createValidationSection('Errors', validationResults.errors, '#e74c3c', '❌');
        content.appendChild(errorSection);
    }

    // Warnings
    if (validationResults.warnings.length > 0) {
        const warningSection = createValidationSection('Warnings', validationResults.warnings, '#f39c12', '⚠️');
        content.appendChild(warningSection);
    }

    // Info
    if (validationResults.info.length > 0) {
        const infoSection = createValidationSection('Information', validationResults.info, '#3498db', 'ℹ️');
        content.appendChild(infoSection);
    }

    // All good message
    if (validationResults.errors.length === 0 && validationResults.warnings.length === 0) {
        const allGood = document.createElement('div');
        allGood.style.cssText = 'text-align: center; padding: 40px; background: #d4edda; border-radius: 8px; color: #155724;';
        allGood.innerHTML = `
            <div style="font-size: 48px; margin-bottom: 10px;">✅</div>
            <h3>Drawing is compliant!</h3>
            <p>No errors or warnings found. AS/NZS 3000 compliance checks passed.</p>
        `;
        content.appendChild(allGood);
    }

    modal.appendChild(content);
    document.body.appendChild(modal);
}

function createValidationSection(title, items, color, icon) {
    const section = document.createElement('div');
    section.style.cssText = `margin-bottom: 20px; border-left: 4px solid ${color}; background: #f8f9fa; padding: 15px; border-radius: 4px;`;

    const sectionTitle = document.createElement('h3');
    sectionTitle.style.cssText = `margin: 0 0 15px 0; color: ${color};`;
    sectionTitle.innerHTML = `${icon} ${title} (${items.length})`;
    section.appendChild(sectionTitle);

    items.forEach(item => {
        const itemDiv = document.createElement('div');
        itemDiv.style.cssText = 'background: white; padding: 12px; margin-bottom: 10px; border-radius: 4px; font-size: 13px;';
        itemDiv.innerHTML = `
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <strong>${item.code}: ${item.message}</strong>
                <span style="background: ${color}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">${item.severity.toUpperCase()}</span>
            </div>
            ${item.standard ? `<div style="color: #7f8c8d; font-size: 11px; margin-bottom: 5px;">📋 ${item.standard}</div>` : ''}
            ${item.fix ? `<div style="color: #27ae60; font-size: 11px;">💡 Fix: ${item.fix}</div>` : ''}
        `;
        section.appendChild(itemDiv);
    });

    return section;
}

function closeValidationPanel() {
    const panel = document.getElementById('validationPanel');
    if (panel) {
        panel.remove();
    }
}

// Auto-start validation when CAD is initialized
setTimeout(() => {
    if (typeof canvas !== 'undefined' && canvas) {
        startValidation();
    }
}, 2000);
