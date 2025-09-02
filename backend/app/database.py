"""
Multi-cluster TiDB database connections for DocuShield Digital Twin
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models import Base
import logging
import ssl
from enum import Enum
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

class ClusterType(Enum):
    OPERATIONAL = "operational"
    SANDBOX = "sandbox"
    ANALYTICS = "analytics"

# Create SSL context for TiDB Cloud
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Multi-cluster engine configuration
engines = {}
session_makers = {}

def create_cluster_engine(cluster_type: ClusterType):
    """Create engine for specific cluster"""
    if cluster_type == ClusterType.OPERATIONAL:
        db_url = settings.operational_database_url
    elif cluster_type == ClusterType.SANDBOX:
        db_url = settings.sandbox_database_url
    elif cluster_type == ClusterType.ANALYTICS:
        db_url = settings.analytics_database_url
    else:
        raise ValueError(f"Unknown cluster type: {cluster_type}")
    
    engine = create_async_engine(
        db_url.replace("mysql+pymysql://", "mysql+aiomysql://"),
        echo=settings.debug,
        pool_pre_ping=True,
        pool_recycle=300,
        # SSL configuration for TiDB Cloud (aiomysql parameters)
        connect_args={
            "ssl": ssl_context
        }
    )
    
    engines[cluster_type] = engine
    session_makers[cluster_type] = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    return engine

# Initialize all cluster engines
operational_engine = create_cluster_engine(ClusterType.OPERATIONAL)
sandbox_engine = create_cluster_engine(ClusterType.SANDBOX)
analytics_engine = create_cluster_engine(ClusterType.ANALYTICS)



async def init_db():
    """Initialize database tables on all clusters"""
    try:
        for cluster_type, engine in engines.items():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info(f"Database initialized successfully for {cluster_type.value} cluster")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

async def get_db(cluster_type: ClusterType = ClusterType.OPERATIONAL) -> AsyncGenerator[AsyncSession, None]:
    """Database dependency for specific cluster"""
    session_maker = session_makers[cluster_type]
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_operational_db() -> AsyncGenerator[AsyncSession, None]:
    """Get operational database session"""
    async for session in get_db(ClusterType.OPERATIONAL):
        yield session

async def get_sandbox_db() -> AsyncGenerator[AsyncSession, None]:
    """Get sandbox database session"""
    async for session in get_db(ClusterType.SANDBOX):
        yield session

async def get_analytics_db() -> AsyncGenerator[AsyncSession, None]:
    """Get analytics database session"""
    async for session in get_db(ClusterType.ANALYTICS):
        yield session

async def test_vector_search(cluster_type: ClusterType = ClusterType.OPERATIONAL):
    """Test TiDB vector search capabilities on specific cluster"""
    try:
        session_maker = session_makers[cluster_type]
        async with session_maker() as session:
            # Test vector distance calculation
            result = await session.execute(
                text("SELECT VEC_L2_DISTANCE('[1,2,3]', '[4,5,6]') as distance")
            )
            distance = result.scalar()
            logger.info(f"Vector search test successful on {cluster_type.value}. Distance: {distance}")
            return True
    except Exception as e:
        logger.warning(f"Vector search not available on {cluster_type.value}: {e}")
        return False

async def test_all_clusters():
    """Test connectivity and vector search on all clusters"""
    results = {}
    for cluster_type in ClusterType:
        try:
            results[cluster_type.value] = await test_vector_search(cluster_type)
        except Exception as e:
            logger.error(f"Failed to test {cluster_type.value} cluster: {e}")
            results[cluster_type.value] = False
    
    return results

async def create_sandbox_branch(source_cluster: ClusterType = ClusterType.OPERATIONAL) -> str:
    """
    Create a sandbox branch from operational data for what-if analysis
    This simulates TiDB's branching feature for safe experimentation
    """
    try:
        # Get data from source cluster
        source_session_maker = session_makers[source_cluster]
        sandbox_session_maker = session_makers[ClusterType.SANDBOX]
        
        async with source_session_maker() as source_session:
            async with sandbox_session_maker() as sandbox_session:
                # Copy recent documents for sandbox analysis
                result = await source_session.execute(
                    text("SELECT * FROM documents ORDER BY created_at DESC LIMIT 100")
                )
                documents = result.fetchall()
                
                # Clear existing sandbox data
                await sandbox_session.execute(text("DELETE FROM documents"))
                
                # Copy documents to sandbox
                for doc in documents:
                    await sandbox_session.execute(
                        text("""
                            INSERT INTO documents (id, title, content, file_type, dataset_id, embedding, created_at)
                            VALUES (:id, :title, :content, :file_type, :dataset_id, :embedding, :created_at)
                        """),
                        dict(doc._asdict())
                    )
                
                await sandbox_session.commit()
                
                branch_id = f"sandbox_{int(time.time())}"
                logger.info(f"Created sandbox branch: {branch_id} with {len(documents)} documents")
                return branch_id
                
    except Exception as e:
        logger.error(f"Failed to create sandbox branch: {e}")
        raise

import time
