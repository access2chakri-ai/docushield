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
    """Ask a question about documents using AI agents"""
    try:
        start_time = time.time()
        
        # Import here to avoid circular imports
        from app.agents import agent_orchestrator
        
        # Process the question
        result = await agent_orchestrator.process_query(
            query=request.question,
            user_id=current_user.user_id,
            document_id=request.document_id,
            conversation_history=request.conversation_history or []
        )
        
        processing_time = time.time() - start_time
        
        return ChatResponse(
            response=result.get("response", "I couldn't process your question."),
            sources=result.get("sources", []),
            confidence=result.get("confidence", 0.0),
            processing_time=processing_time
        )
        
    except Exception as e:
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
            "current_step": run_data["current_step"],
            "steps": run_data["steps"],
            "results": run_data["results"],
            "execution_time": time.time() - run_data["started_at"] if run_data["status"] == "running" else None
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
        
        # Simulate multi-step processing
        steps = [
            {"name": "document_retrieval", "description": "Finding relevant documents"},
            {"name": "content_analysis", "description": "Analyzing document content"},
            {"name": "llm_processing", "description": "Processing with AI models"},
            {"name": "result_compilation", "description": "Compiling final results"}
        ]
        
        run_data["steps"] = steps
        
        for i, step in enumerate(steps):
            run_data["current_step"] = i
            run_data["steps"][i]["status"] = "running"
            
            # Simulate processing time
            await asyncio.sleep(2)
            
            run_data["steps"][i]["status"] = "completed"
            run_data["steps"][i]["completed_at"] = time.time()
        
        # Process with agent orchestrator
        result = await agent_orchestrator.process_query(
            query=run_data["query"],
            user_id=run_data["user_id"]
        )
        
        run_data["status"] = "completed"
        run_data["results"] = result
        run_data["completed_at"] = time.time()
        
    except Exception as e:
        if run_id in chat_runs:
            chat_runs[run_id]["status"] = "failed"
            chat_runs[run_id]["error"] = str(e)
