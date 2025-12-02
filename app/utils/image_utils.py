"""
Image processing utilities for PDF conversion and image handling.
"""

import io
import base64

try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def pdf_to_image_base64(pdf_path, page_num=0):
    """
    Convert PDF page to base64 image for Claude Vision API.
    
    Args:
        pdf_path: Path to the PDF file
        page_num: Page number to convert (0-indexed)
    
    Returns:
        Base64 encoded PNG image string
    
    Raises:
        ImportError: If PyMuPDF is not installed
    """
    if not FITZ_AVAILABLE:
        raise ImportError("PyMuPDF (fitz) is required for PDF conversion")
    
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    
    # Render at high resolution
    mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
    pix = page.get_pixmap(matrix=mat)
    
    # Convert to PNG bytes
    img_bytes = pix.tobytes("png")
    
    # Convert to base64
    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
    
    doc.close()
    return img_base64


def image_to_base64(image_path):
    """
    Convert image file to base64 string.
    
    Args:
        image_path: Path to the image file
    
    Returns:
        Base64 encoded PNG image string
    
    Raises:
        ImportError: If PIL is not installed
    """
    if not PIL_AVAILABLE:
        raise ImportError("PIL/Pillow is required for image conversion")
    
    with Image.open(image_path) as img:
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

