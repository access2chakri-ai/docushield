from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseModel):
    ENV: str = os.getenv("ENV", "local")
    PORT: int = int(os.getenv("PORT", "8000"))
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
    GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
    SQLALCHEMY_URL: str = os.getenv("SQLALCHEMY_URL", "sqlite+aiosqlite:///./docushield_local.db")
    TIDB_URL: str | None = os.getenv("TIDB_URL")
    EMBED_MODEL: str = os.getenv("EMBED_MODEL", "text-embedding-3-small")
    TOP_K: int = int(os.getenv("TOP_K", "6"))

settings = Settings()
