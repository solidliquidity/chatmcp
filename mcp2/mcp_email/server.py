#!/usr/bin/env python3
"""
MCP Email Manager Server

A Model Context Protocol server for email management and client follow-up automation.
Supports both Gmail and Outlook/Microsoft Graph APIs for comprehensive email operations.
"""

import os
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass, asdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64

# Google API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False

# Microsoft Graph imports
try:
    import requests
    from msgraph.core import GraphSession
    OUTLOOK_AVAILABLE = True
except ImportError:
    OUTLOOK_AVAILABLE = False

from dotenv import load_dotenv
from email_validator import validate_email, EmailNotValidError
from dateutil import parser as date_parser

from mcp.server.fastmcp import FastMCP, Context


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """Email service configuration"""
    provider: str  # 'gmail' or 'outlook'
    credentials_path: str
    scopes: List[str]
    
    @classmethod
    def from_env(cls) -> "EmailConfig":
        """Create config from environment variables"""
        provider = os.getenv("EMAIL_PROVIDER", "gmail").lower()
        
        if provider == "gmail":
            return cls(
                provider="gmail",
                credentials_path=os.getenv("GMAIL_CREDENTIALS_PATH", "gmail_credentials.json"),
                scopes=['https://www.googleapis.com/auth/gmail.readonly',
                       'https://www.googleapis.com/auth/gmail.send',
                       'https://www.googleapis.com/auth/gmail.modify']
            )
        elif provider == "outlook":
            return cls(
                provider="outlook",
                credentials_path=os.getenv("OUTLOOK_CREDENTIALS_PATH", "outlook_credentials.json"),
                scopes=['https://graph.microsoft.com/Mail.Read',
                       'https://graph.microsoft.com/Mail.Send',
                       'https://graph.microsoft.com/Mail.ReadWrite']
            )
        else:
            raise ValueError(f"Unsupported email provider: {provider}")


@dataclass
class EmailMessage:
    """Email message data structure"""
    id: str
    subject: str
    sender: str
    recipients: List[str]
    date: datetime
    body: str
    is_read: bool
    has_attachments: bool
    folder: str
    thread_id: Optional[str] = None


@dataclass
class ClientTracker:
    """Client tracking information"""
    email: str
    name: str
    last_contacted: Optional[datetime]
    last_response: Optional[datetime]
    status: str  # 'pending', 'responded', 'overdue'
    follow_up_count: int
    notes: str


@dataclass
class AppContext:
    """Application context with email service"""
    email_config: EmailConfig
    gmail_service: Optional[Any] = None
    outlook_session: Optional[Any] = None


class EmailService:
    """Base email service interface"""
    
    def __init__(self, config: EmailConfig):
        self.config = config
    
    async def authenticate(self):
        """Authenticate with email service"""
        raise NotImplementedError
    
    async def get_folders(self) -> List[Dict[str, Any]]:
        """Get email folders/labels"""
        raise NotImplementedError
    
    async def search_emails(self, query: str, max_results: int = 50) -> List[EmailMessage]:
        """Search emails"""
        raise NotImplementedError
    
    async def send_email(self, to: List[str], subject: str, body: str, cc: List[str] = None, bcc: List[str] = None) -> Dict[str, Any]:
        """Send email"""
        raise NotImplementedError


