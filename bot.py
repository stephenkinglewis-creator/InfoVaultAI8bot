import logging
import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)
from dotenv import load_dotenv

from config import Config
from database import Database
from utils import Utils
from handlers import Handlers

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
    try:
        # Check for bot token
        if not Config.BOT_TOKEN:
            logger.error("❌ BOT_TOKEN not found in environment variables!")
            logger.error("Please set BOT_TOKEN in .env file or Railway environment variables")
            return
        
        # Initialize
        logger.info("🚀 Starting InfoVault AI Bot...")
        db = Database()
        utils = Utils()
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
        application.add_handler(MessageHandler(filters.PHOTO, handlers.handle_photo_for_pdf))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
        application.add_handler(MessageHandler(filters.ATTACHMENT, handlers.handle_message))
        application.add_handler(MessageHandler(filters.Document.ALL, handlers.handle_message))
        application.add_handler(MessageHandler(filters.VOICE, handlers.handle_message))
        application.add_handler(MessageHandler(filters.VIDEO, handlers.handle_message))
        
        # Add callback query handler
        application.add_handler(CallbackQueryHandler(handlers.handle_export_callback, pattern="export_"))
        
        # Get bot info
        bot_info = application.bot.get_me()
        logger.info(f"✅ Bot is running! @{bot_info.username}")
        logger.info(f"📊 Using in-memory storage (data resets on restart)")
        
        # Start polling
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        raise

if __name__ == '__main__':
    main()
