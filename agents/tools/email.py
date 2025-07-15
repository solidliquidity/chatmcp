"""
Email management tools for Columbia Lake Partners agents
"""

import smtplib
import imaplib
import email
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import re

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import EmailConfig
from shared.utils import setup_logging

class EmailManager:
    """Manages email operations for all agents"""
    
    def __init__(self, config: EmailConfig):
        self.config = config
        self.logger = setup_logging("email_manager")
        self.sent_emails = {}  # Track sent emails by action_id
    
    async def send_email(self, to_email: str, subject: str, body: str, 
                        action_id: Optional[str] = None, is_alert: bool = False) -> bool:
        """Send an email via SMTP"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config.email_address
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add action ID to message for tracking
            if action_id:
                msg['X-Action-ID'] = action_id
            
            # Add body
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            if self.config.use_oauth:
                success = await self._send_via_oauth(msg)
            else:
                success = await self._send_via_smtp(msg)
            
            if success:
                # Track sent email
                if action_id:
                    self.sent_emails[action_id] = {
                        'to': to_email,
                        'subject': subject,
                        'sent_at': datetime.now(),
                        'is_alert': is_alert
                    }
                
                self.logger.info(f"Email sent successfully to {to_email}")
            else:
                self.logger.error(f"Failed to send email to {to_email}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending email: {str(e)}")
            return False
    
    async def _send_via_smtp(self, msg: MIMEMultipart) -> bool:
        """Send email via SMTP"""
        try:
            server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
            server.starttls()
            server.login(self.config.email_address, self.config.email_password)
            
            text = msg.as_string()
            server.sendmail(self.config.email_address, msg['To'], text)
            server.quit()
            
            return True
            
        except Exception as e:
            self.logger.error(f"SMTP error: {str(e)}")
            return False
    
    async def _send_via_oauth(self, msg: MIMEMultipart) -> bool:
        """Send email via OAuth (placeholder for OAuth implementation)"""
        # This would implement OAuth authentication for Outlook
        # For now, fall back to SMTP
        self.logger.warning("OAuth not implemented, falling back to SMTP")
        return await self._send_via_smtp(msg)
    
    async def check_for_response(self, action_id: str) -> bool:
        """Check if there's a response to a sent email"""
        try:
            if action_id not in self.sent_emails:
                return False
            
            sent_email = self.sent_emails[action_id]
            
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL('outlook.office365.com')
            mail.login(self.config.email_address, self.config.email_password)
            mail.select('inbox')
            
            # Search for emails from the recipient since the email was sent
            sent_date = sent_email['sent_at']
            search_criteria = f'(FROM "{sent_email["to"]}" SINCE "{sent_date.strftime("%d-%b-%Y")}")'
            
            status, messages = mail.search(None, search_criteria)
            
            if status == 'OK':
                message_ids = messages[0].split()
                
                for msg_id in message_ids:
                    # Fetch the email
                    status, msg_data = mail.fetch(msg_id, '(RFC822)')
                    
                    if status == 'OK':
                        email_body = msg_data[0][1]
                        email_message = email.message_from_bytes(email_body)
                        
                        # Check if this is a response to our email
                        if self._is_response_to_action(email_message, action_id, sent_email):
                            mail.logout()
                            return True
            
            mail.logout()
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking for response: {str(e)}")
            return False
    
    def _is_response_to_action(self, email_message: email.message.Message, 
                             action_id: str, sent_email: Dict[str, Any]) -> bool:
        """Check if an email is a response to a specific action"""
        try:
            # Check subject line for "Re:" pattern
            subject = email_message.get('Subject', '')
            if f"Re: {sent_email['subject']}" in subject:
                return True
            
            # Check for action ID in headers (if we added it)
            action_header = email_message.get('In-Reply-To', '')
            if action_id in action_header:
                return True
            
            # Check message body for references
            body = self._get_email_body(email_message)
            if body and any(keyword in body.lower() for keyword in ['thank', 'received', 'confirm', 'update']):
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking if email is response: {str(e)}")
            return False
    
    def _get_email_body(self, email_message: email.message.Message) -> Optional[str]:
        """Extract body text from email message"""
        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == "text/plain":
                        return part.get_payload(decode=True).decode('utf-8')
            else:
                return email_message.get_payload(decode=True).decode('utf-8')
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting email body: {str(e)}")
            return None
    
    async def get_inbox_summary(self) -> Dict[str, Any]:
        """Get summary of inbox"""
        try:
            mail = imaplib.IMAP4_SSL('outlook.office365.com')
            mail.login(self.config.email_address, self.config.email_password)
            mail.select('inbox')
            
            # Get unread emails
            status, unread = mail.search(None, 'UNSEEN')
            unread_count = len(unread[0].split()) if unread[0] else 0
            
            # Get total emails
            status, total = mail.search(None, 'ALL')
            total_count = len(total[0].split()) if total[0] else 0
            
            # Get recent emails (last 24 hours)
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
            status, recent = mail.search(None, f'SINCE "{yesterday}"')
            recent_count = len(recent[0].split()) if recent[0] else 0
            
            mail.logout()
            
            return {
                'unread_count': unread_count,
                'total_count': total_count,
                'recent_count': recent_count,
                'last_checked': datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting inbox summary: {str(e)}")
            return {}
    
    async def send_bulk_emails(self, email_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send multiple emails in bulk"""
        try:
            results = {
                'sent': 0,
                'failed': 0,
                'errors': []
            }
            
            for email_data in email_list:
                success = await self.send_email(
                    to_email=email_data['to'],
                    subject=email_data['subject'],
                    body=email_data['body'],
                    action_id=email_data.get('action_id'),
                    is_alert=email_data.get('is_alert', False)
                )
                
                if success:
                    results['sent'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"Failed to send to {email_data['to']}")
                
                # Add small delay to avoid rate limiting
                await asyncio.sleep(0.1)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error sending bulk emails: {str(e)}")
            return {'sent': 0, 'failed': len(email_list), 'errors': [str(e)]}
    
    async def create_follow_up_email_template(self, company_name: str, 
                                            action_type: str) -> Dict[str, str]:
        """Create a follow-up email template"""
        templates = {
            'overdue_response': {
                'subject': f'Follow-up: Outstanding Items for {company_name}',
                'body': f"""
Dear {company_name} Team,

I hope this email finds you well. I wanted to follow up on our previous communication regarding some outstanding items that require your attention.

We have not received a response to our recent request, and I wanted to ensure that our message reached you successfully. If you have any questions or need clarification on any of the items discussed, please don't hesitate to reach out.

Could you please provide an update on the status of these items at your earliest convenience?

Thank you for your continued partnership with Columbia Lake Partners.

Best regards,
Columbia Lake Partners Team
"""
            },
            'declining_metrics': {
                'subject': f'Performance Review Required: {company_name}',
                'body': f"""
Dear {company_name} Team,

We hope this message finds you well. Our recent analysis of your company's performance metrics indicates some areas that may require attention and discussion.

We would like to schedule a meeting to discuss these findings and explore potential strategies for improvement. Our team is here to support you in addressing these challenges.

Please let us know your availability for a call or meeting in the coming days.

Best regards,
Columbia Lake Partners Team
"""
            },
            'missing_data': {
                'subject': f'Data Update Required: {company_name}',
                'body': f"""
Dear {company_name} Team,

We hope you are doing well. We noticed that we have not received your latest data updates as scheduled.

To ensure we can continue providing you with the best support and analysis, please provide the following information:
- Latest financial statements
- Updated performance metrics
- Any significant operational changes

Please submit this information at your earliest convenience.

Thank you for your cooperation.

Best regards,
Columbia Lake Partners Team
"""
            }
        }
        
        return templates.get(action_type, {
            'subject': f'Follow-up Required: {company_name}',
            'body': f'Dear {company_name} Team,\n\nWe need to follow up on some items. Please contact us.\n\nBest regards,\nColumbia Lake Partners Team'
        })
    
    def get_sent_email_stats(self) -> Dict[str, Any]:
        """Get statistics about sent emails"""
        try:
            total_sent = len(self.sent_emails)
            alert_emails = sum(1 for email in self.sent_emails.values() if email['is_alert'])
            follow_up_emails = total_sent - alert_emails
            
            # Get emails sent in last 24 hours
            yesterday = datetime.now() - timedelta(days=1)
            recent_emails = sum(1 for email in self.sent_emails.values() 
                              if email['sent_at'] > yesterday)
            
            return {
                'total_sent': total_sent,
                'alert_emails': alert_emails,
                'follow_up_emails': follow_up_emails,
                'recent_emails': recent_emails
            }
            
        except Exception as e:
            self.logger.error(f"Error getting email stats: {str(e)}")
            return {}