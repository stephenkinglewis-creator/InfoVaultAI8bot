from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, mongo_uri: str, db_name: str):
        self.client = AsyncIOMotorClient(mongo_uri)
        self.db = self.client[db_name]
        
        # Collections
        self.users = self.db.users
        self.messages = self.db.messages
        self.files = self.db.files
        self.pdfs = self.db.pdfs
        self.categories = self.db.categories
        self.tags = self.db.tags
        
    async def create_indexes(self):
        """Create necessary indexes for better performance"""
        try:
            await self.messages.create_index([("user_id", 1), ("timestamp", -1)])
            await self.files.create_index([("user_id", 1), ("filename", 1)])
            await self.pdfs.create_index([("user_id", 1), ("created_at", -1)])
            await self.users.create_index("user_id", unique=True)
        except Exception as e:
            logger.error(f"Index creation error: {e}")
        
    async def create_user(self, user_id: int, username: str = None, first_name: str = None):
        """Create a new user if they don't exist"""
        user = await self.users.find_one({"user_id": user_id})
        if not user:
            user_data = {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "created_at": datetime.utcnow(),
                "settings": {
                    "auto_summary": True,
                    "ocr_enabled": True,
                    "language": "en"
                },
                "storage_used": 0,
                "total_messages": 0,
                "total_files": 0
            }
            await self.users.insert_one(user_data)
            return user_data
        return user
    
    async def save_message(self, user_id: int, message_data: Dict[str, Any]):
        """Save a message to the database"""
        message = {
            "user_id": user_id,
            "message_id": message_data.get('message_id'),
            "chat_id": message_data.get('chat_id'),
            "content": message_data.get('text', ''),
            "message_type": message_data.get('type', 'text'),
            "timestamp": datetime.utcnow(),
            "metadata": message_data.get('metadata', {}),
            "has_file": message_data.get('has_file', False),
            "file_id": message_data.get('file_id'),
            "category": message_data.get('category', 'general'),
            "tags": message_data.get('tags', []),
            "summary": message_data.get('summary', '')
        }
        result = await self.messages.insert_one(message)
        
        # Update user stats
        await self.users.update_one(
            {"user_id": user_id},
            {"$inc": {"total_messages": 1}}
        )
        
        return result
    
    async def get_user_messages(self, user_id: int, limit: int = 50, skip: int = 0):
        """Get messages for a user with pagination"""
        cursor = self.messages.find({"user_id": user_id}).sort("timestamp", -1).skip(skip).limit(limit)
        messages = await cursor.to_list(length=limit)
        return messages
    
    async def search_messages(self, user_id: int, query: str, limit: int = 20):
        """Search messages using text search"""
        try:
            cursor = self.messages.find(
                {"user_id": user_id, "$text": {"$search": query}}
            ).sort("timestamp", -1).limit(limit)
            messages = await cursor.to_list(length=limit)
            return messages
        except:
            # If text search fails, fallback to simple search
            cursor = self.messages.find({
                "user_id": user_id,
                "content": {"$regex": query, "$options": "i"}
            }).sort("timestamp", -1).limit(limit)
            messages = await cursor.to_list(length=limit)
            return messages
    
    async def save_file(self, user_id: int, file_data: Dict[str, Any]):
        """Save file information"""
        file = {
            "user_id": user_id,
            "filename": file_data.get('filename'),
            "file_type": file_data.get('file_type'),
            "file_size": file_data.get('file_size', 0),
            "file_id": file_data.get('file_id'),
            "uploaded_at": datetime.utcnow(),
            "metadata": file_data.get('metadata', {}),
            "category": file_data.get('category', 'general'),
            "tags": file_data.get('tags', []),
            "extracted_text": file_data.get('extracted_text', ''),
            "summary": file_data.get('summary', '')
        }
        result = await self.files.insert_one(file)
        
        # Update user stats
        await self.users.update_one(
            {"user_id": user_id},
            {"$inc": {"total_files": 1, "storage_used": file_data.get('file_size', 0)}}
        )
        
        return result
    
    async def get_user_files(self, user_id: int, file_type: str = None, limit: int = 20):
        """Get files for a user"""
        query = {"user_id": user_id}
        if file_type:
            query["file_type"] = file_type
        
        cursor = self.files.find(query).sort("uploaded_at", -1).limit(limit)
        files = await cursor.to_list(length=limit)
        return files
    
    async def save_pdf(self, user_id: int, pdf_data: Dict[str, Any]):
        """Save PDF information"""
        pdf = {
            "user_id": user_id,
            "filename": pdf_data.get('filename'),
            "pdf_id": pdf_data.get('pdf_id'),
            "source_images": pdf_data.get('source_images', []),
            "created_at": datetime.utcnow(),
            "file_size": pdf_data.get('file_size', 0),
            "metadata": pdf_data.get('metadata', {}),
            "category": pdf_data.get('category', 'pdfs'),
            "tags": pdf_data.get('tags', [])
        }
        result = await self.pdfs.insert_one(pdf)
        return result
    
    async def add_category(self, user_id: int, category_name: str):
        """Add a category for a user"""
        category = {
            "user_id": user_id,
            "name": category_name,
            "created_at": datetime.utcnow()
        }
        await self.categories.update_one(
            {"user_id": user_id, "name": category_name},
            {"$set": category},
            upsert=True
        )
        return category
    
    async def get_categories(self, user_id: int):
        """Get all categories for a user"""
        cursor = self.categories.find({"user_id": user_id})
        categories = await cursor.to_list(length=None)
        return categories
    
    async def add_tags(self, user_id: int, tags: List[str]):
        """Add tags for a user"""
        for tag in tags:
            tag_data = {
                "user_id": user_id,
                "name": tag,
                "created_at": datetime.utcnow()
            }
            await self.tags.update_one(
                {"user_id": user_id, "name": tag},
                {"$set": tag_data},
                upsert=True
            )
    
    async def export_user_data(self, user_id: int, format: str = 'json'):
        """Export all user data"""
        messages = await self.get_user_messages(user_id, limit=1000)
        files = await self.get_user_files(user_id, limit=1000)
        
        data = {
            "user_id": user_id,
            "export_date": datetime.utcnow().isoformat(),
            "messages": messages,
            "files": files,
            "total_messages": len(messages),
            "total_files": len(files)
        }
        
        if format == 'json':
            return json.dumps(data, default=str, indent=2)
        elif format == 'txt':
            text = f"InfoVault AI Export\nUser ID: {user_id}\nDate: {data['export_date']}\n\n"
            text += f"Total Messages: {len(messages)}\nTotal Files: {len(files)}\n\n"
            for msg in messages:
                text += f"---\n{msg.get('timestamp', '')}: {msg.get('content', '')}\n"
            return text
        
        return data
