"""
Enhanced configuration for DocuShield Digital Twin Document Intelligence
Supports both .env files (local development) and AWS environment variables (production)
"""
# Import early_config first to ensure secrets are loaded from AWS Secrets Manager
import early_config

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    # Multi-Cluster TiDB Configuration
    # Cluster 1: Operational (real-time search + insights)
    tidb_operational_host: str = os.getenv("TIDB_OPERATIONAL_HOST", "localhost")
    tidb_operational_port: int = int(os.getenv("TIDB_OPERATIONAL_PORT", "4000"))
    tidb_operational_user: str = os.getenv("TIDB_OPERATIONAL_USER", "root")
    tidb_operational_password: str = os.getenv("TIDB_OPERATIONAL_PASSWORD", "")
    tidb_operational_database: str = os.getenv("TIDB_OPERATIONAL_DATABASE", "docushield_ops")
    
    # Cluster 2: Sandbox (branching for what-if analysis)
    tidb_sandbox_host: str = os.getenv("TIDB_SANDBOX_HOST", "localhost")
    tidb_sandbox_port: int = int(os.getenv("TIDB_SANDBOX_PORT", "4001"))
    tidb_sandbox_user: str = os.getenv("TIDB_SANDBOX_USER", "root")
    tidb_sandbox_password: str = os.getenv("TIDB_SANDBOX_PASSWORD", "")
    tidb_sandbox_database: str = os.getenv("TIDB_SANDBOX_DATABASE", "docushield_sandbox")
    
    # Cluster 3: Analytics (patterns, trends, simulations)
    tidb_analytics_host: str = os.getenv("TIDB_ANALYTICS_HOST", "localhost")
    tidb_analytics_port: int = int(os.getenv("TIDB_ANALYTICS_PORT", "4002"))
    tidb_analytics_user: str = os.getenv("TIDB_ANALYTICS_USER", "root")
    tidb_analytics_password: str = os.getenv("TIDB_ANALYTICS_PASSWORD", "")
    tidb_analytics_database: str = os.getenv("TIDB_ANALYTICS_DATABASE", "docushield_analytics")
    
    @property
    def operational_database_url(self) -> str:
        if self.tidb_operational_password:
            return f"mysql+pymysql://{self.tidb_operational_user}:{self.tidb_operational_password}@{self.tidb_operational_host}:{self.tidb_operational_port}/{self.tidb_operational_database}"
        return f"mysql+pymysql://{self.tidb_operational_user}@{self.tidb_operational_host}:{self.tidb_operational_port}/{self.tidb_operational_database}"
    
    @property
    def sandbox_database_url(self) -> str:
        if self.tidb_sandbox_password:
            return f"mysql+pymysql://{self.tidb_sandbox_user}:{self.tidb_sandbox_password}@{self.tidb_sandbox_host}:{self.tidb_sandbox_port}/{self.tidb_sandbox_database}"
        return f"mysql+pymysql://{self.tidb_sandbox_user}@{self.tidb_sandbox_host}:{self.tidb_sandbox_port}/{self.tidb_sandbox_database}"
    
    @property
    def analytics_database_url(self) -> str:
        if self.tidb_analytics_password:
            return f"mysql+pymysql://{self.tidb_analytics_user}:{self.tidb_analytics_password}@{self.tidb_analytics_host}:{self.tidb_analytics_port}/{self.tidb_analytics_database}"
        return f"mysql+pymysql://{self.tidb_analytics_user}@{self.tidb_analytics_host}:{self.tidb_analytics_port}/{self.tidb_analytics_database}"
    
    # LLM Factory - Multi-provider API keys (all optional)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")  # Google API key for Gemini
    google_cloud_api_key: str = os.getenv("GOOGLE_CLOUD_API_KEY", "")  # Google Cloud API key for Vertex AI
    google_cloud_project: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")  # Google Cloud Project ID
    vertex_location: str = os.getenv("VERTEX_LOCATION", "global")  # Vertex AI location (global for preview models)
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    # AWS Configuration for Bedrock (uses standard AWS authentication)
    aws_access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    aws_secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    aws_session_token: str = os.getenv("AWS_SESSION_TOKEN", "")  # Optional for temporary credentials
    aws_default_region: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    
    # LLM Factory settings
    default_llm_provider: str = os.getenv("DEFAULT_LLM_PROVIDER", "bedrock")
    default_embedding_provider: str = os.getenv("DEFAULT_EMBEDDING_PROVIDER", "bedrock")
    llm_fallback_enabled: bool = os.getenv("LLM_FALLBACK_ENABLED", "true").lower() == "true"
    llm_load_balancing: bool = os.getenv("LLM_LOAD_BALANCING", "false").lower() == "true"
    
    # Google Drive Integration (optional)
    google_credentials_path: str = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    google_token_path: str = os.getenv("GOOGLE_TOKEN_PATH", "token.json")
    google_drive_folder_id: Optional[str] = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    
    # External Integrations (optional)
    slack_bot_token: str = os.getenv("SLACK_BOT_TOKEN", "")
    slack_webhook_url: str = os.getenv("SLACK_WEBHOOK_URL", "")
    sendgrid_api_key: str = os.getenv("SENDGRID_API_KEY", "")
    alert_email_from: str = os.getenv("ALERT_EMAIL_FROM", "alerts@docushield.com")
    alert_email_to: str = os.getenv("ALERT_EMAIL_TO", "")
    
    # Background Processing
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    
    # Risk Analysis Settings
    risk_threshold_high: float = float(os.getenv("RISK_THRESHOLD_HIGH", "0.8"))
    risk_threshold_medium: float = float(os.getenv("RISK_THRESHOLD_MEDIUM", "0.5"))
    
    # Document Processing
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    supported_file_types: list = ["pdf", "docx", "txt", "md"]
    max_retry_attempts: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
    retry_cooldown_minutes: int = int(os.getenv("RETRY_COOLDOWN_MINUTES", "5"))
    
    # Processing Safety Limits
    max_processing_time_minutes: int = int(os.getenv("MAX_PROCESSING_TIME_MINUTES", "15"))
    max_text_chunks: int = int(os.getenv("MAX_TEXT_CHUNKS", "500"))
    max_llm_calls_per_document: int = int(os.getenv("MAX_LLM_CALLS_PER_DOCUMENT", "100"))
    max_file_read_iterations: int = int(os.getenv("MAX_FILE_READ_ITERATIONS", "1000"))
    
    # Monitoring & Performance
    enable_real_time_monitoring: bool = os.getenv("ENABLE_REAL_TIME_MONITORING", "true").lower() == "true"
    monitoring_interval_minutes: int = int(os.getenv("MONITORING_INTERVAL_MINUTES", "5"))
    
    # Authentication settings
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-this-in-production")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # App settings
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    class Config:
        # Make .env file optional - works with AWS environment variables
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"  # Allow extra environment variables
        
        # Handle missing .env file gracefully
        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            # Only add .env file source if it exists
            import os
            if os.path.exists(".env"):
                return (
                    init_settings,
                    env_settings,
                    file_secret_settings,
                )
            else:
                # Skip .env file if it doesn't exist (AWS deployment)
                return (
                    init_settings,
                    env_settings,
                )

    def validate_configuration(self) -> dict:
        """Validate and return configuration status for debugging"""
        config_status = {
            "environment": self.environment,
            "debug_mode": self.debug,
            "database_configured": bool(self.tidb_operational_host != "localhost" or self.tidb_operational_password),
            "aws_configured": bool(self.aws_access_key_id or self.aws_default_region),
            "llm_providers": {
                "openai": bool(self.openai_api_key),
                "anthropic": bool(self.anthropic_api_key),
                "gemini": bool(self.gemini_api_key),
                "groq": bool(self.groq_api_key),
                "bedrock": bool(self.aws_access_key_id or self.aws_default_region),
            },
            "default_llm_provider": self.default_llm_provider,
            "default_embedding_provider": self.default_embedding_provider,
        }
        return config_status

settings = Settings()
