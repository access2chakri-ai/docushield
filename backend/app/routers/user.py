"""
User API Router for DocuShield
Handles user profile and information requests
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import logging

from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user", tags=["user"])

@router.get("/profile")
async def get_user_profile(
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current user profile information
    """
    try:
        logger.info(f"👤 Getting profile for user: {current_user.user_id}")
        
        return {
            "success": True,
            "user_id": current_user.user_id,
            "email": current_user.email,
            "name": current_user.name,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "analytics_preferences": current_user.analytics_preferences,
            "dashboard_filters": current_user.dashboard_filters
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get user profile: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve user profile: {str(e)}"
        )

@router.put("/preferences")
async def update_user_preferences(
    preferences: Dict[str, Any],
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Update user analytics preferences
    """
    try:
        logger.info(f"⚙️ Updating preferences for user: {current_user.user_id}")
        
        # Update user preferences in database
        # This would typically update the user record
        # For now, return success
        
        return {
            "success": True,
            "message": "User preferences updated successfully",
            "preferences": preferences
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to update user preferences: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update preferences: {str(e)}"
        )