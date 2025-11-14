/**
 * Cable Schedule Generator
 * Automatically generates cable schedules from CAD drawings
 * AS/NZS 3008.1.1 compliant
 */

async function generateCableSchedule() {
    console.log('📋 Generating cable schedule...');

    // Collect all wires/cables from canvas
    const cables = collectCablesFromCanvas();

    if (cables.length === 0) {
        alert('No cables/wires found on canvas. Draw some wiring first!');
        return;
    }

    // Analyze and categorize cables
    const cableSchedule = await analyzeCables(cables);

    // Display cable schedule
    displayCableSchedule(cableSchedule);
}

function collectCablesFromCanvas() {
    const cables = [];
    const objects = canvas.getObjects();

    objects.forEach((obj, index) => {
        if (obj.customType === 'line' || obj.customType === 'wire') {
            // Calculate cable length
            const length = calculateLineLength(obj);

            // Determine cable type from layer
            const cableType = getCableTypeFromLayer(obj.layer);

            cables.push({
                id: `C${index + 1}`,
                type: cableType,
                layer: obj.layer,
                length: length,
                x1: obj.x1 || obj.left,
                y1: obj.y1 || obj.top,
                x2: obj.x2 || (obj.left + obj.width),
                y2: obj.y2 || (obj.top + obj.height),
                stroke: obj.stroke,
                strokeWidth: obj.strokeWidth
            });
        }
    });

    return cables;
}

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

function getCableTypeFromLayer(layer) {
    const layerToCableType = {
        'POWER-WIRING-RED': 'Active (Live)',
        'NEUTRAL-WIRING-BLUE': 'Neutral',
        'GROUND-WIRING-GREEN': 'Earth/Ground',
        'WALLS-ARCHITECTURAL': 'Conduit/Tray'
    };

    return layerToCableType[layer] || 'General';
}

async function analyzeCables(cables) {
    // Group cables by type and size
    const cableGroups = {};

    cables.forEach(cable => {
        const key = `${cable.type}_${cable.strokeWidth}`;

        if (!cableGroups[key]) {
            cableGroups[key] = {
                type: cable.type,
                description: getCableDescription(cable),
                cables: [],
                totalLength: 0,
                size: estimateCableSize(cable),
                color: getCableColor(cable.type),
                voltage: 230,
                current_rating: 0
            };
        }

        cableGroups[key].cables.push(cable);
        cableGroups[key].totalLength += cable.length;
    });

    // Convert to array and add specifications
    const schedule = [];
    let itemNumber = 1;

    for (const key in cableGroups) {
        const group = cableGroups[key];

        // Estimate cable specifications
        const specs = await getCableSpecifications(group.size, group.type);

        schedule.push({
            item: itemNumber++,
            cable_type: group.type,
            description: group.description,
            size: group.size,
            cores: getCoreCount(group.type),
            color: group.color,
            quantity: Math.ceil(group.totalLength),
            unit: 'm',
            current_rating: specs.current_rating,
            voltage_rating: '450/750V',
            standard: 'AS/NZS 5000.1',
            installation: specs.installation_method,
            from: 'Distribution Board',
            to: 'Various Devices',
            route_length: group.totalLength.toFixed(1),
            cable_count: group.cables.length
        });
    }

    return schedule;
}

function getCableDescription(cable) {
    const descriptions = {
        'Active (Live)': 'Active conductor - Single core',
        'Neutral': 'Neutral conductor - Single core',
        'Earth/Ground': 'Earth conductor - Single core',
        'Conduit/Tray': 'Multi-core cable in conduit'
    };

    return descriptions[cable.type] || 'Electrical cable';
}

function estimateCableSize(cable) {
    // Estimate cable size based on stroke width
    if (cable.strokeWidth >= 4) return '4';
    if (cable.strokeWidth >= 3) return '2.5';
    return '1.5';
}

function getCableColor(cableType) {
    const colors = {
        'Active (Live)': 'Red or Brown',
        'Neutral': 'Blue',
        'Earth/Ground': 'Green/Yellow',
        'Conduit/Tray': 'As per standard'
    };

    return colors[cableType] || 'TBD';
}

function getCoreCount(cableType) {
    if (cableType === 'Conduit/Tray') return '3C+E';
    return '1C';
}

async function getCableSpecifications(size, type) {
    // Default specifications based on AS/NZS 3008.1.1
    const specs = {
        '1.5': { current_rating: 17.5, installation_method: 'Enclosed in conduit' },
        '2.5': { current_rating: 24, installation_method: 'Enclosed in conduit' },
        '4': { current_rating: 32, installation_method: 'Enclosed in conduit' },
        '6': { current_rating: 41, installation_method: 'Enclosed in conduit' },
        '10': { current_rating: 57, installation_method: 'Enclosed in conduit' }
    };

    return specs[size] || { current_rating: 20, installation_method: 'TBD' };
}

