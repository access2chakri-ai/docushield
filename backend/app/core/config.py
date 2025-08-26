"""
Simple configuration for DocuShield hackathon demo
"""
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    tidb_host: str = os.getenv("TIDB_HOST", "localhost")
    tidb_port: int = int(os.getenv("TIDB_PORT", "4000"))
    tidb_user: str = os.getenv("TIDB_USER", "root")
    tidb_password: str = os.getenv("TIDB_PASSWORD", "")
    tidb_database: str = os.getenv("TIDB_DATABASE", "docushield")
    
    @property
    def database_url(self) -> str:
        # SSL is handled in connect_args, not in URL
        if self.tidb_password:
            return f"mysql+pymysql://{self.tidb_user}:{self.tidb_password}@{self.tidb_host}:{self.tidb_port}/{self.tidb_database}"
        return f"mysql+pymysql://{self.tidb_user}@{self.tidb_host}:{self.tidb_port}/{self.tidb_database}"
    
    # LLM APIs
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # App settings
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    class Config:
        env_file = ".env"

settings = Settings()
