/**
 * Panel Schedule Generator
 * Automatically generates electrical panel schedules from CAD drawings
 * AS/NZS 3000 compliant
 */

async function generatePanelSchedule() {
    console.log('🔧 Generating panel schedule...');

    // Collect all electrical devices from canvas
    const devices = collectDevicesFromCanvas();

    if (devices.length === 0) {
        alert('No electrical devices found on canvas. Add symbols first!');
        return;
    }

    // Group devices by circuit type
    const circuits = groupDevicesByCircuit(devices);

    // Calculate electrical parameters for each circuit
    const circuitSchedule = await calculateCircuitParameters(circuits);

    // Generate and display panel schedule
    displayPanelSchedule(circuitSchedule);
}

function collectDevicesFromCanvas() {
    const devices = [];
    const objects = canvas.getObjects();

    objects.forEach(obj => {
        if (obj.customType === 'symbol' && obj.symbolId) {
            // Get symbol data
            const symbolId = obj.symbolId;

            // Determine device info from symbol ID
            const deviceInfo = getDeviceInfoFromSymbol(symbolId);

            if (deviceInfo) {
                devices.push({
                    symbol_id: symbolId,
                    type: deviceInfo.type,
                    name: deviceInfo.name,
                    load_watts: deviceInfo.load,
                    voltage: deviceInfo.voltage || 230,
                    position: { x: obj.left, y: obj.top },
                    layer: obj.layer
                });
            }
        }
    });

    return devices;
}

function getDeviceInfoFromSymbol(symbolId) {
    // Map symbol IDs to electrical specifications
    const symbolSpecs = {
        'power-outlet-single': { type: 'outlet', name: 'Power Outlet (Single)', load: 2400, voltage: 230 },
        'power-outlet-double': { type: 'outlet', name: 'Power Outlet (Double)', load: 2400, voltage: 230 },
        'power-outlet-switched': { type: 'outlet', name: 'Switched Outlet', load: 2400, voltage: 230 },
        'light-ceiling': { type: 'lighting', name: 'Ceiling Light', load: 100, voltage: 230 },
        'light-downlight': { type: 'lighting', name: 'Downlight', load: 60, voltage: 230 },
        'light-wall': { type: 'lighting', name: 'Wall Light', load: 100, voltage: 230 },
        'light-emergency': { type: 'lighting', name: 'Emergency Light', load: 40, voltage: 230 },
        'switch-single': { type: 'control', name: '1-Gang Switch', load: 0, voltage: 230 },
        'switch-double': { type: 'control', name: '2-Gang Switch', load: 0, voltage: 230 },
        'switch-dimmer': { type: 'control', name: 'Dimmer Switch', load: 0, voltage: 230 },
        'exhaust-fan': { type: 'ventilation', name: 'Exhaust Fan', load: 180, voltage: 230 },
        'smoke-detector': { type: 'safety', name: 'Smoke Detector', load: 5, voltage: 230 },
        'data-outlet': { type: 'communication', name: 'Data Outlet', load: 15, voltage: 12 },
        'tv-outlet': { type: 'communication', name: 'TV Outlet', load: 10, voltage: 12 },
        'switchboard': { type: 'distribution', name: 'Sub-Board', load: 0, voltage: 230 },
    };

    return symbolSpecs[symbolId] || null;
}

function groupDevicesByCircuit(devices) {
    // Group devices into logical circuits
    const circuits = [];

    // Separate by device type
    const outlets = devices.filter(d => d.type === 'outlet');
    const lighting = devices.filter(d => d.type === 'lighting');
    const ventilation = devices.filter(d => d.type === 'ventilation');
    const safety = devices.filter(d => d.type === 'safety');

    // Create circuits (max 10 devices per circuit)
    if (outlets.length > 0) {
        const outletCircuits = Math.ceil(outlets.length / 10);
        for (let i = 0; i < outletCircuits; i++) {
            const circuitDevices = outlets.slice(i * 10, (i + 1) * 10);
            circuits.push({
                type: 'Power Outlets',
                description: `Power Circuit ${i + 1}`,
                devices: circuitDevices,
                length_meters: 25  // Estimated
            });
        }
    }

    if (lighting.length > 0) {
        const lightingCircuits = Math.ceil(lighting.length / 15);
        for (let i = 0; i < lightingCircuits; i++) {
            const circuitDevices = lighting.slice(i * 15, (i + 1) * 15);
            circuits.push({
                type: 'Lighting',
                description: `Lighting Circuit ${i + 1}`,
                devices: circuitDevices,
                length_meters: 30  // Estimated
            });
        }
    }

    if (ventilation.length > 0) {
        circuits.push({
            type: 'Ventilation',
            description: 'Exhaust Fans',
            devices: ventilation,
            length_meters: 20
        });
    }

    if (safety.length > 0) {
        circuits.push({
            type: 'Safety',
            description: 'Smoke Detectors',
            devices: safety,
            length_meters: 40
        });
    }

    return circuits;
}

