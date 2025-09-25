"""
DocuShield Digital Twin Document Intelligence - Modular FastAPI Application
Clean, structured implementation with separated routers and schemas
"""
# Import early_config first to fan out DOCUSHIELD_CONFIG_JSON secret
import early_config  # populates TIDB_OPERATIONAL_HOST/PORT/etc. from the JSON

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Setup environment-aware logging first
from app.core.logging_config import setup_logging, get_clean_logger
setup_logging()  # Will use environment variable

# Database and migrations
from app.database import init_db
from app.core.config import settings

# Log configuration source for debugging
import os
logger = get_clean_logger(__name__)
if os.path.exists(".env"):
    logger.info("🔧 Configuration: Using .env file + environment variables")
else:
    logger.info("🔧 Configuration: Using AWS environment variables only")

# Routers
from app.routers import auth, documents, search, health, chat, analytics, llm, integrations, digital_twin, monitoring, providers, profile

# Import dependencies that were previously imported inline
from migrations.migration_runner import MigrationRunner
import uvicorn

# Import startup messages with fallback
try:
    from app.core.startup_messages import log_startup_complete
except ImportError:
    # Fallback if startup_messages is not available
    def log_startup_complete():
        logger = get_clean_logger("app.main")
        logger.info("🚀 DocuShield backend started successfully")
        logger.info("📡 API available at http://localhost:8000")
        logger.info("📖 Documentation at http://localhost:8000/docs")

logger = get_clean_logger(__name__)

# =============================================================================
# FASTAPI APP SETUP
# =============================================================================

app = FastAPI(
    title="DocuShield - Digital Twin Document Intelligence",
    description="Enterprise document analysis with multi-cluster TiDB and LLM Factory",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","https://main.d2be5wdxfumfls.amplifyapp.com", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# INCLUDE ROUTERS
# =============================================================================

app.include_router(health.router)  # Health endpoints (no prefix)
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(chat.router)
app.include_router(analytics.router)
app.include_router(llm.router)
app.include_router(providers.router)
app.include_router(integrations.router)
app.include_router(digital_twin.router)
app.include_router(monitoring.router)
app.include_router(profile.router)

# =============================================================================
# STARTUP & HEALTH ENDPOINTS
# =============================================================================

@app.on_event("startup")
async def startup():
    """Initialize services and test connections"""
    logger.info("🚀 Starting DocuShield Digital Twin Document Intelligence")
    
    # Log configuration status
    config_status = settings.validate_configuration()
    logger.info(f"🔧 Environment: {config_status['environment']}")
    logger.info(f"🔧 Debug mode: {config_status['debug_mode']}")
    logger.info(f"🔧 Database configured: {config_status['database_configured']}")
    logger.info(f"🔧 AWS configured: {config_status['aws_configured']}")
    logger.info(f"🔧 Default LLM provider: {config_status['default_llm_provider']}")
    
    # Debug: Log actual database configuration values
    logger.info("🔍 Database Configuration Debug:")
    logger.info(f"   TIDB_OPERATIONAL_HOST: {settings.tidb_operational_host}")
    logger.info(f"   TIDB_OPERATIONAL_PORT: {settings.tidb_operational_port}")
    logger.info(f"   TIDB_OPERATIONAL_USER: {settings.tidb_operational_user}")
    logger.info(f"   TIDB_OPERATIONAL_PASSWORD: {'***' if settings.tidb_operational_password else 'NOT SET'}")
    logger.info(f"   TIDB_OPERATIONAL_DATABASE: {settings.tidb_operational_database}")
    
    # Debug: Log all environment variables that start with TIDB
    import os
    tidb_env_vars = {k: v for k, v in os.environ.items() if k.startswith('TIDB')}
    logger.info(f"🔍 TIDB Environment Variables: {tidb_env_vars}")
    
    # Initialize database tables first (creates tables if they don't exist)
    # Only try to initialize if we have a proper database configuration
    if (settings.tidb_operational_host and 
        settings.tidb_operational_host != "localhost" and 
        settings.tidb_operational_user and 
        settings.tidb_operational_password and
        settings.tidb_operational_database):
        try:
            await init_db()
            logger.info("✅ Database tables verified")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise  # Fail startup if database init fails
    else:
        logger.warning("⚠️ Database not properly configured - skipping database initialization")
        logger.info("💡 To enable database functionality, set these environment variables in AWS App Runner:")
        logger.info("   - TIDB_OPERATIONAL_HOST (e.g., your-tidb-host.tidbcloud.com)")
        logger.info("   - TIDB_OPERATIONAL_USER (your username)")
        logger.info("   - TIDB_OPERATIONAL_PASSWORD (your password)")
        logger.info("   - TIDB_OPERATIONAL_DATABASE (your database name)")
        logger.info("   - TIDB_OPERATIONAL_PORT (usually 4000)")
    
    # Auto-run database migrations after tables are created
    if (settings.tidb_operational_host and 
        settings.tidb_operational_host != "localhost" and 
        settings.tidb_operational_user and 
        settings.tidb_operational_password and
        settings.tidb_operational_database):
        try:
            migration_runner = MigrationRunner()
            logger.info("🔄 Running database migrations...")
            await migration_runner.migrate()
            logger.info("✅ Database migrations completed")
        except Exception as e:
            logger.error(f"❌ Database migration failed: {e}")
            # Don't fail startup if migrations fail - log and continue
    else:
        logger.info("⏭️ Skipping database migrations - database not configured")
    
    # Log clean startup message
    log_startup_complete()

# Health endpoints are now handled by health.router

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
