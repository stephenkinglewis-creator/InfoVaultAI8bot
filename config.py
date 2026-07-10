import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram Bot
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    # MongoDB - Optional, will use local storage if not provided
    MONGODB_URI = os.getenv('MONGODB_URI')
    DB_NAME = os.getenv('DB_NAME', 'infovault_ai')
    
    # File Storage
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mp3', 'wav', 'pdf', 'doc', 'docx', 'txt']
    
    # OCR
    OCR_LANGUAGE = 'eng'
    
    # Security
    SESSION_EXPIRY = 3600  # 1 hour
    
    # Pagination
    ITEMS_PER_PAGE = 10
    
    # Upload Directories
    UPLOAD_DIR = 'uploads'
    PDF_DIR = 'pdfs'
    
    # Create directories if they don't exist
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(PDF_DIR, exist_ok=True)
