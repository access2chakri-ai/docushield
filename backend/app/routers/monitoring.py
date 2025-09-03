"""
Performance monitoring router for DocuShield API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any
import time

from app.database import get_operational_db
from app.core.dependencies import get_current_active_user
from app.core.performance_limits import get_processing_limits

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

@router.get("/performance")
async def get_performance_metrics(
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Get performance metrics and system status"""
    try:
        # Get processing status counts
        processing_status = await db.execute(
            text("""
                SELECT 
                    status,
                    COUNT(*) as count,
                    AVG(TIMESTAMPDIFF(SECOND, created_at, COALESCE(updated_at, NOW()))) as avg_processing_time
                FROM bronze_contracts 
                WHERE owner_user_id = :user_id
                GROUP BY status
            """),
            {"user_id": current_user.user_id}
        )
        
        status_data = {}
        for row in processing_status.fetchall():
            status_data[row[0]] = {
                "count": row[1],
                "avg_processing_time_seconds": float(row[2] or 0)
            }
        
        # Get recent processing times
        recent_processing = await db.execute(
            text("""
                SELECT 
                    contract_id,
                    filename,
                    status,
                    TIMESTAMPDIFF(SECOND, created_at, updated_at) as processing_time
                FROM bronze_contracts 
                WHERE owner_user_id = :user_id 
                AND status IN ('completed', 'failed', 'timeout')
                ORDER BY updated_at DESC 
                LIMIT 10
            """),
            {"user_id": current_user.user_id}
        )
        
        recent_data = []
        for row in recent_processing.fetchall():
            recent_data.append({
                "contract_id": row[0],
                "filename": row[1],
                "status": row[2],
                "processing_time_seconds": row[3] or 0
            })
        
        # Get system limits
        limits = get_processing_limits()
        
        return {
            "user_id": current_user.user_id,
            "timestamp": time.time(),
            "processing_status": status_data,
            "recent_processing": recent_data,
            "system_limits": limits,
            "performance_tips": [
                f"Keep documents under {limits['max_file_size_mb']}MB for fastest processing",
                "PDF and Word documents work best for business analysis",
                f"Processing typically completes within {limits['max_processing_time']//60} minutes",
                "Text documents with business keywords are processed most accurately"
            ]
        }
        
    except Exception as e:
        return {
            "error": f"Failed to get performance metrics: {str(e)}",
            "user_id": current_user.user_id,
            "timestamp": time.time()
        }

@router.get("/limits")
async def get_system_limits():
    """Get current system limits and quotas"""
    return {
        "limits": get_processing_limits(),
        "timestamp": time.time(),
        "description": "Current system limits to ensure optimal performance"
    }

@router.get("/health/processing")
async def get_processing_health(
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Get processing health status for user"""
    try:
        # Check for stuck processing jobs
        stuck_jobs = await db.execute(
            text("""
                SELECT COUNT(*) 
                FROM bronze_contracts 
                WHERE owner_user_id = :user_id 
                AND status = 'processing' 
                AND TIMESTAMPDIFF(MINUTE, updated_at, NOW()) > 15
            """),
            {"user_id": current_user.user_id}
        )
        
        stuck_count = stuck_jobs.scalar()
        
        # Check total processing jobs
        total_processing = await db.execute(
            text("""
                SELECT COUNT(*) 
                FROM bronze_contracts 
                WHERE owner_user_id = :user_id 
                AND status = 'processing'
            """),
            {"user_id": current_user.user_id}
        )
        
        processing_count = total_processing.scalar()
        
        # Determine health status
        if stuck_count > 0:
            health_status = "warning"
            message = f"{stuck_count} documents may be stuck in processing"
        elif processing_count > 5:
            health_status = "caution"
            message = f"{processing_count} documents currently processing"
        else:
            health_status = "healthy"
            message = "All systems operating normally"
        
        return {
            "user_id": current_user.user_id,
            "health_status": health_status,
            "message": message,
            "stuck_jobs": stuck_count,
            "processing_jobs": processing_count,
            "timestamp": time.time(),
            "recommendations": [
                "If documents are stuck, try uploading smaller files",
                "Ensure uploaded files are business documents (contracts, policies, etc.)",
                "Contact support if processing takes longer than 10 minutes"
            ] if stuck_count > 0 else []
        }
        
    except Exception as e:
        return {
            "error": f"Health check failed: {str(e)}",
            "user_id": current_user.user_id,
            "timestamp": time.time()
        }
