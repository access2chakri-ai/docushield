"""
ETL Monitoring Router
Monitor your automatic ETL notebook executions
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, List, Optional
import logging
import boto3
from datetime import datetime, timedelta

from app.core.dependencies import get_current_active_user
from app.core.config import settings

router = APIRouter(prefix="/api/etl-monitoring", tags=["etl-monitoring"])
logger = logging.getLogger(__name__)

@router.get("/dashboard")
async def get_etl_dashboard(
    current_user = Depends(get_current_active_user)
):
    """Get ETL monitoring dashboard for user"""
    try:
        sagemaker_client = boto3.client('sagemaker')
        
        # Get recent ETL jobs for this user
        response = sagemaker_client.list_processing_jobs(
            MaxResults=10,
            SortBy='CreationTime',
            SortOrder='Descending'
        )
        
        # Filter jobs related to DocuShield ETL
        etl_jobs = []
        for job in response.get('ProcessingJobSummaries', []):
            job_name = job['ProcessingJobName']
            if 'docushield' in job_name.lower() and 'etl' in job_name.lower():
                etl_jobs.append({
                    "job_name": job_name,
                    "status": job['ProcessingJobStatus'],
                    "created_at": job['CreationTime'].isoformat(),
                    "last_modified": job['LastModifiedTime'].isoformat()
                })
        
        # Get automation status
        from app.services.auto_export_service import auto_export_service
        
        return {
            "user_id": current_user.user_id,
            "automation_status": {
                "enabled": auto_export_service.enabled,
                "sagemaker_auto_run": auto_export_service.sagemaker_auto_run,
                "notebook": "tidbdata_etl_athena.ipynb"
            },
            "recent_etl_jobs": etl_jobs,
            "data_pipeline": {
                "source": "TiDB (your processed documents)",
                "processing": "SageMaker notebook execution",
                "output": "S3 parquet files",
                "destination": "QuickSight dashboards (user-filtered)"
            },
            "user_data_filtering": {
                "enabled": True,
                "filter_column": "owner_user_id",
                "your_filter_value": current_user.user_id,
                "description": "You only see your own documents and analytics"
            },
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"ETL dashboard failed: {e}")
        raise HTTPException(status_code=500, detail=f"Dashboard failed: {str(e)}")

@router.get("/job-details/{job_name}")
async def get_job_details(
    job_name: str,
    current_user = Depends(get_current_active_user)
):
    """Get detailed information about a specific ETL job"""
    try:
        from app.services.simple_sagemaker_service import simple_sagemaker
        
        job_status = await simple_sagemaker.check_etl_status(job_name)
        
        return {
            "user_id": current_user.user_id,
            "job_details": job_status,
            "output_info": {
                "parquet_location": f"s3://{settings.sagemaker_bucket}/analytics/parquet/",
                "quicksight_refresh": "Automatic after job completion",
                "user_data_filter": f"owner_user_id = '{current_user.user_id}'"
            },
            "monitoring_tips": [
                "✅ Completed: Your dashboards have fresh data",
                "⏳ InProgress: ETL is running, dashboards will update soon",
                "❌ Failed: Check logs, may need manual intervention"
            ]
        }
        
    except Exception as e:
        logger.error(f"Job details failed: {e}")
        raise HTTPException(status_code=500, detail=f"Job details failed: {str(e)}")

@router.post("/trigger-manual-etl")
async def trigger_manual_etl(
    current_user = Depends(get_current_active_user)
):
    """Manually trigger ETL notebook execution"""
    try:
        from app.services.simple_sagemaker_service import simple_sagemaker
        
        # Trigger ETL for this user
        result = await simple_sagemaker.trigger_etl_notebook(
            contract_id="manual_trigger",
            user_id=current_user.user_id
        )
        
        return {
            "user_id": current_user.user_id,
            "trigger_result": result,
            "message": "Manual ETL triggered. Check job status in a few minutes.",
            "monitoring": {
                "check_status_url": f"/api/etl-monitoring/job-details/{result.get('job_name')}",
                "expected_completion": "5-10 minutes",
                "output_location": result.get('expected_output')
            }
        }
        
    except Exception as e:
        logger.error(f"Manual ETL trigger failed: {e}")
        raise HTTPException(status_code=500, detail=f"Manual trigger failed: {str(e)}")

@router.get("/data-freshness")
async def check_data_freshness(
    current_user = Depends(get_current_active_user)
):
    """Check how fresh your dashboard data is"""
    try:
        import boto3
        from datetime import datetime
        
        s3_client = boto3.client('s3')
        bucket_name = settings.sagemaker_bucket
        
        # Check last modified time of parquet files
        try:
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix='analytics/parquet/',
                MaxKeys=10
            )
            
            if 'Contents' in response:
                latest_file = max(response['Contents'], key=lambda x: x['LastModified'])
                last_updated = latest_file['LastModified']
                
                # Calculate freshness
                now = datetime.now(last_updated.tzinfo)
                age_minutes = (now - last_updated).total_seconds() / 60
                
                if age_minutes < 60:
                    freshness = f"🟢 Fresh ({int(age_minutes)} minutes ago)"
                elif age_minutes < 1440:  # 24 hours
                    freshness = f"🟡 Recent ({int(age_minutes/60)} hours ago)"
                else:
                    freshness = f"🔴 Stale ({int(age_minutes/1440)} days ago)"
                
            else:
                freshness = "❓ No data files found"
                last_updated = None
                
        except Exception as s3_error:
            freshness = f"❌ Cannot check S3: {s3_error}"
            last_updated = None
        
        return {
            "user_id": current_user.user_id,
            "data_freshness": freshness,
            "last_etl_run": last_updated.isoformat() if last_updated else None,
            "parquet_location": f"s3://{bucket_name}/analytics/parquet/",
            "recommendations": [
                "🔄 Process a document to trigger automatic ETL",
                "🎯 Use manual trigger if data seems stale",
                "📊 Check QuickSight for latest analytics"
            ]
        }
        
    except Exception as e:
        logger.error(f"Data freshness check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Freshness check failed: {str(e)}")