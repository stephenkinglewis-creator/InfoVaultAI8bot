from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import os
import asyncio
from datetime import datetime
import json
from typing import Dict, Any, List
import logging

from database import Database
from utils import Utils
from config import Config

logger = logging.getLogger(__name__)

# Conversation states
UPLOAD, ADD_TAGS, ADD_CATEGORY, SEARCH, EXPORT = range(5)

class Handlers:
    def __init__(self, db: Database, utils: Utils):
        self.db = db
        self.utils = utils
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        # Create user in database
        await self.db.create_user(
            user.id,
            user.username,
            user.first_name
        )
        
        welcome_text = f"""
🤖 Welcome to InfoVault AI, {user.first_name}!

Your personal second brain for Telegram. I'll help you store, organize, and retrieve all your important information.

📚 **What I can do:**
• Store all your messages, images, documents, and files
• Extract text from images using OCR
• Generate summaries of long documents
• Convert images to PDF
• Search your stored information using keywords or AI
• Organize content by categories and tags
• Export your data in multiple formats

🔍 **Commands:**
/start - Show this welcome message
/help - Show help menu
/store - Save current message to your vault
/search - Search your vault using keywords or AI
/categories - Manage categories
/tags - Manage tags
/recent - Show recent messages
/export - Export your data
/stats - Show storage statistics
/pdf - Convert images to PDF
/clear - Clear conversation

Start by sending me any message, image, or document to save it to your personal vault!
"""
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🔍 **InfoVault AI Help**

**Saving Content:**
• Send any message to save it
• Send images, documents, videos, or audio files
• Forward messages to save them
• Use /store to manually save current conversation

**Organizing Content:**
• Use /categories to manage categories
• Use /tags to add tags to messages
• Send #hashtags in messages for auto-tagging

**Searching & Retrieving:**
• Use /search to find content with keywords
• The AI can understand natural language queries
• Use /recent to see recent messages

**Export & Management:**
• Use /export to download your data
• Use /stats to see your storage usage
• Use /pdf to create PDFs from images

**Tips:**
• Add categories for better organization
• Use specific tags for easy retrieval
• You can search using natural language questions

