"""
Add document classification fields to support any document type
"""
import logging
from sqlalchemy import text

async def upgrade(db):
    """Add document classification fields"""
    logger = logging.getLogger(__name__)
    
    try:
        await db.execute(text("""
            ALTER TABLE bronze_contracts 
            ADD COLUMN document_type VARCHAR(100) NULL,
            ADD COLUMN industry_type VARCHAR(100) NULL,
            ADD COLUMN document_category VARCHAR(50) NULL,
            ADD COLUMN user_description TEXT NULL
        """))
        logger.info("✅ Added document classification fields to bronze_contracts table")
    except Exception as e:
        error_msg = str(e).lower()
        if "duplicate column name" in error_msg or "column already exists" in error_msg:
            logger.info("ℹ️ Document classification columns already exist, skipping")
        else:
            logger.error(f"❌ Failed to add document classification columns: {e}")
            raise

async def downgrade(db):
    """Remove document classification fields"""
    await db.execute(text("""
        ALTER TABLE bronze_contracts 
        DROP COLUMN document_type,
        DROP COLUMN industry_type,
        DROP COLUMN document_category,
        DROP COLUMN user_description
    """))