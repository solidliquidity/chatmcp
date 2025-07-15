"""
Notification Agent for Columbia Lake Partners
Notifies when a company is failing based on database conditions using Google ADK
"""

import google.generativeai as genai
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid
import asyncio
import json

from ..shared.config import GOOGLE_ADK_CONFIG, DATABASE_CONFIG, EMAIL_CONFIG, AGENT_CONFIG
from ..shared.types import (
    CompanyData, NotificationAlert, AgentResponse, 
    CompanyStatus, AlertSeverity
)
from ..shared.utils import (
    setup_logging, create_success_response, create_error_response,
    calculate_company_health_score, determine_alert_severity,
    get_current_timestamp
)
from ..tools.database import DatabaseManager
from ..tools.email import EmailManager

class NotificationAgent:
    """Agent for monitoring company health and sending failure alerts"""
    
    def __init__(self):
        self.logger = setup_logging("notification_agent")
        self.config = AGENT_CONFIG
        self.config.agent_name = "notification_agent"
        
        # Initialize Google ADK
        genai.configure(api_key=GOOGLE_ADK_CONFIG.api_key)
        self.model = genai.GenerativeModel(self.config.model)
        
        # Initialize database and email manager
        self.db_manager = DatabaseManager(DATABASE_CONFIG)
        self.email_manager = EmailManager(EMAIL_CONFIG)
        
        # Alert thresholds
        self.alert_thresholds = {
            'critical_health_score': 30.0,
            'high_health_score': 50.0,
            'medium_health_score': 70.0,
            'consecutive_declining_days': 7,
            'missing_data_days': 14,
            'negative_cash_flow_threshold': -10000
        }
        
        # Notification recipients
        self.notification_recipients = [
            "management@columbialake.com",
            "alerts@columbialake.com"
        ]
        
        self.logger.info(f"Notification Agent initialized with model: {self.config.model}")
    
    async def monitor_company_health(self) -> List[NotificationAlert]:
        """Monitor all companies for health issues and generate alerts"""
        try:
            self.logger.info("Monitoring company health for all companies")
            
            companies = await self.db_manager.get_all_companies()
            alerts = []
            
            for company in companies:
                company_alerts = await self._evaluate_company_health(company)
                alerts.extend(company_alerts)
            
            self.logger.info(f"Generated {len(alerts)} health alerts")
            return alerts
            
        except Exception as e:
            self.logger.error(f"Error monitoring company health: {str(e)}")
            return []
    
    async def _evaluate_company_health(self, company: CompanyData) -> List[NotificationAlert]:
        """Evaluate a single company's health and generate alerts"""
        alerts = []
        
        try:
            # Calculate current health score
            health_score = calculate_company_health_score(company.metrics)
            
            # Check critical health score
            if health_score <= self.alert_thresholds['critical_health_score']:
                alerts.append(await self._create_alert(
                    company,
                    AlertSeverity.CRITICAL,
                    f"Company health score critical: {health_score:.1f}%"
                ))
            elif health_score <= self.alert_thresholds['high_health_score']:
                alerts.append(await self._create_alert(
                    company,
                    AlertSeverity.HIGH,
                    f"Company health score concerning: {health_score:.1f}%"
                ))
            elif health_score <= self.alert_thresholds['medium_health_score']:
                alerts.append(await self._create_alert(
                    company,
                    AlertSeverity.MEDIUM,
                    f"Company health score declining: {health_score:.1f}%"
                ))
            
            # Check for status changes
            if company.status == CompanyStatus.FAILING:
                alerts.append(await self._create_alert(
                    company,
                    AlertSeverity.CRITICAL,
                    "Company status changed to FAILING"
                ))
            elif company.status == CompanyStatus.SUSPENDED:
                alerts.append(await self._create_alert(
                    company,
                    AlertSeverity.HIGH,
                    "Company status changed to SUSPENDED"
                ))
            
            # Check for missing data
            days_since_update = (datetime.now() - company.last_updated).days
            if days_since_update >= self.alert_thresholds['missing_data_days']:
                alerts.append(await self._create_alert(
                    company,
                    AlertSeverity.MEDIUM,
                    f"No data update for {days_since_update} days"
                ))
            
            # Check financial metrics
            if 'cash_flow' in company.metrics:
                cash_flow = company.metrics['cash_flow']
                if cash_flow < self.alert_thresholds['negative_cash_flow_threshold']:
                    alerts.append(await self._create_alert(
                        company,
                        AlertSeverity.HIGH,
                        f"Negative cash flow: ${cash_flow:,.2f}"
                    ))
            
            # Check for consecutive declining performance
            declining_trend = await self._check_declining_trend(company)
            if declining_trend:
                alerts.append(await self._create_alert(
                    company,
                    AlertSeverity.HIGH,
                    f"Consecutive declining performance for {declining_trend} days"
                ))
            
        except Exception as e:
            self.logger.error(f"Error evaluating health for {company.name}: {str(e)}")
        
        return alerts
    
    async def _create_alert(self, company: CompanyData, severity: AlertSeverity, message: str) -> NotificationAlert:
        """Create a notification alert"""
        return NotificationAlert(
            alert_id=str(uuid.uuid4()),
            company_id=company.company_id,
            company_name=company.name,
            severity=severity,
            message=message,
            timestamp=get_current_timestamp(),
            resolved=False
        )
    
    async def _check_declining_trend(self, company: CompanyData) -> Optional[int]:
        """Check if company has been declining for consecutive days"""
        try:
            # Get historical health scores
            historical_scores = await self.db_manager.get_historical_health_scores(
                company.company_id, 
                days=self.alert_thresholds['consecutive_declining_days']
            )
            
            if len(historical_scores) < 2:
                return None
            
            # Check if scores are consistently declining
            declining_days = 0
            for i in range(1, len(historical_scores)):
                if historical_scores[i] < historical_scores[i-1]:
                    declining_days += 1
                else:
                    declining_days = 0
            
            return declining_days if declining_days >= self.alert_thresholds['consecutive_declining_days'] else None
            
        except Exception as e:
            self.logger.error(f"Error checking declining trend: {str(e)}")
            return None
    
    async def process_alerts(self, alerts: List[NotificationAlert]) -> AgentResponse:
        """Process and send notification alerts"""
        try:
            processed_count = 0
            errors = []
            
            # Group alerts by severity
            grouped_alerts = self._group_alerts_by_severity(alerts)
            
            for severity, severity_alerts in grouped_alerts.items():
                try:
                    # Generate comprehensive notification using Google ADK
                    notification_content = await self._generate_alert_notification(
                        severity_alerts, 
                        severity
                    )
                    
                    if notification_content:
                        # Send notification to all recipients
                        for recipient in self.notification_recipients:
                            success = await self._send_alert_notification(
                                recipient, 
                                notification_content
                            )
                            
                            if success:
                                processed_count += len(severity_alerts)
                            else:
                                errors.append(f"Failed to send {severity.value} alert to {recipient}")
                    else:
                        errors.append(f"Failed to generate notification for {severity.value} alerts")
                    
                except Exception as e:
                    error_msg = f"Error processing {severity.value} alerts: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
            
            # Store alerts in database
            for alert in alerts:
                await self.db_manager.insert_notification_alert(alert)
            
            return create_success_response(
                f"Processed {processed_count} alerts",
                data={'processed': processed_count, 'errors': errors}
            )
            
        except Exception as e:
            error_msg = f"Failed to process alerts: {str(e)}"
            self.logger.error(error_msg)
            return create_error_response(error_msg)
    
    def _group_alerts_by_severity(self, alerts: List[NotificationAlert]) -> Dict[AlertSeverity, List[NotificationAlert]]:
        """Group alerts by severity level"""
        grouped = {}
        
        for alert in alerts:
            if alert.severity not in grouped:
                grouped[alert.severity] = []
            grouped[alert.severity].append(alert)
        
        return grouped
    
    async def _generate_alert_notification(self, alerts: List[NotificationAlert], severity: AlertSeverity) -> Optional[Dict[str, str]]:
        """Generate comprehensive alert notification using Google ADK"""
        try:
            alert_details = []
            for alert in alerts:
                alert_details.append({
                    'company': alert.company_name,
                    'message': alert.message,
                    'timestamp': alert.timestamp.isoformat()
                })
            
            prompt = f"""
            Generate a professional alert notification email for Columbia Lake Partners management.
            
            Severity: {severity.value.upper()}
            Number of alerts: {len(alerts)}
            Alert details: {json.dumps(alert_details, indent=2)}
            
            Email should include:
            1. Clear subject line indicating severity
            2. Executive summary of the situation
            3. Detailed breakdown of each alert
            4. Recommended immediate actions
            5. Contact information for follow-up
            
            Make it professional, urgent but not panic-inducing, and actionable.
            Return JSON with 'subject' and 'body' fields only.
            """
            
            response = await self.model.generate_content_async(prompt)
            
            if response.text:
                try:
                    notification_content = json.loads(response.text)
                    return notification_content
                except json.JSONDecodeError:
                    self.logger.warning(f"Failed to parse notification JSON: {response.text}")
                    return None
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error generating alert notification: {str(e)}")
            return None
    
    async def _send_alert_notification(self, recipient: str, notification_content: Dict[str, str]) -> bool:
        """Send alert notification email"""
        try:
            success = await self.email_manager.send_email(
                to_email=recipient,
                subject=notification_content['subject'],
                body=notification_content['body'],
                is_alert=True
            )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending alert notification: {str(e)}")
            return False
    
    async def get_alert_dashboard(self) -> AgentResponse:
        """Get alert dashboard with current status"""
        try:
            # Get recent alerts
            recent_alerts = await self.db_manager.get_recent_alerts(days=7)
            
            # Get alert statistics
            alert_stats = await self.db_manager.get_alert_statistics()
            
            # Get companies by risk level
            risk_companies = await self._get_companies_by_risk_level()
            
            dashboard_data = {
                'recent_alerts': recent_alerts,
                'statistics': alert_stats,
                'risk_companies': risk_companies,
                'last_updated': get_current_timestamp()
            }
            
            return create_success_response(
                "Alert dashboard retrieved",
                data=dashboard_data
            )
            
        except Exception as e:
            error_msg = f"Failed to get alert dashboard: {str(e)}"
            self.logger.error(error_msg)
            return create_error_response(error_msg)
    
    async def _get_companies_by_risk_level(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get companies grouped by risk level"""
        try:
            companies = await self.db_manager.get_all_companies()
            risk_levels = {
                'critical': [],
                'high': [],
                'medium': [],
                'low': []
            }
            
            for company in companies:
                health_score = calculate_company_health_score(company.metrics)
                severity = determine_alert_severity(health_score)
                
                company_info = {
                    'company_id': company.company_id,
                    'name': company.name,
                    'health_score': health_score,
                    'status': company.status.value,
                    'last_updated': company.last_updated.isoformat()
                }
                
                risk_levels[severity.value].append(company_info)
            
            return risk_levels
            
        except Exception as e:
            self.logger.error(f"Error getting companies by risk level: {str(e)}")
            return {}
    
    async def run_monitoring_cycle(self) -> AgentResponse:
        """Run complete monitoring cycle"""
        try:
            self.logger.info("Starting monitoring cycle")
            
            # Step 1: Monitor health
            alerts = await self.monitor_company_health()
            
            if not alerts:
                return create_success_response("No alerts generated during monitoring cycle")
            
            # Step 2: Process alerts
            result = await self.process_alerts(alerts)
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to run monitoring cycle: {str(e)}"
            self.logger.error(error_msg)
            return create_error_response(error_msg)

# Usage example
async def main():
    agent = NotificationAgent()
    
    # Run monitoring cycle
    result = await agent.run_monitoring_cycle()
    
    if result.success:
        print(f"Monitoring cycle completed: {result.message}")
    else:
        print(f"Monitoring cycle failed: {result.message}")

if __name__ == "__main__":
    asyncio.run(main())