"""
Simplified SageMaker Service for DocuShield
Focused on your specific use case: automatic ETL notebook execution
"""

import boto3
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

from app.core.config import settings

logger = logging.getLogger(__name__)

class SimpleSageMakerService:
    """
    Streamlined SageMaker service focused on your ETL notebook automation
    """
    
    def __init__(self):
        self.sagemaker_client = boto3.client('sagemaker')
        self.s3_client = boto3.client('s3')
        self.bucket_name = settings.sagemaker_bucket
        self.notebook_name = "tidbdata_etl_athena.ipynb"
        self.notebook_path_in_jupyter = "/home/ec2-user/SageMaker/utils/tidbdata_etl_athena.ipynb"
        
    async def trigger_etl_notebook(self, contract_id: str, user_id: str) -> Dict[str, Any]:
        """
        Trigger your existing ETL notebook in SageMaker instance (no S3 download needed)
        """
        try:
            logger.info(f"🚀 Triggering ETL notebook in SageMaker instance for new data (contract: {contract_id})")
            
            # Use SageMaker API to execute notebook directly on existing instance
            notebook_instance_name = "DocuShield-Analysis"  # Your SageMaker instance name
            
            # Check if notebook instance is running
            try:
                response = self.sagemaker_client.describe_notebook_instance(
                    NotebookInstanceName=notebook_instance_name
                )
                
                status = response['NotebookInstanceStatus']
                
                if status != 'InService':
                    return {
                        "status": "failed",
                        "error": f"SageMaker instance {notebook_instance_name} is not running (status: {status})",
                        "message": "Please start your SageMaker notebook instance first"
                    }
                
                # Create execution trigger via SageMaker API
                # Since we can't directly execute notebooks via API, we'll use a webhook/API approach
                execution_id = f"etl-{contract_id}-{int(datetime.now().timestamp())}"
                
                # Store trigger info in S3 for the notebook to pick up
                trigger_info = {
                    "execution_id": execution_id,
                    "contract_id": contract_id,
                    "user_id": user_id,
                    "trigger_time": datetime.now().isoformat(),
                    "trigger_reason": "new_document_processed",
                    "notebook_path": self.notebook_path_in_jupyter,
                    "tidb_config": {
                        "host": settings.tidb_operational_host,
                        "port": settings.tidb_operational_port,
                        "user": settings.tidb_operational_user,
                        "password": settings.tidb_operational_password,
                        "database": settings.tidb_operational_database
                    }
                }
                
                # Save trigger file to S3 for notebook to detect
                import json
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=f"docushield/triggers/etl_trigger_{execution_id}.json",
                    Body=json.dumps(trigger_info, indent=2),
                    ContentType='application/json'
                )
                
                logger.info(f"✅ ETL trigger created: {execution_id}")
                
                return {
                    "status": "triggered",
                    "execution_id": execution_id,
                    "notebook_instance": notebook_instance_name,
                    "notebook_path": self.notebook_path_in_jupyter,
                    "trigger_file": f"s3://{self.bucket_name}/docushield/triggers/etl_trigger_{execution_id}.json",
                    "message": "Trigger created. Your notebook can check S3 triggers folder and execute ETL.",
                    "instructions": [
                        "1. Your notebook should check s3://bucket/triggers/ for new trigger files",
                        "2. When found, execute your ETL process",
                        "3. Update parquet files as usual",
                        "4. Delete the trigger file when done"
                    ]
                }
                
            except Exception as sagemaker_error:
                logger.error(f"❌ SageMaker instance check failed: {sagemaker_error}")
                return {
                    "status": "failed",
                    "error": str(sagemaker_error),
                    "message": "Could not access SageMaker notebook instance"
                }
            
        except Exception as e:
            logger.error(f"❌ ETL notebook trigger failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "contract_id": contract_id,
                "user_id": user_id
            }
    
    async def check_etl_status(self, job_name: str) -> Dict[str, Any]:
        """Check status of your ETL notebook execution"""
        try:
            response = self.sagemaker_client.describe_processing_job(
                ProcessingJobName=job_name
            )
            
            status = response['ProcessingJobStatus']
            
            result = {
                "job_name": job_name,
                "status": status,
                "started_at": response.get('CreationTime'),
                "last_updated": response.get('LastModifiedTime')
            }
            
            if status == 'Completed':
                result.update({
                    "completed_at": response.get('ProcessingEndTime'),
                    "parquet_location": f"s3://{self.bucket_name}/analytics/parquet/",
                    "message": "✅ ETL completed! Your QuickSight dashboards should show updated data."
                })
            elif status == 'Failed':
                result.update({
                    "failure_reason": response.get('FailureReason', 'Unknown error'),
                    "message": "❌ ETL failed. Check logs for details."
                })
            elif status in ['InProgress', 'Starting']:
                result["message"] = "⏳ ETL notebook is running..."
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to check ETL status: {e}")
            return {
                "job_name": job_name,
                "status": "unknown",
                "error": str(e)
            }
    
    async def setup_notebook_files(self) -> Dict[str, Any]:
        """
        Upload your notebook and runner script to S3
        Run this once to set up the automation
        """
        try:
            logger.info("📤 Setting up notebook files in S3...")
            
            # Upload the runner script
            with open("notebook_templates/run_notebook.py", "rb") as f:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key="notebooks/run_notebook.py",
                    Body=f.read(),
                    ContentType='text/x-python'
                )
            
            logger.info("✅ Notebook automation setup complete")
            
            return {
                "status": "setup_complete",
                "files_uploaded": [
                    f"s3://{self.bucket_name}/notebooks/run_notebook.py"
                ],
                "next_steps": [
                    f"1. Upload your {self.notebook_name} to s3://{self.bucket_name}/utils/",
                    "2. Ensure your notebook reads from TiDB and outputs parquet to S3",
                    "3. Automation will trigger after each document processing"
                ],
                "notebook_location": {
                    "jupyter_lab_path": self.notebook_path_in_jupyter,
                    "s3_upload_target": f"s3://{self.bucket_name}/utils/{self.notebook_name}",
                    "upload_command": f"aws s3 cp {self.notebook_path_in_jupyter} s3://{self.bucket_name}/utils/"
                },
                "message": "Ready for automatic ETL execution!"
            }
            
        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            return {
                "status": "setup_failed",
                "error": str(e)
            }

# Global instance
simple_sagemaker = SimpleSageMakerService()