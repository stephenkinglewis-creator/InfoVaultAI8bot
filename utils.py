import os
import io
import pytesseract
from PIL import Image
import pdf2image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import hashlib
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import aiofiles
import logging

logger = logging.getLogger(__name__)

class Utils:
    def __init__(self):
        # Set Tesseract path if on Windows
        if os.name == 'nt':
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        
    async def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from image using OCR"""
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, lang='eng')
            return text.strip()
        except Exception as e:
            logger.error(f"OCR Error: {e}")
            return ""
    
    async def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF"""
        try:
            images = pdf2image.convert_from_path(pdf_path)
            text = ""
            for image in images:
                text += pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            return ""
    
    async def generate_summary(self, text: str, max_length: int = 500) -> str:
        """Generate summary of text (simple version)"""
        if len(text) < 100:
            return text
        
        # Simple summarization: take first few sentences
        sentences = text.split('.')
        if len(sentences) <= 3:
            return text
        
        summary = '. '.join(sentences[:3]) + '.'
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        
        return summary
    
    async def create_pdf_from_images(self, image_paths: List[str], output_path: str = None) -> str:
        """Create PDF from multiple images"""
        if not output_path:
            output_path = f"pdfs/pdf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        try:
            c = canvas.Canvas(output_path, pagesize=A4)
            
            for img_path in image_paths:
                img = Image.open(img_path)
                width, height = img.size
                
                # Calculate dimensions to fit on A4
                max_width = 595.28  # A4 width in points
                max_height = 841.89  # A4 height in points
                
                if width > max_width or height > max_height:
                    scale = min(max_width/width, max_height/height)
                    width = width * scale
                    height = height * scale
                
                # Center image on page
                x = (max_width - width) / 2
                y = (max_height - height) / 2
                
                c.drawImage(img_path, x, y, width=width, height=height)
                c.showPage()
            
            c.save()
            return output_path
        except Exception as e:
            logger.error(f"PDF creation error: {e}")
            return None
    
    async def format_file_size(self, size_bytes: int) -> str:
        """Format file size for display"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    async def hash_file(self, file_path: str) -> str:
        """Generate hash for file"""
        sha256_hash = hashlib.sha256()
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(8192):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
