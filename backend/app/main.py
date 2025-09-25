"""
DocuShield Digital Twin Document Intelligence - Modular FastAPI Application
Clean, structured implementation with separated routers and schemas
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Setup environment-aware logging first
from app.core.logging_config import setup_logging, get_clean_logger
setup_logging()  # Will use environment variable

# Database and migrations
from app.database import init_db
from app.core.config import settings

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
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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
    
    # Initialize database tables first (creates tables if they don't exist)
    try:
        await init_db()
        logger.info("✅ Database tables verified")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise  # Fail startup if database init fails
    
    # Auto-run database migrations after tables are created
    try:
        migration_runner = MigrationRunner()
        logger.info("🔄 Running database migrations...")
        await migration_runner.migrate()
        logger.info("✅ Database migrations completed")
    except Exception as e:
        logger.error(f"❌ Database migration failed: {e}")
        # Don't fail startup if migrations fail - log and continue
    
    # Log clean startup message
    log_startup_complete()

# Health endpoints are now handled by health.router

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
