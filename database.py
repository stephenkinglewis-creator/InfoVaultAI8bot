from datetime import datetime
from typing import Dict, List, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        """In-memory database - no external dependencies"""
        self.storage = {
            'users': {},
            'messages': {},
            'files': {},
            'pdfs': {},
            'categories': {},
            'tags': {}
        }
        self.counters = {
            'users': 0,
            'messages': 0,
            'files': 0,
            'pdfs': 0
        }
        logger.info("✅ Using in-memory storage")
    
    def _get_user_data(self, user_id: int):
        """Get or create user data structure"""
        if user_id not in self.storage['users']:
            self.storage['users'][user_id] = {
                'user_id': user_id,
                'messages': [],
                'files': [],
                'pdfs': [],
                'categories': [],
                'tags': [],
                'total_messages': 0,
                'total_files': 0,
                'storage_used': 0,
                'created_at': datetime.utcnow()
            }
        return self.storage['users'][user_id]
    
    async def create_user(self, user_id: int, username: str = None, first_name: str = None):
        """Create a new user if they don't exist"""
        user_data = self._get_user_data(user_id)
        if not user_data.get('username'):
            user_data.update({
                'username': username,
                'first_name': first_name,
                'created_at': datetime.utcnow()
            })
        return user_data
    
    async def save_message(self, user_id: int, message_data: Dict[str, Any]):
        """Save a message"""
        user_data = self._get_user_data(user_id)
        
        message = {
            'id': len(user_data['messages']) + 1,
            'user_id': user_id,
            'message_id': message_data.get('message_id'),
            'content': message_data.get('text', ''),
            'message_type': message_data.get('type', 'text'),
            'timestamp': datetime.utcnow().isoformat(),
            'has_file': message_data.get('has_file', False),
            'file_id': message_data.get('file_id'),
            'category': message_data.get('category', 'general'),
            'tags': message_data.get('tags', []),
            'summary': message_data.get('summary', '')
        }
        
        user_data['messages'].append(message)
        user_data['total_messages'] += 1
        
        return message
    
    async def get_user_messages(self, user_id: int, limit: int = 50, skip: int = 0):
        """Get messages for a user"""
        user_data = self._get_user_data(user_id)
        messages = user_data['messages']
        # Sort by timestamp descending
        messages = sorted(messages, key=lambda x: x.get('timestamp', ''), reverse=True)
        return messages[skip:skip+limit]
    
    async def search_messages(self, user_id: int, query: str, limit: int = 20):
        """Search messages"""
        user_data = self._get_user_data(user_id)
        results = []
        query_lower = query.lower()
        
        for msg in user_data['messages']:
            content = msg.get('content', '').lower()
            if query_lower in content:
                results.append(msg)
                if len(results) >= limit:
                    break
        
        return results
    
    async def save_file(self, user_id: int, file_data: Dict[str, Any]):
        """Save file information"""
        user_data = self._get_user_data(user_id)
        
        file_info = {
            'id': len(user_data['files']) + 1,
            'user_id': user_id,
            'filename': file_data.get('filename'),
            'file_type': file_data.get('file_type'),
            'file_size': file_data.get('file_size', 0),
            'file_id': file_data.get('file_id'),
            'uploaded_at': datetime.utcnow().isoformat(),
            'category': file_data.get('category', 'general'),
            'tags': file_data.get('tags', []),
            'extracted_text': file_data.get('extracted_text', ''),
            'summary': file_data.get('summary', '')
        }
        
        user_data['files'].append(file_info)
        user_data['total_files'] += 1
        user_data['storage_used'] += file_data.get('file_size', 0)
        
        return file_info
    
    async def get_user_files(self, user_id: int, file_type: str = None, limit: int = 20):
        """Get files for a user"""
        user_data = self._get_user_data(user_id)
        files = user_data['files']
        
        if file_type:
            files = [f for f in files if f.get('file_type') == file_type]
        
        files = sorted(files, key=lambda x: x.get('uploaded_at', ''), reverse=True)
        return files[:limit]
    
    async def save_pdf(self, user_id: int, pdf_data: Dict[str, Any]):
        """Save PDF information"""
        user_data = self._get_user_data(user_id)
        
        pdf_info = {
            'id': len(user_data['pdfs']) + 1,
            'user_id': user_id,
            'filename': pdf_data.get('filename'),
            'pdf_id': pdf_data.get('pdf_id'),
            'source_images': pdf_data.get('source_images', []),
            'created_at': datetime.utcnow().isoformat(),
            'file_size': pdf_data.get('file_size', 0),
            'category': pdf_data.get('category', 'pdfs'),
            'tags': pdf_data.get('tags', [])
        }
        
        user_data['pdfs'].append(pdf_info)
        return pdf_info
    
    async def add_category(self, user_id: int, category_name: str):
        """Add a category"""
        user_data = self._get_user_data(user_id)
        
        if category_name not in user_data['categories']:
            user_data['categories'].append(category_name)
        
        return category_name
    
    async def get_categories(self, user_id: int):
        """Get all categories"""
        user_data = self._get_user_data(user_id)
        return user_data['categories']
    
    async def add_tags(self, user_id: int, tags: List[str]):
        """Add tags"""
        user_data = self._get_user_data(user_id)
        
        for tag in tags:
            if tag not in user_data['tags']:
                user_data['tags'].append(tag)
    
    async def export_user_data(self, user_id: int, format: str = 'json'):
        """Export all user data"""
        user_data = self._get_user_data(user_id)
        
        data = {
            "user_id": user_id,
            "export_date": datetime.utcnow().isoformat(),
            "total_messages": user_data['total_messages'],
            "total_files": user_data['total_files'],
            "storage_used": user_data['storage_used'],
            "messages": user_data['messages'],
            "files": user_data['files'],
            "pdfs": user_data['pdfs'],
            "categories": user_data['categories'],
            "tags": user_data['tags']
        }
        
        if format == 'json':
            return json.dumps(data, default=str, indent=2)
        elif format == 'txt':
            text = f"InfoVault AI Export\nUser ID: {user_id}\nDate: {data['export_date']}\n\n"
            text += f"Total Messages: {data['total_messages']}\n"
            text += f"Total Files: {data['total_files']}\n"
            text += f"Storage Used: {data['storage_used']} bytes\n\n"
            text += "--- MESSAGES ---\n"
            for msg in data['messages']:
                text += f"{msg.get('timestamp')}: {msg.get('content')}\n"
            return text
        
        return data
    
    async def get_user_stats(self, user_id: int):
        """Get user statistics"""
        user_data = self._get_user_data(user_id)
        return {
            'total_messages': user_data['total_messages'],
            'total_files': user_data['total_files'],
            'storage_used': user_data['storage_used'],
            'categories': len(user_data['categories']),
            'tags': len(user_data['tags'])
        }