function displayCableSchedule(schedule) {
    // Create modal with cable schedule table
    const modal = document.createElement('div');
    modal.id = 'cableScheduleModal';
    modal.className = 'modal active';
    modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 10000; display: flex; align-items: center; justify-content: center;';

    const content = document.createElement('div');
    content.style.cssText = 'background: white; padding: 30px; border-radius: 8px; max-width: 95%; max-height: 90%; overflow: auto; color: black;';

    // Header
    const header = document.createElement('div');
    header.style.cssText = 'display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;';
    header.innerHTML = `
        <h2 style="margin: 0; color: #2C3E50;">📋 Cable Schedule</h2>
        <button onclick="closeCableSchedule()" style="background: #e74c3c; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">Close</button>
    `;
    content.appendChild(header);

    // Summary
    const totalLength = schedule.reduce((sum, item) => sum + parseFloat(item.route_length), 0);
    const totalCables = schedule.reduce((sum, item) => sum + item.cable_count, 0);

    const summary = document.createElement('div');
    summary.style.cssText = 'background: #f8f9fa; padding: 15px; border-radius: 4px; margin-bottom: 20px;';
    summary.innerHTML = `
        <p style="margin: 5px 0;"><strong>Total Cable Types:</strong> ${schedule.length}</p>
        <p style="margin: 5px 0;"><strong>Total Cable Runs:</strong> ${totalCables}</p>
        <p style="margin: 5px 0;"><strong>Total Length:</strong> ${totalLength.toFixed(1)}m</p>
        <p style="margin: 5px 0;"><strong>Standard:</strong> AS/NZS 3008.1.1, AS/NZS 5000.1</p>
    `;
    content.appendChild(summary);

    // Table
    const table = document.createElement('table');
    table.style.cssText = 'width: 100%; border-collapse: collapse; font-size: 13px;';
    table.innerHTML = `
        <thead>
            <tr style="background: #2C3E50; color: white;">
                <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">#</th>
                <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Cable Type</th>
                <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Description</th>
                <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">Size (mm²)</th>
                <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">Cores</th>
                <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">Color</th>
                <th style="padding: 10px; border: 1px solid #ddd; text-align: right;">Length (m)</th>
                <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">Runs</th>
                <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">Rating (A)</th>
                <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Installation</th>
            </tr>
        </thead>
        <tbody>
            ${schedule.map((item, idx) => `
                <tr style="background: ${idx % 2 === 0 ? '#f8f9fa' : 'white'};">
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${item.item}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">${item.cable_type}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; font-size: 11px;">${item.description}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;"><strong>${item.size}</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${item.cores}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${item.color}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right;"><strong>${item.route_length}</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${item.cable_count}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${item.current_rating}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; font-size: 11px;">${item.installation}</td>
                </tr>
            `).join('')}
        </tbody>
    `;
    content.appendChild(table);

    // Notes
    const notes = document.createElement('div');
    notes.style.cssText = 'margin-top: 20px; padding: 15px; background: #fff3cd; border-left: 4px solid #ffc107; font-size: 12px;';
    notes.innerHTML = `
        <p style="margin: 5px 0; font-weight: bold;">Installation Notes:</p>
        <ul style="margin: 5px 0 5px 20px;">
            <li>All cables to comply with AS/NZS 5000.1</li>
            <li>Minimum cable size 1.5mm² for lighting, 2.5mm² for power circuits</li>
            <li>All cables to be installed in approved conduit or cable tray</li>
            <li>Earth conductor to be continuous throughout installation</li>
            <li>Cable colors to comply with AS/NZS 3000 Table 3.8.1</li>
            <li>Allowances: Add 10% for terminations and bends</li>
        </ul>
    `;
    content.appendChild(notes);

    // Buttons
    const buttonRow = document.createElement('div');
    buttonRow.style.cssText = 'margin-top: 20px; display: flex; gap: 10px;';

    const exportBtn = document.createElement('button');
    exportBtn.textContent = '📄 Export to PDF';
    exportBtn.style.cssText = 'padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer;';
    exportBtn.onclick = () => exportCableScheduleToPDF(schedule);

    const printBtn = document.createElement('button');
    printBtn.textContent = '🖨️ Print';
    printBtn.style.cssText = 'padding: 10px 20px; background: #27ae60; color: white; border: none; border-radius: 4px; cursor: pointer;';
    printBtn.onclick = () => window.print();

    buttonRow.appendChild(exportBtn);
    buttonRow.appendChild(printBtn);
    content.appendChild(buttonRow);

    modal.appendChild(content);
    document.body.appendChild(modal);
}

function closeCableSchedule() {
    const modal = document.getElementById('cableScheduleModal');
    if (modal) {
        modal.remove();
    }
}

function exportCableScheduleToPDF(schedule) {
    alert('PDF export functionality coming soon!');
    console.log('Cable schedule data:', schedule);
}
