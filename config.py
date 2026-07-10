import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram Bot
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    # MongoDB
    MONGODB_URI = os.getenv('MONGODB_URI')
    DB_NAME = os.getenv('DB_NAME', 'infovault_ai')
    
    # Redis (for caching)
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    # File Storage
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mp3', 'wav', 'pdf', 'doc', 'docx', 'txt']
    
    # AI Models
    OCR_LANGUAGE = 'eng'
    SUMMARY_MAX_LENGTH = 500
    SUMMARY_MIN_LENGTH = 100
    
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
