"""
Conversational AI Router - Enhanced Chat API
Handles any user query using AI agents and MCP services
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.agents.conversational_agent import ConversationalAgent
from app.agents.base_agent import AgentContext
from app.core.config import settings
from app.schemas.responses import ChatResponse as SchemaChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["conversational-ai"])

class ChatRequest(BaseModel):
    query: str
    contract_id: Optional[str] = None  # Document ID for context
    document_type: Optional[str] = None  # contract, invoice, policy, etc.
    context: Optional[Dict[str, Any]] = None
    use_external_data: Optional[bool] = True  # For legal/industry context
    max_response_length: Optional[int] = 1000

# Using ChatResponse from schemas for consistency

@router.post("/ask", response_model=SchemaChatResponse)
async def ask_question(request: ChatRequest):
    """
    Ask questions about your documents or get general assistance
    
    PRIMARY USE: Document Intelligence
    - "What are the risks in my contract?"
    - "Summarize the key terms"
    - "Is this document compliant?"
    - "Find liability clauses"
    
    SECONDARY USE: General Knowledge (when no document context)
    - Legal precedents and regulations
    - Industry standards and practices
    - Current market information
    - Technical explanations
    """
    try:
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        logger.info(f"🤖 Chat request: {request.query}")
        
        # Create agent context (document-focused)
        context = AgentContext(
            contract_id=request.contract_id or "no_document",  # Document context if provided
            user_id="api_user",  # Default user for API calls
            query=request.query.strip(),
            document_type=request.document_type or "general",
            metadata=request.context or {}
        )
        
        # Get conversational agent from factory (supports remote/local/agentcore)
        from app.agents.agent_factory import agent_factory
        agent = agent_factory.get_agent("conversational_agent")
        
        if not agent:
            raise HTTPException(status_code=503, detail="Conversational agent not available")
        
        # Execute analysis
        result = await agent.analyze(context)
        
        # Extract response from findings
        response_text = ""
        sources_set = set()
        enhanced_with_external_data = False
        
        for finding in result.findings:
            if finding.get("type") in ["enhanced_response", "ai_response"]:
                response_text = finding.get("description", "")
                if finding.get("type") == "enhanced_response":
                    enhanced_with_external_data = True
            
            # Collect sources
            if finding.get("source"):
                sources_set.add(finding["source"])
            elif finding.get("data"):
                sources_set.add(finding.get("type", "unknown"))
        
        # Add data sources from result
        if result.data_sources:
            for source in result.data_sources:
                sources_set.add(source)
        
        # Convert sources to expected dict format
        sources = [{"name": source, "type": "data_source"} for source in sources_set]
        
        # Fallback response if no main response found
        if not response_text and result.findings:
            response_text = result.findings[0].get("description", "I processed your query but couldn't generate a specific response.")
        elif not response_text:
            response_text = "I'm having trouble processing your query right now. Please try rephrasing or contact support."
        
        return SchemaChatResponse(
            response=response_text,
            confidence=result.confidence,
            sources=sources,
            processing_time=result.execution_time_ms / 1000.0  # Convert to seconds
        )
        
    except Exception as e:
        logger.error(f"Chat request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@router.post("/ask-with-context")
async def ask_with_document_context(
    query: str,
    contract_id: Optional[str] = None,
    document_type: Optional[str] = None
):
    """
    Ask a question with document context
    Useful when you want to ask about a specific document
    """
    try:
        logger.info(f"🤖 Chat with context: {query} (doc: {contract_id})")
        
        # Create agent context with document info
        context = AgentContext(
            contract_id=contract_id or "no_document",
            user_id="api_user",  # Default user for API calls
            query=query,
            document_type=document_type or "general"
        )
        
        # Use conversational agent
        agent = ConversationalAgent()
        result = await agent.analyze(context)
        
        # Extract response
        response_text = ""
        for finding in result.findings:
            if finding.get("type") in ["enhanced_response", "ai_response"]:
                response_text = finding.get("description", "")
                break
        
        if not response_text:
            response_text = "I couldn't generate a specific response for your query."
        
        return {
            "response": response_text,
            "confidence": result.confidence,
            "document_context": contract_id is not None,
            "findings": result.findings,
            "recommendations": result.recommendations
        }
        
    except Exception as e:
        logger.error(f"Contextual chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/capabilities")
async def get_chat_capabilities():
    """
    Get information about document-focused chat capabilities
    """
    return {
        "primary_capabilities": [
            "Document risk analysis and assessment",
            "Contract terms and clause identification",
            "Compliance checking and validation",
            "Document summarization and key insights",
            "Liability and obligation analysis",
            "Document comparison and differences",
            "Regulatory compliance verification",
            "Industry-specific document review"
        ],
        "secondary_capabilities": [
            "Legal precedents and case law",
            "Industry standards and best practices",
            "Regulatory updates and changes",
            "Company information for due diligence",
            "Market context for business documents",
            "Technical explanations of legal terms"
        ],
        "document_types_supported": [
            "Contracts and agreements",
            "Invoices and financial documents",
            "Policies and procedures",
            "Legal documents",
            "Compliance documents",
            "Business correspondence"
        ],
        "example_document_queries": [
            "What are the main risks in this contract?",
            "Summarize the key terms and obligations",
            "Is this document compliant with regulations?",
            "Find all liability clauses",
            "What are the termination conditions?",
            "Compare payment terms across documents",
            "Check for auto-renewal clauses",
            "Identify intellectual property terms"
        ],
        "example_general_queries": [
            "What are current data privacy regulations?",
            "Explain force majeure clauses",
            "What are industry standards for SLAs?",
            "Recent changes in contract law",
            "Best practices for liability limitations"
        ],
        "data_sources": [
            "Your uploaded documents (primary)",
            "Legal precedent databases",
            "Regulatory databases (SEC, Federal Register)",
            "Industry intelligence",
            "AI legal knowledge base",
            "Current legal and business news"
        ],
        "features": {
            "document_focused_analysis": True,
            "external_legal_context": True,
            "industry_specific_insights": True,
            "compliance_validation": True,
            "risk_assessment": True,
            "confidence_scoring": True,
            "multi_document_support": True
        },
        "usage_modes": {
            "document_mode": "Upload a document first, then ask questions about it",
            "general_mode": "Ask general legal/business questions without document context",
            "hybrid_mode": "Document analysis enhanced with external legal/industry context"
        }
    }

@router.get("/health")
async def chat_health_check():
    """
    Check the health of chat services
    """
    try:
        # Test basic agent initialization
        agent = ConversationalAgent()
        
        # Test MCP services
        from app.services.mcp_integration import mcp_service
        
        health_status = {
            "status": "healthy",
            "agent_available": True,
            "mcp_services": {},
            "timestamp": "2025-01-06T00:00:00Z"
        }
        
        # Quick MCP health check
        try:
            async with mcp_service:
                # Test web search
                test_result = await mcp_service.web_search("test", max_results=1)
                health_status["mcp_services"]["web_search"] = test_result.success
        except Exception as e:
            health_status["mcp_services"]["web_search"] = False
            logger.warning(f"MCP health check failed: {e}")
        
        return health_status
        
    except Exception as e:
        logger.error(f"Chat health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2025-01-06T00:00:00Z"
        }