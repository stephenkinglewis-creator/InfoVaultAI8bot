import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ONLY Telegram Bot Token
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is required! Get it from @BotFather")
    
    # File Storage
    UPLOAD_DIR = 'uploads'
    PDF_DIR = 'pdfs'
    
    # Create directories
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(PDF_DIR, exist_ok=True)
