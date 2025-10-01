"""
AWS Bedrock Agent Runtime Handler for Document Search
Minimal runtime wrapper for the DocumentSearchAgent
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

from app.agents.search_agent import DocumentSearchAgent
from app.agents.base_agent import AgentContext


async def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Bedrock Agent runtime handler for document search
    
    Args:
        event: Event payload containing inputs or direct query/contract_id
        context: AWS Lambda context (unused in this implementation)
    
    Returns:
        Dict containing agent result in Bedrock-compatible format
    """
    try:
        # Extract inputs from event
        inputs = event.get("inputs") or {}
        query = inputs.get("query") or event.get("query")
        contract_id = inputs.get("contract_id") or event.get("contract_id")
        user_id = inputs.get("user_id") or event.get("user_id", "default-user")
        
        # Validate required inputs
        if not query:
            return {
                "status": "FAILED",
                "error_message": "Query is required",
                "confidence": 0.0,
                "findings": [],
                "recommendations": [],
                "llm_calls": 0,
                "data_sources": []
            }
        
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
            # Create agent context
            ctx = AgentContext(
                contract_id=contract_id,
                user_id=user_id,
                query=query
            )
            
            # Initialize and run agent
            agent = DocumentSearchAgent()
            result = await agent.analyze(ctx)
            
            # Return result in Bedrock-compatible format
            return {
                "status": result.status.value if hasattr(result.status, 'value') else str(result.status),
                "confidence": result.confidence,
                "findings": result.findings,
                "recommendations": result.recommendations,
                "llm_calls": result.llm_calls,
                "data_sources": result.data_sources,
                "warnings": getattr(result, 'warnings', []),
                "metrics": getattr(result, 'metrics', {}),
                "raw": getattr(result, 'raw', {}),
                "error_message": result.error_message,
            }
        
        # Run async function directly (we'll make the handler async)
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