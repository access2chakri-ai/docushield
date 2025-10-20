"""
Automatic Export Service - Real-time S3 sync and SageMaker ETL trigger
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.services.data_export import data_export_service
from app.core.config import settings

logger = logging.getLogger(__name__)

class AutoExportService:
    """Service for automatic real-time data export and SageMaker ETL triggering"""
    
    def __init__(self):
        self.enabled = settings.auto_export_enabled
        self.sagemaker_auto_run = settings.sagemaker_auto_run_enabled
        
    async def trigger_after_document_processing(self, contract_id: str, user_id: str) -> Dict[str, Any]:
        """
        Automatically trigger SageMaker notebook execution after document processing completes
        This should be called from document_processor after gold findings are saved
        """
        if not self.enabled:
            logger.info(f"Auto-export disabled for contract {contract_id}")
            return {"status": "disabled"}
            
        try:
            logger.info(f"🚀 Starting automatic notebook ETL for contract {contract_id}, user {user_id}")
            
            # 1. Trigger SageMaker Notebook Execution (this handles ETL and S3 output)
            notebook_result = None
            if self.sagemaker_auto_run:
                notebook_result = await self._trigger_notebook_execution(user_id, contract_id)
            
            # 2. Update QuickSight data if configured
            quicksight_result = await self._refresh_quicksight_data(user_id)
            
            logger.info(f"✅ Automatic notebook ETL triggered for contract {contract_id}")
            
            return {
                "status": "completed",
                "contract_id": contract_id,
                "user_id": user_id,
                "notebook_execution_result": notebook_result,
                "quicksight_result": quicksight_result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Auto-notebook-ETL failed for contract {contract_id}: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "contract_id": contract_id,
                "user_id": user_id
            }
    
    async def _trigger_notebook_execution(self, user_id: str, contract_id: str) -> Optional[Dict[str, Any]]:
        """Trigger your existing ETL notebook using simplified service"""
        try:
            logger.info(f"📓 Triggering your ETL notebook for contract {contract_id}, user {user_id}")
            
            # Use the simplified SageMaker service
            from app.services.simple_sagemaker_service import simple_sagemaker
            
            result = await simple_sagemaker.trigger_etl_notebook(contract_id, user_id)
            
            logger.info(f"✅ ETL notebook trigger result: {result.get('status')}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Notebook trigger failed for contract {contract_id}: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "contract_id": contract_id,
                "user_id": user_id
            }
    
    async def _refresh_quicksight_data(self, user_id: str) -> Dict[str, Any]:
        """Refresh QuickSight datasets with new data"""
        try:
            logger.info(f"📊 Refreshing QuickSight data for user {user_id}")
            
            from app.services.quicksight_integration import quicksight_service
            
            # Trigger dataset refresh in QuickSight
            refresh_result = await quicksight_service.refresh_user_datasets(user_id)
            
            logger.info(f"✅ QuickSight refresh completed")
            return refresh_result
            
        except Exception as e:
            logger.error(f"❌ QuickSight refresh failed for user {user_id}: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }

# Global instance
auto_export_service = AutoExportService()