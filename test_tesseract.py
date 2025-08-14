# test_tesseract.py
import pytesseract
from PIL import Image
import numpy as np

# Set the path (if needed)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Create a simple test image
img = Image.new('RGB', (200, 100), color='white')
from PIL import ImageDraw, ImageFont

draw = ImageDraw.Draw(img)
try:
    # Try to use default font
    draw.text((10, 40), "Test OCR", fill='black')
except:
    # Fallback if no font available
    pass

# Test OCR
try:
    text = pytesseract.image_to_string(img)
    print("✅ Tesseract is working!")
    print(f"Detected text: '{text.strip()}'")
except Exception as e:
    print(f"❌ Tesseract error: {e}")