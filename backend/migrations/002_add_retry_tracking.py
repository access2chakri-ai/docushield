"""
Migration: Add retry tracking fields to bronze_contracts table
"""
import logging
from sqlalchemy import text

async def upgrade(db):
    """Add retry tracking columns to bronze_contracts table"""
    logger = logging.getLogger(__name__)
    
    # Add retry_count column
    try:
        await db.execute(text("""
            ALTER TABLE bronze_contracts 
            ADD COLUMN retry_count INT DEFAULT 0;
        """))
        logger.info("✅ Added retry_count column")
    except Exception as e:
        error_msg = str(e).lower()
        if "duplicate column name" in error_msg or "column already exists" in error_msg:
            logger.info("ℹ️ retry_count column already exists, skipping")
        else:
            logger.error(f"❌ Failed to add retry_count column: {e}")
            raise  # Re-raise if it's not a "column exists" error
    
    # Add last_retry_at column
    try:
        await db.execute(text("""
            ALTER TABLE bronze_contracts 
            ADD COLUMN last_retry_at DATETIME NULL;
        """))
        logger.info("✅ Added last_retry_at column")
    except Exception as e:
        error_msg = str(e).lower()
        if "duplicate column name" in error_msg or "column already exists" in error_msg:
            logger.info("ℹ️ last_retry_at column already exists, skipping")
        else:
            logger.error(f"❌ Failed to add last_retry_at column: {e}")
            raise  # Re-raise if it's not a "column exists" error
    
    # Add max_retries column
    try:
        await db.execute(text("""
            ALTER TABLE bronze_contracts 
            ADD COLUMN max_retries INT DEFAULT 3;
        """))
        logger.info("✅ Added max_retries column")
    except Exception as e:
        error_msg = str(e).lower()
        if "duplicate column name" in error_msg or "column already exists" in error_msg:
            logger.info("ℹ️ max_retries column already exists, skipping")
        else:
            logger.error(f"❌ Failed to add max_retries column: {e}")
            raise  # Re-raise if it's not a "column exists" error

async def downgrade(db):
    """Remove retry tracking columns from bronze_contracts table"""
    await db.execute(text("""
        ALTER TABLE bronze_contracts 
        DROP COLUMN retry_count;
    """))
    
    await db.execute(text("""
        ALTER TABLE bronze_contracts 
        DROP COLUMN last_retry_at;
    """))
    
    await db.execute(text("""
        ALTER TABLE bronze_contracts 
        DROP COLUMN max_retries;
    """))
