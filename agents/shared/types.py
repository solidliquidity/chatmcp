"""
Type definitions for Columbia Lake Partners agents
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class CompanyStatus(Enum):
    """Company status enumeration"""
    ACTIVE = "active"
    FAILING = "failing"
    SUSPENDED = "suspended"
    CLOSED = "closed"

class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class CompanyData:
    """Company data structure"""
    company_id: str
    name: str
    contact_email: str
    status: CompanyStatus
    last_updated: datetime
    financial_data: Dict[str, Any]
    metrics: Dict[str, float]
    
@dataclass
class ExcelProcessingResult:
    """Result of Excel sheet processing"""
    success: bool
    company_data: Optional[CompanyData]
    errors: List[str]
    warnings: List[str]
    processed_rows: int
    
@dataclass
class FollowUpAction:
    """Follow-up action structure"""
    action_id: str
    company_id: str
    action_type: str
    due_date: datetime
    status: str
    email_sent: bool
    response_received: bool
    
@dataclass
class NotificationAlert:
    """Notification alert structure"""
    alert_id: str
    company_id: str
    company_name: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    resolved: bool
    
@dataclass
class AgentResponse:
    """Standard agent response structure"""
    success: bool
    message: str
    data: Optional[Any] = None
    errors: List[str] = None
    
@dataclass
class DatabaseConnection:
    """Database connection details"""
    host: str
    port: int
    database: str
    username: str
    password: str