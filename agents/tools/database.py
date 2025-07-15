"""
Database management tools for Columbia Lake Partners agents
"""

import asyncio
import asyncpg
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from ..shared.config import DatabaseConfig
from ..shared.types import CompanyData, FollowUpAction, NotificationAlert, CompanyStatus, AlertSeverity
from ..shared.utils import setup_logging

class DatabaseManager:
    """Manages database operations for all agents"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.logger = setup_logging("database_manager")
        self.pool = None
    
    async def init_pool(self):
        """Initialize database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password,
                min_size=5,
                max_size=20
            )
            self.logger.info("Database connection pool initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize database pool: {str(e)}")
            raise
    
    async def close_pool(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            self.logger.info("Database connection pool closed")
    
    async def insert_company_data(self, company: CompanyData) -> bool:
        """Insert or update company data"""
        try:
            if not self.pool:
                await self.init_pool()
            
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO companies (
                        company_id, name, contact_email, status, last_updated, 
                        financial_data, metrics
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (company_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        contact_email = EXCLUDED.contact_email,
                        status = EXCLUDED.status,
                        last_updated = EXCLUDED.last_updated,
                        financial_data = EXCLUDED.financial_data,
                        metrics = EXCLUDED.metrics
                """, 
                    company.company_id,
                    company.name,
                    company.contact_email,
                    company.status.value,
                    company.last_updated,
                    json.dumps(company.financial_data),
                    json.dumps(company.metrics)
                )
            
            self.logger.info(f"Company data inserted/updated: {company.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error inserting company data: {str(e)}")
            return False
    
    async def get_company_data(self, company_id: str) -> Optional[CompanyData]:
        """Get company data by ID"""
        try:
            if not self.pool:
                await self.init_pool()
            
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT company_id, name, contact_email, status, last_updated, 
                           financial_data, metrics
                    FROM companies WHERE company_id = $1
                """, company_id)
                
                if row:
                    return CompanyData(
                        company_id=row['company_id'],
                        name=row['name'],
                        contact_email=row['contact_email'],
                        status=CompanyStatus(row['status']),
                        last_updated=row['last_updated'],
                        financial_data=json.loads(row['financial_data']),
                        metrics=json.loads(row['metrics'])
                    )
                
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting company data: {str(e)}")
            return None
    
    async def get_all_companies(self) -> List[CompanyData]:
        """Get all companies"""
        try:
            if not self.pool:
                await self.init_pool()
            
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT company_id, name, contact_email, status, last_updated, 
                           financial_data, metrics
                    FROM companies
                """)
                
                companies = []
                for row in rows:
                    companies.append(CompanyData(
                        company_id=row['company_id'],
                        name=row['name'],
                        contact_email=row['contact_email'],
                        status=CompanyStatus(row['status']),
                        last_updated=row['last_updated'],
                        financial_data=json.loads(row['financial_data']),
                        metrics=json.loads(row['metrics'])
                    ))
                
                return companies
                
        except Exception as e:
            self.logger.error(f"Error getting all companies: {str(e)}")
            return []
    
    async def update_follow_up_action(self, action: FollowUpAction) -> bool:
        """Update follow-up action"""
        try:
            if not self.pool:
                await self.init_pool()
            
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO follow_up_actions (
                        action_id, company_id, action_type, due_date, status, 
                        email_sent, response_received
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (action_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        email_sent = EXCLUDED.email_sent,
                        response_received = EXCLUDED.response_received
                """, 
                    action.action_id,
                    action.company_id,
                    action.action_type,
                    action.due_date,
                    action.status,
                    action.email_sent,
                    action.response_received
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating follow-up action: {str(e)}")
            return False
    
    async def get_pending_follow_up_actions(self) -> List[FollowUpAction]:
        """Get pending follow-up actions"""
        try:
            if not self.pool:
                await self.init_pool()
            
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT action_id, company_id, action_type, due_date, status, 
                           email_sent, response_received
                    FROM follow_up_actions
                    WHERE status IN ('pending', 'sent')
                """)
                
                actions = []
                for row in rows:
                    actions.append(FollowUpAction(
                        action_id=row['action_id'],
                        company_id=row['company_id'],
                        action_type=row['action_type'],
                        due_date=row['due_date'],
                        status=row['status'],
                        email_sent=row['email_sent'],
                        response_received=row['response_received']
                    ))
                
                return actions
                
        except Exception as e:
            self.logger.error(f"Error getting pending follow-up actions: {str(e)}")
            return []
    
    async def insert_notification_alert(self, alert: NotificationAlert) -> bool:
        """Insert notification alert"""
        try:
            if not self.pool:
                await self.init_pool()
            
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO notification_alerts (
                        alert_id, company_id, company_name, severity, message, 
                        timestamp, resolved
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, 
                    alert.alert_id,
                    alert.company_id,
                    alert.company_name,
                    alert.severity.value,
                    alert.message,
                    alert.timestamp,
                    alert.resolved
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error inserting notification alert: {str(e)}")
            return False
    
    async def get_last_contact_date(self, company_id: str) -> Optional[datetime]:
        """Get last contact date for a company"""
        try:
            if not self.pool:
                await self.init_pool()
            
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT MAX(timestamp) as last_contact
                    FROM follow_up_actions
                    WHERE company_id = $1 AND email_sent = true
                """, company_id)
                
                return row['last_contact'] if row else None
                
        except Exception as e:
            self.logger.error(f"Error getting last contact date: {str(e)}")
            return None
    
    async def get_historical_health_scores(self, company_id: str, days: int = 30) -> List[float]:
        """Get historical health scores for a company"""
        try:
            if not self.pool:
                await self.init_pool()
            
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT health_score, recorded_date
                    FROM health_scores
                    WHERE company_id = $1 
                    AND recorded_date >= $2
                    ORDER BY recorded_date DESC
                """, company_id, datetime.now() - timedelta(days=days))
                
                return [row['health_score'] for row in rows]
                
        except Exception as e:
            self.logger.error(f"Error getting historical health scores: {str(e)}")
            return []
    
    async def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics"""
        try:
            if not self.pool:
                await self.init_pool()
            
            async with self.pool.acquire() as conn:
                # Get company counts by status
                status_counts = await conn.fetch("""
                    SELECT status, COUNT(*) as count
                    FROM companies
                    GROUP BY status
                """)
                
                # Get recent processing activity
                recent_activity = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_companies,
                        MAX(last_updated) as last_update
                    FROM companies
                """)
                
                return {
                    'status_counts': {row['status']: row['count'] for row in status_counts},
                    'total_companies': recent_activity['total_companies'],
                    'last_update': recent_activity['last_update']
                }
                
        except Exception as e:
            self.logger.error(f"Error getting processing statistics: {str(e)}")
            return {}
    
    async def get_follow_up_statistics(self) -> Dict[str, Any]:
        """Get follow-up statistics"""
        try:
            if not self.pool:
                await self.init_pool()
            
            async with self.pool.acquire() as conn:
                stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_actions,
                        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                        COUNT(CASE WHEN status = 'sent' THEN 1 END) as sent,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                        COUNT(CASE WHEN email_sent = true THEN 1 END) as emails_sent,
                        COUNT(CASE WHEN response_received = true THEN 1 END) as responses_received
                    FROM follow_up_actions
                """)
                
                return dict(stats)
                
        except Exception as e:
            self.logger.error(f"Error getting follow-up statistics: {str(e)}")
            return {}
    
    async def get_recent_alerts(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        try:
            if not self.pool:
                await self.init_pool()
            
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT alert_id, company_id, company_name, severity, message, 
                           timestamp, resolved
                    FROM notification_alerts
                    WHERE timestamp >= $1
                    ORDER BY timestamp DESC
                """, datetime.now() - timedelta(days=days))
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Error getting recent alerts: {str(e)}")
            return []
    
    async def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        try:
            if not self.pool:
                await self.init_pool()
            
            async with self.pool.acquire() as conn:
                stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_alerts,
                        COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical,
                        COUNT(CASE WHEN severity = 'high' THEN 1 END) as high,
                        COUNT(CASE WHEN severity = 'medium' THEN 1 END) as medium,
                        COUNT(CASE WHEN severity = 'low' THEN 1 END) as low,
                        COUNT(CASE WHEN resolved = true THEN 1 END) as resolved
                    FROM notification_alerts
                """)
                
                return dict(stats)
                
        except Exception as e:
            self.logger.error(f"Error getting alert statistics: {str(e)}")
            return {}