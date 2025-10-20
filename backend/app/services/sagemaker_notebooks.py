"""
SageMaker Notebooks Service for DocuShield Analytics
Manages cloud-based Jupyter notebooks for advanced analytics
"""

import boto3
import json
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)

class SageMakerNotebookService:
    """Service for managing SageMaker notebook instances for DocuShield analytics"""
    
    def __init__(self):
        self.sagemaker_client = boto3.client('sagemaker', region_name=settings.aws_default_region)
        self.s3_client = boto3.client('s3', region_name=settings.aws_default_region)
        self.notebook_bucket = os.getenv('DOCUSHIELD_ANALYTICS_BUCKET', 'sagemaker-us-east-1-192933326034')
        self.instance_type = "ml.t3.medium"  # Cost-effective for analytics
        
    def get_notebook_templates(self) -> List[Dict[str, Any]]:
        """Get available notebook templates for DocuShield analytics"""
        
        templates = [
            {
                "id": "risk-analysis",
                "name": "Document Risk Analysis",
                "description": "Analyze risk patterns across your document portfolio",
                "category": "Risk Management",
                "estimated_time": "15-30 minutes",
                "features": [
                    "Risk distribution analysis",
                    "Document type risk correlation", 
                    "Trend analysis over time",
                    "Custom risk scoring models"
                ],
                "notebook_file": "risk_analysis_template.ipynb"
            },
            {
                "id": "user-productivity",
                "name": "User Productivity Analytics", 
                "description": "Analyze user behavior and productivity patterns",
                "category": "Performance",
                "estimated_time": "20-40 minutes",
                "features": [
                    "User activity analysis",
                    "Processing time optimization",
                    "Productivity benchmarking",
                    "Workflow efficiency insights"
                ],
                "notebook_file": "user_productivity_template.ipynb"
            },
            {
                "id": "document-classification",
                "name": "Document Classification ML",
                "description": "Train ML models to automatically classify document types",
                "category": "Machine Learning",
                "estimated_time": "45-60 minutes",
                "features": [
                    "Feature extraction from documents",
                    "Classification model training",
                    "Model evaluation and tuning",
                    "Deployment preparation"
                ],
                "notebook_file": "document_classification_ml.ipynb"
            },
            {
                "id": "trend-forecasting",
                "name": "Document Trend Forecasting",
                "description": "Predict future document volumes and risk patterns",
                "category": "Forecasting",
                "estimated_time": "30-45 minutes",
                "features": [
                    "Time series analysis",
                    "Volume forecasting",
                    "Risk trend prediction",
                    "Seasonal pattern detection"
                ],
                "notebook_file": "trend_forecasting_template.ipynb"
            }
        ]
        
        return templates
    
    async def get_existing_notebook_instance(self, user_id: str, template_id: str) -> Dict[str, Any]:
        """Connect to existing SageMaker notebook instance instead of creating new ones"""
        
        try:
            # Use the existing DocuShield-Analysis instance
            existing_notebook_name = "DocuShield-Analysis"
            
            # Get the status of the existing notebook
            status_info = await self.get_notebook_status(existing_notebook_name)
            
            if not status_info:
                raise Exception(f"Existing notebook '{existing_notebook_name}' not found")
            
            logger.info(f"Using existing notebook instance {existing_notebook_name} for user {user_id}")
            
            return {
                "notebook_name": existing_notebook_name,
                "status": status_info.get("status", "Unknown"),
                "template_id": template_id,
                "message": f"Using existing notebook instance '{existing_notebook_name}'. " + 
                          ("Ready to use!" if status_info.get("status") == "InService" 
                           else f"Current status: {status_info.get('status')}")
            }
            
        except Exception as e:
            logger.error(f"Failed to connect to existing notebook instance: {e}")
            raise Exception(f"Failed to connect to notebook: {str(e)}")
    
    async def get_notebook_status(self, notebook_name: str) -> Dict[str, Any]:
        """Get the status of a notebook instance"""
        
        try:
            response = self.sagemaker_client.describe_notebook_instance(
                NotebookInstanceName=notebook_name
            )
            
            status = response['NotebookInstanceStatus']
            
            result = {
                "notebook_name": notebook_name,
                "status": status,
                "instance_type": response.get('InstanceType'),
                "created_at": response.get('CreationTime', '').isoformat() if response.get('CreationTime') else None,
                "last_modified": response.get('LastModifiedTime', '').isoformat() if response.get('LastModifiedTime') else None
            }
            
            # Add notebook URL if available
            if status == 'InService':
                result["notebook_url"] = response.get('Url')
                result["message"] = "Notebook is ready to use!"
            elif status == 'Pending':
                result["message"] = "Notebook is starting up..."
            elif status == 'Stopping':
                result["message"] = "Notebook is shutting down..."
            elif status == 'Stopped':
                result["message"] = "Notebook is stopped. You can start it again."
            elif status == 'Failed':
                result["message"] = "Notebook failed to start. Please try again."
                result["failure_reason"] = response.get('FailureReason', 'Unknown error')
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get notebook status: {e}")
            return {
                "notebook_name": notebook_name,
                "status": "Unknown",
                "message": f"Failed to get status: {str(e)}"
            }
    
    async def list_user_notebooks(self, user_id: str) -> List[Dict[str, Any]]:
        """List available notebook instances (using existing DocuShield-Analysis instance)"""
        
        try:
            # Return the existing DocuShield-Analysis instance
            existing_notebook_name = "DocuShield-Analysis"
            status_info = await self.get_notebook_status(existing_notebook_name)
            
            if status_info:
                return [{
                    "notebook_name": existing_notebook_name,
                    "status": status_info.get("status", "Unknown"),
                    "instance_type": status_info.get("instance_type", "ml.t3.medium"),
                    "created_at": status_info.get("created_at"),
                    "last_modified": status_info.get("last_modified"),
                    "template_id": "shared-analysis",
                    "url": status_info.get("notebook_url"),
                    "shared": True,
                    "description": "Shared DocuShield analytics notebook instance"
                }]
            else:
                return []
            
        except Exception as e:
            logger.error(f"Failed to list notebooks: {e}")
            return []
    
    async def stop_notebook_instance(self, notebook_name: str) -> Dict[str, Any]:
        """Stop a notebook instance to save costs"""
        
        try:
            self.sagemaker_client.stop_notebook_instance(
                NotebookInstanceName=notebook_name
            )
            
            logger.info(f"Stopping notebook instance {notebook_name}")
            
            return {
                "notebook_name": notebook_name,
                "status": "Stopping",
                "message": "Notebook is shutting down to save costs."
            }
            
        except Exception as e:
            logger.error(f"Failed to stop notebook: {e}")
            return {
                "notebook_name": notebook_name,
                "status": "Error",
                "message": f"Failed to stop notebook: {str(e)}"
            }
    
    async def start_notebook_instance(self, notebook_name: str) -> Dict[str, Any]:
        """Start a stopped notebook instance"""
        
        try:
            self.sagemaker_client.start_notebook_instance(
                NotebookInstanceName=notebook_name
            )
            
            logger.info(f"Starting notebook instance {notebook_name}")
            
            return {
                "notebook_name": notebook_name,
                "status": "Pending",
                "message": "Notebook is starting up. This usually takes 2-3 minutes."
            }
            
        except Exception as e:
            logger.error(f"Failed to start notebook: {e}")
            return {
                "notebook_name": notebook_name,
                "status": "Error", 
                "message": f"Failed to start notebook: {str(e)}"
            }
    
    async def delete_notebook_instance(self, notebook_name: str) -> Dict[str, Any]:
        """Delete a notebook instance permanently"""
        
        try:
            self.sagemaker_client.delete_notebook_instance(
                NotebookInstanceName=notebook_name
            )
            
            logger.info(f"Deleting notebook instance {notebook_name}")
            
            return {
                "notebook_name": notebook_name,
                "status": "Deleting",
                "message": "Notebook is being deleted permanently."
            }
            
        except Exception as e:
            logger.error(f"Failed to delete notebook: {e}")
            return {
                "notebook_name": notebook_name,
                "status": "Error",
                "message": f"Failed to delete notebook: {str(e)}"
            }
    
    def _get_sagemaker_execution_role(self) -> str:
        """Get the IAM role for SageMaker execution"""
        # This should be configured in your settings
        return getattr(settings, 'sagemaker_execution_role_arn', 
                      f"arn:aws:iam::{settings.aws_account_id}:role/SageMakerExecutionRole")
    
    def _get_notebook_repository_url(self) -> str:
        """Get the Git repository URL for notebook templates"""
        # This could be your private repo with DocuShield-specific templates
        return getattr(settings, 'notebook_repository_url',
                      "https://github.com/docushield/analytics-notebooks.git")
    
    async def prepare_user_data(self, user_id: str, template_id: str) -> Dict[str, Any]:
        """Prepare user-specific data for notebook analysis"""
        try:
            from app.services.data_export import data_export_service
            
            # Export user data to S3
            export_result = await data_export_service.export_user_data(
                user_id=user_id,
                data_types=['document_metrics', 'risk_findings', 'user_activity']
            )
            
            # Create notebook configuration
            config = await data_export_service.create_notebook_config(user_id, template_id)
            
            return {
                "user_id": user_id,
                "template_id": template_id,
                "data_export": export_result,
                "notebook_config": config,
                "data_location": f"s3://{self.notebook_bucket}/docushield/user-data/{user_id}/",
                "connection_info": {
                    "s3_bucket": self.notebook_bucket,
                    "region": settings.aws_default_region,
                    "config_file": f"docushield/notebook-configs/{user_id}_{template_id}_config.json"
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to prepare data for user {user_id}: {e}")
            raise

    async def get_notebook_cost_estimate(self, instance_type: str = None) -> Dict[str, Any]:
        """Get cost estimates for running notebooks"""
        
        instance_type = instance_type or self.instance_type
        
        # Rough AWS pricing estimates (update with current rates)
        hourly_costs = {
            "ml.t3.medium": 0.0464,   # $0.0464/hour
            "ml.t3.large": 0.0928,    # $0.0928/hour  
            "ml.m5.large": 0.115,     # $0.115/hour
            "ml.m5.xlarge": 0.23,     # $0.23/hour
        }
        
        hourly_cost = hourly_costs.get(instance_type, 0.10)
        
        return {
            "instance_type": instance_type,
            "hourly_cost_usd": hourly_cost,
            "daily_cost_usd": hourly_cost * 24,
            "monthly_cost_usd": hourly_cost * 24 * 30,
            "recommendations": [
                "Stop notebooks when not in use to save costs",
                "Use ml.t3.medium for basic analytics (most cost-effective)",
                "Upgrade to ml.m5.large only for heavy ML workloads"
            ]
        }

# Global instance
sagemaker_notebooks = SageMakerNotebookService()