Need help? Just ask me!
"""
        await update.message.reply_text(help_text)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all incoming messages"""
        user = update.effective_user
        message = update.message
        
        # Ensure user exists
        await self.db.create_user(user.id, user.username, user.first_name)
        
        # Process message based on type
        message_data = {
            "message_id": message.message_id,
            "chat_id": message.chat_id,
            "type": "text",
            "has_file": False
        }
        
        # Extract text content
        if message.text:
            message_data["text"] = message.text
            
            # Check for hashtags
            import re
            tags = re.findall(r'#(\w+)', message.text)
            if tags:
                message_data["tags"] = tags
                await self.db.add_tags(user.id, tags)
        
        # Handle different types of media
        if message.photo:
            message_data["type"] = "photo"
            message_data["has_file"] = True
            # Get the largest photo
            photo = message.photo[-1]
            message_data["file_id"] = photo.file_id
            message_data["file_size"] = photo.file_size
            
            # Download and process image
            file = await context.bot.get_file(photo.file_id)
            file_path = f"uploads/photo_{message.message_id}_{user.id}.jpg"
            await file.download_to_drive(file_path)
            
            # Extract text using OCR
            extracted_text = await self.utils.extract_text_from_image(file_path)
            if extracted_text:
                message_data["extracted_text"] = extracted_text
                message_data["text"] = message_data.get("text", "") + "\n\n[OCR Extracted]:\n" + extracted_text
            
            # Store file info
            await self.db.save_file(user.id, {
                "filename": f"photo_{message.message_id}.jpg",
                "file_type": "image",
                "file_size": photo.file_size,
                "file_id": photo.file_id,
                "extracted_text": extracted_text
            })
            
        elif message.document:
            message_data["type"] = "document"
            message_data["has_file"] = True
            doc = message.document
            message_data["file_id"] = doc.file_id
            message_data["file_size"] = doc.file_size
            message_data["filename"] = doc.file_name
            
            # Download document
            file = await context.bot.get_file(doc.file_id)
            file_path = f"uploads/doc_{message.message_id}_{user.id}_{doc.file_name}"
            await file.download_to_drive(file_path)
            
            # Process based on file type
            ext = os.path.splitext(doc.file_name)[1].lower()
            
            if ext == '.pdf':
                # Extract text from PDF
                extracted_text = await self.utils.extract_text_from_pdf(file_path)
                if extracted_text:
                    message_data["extracted_text"] = extracted_text
                
                # Generate summary
                if len(extracted_text) > 100:
                    summary = await self.utils.generate_summary(extracted_text)
                    message_data["summary"] = summary
            
            # Store file info
            await self.db.save_file(user.id, {
                "filename": doc.file_name,
                "file_type": "document",
                "file_size": doc.file_size,
                "file_id": doc.file_id,
                "extracted_text": message_data.get("extracted_text", ""),
                "summary": message_data.get("summary", "")
            })
        
        elif message.voice:
            message_data["type"] = "voice"
            message_data["has_file"] = True
            voice = message.voice
            message_data["file_id"] = voice.file_id
            message_data["file_size"] = voice.file_size
            
            # Store voice note info
            await self.db.save_file(user.id, {
                "filename": f"voice_{message.message_id}.ogg",
                "file_type": "audio",
                "file_size": voice.file_size,
                "file_id": voice.file_id
            })
        
        elif message.video:
            message_data["type"] = "video"
            message_data["has_file"] = True
            video = message.video
            message_data["file_id"] = video.file_id
            message_data["file_size"] = video.file_size
            
            await self.db.save_file(user.id, {
                "filename": f"video_{message.message_id}.mp4",
                "file_type": "video",
                "file_size": video.file_size,
                "file_id": video.file_id
            })
        
        # Save message to database
        await self.db.save_message(user.id, message_data)
        
        # Send confirmation
        response = "✅ Message saved to your vault!"
        
        if message_data.get("extracted_text"):
            response += "\n\n📝 Extracted text:\n" + message_data["extracted_text"][:200] + "..."
        elif message_data.get("summary"):
            response += "\n\n📊 Summary:\n" + message_data["summary"]
        
        await update.message.reply_text(response)
    
    async def search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command"""
        user = update.effective_user
        
        # If query provided in command, use it
        query = ' '.join(context.args)
        
        if query:
            await self.perform_search(update, context, query)
        else:
            await update.message.reply_text(
                "🔍 What would you like to search for?\n\n"
                "Send me your search query. You can use:\n"
                "- Keywords (e.g., 'project report')\n"
                "- Natural language (e.g., 'show me documents from last week')\n"
                "- Specific types (e.g., 'images', 'documents', 'pdfs')\n\n"
                "Or use /search <your query> directly."
            )
            return SEARCH
    
    async def perform_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
        """Perform the actual search"""
        user = update.effective_user
        
        # Get all user messages
        messages = await self.db.get_user_messages(user.id, limit=100)
        
        if not messages:
            await update.message.reply_text("📭 Your vault is empty. Start saving messages first!")
            return
        
        # Extract text from messages for searching
        texts = [msg.get('content', '') for msg in messages if msg.get('content')]
        
        if not texts:
            await update.message.reply_text("No text content found to search through.")
            return
        
        # Perform semantic search
        results = await self.utils.semantic_search(query, texts, top_k=10)
        
        if not results:
            await update.message.reply_text("🔍 No results found for your query. Try different keywords.")
            return
        
        # Format results
        response = f"🔍 *Search Results for:* {query}\n\n"
        
        for i, result in enumerate(results[:5], 1):
            score = result['score'] * 100
            text = result['text'][:200] + "..." if len(result['text']) > 200 else result['text']
            response += f"{i}. {text}\n   *Relevance:* {score:.0f}%\n\n"
        
        response += "\n💡 Use /recent to see all recent messages or try a different search."
        
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /categories command"""
        user = update.effective_user
        
        categories = await self.db.get_categories(user.id)
        
        if not categories:
            await update.message.reply_text(
                "📁 No categories yet.\n\n"
                "To add a category, use:\n"
                "/addcategory <category_name>\n\n"
                "You can also add categories to messages using #category in your messages."
            )
            return
        
        response = "📁 *Your Categories*\n\n"
        for cat in categories:
            response += f"• {cat['name']}\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def add_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle adding a category"""
        user = update.effective_user
        category_name = ' '.join(context.args)
        
        if not category_name:
            await update.message.reply_text("Please specify a category name.\nExample: /addcategory Work")
            return
        
        await self.db.add_category(user.id, category_name)
        await update.message.reply_text(f"✅ Category '{category_name}' added successfully!")
    
    async def recent(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /recent command"""
        user = update.effective_user
        
        messages = await self.db.get_user_messages(user.id, limit=10)
        
        if not messages:
            await update.message.reply_text("📭 No messages in your vault yet!")
            return
        
        response = "📋 *Recent Messages*\n\n"
        
        for msg in messages:
            timestamp = msg.get('timestamp', datetime.utcnow()).strftime("%Y-%m-%d %H:%M")
            content = msg.get('content', '')[:100]
            if len(msg.get('content', '')) > 100:
                content += "..."
            
            response += f"• {timestamp}: {content}\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        user = update.effective_user
        
        # Get user stats
        user_data = await self.db.users.find_one({"user_id": user.id})
        
        if not user_data:
            await update.message.reply_text("User not found. Start by sending a message!")
            return
        
        stats_text = f"""
📊 *Your InfoVault AI Statistics*

👤 User: {user_data.get('first_name', 'User')}
📝 Total Messages: {user_data.get('total_messages', 0)}
📁 Total Files: {user_data.get('total_files', 0)}
💾 Storage Used: {await self.utils.format_file_size(user_data.get('storage_used', 0))}
📅 Member Since: {user_data.get('created_at', datetime.utcnow()).strftime('%Y-%m-%d')}

🔍 *Quick Actions:*
• /recent - View recent messages
• /search - Search your vault
• /export - Export your data
"""
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    
    async def export(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /export command"""
        user = update.effective_user
        
        keyboard = [
            [
                InlineKeyboardButton("📄 JSON", callback_data="export_json"),
                InlineKeyboardButton("📝 TXT", callback_data="export_txt")
            ],
            [
                InlineKeyboardButton("📊 PDF", callback_data="export_pdf"),
                InlineKeyboardButton("📋 DOCX", callback_data="export_docx")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📤 *Export Your Data*\n\n"
            "Choose the format you want to export your data in:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def pdf_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pdf command"""
        await update.message.reply_text(
            "📄 *Image to PDF Converter*\n\n"
            "Send me one or more images and I'll convert them to a PDF.\n\n"
            "How to use:\n"
            "1. Send an image or multiple images\n"
            "2. Use /generatepdf after sending images\n"
            "3. I'll create a PDF and send it to you\n\n"
            "You can also use /my_pdfs to see all your generated PDFs."
        )
    
    async def generate_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate PDF from images in context"""
        user = update.effective_user
        
        # Get images from context
        if not hasattr(context.user_data, 'images'):
            context.user_data['images'] = []
        
        if not context.user_data['images']:
            await update.message.reply_text(
                "No images found. Send images first and use /generatepdf."
            )
            return
        
        # Download and process images
        image_paths = []
        for file_id in context.user_data['images']:
            file = await context.bot.get_file(file_id)
            path = f"uploads/image_{user.id}_{len(image_paths)}.jpg"
            await file.download_to_drive(path)
            image_paths.append(path)
        
        # Create PDF
        pdf_path = await self.utils.create_pdf_from_images(image_paths)
        
        if pdf_path:
            # Save PDF info to database
            await self.db.save_pdf(user.id, {
                "filename": f"pdf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                "pdf_id": pdf_path,
                "source_images": image_paths,
                "file_size": os.path.getsize(pdf_path)
            })
            
            # Send PDF
            with open(pdf_path, 'rb') as f:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=f,
                    filename=f"vault_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                )
            
            await update.message.reply_text("✅ PDF generated and saved to your vault!")
            
            # Clean up
            context.user_data['images'] = []
            for path in image_paths:
                if os.path.exists(path):
                    os.remove(path)
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        else:
            await update.message.reply_text("❌ Failed to generate PDF. Please try again.")
    
    async def handle_photo_for_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photos for PDF creation"""
        if 'images' not in context.user_data:
            context.user_data['images'] = []
        
        photo = update.message.photo[-1]
        context.user_data['images'].append(photo.file_id)
        
        await update.message.reply_text(
            f"✅ Image {len(context.user_data['images'])} added to PDF.\n"
            "Send more images or use /generatepdf to create the PDF."
        )
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel current operation"""
        await update.message.reply_text("Operation cancelled.")
        return ConversationHandler.END
