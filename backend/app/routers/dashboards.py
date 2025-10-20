"""
Dashboard API Router for DocuShield
Handles user-specific QuickSight dashboard requests
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional
import logging

from app.services.quicksight_integration import quicksight_service
from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["dashboards"])

@router.get("/dashboards")
async def get_user_dashboards(
    user_id: Optional[str] = Query(None, description="User ID for filtering dashboards"),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get QuickSight dashboards for the current user
    Returns user-specific dashboards with embed URLs
    """
    try:
        # Use provided user_id or fall back to current user
        target_user_id = user_id or current_user.user_id
        
        logger.info(f"🔍 Getting dashboards for user: {target_user_id}")
        
        # Security check: users can only access their own dashboards
        if target_user_id != current_user.user_id:
            raise HTTPException(
                status_code=403, 
                detail="Access denied: You can only view your own dashboards"
            )
        
        # Get user-specific dashboards from QuickSight
        dashboards_data = await quicksight_service.get_user_dashboards(target_user_id)
        
        return {
            "success": True,
            "data": dashboards_data,
            "message": f"Retrieved {dashboards_data['total_count']} dashboard(s) for user {target_user_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get dashboards for user {target_user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve dashboards: {str(e)}"
        )

@router.post("/embed-url")
async def get_dashboard_embed_url(
    request: Dict[str, str],
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Generate user-specific embed URL for a QuickSight dashboard
    """
    try:
        dashboard_id = request.get("dashboardId")
        if not dashboard_id:
            raise HTTPException(status_code=400, detail="dashboardId is required")
        
        user_id = current_user.user_id
        logger.info(f"🔗 Generating embed URL for dashboard {dashboard_id}, user {user_id}")
        
        # Generate user-specific embed URL
        embed_url = await quicksight_service.generate_dashboard_embed_url(
            dashboard_id=dashboard_id,
            user_id=user_id
        )
        
        if not embed_url:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate embed URL"
            )
        
        return {
            "success": True,
            "embedUrl": embed_url,
            "dashboardId": dashboard_id,
            "userId": user_id,
            "message": "Embed URL generated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to generate embed URL: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate embed URL: {str(e)}"
        )

@router.get("/status")
async def get_quicksight_status(
    user_id: Optional[str] = Query(None, description="User ID for status check"),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get QuickSight service status for the user
    """
    try:
        target_user_id = user_id or current_user.user_id
        
        # Security check
        if target_user_id != current_user.user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You can only check your own status"
            )
        
        logger.info(f"📊 Checking QuickSight status for user: {target_user_id}")
        
        # Get user dashboards to check availability
        dashboards_data = await quicksight_service.get_user_dashboards(target_user_id)
        
        status = {
            "status": "healthy" if dashboards_data['total_count'] > 0 else "no_data",
            "user_id": target_user_id,
            "dashboards_available": dashboards_data['total_count'],
            "service": "QuickSight",
            "timestamp": "2024-10-19T18:37:34Z"
        }
        
        if dashboards_data['total_count'] == 0:
            status["message"] = "No dashboards available. Process some documents to generate analytics."
        else:
            status["message"] = f"QuickSight is healthy with {dashboards_data['total_count']} dashboard(s)"
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to check QuickSight status: {e}")
        return {
            "status": "error",
            "user_id": target_user_id,
            "dashboards_available": 0,
            "error": str(e),
            "message": "Failed to check QuickSight status"
        }

@router.post("/refresh-datasets")
async def refresh_user_datasets(
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Refresh QuickSight datasets for the current user
    Useful after new documents are processed
    """
    try:
        user_id = current_user.user_id
        logger.info(f"🔄 Refreshing datasets for user: {user_id}")
        
        # Refresh user-specific datasets
        refresh_result = await quicksight_service.refresh_user_datasets(user_id)
        
        return {
            "success": True,
            "data": refresh_result,
            "message": "Dataset refresh initiated successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to refresh datasets for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh datasets: {str(e)}"
        )