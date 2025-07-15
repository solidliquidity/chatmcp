"""
Utility functions for Columbia Lake Partners agents
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from .types import AgentResponse, CompanyStatus, AlertSeverity

def setup_logging(agent_name: str) -> logging.Logger:
    """Set up logging for an agent"""
    logger = logging.getLogger(agent_name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

def create_success_response(message: str, data: Optional[Any] = None) -> AgentResponse:
    """Create a successful agent response"""
    return AgentResponse(
        success=True,
        message=message,
        data=data,
        errors=None
    )

def create_error_response(message: str, errors: list = None) -> AgentResponse:
    """Create an error agent response"""
    return AgentResponse(
        success=False,
        message=message,
        data=None,
        errors=errors or []
    )

def validate_company_data(data: Dict[str, Any]) -> list:
    """Validate company data structure"""
    errors = []
    required_fields = ['company_id', 'name', 'contact_email', 'status']
    
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f"Missing required field: {field}")
    
    if 'status' in data:
        try:
            CompanyStatus(data['status'])
        except ValueError:
            errors.append(f"Invalid status: {data['status']}")
    
    return errors

def parse_excel_data(row_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse and clean Excel row data"""
    cleaned_data = {}
    
    for key, value in row_data.items():
        if value is not None and str(value).strip():
            # Clean column names
            clean_key = key.lower().replace(' ', '_').replace('-', '_')
            cleaned_data[clean_key] = value
    
    return cleaned_data

def calculate_company_health_score(metrics: Dict[str, float]) -> float:
    """Calculate company health score based on metrics"""
    if not metrics:
        return 0.0
    
    weights = {
        'revenue': 0.3,
        'profit_margin': 0.25,
        'cash_flow': 0.25,
        'debt_ratio': -0.2  # Negative weight for debt
    }
    
    score = 0.0
    total_weight = 0.0
    
    for metric, value in metrics.items():
        if metric in weights:
            score += value * weights[metric]
            total_weight += abs(weights[metric])
    
    return max(0.0, min(100.0, (score / total_weight) * 100)) if total_weight > 0 else 0.0

def determine_alert_severity(health_score: float) -> AlertSeverity:
    """Determine alert severity based on health score"""
    if health_score >= 80:
        return AlertSeverity.LOW
    elif health_score >= 60:
        return AlertSeverity.MEDIUM
    elif health_score >= 40:
        return AlertSeverity.HIGH
    else:
        return AlertSeverity.CRITICAL

def format_currency(amount: float) -> str:
    """Format currency for display"""
    return f"${amount:,.2f}"

def safe_json_loads(json_str: str) -> Optional[Dict[str, Any]]:
    """Safely parse JSON string"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return None

def get_current_timestamp() -> datetime:
    """Get current timestamp"""
    return datetime.now()