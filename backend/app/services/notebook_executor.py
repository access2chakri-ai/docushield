"""
SageMaker Notebook Remote Execution Service
Automatically executes Jupyter notebooks remotely after document processing
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import boto3
import json

from app.core.config import settings

logger = logging.getLogger(__name__)

class NotebookExecutorService:
    """Service for remotely executing SageMaker notebooks"""
    
    def __init__(self):
        self.sagemaker_client = boto3.client('sagemaker')
        self.s3_client = boto3.client('s3')
        self.bucket_name = settings.sagemaker_bucket
        
    async def execute_etl_notebook(self, contract_id: str, user_id: str) -> Dict[str, Any]:
        """
        Execute the ETL notebook remotely for a specific contract
        """
        try:
            logger.info(f"🚀 Executing ETL notebook for contract {contract_id}, user {user_id}")
            
            # Method 1: Use SageMaker Processing Job with notebook execution
            result = await self._execute_via_processing_job(contract_id, user_id)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Notebook execution failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "contract_id": contract_id,
                "user_id": user_id
            }
    
    async def _execute_via_processing_job(self, contract_id: str, user_id: str) -> Dict[str, Any]:
        """Execute notebook using SageMaker Processing Job"""
        
        job_name = f"docushield-notebook-{contract_id}-{int(datetime.now().timestamp())}"
        
        # Environment variables for the notebook
        env_vars = {
            'CONTRACT_ID': contract_id,
            'USER_ID': user_id,
            'TIDB_OPERATIONAL_HOST': settings.tidb_operational_host,
            'TIDB_OPERATIONAL_PORT': str(settings.tidb_operational_port),
            'TIDB_OPERATIONAL_USER': settings.tidb_operational_user,
            'TIDB_OPERATIONAL_PASSWORD': settings.tidb_operational_password,
            'TIDB_OPERATIONAL_DATABASE': settings.tidb_operational_database,
            'OUTPUT_S3': f's3://{self.bucket_name}/docushield/analytics',
            'SINCE_DAYS': '1'  # Process recent data
        }
        
        try:
            response = self.sagemaker_client.create_processing_job(
                ProcessingJobName=job_name,
                ProcessingResources={
                    'ClusterConfig': {
                        'InstanceCount': 1,
                        'InstanceType': 'ml.t3.medium',
                        'VolumeSizeInGB': 20
                    }
                },
                AppSpecification={
                    'ImageUri': '763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:1.12.0-cpu-py38-ubuntu20.04-sagemaker',
                    'ContainerEntrypoint': ['python3'],
                    'ContainerArguments': [
                        '/opt/ml/processing/code/execute_notebook.py'
                    ]
                },
                Environment=env_vars,
                ProcessingInputs=[
                    {
                        'InputName': 'notebook',
                        'S3Input': {
                            'S3Uri': f's3://{self.bucket_name}/docushield/notebooks/docushield_etl_notebook.ipynb',
                            'LocalPath': '/opt/ml/processing/input',
                            'S3DataType': 'S3Prefix',
                            'S3InputMode': 'File'
                        }
                    },
                    {
                        'InputName': 'executor',
                        'S3Input': {
                            'S3Uri': f's3://{self.bucket_name}/docushield/notebooks/execute_notebook.py',
                            'LocalPath': '/opt/ml/processing/code',
                            'S3DataType': 'S3Prefix',
                            'S3InputMode': 'File'
                        }
                    }
                ],
                ProcessingOutputConfig={
                    'Outputs': [
                        {
                            'OutputName': 'analytics-data',
                            'S3Output': {
                                'S3Uri': f's3://{self.bucket_name}/docushield/analytics/',
                                'LocalPath': '/opt/ml/processing/output',
                                'S3UploadMode': 'EndOfJob'
                            }
                        },
                        {
                            'OutputName': 'executed-notebook',
                            'S3Output': {
                                'S3Uri': f's3://{self.bucket_name}/docushield/executed-notebooks/',
                                'LocalPath': '/opt/ml/processing/executed',
                                'S3UploadMode': 'EndOfJob'
                            }
                        }
                    ]
                },
                RoleArn=settings.sagemaker_execution_role,
                Tags=[
                    {'Key': 'Project', 'Value': 'DocuShield'},
                    {'Key': 'Type', 'Value': 'NotebookETL'},
                    {'Key': 'ContractId', 'Value': contract_id},
                    {'Key': 'UserId', 'Value': user_id}
                ]
            )
            
            logger.info(f"✅ Notebook execution job started: {job_name}")
            
            return {
                "status": "started",
                "processing_job_name": job_name,
                "job_arn": response.get('ProcessingJobArn'),
                "job_type": "notebook_execution",
                "contract_id": contract_id,
                "user_id": user_id,
                "notebook_path": f's3://{self.bucket_name}/docushield/notebooks/docushield_etl_notebook.ipynb'
            }
            
        except Exception as e:
            logger.error(f"❌ Processing job creation failed: {e}")
            raise
    
    async def _execute_via_notebook_instance(self, contract_id: str, user_id: str) -> Dict[str, Any]:
        """Execute notebook on existing SageMaker notebook instance (alternative method)"""
        
        notebook_instance_name = "DocuShield-Analysis"
        
        try:
            # Check if notebook instance exists and is running
            response = self.sagemaker_client.describe_notebook_instance(
                NotebookInstanceName=notebook_instance_name
            )
            
            status = response['NotebookInstanceStatus']
            
            if status != 'InService':
                logger.warning(f"Notebook instance {notebook_instance_name} is not running (status: {status})")
                return {
                    "status": "failed",
                    "error": f"Notebook instance not available (status: {status})",
                    "contract_id": contract_id,
                    "user_id": user_id
                }
            
            # Create execution script
            execution_script = self._create_execution_script(contract_id, user_id)
            
            # Upload execution script to S3
            script_key = f"docushield/execution-scripts/execute_{contract_id}_{int(datetime.now().timestamp())}.py"
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=script_key,
                Body=execution_script,
                ContentType='text/x-python'
            )
            
            logger.info(f"📤 Execution script uploaded to s3://{self.bucket_name}/{script_key}")
            
            # Note: Direct notebook execution would require additional setup
            # For now, we'll return the script location for manual execution
            
            return {
                "status": "script_ready",
                "notebook_instance": notebook_instance_name,
                "execution_script": f"s3://{self.bucket_name}/{script_key}",
                "contract_id": contract_id,
                "user_id": user_id,
                "instructions": [
                    f"1. Open {notebook_instance_name} notebook instance",
                    f"2. Download execution script from s3://{self.bucket_name}/{script_key}",
                    "3. Run the script to execute ETL notebook",
                    "4. Check S3 for output data"
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ Notebook instance execution failed: {e}")
            raise
    
    def _create_execution_script(self, contract_id: str, user_id: str) -> str:
        """Create Python script to execute the notebook"""
        
        script = f'''#!/usr/bin/env python3
"""
Auto-generated script to execute DocuShield ETL notebook
Contract ID: {contract_id}
User ID: {user_id}
Generated: {datetime.now().isoformat()}
"""

import os
import subprocess
import sys

# Set environment variables
os.environ['CONTRACT_ID'] = '{contract_id}'
os.environ['USER_ID'] = '{user_id}'
os.environ['TIDB_OPERATIONAL_HOST'] = '{settings.tidb_operational_host}'
os.environ['TIDB_OPERATIONAL_PORT'] = '{settings.tidb_operational_port}'
os.environ['TIDB_OPERATIONAL_USER'] = '{settings.tidb_operational_user}'
os.environ['TIDB_OPERATIONAL_PASSWORD'] = '{settings.tidb_operational_password}'
os.environ['TIDB_OPERATIONAL_DATABASE'] = '{settings.tidb_operational_database}'
os.environ['OUTPUT_S3'] = 's3://{self.bucket_name}/docushield/analytics'
os.environ['SINCE_DAYS'] = '1'

print("🚀 Starting DocuShield ETL Notebook Execution")
print(f"📄 Contract ID: {contract_id}")
print(f"👤 User ID: {user_id}")

try:
    # Execute notebook using papermill or nbconvert
    notebook_path = "/home/ec2-user/SageMaker/docushield_etl_notebook.ipynb"
    output_path = f"/home/ec2-user/SageMaker/executed_notebooks/etl_{{contract_id}}_{{int(datetime.now().timestamp())}}.ipynb"
    
    # Install required packages
    subprocess.run([sys.executable, "-m", "pip", "install", "papermill", "-q"], check=True)
    
    # Execute notebook
    subprocess.run([
        "papermill", 
        notebook_path, 
        output_path,
        "--log-output"
    ], check=True)
    
    print("✅ Notebook execution completed successfully")
    print(f"📄 Output notebook: {{output_path}}")
    
except subprocess.CalledProcessError as e:
    print(f"❌ Notebook execution failed: {{e}}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {{e}}")
    sys.exit(1)
'''
        
        return script
    
    async def get_execution_status(self, job_name: str) -> Dict[str, Any]:
        """Get status of notebook execution job"""
        
        try:
            response = self.sagemaker_client.describe_processing_job(
                ProcessingJobName=job_name
            )
            
            status = response['ProcessingJobStatus']
            
            result = {
                "job_name": job_name,
                "status": status,
                "creation_time": response.get('CreationTime'),
                "last_modified_time": response.get('LastModifiedTime')
            }
            
            if status == 'Failed':
                result["failure_reason"] = response.get('FailureReason', 'Unknown')
            
            if status == 'Completed':
                result["processing_end_time"] = response.get('ProcessingEndTime')
                result["output_location"] = f"s3://{self.bucket_name}/docushield/analytics/"
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to get job status: {e}")
            return {
                "job_name": job_name,
                "status": "unknown",
                "error": str(e)
            }

# Global instance
notebook_executor = NotebookExecutorService()