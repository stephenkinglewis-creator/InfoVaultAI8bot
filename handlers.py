from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import os
import re
from datetime import datetime
import logging

from database import Database
from utils import Utils

logger = logging.getLogger(__name__)

class Handlers:
    def __init__(self, db: Database, utils: Utils):
        self.db = db
        self.utils = utils
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        await self.db.create_user(user.id, user.username, user.first_name)
        
        welcome_text = f"""
🤖 **Welcome to InfoVault AI, {user.first_name}!**

Your personal second brain for Telegram. I'll help you store, organize, and retrieve all your important information.

📚 **What I can do:**
• Store all your messages, images, documents, and files
• Extract text from images using OCR
• Generate summaries of documents
• Convert images to PDF
• Search your stored information
• Export your data

🔍 **Commands:**
/start - Show this welcome message
/help - Show help menu
/search <query> - Search your vault
/categories - Manage categories
/addcategory <name> - Add a new category
/recent - Show recent messages
/export - Export your data
/stats - Show storage statistics
/pdf - Convert images to PDF
/generatepdf - Generate PDF from uploaded images

Start by sending me any message, image, or document to save it!
"""
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🔍 **InfoVault AI Help**

**Saving Content:**
• Send any message to save it
• Send images, documents, videos, or audio files
• Use #hashtags in messages for auto-tagging

**Organizing Content:**
• /categories - View your categories
• /addcategory <name> - Add a new category

**Searching & Retrieving:**
• /search <query> - Find content
• /recent - See recent messages

**Export & Management:**
• /export - Download your data
• /stats - See your storage usage
• /pdf - Create PDFs from images

