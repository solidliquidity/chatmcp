import os
from dataclasses import dataclass

@dataclass
class GoogleADKConfig:
    api_key: str = os.getenv("GOOGLE_API_KEY", "")

@dataclass
class DatabaseConfig:
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    database: str = os.getenv("DB_NAME", "columbia_lake")
    username: str = os.getenv("DB_USER", "postgres")
    password: str = os.getenv("DB_PASSWORD", "")

@dataclass
class EmailConfig:
    smtp_server: str = os.getenv("SMTP_SERVER", "smtp.office365.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    email_address: str = os.getenv("EMAIL_ADDRESS", "")
    email_password: str = os.getenv("EMAIL_PASSWORD", "")
    use_oauth: bool = os.getenv("USE_OAUTH", "false").lower() == "true"

@dataclass
class AgentConfig:
    agent_name: str = "base_agent"
    model: str = "gemini-1.5-flash"
    temperature: float = 0.1

GOOGLE_ADK_CONFIG = GoogleADKConfig()
DATABASE_CONFIG = DatabaseConfig()
EMAIL_CONFIG = EmailConfig()
AGENT_CONFIG = AgentConfig()