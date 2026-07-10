import os
import io
import pytesseract
from PIL import Image
import pdf2image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.utils import ImageReader
import hashlib
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import aiofiles
import logging
from transformers import pipeline
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

logger = logging.getLogger(__name__)

class Utils:
    def __init__(self):
        # Initialize AI models
        self.summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        self.embeddings_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.ocr_initialized = False
        
        # Set Tesseract path (adjust for your system)
        if os.name == 'nt':  # Windows
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
        """Generate summary of text"""
        if len(text) < 100:
            return text
        
        try:
            # Truncate text if too long
            if len(text) > 2000:
                text = text[:2000]
            
            summary = self.summarizer(
                text,
                max_length=min(max_length, 200),
                min_length=30,
                do_sample=False
            )
            return summary[0]['summary_text'] if summary else text
        except Exception as e:
            logger.error(f"Summary error: {e}")
            return text[:max_length] + "..."
    
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
    
    async def generate_embeddings(self, text: str) -> np.ndarray:
        """Generate embeddings for text"""
        return self.embeddings_model.encode([text])[0]
    
    async def semantic_search(self, query: str, texts: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """Perform semantic search using embeddings"""
        if not texts:
            return []
        
        # Generate query embedding
        query_embedding = self.embeddings_model.encode([query])
        
        # Generate text embeddings
        text_embeddings = self.embeddings_model.encode(texts)
        
        # Create FAISS index
        dim = text_embeddings.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(text_embeddings)
        
        # Search
        distances, indices = index.search(query_embedding, min(top_k, len(texts)))
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(texts):
                results.append({
                    "text": texts[idx],
                    "score": float(1 / (1 + distances[0][i]))  # Convert distance to similarity score
                })
        
        return results
    
    async def hash_file(self, file_path: str) -> str:
        """Generate hash for file"""
        sha256_hash = hashlib.sha256()
        async with aiofiles.open(file_path, 'rb') as f:
            for chunk in await f.read():
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    async def format_file_size(self, size_bytes: int) -> str:
        """Format file size for display"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    async def extract_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from file"""
        import os
        from datetime import datetime
        
        metadata = {
            "filename": os.path.basename(file_path),
            "file_size": os.path.getsize(file_path),
            "created_at": datetime.fromtimestamp(os.path.getctime(file_path)).isoformat(),
            "modified_at": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
        }
        
        # Extract additional metadata based on file type
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in ['.jpg', '.jpeg', '.png', '.gif']:
            try:
                img = Image.open(file_path)
                metadata.update({
                    "width": img.width,
                    "height": img.height,
                    "format": img.format
                })
            except:
                pass
        
        return metadata
