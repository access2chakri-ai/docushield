"""
Migration Runner for DocuShield
Handles database schema migrations with tracking
"""
import asyncio
import importlib
import os
import sys
from pathlib import Path
from sqlalchemy import text
from app.database import get_operational_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

class MigrationRunner:
    def __init__(self):
        self.migrations_dir = Path(__file__).parent
        
    async def create_migrations_table(self):
        """Create migrations tracking table if it doesn't exist"""
        try:
            async for db in get_operational_db():
                await db.execute(text("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        migration_id VARCHAR(255) PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        success BOOLEAN DEFAULT TRUE
                    )
                """))
                await db.commit()
                logger.info("✅ Migrations tracking table ready")
                break
        except Exception as e:
            logger.warning(f"⚠️ Could not create migrations table: {e}")
            # This might happen if database doesn't exist yet - that's okay
    
    async def get_applied_migrations(self):
        """Get list of already applied migrations"""
        try:
            async for db in get_operational_db():
                result = await db.execute(text("""
                    SELECT migration_id FROM schema_migrations 
                    WHERE success = TRUE 
                    ORDER BY applied_at
                """))
                return [row.migration_id for row in result.fetchall()]
        except Exception as e:
            logger.warning(f"⚠️ Could not get applied migrations: {e}")
            return []  # Return empty list if table doesn't exist yet
    
    def get_available_migrations(self):
        """Get list of available migration files"""
        migrations = []
        for file in sorted(self.migrations_dir.glob("*.py")):
            if file.name.startswith(("__", "migration_runner")):
                continue
            migration_id = file.stem
            migrations.append(migration_id)
        return migrations
    
    async def run_migration(self, migration_id):
        """Run a specific migration"""
        try:
            # Import the migration module
            module_name = f"migrations.{migration_id}"
            migration_module = importlib.import_module(module_name)
            
            # Run the upgrade function
            if hasattr(migration_module, 'upgrade'):
                await migration_module.upgrade()
                
                # Record successful migration
                async for db in get_operational_db():
                    await db.execute(text("""
                        INSERT INTO schema_migrations (migration_id, success) 
                        VALUES (:migration_id, TRUE)
                    """), {"migration_id": migration_id})
                    await db.commit()
                    break
                
                logger.info(f"✅ Migration {migration_id} applied successfully")
                return True
            else:
                logger.error(f"❌ Migration {migration_id} has no upgrade function")
                return False
                
        except Exception as e:
            logger.error(f"❌ Migration {migration_id} failed: {e}")
            
            # Record failed migration
            async for db in get_operational_db():
                await db.execute(text("""
                    INSERT INTO schema_migrations (migration_id, success) 
                    VALUES (:migration_id, FALSE)
                """), {"migration_id": migration_id})
                await db.commit()
                break
            
            return False
    
    async def migrate(self):
        """Run all pending migrations"""
        logger.info("🚀 Starting database migrations...")
        
        # Create migrations table
        await self.create_migrations_table()
        
        # Get applied and available migrations
        applied = await self.get_applied_migrations()
        available = self.get_available_migrations()
        
        # Find pending migrations
        pending = [m for m in available if m not in applied]
        
        if not pending:
            logger.info("✅ No pending migrations")
            return
        
        logger.info(f"📋 Found {len(pending)} pending migrations: {pending}")
        
        # Run each pending migration
        for migration_id in pending:
            logger.info(f"🔄 Running migration: {migration_id}")
            success = await self.run_migration(migration_id)
            if not success:
                logger.error(f"❌ Migration failed, stopping: {migration_id}")
                break
        
        logger.info("🎉 All migrations completed!")
    
    async def status(self):
        """Show migration status"""
        await self.create_migrations_table()
        
        applied = await self.get_applied_migrations()
        available = self.get_available_migrations()
        pending = [m for m in available if m not in applied]
        
        print("\n📊 Migration Status:")
        print(f"Applied: {len(applied)}")
        print(f"Available: {len(available)}")
        print(f"Pending: {len(pending)}")
        
        if applied:
            print("\n✅ Applied migrations:")
            for migration in applied:
                print(f"  - {migration}")
        
        if pending:
            print("\n⏳ Pending migrations:")
            for migration in pending:
                print(f"  - {migration}")

async def main():
    runner = MigrationRunner()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "status":
            await runner.status()
        elif command == "migrate":
            await runner.migrate()
        else:
            print("Usage: python migration_runner.py [status|migrate]")
    else:
        await runner.migrate()

if __name__ == "__main__":
    asyncio.run(main())
