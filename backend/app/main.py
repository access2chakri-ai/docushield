"""
DocuShield Digital Twin Document Intelligence - Modular FastAPI Application
Clean, structured implementation with separated routers and schemas
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Database and migrations
from app.database import init_db
from app.core.config import settings

# Routers
from app.routers import auth, documents, search, health, chat, analytics, llm, integrations, digital_twin, monitoring

logger = logging.getLogger(__name__)

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
app.include_router(integrations.router)
app.include_router(digital_twin.router)
app.include_router(monitoring.router)

# =============================================================================
# STARTUP & HEALTH ENDPOINTS
# =============================================================================

@app.on_event("startup")
async def startup():
    """Initialize services and test connections"""
    logger.info("🚀 Starting DocuShield Digital Twin Document Intelligence")
    
    # Auto-run database migrations on startup
    try:
        from migrations.migration_runner import MigrationRunner
        migration_runner = MigrationRunner()
        
        logger.info("🔄 Checking for database migrations...")
        await migration_runner.migrate()
        logger.info("✅ Database migrations completed")
    except Exception as e:
        logger.error(f"❌ Database migration failed: {e}")
        # Don't fail startup if migrations fail - log and continue
    
    # Initialize database tables (creates tables if they don't exist)
    try:
        await init_db()
        logger.info("✅ Database tables verified")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")

# Health endpoints are now handled by health.router

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
