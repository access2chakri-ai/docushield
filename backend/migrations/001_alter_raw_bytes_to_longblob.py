"""
Migration 001: Alter raw_bytes column to LONGBLOB
Created: 2025-01-02
Purpose: Fix "Data too long for column" error by increasing raw_bytes column size
"""
import asyncio
import sys
from pathlib import Path
from sqlalchemy import text
import logging

# Ensure the backend directory is in the Python path
backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.database import get_operational_db

logger = logging.getLogger(__name__)

async def upgrade():
    """Apply the migration"""
    async for db in get_operational_db():
        logger.info("🔧 Migration 001: Altering raw_bytes column to LONGBLOB...")
        
        # Check current column definition
        result = await db.execute(text("""
            SELECT COLUMN_TYPE, DATA_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'bronze_contracts' 
            AND COLUMN_NAME = 'raw_bytes'
        """))
        
        current_def = result.fetchone()
        if current_def:
            logger.info(f"Current raw_bytes column: {current_def.COLUMN_TYPE}")
        
        # Alter the column to LONGBLOB
        await db.execute(text("""
            ALTER TABLE bronze_contracts 
            MODIFY COLUMN raw_bytes LONGBLOB
        """))
        
        await db.commit()
        
        # Verify the change
        result = await db.execute(text("""
            SELECT COLUMN_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'bronze_contracts' 
            AND COLUMN_NAME = 'raw_bytes'
        """))
        
        new_def = result.fetchone()
        logger.info(f"✅ Updated raw_bytes column: {new_def.COLUMN_TYPE}")
        logger.info("🎉 Migration 001 completed successfully!")
        break

async def downgrade():
    """Rollback the migration (optional)"""
    async for db in get_operational_db():
        logger.info("🔄 Rolling back Migration 001: Reverting to BLOB...")
        
        await db.execute(text("""
            ALTER TABLE bronze_contracts 
            MODIFY COLUMN raw_bytes BLOB
        """))
        
        await db.commit()
        logger.info("✅ Migration 001 rolled back")
        break

if __name__ == "__main__":
    asyncio.run(upgrade())
