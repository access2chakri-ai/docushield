"""Data Export Service for SageMaker Notebooks"""

import pandas as pd
import boto3
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import os
from sqlalchemy import text
from app.database import get_operational_db
from app.models import User, BronzeContract, GoldFinding

logger = logging.getLogger(__name__)

def _rows_to_dataframe(rows) -> Optional[pd.DataFrame]:
    """Safely convert database rows to pandas DataFrame"""
    if not rows:
        return None
    
    data = []
    for row in rows:
        try:
            if hasattr(row, '_mapping'):
                data.append(dict(row._mapping))
            else:
                # Fallback for different row types
                data.append(dict(row))
        except Exception as e:
            logger.warning(f"Failed to convert row to dict: {e}")
            continue
    
    if data:
        return pd.DataFrame(data)
    return None

class DataExportService:
    """Service for exporting DocuShield data to S3 for SageMaker notebooks"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = os.getenv('DOCUSHIELD_ANALYTICS_BUCKET', 'sagemaker-us-east-1-192933326034')
        
    async def export_user_data(self, user_id: str, data_types: List[str] = None) -> Dict[str, Any]:
        """Export user-specific data for notebook analysis"""
        try:
            if data_types is None:
                data_types = ['document_metrics', 'risk_findings', 'user_activity']
            
            exported_files = {}
            
            async for db in get_operational_db():
                for data_type in data_types:
                    if data_type == 'document_metrics':
                        data = await self._export_document_metrics(db, user_id)
                    elif data_type == 'risk_findings':
                        data = await self._export_risk_findings(db, user_id)
                    elif data_type == 'user_activity':
                        data = await self._export_user_activity(db, user_id)
                    else:
                        continue
                    
                    if data is not None and not data.empty:
                        file_key = f"docushield/user-data/{user_id}/{data_type}_{user_id}.csv"
                        s3_url = await self._upload_to_s3(data, file_key)
                        exported_files[data_type] = {
                            'file_key': file_key,
                            's3_url': s3_url,
                            'records_count': len(data)
                        }
            
            return {
                'user_id': user_id,
                'export_timestamp': datetime.now().isoformat(),
                'exported_files': exported_files,
                'bucket': self.bucket_name
            }
            
        except Exception as e:
            logger.error(f"Failed to export data for user {user_id}: {e}")
            raise
    
    async def _export_document_metrics(self, db, user_id: str) -> Optional[pd.DataFrame]:
        """Export document processing metrics for a user"""
        try:
            query = text("""
                SELECT 
                    bc.contract_id as document_id,
                    bc.document_type,
                    bc.file_size,
                    bc.status as processing_status,
                    bc.created_at,
                    bc.updated_at,
                    TIMESTAMPDIFF(SECOND, bc.created_at, bc.updated_at) as processing_time_seconds,
                    COUNT(gf.finding_id) as risk_count,
                    AVG(CASE gf.severity 
                        WHEN 'low' THEN 25 
                        WHEN 'medium' THEN 50 
                        WHEN 'high' THEN 75 
                        WHEN 'critical' THEN 100 
                        ELSE 0 END) as avg_risk_score,
                    MAX(CASE gf.severity 
                        WHEN 'low' THEN 25 
                        WHEN 'medium' THEN 50 
                        WHEN 'high' THEN 75 
                        WHEN 'critical' THEN 100 
                        ELSE 0 END) as max_risk_score
                FROM bronze_contracts bc
                LEFT JOIN gold_findings gf ON bc.contract_id = gf.contract_id
                WHERE bc.owner_user_id = :user_id
                GROUP BY bc.contract_id, bc.document_type, bc.file_size, bc.status, bc.created_at, bc.updated_at
                ORDER BY bc.created_at DESC
            """)
            
            result = await db.execute(query, {"user_id": user_id})
            rows = result.fetchall()
            
            return _rows_to_dataframe(rows)
            
        except Exception as e:
            logger.error(f"Failed to export document metrics: {e}")
            return None
    
    async def _export_risk_findings(self, db, user_id: str) -> Optional[pd.DataFrame]:
        """Export risk findings for a user's documents"""
        try:
            query = text("""
                SELECT 
                    gf.finding_id as risk_id,
                    gf.contract_id as document_id,
                    bc.document_type,
                    gf.finding_type as risk_type,
                    gf.impact_category as risk_category,
                    CASE gf.severity 
                        WHEN 'low' THEN 25 
                        WHEN 'medium' THEN 50 
                        WHEN 'high' THEN 75 
                        WHEN 'critical' THEN 100 
                        ELSE 0 END as risk_score,
                    gf.confidence as confidence_score,
                    gf.severity as severity_level,
                    gf.description,
                    gf.created_at,
                    NULL as location_page,
                    NULL as location_section
                FROM gold_findings gf
                JOIN bronze_contracts bc ON gf.contract_id = bc.contract_id
                WHERE bc.owner_user_id = :user_id
                ORDER BY gf.created_at DESC
            """)
            
            result = await db.execute(query, {"user_id": user_id})
            rows = result.fetchall()
            
            return _rows_to_dataframe(rows)
            
        except Exception as e:
            logger.error(f"Failed to export risk findings: {e}")
            return None
    
    async def _export_user_activity(self, db, user_id: str) -> Optional[pd.DataFrame]:
        """Export user activity patterns"""
        try:
            # This would typically come from activity logs or analytics tables
            # For now, we'll generate sample activity data based on documents
            query = text("""
                SELECT 
                    DATE(bc.created_at) as activity_date,
                    COUNT(*) as documents_processed,
                    AVG(TIMESTAMPDIFF(SECOND, bc.created_at, bc.updated_at)) as avg_processing_time,
                    SUM(TIMESTAMPDIFF(SECOND, bc.created_at, bc.updated_at)) as total_processing_time,
                    COUNT(DISTINCT bc.document_type) as document_types_handled,
                    AVG(CASE gf.severity 
                        WHEN 'low' THEN 25 
                        WHEN 'medium' THEN 50 
                        WHEN 'high' THEN 75 
                        WHEN 'critical' THEN 100 
                        ELSE 0 END) as avg_risk_score
                FROM bronze_contracts bc
                LEFT JOIN gold_findings gf ON bc.contract_id = gf.contract_id
                WHERE bc.owner_user_id = :user_id
                GROUP BY DATE(bc.created_at)
                ORDER BY activity_date DESC
            """)
            
            result = await db.execute(query, {"user_id": user_id})
            rows = result.fetchall()
            
            return _rows_to_dataframe(rows)
            
        except Exception as e:
            logger.error(f"Failed to export user activity: {e}")
            return None
    
    async def _upload_to_s3(self, df: pd.DataFrame, file_key: str) -> str:
        """Upload DataFrame to S3 as CSV"""
        try:
            # Convert DataFrame to CSV
            csv_buffer = df.to_csv(index=False)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_key,
                Body=csv_buffer,
                ContentType='text/csv'
            )
            
            # Return S3 URL
            s3_url = f"s3://{self.bucket_name}/{file_key}"
            logger.info(f"Uploaded data to {s3_url}")
            return s3_url
            
        except Exception as e:
            logger.error(f"Failed to upload to S3: {e}")
            raise
    
    async def create_notebook_config(self, user_id: str, notebook_type: str) -> Dict[str, Any]:
        """Create configuration file for notebook with data connections"""
        try:
            config = {
                "user_id": user_id,
                "notebook_type": notebook_type,
                "data_sources": {
                    "s3_bucket": self.bucket_name,
                    "data_prefix": f"docushield/user-data/{user_id}/",
                    "tidb_connection": {
                        "host": os.getenv('TIDB_OPERATIONAL_HOST'),
                        "port": int(os.getenv('TIDB_OPERATIONAL_PORT', 4000)),
                        "database": os.getenv('TIDB_OPERATIONAL_DATABASE'),
                        "user": os.getenv('TIDB_OPERATIONAL_USER')
                        # Note: Password should be injected via IAM or secrets manager
                    }
                },
                "aws_config": {
                    "region": os.getenv('AWS_REGION', 'us-east-1'),
                    "bucket": self.bucket_name
                },
                "created_at": datetime.now().isoformat()
            }
            
            # Upload config to S3
            config_key = f"docushield/notebook-configs/{user_id}_{notebook_type}_config.json"
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=config_key,
                Body=json.dumps(config, indent=2),
                ContentType='application/json'
            )
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to create notebook config: {e}")
            raise
    
    async def export_aggregated_data(self, data_type: str = 'all') -> Dict[str, Any]:
        """Export aggregated data for system-wide analysis"""
        try:
            exported_files = {}
            
            async for db in get_operational_db():
                if data_type in ['all', 'document_stats']:
                    df = await self._export_document_statistics(db)
                    if df is not None and not df.empty:
                        file_key = f"docushield/analysis-results/document_statistics_{datetime.now().strftime('%Y%m%d')}.csv"
                        s3_url = await self._upload_to_s3(df, file_key)
                        exported_files['document_stats'] = {
                            'file_key': file_key,
                            's3_url': s3_url,
                            'records_count': len(df)
                        }
                
                if data_type in ['all', 'risk_trends']:
                    df = await self._export_risk_trends(db)
                    if df is not None and not df.empty:
                        file_key = f"docushield/analysis-results/risk_trends_{datetime.now().strftime('%Y%m%d')}.csv"
                        s3_url = await self._upload_to_s3(df, file_key)
                        exported_files['risk_trends'] = {
                            'file_key': file_key,
                            's3_url': s3_url,
                            'records_count': len(df)
                        }
            
            return {
                'export_type': 'aggregated',
                'export_timestamp': datetime.now().isoformat(),
                'exported_files': exported_files,
                'bucket': self.bucket_name
            }
            
        except Exception as e:
            logger.error(f"Failed to export aggregated data: {e}")
            raise
    
    async def _export_document_statistics(self, db) -> Optional[pd.DataFrame]:
        """Export system-wide document statistics"""
        try:
            query = text("""
                SELECT 
                    DATE(bc.created_at) as date,
                    bc.document_type,
                    COUNT(*) as document_count,
                    AVG(bc.file_size) as avg_file_size,
                    AVG(TIMESTAMPDIFF(SECOND, bc.created_at, bc.updated_at)) as avg_processing_time,
                    COUNT(DISTINCT bc.owner_user_id) as unique_users,
                    SUM(CASE WHEN bc.status = 'completed' THEN 1 ELSE 0 END) as completed_count,
                    SUM(CASE WHEN bc.status = 'failed' THEN 1 ELSE 0 END) as failed_count
                FROM bronze_contracts bc
                WHERE bc.created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                GROUP BY DATE(bc.created_at), bc.document_type
                ORDER BY date DESC, document_type
            """)
            
            result = await db.execute(query)
            rows = result.fetchall()
            
            return _rows_to_dataframe(rows)
            
        except Exception as e:
            logger.error(f"Failed to export document statistics: {e}")
            return None
    
    async def _export_risk_trends(self, db) -> Optional[pd.DataFrame]:
        """Export risk trend data"""
        try:
            query = text("""
                SELECT 
                    DATE(gf.created_at) as date,
                    gf.finding_type as risk_type,
                    gf.impact_category as risk_category,
                    gf.severity as severity_level,
                    COUNT(*) as risk_count,
                    AVG(CASE gf.severity 
                        WHEN 'low' THEN 25 
                        WHEN 'medium' THEN 50 
                        WHEN 'high' THEN 75 
                        WHEN 'critical' THEN 100 
                        ELSE 0 END) as avg_risk_score,
                    AVG(gf.confidence) as avg_confidence,
                    COUNT(DISTINCT gf.contract_id) as affected_documents
                FROM gold_findings gf
                WHERE gf.created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                GROUP BY DATE(gf.created_at), gf.finding_type, gf.impact_category, gf.severity
                ORDER BY date DESC, risk_type
            """)
            
            result = await db.execute(query)
            rows = result.fetchall()
            
            return _rows_to_dataframe(rows)
            
        except Exception as e:
            logger.error(f"Failed to export risk trends: {e}")
            return None

# Global instance
data_export_service = DataExportService()