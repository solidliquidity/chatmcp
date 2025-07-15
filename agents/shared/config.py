"""
Configuration settings for Google ADK agents
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class AgentConfig:
    """Base configuration for all agents"""
    agent_name: str
    model: str = "gemini-1.5-flash"
    temperature: float = 0.1
    max_tokens: int = 1000
    timeout: int = 30

@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    database: str = os.getenv("DB_NAME", "columbia_lake")
    username: str = os.getenv("DB_USER", "postgres")
    password: str = os.getenv("DB_PASSWORD", "")
    
@dataclass
class EmailConfig:
    """Email/Outlook configuration"""
    smtp_server: str = os.getenv("SMTP_SERVER", "smtp.office365.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    email_address: str = os.getenv("EMAIL_ADDRESS", "")
    email_password: str = os.getenv("EMAIL_PASSWORD", "")
    use_oauth: bool = os.getenv("USE_OAUTH", "false").lower() == "true"
    
@dataclass
class GoogleADKConfig:
    """Google ADK specific configuration"""
    api_key: str = os.getenv("GOOGLE_API_KEY", "")
    project_id: str = os.getenv("GOOGLE_PROJECT_ID", "")
    
# Global configuration instances
AGENT_CONFIG = AgentConfig(agent_name="base_agent")
DATABASE_CONFIG = DatabaseConfig()
EMAIL_CONFIG = EmailConfig()
GOOGLE_ADK_CONFIG = GoogleADKConfig()