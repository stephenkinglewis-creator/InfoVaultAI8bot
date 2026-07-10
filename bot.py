import logging
import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler
)
from dotenv import load_dotenv

from config import Config
from database import Database
from utils import Utils
from handlers import Handlers, SEARCH

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Start the bot"""
    # Initialize database
    db = Database(Config.MONGODB_URI, Config.DB_NAME)
    
    # Initialize utilities
    utils = Utils()
    
    # Initialize handlers
    handlers = Handlers(db, utils)
    
    # Create application
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("help", handlers.help))
    application.add_handler(CommandHandler("search", handlers.search))
    application.add_handler(CommandHandler("categories", handlers.categories))
    application.add_handler(CommandHandler("addcategory", handlers.add_category))
    application.add_handler(CommandHandler("recent", handlers.recent))
    application.add_handler(CommandHandler("stats", handlers.stats))
    application.add_handler(CommandHandler("export", handlers.export))
    application.add_handler(CommandHandler("pdf", handlers.pdf_command))
    application.add_handler(CommandHandler("generatepdf", handlers.generate_pdf))
    application.add_handler(CommandHandler("cancel", handlers.cancel))
    
    # Add message handlers
    application.add_handler(MessageHandler(
        filters.PHOTO, handlers.handle_photo_for_pdf
    ))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handlers.handle_message
    ))
    application.add_handler(MessageHandler(
        filters.ATTACHMENT, handlers.handle_message
    ))
    application.add_handler(MessageHandler(
        filters.Document.ALL, handlers.handle_message
    ))
    application.add_handler(MessageHandler(
        filters.VOICE, handlers.handle_message
    ))
    application.add_handler(MessageHandler(
        filters.VIDEO, handlers.handle_message
    ))
    
    # Add callback query handler for export buttons
    application.add_handler(CallbackQueryHandler(handlers.handle_export_callback, pattern="export_"))
    
    # Start bot
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
