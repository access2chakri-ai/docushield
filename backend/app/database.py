"""
Simple TiDB database connection
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models import Base
import logging
import ssl

logger = logging.getLogger(__name__)

# Create SSL context for TiDB Cloud
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Create async engine for TiDB with SSL support
engine = create_async_engine(
    settings.database_url.replace("mysql+pymysql://", "mysql+aiomysql://"),
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=300,
    # SSL configuration for TiDB Cloud (aiomysql parameters)
    connect_args={
        "ssl": ssl_context
    }
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    """Initialize database tables"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

async def get_db():
    """Database dependency"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def test_vector_search():
    """Test TiDB vector search capabilities"""
    try:
        async with AsyncSessionLocal() as session:
            # Test vector distance calculation
            result = await session.execute(
                text("SELECT VEC_L2_DISTANCE('[1,2,3]', '[4,5,6]') as distance")
            )
            distance = result.scalar()
            logger.info(f"Vector search test successful. Distance: {distance}")
            return True
    except Exception as e:
        logger.warning(f"Vector search not available: {e}")
        return False
