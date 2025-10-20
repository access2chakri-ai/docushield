"""
QuickSight Embed URL Router for DocuShield
Handles QuickSight dashboard embedding endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
from app.core.dependencies import get_current_active_user
from app.services.quicksight_integration import quicksight_service
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["quicksight"])

class EmbedUrlRequest(BaseModel):
    dashboardId: str
    userArn: Optional[str] = None

@router.post('/embed-url')
async def generate_embed_url(
    request: EmbedUrlRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Generate QuickSight embed URL endpoint"""
    try:
        dashboard_id = request.dashboardId
        
        if not dashboard_id:
            raise HTTPException(status_code=400, detail="dashboardId is required")
        
        # Use the user ID from the authenticated user
        user_id = current_user.user_id
        
        embed_url = await quicksight_service.generate_dashboard_embed_url(dashboard_id, user_id)
        
        if not embed_url:
            raise HTTPException(
                status_code=500, 
                detail="Failed to generate embed URL. Please check dashboard permissions."
            )
        
        # Check if it's a public URL (fallback) or actual embed URL
        is_embed_url = embed_url.startswith('https://') and 'embed' in embed_url
        
        return {
            'embedUrl': embed_url,
            'expiresInMinutes': 600 if is_embed_url else None,
            'isEmbedUrl': is_embed_url,
            'message': 'Embed URL generated successfully' if is_embed_url else 'Public dashboard URL provided (embedding not available)'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate embed URL for dashboard {request.dashboardId}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get('/dashboards')
async def get_user_dashboards(current_user: User = Depends(get_current_active_user)):
    """Get available dashboards for the current user"""
    try:
        user_id = current_user.user_id
        dashboards = await quicksight_service.get_user_dashboards(user_id)
        
        return {
            'success': True,
            'data': dashboards
        }
        
    except Exception as e:
        logger.error(f"Failed to get dashboards for user {current_user.user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve dashboards: {str(e)}")

@router.get('/status')
async def get_quicksight_status(current_user: User = Depends(get_current_active_user)):
    """Get QuickSight service status"""
    try:
        # Try to list dashboards to check if service is working
        response = await quicksight_service.get_user_dashboards(current_user.user_id)
        
        return {
            'status': 'healthy',
            'service': 'QuickSight',
            'dashboards_available': len(response.get('dashboards', [])),
            'account_id': quicksight_service.account_id,
            'region': quicksight_service.region
        }
        
    except Exception as e:
        logger.error(f"QuickSight status check failed: {str(e)}")
        return {
            'status': 'error',
            'service': 'QuickSight',
            'error': str(e),
            'account_id': quicksight_service.account_id,
            'region': quicksight_service.region
        }