**Tips:**
• Use categories and tags for better organization
• All data is stored in memory (resets on restart)
"""
        await update.message.reply_text(help_text)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all incoming messages"""
        user = update.effective_user
        message = update.message
        
        await self.db.create_user(user.id, user.username, user.first_name)
        
        message_data = {
            "message_id": message.message_id,
            "chat_id": message.chat_id,
            "type": "text",
            "has_file": False
        }
        
        # Extract text
        if message.text:
            message_data["text"] = message.text
            
            # Check for hashtags
            tags = re.findall(r'#(\w+)', message.text)
            if tags:
                message_data["tags"] = tags
                await self.db.add_tags(user.id, tags)
        
        # Handle photos
        if message.photo:
            message_data["type"] = "photo"
            message_data["has_file"] = True
            photo = message.photo[-1]
            message_data["file_id"] = photo.file_id
            message_data["file_size"] = photo.file_size
            
            # Download and process
            file = await context.bot.get_file(photo.file_id)
            file_path = f"uploads/photo_{message.message_id}_{user.id}.jpg"
            await file.download_to_drive(file_path)
            
            extracted_text = await self.utils.extract_text_from_image(file_path)
            if extracted_text:
                message_data["extracted_text"] = extracted_text
                message_data["text"] = message_data.get("text", "") + "\n\n[OCR]:\n" + extracted_text
            
            await self.db.save_file(user.id, {
                "filename": f"photo_{message.message_id}.jpg",
                "file_type": "image",
                "file_size": photo.file_size,
                "file_id": photo.file_id,
                "extracted_text": extracted_text
            })
            
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Handle documents
        elif message.document:
            message_data["type"] = "document"
            message_data["has_file"] = True
            doc = message.document
            message_data["file_id"] = doc.file_id
            message_data["file_size"] = doc.file_size
            message_data["filename"] = doc.file_name
            
            file = await context.bot.get_file(doc.file_id)
            file_path = f"uploads/doc_{message.message_id}_{user.id}_{doc.file_name}"
            await file.download_to_drive(file_path)
            
            ext = os.path.splitext(doc.file_name)[1].lower()
            
            if ext == '.pdf':
                extracted_text = await self.utils.extract_text_from_pdf(file_path)
                if extracted_text:
                    message_data["extracted_text"] = extracted_text
                    if len(extracted_text) > 100:
                        message_data["summary"] = await self.utils.generate_summary(extracted_text)
            
            await self.db.save_file(user.id, {
                "filename": doc.file_name,
                "file_type": "document",
                "file_size": doc.file_size,
                "file_id": doc.file_id,
                "extracted_text": message_data.get("extracted_text", ""),
                "summary": message_data.get("summary", "")
            })
            
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Handle voice
        elif message.voice:
            message_data["type"] = "voice"
            message_data["has_file"] = True
            voice = message.voice
            message_data["file_id"] = voice.file_id
            message_data["file_size"] = voice.file_size
            
            await self.db.save_file(user.id, {
                "filename": f"voice_{message.message_id}.ogg",
                "file_type": "audio",
                "file_size": voice.file_size,
                "file_id": voice.file_id
            })
        
        # Handle video
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
        
        # Save message
        await self.db.save_message(user.id, message_data)
        
        # Send confirmation
        response = "✅ Message saved!"
        if message_data.get("extracted_text"):
            response += f"\n\n📝 Extracted:\n{message_data['extracted_text'][:150]}..."
        elif message_data.get("summary"):
            response += f"\n\n📊 Summary:\n{message_data['summary']}"
        
        await update.message.reply_text(response)
    
    async def search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command"""
        user = update.effective_user
        query = ' '.join(context.args)
        
        if not query:
            await update.message.reply_text("🔍 Please provide a search query.\nExample: /search hello")
            return
        
        results = await self.db.search_messages(user.id, query)
        
        if not results:
            await update.message.reply_text("🔍 No results found.")
            return
        
        response = f"🔍 *Results for:* {query}\n\n"
        for i, msg in enumerate(results[:5], 1):
            content = msg.get('content', '')[:150]
            if len(msg.get('content', '')) > 150:
                content += "..."
            timestamp = msg.get('timestamp', '')[:16]
            response += f"{i}. {content}\n   📅 {timestamp}\n\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /categories command"""
        user = update.effective_user
        categories = await self.db.get_categories(user.id)
        
        if not categories:
            await update.message.reply_text("📁 No categories yet.\nUse /addcategory <name> to add one.")
            return
        
        response = "📁 *Your Categories*\n\n"
        for cat in categories:
            response += f"• {cat}\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def add_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle adding a category"""
        user = update.effective_user
        category_name = ' '.join(context.args)
        
        if not category_name:
            await update.message.reply_text("Please specify a category name.\nExample: /addcategory Work")
            return
        
        await self.db.add_category(user.id, category_name)
        await update.message.reply_text(f"✅ Category '{category_name}' added!")
    
    async def recent(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /recent command"""
        user = update.effective_user
        messages = await self.db.get_user_messages(user.id, limit=10)
        
        if not messages:
            await update.message.reply_text("📭 No messages yet!")
            return
        
        response = "📋 *Recent Messages*\n\n"
        for msg in messages:
            timestamp = msg.get('timestamp', '')[:16]
            content = msg.get('content', '')[:80]
            if len(msg.get('content', '')) > 80:
                content += "..."
            response += f"• {timestamp}: {content}\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        user = update.effective_user
        stats = await self.db.get_user_stats(user.id)
        
        stats_text = f"""
📊 *Your InfoVault AI Stats*

📝 Total Messages: {stats['total_messages']}
📁 Total Files: {stats['total_files']}
💾 Storage Used: {await self.utils.format_file_size(stats['storage_used'])}
🏷️ Categories: {stats['categories']}
🔖 Tags: {stats['tags']}

💡 Quick Actions:
/recent - View recent messages
/search - Search your vault
/export - Export your data
"""
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    
    async def export(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /export command"""
        user = update.effective_user
        
        keyboard = [
            [
                InlineKeyboardButton("📄 JSON", callback_data="export_json"),
                InlineKeyboardButton("📝 TXT", callback_data="export_txt")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📤 *Export Your Data*\n\nChoose format:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def handle_export_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle export format selection"""
        query = update.callback_query
        await query.answer()
        
        user = update.effective_user
        format_type = query.data.replace('export_', '')
        
        data = await self.db.export_user_data(user.id, format_type)
        
        filename = f"vault_export_{user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format_type}"
        file_path = f"uploads/{filename}"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(data)
        
        with open(file_path, 'rb') as f:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=f,
                filename=filename
            )
        
        os.remove(file_path)
        await query.edit_message_text("✅ Data exported successfully!")
    
    async def pdf_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pdf command"""
        await update.message.reply_text(
            "📄 *Image to PDF Converter*\n\n"
            "1. Send one or more images\n"
            "2. Use /generatepdf to create the PDF\n\n"
            "The PDF will be sent to you and saved in your vault."
        )
    
    async def generate_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate PDF from images"""
        user = update.effective_user
        
        if 'images' not in context.user_data or not context.user_data['images']:
            await update.message.reply_text(
                "No images found. Send images first, then use /generatepdf"
            )
            return
        
        image_paths = []
        for file_id in context.user_data['images']:
            file = await context.bot.get_file(file_id)
            path = f"uploads/image_{user.id}_{len(image_paths)}.jpg"
            await file.download_to_drive(path)
            image_paths.append(path)
        
        pdf_path = await self.utils.create_pdf_from_images(image_paths)
        
        if pdf_path:
            await self.db.save_pdf(user.id, {
                "filename": f"pdf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                "pdf_id": pdf_path,
                "source_images": image_paths,
                "file_size": os.path.getsize(pdf_path)
            })
            
            with open(pdf_path, 'rb') as f:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=f,
                    filename=f"pdf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                )
            
            await update.message.reply_text("✅ PDF generated and saved!")
            
            # Cleanup
            context.user_data['images'] = []
            for path in image_paths:
                if os.path.exists(path):
                    os.remove(path)
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        else:
            await update.message.reply_text("❌ Failed to generate PDF.")
    
    async def handle_photo_for_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photos for PDF creation"""
        if 'images' not in context.user_data:
            context.user_data['images'] = []
        
        photo = update.message.photo[-1]
        context.user_data['images'].append(photo.file_id)
        
        await update.message.reply_text(
            f"✅ Image {len(context.user_data['images'])} added.\n"
            "Send more or use /generatepdf"
        )
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel current operation"""
        context.user_data['images'] = []
        await update.message.reply_text("Operation cancelled.")
