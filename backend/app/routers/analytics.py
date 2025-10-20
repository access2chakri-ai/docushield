"""
Analytics and dashboard router for DocuShield API
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from typing import Dict, Any

from app.database import get_operational_db
from app.models import BronzeContract, GoldContractScore, GoldFinding, LlmCall, User
from app.core.dependencies import get_current_active_user
from app.services.privacy_safe_llm import privacy_safe_llm
from app.services.sagemaker_notebooks import sagemaker_notebooks
from app.services.data_export import data_export_service
from app.services.quicksight_integration import quicksight_service

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/dashboard")
async def get_dashboard_data(
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Get dashboard analytics data"""
    try:
        # Contract statistics
        total_contracts = await db.execute(
            text("SELECT COUNT(*) FROM bronze_contracts WHERE owner_user_id = :user_id"),
            {"user_id": current_user.user_id}
        )
        total_contracts = total_contracts.scalar()
        
        # Risk distribution
        risk_distribution = await db.execute(
            text("""
                SELECT 
                    COALESCE(gcs.risk_level, 'unprocessed') as risk_level,
                    COUNT(*) as count
                FROM bronze_contracts bc
                LEFT JOIN gold_contract_scores gcs ON bc.contract_id = gcs.contract_id
                WHERE bc.owner_user_id = :user_id
                GROUP BY COALESCE(gcs.risk_level, 'unprocessed')
            """),
            {"user_id": current_user.user_id}
        )
        risk_rows = risk_distribution.fetchall()
        risk_data = [{"risk_level": row[0] or "unprocessed", "count": row[1] or 0} for row in risk_rows]
        
        # Recent activity - exclude raw_bytes to prevent memory issues
        recent_contracts = await db.execute(
            select(
                BronzeContract.contract_id,
                BronzeContract.filename,
                BronzeContract.status,
                BronzeContract.created_at
            )
            .where(BronzeContract.owner_user_id == current_user.user_id)
            .order_by(BronzeContract.created_at.desc())
            .limit(5)
        )
        recent_data = [
            {
                "contract_id": contract.contract_id,
                "filename": contract.filename,
                "status": contract.status,
                "created_at": contract.created_at.isoformat()
            }
            for contract in recent_contracts.all()
        ]
        
        processed_contracts = sum(item["count"] for item in risk_data if item["risk_level"] != "unprocessed")
        high_risk_contracts = next((item["count"] for item in risk_data if item["risk_level"] == "high"), 0)
        
        # Get user preferences for personalization
        user_prefs = await db.execute(
            select(User.analytics_preferences, User.preferred_document_types, User.preferred_time_range)
            .where(User.user_id == current_user.user_id)
        )
        user_data = user_prefs.first()
        
        return {
            "user_id": current_user.user_id,
            "summary": {
                "total_contracts": total_contracts or 0,
                "processed_contracts": processed_contracts,
                "high_risk_contracts": high_risk_contracts
            },
            "risk_distribution": risk_data,
            "recent_activity": recent_data,
            "provider_usage": privacy_safe_llm.llm_factory.usage_stats if hasattr(privacy_safe_llm.llm_factory, 'usage_stats') else {},
            "user_preferences": {
                "analytics_preferences": user_data[0] if user_data else {},
                "preferred_document_types": user_data[1] if user_data else [],
                "preferred_time_range": user_data[2] if user_data else "30d"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard data retrieval failed: {str(e)}")

@router.get("/contracts/risk-analysis")
async def get_risk_analysis(
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Get detailed risk analysis across user's contracts"""
    try:
        # Get contracts with risk scores
        # Note: TiDB doesn't support NULLS LAST, so we use CASE to handle nulls
        risk_analysis = await db.execute(
            text("""
                SELECT 
                    bc.contract_id,
                    bc.filename,
                    gcs.overall_score,
                    gcs.risk_level,
                    gcs.category_scores,
                    COALESCE(COUNT(gf.finding_id), 0) as findings_count
                FROM bronze_contracts bc
                LEFT JOIN gold_contract_scores gcs ON bc.contract_id = gcs.contract_id
                LEFT JOIN gold_findings gf ON bc.contract_id = gf.contract_id
                WHERE bc.owner_user_id = :user_id
                GROUP BY bc.contract_id, bc.filename, gcs.overall_score, gcs.risk_level, gcs.category_scores
                ORDER BY CASE WHEN gcs.overall_score IS NULL THEN 1 ELSE 0 END, gcs.overall_score DESC
            """),
            {"user_id": current_user.user_id}
        )
        
        contracts = []
        rows = risk_analysis.fetchall()
        
        for row in rows:
            contracts.append({
                "contract_id": row[0],
                "filename": row[1] or "Unknown",  # Handle null filename
                "overall_score": row[2],
                "risk_level": row[3],
                "category_scores": row[4],
                "findings_count": row[5] or 0  # Handle null count
            })
        
        analyzed_contracts = [c for c in contracts if c["overall_score"] is not None]
        total_analyzed = len(analyzed_contracts)
        average_score = 0
        
        if total_analyzed > 0:
            average_score = sum(c["overall_score"] for c in analyzed_contracts) / total_analyzed
        
        return {
            "contracts": contracts,
            "total_analyzed": total_analyzed,
            "average_score": average_score
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk analysis failed: {str(e)}")

@router.get("/usage/llm")
async def get_llm_usage_stats(
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Get LLM usage statistics for the user"""
    try:
        # Get LLM calls for user's contracts
        llm_usage = await db.execute(
            text("""
                SELECT 
                    lc.provider,
                    lc.model,
                    lc.call_type,
                    COUNT(*) as call_count,
                    SUM(lc.input_tokens) as total_input_tokens,
                    SUM(lc.output_tokens) as total_output_tokens,
                    SUM(lc.estimated_cost) as total_cost,
                    AVG(lc.latency_ms) as avg_latency
                FROM llm_calls lc
                JOIN bronze_contracts bc ON lc.contract_id = bc.contract_id
                WHERE bc.owner_user_id = :user_id
                GROUP BY lc.provider, lc.model, lc.call_type
                ORDER BY total_cost DESC
            """),
            {"user_id": current_user.user_id}
        )
        
        usage_data = []
        for row in llm_usage.fetchall():
            usage_data.append({
                "provider": row[0],
                "model": row[1],
                "call_type": row[2],
                "call_count": row[3],
                "total_input_tokens": row[4] or 0,
                "total_output_tokens": row[5] or 0,
                "total_cost": float(row[6] or 0),
                "avg_latency_ms": float(row[7] or 0)
            })
        
        # Calculate totals
        total_calls = sum(item["call_count"] for item in usage_data)
        total_cost = sum(item["total_cost"] for item in usage_data)
        total_tokens = sum(item["total_input_tokens"] + item["total_output_tokens"] for item in usage_data)
        
        return {
            "user_id": current_user.user_id,
            "summary": {
                "total_calls": total_calls,
                "total_cost": total_cost,
                "total_tokens": total_tokens
            },
            "by_provider": usage_data,
            "cost_breakdown": [
                {"provider": item["provider"], "cost": item["total_cost"]}
                for item in usage_data
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Usage statistics failed: {str(e)}")

# =============================================================================
# 🎯 PERSONALIZATION ENDPOINTS
# =============================================================================

@router.get("/preferences")
async def get_user_preferences(
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Get user's analytics preferences"""
    try:
        user_prefs = await db.execute(
            select(
                User.analytics_preferences,
                User.dashboard_filters, 
                User.preferred_document_types,
                User.preferred_risk_levels,
                User.preferred_time_range
            ).where(User.user_id == current_user.user_id)
        )
        prefs = user_prefs.first()
        
        if not prefs:
            return {"message": "No preferences found"}
            
        return {
            "user_id": current_user.user_id,
            "analytics_preferences": prefs[0] or {},
            "dashboard_filters": prefs[1] or {},
            "preferred_document_types": prefs[2] or [],
            "preferred_risk_levels": prefs[3] or [],
            "preferred_time_range": prefs[4] or "30d"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get preferences: {str(e)}")

@router.post("/preferences")
async def update_user_preferences(
    preferences: Dict[str, Any],
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Update user's analytics preferences"""
    try:
        # Update user preferences
        await db.execute(
            text("""
                UPDATE users SET 
                    analytics_preferences = :analytics_prefs,
                    dashboard_filters = :dashboard_filters,
                    preferred_document_types = :doc_types,
                    preferred_risk_levels = :risk_levels,
                    preferred_time_range = :time_range,
                    updated_at = NOW()
                WHERE user_id = :user_id
            """),
            {
                "user_id": current_user.user_id,
                "analytics_prefs": preferences.get("analytics_preferences", {}),
                "dashboard_filters": preferences.get("dashboard_filters", {}),
                "doc_types": preferences.get("preferred_document_types", []),
                "risk_levels": preferences.get("preferred_risk_levels", []),
                "time_range": preferences.get("preferred_time_range", "30d")
            }
        )
        await db.commit()
        
        return {"message": "Preferences updated successfully"}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update preferences: {str(e)}")

@router.post("/track-interaction")
async def track_dashboard_interaction(
    interaction_data: Dict[str, Any],
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Track user dashboard interactions for learning preferences"""
    try:
        # Get current preferences
        current_prefs = await db.execute(
            select(User.analytics_preferences).where(User.user_id == current_user.user_id)
        )
        prefs = current_prefs.scalar() or {}
        
        # Update interaction tracking
        if "interactions" not in prefs:
            prefs["interactions"] = []
            
        # Add new interaction (keep last 100)
        prefs["interactions"].append({
            "timestamp": interaction_data.get("timestamp"),
            "action": interaction_data.get("action"),
            "filters_used": interaction_data.get("filters", {}),
            "time_spent": interaction_data.get("time_spent", 0)
        })
        
        # Keep only last 100 interactions
        prefs["interactions"] = prefs["interactions"][-100:]
        
        # Update in database
        await db.execute(
            text("UPDATE users SET analytics_preferences = :prefs WHERE user_id = :user_id"),
            {"user_id": current_user.user_id, "prefs": prefs}
        )
        await db.commit()
        
        return {"message": "Interaction tracked"}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to track interaction: {str(e)}")

@router.get("/personalized-dashboard")
async def get_personalized_dashboard(
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Get dashboard data with user's preferred filters applied"""
    try:
        # Get user preferences
        user_prefs = await db.execute(
            select(
                User.preferred_document_types,
                User.preferred_risk_levels,
                User.preferred_time_range
            ).where(User.user_id == current_user.user_id)
        )
        prefs = user_prefs.first()
        
        # Apply user preferences to queries
        doc_types_filter = ""
        if prefs and prefs[0]:  # preferred_document_types
            doc_types = "', '".join(prefs[0])
            doc_types_filter = f"AND bc.document_type IN ('{doc_types}')"
            
        time_range_filter = "AND bc.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)"
        if prefs and prefs[2]:  # preferred_time_range
            if prefs[2] == "7d":
                time_range_filter = "AND bc.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
            elif prefs[2] == "90d":
                time_range_filter = "AND bc.created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)"
        
        # Get personalized contract statistics
        personalized_stats = await db.execute(
            text(f"""
                SELECT 
                    COUNT(*) as total_contracts,
                    COUNT(CASE WHEN gcs.risk_level IS NOT NULL THEN 1 END) as processed_contracts,
                    COUNT(CASE WHEN gcs.risk_level = 'high' THEN 1 END) as high_risk_contracts
                FROM bronze_contracts bc
                LEFT JOIN gold_contract_scores gcs ON bc.contract_id = gcs.contract_id
                WHERE bc.owner_user_id = :user_id {doc_types_filter} {time_range_filter}
            """),
            {"user_id": current_user.user_id}
        )
        stats = personalized_stats.first()
        
        return {
            "user_id": current_user.user_id,
            "personalized_summary": {
                "total_contracts": stats[0] or 0,
                "processed_contracts": stats[1] or 0,
                "high_risk_contracts": stats[2] or 0,
                "applied_filters": {
                    "document_types": prefs[0] if prefs else [],
                    "time_range": prefs[2] if prefs else "30d"
                }
            },
            "recommendations": [
                "Based on your activity, you might want to review high-risk contracts",
                "Consider setting up alerts for critical risk findings"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Personalized dashboard failed: {str(e)}")

# =============================================================================
# 📊 SAGEMAKER NOTEBOOKS ENDPOINTS
# =============================================================================

@router.get("/notebooks/templates")
async def get_notebook_templates(
    current_user = Depends(get_current_active_user)
):
    """Get available SageMaker notebook templates for analytics"""
    try:
        templates = sagemaker_notebooks.get_notebook_templates()
        
        return {
            "templates": templates,
            "user_id": current_user.user_id,
            "message": "Available analytics notebook templates"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get templates: {str(e)}")

@router.post("/create-sample-data")
async def create_sample_data(
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Create sample data for testing analytics export"""
    try:
        from app.models import Document, RiskFinding
        from datetime import datetime, timedelta
        import uuid
        
        # Create sample documents
        sample_docs = []
        for i in range(5):
            doc = Document(
                document_id=str(uuid.uuid4()),
                user_id=current_user.user_id,
                document_type=['contract', 'invoice', 'legal'][i % 3],
                file_size=1000 + (i * 500),
                processing_status='completed',
                created_at=datetime.now() - timedelta(days=i),
                updated_at=datetime.now() - timedelta(days=i) + timedelta(minutes=5)
            )
            sample_docs.append(doc)
            db.add(doc)
        
        await db.commit()
        
        # Create sample risk findings
        for i, doc in enumerate(sample_docs):
            risk = RiskFinding(
                risk_id=str(uuid.uuid4()),
                document_id=doc.document_id,
                risk_type=['financial', 'legal', 'compliance'][i % 3],
                risk_category='high_risk',
                risk_score=50 + (i * 10),
                confidence_score=0.8 + (i * 0.05),
                severity_level=['LOW', 'MEDIUM', 'HIGH'][i % 3],
                description=f'Sample risk finding {i+1}',
                created_at=datetime.now() - timedelta(days=i),
                location_page=1,
                location_section='header'
            )
            db.add(risk)
        
        await db.commit()
        
        return {
            "status": "success",
            "message": f"Created {len(sample_docs)} sample documents and {len(sample_docs)} risk findings",
            "user_id": current_user.user_id
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create sample data: {str(e)}")

@router.post("/test-export")
async def test_data_export(
    current_user = Depends(get_current_active_user)
):
    """Test data export to S3"""
    try:
        # Export user data directly
        export_result = await data_export_service.export_user_data(
            user_id=current_user.user_id,
            data_types=['document_metrics', 'risk_findings', 'user_activity']
        )
        
        return {
            "status": "success",
            "export_result": export_result,
            "message": f"Data exported to S3 for user {current_user.user_id}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export test failed: {str(e)}")

@router.post("/notebooks/connect")
async def connect_to_notebook(
    template_data: Dict[str, Any],
    current_user = Depends(get_current_active_user)
):
    """Connect to existing SageMaker notebook instance"""
    try:
        template_id = template_data.get("template_id", "shared-analysis")
        
        # Connect to existing notebook instance
        result = await sagemaker_notebooks.get_existing_notebook_instance(
            user_id=current_user.user_id,
            template_id=template_id
        )
        
        # Prepare user data for the notebook
        try:
            data_info = await sagemaker_notebooks.prepare_user_data(
                user_id=current_user.user_id,
                template_id=template_id
            )
            result["data_info"] = data_info
        except Exception as data_error:
            # Don't fail connection if data prep fails
            result["data_info"] = {"error": f"Data preparation failed: {str(data_error)}"}
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to notebook: {str(e)}")

@router.get("/notebooks")
async def list_user_notebooks(
    current_user = Depends(get_current_active_user)
):
    """List all notebook instances for the current user"""
    try:
        notebooks = await sagemaker_notebooks.list_user_notebooks(current_user.user_id)
        
        return {
            "notebooks": notebooks,
            "user_id": current_user.user_id,
            "total_count": len(notebooks)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list notebooks: {str(e)}")

@router.get("/notebooks/{notebook_name}/status")
async def get_notebook_status(
    notebook_name: str,
    current_user = Depends(get_current_active_user)
):
    """Get the status of a specific notebook instance"""
    try:
        # Verify notebook belongs to user
        if f"-{current_user.user_id}-" not in notebook_name:
            raise HTTPException(status_code=403, detail="Access denied to this notebook")
        
        status = await sagemaker_notebooks.get_notebook_status(notebook_name)
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get notebook status: {str(e)}")

@router.post("/notebooks/{notebook_name}/stop")
async def stop_notebook_instance(
    notebook_name: str,
    current_user = Depends(get_current_active_user)
):
    """Stop a notebook instance to save costs"""
    try:
        # Allow access to DocuShield-Analysis for all users
        if notebook_name != "DocuShield-Analysis":
            raise HTTPException(status_code=403, detail="Access denied to this notebook")
        
        result = await sagemaker_notebooks.stop_notebook_instance(notebook_name)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop notebook: {str(e)}")

@router.post("/notebooks/{notebook_name}/start")
async def start_notebook_instance(
    notebook_name: str,
    current_user = Depends(get_current_active_user)
):
    """Start a stopped notebook instance"""
    try:
        # Allow access to DocuShield-Analysis for all users
        if notebook_name != "DocuShield-Analysis":
            raise HTTPException(status_code=403, detail="Access denied to this notebook")
        
        result = await sagemaker_notebooks.start_notebook_instance(notebook_name)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start notebook: {str(e)}")

@router.delete("/notebooks/{notebook_name}")
async def delete_notebook_instance(
    notebook_name: str,
    current_user = Depends(get_current_active_user)
):
    """Delete a notebook instance permanently"""
    try:
        # Verify notebook belongs to user
        if f"-{current_user.user_id}-" not in notebook_name:
            raise HTTPException(status_code=403, detail="Access denied to this notebook")
        
        result = await sagemaker_notebooks.delete_notebook_instance(notebook_name)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete notebook: {str(e)}")

@router.get("/notebooks/cost-estimate")
async def get_notebook_cost_estimate(
    instance_type: str = "ml.t3.medium",
    current_user = Depends(get_current_active_user)
):
    """Get cost estimates for running SageMaker notebooks"""
    try:
        estimate = await sagemaker_notebooks.get_notebook_cost_estimate(instance_type)
        
        return estimate
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cost estimate: {str(e)}")

# =============================================================================
# 📊 QUICKSIGHT INTEGRATION ENDPOINTS
# =============================================================================

@router.get("/quicksight/dashboards")
async def get_quicksight_dashboards(
    current_user = Depends(get_current_active_user)
):
    """Get QuickSight dashboards for the current user"""
    try:
        dashboards = await quicksight_service.get_user_dashboards(current_user.user_id)
        
        return {
            "status": "success",
            "dashboards": dashboards,
            "user_id": current_user.user_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get QuickSight dashboards: {str(e)}")

@router.get("/quicksight/embed-url/{dashboard_id}")
async def get_dashboard_embed_url(
    dashboard_id: str,
    current_user = Depends(get_current_active_user)
):
    """Get embed URL for a specific QuickSight dashboard with user-specific data filtering"""
    try:
        from app.services.user_specific_quicksight import user_quicksight_service
        
        # Generate user-specific embed URL (filters data to user's documents only)
        embed_url = await user_quicksight_service.generate_user_embed_url(
            user_id=current_user.user_id,
            dashboard_id=dashboard_id
        )
        
        if embed_url:
            return {
                "status": "success",
                "dashboard_id": dashboard_id,
                "embed_url": embed_url,
                "user_id": current_user.user_id,
                "data_scope": "user_documents_only",
                "expires_in_minutes": 600
            }
        else:
            raise HTTPException(status_code=404, detail="Dashboard not found or access denied")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate embed URL: {str(e)}")

@router.post("/quicksight/refresh-data")
async def refresh_quicksight_data(
    current_user = Depends(get_current_active_user)
):
    """Refresh QuickSight data by re-exporting from TiDB"""
    try:
        # First, export fresh data to S3
        export_result = await data_export_service.export_user_data(
            user_id=current_user.user_id,
            data_types=['document_metrics', 'risk_findings', 'user_activity']
        )
        
        # Then get updated dashboards
        dashboards = await quicksight_service.get_user_dashboards(current_user.user_id)
        
        return {
            "status": "success",
            "message": "Data refreshed successfully",
            "export_result": export_result,
            "dashboards": dashboards
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh QuickSight data: {str(e)}")

@router.post("/embed-url")
async def generate_embed_url(
    request_data: Dict[str, Any],
    current_user = Depends(get_current_active_user)
):
    """Generate QuickSight embed URL for registered users"""
    try:
        dashboard_id = request_data.get('dashboardId')
        user_arn = request_data.get('userArn')
        
        if not dashboard_id:
            raise HTTPException(status_code=400, detail="dashboardId is required")
        
        # If user_arn is provided, use registered user embedding
        if user_arn:
            embed_url = quicksight_service.get_embed_url_for_registered_user(dashboard_id, user_arn)
        else:
            # Fall back to anonymous embedding
            embed_url = await quicksight_service.generate_dashboard_embed_url(dashboard_id, current_user.user_id)
        
        if embed_url:
            return {
                "status": "success",
                "embedUrl": embed_url,
                "expiresInMinutes": 600
            }
        else:
            raise HTTPException(status_code=404, detail="Failed to generate embed URL")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate embed URL: {str(e)}")

@router.get("/quicksight/user-arn")
async def get_user_arn(
    current_user = Depends(get_current_active_user)
):
    """Get or create QuickSight user ARN for the current user"""
    try:
        # Try to get existing user ARN
        user_arn = quicksight_service.get_user_arn(current_user.user_id)
        
        if not user_arn:
            # Create new QuickSight user if doesn't exist
            user_arn = quicksight_service.create_quicksight_user(
                current_user.user_id, 
                current_user.email if hasattr(current_user, 'email') else f"user-{current_user.user_id}@docushield.com"
            )
        
        if user_arn:
            return {
                "status": "success",
                "userArn": user_arn,
                "userId": current_user.user_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to get or create QuickSight user")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user ARN: {str(e)}")
