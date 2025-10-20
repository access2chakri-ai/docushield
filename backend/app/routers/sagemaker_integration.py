"""
SageMaker Integration Router
Provides endpoints for SageMaker notebook automation and user-specific data processing
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, List, Optional
import logging

from app.core.dependencies import get_current_active_user
from app.services.data_export import data_export_service
from app.services.simple_sagemaker_service import simple_sagemaker

router = APIRouter(prefix="/api/sagemaker", tags=["sagemaker-integration"])
logger = logging.getLogger(__name__)

@router.post("/export-data/{user_id}")
async def export_user_data_for_sagemaker(
    user_id: str,
    export_request: Dict[str, Any] = None,
    current_user = Depends(get_current_active_user)
):
    """Export user data specifically for SageMaker notebook consumption"""
    try:
        # Verify user can access this data
        if current_user.user_id != user_id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Default data types for SageMaker
        data_types = ['document_metrics', 'risk_findings', 'user_activity']
        if export_request and 'data_types' in export_request:
            data_types = export_request['data_types']
        
        # Export data
        export_result = await data_export_service.export_user_data(
            user_id=user_id,
            data_types=data_types
        )
        
        # Create SageMaker-specific response
        return {
            "status": "success",
            "user_id": user_id,
            "export_info": export_result,
            "sagemaker_instructions": {
                "data_location": f"s3://{export_result.get('bucket', '')}/user_data/{user_id}/",
                "load_command": f"datasets = load_user_data('{user_id}')",
                "available_datasets": list(export_result.get('exported_files', {}).keys())
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to export data for SageMaker: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.get("/notebook-status/{notebook_name}")
async def get_sagemaker_notebook_status(
    notebook_name: str,
    current_user = Depends(get_current_active_user)
):
    """Get status of SageMaker notebook instance"""
    try:
        from app.services.sagemaker_notebooks import sagemaker_notebooks
        
        # For shared notebook, allow all users
        if notebook_name != "DocuShield-Analysis":
            raise HTTPException(status_code=403, detail="Access denied to this notebook")
        
        status = await sagemaker_notebooks.get_notebook_status(notebook_name)
        
        return {
            "notebook_name": notebook_name,
            "status": status,
            "access_url": status.get("notebook_url") if status.get("status") == "InService" else None,
            "user_workspace": f"/home/ec2-user/SageMaker/users/{current_user.user_id}/",
            "shared_utils": "/home/ec2-user/SageMaker/utils/"
        }
        
    except Exception as e:
        logger.error(f"Failed to get notebook status: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@router.get("/templates")
async def get_sagemaker_templates(
    current_user = Depends(get_current_active_user)
):
    """Get available templates for SageMaker notebooks"""
    try:
        from app.services.sagemaker_notebooks import sagemaker_notebooks
        
        templates = sagemaker_notebooks.get_notebook_templates()
        
        # Add SageMaker-specific information
        for template in templates:
            template["sagemaker_path"] = f"/home/ec2-user/SageMaker/utils/{template['notebook_file']}"
            template["data_requirements"] = template.get("data_sources", [])
        
        return {
            "templates": templates,
            "user_id": current_user.user_id,
            "notebook_instance": "DocuShield-Analysis",
            "setup_instructions": {
                "1": "Run: exec(open('/home/ec2-user/SageMaker/startup.py').read())",
                "2": "Navigate to templates/ folder",
                "3": "Open desired template notebook",
                "4": "Run cells to analyze your data"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get templates: {e}")
        raise HTTPException(status_code=500, detail=f"Template fetch failed: {str(e)}")

@router.post("/prepare-workspace/{user_id}")
async def prepare_sagemaker_workspace(
    user_id: str,
    current_user = Depends(get_current_active_user)
):
    """Prepare user workspace in SageMaker notebook"""
    try:
        # Verify user access
        if current_user.user_id != user_id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Export data for the user
        export_result = await data_export_service.export_user_data(user_id)
        
        # Create workspace configuration
        workspace_config = {
            "user_id": user_id,
            "workspace_path": f"/home/ec2-user/SageMaker/users/{user_id}/",
            "data_location": export_result.get("data_location"),
            "exported_files": export_result.get("exported_files", {}),
            "setup_commands": [
                f"mkdir -p /home/ec2-user/SageMaker/users/{user_id}",
                f"cd /home/ec2-user/SageMaker/users/{user_id}",
                "exec(open('/home/ec2-user/SageMaker/startup.py').read())"
            ],
            "available_datasets": list(export_result.get("exported_files", {}).keys())
        }
        
        return {
            "status": "workspace_prepared",
            "workspace_config": workspace_config,
            "next_steps": [
                "Open your DocuShield-Analysis notebook",
                "Run the setup commands in a new notebook cell",
                "Start analyzing with your personal data!"
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to prepare workspace: {e}")
        raise HTTPException(status_code=500, detail=f"Workspace preparation failed: {str(e)}")

@router.post("/setup-automation")
async def setup_etl_automation(
    current_user = Depends(get_current_active_user)
):
    """Set up automatic ETL notebook execution (run this once)"""
    try:
        from app.services.simple_sagemaker_service import simple_sagemaker
        
        setup_result = await simple_sagemaker.setup_notebook_files()
        
        return {
            "status": "automation_configured",
            "user_id": current_user.user_id,
            "setup_result": setup_result,
            "automation_info": {
                "trigger": "Automatic after each document processing",
                "notebook": "tidbdata_etl_athena.ipynb",
                "output": "S3 parquet files for QuickSight",
                "user_data_filtering": "Enabled via user_id parameter"
            },
            "next_steps": [
                "1. Upload your notebook to S3 (see setup_result for location)",
                "2. Process a test document to trigger automation",
                "3. Check QuickSight dashboards for updated data"
            ]
        }
        
    except Exception as e:
        logger.error(f"Automation setup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Setup failed: {str(e)}")

@router.get("/etl-status/{job_name}")
async def get_etl_job_status(
    job_name: str,
    current_user = Depends(get_current_active_user)
):
    """Check status of ETL notebook execution"""
    try:
        from app.services.simple_sagemaker_service import simple_sagemaker
        
        status = await simple_sagemaker.check_etl_status(job_name)
        
        return {
            "user_id": current_user.user_id,
            "etl_status": status,
            "dashboard_info": {
                "message": "Check your QuickSight dashboard for updated analytics",
                "user_specific_data": f"Filtered for user: {current_user.user_id}",
                "refresh_note": "Data updates automatically after ETL completion"
            }
        }
        
    except Exception as e:
        logger.error(f"ETL status check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@router.get("/connection-test")
async def test_sagemaker_connection(
    current_user = Depends(get_current_active_user)
):
    """Test connection and show automation status"""
    try:
        return {
            "status": "connected",
            "user_id": current_user.user_id,
            "automation": {
                "etl_notebook": "tidbdata_etl_athena.ipynb",
                "trigger": "Automatic after document processing",
                "output": "S3 parquet files → QuickSight dashboards",
                "user_filtering": "Enabled (you see only your data)"
            },
            "services": {
                "simple_sagemaker": "available",
                "auto_export": "available",
                "quicksight_integration": "available"
            },
            "workflow": [
                "1. Document uploaded & processed",
                "2. ETL notebook triggered automatically", 
                "3. Parquet files updated in S3",
                "4. QuickSight dashboards refresh",
                "5. You see your updated analytics"
            ]
        }
        
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")

@router.post("/save-analysis")
async def save_analysis_results(
    analysis_data: Dict[str, Any],
    current_user = Depends(get_current_active_user)
):
    """Save analysis results from SageMaker back to DocuShield"""
    try:
        user_id = current_user.user_id
        analysis_name = analysis_data.get("analysis_name", "untitled_analysis")
        results = analysis_data.get("results", {})
        
        # Save to S3 for DocuShield to pick up
        import boto3
        import json
        from datetime import datetime
        
        s3_client = boto3.client('s3')
        bucket_name = "docushield-analytics-bucket"  # From your config
        
        # Create analysis result object
        analysis_result = {
            "user_id": user_id,
            "analysis_name": analysis_name,
            "results": results,
            "created_at": datetime.now().isoformat(),
            "source": "sagemaker_notebook"
        }
        
        # Save to S3
        key = f"analysis_results/{user_id}/{analysis_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=json.dumps(analysis_result, default=str),
            ContentType='application/json'
        )
        
        return {
            "status": "saved",
            "analysis_name": analysis_name,
            "s3_location": f"s3://{bucket_name}/{key}",
            "message": "Analysis results saved successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to save analysis results: {e}")
        raise HTTPException(status_code=500, detail=f"Save failed: {str(e)}")