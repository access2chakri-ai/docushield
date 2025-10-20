"""
AWS Bedrock Agent Runtime Handler for Document Analysis
Minimal runtime wrapper for the DocumentAnalysisAgent
"""
import asyncio
import sys
import os
from typing import Dict, Any

# Add backend to path for imports
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(THIS_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.agents.document_analyzer import DocumentAnalysisAgent
from app.agents.base_agent import AgentContext, AgentPriority


async def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Bedrock Agent runtime handler for document analysis
    
    Args:
        event: Event payload containing inputs or direct contract_id/user_id
        context: AWS Lambda context (unused in this implementation)
    
    Returns:
        Dict containing agent result in Bedrock-compatible format
    """
    try:
        # Extract inputs from event
        inputs = event.get("inputs") or {}
        contract_id = inputs.get("contract_id") or event.get("contract_id")
        user_id = inputs.get("user_id") or event.get("user_id", "default-user")
        query = inputs.get("query") or event.get("query")
        document_type = inputs.get("document_type") or event.get("document_type")
        priority = inputs.get("priority") or event.get("priority", "MEDIUM")
        
        # Validate required inputs
        if not contract_id:
            return {
                "status": "FAILED", 
                "error_message": "Contract ID is required",
                "confidence": 0.0,
                "findings": [],
                "recommendations": [],
                "llm_calls": 0,
                "data_sources": []
            }
        
        async def _run():
            # Map priority string to enum
            priority_map = {
                "LOW": AgentPriority.LOW,
                "MEDIUM": AgentPriority.MEDIUM,
                "HIGH": AgentPriority.HIGH,
                "CRITICAL": AgentPriority.CRITICAL
            }
            
            # Create agent context
            ctx = AgentContext(
                contract_id=contract_id,
                user_id=user_id,
                query=query,
                document_type=document_type,
                priority=priority_map.get(priority.upper(), AgentPriority.MEDIUM)
            )
            
            # Initialize and run agent
            agent = DocumentAnalysisAgent()
            result = await agent.analyze(ctx)
            
            # Return result in Bedrock-compatible format
            return {
                "status": result.status.value if hasattr(result.status, 'value') else str(result.status),
                "confidence": result.confidence,
                "findings": result.findings,
                "recommendations": result.recommendations,
                "llm_calls": result.llm_calls,
                "data_sources": result.data_sources,
                "execution_time_ms": getattr(result, 'execution_time_ms', 0.0),
                "memory_usage_mb": getattr(result, 'memory_usage_mb', 0.0),
                "agent_name": getattr(result, 'agent_name', 'document_analysis_agent'),
                "agent_version": getattr(result, 'agent_version', '3.0.0'),
                "error_message": result.error_message,
            }
        
        # Run async function directly
        return await _run()
        
    except Exception as e:
        # Return error in Bedrock-compatible format
        return {
            "status": "FAILED",
            "error_message": f"Runtime handler error: {str(e)}",
            "confidence": 0.0,
            "findings": [],
            "recommendations": [],
            "llm_calls": 0,
            "data_sources": []
        }