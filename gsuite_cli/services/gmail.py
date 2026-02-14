"""
Gmail service integration
"""

import logging
import base64
import mimetypes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from googleapiclient.errors import HttpError

from ..auth.oauth import OAuthManager
from ..utils.formatters import format_datetime, print_error, validate_email, truncate_text
from ..utils.cache import ServiceCache

logger = logging.getLogger(__name__)


class GmailService:
    """Gmail API service wrapper"""
    
    def __init__(self, oauth_manager: OAuthManager, cache_manager=None):
        self.oauth_manager = oauth_manager
        self.service = None
        self.cache = ServiceCache('gmail', cache_manager) if cache_manager else None
        self._initialize_service()
    
    def _initialize_service(self) -> bool:
        """Initialize the Gmail service"""
        try:
            self.service = self.oauth_manager.build_service('gmail', 'v1')
            return self.service is not None
        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {e}")
            return False
    
    def list_messages(self, 
                     query: str = '',
                     max_results: int = 50,
                     label_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """List email messages"""
        if not self.service:
            return []
        
        try:
            params = {
                'userId': 'me',
                'maxResults': max_results,
                'q': query
            }
            
            if label_ids:
                params['labelIds'] = label_ids
            
            result = self.service.users().messages().list(**params).execute()
            messages = result.get('messages', [])
            
            detailed_messages = []
            for message in messages:
                detail = self.get_message(message['id'], format='metadata')
                if detail:
                    detailed_messages.append(detail)
            
            return detailed_messages
        except HttpError as e:
            logger.error(f"Failed to list messages: {e}")
            print_error(f"Failed to list messages: {e}")
            return []
    
    def get_message(self, 
                   message_id: str, 
                   format: str = 'full') -> Optional[Dict[str, Any]]:
        """Get a specific email message"""
        if not self.service:
            return None
        
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format=format
            ).execute()
            
            # Extract headers
            headers = {}
            for header in message.get('payload', {}).get('headers', []):
                headers[header['name'].lower()] = header['value']
            
            # Extract body content
            body = self._extract_body(message.get('payload', {}))
            
            formatted_message = {
                'id': message.get('id'),
                'thread_id': message.get('threadId'),
                'subject': headers.get('subject', '(No subject)'),
                'from': headers.get('from', ''),
                'to': headers.get('to', ''),
                'date': headers.get('date', ''),
                'snippet': message.get('snippet', ''),
                'body': body,
                'label_ids': message.get('labelIds', []),
                'size_estimate': message.get('sizeEstimate', 0),
            }
            
            return formatted_message
        except HttpError as e:
            logger.error(f"Failed to get message {message_id}: {e}")
            print_error(f"Failed to get message: {e}")
            return None
    
    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Extract email body from payload"""
        if 'parts' in payload:
            # Multipart message
            body_parts = []
            for part in payload['parts']:
                if part['mimeType'].startswith('text/plain'):
                    data = part['body'].get('data', '')
                    if data:
                        body_parts.append(base64.urlsafe_b64decode(data).decode('utf-8'))
                elif part['mimeType'].startswith('text/html'):
                    # Prefer plain text, but use HTML if no plain text available
                    if not body_parts:
                        data = part['body'].get('data', '')
                        if data:
                            body_parts.append(base64.urlsafe_b64decode(data).decode('utf-8'))
            return '\n'.join(body_parts)
        else:
            # Single part message
            data = payload.get('body', {}).get('data', '')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8')
        return ''
    
    def send_message(self, 
                    to: str,
                    subject: str,
                    body: str,
                    cc: Optional[str] = None,
                    bcc: Optional[str] = None,
                    attachments: Optional[List[str]] = None,
                    html_body: Optional[str] = None) -> Optional[str]:
        """Send an email"""
        if not self.service:
            return None
        
        # Validate email addresses
        if not validate_email(to):
            print_error(f"Invalid recipient email: {to}")
            return None
        
        if cc and not validate_email(cc):
            print_error(f"Invalid CC email: {cc}")
            return None
        
        if bcc and not validate_email(bcc):
            print_error(f"Invalid BCC email: {bcc}")
            return None
        
        try:
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc
            
            # Add body
            if html_body:
                # HTML email
                message.attach(MIMEText(body, 'plain'))
                message.attach(MIMEText(html_body, 'html'))
            else:
                # Plain text email
                message.attach(MIMEText(body, 'plain'))
            
            # Add attachments
            if attachments:
                for file_path in attachments:
                    self._add_attachment(message, file_path)
            
            # Encode and send
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            result = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            message_id = result.get('id')
            logger.info(f"Message sent: {message_id}")
            return message_id
        except HttpError as e:
            logger.error(f"Failed to send message: {e}")
            print_error(f"Failed to send message: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create message: {e}")
            print_error(f"Failed to create message: {e}")
            return None
    
    def _add_attachment(self, message: MIMEMultipart, file_path: str) -> bool:
        """Add attachment to email"""
        try:
            path = Path(file_path)
            if not path.exists():
                print_error(f"Attachment file not found: {file_path}")
                return False
            
            # Guess MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type is None:
                mime_type = 'application/octet-stream'
            
            main_type, sub_type = mime_type.split('/', 1)
            
            with open(file_path, 'rb') as f:
                part = MIMEBase(main_type, sub_type)
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{path.name}"'
                )
                message.attach(part)
            
            return True
        except Exception as e:
            logger.error(f"Failed to add attachment {file_path}: {e}")
            print_error(f"Failed to add attachment: {e}")
            return False
    
    def search_messages(self, 
                       query: str,
                       max_results: int = 50) -> List[Dict[str, Any]]:
        """Search messages using Gmail search syntax"""
        return self.list_messages(query=query, max_results=max_results)
    
    def delete_message(self, message_id: str) -> bool:
        """Delete a message"""
        if not self.service:
            return False
        
        try:
            self.service.users().messages().delete(
                userId='me',
                id=message_id
            ).execute()
            
            logger.info(f"Message deleted: {message_id}")
            return True
        except HttpError as e:
            logger.error(f"Failed to delete message {message_id}: {e}")
            print_error(f"Failed to delete message: {e}")
            return False
    
    def batch_delete_messages(self, message_ids: List[str]) -> Dict[str, bool]:
        """Delete multiple messages"""
        results = {}
        for message_id in message_ids:
            results[message_id] = self.delete_message(message_id)
        return results
    
    def mark_as_read(self, message_id: str) -> bool:
        """Mark message as read"""
        if not self.service:
            return False
        
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            
            logger.info(f"Message marked as read: {message_id}")
            return True
        except HttpError as e:
            logger.error(f"Failed to mark message as read {message_id}: {e}")
            print_error(f"Failed to mark message as read: {e}")
            return False
    
    def mark_as_unread(self, message_id: str) -> bool:
        """Mark message as unread"""
        if not self.service:
            return False
        
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': ['UNREAD']}
            ).execute()
            
            logger.info(f"Message marked as unread: {message_id}")
            return True
        except HttpError as e:
            logger.error(f"Failed to mark message as unread {message_id}: {e}")
            print_error(f"Failed to mark message as unread: {e}")
            return False
    
    def get_labels(self) -> List[Dict[str, Any]]:
        """Get all Gmail labels"""
        if not self.service:
            return []
        
        try:
            result = self.service.users().labels().list(userId='me').execute()
            labels = result.get('labels', [])
            
            formatted_labels = []
            for label in labels:
                formatted_labels.append({
                    'id': label.get('id'),
                    'name': label.get('name'),
                    'type': label.get('type'),
                    'messages_total': label.get('messagesTotal', 0),
                    'messages_unread': label.get('messagesUnread', 0),
                    'threads_total': label.get('threadsTotal', 0),
                    'threads_unread': label.get('threadsUnread', 0),
                })
            
            return formatted_labels
        except HttpError as e:
            logger.error(f"Failed to get labels: {e}")
            print_error(f"Failed to get labels: {e}")
            return []
    
    def get_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get email thread"""
        if not self.service:
            return None
        
        try:
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id
            ).execute()
            
            messages = []
            for message in thread.get('messages', []):
                formatted_message = self.get_message(message['id'], format='full')
                if formatted_message:
                    messages.append(formatted_message)
            
            return {
                'id': thread.get('id'),
                'history_id': thread.get('historyId'),
                'messages': messages,
            }
        except HttpError as e:
            logger.error(f"Failed to get thread {thread_id}: {e}")
            print_error(f"Failed to get thread: {e}")
            return None
