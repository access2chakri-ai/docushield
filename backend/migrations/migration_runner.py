"""
Migration Runner for DocuShield
Detects and runs migration files with tracking
"""
import asyncio
import sys
import importlib
from pathlib import Path
from sqlalchemy import text
import logging

# Add backend to Python path
backend_path = str(Path(__file__).parent.parent)
sys.path.insert(0, backend_path)

from app.database import get_operational_db
from app.core.logging_config import setup_logging, get_clean_logger

# Setup clean logging for migrations
setup_logging(log_level="INFO")
logger = get_clean_logger("migrations")

# Import startup messages at module level to avoid inline imports
try:
    from app.core.startup_messages import log_migration_summary
except ImportError:
    # Fallback if startup_messages is not available
    def log_migration_summary(applied_count: int, pending_count: int):
        if pending_count == 0:
            logger.info(f"✅ Database up to date ({applied_count} migrations applied)")
        else:
            logger.info(f"🔄 Running {pending_count} pending migrations...")

class MigrationRunner:
    """Migration runner that detects and runs migration files"""
    
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
    
    async def get_applied_migrations(self):
        """Get list of already applied migrations"""
        try:
            async for db in get_operational_db():
                # Get successful migrations
                result = await db.execute(text("""
                    SELECT migration_id FROM schema_migrations 
                    WHERE success = TRUE
                    ORDER BY applied_at
                """))
                applied_migrations = [row.migration_id for row in result.fetchall()]
                return applied_migrations
        except Exception as e:
            logger.warning(f"⚠️ Could not get applied migrations: {e}")
            return []
    
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
                # Get database connection and pass it to migration
                async for db in get_operational_db():
                    await migration_module.upgrade(db)
                    
                    # Record successful migration - update if exists
                    await db.execute(text("""
                        INSERT INTO schema_migrations (migration_id, success, applied_at)
                        VALUES (:migration_id, TRUE, NOW())
                        ON DUPLICATE KEY UPDATE 
                            success = TRUE, 
                            applied_at = NOW()
                    """), {"migration_id": migration_id})
                    await db.commit()
                    break
                
                # Success logging handled by main loop
                return True
            else:
                logger.error(f"❌ Migration {migration_id} has no upgrade function")
                return False
                
        except Exception as e:
            logger.error(f"❌ Migration {migration_id} failed: {e}")
            
            # Record failed migration
            try:
                async for db in get_operational_db():
                    await db.execute(text("""
                        INSERT INTO schema_migrations (migration_id, success, applied_at)
                        VALUES (:migration_id, FALSE, NOW())
                        ON DUPLICATE KEY UPDATE 
                            success = FALSE, 
                            applied_at = NOW()
                    """), {"migration_id": migration_id})
                    await db.commit()
                    break
            except Exception as record_error:
                logger.error(f"❌ Could not record migration failure: {record_error}")
            
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
            log_migration_summary(len(applied), 0)
            return
        
        log_migration_summary(len(applied), len(pending))
        
        # Run each pending migration
        for migration_id in pending:
            logger.info(f"🔄 {migration_id}")
            success = await self.run_migration(migration_id)
            if not success:
                logger.error(f"❌ Migration failed: {migration_id}")
                break
            logger.info(f"✅ {migration_id}")
        
        logger.info("✅ All migrations completed")
    
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
