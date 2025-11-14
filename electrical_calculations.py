"""
Electrical Calculations Module
AS/NZS 3000:2018 Compliant

Provides circuit calculations for:
- Load analysis
- Wire sizing (cable selection)
- Voltage drop calculations
- Circuit breaker sizing
- RCD requirements
"""

import math


class ElectricalCalculator:
    """Professional electrical calculations following AS/NZS 3000 standards"""

    # Standard voltage in Australia/NZ
    NOMINAL_VOLTAGE = 230  # V (single phase)
    FREQUENCY = 50  # Hz

    # Cable resistance (ohms per km) for copper conductors at 75°C
    # AS/NZS 3008.1.1 Table 30
    CABLE_RESISTANCE = {
        '1.5': 14.8,   # 1.5mm²
        '2.5': 8.96,   # 2.5mm²
        '4': 5.49,     # 4mm²
        '6': 3.66,     # 6mm²
        '10': 2.14,    # 10mm²
        '16': 1.35,    # 16mm²
        '25': 0.868,   # 25mm²
        '35': 0.627,   # 35mm²
        '50': 0.444,   # 50mm²
        '70': 0.317,   # 70mm²
        '95': 0.235,   # 95mm²
        '120': 0.186,  # 120mm²
    }

    # Current carrying capacity (Amps) for copper in conduit/duct
    # AS/NZS 3008.1.1 Table 4 (Column 3 - 2 or 3 cables)
    CABLE_CURRENT_CAPACITY = {
        '1.5': 17.5,
        '2.5': 24,
        '4': 32,
        '6': 41,
        '10': 57,
        '16': 76,
        '25': 101,
        '35': 125,
        '50': 151,
        '70': 192,
        '95': 232,
        '120': 269,
    }

    # Maximum voltage drop: 5% for sub-circuits (AS/NZS 3000 Clause 2.2.2)
    MAX_VOLTAGE_DROP_PERCENT = 5.0
    MAX_VOLTAGE_DROP_VOLTS = NOMINAL_VOLTAGE * (MAX_VOLTAGE_DROP_PERCENT / 100)

    def __init__(self):
        pass

    def calculate_load(self, devices):
        """
        Calculate total load for a circuit

        Args:
            devices: List of device dicts with 'type', 'quantity', 'load' (watts)

        Returns:
            Dict with load_watts, load_amps, diversity_factor, design_load_amps
        """
        total_watts = 0
        for device in devices:
            qty = device.get('quantity', 1)
            load = device.get('load', device.get('loadEstimate', 0))
            total_watts += qty * load

        # Calculate current (assuming unity power factor for simplicity)
        load_amps = total_watts / self.NOMINAL_VOLTAGE

        # Apply diversity factor (AS/NZS 3000 Appendix C)
        diversity_factor = self._get_diversity_factor(devices)
        design_load_amps = load_amps * diversity_factor

        return {
            'total_load_watts': total_watts,
            'load_amps': load_amps,
            'diversity_factor': diversity_factor,
            'design_load_amps': design_load_amps,
            'nominal_voltage': self.NOMINAL_VOLTAGE
        }

    def _get_diversity_factor(self, devices):
        """
        Get diversity factor based on circuit type
        AS/NZS 3000 Appendix C

        For simplicity, using conservative factors:
        - Lighting: 0.9
        - Power outlets: 0.75
        - Fixed appliances: 1.0
        """
        device_types = [d.get('type', '').lower() for d in devices]

        if any('light' in t for t in device_types):
            return 0.9
        elif any('outlet' in t or 'socket' in t for t in device_types):
            return 0.75
        else:
            return 1.0  # Conservative for fixed appliances

    def size_cable(self, load_amps, length_meters, installation_method='conduit'):
        """
        Select appropriate cable size based on load and length

        Args:
            load_amps: Design load current (Amps)
            length_meters: Cable run length (meters)
            installation_method: Installation method (conduit, tray, etc.)

        Returns:
            Dict with cable_size, max_current, voltage_drop, compliant
        """
        # Find minimum cable size based on current capacity
        suitable_cables = []

        for size, capacity in self.CABLE_CURRENT_CAPACITY.items():
            if capacity >= load_amps:
                # Check voltage drop
                voltage_drop = self.calculate_voltage_drop(
                    load_amps, length_meters, size
                )

                suitable_cables.append({
                    'size': size,
                    'max_current': capacity,
                    'voltage_drop_volts': voltage_drop,
                    'voltage_drop_percent': (voltage_drop / self.NOMINAL_VOLTAGE) * 100,
                    'compliant': voltage_drop <= self.MAX_VOLTAGE_DROP_VOLTS
                })

        # Find the smallest compliant cable
        compliant_cables = [c for c in suitable_cables if c['compliant']]

        if compliant_cables:
            recommended = min(compliant_cables, key=lambda x: float(x['size']))
            return recommended
        elif suitable_cables:
            # Return smallest by current capacity (but not compliant with voltage drop)
            return min(suitable_cables, key=lambda x: float(x['size']))
        else:
            return {
                'size': 'ERROR',
                'max_current': 0,
                'voltage_drop_volts': 0,
                'voltage_drop_percent': 0,
                'compliant': False,
                'error': 'No cable size suitable for this load'
            }

    def calculate_voltage_drop(self, current_amps, length_meters, cable_size):
        """
        Calculate voltage drop for a cable run

        Args:
            current_amps: Load current (A)
            length_meters: Cable length (m)
            cable_size: Cable size (mm²) as string

        Returns:
            Voltage drop in volts
        """
        # Get cable resistance
        resistance_per_km = self.CABLE_RESISTANCE.get(cable_size, 0)

        if resistance_per_km == 0:
            return 0

        # Convert to resistance for this run (considering both conductors)
        # R = ρ * L / 1000  (for km to m conversion)
        # Two-way run = 2 * length
        total_resistance = (resistance_per_km * length_meters * 2) / 1000

        # Voltage drop = I * R
        voltage_drop = current_amps * total_resistance

        return voltage_drop

    def size_circuit_breaker(self, design_load_amps, cable_size):
        """
        Select appropriate circuit breaker size

        Args:
            design_load_amps: Design load current
            cable_size: Cable size selected

        Returns:
            Dict with breaker_rating, type, compliant
        """
        # Standard MCB ratings (AS/NZS 60898)
        standard_ratings = [6, 10, 16, 20, 25, 32, 40, 50, 63]

        # Get cable current capacity
        cable_capacity = self.CABLE_CURRENT_CAPACITY.get(cable_size, 0)

        # Breaker must be:
        # 1. >= design load
        # 2. <= cable capacity (to protect the cable)
        suitable_breakers = [
            r for r in standard_ratings
            if r >= design_load_amps and r <= cable_capacity
        ]

        if suitable_breakers:
            recommended_rating = min(suitable_breakers)
            return {
                'rating': recommended_rating,
                'type': 'MCB',
                'curve': 'C',  # Type C for general use
                'compliant': True,
                'standard': 'AS/NZS 60898'
            }
        else:
            return {
                'rating': None,
                'type': 'MCB',
                'curve': 'C',
                'compliant': False,
                'error': 'No suitable breaker found'
            }

    def check_rcd_requirement(self, circuit_type, location):
        """
        Check if RCD (safety switch) is required

        Args:
            circuit_type: Type of circuit (power, lighting, etc.)
            location: Location (bathroom, outdoor, etc.)

        Returns:
            Dict with required, type, sensitivity
        """
        # AS/NZS 3000 Clause 2.5.2 - RCD requirements

        # RCD required for:
        # - Socket outlets in wet areas
        # - All socket outlets (general requirement)
        # - Outdoor circuits
        # - Socket outlets in commercial kitchens

        requires_rcd = False
        sensitivity = 30  # mA (standard for personal protection)

        if 'socket' in circuit_type.lower() or 'outlet' in circuit_type.lower():
            requires_rcd = True

        if any(loc in location.lower() for loc in ['bathroom', 'outdoor', 'laundry', 'kitchen']):
            requires_rcd = True

        return {
            'required': requires_rcd,
            'type': 'RCD' if requires_rcd else None,
            'sensitivity': sensitivity if requires_rcd else None,
            'standard': 'AS/NZS 3000 Clause 2.5.2'
        }

    def generate_circuit_schedule(self, circuits):
        """
        Generate a complete circuit schedule for a panel

        Args:
            circuits: List of circuit dicts with devices, length, location

        Returns:
            List of circuit calculations with all parameters
        """
        schedule = []

        for idx, circuit in enumerate(circuits):
            circuit_no = circuit.get('circuit_number', idx + 1)
            description = circuit.get('description', f'Circuit {circuit_no}')
            devices = circuit.get('devices', [])
            length = circuit.get('length_meters', 20)
            location = circuit.get('location', 'general')

            # Calculate load
            load_calc = self.calculate_load(devices)

            # Size cable
            cable = self.size_cable(load_calc['design_load_amps'], length)

            # Size breaker
            breaker = self.size_circuit_breaker(
                load_calc['design_load_amps'],
                cable.get('size', '2.5')
            )

            # Check RCD requirement
            rcd = self.check_rcd_requirement(description, location)

            schedule.append({
                'circuit_number': circuit_no,
                'description': description,
                'load_watts': load_calc['total_load_watts'],
                'load_amps': round(load_calc['load_amps'], 2),
                'design_amps': round(load_calc['design_load_amps'], 2),
                'cable_size': cable.get('size', 'ERROR'),
                'cable_max_current': cable.get('max_current', 0),
                'voltage_drop_volts': round(cable.get('voltage_drop_volts', 0), 2),
                'voltage_drop_percent': round(cable.get('voltage_drop_percent', 0), 2),
                'breaker_rating': breaker.get('rating', 'ERROR'),
                'breaker_type': breaker.get('type', 'MCB'),
                'rcd_required': rcd['required'],
                'rcd_sensitivity': rcd['sensitivity'],
                'compliant': cable.get('compliant', False) and breaker.get('compliant', False),
                'length_meters': length
            })

        return schedule


# Convenience function for API use
def calculate_circuit(devices, length_meters=20, circuit_type='power', location='general'):
    """
    Calculate complete circuit parameters

    Args:
        devices: List of device dicts
        length_meters: Cable run length
        circuit_type: Type of circuit
        location: Installation location

    Returns:
        Dict with all circuit calculations
    """
    calc = ElectricalCalculator()

    load = calc.calculate_load(devices)
    cable = calc.size_cable(load['design_load_amps'], length_meters)
    breaker = calc.size_circuit_breaker(load['design_load_amps'], cable.get('size', '2.5'))
    rcd = calc.check_rcd_requirement(circuit_type, location)

    return {
        'load': load,
        'cable': cable,
        'breaker': breaker,
        'rcd': rcd,
        'compliant': cable.get('compliant', False) and breaker.get('compliant', False)
    }
