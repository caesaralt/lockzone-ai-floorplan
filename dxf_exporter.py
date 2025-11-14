"""
DXF Exporter for CAD Designer
Converts Fabric.js canvas objects to AutoCAD DXF format
Compliant with DXF R12 format for maximum compatibility
"""

import math
from datetime import datetime


class DXFExporter:
    """Generate DXF files from CAD drawing data"""

    def __init__(self):
        self.layers = []
        self.entities = []
        self.blocks = []
        self.handle_counter = 256  # Start handles from 256

    def generate_dxf(self, cad_data):
        """
        Generate DXF file from CAD session data

        Args:
            cad_data: Dictionary containing layers, objects, metadata

        Returns:
            String containing DXF file content
        """
        self.layers = cad_data.get('layers', [])
        canvas_objects = cad_data.get('objects', [])
        metadata = cad_data.get('metadata', {})

        # Parse canvas objects and convert to DXF entities
        for obj in canvas_objects:
            self._convert_object_to_entity(obj)

        # Build DXF file
        dxf_content = self._build_dxf()
        return dxf_content

    def _convert_object_to_entity(self, obj):
        """Convert a Fabric.js object to DXF entity"""
        obj_type = obj.get('type', obj.get('customType', 'unknown'))

        if obj_type == 'line' or obj_type == 'wire':
            self._add_line(obj)
        elif obj_type == 'rect' or obj_type == 'rectangle':
            self._add_rectangle(obj)
        elif obj_type == 'circle':
            self._add_circle(obj)
        elif obj_type == 'text' or obj_type == 'i-text':
            self._add_text(obj)
        elif obj_type == 'group':
            self._add_group(obj)
        elif obj_type == 'dimension':
            self._add_dimension(obj)
        elif obj_type == 'symbol':
            self._add_symbol(obj)

    def _add_line(self, obj):
        """Add LINE entity"""
        # Extract coordinates
        x1 = obj.get('x1', obj.get('left', 0))
        y1 = obj.get('y1', obj.get('top', 0))
        x2 = obj.get('x2', x1 + obj.get('width', 100))
        y2 = obj.get('y2', y1)

        layer = obj.get('layer', '0')

        entity = {
            'type': 'LINE',
            'layer': layer,
            'x1': x1,
            'y1': y1,
            'x2': x2,
            'y2': y2
        }
        self.entities.append(entity)

    def _add_rectangle(self, obj):
        """Add rectangle as 4 LWPOLYLINE entities"""
        left = obj.get('left', 0)
        top = obj.get('top', 0)
        width = obj.get('width', 100)
        height = obj.get('height', 100)
        layer = obj.get('layer', '0')

        # Create closed polyline for rectangle
        entity = {
            'type': 'LWPOLYLINE',
            'layer': layer,
            'closed': True,
            'vertices': [
                (left, top),
                (left + width, top),
                (left + width, top + height),
                (left, top + height)
            ]
        }
        self.entities.append(entity)

    def _add_circle(self, obj):
        """Add CIRCLE entity"""
        # Fabric.js stores circles differently
        left = obj.get('left', 0)
        top = obj.get('top', 0)
        radius = obj.get('radius', 50)
        layer = obj.get('layer', '0')

        # Center point
        cx = left + radius
        cy = top + radius

        entity = {
            'type': 'CIRCLE',
            'layer': layer,
            'cx': cx,
            'cy': cy,
            'radius': radius
        }
        self.entities.append(entity)

    def _add_text(self, obj):
        """Add TEXT entity"""
        text_content = obj.get('text', '')
        left = obj.get('left', 0)
        top = obj.get('top', 0)
        font_size = obj.get('fontSize', 12)
        layer = obj.get('layer', '0')
        angle = obj.get('angle', 0)

        entity = {
            'type': 'TEXT',
            'layer': layer,
            'x': left,
            'y': top,
            'height': font_size,
            'text': text_content,
            'rotation': angle
        }
        self.entities.append(entity)

    def _add_group(self, obj):
        """Add grouped objects"""
        objects = obj.get('objects', [])
        for sub_obj in objects:
            self._convert_object_to_entity(sub_obj)

    def _add_dimension(self, obj):
        """Add DIMENSION entity"""
        # DXF dimensions are complex, for now add as lines and text
        # TODO: Implement proper DIMENSION entity
        pass

    def _add_symbol(self, obj):
        """Add symbol as a BLOCK reference (INSERT)"""
        symbol_id = obj.get('symbolId', 'unknown')
        left = obj.get('left', 0)
        top = obj.get('top', 0)
        layer = obj.get('layer', '0')

        entity = {
            'type': 'INSERT',
            'layer': layer,
            'block_name': symbol_id,
            'x': left,
            'y': top,
            'scale_x': 1.0,
            'scale_y': 1.0,
            'rotation': obj.get('angle', 0)
        }
        self.entities.append(entity)

    def _build_dxf(self):
        """Build complete DXF file"""
        dxf = []

        # HEADER SECTION
        dxf.append("0\nSECTION\n2\nHEADER")
        dxf.append("9\n$ACADVER\n1\nAC1009")  # AutoCAD R12
        dxf.append("9\n$INSBASE\n10\n0.0\n20\n0.0\n30\n0.0")
        dxf.append("9\n$EXTMIN\n10\n0.0\n20\n0.0\n30\n0.0")
        dxf.append("9\n$EXTMAX\n10\n1000.0\n20\n1000.0\n30\n0.0")
        dxf.append("0\nENDSEC")

        # TABLES SECTION
        dxf.append("0\nSECTION\n2\nTABLES")

        # LAYER TABLE
        dxf.append("0\nTABLE\n2\nLAYER\n70\n{}".format(len(self.layers) + 1))

        # Default layer
        dxf.append("0\nLAYER\n2\n0\n70\n0\n62\n7\n6\nCONTINUOUS")

        # Add custom layers
        for layer in self.layers:
            layer_name = layer.get('name', 'LAYER')
            color = self._color_to_aci(layer.get('color', '#FFFFFF'))
            dxf.append(f"0\nLAYER\n2\n{layer_name}\n70\n0\n62\n{color}\n6\nCONTINUOUS")

        dxf.append("0\nENDTAB")

        # STYLE TABLE (for text)
        dxf.append("0\nTABLE\n2\nSTYLE\n70\n1")
        dxf.append("0\nSTYLE\n2\nSTANDARD\n70\n0\n40\n0.0\n41\n1.0\n50\n0.0\n71\n0\n42\n0.2\n3\ntxt\n4\n")
        dxf.append("0\nENDTAB")

        dxf.append("0\nENDSEC")

        # BLOCKS SECTION
        dxf.append("0\nSECTION\n2\nBLOCKS")
        # TODO: Add symbol blocks here
        dxf.append("0\nENDSEC")

        # ENTITIES SECTION
        dxf.append("0\nSECTION\n2\nENTITIES")

        for entity in self.entities:
            dxf.append(self._entity_to_dxf(entity))

        dxf.append("0\nENDSEC")

        # EOF
        dxf.append("0\nEOF")

        return "\n".join(dxf)

    def _entity_to_dxf(self, entity):
        """Convert entity dictionary to DXF string"""
        entity_type = entity['type']
        layer = entity.get('layer', '0')

        if entity_type == 'LINE':
            return (
                f"0\nLINE\n"
                f"8\n{layer}\n"
                f"10\n{entity['x1']}\n"
                f"20\n{entity['y1']}\n"
                f"30\n0.0\n"
                f"11\n{entity['x2']}\n"
                f"21\n{entity['y2']}\n"
                f"31\n0.0"
            )

        elif entity_type == 'CIRCLE':
            return (
                f"0\nCIRCLE\n"
                f"8\n{layer}\n"
                f"10\n{entity['cx']}\n"
                f"20\n{entity['cy']}\n"
                f"30\n0.0\n"
                f"40\n{entity['radius']}"
            )

        elif entity_type == 'LWPOLYLINE':
            vertices = entity['vertices']
            closed = entity.get('closed', False)
            poly_dxf = f"0\nLWPOLYLINE\n8\n{layer}\n90\n{len(vertices)}\n70\n{'1' if closed else '0'}\n"
            for x, y in vertices:
                poly_dxf += f"10\n{x}\n20\n{y}\n"
            return poly_dxf

        elif entity_type == 'TEXT':
            return (
                f"0\nTEXT\n"
                f"8\n{layer}\n"
                f"10\n{entity['x']}\n"
                f"20\n{entity['y']}\n"
                f"30\n0.0\n"
                f"40\n{entity['height']}\n"
                f"1\n{entity['text']}\n"
                f"50\n{entity.get('rotation', 0)}"
            )

        elif entity_type == 'INSERT':
            return (
                f"0\nINSERT\n"
                f"8\n{layer}\n"
                f"2\n{entity['block_name']}\n"
                f"10\n{entity['x']}\n"
                f"20\n{entity['y']}\n"
                f"30\n0.0\n"
                f"41\n{entity['scale_x']}\n"
                f"42\n{entity['scale_y']}\n"
                f"50\n{entity.get('rotation', 0)}"
            )

        return ""

    def _color_to_aci(self, hex_color):
        """Convert hex color to AutoCAD Color Index (ACI)"""
        # Simplified mapping - AutoCAD uses ACI 1-255
        color_map = {
            '#E74C3C': 1,  # Red
            '#3498DB': 5,  # Blue
            '#27AE60': 3,  # Green
            '#F39C12': 30, # Orange
            '#2C3E50': 8,  # Dark gray
            '#34495E': 8,  # Gray
        }
        return color_map.get(hex_color, 7)  # Default to white


def export_to_dxf(cad_data):
    """
    Main export function

    Args:
        cad_data: Dictionary with canvas_state, layers, metadata

    Returns:
        DXF file content as string
    """
    exporter = DXFExporter()

    # Extract objects from canvas state
    canvas_state = cad_data.get('canvas_state', {})
    objects = canvas_state.get('objects', [])

    # Prepare data for exporter
    export_data = {
        'layers': cad_data.get('layers', []),
        'objects': objects,
        'metadata': cad_data.get('metadata', {})
    }

    return exporter.generate_dxf(export_data)