class GmailService(EmailService):
    """Gmail API service implementation"""
    
    def __init__(self, config: EmailConfig):
        super().__init__(config)
        self.service = None
    
    async def authenticate(self):
        """Authenticate with Gmail API"""
        if not GMAIL_AVAILABLE:
            raise ImportError("Gmail dependencies not installed. Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        
        creds = None
        token_path = "gmail_token.json"
        
        # Load existing token
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, self.config.scopes)
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.config.credentials_path):
                    raise FileNotFoundError(f"Gmail credentials file not found: {self.config.credentials_path}")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.config.credentials_path, self.config.scopes
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail authentication successful")
    
    async def get_folders(self) -> List[Dict[str, Any]]:
        """Get Gmail labels"""
        try:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            return [
                {
                    "id": label['id'],
                    "name": label['name'],
                    "type": label.get('type', 'user'),
                    "message_count": label.get('messagesTotal', 0)
                }
                for label in labels
            ]
        except Exception as e:
            logger.error(f"Error getting Gmail labels: {e}")
            return []
    
    async def search_emails(self, query: str, max_results: int = 50) -> List[EmailMessage]:
        """Search Gmail messages"""
        try:
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            email_list = []
            
            for msg in messages:
                try:
                    message = self.service.users().messages().get(
                        userId='me', id=msg['id'], format='full'
                    ).execute()
                    
                    email_msg = self._parse_gmail_message(message)
                    if email_msg:
                        email_list.append(email_msg)
                        
                except Exception as e:
                    logger.warning(f"Error parsing message {msg['id']}: {e}")
                    continue
            
            return email_list
            
        except Exception as e:
            logger.error(f"Error searching Gmail: {e}")
            return []
    
    def _parse_gmail_message(self, message: Dict) -> Optional[EmailMessage]:
        """Parse Gmail message format"""
        try:
            headers = {h['name']: h['value'] for h in message['payload'].get('headers', [])}
            
            # Extract body
            body = ""
            if 'parts' in message['payload']:
                for part in message['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode('utf-8')
                            break
            else:
                data = message['payload']['body'].get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
            
            return EmailMessage(
                id=message['id'],
                subject=headers.get('Subject', '(No Subject)'),
                sender=headers.get('From', ''),
                recipients=headers.get('To', '').split(',') if headers.get('To') else [],
                date=date_parser.parse(headers.get('Date', '')),
                body=body,
                is_read='UNREAD' not in message.get('labelIds', []),
                has_attachments=any(part.get('filename') for part in message['payload'].get('parts', [])),
                folder=','.join(message.get('labelIds', [])),
                thread_id=message.get('threadId')
            )
            
        except Exception as e:
            logger.error(f"Error parsing Gmail message: {e}")
            return None
    
    async def send_email(self, to: List[str], subject: str, body: str, cc: List[str] = None, bcc: List[str] = None) -> Dict[str, Any]:
        """Send email via Gmail"""
        try:
            message = MIMEMultipart()
            message['to'] = ', '.join(to)
            message['subject'] = subject
            
            if cc:
                message['cc'] = ', '.join(cc)
            if bcc:
                message['bcc'] = ', '.join(bcc)
            
            message.attach(MIMEText(body, 'plain'))
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            result = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return {
                "success": True,
                "message_id": result['id'],
                "thread_id": result.get('threadId')
            }
            
        except Exception as e:
            logger.error(f"Error sending Gmail: {e}")
            return {"success": False, "error": str(e)}


class OutlookService(EmailService):
    """Microsoft Graph/Outlook service implementation"""
    
    def __init__(self, config: EmailConfig):
        super().__init__(config)
        self.session = None
        self.access_token = None
    
    async def authenticate(self):
        """Authenticate with Microsoft Graph"""
        if not OUTLOOK_AVAILABLE:
            raise ImportError("Outlook dependencies not installed. Install with: pip install msgraph-core requests")
        
        # Load credentials
        if not os.path.exists(self.config.credentials_path):
            raise FileNotFoundError(f"Outlook credentials file not found: {self.config.credentials_path}")
        
        with open(self.config.credentials_path, 'r') as f:
            creds = json.load(f)
        
        # Get access token (simplified - in production use proper OAuth flow)
        self.access_token = creds.get('access_token')
        if not self.access_token:
            raise ValueError("No access token found in Outlook credentials")
        
        self.session = GraphSession()
        logger.info("Outlook authentication successful")
    
    async def get_folders(self) -> List[Dict[str, Any]]:
        """Get Outlook mail folders"""
        try:
            headers = {'Authorization': f'Bearer {self.access_token}'}
            response = requests.get(
                'https://graph.microsoft.com/v1.0/me/mailFolders',
                headers=headers
            )
            
            if response.status_code == 200:
                folders = response.json().get('value', [])
                return [
                    {
                        "id": folder['id'],
                        "name": folder['displayName'],
                        "type": "system" if folder['displayName'] in ['Inbox', 'Sent Items', 'Drafts'] else "user",
                        "message_count": folder.get('totalItemCount', 0)
                    }
                    for folder in folders
                ]
            return []
            
        except Exception as e:
            logger.error(f"Error getting Outlook folders: {e}")
            return []
    
    async def search_emails(self, query: str, max_results: int = 50) -> List[EmailMessage]:
        """Search Outlook messages"""
        try:
            headers = {'Authorization': f'Bearer {self.access_token}'}
            params = {
                '$search': f'"{query}"',
                '$top': max_results,
                '$select': 'id,subject,sender,toRecipients,receivedDateTime,body,isRead,hasAttachments,parentFolderId,conversationId'
            }
            
            response = requests.get(
                'https://graph.microsoft.com/v1.0/me/messages',
                headers=headers,
                params=params
            )
            
            if response.status_code == 200:
                messages = response.json().get('value', [])
                return [self._parse_outlook_message(msg) for msg in messages]
            
            return []
            
        except Exception as e:
            logger.error(f"Error searching Outlook: {e}")
            return []
    
    def _parse_outlook_message(self, message: Dict) -> EmailMessage:
        """Parse Outlook message format"""
        try:
            return EmailMessage(
                id=message['id'],
                subject=message.get('subject', '(No Subject)'),
                sender=message.get('sender', {}).get('emailAddress', {}).get('address', ''),
                recipients=[r['emailAddress']['address'] for r in message.get('toRecipients', [])],
                date=date_parser.parse(message['receivedDateTime']),
                body=message.get('body', {}).get('content', ''),
                is_read=message.get('isRead', False),
                has_attachments=message.get('hasAttachments', False),
                folder=message.get('parentFolderId', ''),
                thread_id=message.get('conversationId')
            )
            
        except Exception as e:
            logger.error(f"Error parsing Outlook message: {e}")
            return None
    
    async def send_email(self, to: List[str], subject: str, body: str, cc: List[str] = None, bcc: List[str] = None) -> Dict[str, Any]:
        """Send email via Outlook"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            recipients = [{"emailAddress": {"address": email}} for email in to]
            cc_recipients = [{"emailAddress": {"address": email}} for email in (cc or [])]
            bcc_recipients = [{"emailAddress": {"address": email}} for email in (bcc or [])]
            
            email_data = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "Text",
                        "content": body
                    },
                    "toRecipients": recipients,
                    "ccRecipients": cc_recipients,
                    "bccRecipients": bcc_recipients
                }
            }
            
            response = requests.post(
                'https://graph.microsoft.com/v1.0/me/sendMail',
                headers=headers,
                json=email_data
            )
            
            if response.status_code == 202:
                return {"success": True, "message": "Email sent successfully"}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            logger.error(f"Error sending Outlook email: {e}")
            return {"success": False, "error": str(e)}


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle"""
    email_config = EmailConfig.from_env()
    
    # Initialize email service
    if email_config.provider == "gmail":
        service = GmailService(email_config)
    elif email_config.provider == "outlook":
        service = OutlookService(email_config)
    else:
        raise ValueError(f"Unsupported email provider: {email_config.provider}")
    
    try:
        await service.authenticate()
        logger.info(f"Successfully authenticated with {email_config.provider}")
    except Exception as e:
        logger.error(f"Failed to authenticate with {email_config.provider}: {e}")
        raise
    
    context = AppContext(email_config=email_config)
    if email_config.provider == "gmail":
        context.gmail_service = service
    else:
        context.outlook_session = service
    
    try:
        yield context
    finally:
        logger.info("Shutting down Email MCP server")


# Initialize FastMCP server
mcp = FastMCP(
    "Email Manager MCP Server",
    lifespan=app_lifespan
)


def get_email_service(ctx: AppContext) -> EmailService:
    """Get the appropriate email service from context"""
    if ctx.email_config.provider == "gmail":
        return ctx.gmail_service
    else:
        return ctx.outlook_session


# Resources - Email folder and message structures
@mcp.resource("email://folders")
def get_email_folders() -> str:
    """Get all email folders/labels"""
    ctx = mcp.get_context()
    service = get_email_service(ctx.request_context.lifespan_context)
    
    try:
        # This should be async, but FastMCP handles sync resources
        import asyncio
        folders = asyncio.run(service.get_folders())
        
        result = f"Email Folders ({ctx.request_context.lifespan_context.email_config.provider}):\n\n"
        for folder in folders:
            result += f"📁 {folder['name']} (ID: {folder['id']})\n"
            result += f"   Type: {folder['type']}\n"
            result += f"   Messages: {folder['message_count']}\n\n"
        
        return result
        
    except Exception as e:
        return f"Error retrieving email folders: {str(e)}"


@mcp.resource("email://folder/{folder_name}")
def get_folder_details(folder_name: str) -> str:
    """Get details about a specific email folder"""
    ctx = mcp.get_context()
    service = get_email_service(ctx.request_context.lifespan_context)
    
    try:
        import asyncio
        # Search for recent emails in the folder
        query = f"in:{folder_name}" if ctx.request_context.lifespan_context.email_config.provider == "gmail" else folder_name
        messages = asyncio.run(service.search_emails(query, max_results=10))
        
        result = f"Folder: {folder_name}\n"
        result += f"Recent messages ({len(messages)}):\n\n"
        
        for msg in messages:
            status = "📩" if not msg.is_read else "📧"
            attachment_icon = "📎" if msg.has_attachments else ""
            result += f"{status} {msg.subject} {attachment_icon}\n"
            result += f"   From: {msg.sender}\n"
            result += f"   Date: {msg.date.strftime('%Y-%m-%d %H:%M')}\n"
            result += f"   Preview: {msg.body[:100]}...\n\n"
        
        return result
        
    except Exception as e:
        return f"Error retrieving folder details: {str(e)}"


# Tools - Email operations and client management
@mcp.tool()
def search_emails(query: str, max_results: Optional[int] = 20) -> Dict[str, Any]:
    """
    Search emails with a query string.
    
    Args:
        query: Search query (subject, sender, content keywords)
        max_results: Maximum number of results to return (default: 20, max: 100)
    
    Returns:
        Dictionary with search results and metadata
    """
    ctx = mcp.get_context()
    service = get_email_service(ctx.request_context.lifespan_context)
    
    if max_results is None or max_results > 100:
        max_results = 100
    if max_results < 1:
        max_results = 1
    
    try:
        import asyncio
        messages = asyncio.run(service.search_emails(query, max_results))
        
        results = []
        for msg in messages:
            results.append({
                "id": msg.id,
                "subject": msg.subject,
                "sender": msg.sender,
                "recipients": msg.recipients,
                "date": msg.date.isoformat(),
                "is_read": msg.is_read,
                "has_attachments": msg.has_attachments,
                "body_preview": msg.body[:200] + "..." if len(msg.body) > 200 else msg.body,
                "folder": msg.folder,
                "thread_id": msg.thread_id
            })
        
        return {
            "results": results,
            "count": len(results),
            "query": query,
            "provider": ctx.request_context.lifespan_context.email_config.provider,
            "success": True
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "query": query,
            "success": False
        }


@mcp.tool()
def send_follow_up_email(
    to_email: str,
    client_name: str,
    subject: str,
    follow_up_type: str = "gentle",
    custom_message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send a follow-up email to a client.
    
    Args:
        to_email: Client's email address
        client_name: Client's name
        subject: Email subject
        follow_up_type: Type of follow-up ('gentle', 'reminder', 'urgent')
        custom_message: Custom message content (optional)
    
    Returns:
        Dictionary with send result
    """
    ctx = mcp.get_context()
    service = get_email_service(ctx.request_context.lifespan_context)
    
    # Validate email
    try:
        validate_email(to_email)
    except EmailNotValidError:
        return {"success": False, "error": "Invalid email address"}
    
    # Generate follow-up message based on type
    if custom_message:
        body = custom_message
    else:
        templates = {
            "gentle": f"""
Hi {client_name},

I hope this email finds you well. I wanted to follow up on our previous conversation regarding {subject}.

I understand you may be busy, but I'd appreciate any updates you might have. Please let me know if you need any additional information from my end.

Looking forward to hearing from you.

Best regards
""",
            "reminder": f"""
Hi {client_name},

I'm following up on my previous email regarding {subject}.

Could you please provide an update on this matter? If you need any clarification or additional information, please don't hesitate to reach out.

I'd appreciate your response at your earliest convenience.

Best regards
""",
            "urgent": f"""
Hi {client_name},

I hope you're doing well. I'm reaching out regarding {subject} which requires your urgent attention.

This matter is time-sensitive, and I would greatly appreciate your immediate response. If there are any concerns or questions, please let me know so we can address them promptly.

Thank you for your urgent consideration.

Best regards
"""
        }
        
        body = templates.get(follow_up_type, templates["gentle"])
    
    try:
        import asyncio
        result = asyncio.run(service.send_email(
            to=[to_email],
            subject=f"Follow-up: {subject}",
            body=body
        ))
        
        if result["success"]:
            return {
                "success": True,
                "message": f"Follow-up email sent to {client_name} ({to_email})",
                "follow_up_type": follow_up_type,
                "email_id": result.get("message_id")
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error sending email")
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
def track_client_status(client_email: str, status: str = "pending") -> Dict[str, Any]:
    """
    Track or update client status for follow-up management.
    
    Args:
        client_email: Client's email address
        status: Client status ('pending', 'responded', 'overdue', 'closed')
    
    Returns:
        Dictionary with tracking result
    """
    # In a real implementation, this would use a database or persistent storage
    # For now, we'll simulate tracking functionality
    
    valid_statuses = ["pending", "responded", "overdue", "closed"]
    if status not in valid_statuses:
        return {
            "success": False,
            "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        }
    
    try:
        validate_email(client_email)
    except EmailNotValidError:
        return {"success": False, "error": "Invalid email address"}
    
    # Simulate tracking storage
    tracking_info = {
        "client_email": client_email,
        "status": status,
        "last_updated": datetime.now().isoformat(),
        "follow_up_needed": status in ["pending", "overdue"]
    }
    
    return {
        "success": True,
        "message": f"Client status updated for {client_email}",
        "tracking_info": tracking_info
    }


@mcp.tool()
def find_overdue_clients(days_threshold: int = 7) -> Dict[str, Any]:
    """
    Find clients who haven't responded within the specified threshold.
    
    Args:
        days_threshold: Number of days to consider as overdue (default: 7)
    
    Returns:
        Dictionary with overdue clients list
    """
    ctx = mcp.get_context()
    service = get_email_service(ctx.request_context.lifespan_context)
    
    try:
        import asyncio
        
        # Search for sent emails in the last month
        cutoff_date = datetime.now() - timedelta(days=30)
        query = f"in:sent after:{cutoff_date.strftime('%Y/%m/%d')}"
        
        sent_messages = asyncio.run(service.search_emails(query, max_results=100))
        
        # Group by recipient and find those without recent responses
        client_tracking = {}
        overdue_threshold = datetime.now() - timedelta(days=days_threshold)
        
        for msg in sent_messages:
            for recipient in msg.recipients:
                if recipient not in client_tracking:
                    client_tracking[recipient] = {
                        "last_sent": msg.date,
                        "last_response": None,
                        "sent_count": 1
                    }
                else:
                    if msg.date > client_tracking[recipient]["last_sent"]:
                        client_tracking[recipient]["last_sent"] = msg.date
                    client_tracking[recipient]["sent_count"] += 1
        
        # Find received emails from these clients
        for client_email, info in client_tracking.items():
            response_query = f"from:{client_email}"
            responses = asyncio.run(service.search_emails(response_query, max_results=10))
            
            if responses:
                latest_response = max(responses, key=lambda x: x.date)
                if latest_response.date > info["last_sent"]:
                    info["last_response"] = latest_response.date
        
        # Identify overdue clients
        overdue_clients = []
        for client_email, info in client_tracking.items():
            if (info["last_response"] is None or 
                info["last_response"] < overdue_threshold) and \
               info["last_sent"] < overdue_threshold:
                
                days_overdue = (datetime.now() - info["last_sent"]).days
                overdue_clients.append({
                    "email": client_email,
                    "last_sent": info["last_sent"].isoformat(),
                    "last_response": info["last_response"].isoformat() if info["last_response"] else None,
                    "days_overdue": days_overdue,
                    "sent_count": info["sent_count"]
                })
        
        return {
            "success": True,
            "overdue_clients": sorted(overdue_clients, key=lambda x: x["days_overdue"], reverse=True),
            "count": len(overdue_clients),
            "threshold_days": days_threshold
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# Prompts - Email management templates
@mcp.prompt("follow-up-campaign")
def follow_up_campaign_prompt(client_type: str = "general", urgency: str = "medium") -> str:
    """Generate a prompt for creating a follow-up email campaign"""
    return f"""
I need to create a follow-up email campaign for {client_type} clients with {urgency} urgency.

Please help me:

1. First, find overdue clients using the find_overdue_clients tool
2. Analyze the client list and categorize by:
   - Days overdue
   - Previous interaction history
   - Response patterns

3. Create a targeted follow-up strategy:
   - Gentle reminders for 1-3 days overdue
   - Standard follow-ups for 4-7 days overdue  
   - Urgent follow-ups for 8+ days overdue

4. Draft appropriate email templates for each category
5. Execute the follow-up campaign using send_follow_up_email tool

Focus on maintaining professional relationships while being persistent about getting responses.
"""


@mcp.prompt("client-analysis")
def client_analysis_prompt(time_period: str = "last_month") -> str:
    """Generate a prompt for analyzing client communication patterns"""
    return f"""
I want to analyze client communication patterns for the {time_period}.

Please help me:

1. Search for all sent and received emails in the specified time period
2. Analyze communication patterns:
   - Response rates by client
   - Average response time
   - Email frequency patterns
   - Clients with declining engagement

3. Identify:
   - Most responsive clients
   - Clients at risk of churn
   - Opportunities for better engagement

4. Generate insights and recommendations for:
   - Improving response rates
   - Optimizing follow-up timing
   - Personalized communication strategies

Use the email search and tracking tools to gather comprehensive data.
"""


@mcp.prompt("email-cleanup")
def email_cleanup_prompt(folder_name: str = "inbox") -> str:
    """Generate a prompt for email organization and cleanup"""
    return f"""
I need to organize and clean up my {folder_name} folder.

Please help me:

1. Analyze the current state of the {folder_name} folder
2. Identify:
   - Unread emails requiring attention
   - Old emails that can be archived
   - Follow-up opportunities
   - Spam or unnecessary emails

3. Create an action plan for:
   - Prioritizing important emails
   - Archiving or deleting old emails
   - Setting up follow-up reminders
   - Organizing emails by category

4. Execute cleanup actions where appropriate

Focus on maintaining important communications while reducing clutter.
"""


def main():
    """Main entry point for the MCP server"""
    import asyncio
    
    # Check for required environment variables
    provider = os.getenv("EMAIL_PROVIDER", "gmail").lower()
    required_vars = ["EMAIL_PROVIDER"]
    
    if provider == "gmail":
        required_vars.extend(["GMAIL_CREDENTIALS_PATH"])
    elif provider == "outlook":
        required_vars.extend(["OUTLOOK_CREDENTIALS_PATH"])
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set the following environment variables:")
        logger.error("- EMAIL_PROVIDER (gmail or outlook)")
        if provider == "gmail":
            logger.error("- GMAIL_CREDENTIALS_PATH (path to Gmail credentials JSON)")
        else:
            logger.error("- OUTLOOK_CREDENTIALS_PATH (path to Outlook credentials JSON)")
        exit(1)
    
    logger.info(f"Starting Email Manager MCP Server with {provider}...")
    mcp.run()


if __name__ == "__main__":
    main()