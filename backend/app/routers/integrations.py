"""
External integrations router for DocuShield API
"""
from fastapi import APIRouter, HTTPException, Depends

from app.core.dependencies import get_current_active_user
from app.services.google_drive import google_drive_service
from app.services.external_integrations import external_integrations

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

@router.post("/google-drive/sync")
async def sync_google_drive(current_user = Depends(get_current_active_user)):
    """Trigger Google Drive synchronization"""
    try:
        results = await google_drive_service.sync_documents()
        return {
            "user_id": current_user.user_id,
            "sync_results": results,
            "message": "Google Drive sync completed"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google Drive sync failed: {str(e)}")

@router.get("/google-drive/status")
async def get_google_drive_status(current_user = Depends(get_current_active_user)):
    """Get Google Drive integration status"""
    try:
        # Check if Google Drive service is configured
        is_configured = hasattr(google_drive_service, 'service') and google_drive_service.service is not None
        
        return {
            "user_id": current_user.user_id,
            "google_drive": {
                "configured": is_configured,
                "status": "active" if is_configured else "not_configured",
                "last_sync": getattr(google_drive_service, 'last_sync', None)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google Drive status check failed: {str(e)}")

@router.post("/alerts/test")
async def test_alert_integrations(current_user = Depends(get_current_active_user)):
    """Test external alert integrations"""
    try:
        results = await external_integrations.test_integrations()
        return {
            "user_id": current_user.user_id,
            "integration_status": results,
            "message": "Integration test completed"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Integration test failed: {str(e)}")

@router.get("/alerts/status")
async def get_alert_status(current_user = Depends(get_current_active_user)):
    """Get alert integration status"""
    try:
        # Check integration statuses
        status = {
            "slack": {
                "configured": bool(getattr(external_integrations, 'slack_client', None)),
                "status": "active"
            },
            "email": {
                "configured": bool(getattr(external_integrations, 'sendgrid_client', None)),
                "status": "active"
            },
            "webhook": {
                "configured": True,
                "status": "active"
            }
        }
        
        return {
            "user_id": current_user.user_id,
            "integrations": status
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alert status check failed: {str(e)}")

@router.post("/slack/notify")
async def send_slack_notification(
    message: str,
    channel: str = "#general",
    current_user = Depends(get_current_active_user)
):
    """Send a test notification to Slack"""
    try:
        result = await external_integrations.send_slack_alert(
            message=message,
            channel=channel,
            user_id=current_user.user_id
        )
        
        return {
            "user_id": current_user.user_id,
            "message": "Slack notification sent",
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Slack notification failed: {str(e)}")
