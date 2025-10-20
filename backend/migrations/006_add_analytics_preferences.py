"""Add analytics preferences to User model for personalized dashboards"""

import logging
from sqlalchemy import text

async def upgrade(db):
    """Add analytics preference columns to users table"""
    logger = logging.getLogger(__name__)
    
    try:
        await db.execute(text("""
            ALTER TABLE users 
            ADD COLUMN analytics_preferences JSON NULL,
            ADD COLUMN dashboard_filters JSON NULL,
            ADD COLUMN preferred_document_types JSON NULL,
            ADD COLUMN preferred_risk_levels JSON NULL,
            ADD COLUMN preferred_time_range VARCHAR(50) DEFAULT '30d'
        """))
        
        logger.info("✅ Added analytics preferences columns to users table")
        
    except Exception as e:
        error_msg = str(e).lower()
        if "duplicate column name" in error_msg or "column already exists" in error_msg:
            logger.info("ℹ️ Analytics preferences columns already exist, skipping")
        else:
            logger.error(f"❌ Failed to add analytics preferences columns: {e}")
            raise

async def downgrade(db):
    """Remove analytics preference columns from users table"""
    await db.execute(text("""
        ALTER TABLE users 
        DROP COLUMN analytics_preferences,
        DROP COLUMN dashboard_filters,
        DROP COLUMN preferred_document_types,
        DROP COLUMN preferred_risk_levels,
        DROP COLUMN preferred_time_range
    """))