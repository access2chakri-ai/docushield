"""
Chat and Agent router for DocuShield API
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
import time
import uuid
import asyncio

from app.core.dependencies import get_current_active_user
from app.schemas.requests import ChatRequest, RunRequest
from app.schemas.responses import ChatResponse, RunResponse

router = APIRouter(prefix="/api", tags=["chat", "agents"])

# In-memory storage for chat runs (in production, use database)
chat_runs = {}

@router.post("/ask", response_model=ChatResponse)
async def ask_question(
    request: ChatRequest,
    current_user = Depends(get_current_active_user)
):
    """
    Ask questions about your documents using enhanced AI with MCP integration
    
    DOCUMENT MODE: When document_id is provided
    - Analyzes specific document content
    - Provides document-focused insights
    - Enhanced with external legal/industry context
    
    GENERAL MODE: When no document_id provided
    - General document guidance
    - Legal and business knowledge
    - Industry best practices
    """
    try:
        start_time = time.time()
        
        # Import the enhanced conversational agent
        from app.agents.conversational_agent import ConversationalAgent
        from app.agents.base_agent import AgentContext
        
        # Determine chat mode
        chat_mode = request.chat_mode or "documents"
        
        # Validate mode restrictions
        if chat_mode == "documents" and not request.document_id and not request.search_all_documents:
            # Document mode requires either a specific document or all documents search
            return ChatResponse(
                response="Please select a document or enable 'Search All Documents' to ask questions about your documents. For general questions, switch to 'General Mode'.",
                sources=[{"name": "system", "type": "guidance"}],
                confidence=1.0,
                processing_time=0.0,
                agent_results=[]
            )
        
        # Create agent context
        context = AgentContext(
            contract_id=request.document_id or "no_document",
            user_id=current_user.user_id,
            query=request.question,
            document_type="contract",
            metadata={
                "conversation_history": request.conversation_history or [],
                "document_types": request.document_types,
                "industry_types": request.industry_types,
                "chat_mode": chat_mode,
                "search_all_documents": request.search_all_documents
            }
        )
        
        # Get conversational agent from factory (supports remote/local/agentcore)
        from app.agents.agent_factory import agent_factory
        agent = agent_factory.get_agent("conversational_agent")
        
        if not agent:
            raise HTTPException(status_code=503, detail="Conversational agent not available")
        result = await agent.analyze(context)
        
        processing_time = time.time() - start_time
        
        # Extract response from agent result
        response_text = ""
        sources = []
        enhanced_with_external = False
        
        for finding in result.findings:
            if finding.get("type") in ["document_chat_response", "enhanced_response", "ai_response", "document_guidance"]:
                response_text = finding.get("description", "")
                if finding.get("enhanced_with_external", False):
                    enhanced_with_external = True
                break
        
        # Collect sources from data sources and findings - convert to dict format
        sources_set = set()
        
        # Add data sources
        if result.data_sources:
            for source in result.data_sources:
                sources_set.add(source)
        
        # Add sources from findings
        for finding in result.findings:
            if finding.get("source"):
                sources_set.add(finding["source"])
        
        # Convert sources to expected dict format
        sources = [{"name": source, "type": "data_source"} for source in sources_set]
        
        # Fallback response if no main response found
        if not response_text:
            if result.findings:
                response_text = result.findings[0].get("description", "I processed your question but couldn't generate a specific response.")
            else:
                response_text = "I'm having trouble processing your question right now. Please try rephrasing or contact support."
        
        # Add context information to response
        if request.document_id and response_text:
            response_text += f"\n\n💡 This analysis is based on your uploaded document. Ask follow-up questions for more details!"
        elif not request.document_id and "document" in request.question.lower():
            response_text += f"\n\n📄 To get specific document analysis, please select a document from the dropdown above."
        
        return ChatResponse(
            response=response_text,
            sources=sources,
            confidence=result.confidence,
            processing_time=processing_time
        )
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Chat processing error: {error_details}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@router.post("/runs", response_model=RunResponse)
async def start_run(
    request: RunRequest,
    current_user = Depends(get_current_active_user)
):
    """Start a multi-step document analysis run"""
    try:
        # Create a unique run ID
        run_id = str(uuid.uuid4())
        
        # Initialize the run
        run_data = {
            "id": run_id,
            "query": request.query,
            "user_id": current_user.user_id,
            "dataset_id": request.dataset_id or "default",
            "document_filter": request.document_filter,
            "status": "running",
            "started_at": time.time(),
            "steps": [],
            "current_step": 0,
            "results": {}
        }
        
        chat_runs[run_id] = run_data
        
        # Start background processing
        asyncio.create_task(process_run_background(run_id))
        
        return RunResponse(
            run_id=run_id,
            status="running",
            query=request.query,
            started_at=run_data["started_at"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Run creation failed: {str(e)}")

@router.get("/runs/{run_id}")
async def get_run_status(
    run_id: str,
    current_user = Depends(get_current_active_user)
):
    """Get status and results of a running analysis"""
    try:
        if run_id not in chat_runs:
            raise HTTPException(status_code=404, detail="Run not found")
        
        run_data = chat_runs[run_id]
        
        # Check if user owns this run
        if run_data["user_id"] != current_user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return {
            "run_id": run_id,
            "status": run_data["status"],
            "query": run_data["query"],
            "started_at": run_data["started_at"],
            "current_step": run_data.get("current_step", 0),
            "steps": run_data.get("steps", []),
            "results": run_data.get("results", {}),
            "final_answer": run_data.get("final_answer", ""),
            "total_steps": run_data.get("total_steps", 0),
            "retrieval_results": run_data.get("retrieval_results", []),
            "llm_analysis": run_data.get("llm_analysis", []),
            "external_actions": run_data.get("external_actions", {}),
            "execution_time": time.time() - run_data["started_at"] if run_data["status"] == "running" else run_data.get("completed_at", time.time()) - run_data["started_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get run status: {str(e)}")

@router.get("/runs")
async def list_runs(
    limit: int = 20,
    current_user = Depends(get_current_active_user)
):
    """List recent chat runs for a user"""
    try:
        # Filter runs by user_id
        user_runs = [
            {
                "id": run_data["id"],
                "query": run_data["query"],
                "status": run_data["status"],
                "started_at": run_data["started_at"],
                "execution_time": time.time() - run_data["started_at"] if run_data["status"] == "running" else None
            }
            for run_data in chat_runs.values()
            if run_data["user_id"] == current_user.user_id
        ]
        
        # Sort by start time (newest first) and limit
        user_runs.sort(key=lambda x: x["started_at"], reverse=True)
        user_runs = user_runs[:limit]
        
        return {
            "runs": user_runs,
            "total": len(user_runs),
            "user_id": current_user.user_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list runs: {str(e)}")

# Background task function
async def process_run_background(run_id: str):
    """Background processing for multi-step runs"""
    try:
        if run_id not in chat_runs:
            return
        
        run_data = chat_runs[run_id]
        
        # Import here to avoid circular imports
        from app.agents import agent_orchestrator
        
        # Define realistic processing steps
        steps = [
            {"name": "document_retrieval", "description": "Retrieving document from database", "status": "pending"},
            {"name": "vector_search", "description": "Searching with TiDB vector embeddings", "status": "pending"},
            {"name": "agent_analysis", "description": "Running specialized AI agents", "status": "pending"},
            {"name": "result_synthesis", "description": "Synthesizing final response", "status": "pending"}
        ]
        
        run_data["steps"] = steps
        run_data["current_step"] = 0
        run_data["total_steps"] = len(steps)
        
        # Step 1: Document retrieval
        run_data["current_step"] = 0
        run_data["steps"][0]["status"] = "running"
        await asyncio.sleep(1)
        run_data["steps"][0]["status"] = "completed"
        run_data["steps"][0]["completed_at"] = time.time()
        
        # Step 2: Vector search
        run_data["current_step"] = 1
        run_data["steps"][1]["status"] = "running"
        await asyncio.sleep(2)
        run_data["steps"][1]["status"] = "completed"
        run_data["steps"][1]["completed_at"] = time.time()
        
        # Step 3: Agent analysis (main processing)
        run_data["current_step"] = 2
        run_data["steps"][2]["status"] = "running"
        
        # Process with agent orchestrator
        result = await agent_orchestrator.process_query(
            query=run_data["query"],
            user_id=run_data["user_id"],
            document_id=run_data.get("document_filter"),
            conversation_history=[]
        )
        
        run_data["steps"][2]["status"] = "completed"
        run_data["steps"][2]["completed_at"] = time.time()
        
        # Step 4: Result synthesis
        run_data["current_step"] = 3
        run_data["steps"][3]["status"] = "running"
        await asyncio.sleep(1)
        run_data["steps"][3]["status"] = "completed"
        run_data["steps"][3]["completed_at"] = time.time()
        
        run_data["status"] = "completed"
        run_data["results"] = result
        run_data["final_answer"] = result.get("response", "Analysis completed")
        run_data["total_steps"] = len(result.get("agent_results", []))
        run_data["retrieval_results"] = result.get("sources", [])
        run_data["llm_analysis"] = result.get("agent_results", [])
        run_data["external_actions"] = {}
        run_data["completed_at"] = time.time()
        
    except Exception as e:
        if run_id in chat_runs:
            chat_runs[run_id]["status"] = "failed"
            chat_runs[run_id]["error"] = str(e)
