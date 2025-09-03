"""
System health and capabilities router for DocuShield API
"""
from fastapi import APIRouter
from sqlalchemy import text
from typing import Optional

from app.database import get_operational_db
from app.services.llm_factory import llm_factory

router = APIRouter(tags=["health"])

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "DocuShield Digital Twin Document Intelligence",
        "version": "2.0.0"
    }

@router.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "DocuShield Digital Twin Document Intelligence API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
        "features": {
            "jwt_authentication": "✅ Secure token-based auth",
            "document_upload": "✅ Multi-format support",
            "ai_analysis": "✅ LLM-powered insights",
            "vector_search": "✅ TiDB Vector Search",
            "multi_cluster": "✅ Operational/Sandbox/Analytics"
        }
    }

@router.get("/api/capabilities")
async def get_system_capabilities():
    """Get comprehensive system capabilities and status"""
    return {
        "service": "DocuShield Digital Twin Document Intelligence",
        "version": "2.0.0",
        "architecture": "Bronze → Silver → Gold Data Architecture",
        
        "core_features": {
            "authentication": {
                "user_management": "✅ Multi-user support with JWT tokens",
                "registration": "✅ User registration and login",
                "security": "✅ Document access control per user"
            },
            "document_processing": {
                "upload": "✅ Secure file upload to TiDB LONGBLOB",
                "text_extraction": "✅ PDF, DOCX, TXT processing",
                "deduplication": "✅ SHA-256 hash-based duplicate detection",
                "storage": "✅ TiDB multi-cluster storage"
            },
            "ai_capabilities": {
                "chat_interface": "✅ Real-time document Q&A",
                "vector_search": "✅ TiDB Vector Search integration",
                "llm_integration": "✅ Multi-provider LLM support",
                "context_awareness": "✅ User-specific document context"
            }
        },
        
        "available_endpoints": {
            "authentication": ["/api/auth/login", "/api/auth/register", "/api/auth/refresh", "/api/auth/me"],
            "documents": ["/api/documents/upload", "/api/documents", "/api/documents/{id}/analysis"],
            "search": ["/api/search/advanced", "/api/search/suggestions"],
            "system": ["/health", "/api/capabilities"]
        },
        
        "demo_features": {
            "user_isolation": "✅ Each user sees only their documents",
            "real_time_processing": "✅ Background document processing",
            "document_analysis": "✅ Extensible analysis pipeline",
            "multi_format_support": "✅ PDF, DOCX, TXT, MD processing",
            "jwt_security": "✅ Token-based authentication"
        }
    }

@router.get("/api/providers/status")
async def get_provider_status():
    """Get status of external providers and services"""
    try:
        # Test database connectivity
        db_status = "connected"
        try:
            async for db in get_operational_db():
                await db.execute(text("SELECT 1"))
        except Exception:
            db_status = "disconnected"
        
        # Get LLM provider status
        llm_status = llm_factory.get_provider_status()
        
        return {
            "database": {
                "operational_cluster": db_status,
                "status": "✅" if db_status == "connected" else "❌"
            },
            "llm_providers": llm_status,
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
    except Exception as e:
        return {
            "error": f"Status check failed: {str(e)}",
            "timestamp": "2024-01-01T00:00:00Z"
        }