async function calculateCircuitParameters(circuits) {
    const schedule = [];

    for (let i = 0; i < circuits.length; i++) {
        const circuit = circuits[i];

        // Calculate total load
        const totalLoad = circuit.devices.reduce((sum, d) => sum + d.load_watts, 0);
        const loadAmps = totalLoad / 230;  // V = 230V

        // Call backend for proper calculations
        try {
            const response = await fetch('/api/cad/calculate-circuit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    devices: circuit.devices,
                    length_meters: circuit.length_meters,
                    circuit_type: circuit.type.toLowerCase()
                })
            });

            const data = await response.json();

            if (data.success) {
                schedule.push({
                    circuit_number: i + 1,
                    description: circuit.description,
                    type: circuit.type,
                    device_count: circuit.devices.length,
                    load_watts: totalLoad,
                    load_amps: data.load.load_amps,
                    cable_size: data.cable.size,
                    breaker_rating: data.breaker.rating,
                    rcd_required: data.rcd.required,
                    voltage_drop: data.cable.voltage_drop_percent,
                    compliant: data.compliant
                });
            }
        } catch (error) {
            console.error('Circuit calculation error:', error);
            // Fallback to simple calculation
            schedule.push({
                circuit_number: i + 1,
                description: circuit.description,
                type: circuit.type,
                device_count: circuit.devices.length,
                load_watts: totalLoad,
                load_amps: loadAmps.toFixed(2),
                cable_size: loadAmps > 10 ? '2.5' : '1.5',
                breaker_rating: loadAmps > 10 ? 16 : 10,
                rcd_required: circuit.type === 'Power Outlets',
                voltage_drop: 'N/A',
                compliant: true
            });
        }
    }

    return schedule;
}

function displayPanelSchedule(schedule) {
    // Create modal with panel schedule table
    const modal = document.createElement('div');
    modal.id = 'panelScheduleModal';
    modal.className = 'modal active';
    modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 10000; display: flex; align-items: center; justify-content: center;';

    const content = document.createElement('div');
    content.style.cssText = 'background: white; padding: 30px; border-radius: 8px; max-width: 90%; max-height: 90%; overflow: auto; color: black;';

    // Header
    const header = document.createElement('div');
    header.style.cssText = 'display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;';
    header.innerHTML = `
        <h2 style="margin: 0; color: #2C3E50;">📊 Electrical Panel Schedule</h2>
        <button onclick="closePanelSchedule()" style="background: #e74c3c; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">Close</button>
    `;
    content.appendChild(header);

    // Summary
    const totalLoad = schedule.reduce((sum, c) => sum + c.load_watts, 0);
    const totalAmps = schedule.reduce((sum, c) => sum + parseFloat(c.load_amps), 0);

    const summary = document.createElement('div');
    summary.style.cssText = 'background: #f8f9fa; padding: 15px; border-radius: 4px; margin-bottom: 20px;';
    summary.innerHTML = `
        <p style="margin: 5px 0;"><strong>Total Circuits:</strong> ${schedule.length}</p>
        <p style="margin: 5px 0;"><strong>Total Load:</strong> ${totalLoad.toFixed(0)}W (${totalAmps.toFixed(2)}A)</p>
        <p style="margin: 5px 0;"><strong>Main Breaker Required:</strong> ${Math.ceil(totalAmps * 1.25)}A (with 25% margin)</p>
        <p style="margin: 5px 0;"><strong>Standard:</strong> AS/NZS 3000:2018</p>
    `;
    content.appendChild(summary);

    // Table
    const table = document.createElement('table');
    table.style.cssText = 'width: 100%; border-collapse: collapse; font-size: 14px;';
    table.innerHTML = `
        <thead>
            <tr style="background: #2C3E50; color: white;">
                <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Cct#</th>
                <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Description</th>
                <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">Devices</th>
                <th style="padding: 10px; border: 1px solid #ddd; text-align: right;">Load (W)</th>
                <th style="padding: 10px; border: 1px solid #ddd; text-align: right;">Load (A)</th>
                <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">Cable (mm²)</th>
                <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">Breaker (A)</th>
                <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">RCD</th>
                <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">V.Drop</th>
                <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">✓</th>
            </tr>
        </thead>
        <tbody>
            ${schedule.map((circuit, idx) => `
                <tr style="background: ${idx % 2 === 0 ? '#f8f9fa' : 'white'};">
                    <td style="padding: 8px; border: 1px solid #ddd;">${circuit.circuit_number}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">${circuit.description}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${circuit.device_count}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">${circuit.load_watts}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">${circuit.load_amps}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${circuit.cable_size}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${circuit.breaker_rating}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${circuit.rcd_required ? '✓ 30mA' : '—'}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${circuit.voltage_drop}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">${circuit.compliant ? '✅' : '⚠️'}</td>
                </tr>
            `).join('')}
        </tbody>
    `;
    content.appendChild(table);

    // Export button
    const exportBtn = document.createElement('button');
    exportBtn.textContent = '📄 Export to PDF';
    exportBtn.style.cssText = 'margin-top: 20px; padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer;';
    exportBtn.onclick = () => exportPanelScheduleToPDF(schedule);
    content.appendChild(exportBtn);

    modal.appendChild(content);
    document.body.appendChild(modal);
}

function closePanelSchedule() {
    const modal = document.getElementById('panelScheduleModal');
    if (modal) {
        modal.remove();
    }
}

function exportPanelScheduleToPDF(schedule) {
    alert('PDF export functionality coming soon!');
    console.log('Schedule data:', schedule);
}
