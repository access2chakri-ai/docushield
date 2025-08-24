from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, LargeBinary, JSON
from .settings import settings

class Base(DeclarativeBase): 
    pass

class Document(Base):
    __tablename__ = "documents"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[str] = mapped_column(String(64), index=True)
    chunk_id: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[bytes] = mapped_column(LargeBinary)  # np.float32 bytes
    meta: Mapped[dict | None] = mapped_column(JSON)

class Audit(Base):
    __tablename__ = "audit"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mode: Mapped[str] = mapped_column(String(32))
    prompt: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text)
    contexts: Mapped[dict | None] = mapped_column(JSON)

def get_engine() -> AsyncEngine:
    url = settings.SQLALCHEMY_URL if settings.ENV == "local" else (settings.TIDB_URL or settings.SQLALCHEMY_URL)
    return create_async_engine(
        url, 
        echo=False, 
        pool_pre_ping=True,
        pool_size=10, 
        max_overflow=20, 
        pool_recycle=1800, 
        pool_timeout=30
    )
