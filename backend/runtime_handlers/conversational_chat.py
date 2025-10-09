"""
AWS Bedrock Agent Runtime Handler for Conversational Chat
Minimal runtime wrapper for the ConversationalAgent
"""
import asyncio
import sys
import os
from typing import Dict, Any, List, Optional

# Add backend to path for imports
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(THIS_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.agents.conversational_agent import ConversationalAgent
from app.agents.base_agent import AgentContext


async def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Bedrock Agent runtime handler for conversational chat
    
    Args:
        event: Event payload containing inputs or direct query/document_id
        context: AWS Lambda context (unused in this implementation)
    
    Returns:
        Dict containing agent result in Bedrock-compatible format
    """
    try:
        # Extract inputs from event
        inputs = event.get("inputs") or {}
        query = inputs.get("query") or event.get("query")
        document_id = inputs.get("document_id") or event.get("document_id") or inputs.get("contract_id") or event.get("contract_id")
        user_id = inputs.get("user_id") or event.get("user_id", "default-user")
        document_type = inputs.get("document_type") or event.get("document_type", "contract")
        chat_mode = inputs.get("chat_mode") or event.get("chat_mode", "documents")
        search_all_documents = inputs.get("search_all_documents") or event.get("search_all_documents", False)
        conversation_history = inputs.get("conversation_history") or event.get("conversation_history", [])
        use_external_data = inputs.get("use_external_data") or event.get("use_external_data", True)
        max_response_length = inputs.get("max_response_length") or event.get("max_response_length", 1000)
        
        # Validate required inputs
        if not query:
            return {
                "status": "FAILED",
                "error_message": "Query is required",
                "confidence": 0.0,
                "findings": [],
                "recommendations": [],
                "llm_calls": 0,
                "data_sources": [],
                "response": "Query parameter is required for conversational chat",
                "chat_mode": chat_mode,
                "document_context": False
            }
        
        # Validate chat mode requirements
        if chat_mode == "documents" and not document_id and not search_all_documents:
            return {
                "status": "COMPLETED",
                "error_message": None,
                "confidence": 1.0,
                "findings": [{
                    "type": "mode_restriction",
                    "title": "Document selection required",
                    "severity": "info",
                    "description": "Please select a document or enable 'Search All Documents' to ask questions about your documents. For general questions, switch to 'General Mode'.",
                    "requires_document": True
                }],
                "recommendations": [
                    "Upload a document to get specific analysis",
                    "Enable 'Search All Documents' for multi-document queries",
                    "Switch to 'General Mode' for non-document questions"
                ],
                "llm_calls": 0,
                "data_sources": ["system_guidance"],
                "response": "Please select a document or enable 'Search All Documents' to ask questions about your documents. For general questions, switch to 'General Mode'.",
                "chat_mode": chat_mode,
                "document_context": False
            }
        
        async def _run():
            # Create agent context with metadata
            ctx = AgentContext(
                contract_id=document_id or "no_document",
                user_id=user_id,
                query=query,
                document_type=document_type,
                metadata={
                    "chat_mode": chat_mode,
                    "search_all_documents": search_all_documents,
                    "conversation_history": conversation_history,
                    "use_external_data": use_external_data,
                    "max_response_length": max_response_length
                }
            )
            
            # Initialize and run agent
            agent = ConversationalAgent()
            result = await agent.analyze(ctx)
            
            # Extract response from findings
            response_text = ""
            enhanced_with_external = False
            
            for finding in result.findings:
                if finding.get("type") in ["document_chat_response", "enhanced_response", "ai_response", "document_guidance"]:
                    response_text = finding.get("description", "")
                    if finding.get("enhanced_with_external", False):
                        enhanced_with_external = True
                    break
            
            # Fallback response
            if not response_text:
                if result.findings:
                    response_text = result.findings[0].get("description", "I processed your query but couldn't generate a specific response.")
                else:
                    response_text = "I'm having trouble processing your query right now. Please try rephrasing or contact support."
            
            # Return result in Bedrock-compatible format with conversational extensions
            return {
                "status": result.status.value if hasattr(result.status, 'value') else str(result.status),
                "confidence": result.confidence,
                "findings": result.findings,
                "recommendations": result.recommendations,
                "llm_calls": result.llm_calls,
                "data_sources": result.data_sources,
                "execution_time_ms": getattr(result, 'execution_time_ms', 0.0),
                "memory_usage_mb": getattr(result, 'memory_usage_mb', 0.0),
                "agent_name": getattr(result, 'agent_name', 'conversational_agent'),
                "agent_version": getattr(result, 'agent_version', '2.0.0'),
                "error_message": result.error_message,
                # Conversational-specific fields
                "response": response_text,
                "chat_mode": chat_mode,
                "document_context": bool(document_id and document_id != "no_document"),
                "enhanced_with_external": enhanced_with_external,
                "conversation_metadata": {
                    "query_length": len(query),
                    "response_length": len(response_text),
                    "history_length": len(conversation_history),
                    "external_data_used": enhanced_with_external,
                    "document_analyzed": bool(document_id and document_id != "no_document")
                }
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
            "data_sources": [],
            "response": f"I encountered an error processing your request: {str(e)}",
            "chat_mode": event.get("chat_mode", "documents"),
            "document_context": False,
            "enhanced_with_external": False
        }


# Alternative handler for simplified chat interface
async def chat_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Simplified chat handler for basic conversational queries
    
    Args:
        event: Event payload with query and optional document_id
        context: AWS Lambda context (unused)
    
    Returns:
        Simplified response format
    """
    try:
        query = event.get("query")
        document_id = event.get("document_id")
        user_id = event.get("user_id", "api_user")
        
        if not query:
            return {
                "response": "Please provide a query",
                "success": False,
                "error": "Query is required"
            }
        
        # Use main handler
        full_result = await handler({
            "query": query,
            "document_id": document_id,
            "user_id": user_id,
            "chat_mode": "documents" if document_id else "general"
        }, context)
        
        # Return simplified format
        return {
            "response": full_result.get("response", ""),
            "success": full_result.get("status") == "COMPLETED",
            "confidence": full_result.get("confidence", 0.0),
            "sources": full_result.get("data_sources", []),
            "document_context": full_result.get("document_context", False),
            "error": full_result.get("error_message")
        }
        
    except Exception as e:
        return {
            "response": f"Error processing chat request: {str(e)}",
            "success": False,
            "confidence": 0.0,
            "sources": [],
            "document_context": False,
            "error": str(e)
        }