/**
 * Professional AS/NZS 3000 Electrical Symbol Library
 * SVG-based symbols for CAD Designer
 *
 * Standards compliance:
 * - AS/NZS 3000:2018 Electrical installations (Wiring Rules)
 * - AS/NZS 1100.101:1992 Technical drawing - Graphical symbols for electrotechnology
 */

const ELECTRICAL_SYMBOLS = {
    // ============================================
    // POWER OUTLETS
    // ============================================
    'power-outlet-single': {
        id: 'power-outlet-single',
        name: 'Power Outlet (Single)',
        category: 'outlets',
        width: 20,
        height: 20,
        svg: `<svg width="20" height="20" viewBox="0 0 20 20">
            <circle cx="10" cy="10" r="8" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <line x1="10" y1="4" x2="10" y2="7" stroke="currentColor" stroke-width="1.5"/>
            <line x1="10" y1="13" x2="10" y2="16" stroke="currentColor" stroke-width="1.5"/>
        </svg>`,
        description: 'Single phase power outlet 230V',
        standards: 'AS/NZS 3000',
        electrical: {
            voltage: 230,
            phases: 1,
            loadEstimate: 10 // Amps
        }
    },

    'power-outlet-double': {
        id: 'power-outlet-double',
        name: 'Power Outlet (Double)',
        category: 'outlets',
        width: 30,
        height: 20,
        svg: `<svg width="30" height="20" viewBox="0 0 30 20">
            <circle cx="8" cy="10" r="6" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <line x1="8" y1="5" x2="8" y2="7" stroke="currentColor" stroke-width="1.5"/>
            <line x1="8" y1="13" x2="8" y2="15" stroke="currentColor" stroke-width="1.5"/>
            <circle cx="22" cy="10" r="6" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <line x1="22" y1="5" x2="22" y2="7" stroke="currentColor" stroke-width="1.5"/>
            <line x1="22" y1="13" x2="22" y2="15" stroke="currentColor" stroke-width="1.5"/>
        </svg>`,
        description: 'Double power outlet 230V',
        standards: 'AS/NZS 3000',
        electrical: {
            voltage: 230,
            phases: 1,
            loadEstimate: 10
        }
    },

    'power-outlet-switched': {
        id: 'power-outlet-switched',
        name: 'Power Outlet (Switched)',
        category: 'outlets',
        width: 20,
        height: 25,
        svg: `<svg width="20" height="25" viewBox="0 0 20 25">
            <circle cx="10" cy="12" r="8" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <line x1="10" y1="6" x2="10" y2="9" stroke="currentColor" stroke-width="1.5"/>
            <line x1="10" y1="15" x2="10" y2="18" stroke="currentColor" stroke-width="1.5"/>
            <text x="10" y="4" font-size="6" text-anchor="middle" fill="currentColor">S</text>
        </svg>`,
        description: 'Switched power outlet 230V',
        standards: 'AS/NZS 3000',
        electrical: {
            voltage: 230,
            phases: 1,
            loadEstimate: 10
        }
    },

    // ============================================
    // LIGHTING
    // ============================================
    'light-ceiling': {
        id: 'light-ceiling',
        name: 'Ceiling Light',
        category: 'lighting',
        width: 20,
        height: 20,
        svg: `<svg width="20" height="20" viewBox="0 0 20 20">
            <circle cx="10" cy="10" r="7" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <line x1="3" y1="10" x2="6" y2="10" stroke="currentColor" stroke-width="1"/>
            <line x1="14" y1="10" x2="17" y2="10" stroke="currentColor" stroke-width="1"/>
            <line x1="10" y1="3" x2="10" y2="6" stroke="currentColor" stroke-width="1"/>
            <line x1="10" y1="14" x2="10" y2="17" stroke="currentColor" stroke-width="1"/>
        </svg>`,
        description: 'Ceiling mounted light fitting',
        standards: 'AS/NZS 3000',
        electrical: {
            voltage: 230,
            phases: 1,
            loadEstimate: 0.5 // Amps (LED)
        }
    },

    'light-downlight': {
        id: 'light-downlight',
        name: 'Downlight',
        category: 'lighting',
        width: 18,
        height: 18,
        svg: `<svg width="18" height="18" viewBox="0 0 18 18">
            <circle cx="9" cy="9" r="6" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <circle cx="9" cy="9" r="3" fill="currentColor"/>
        </svg>`,
        description: 'Recessed downlight',
        standards: 'AS/NZS 3000',
        electrical: {
            voltage: 230,
            phases: 1,
            loadEstimate: 0.3
        }
    },

    'light-wall': {
        id: 'light-wall',
        name: 'Wall Light',
        category: 'lighting',
        width: 20,
        height: 20,
        svg: `<svg width="20" height="20" viewBox="0 0 20 20">
            <circle cx="10" cy="10" r="7" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <line x1="3" y1="10" x2="6" y2="10" stroke="currentColor" stroke-width="1.5"/>
            <text x="10" y="13" font-size="6" text-anchor="middle" fill="currentColor">W</text>
        </svg>`,
        description: 'Wall mounted light fitting',
        standards: 'AS/NZS 3000',
        electrical: {
            voltage: 230,
            phases: 1,
            loadEstimate: 0.5
        }
    },

    'light-emergency': {
        id: 'light-emergency',
        name: 'Emergency Light',
        category: 'lighting',
        width: 22,
        height: 22,
        svg: `<svg width="22" height="22" viewBox="0 0 22 22">
            <circle cx="11" cy="11" r="8" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <line x1="4" y1="11" x2="7" y2="11" stroke="currentColor" stroke-width="1"/>
            <line x1="15" y1="11" x2="18" y2="11" stroke="currentColor" stroke-width="1"/>
            <line x1="11" y1="4" x2="11" y2="7" stroke="currentColor" stroke-width="1"/>
            <line x1="11" y1="15" x2="11" y2="18" stroke="currentColor" stroke-width="1"/>
            <text x="11" y="14" font-size="5" text-anchor="middle" fill="currentColor">EM</text>
        </svg>`,
        description: 'Emergency light with battery backup',
        standards: 'AS/NZS 3000, AS/NZS 2293',
        electrical: {
            voltage: 230,
            phases: 1,
            loadEstimate: 0.2
        }
    },

    // ============================================
    // SWITCHES
    // ============================================
    'switch-single': {
        id: 'switch-single',
        name: 'Switch (1-Gang)',
        category: 'switches',
        width: 20,
        height: 20,
        svg: `<svg width="20" height="20" viewBox="0 0 20 20">
            <rect x="3" y="3" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <text x="10" y="13" font-size="8" text-anchor="middle" fill="currentColor">S</text>
        </svg>`,
        description: 'Single gang light switch',
        standards: 'AS/NZS 3000',
        electrical: {
            voltage: 230,
            phases: 1,
            rating: 10 // Amps
        }
    },

    'switch-double': {
        id: 'switch-double',
        name: 'Switch (2-Gang)',
        category: 'switches',
        width: 30,
        height: 20,
        svg: `<svg width="30" height="20" viewBox="0 0 30 20">
            <rect x="3" y="3" width="24" height="14" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <line x1="15" y1="3" x2="15" y2="17" stroke="currentColor" stroke-width="1"/>
            <text x="9" y="13" font-size="6" text-anchor="middle" fill="currentColor">S</text>
            <text x="21" y="13" font-size="6" text-anchor="middle" fill="currentColor">S</text>
        </svg>`,
        description: 'Two gang light switch',
        standards: 'AS/NZS 3000',
        electrical: {
            voltage: 230,
            phases: 1,
            rating: 10
        }
    },

    'switch-triple': {
        id: 'switch-triple',
        name: 'Switch (3-Gang)',
        category: 'switches',
        width: 40,
        height: 20,
        svg: `<svg width="40" height="20" viewBox="0 0 40 20">
            <rect x="3" y="3" width="34" height="14" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <line x1="13.3" y1="3" x2="13.3" y2="17" stroke="currentColor" stroke-width="1"/>
            <line x1="26.6" y1="3" x2="26.6" y2="17" stroke="currentColor" stroke-width="1"/>
            <text x="8" y="12" font-size="5" text-anchor="middle" fill="currentColor">S</text>
            <text x="20" y="12" font-size="5" text-anchor="middle" fill="currentColor">S</text>
            <text x="32" y="12" font-size="5" text-anchor="middle" fill="currentColor">S</text>
        </svg>`,
        description: 'Three gang light switch',
        standards: 'AS/NZS 3000',
        electrical: {
            voltage: 230,
            phases: 1,
            rating: 10
        }
    },

    'switch-dimmer': {
        id: 'switch-dimmer',
        name: 'Dimmer Switch',
        category: 'switches',
        width: 20,
        height: 20,
        svg: `<svg width="20" height="20" viewBox="0 0 20 20">
            <rect x="3" y="3" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <text x="10" y="13" font-size="7" text-anchor="middle" fill="currentColor">D</text>
        </svg>`,
        description: 'Dimmer switch for lighting control',
        standards: 'AS/NZS 3000',
        electrical: {
            voltage: 230,
            phases: 1,
            rating: 10
        }
    },

    'switch-two-way': {
        id: 'switch-two-way',
        name: 'Switch (2-Way)',
        category: 'switches',
        width: 20,
        height: 20,
        svg: `<svg width="20" height="20" viewBox="0 0 20 20">
            <rect x="3" y="3" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <text x="10" y="10" font-size="6" text-anchor="middle" fill="currentColor">2</text>
            <text x="10" y="15" font-size="6" text-anchor="middle" fill="currentColor">W</text>
        </svg>`,
        description: 'Two-way switch for multi-point control',
        standards: 'AS/NZS 3000',
        electrical: {
            voltage: 230,
            phases: 1,
            rating: 10
        }
    },

    // ============================================
    // DISTRIBUTION & PROTECTION
    // ============================================
    'switchboard': {
        id: 'switchboard',
        name: 'Switchboard',
        category: 'distribution',
        width: 60,
        height: 80,
        svg: `<svg width="60" height="80" viewBox="0 0 60 80">
            <rect x="5" y="5" width="50" height="70" fill="none" stroke="currentColor" stroke-width="2"/>
            <line x1="5" y1="20" x2="55" y2="20" stroke="currentColor" stroke-width="1"/>
            <text x="30" y="15" font-size="8" text-anchor="middle" fill="currentColor">MSB</text>
            <rect x="10" y="25" width="15" height="20" fill="none" stroke="currentColor" stroke-width="1"/>
            <rect x="10" y="50" width="15" height="20" fill="none" stroke="currentColor" stroke-width="1"/>
            <rect x="35" y="25" width="15" height="20" fill="none" stroke="currentColor" stroke-width="1"/>
            <rect x="35" y="50" width="15" height="20" fill="none" stroke="currentColor" stroke-width="1"/>
        </svg>`,
        description: 'Main switchboard/distribution board',
        standards: 'AS/NZS 3000',
        electrical: {
            voltage: 230,
            phases: 1,
            mainRating: 63 // Amps
        }
    },

    'circuit-breaker': {
        id: 'circuit-breaker',
        name: 'Circuit Breaker',
        category: 'protection',
        width: 25,
        height: 35,
        svg: `<svg width="25" height="35" viewBox="0 0 25 35">
            <rect x="5" y="5" width="15" height="25" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <line x1="5" y1="15" x2="20" y2="15" stroke="currentColor" stroke-width="1"/>
            <line x1="5" y1="20" x2="20" y2="20" stroke="currentColor" stroke-width="1"/>
            <text x="12.5" y="13" font-size="6" text-anchor="middle" fill="currentColor">CB</text>
        </svg>`,
        description: 'Miniature circuit breaker (MCB)',
        standards: 'AS/NZS 3000, AS/NZS 60898',
        electrical: {
            voltage: 230,
            phases: 1,
            rating: 16, // Default, configurable
            breakingCapacity: 6000 // 6kA
        }
    },

    'rcd': {
        id: 'rcd',
        name: 'RCD',
        category: 'protection',
        width: 25,
        height: 35,
        svg: `<svg width="25" height="35" viewBox="0 0 25 35">
            <rect x="5" y="5" width="15" height="25" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <circle cx="12.5" cy="17.5" r="6" fill="none" stroke="currentColor" stroke-width="1"/>
            <text x="12.5" y="13" font-size="5" text-anchor="middle" fill="currentColor">RCD</text>
        </svg>`,
        description: 'Residual current device (safety switch)',
        standards: 'AS/NZS 3000, AS/NZS 61008',
        electrical: {
            voltage: 230,
            phases: 1,
            rating: 40, // Amps
            sensitivity: 30 // mA
        }
    },

    'rcbo': {
        id: 'rcbo',
        name: 'RCBO',
        category: 'protection',
        width: 25,
        height: 35,
        svg: `<svg width="25" height="35" viewBox="0 0 25 35">
            <rect x="5" y="5" width="15" height="25" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <line x1="5" y1="15" x2="20" y2="15" stroke="currentColor" stroke-width="1"/>
            <circle cx="12.5" cy="22" r="4" fill="none" stroke="currentColor" stroke-width="1"/>
            <text x="12.5" y="10" font-size="4" text-anchor="middle" fill="currentColor">RCBO</text>
        </svg>`,
        description: 'RCD with overcurrent protection',
        standards: 'AS/NZS 3000, AS/NZS 61009',
        electrical: {
            voltage: 230,
            phases: 1,
            rating: 16,
            sensitivity: 30
        }
    },

    // ============================================
    // COMMUNICATION OUTLETS
    // ============================================
    'data-outlet': {
        id: 'data-outlet',
        name: 'Data Outlet',
        category: 'communication',
        width: 20,
        height: 20,
        svg: `<svg width="20" height="20" viewBox="0 0 20 20">
            <rect x="3" y="5" width="14" height="10" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <line x1="6" y1="8" x2="6" y2="12" stroke="currentColor" stroke-width="1"/>
            <line x1="8.5" y1="8" x2="8.5" y2="12" stroke="currentColor" stroke-width="1"/>
            <line x1="11" y1="8" x2="11" y2="12" stroke="currentColor" stroke-width="1"/>
            <line x1="13.5" y1="8" x2="13.5" y2="12" stroke="currentColor" stroke-width="1"/>
            <text x="10" y="4" font-size="4" text-anchor="middle" fill="currentColor">DATA</text>
        </svg>`,
        description: 'Data outlet (Cat6/Cat6A)',
        standards: 'AS/NZS 3000, AS/CA S009',
        electrical: {
            type: 'low-voltage',
            category: 'Cat6A'
        }
    },

    'phone-outlet': {
        id: 'phone-outlet',
        name: 'Phone Outlet',
        category: 'communication',
        width: 20,
        height: 20,
        svg: `<svg width="20" height="20" viewBox="0 0 20 20">
            <circle cx="10" cy="10" r="7" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <path d="M 7 12 Q 7 8 10 8 Q 13 8 13 12" fill="none" stroke="currentColor" stroke-width="1"/>
            <text x="10" y="16" font-size="4" text-anchor="middle" fill="currentColor">TEL</text>
        </svg>`,
        description: 'Telephone outlet',
        standards: 'AS/NZS 3000, AS/CA S009',
        electrical: {
            type: 'low-voltage'
        }
    },

    'tv-outlet': {
        id: 'tv-outlet',
        name: 'TV Outlet',
        category: 'communication',
        width: 20,
        height: 20,
        svg: `<svg width="20" height="20" viewBox="0 0 20 20">
            <rect x="4" y="5" width="12" height="9" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <line x1="9" y1="14" x2="11" y2="14" stroke="currentColor" stroke-width="1.5"/>
            <line x1="7" y1="16" x2="13" y2="16" stroke="currentColor" stroke-width="1.5"/>
            <text x="10" y="11" font-size="5" text-anchor="middle" fill="currentColor">TV</text>
        </svg>`,
        description: 'TV antenna outlet',
        standards: 'AS/NZS 3000, AS/CA S009',
        electrical: {
            type: 'low-voltage'
        }
    },

    // ============================================
    // LOXONE DEVICES
    // ============================================
    'loxone-miniserver': {
        id: 'loxone-miniserver',
        name: 'Loxone Miniserver',
        category: 'loxone',
        width: 80,
        height: 60,
        svg: `<svg width="80" height="60" viewBox="0 0 80 60">
            <rect x="5" y="5" width="70" height="50" rx="3" fill="none" stroke="currentColor" stroke-width="2"/>
            <rect x="10" y="10" width="20" height="15" fill="currentColor" opacity="0.3"/>
            <circle cx="65" cy="17.5" r="3" fill="#00ff00"/>
            <text x="40" y="38" font-size="10" text-anchor="middle" fill="currentColor">Miniserver</text>
            <text x="40" y="48" font-size="6" text-anchor="middle" fill="currentColor">Gen 2</text>
        </svg>`,
        description: 'Loxone Miniserver Gen 2',
        standards: 'CE, Loxone',
        electrical: {
            voltage: 230,
            phases: 1,
            loadEstimate: 0.3,
            powerSupply: '24VDC'
        }
    },

    'loxone-extension': {
        id: 'loxone-extension',
        name: 'Loxone Extension',
        category: 'loxone',
        width: 60,
        height: 50,
        svg: `<svg width="60" height="50" viewBox="0 0 60 50">
            <rect x="5" y="5" width="50" height="40" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <rect x="10" y="10" width="15" height="10" fill="currentColor" opacity="0.3"/>
            <circle cx="48" cy="15" r="2" fill="#00ff00"/>
            <line x1="10" y1="25" x2="50" y2="25" stroke="currentColor" stroke-width="0.5"/>
            <text x="30" y="37" font-size="7" text-anchor="middle" fill="currentColor">Extension</text>
        </svg>`,
        description: 'Loxone Extension module',
        standards: 'CE, Loxone',
        electrical: {
            voltage: 24,
            type: 'DC',
            loadEstimate: 0.1
        }
    },

    'loxone-relay': {
        id: 'loxone-relay',
        name: 'Relay Extension',
        category: 'loxone',
        width: 60,
        height: 50,
        svg: `<svg width="60" height="50" viewBox="0 0 60 50">
            <rect x="5" y="5" width="50" height="40" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <rect x="12" y="12" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1"/>
            <rect x="26" y="12" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1"/>
            <rect x="40" y="12" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1"/>
            <text x="30" y="35" font-size="6" text-anchor="middle" fill="currentColor">Relay Ext</text>
        </svg>`,
        description: 'Loxone Relay Extension (14x relays)',
        standards: 'CE, Loxone',
        electrical: {
            voltage: 24,
            type: 'DC',
            relayRating: 16 // Amps per relay
        }
    },

    'loxone-dimmer': {
        id: 'loxone-dimmer',
        name: 'Dimmer Extension',
        category: 'loxone',
        width: 60,
        height: 50,
        svg: `<svg width="60" height="50" viewBox="0 0 60 50">
            <rect x="5" y="5" width="50" height="40" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <path d="M 15 15 L 20 25 L 15 25 Z" fill="currentColor" opacity="0.5"/>
            <path d="M 25 15 L 30 25 L 25 25 Z" fill="currentColor" opacity="0.7"/>
            <path d="M 35 15 L 40 25 L 35 25 Z" fill="currentColor" opacity="0.9"/>
            <text x="30" y="37" font-size="6" text-anchor="middle" fill="currentColor">Dimmer Ext</text>
        </svg>`,
        description: 'Loxone Dimmer Extension (4 channels)',
        standards: 'CE, Loxone',
        electrical: {
            voltage: 230,
            phases: 1,
            channelRating: 16 // Amps per channel
        }
    },

    // ============================================
    // SPECIALTY DEVICES
    // ============================================
    'smoke-detector': {
        id: 'smoke-detector',
        name: 'Smoke Detector',
        category: 'safety',
        width: 22,
        height: 22,
        svg: `<svg width="22" height="22" viewBox="0 0 22 22">
            <circle cx="11" cy="11" r="9" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <path d="M 8 8 Q 11 6 14 8 Q 11 10 8 8" fill="currentColor" opacity="0.5"/>
            <path d="M 8 12 Q 11 10 14 12 Q 11 14 8 12" fill="currentColor" opacity="0.5"/>
            <text x="11" y="20" font-size="4" text-anchor="middle" fill="currentColor">SD</text>
        </svg>`,
        description: 'Smoke detector (photoelectric)',
        standards: 'AS/NZS 3000, AS 3786',
        electrical: {
            voltage: 230,
            phases: 1,
            loadEstimate: 0.02
        }
    },

    'exhaust-fan': {
        id: 'exhaust-fan',
        name: 'Exhaust Fan',
        category: 'ventilation',
        width: 24,
        height: 24,
        svg: `<svg width="24" height="24" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <circle cx="12" cy="12" r="2" fill="currentColor"/>
            <path d="M 12 6 L 15 10 L 9 10 Z" fill="currentColor" opacity="0.7"/>
            <path d="M 18 12 L 14 15 L 14 9 Z" fill="currentColor" opacity="0.7"/>
            <path d="M 12 18 L 9 14 L 15 14 Z" fill="currentColor" opacity="0.7"/>
            <path d="M 6 12 L 10 9 L 10 15 Z" fill="currentColor" opacity="0.7"/>
        </svg>`,
        description: 'Exhaust fan (bathroom/kitchen)',
        standards: 'AS/NZS 3000',
        electrical: {
            voltage: 230,
            phases: 1,
            loadEstimate: 0.8
        }
    },

    'meter': {
        id: 'meter',
        name: 'Electricity Meter',
        category: 'distribution',
        width: 40,
        height: 50,
        svg: `<svg width="40" height="50" viewBox="0 0 40 50">
            <rect x="5" y="5" width="30" height="40" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/>
            <rect x="8" y="8" width="24" height="15" fill="currentColor" opacity="0.2"/>
            <text x="20" y="18" font-size="8" text-anchor="middle" fill="currentColor">kWh</text>
            <circle cx="12" cy="32" r="3" fill="none" stroke="currentColor" stroke-width="1"/>
            <circle cx="28" cy="32" r="3" fill="none" stroke="currentColor" stroke-width="1"/>
            <text x="20" y="43" font-size="5" text-anchor="middle" fill="currentColor">METER</text>
        </svg>`,
        description: 'Electricity meter (revenue grade)',
        standards: 'AS/NZS 3000, NMI',
        electrical: {
            voltage: 230,
            phases: 1,
            maxRating: 100
        }
    }
};

// Export for use in CAD Designer
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ELECTRICAL_SYMBOLS;
}
