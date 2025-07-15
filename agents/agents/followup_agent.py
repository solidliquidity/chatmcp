"""
Follow-up Agent for Columbia Lake Partners
Automatically chases up companies based on conditions and has access to Outlook using Google ADK
"""

import google.generativeai as genai
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import GOOGLE_ADK_CONFIG, DATABASE_CONFIG, EMAIL_CONFIG, AGENT_CONFIG
from shared.types import (
    CompanyData, FollowUpAction, AgentResponse, 
    CompanyStatus, AlertSeverity
)
from shared.utils import (
    setup_logging, create_success_response, create_error_response,
    calculate_company_health_score, determine_alert_severity,
    get_current_timestamp
)
from tools.database import DatabaseManager
from tools.email import EmailManager

class FollowUpAgent:
    """Agent for automated follow-up actions with Outlook integration"""
    
    def __init__(self):
        self.logger = setup_logging("followup_agent")
        self.config = AGENT_CONFIG
        self.config.agent_name = "followup_agent"
        
        # Initialize Google ADK
        genai.configure(api_key=GOOGLE_ADK_CONFIG.api_key)
        self.model = genai.GenerativeModel(self.config.model)
        
        # Initialize database and email manager
        self.db_manager = DatabaseManager(DATABASE_CONFIG)
        self.email_manager = EmailManager(EMAIL_CONFIG)
        
        # Follow-up conditions
        self.follow_up_conditions = {
            'overdue_response': 7,  # days
            'declining_metrics': 0.8,  # threshold
            'missing_data': 30,  # days
            'status_change': 1  # days
        }
        
        self.logger.info(f"Follow-up Agent initialized with model: {self.config.model}")
    
    async def check_follow_up_conditions(self) -> List[FollowUpAction]:
        """Check all companies against follow-up conditions"""
        try:
            self.logger.info("Checking follow-up conditions for all companies")
            
            companies = await self.db_manager.get_all_companies()
            follow_up_actions = []
            
            for company in companies:
                actions = await self._evaluate_company_conditions(company)
                follow_up_actions.extend(actions)
            
            self.logger.info(f"Generated {len(follow_up_actions)} follow-up actions")
            return follow_up_actions
            
        except Exception as e:
            self.logger.error(f"Error checking follow-up conditions: {str(e)}")
            return []
    
    async def _evaluate_company_conditions(self, company: CompanyData) -> List[FollowUpAction]:
        """Evaluate a single company against follow-up conditions"""
        actions = []
        
        try:
            # Check for overdue responses
            last_contact = await self.db_manager.get_last_contact_date(company.company_id)
            if last_contact:
                days_since_contact = (datetime.now() - last_contact).days
                if days_since_contact >= self.follow_up_conditions['overdue_response']:
                    actions.append(await self._create_follow_up_action(
                        company, 
                        "overdue_response",
                        f"No response for {days_since_contact} days"
                    ))
            
            # Check for declining metrics
            health_score = calculate_company_health_score(company.metrics)
            if health_score < self.follow_up_conditions['declining_metrics'] * 100:
                actions.append(await self._create_follow_up_action(
                    company,
                    "declining_metrics",
                    f"Health score declined to {health_score:.1f}%"
                ))
            
            # Check for missing data
            days_since_update = (datetime.now() - company.last_updated).days
            if days_since_update >= self.follow_up_conditions['missing_data']:
                actions.append(await self._create_follow_up_action(
                    company,
                    "missing_data",
                    f"No data update for {days_since_update} days"
                ))
            
            # Check for status changes
            if company.status in [CompanyStatus.FAILING, CompanyStatus.SUSPENDED]:
                actions.append(await self._create_follow_up_action(
                    company,
                    "status_change",
                    f"Company status changed to {company.status.value}"
                ))
            
        except Exception as e:
            self.logger.error(f"Error evaluating conditions for {company.name}: {str(e)}")
        
        return actions
    
    async def _create_follow_up_action(self, company: CompanyData, action_type: str, reason: str) -> FollowUpAction:
        """Create a follow-up action"""
        return FollowUpAction(
            action_id=str(uuid.uuid4()),
            company_id=company.company_id,
            action_type=action_type,
            due_date=datetime.now() + timedelta(days=1),
            status="pending",
            email_sent=False,
            response_received=False
        )
    
    async def process_follow_up_actions(self, actions: List[FollowUpAction]) -> AgentResponse:
        """Process a list of follow-up actions"""
        try:
            processed_count = 0
            errors = []
            
            for action in actions:
                try:
                    # Generate personalized email content using Google ADK
                    email_content = await self._generate_follow_up_email(action)
                    
                    if email_content:
                        # Send email
                        success = await self._send_follow_up_email(action, email_content)
                        
                        if success:
                            action.email_sent = True
                            action.status = "sent"
                            processed_count += 1
                        else:
                            errors.append(f"Failed to send email for action {action.action_id}")
                    else:
                        errors.append(f"Failed to generate email content for action {action.action_id}")
                    
                    # Update action in database
                    await self.db_manager.update_follow_up_action(action)
                    
                except Exception as e:
                    error_msg = f"Error processing action {action.action_id}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
            
            return create_success_response(
                f"Processed {processed_count} follow-up actions",
                data={'processed': processed_count, 'errors': errors}
            )
            
        except Exception as e:
            error_msg = f"Failed to process follow-up actions: {str(e)}"
            self.logger.error(error_msg)
            return create_error_response(error_msg)
    
    async def _generate_follow_up_email(self, action: FollowUpAction) -> Optional[Dict[str, str]]:
        """Generate personalized follow-up email using Google ADK"""
        try:
            # Get company data
            company = await self.db_manager.get_company_data(action.company_id)
            if not company:
                return None
            
            # Generate email content based on action type
            prompt = f"""
            Generate a professional follow-up email for the following situation:
            
            Company: {company.name}
            Contact Email: {company.contact_email}
            Action Type: {action.action_type}
            Company Status: {company.status.value}
            
            Email should be:
            1. Professional and courteous
            2. Specific to the action type
            3. Include relevant company information
            4. Have a clear call to action
            5. Be concise but informative
            
            Return JSON with 'subject' and 'body' fields only.
            """
            
            response = await self.model.generate_content_async(prompt)
            
            if response.text:
                import json
                try:
                    email_content = json.loads(response.text)
                    return email_content
                except json.JSONDecodeError:
                    self.logger.warning(f"Failed to parse email JSON: {response.text}")
                    return None
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error generating follow-up email: {str(e)}")
            return None
    
    async def _send_follow_up_email(self, action: FollowUpAction, email_content: Dict[str, str]) -> bool:
        """Send follow-up email via Outlook"""
        try:
            company = await self.db_manager.get_company_data(action.company_id)
            if not company:
                return False
            
            # Send email using email manager
            success = await self.email_manager.send_email(
                to_email=company.contact_email,
                subject=email_content['subject'],
                body=email_content['body'],
                action_id=action.action_id
            )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending follow-up email: {str(e)}")
            return False
    
    async def check_email_responses(self) -> AgentResponse:
        """Check for email responses and update follow-up actions"""
        try:
            # Get pending follow-up actions
            pending_actions = await self.db_manager.get_pending_follow_up_actions()
            
            updated_count = 0
            
            for action in pending_actions:
                if action.email_sent and not action.response_received:
                    # Check for response using email manager
                    has_response = await self.email_manager.check_for_response(action.action_id)
                    
                    if has_response:
                        action.response_received = True
                        action.status = "completed"
                        await self.db_manager.update_follow_up_action(action)
                        updated_count += 1
            
            return create_success_response(
                f"Updated {updated_count} follow-up actions with responses",
                data={'updated_count': updated_count}
            )
            
        except Exception as e:
            error_msg = f"Failed to check email responses: {str(e)}"
            self.logger.error(error_msg)
            return create_error_response(error_msg)
    
    async def get_follow_up_statistics(self) -> AgentResponse:
        """Get follow-up statistics"""
        try:
            stats = await self.db_manager.get_follow_up_statistics()
            
            return create_success_response(
                "Follow-up statistics retrieved",
                data=stats
            )
            
        except Exception as e:
            error_msg = f"Failed to get follow-up statistics: {str(e)}"
            self.logger.error(error_msg)
            return create_error_response(error_msg)
    
    async def run_automated_follow_up(self) -> AgentResponse:
        """Run the complete automated follow-up process"""
        try:
            self.logger.info("Starting automated follow-up process")
            
            # Step 1: Check conditions
            actions = await self.check_follow_up_conditions()
            
            if not actions:
                return create_success_response("No follow-up actions required")
            
            # Step 2: Process actions
            result = await self.process_follow_up_actions(actions)
            
            # Step 3: Check for responses
            await self.check_email_responses()
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to run automated follow-up: {str(e)}"
            self.logger.error(error_msg)
            return create_error_response(error_msg)

# Usage example
async def main():
    agent = FollowUpAgent()
    
    # Run automated follow-up process
    result = await agent.run_automated_follow_up()
    
    if result.success:
        print(f"Follow-up process completed: {result.message}")
    else:
        print(f"Follow-up process failed: {result.message}")

if __name__ == "__main__":
    asyncio.run(main())