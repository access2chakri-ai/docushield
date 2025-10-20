"""
User-Specific QuickSight Integration
Ensures users only see their own data in embedded dashboards
"""

import boto3
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.dependencies import get_current_active_user

logger = logging.getLogger(__name__)

class UserSpecificQuickSightService:
    """Service for creating user-specific QuickSight dashboards and embeddings"""
    
    def __init__(self):
        self.quicksight_client = boto3.client('quicksight')
        self.account_id = boto3.client('sts').get_caller_identity()['Account']
        self.region = settings.aws_default_region
        
    async def create_user_specific_dataset(self, user_id: str) -> Dict[str, Any]:
        """Create a QuickSight dataset filtered for specific user"""
        
        try:
            logger.info(f"🎯 Creating user-specific dataset for user {user_id}")
            
            # Dataset configuration with user filter
            dataset_config = {
                "DataSetId": f"docushield-user-{user_id}",
                "Name": f"DocuShield Data - User {user_id}",
                "PhysicalTableMap": {
                    "document_agg": {
                        "S3Source": {
                            "DataSourceArn": f"arn:aws:quicksight:{self.region}:{self.account_id}:datasource/docushield-s3-source",
                            "InputColumns": [
                                {"Name": "contract_id", "Type": "STRING"},
                                {"Name": "owner_user_id", "Type": "STRING"},
                                {"Name": "document_type", "Type": "STRING"},
                                {"Name": "doc_max_risk", "Type": "DECIMAL"},
                                {"Name": "risk_count", "Type": "INTEGER"},
                                {"Name": "created_at", "Type": "DATETIME"},
                                {"Name": "file_size_mb", "Type": "DECIMAL"},
                                {"Name": "processing_time_seconds", "Type": "INTEGER"}
                            ]
                        }
                    },
                    "risk_findings": {
                        "S3Source": {
                            "DataSourceArn": f"arn:aws:quicksight:{self.region}:{self.account_id}:datasource/docushield-s3-source",
                            "InputColumns": [
                                {"Name": "finding_id", "Type": "STRING"},
                                {"Name": "contract_id", "Type": "STRING"},
                                {"Name": "finding_type", "Type": "STRING"},
                                {"Name": "severity_level", "Type": "STRING"},
                                {"Name": "risk_score", "Type": "DECIMAL"},
                                {"Name": "confidence_score", "Type": "DECIMAL"},
                                {"Name": "created_at", "Type": "DATETIME"}
                            ]
                        }
                    }
                },
                "LogicalTableMap": {
                    "user_documents": {
                        "Alias": "UserDocuments",
                        "DataTransforms": [
                            {
                                "FilterOperation": {
                                    "ConditionExpression": f"owner_user_id = '{user_id}'"
                                }
                            }
                        ],
                        "Source": {
                            "PhysicalTableId": "document_agg"
                        }
                    },
                    "user_risks": {
                        "Alias": "UserRisks", 
                        "DataTransforms": [
                            {
                                "FilterOperation": {
                                    "ConditionExpression": f"contract_id IN (SELECT contract_id FROM document_agg WHERE owner_user_id = '{user_id}')"
                                }
                            }
                        ],
                        "Source": {
                            "PhysicalTableId": "risk_findings"
                        }
                    }
                }
            }
            
            # Create the dataset
            response = self.quicksight_client.create_data_set(
                AwsAccountId=self.account_id,
                **dataset_config
            )
            
            logger.info(f"✅ User-specific dataset created: {response['DataSetId']}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Failed to create user dataset: {e}")
            raise
    
    async def generate_user_embed_url(self, user_id: str, dashboard_id: str = None) -> str:
        """Generate embed URL with user-specific data filtering"""
        
        try:
            logger.info(f"🔗 Generating embed URL for user {user_id}")
            
            # If no dashboard specified, use user-specific dashboard
            if not dashboard_id:
                dashboard_id = f"docushield-dashboard-{user_id}"
            
            # Session tags for user identification
            session_tags = [
                {
                    'Key': 'user_id',
                    'Value': user_id
                },
                {
                    'Key': 'access_level',
                    'Value': 'user_data_only'
                }
            ]
            
            # Generate embed URL with user context
            response = self.quicksight_client.generate_embed_url_for_anonymous_user(
                AwsAccountId=self.account_id,
                Namespace='default',
                AuthorizedResourceArns=[
                    f"arn:aws:quicksight:{self.region}:{self.account_id}:dashboard/{dashboard_id}"
                ],
                ExperienceConfiguration={
                    'Dashboard': {
                        'InitialDashboardId': dashboard_id,
                        'FeatureConfigurations': {
                            'StatePersistence': {
                                'Enabled': True
                            }
                        }
                    }
                },
                SessionTags=session_tags,
                SessionLifetimeInMinutes=600  # 10 hours
            )
            
            embed_url = response['EmbedUrl']
            logger.info(f"✅ Embed URL generated for user {user_id}")
            
            return embed_url
            
        except Exception as e:
            logger.error(f"❌ Failed to generate embed URL: {e}")
            raise
    
    async def create_user_dashboard(self, user_id: str) -> Dict[str, Any]:
        """Create a dashboard specifically for a user with their data only"""
        
        try:
            logger.info(f"📊 Creating user-specific dashboard for user {user_id}")
            
            dashboard_id = f"docushield-dashboard-{user_id}"
            
            # Dashboard definition with user-filtered data
            dashboard_definition = {
                "DataSetIdentifierDeclarations": [
                    {
                        "DataSetArn": f"arn:aws:quicksight:{self.region}:{self.account_id}:dataset/docushield-user-{user_id}",
                        "Identifier": "user_data"
                    }
                ],
                "Sheets": [
                    {
                        "SheetId": "risk-overview",
                        "Name": "Risk Overview",
                        "Visuals": [
                            {
                                "BarChartVisual": {
                                    "VisualId": "risk-by-type",
                                    "Title": {
                                        "Visibility": "VISIBLE",
                                        "FormatText": {
                                            "PlainText": "Risk Findings by Type"
                                        }
                                    },
                                    "FieldWells": {
                                        "BarChartAggregatedFieldWells": {
                                            "Category": [
                                                {
                                                    "CategoricalDimensionField": {
                                                        "FieldId": "finding_type",
                                                        "Column": {
                                                            "DataSetIdentifier": "user_data",
                                                            "ColumnName": "finding_type"
                                                        }
                                                    }
                                                }
                                            ],
                                            "Values": [
                                                {
                                                    "NumericalMeasureField": {
                                                        "FieldId": "risk_count",
                                                        "Column": {
                                                            "DataSetIdentifier": "user_data", 
                                                            "ColumnName": "risk_score"
                                                        },
                                                        "AggregationFunction": {
                                                            "SimpleNumericalAggregation": "COUNT"
                                                        }
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                }
                            },
                            {
                                "PieChartVisual": {
                                    "VisualId": "documents-by-type",
                                    "Title": {
                                        "Visibility": "VISIBLE",
                                        "FormatText": {
                                            "PlainText": "Documents by Type"
                                        }
                                    },
                                    "FieldWells": {
                                        "PieChartAggregatedFieldWells": {
                                            "Category": [
                                                {
                                                    "CategoricalDimensionField": {
                                                        "FieldId": "document_type",
                                                        "Column": {
                                                            "DataSetIdentifier": "user_data",
                                                            "ColumnName": "document_type"
                                                        }
                                                    }
                                                }
                                            ],
                                            "Values": [
                                                {
                                                    "NumericalMeasureField": {
                                                        "FieldId": "doc_count",
                                                        "Column": {
                                                            "DataSetIdentifier": "user_data",
                                                            "ColumnName": "contract_id"
                                                        },
                                                        "AggregationFunction": {
                                                            "SimpleNumericalAggregation": "COUNT"
                                                        }
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                }
                            }
                        ]
                    }
                ]
            }
            
            # Create the dashboard
            response = self.quicksight_client.create_dashboard(
                AwsAccountId=self.account_id,
                DashboardId=dashboard_id,
                Name=f"DocuShield Analytics - User {user_id}",
                Definition=dashboard_definition,
                Permissions=[
                    {
                        'Principal': f"arn:aws:quicksight:{self.region}:{self.account_id}:user/default/docushield-user-{user_id}",
                        'Actions': [
                            'quicksight:DescribeDashboard',
                            'quicksight:ListDashboardVersions',
                            'quicksight:QueryDashboard'
                        ]
                    }
                ]
            )
            
            logger.info(f"✅ User dashboard created: {dashboard_id}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Failed to create user dashboard: {e}")
            raise
    
    async def setup_row_level_security(self, user_id: str) -> Dict[str, Any]:
        """Setup Row-Level Security (RLS) for user data isolation"""
        
        try:
            logger.info(f"🔒 Setting up Row-Level Security for user {user_id}")
            
            # Create RLS configuration
            rls_config = {
                "DataSetId": "docushield-main-dataset",
                "RowLevelPermissionDataSet": {
                    "Namespace": "default",
                    "Arn": f"arn:aws:quicksight:{self.region}:{self.account_id}:dataset/docushield-user-permissions",
                    "PermissionPolicy": "GRANT_ACCESS",
                    "FormatVersion": "VERSION_1"
                }
            }
            
            # Apply RLS to dataset
            response = self.quicksight_client.update_data_set(
                AwsAccountId=self.account_id,
                **rls_config
            )
            
            logger.info(f"✅ Row-Level Security configured for user {user_id}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Failed to setup RLS: {e}")
            raise

# Global instance
user_quicksight_service = UserSpecificQuickSightService()