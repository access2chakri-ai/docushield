"""
Analytics and dashboard router for DocuShield API
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from typing import Dict, Any

from app.database import get_operational_db
from app.models import BronzeContract, GoldContractScore, GoldFinding, LlmCall
from app.core.dependencies import get_current_active_user
from app.services.llm_factory import llm_factory

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
        risk_data = [{"risk_level": row[0], "count": row[1]} for row in risk_distribution.fetchall()]
        
        # Recent activity
        recent_contracts = await db.execute(
            select(BronzeContract)
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
            for contract in recent_contracts.scalars().all()
        ]
        
        return {
            "user_id": current_user.user_id,
            "summary": {
                "total_contracts": total_contracts,
                "processed_contracts": sum(item["count"] for item in risk_data if item["risk_level"] != "unprocessed"),
                "high_risk_contracts": next((item["count"] for item in risk_data if item["risk_level"] == "high"), 0)
            },
            "risk_distribution": risk_data,
            "recent_activity": recent_data,
            "provider_usage": llm_factory.usage_stats if hasattr(llm_factory, 'usage_stats') else {}
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
        risk_analysis = await db.execute(
            text("""
                SELECT 
                    bc.contract_id,
                    bc.filename,
                    gcs.overall_score,
                    gcs.risk_level,
                    gcs.category_scores,
                    COUNT(gf.finding_id) as findings_count
                FROM bronze_contracts bc
                LEFT JOIN gold_contract_scores gcs ON bc.contract_id = gcs.contract_id
                LEFT JOIN gold_findings gf ON bc.contract_id = gf.contract_id
                WHERE bc.owner_user_id = :user_id
                GROUP BY bc.contract_id, bc.filename, gcs.overall_score, gcs.risk_level, gcs.category_scores
                ORDER BY gcs.overall_score DESC NULLS LAST
            """),
            {"user_id": current_user.user_id}
        )
        
        contracts = []
        for row in risk_analysis.fetchall():
            contracts.append({
                "contract_id": row[0],
                "filename": row[1],
                "overall_score": row[2],
                "risk_level": row[3],
                "category_scores": row[4],
                "findings_count": row[5]
            })
        
        return {
            "contracts": contracts,
            "total_analyzed": len([c for c in contracts if c["overall_score"] is not None]),
            "average_score": sum(c["overall_score"] for c in contracts if c["overall_score"]) / len(contracts) if contracts else 0
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
