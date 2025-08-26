"""
Simplified FastAPI routes for TiDB Hackathon demo
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from typing import List, Optional
import json
import PyPDF2
import docx
import io

from app.database import get_db, init_db, test_vector_search
from app.agents import agent
from app.models import AgentRun, Document
from app.core.config import settings

# Pydantic models
class AskRequest(BaseModel):
    question: str
    dataset_id: str = "default"

class DocumentUploadResponse(BaseModel):
    document_id: str
    message: str

class AnalysisResponse(BaseModel):
    run_id: str
    message: str

class RunResult(BaseModel):
    id: str
    query: str
    status: str
    final_answer: Optional[str]
    total_steps: int
    execution_time: Optional[float]
    retrieval_results: Optional[List]
    llm_analysis: Optional[dict]
    external_actions: Optional[dict]

# Create FastAPI app
app = FastAPI(
    title="DocuShield - TiDB Hackathon Demo",
    description="Multi-step Document Analysis Agent using TiDB Vector Search",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    """Initialize database and test vector search"""
    await init_db()
    vector_available = await test_vector_search()
    if vector_available:
        print("✅ TiDB Vector Search is available")
    else:
        print("⚠️ TiDB Vector Search not available, using fallback")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "DocuShield TiDB Demo is running",
        "tidb_connected": True,
        "openai_configured": bool(settings.openai_api_key)
    }

@app.post("/api/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    dataset_id: str = "default"
):
    """Upload and ingest document with vector embedding"""
    try:
        # Read file content
        content = await file.read()
        
        # Extract text based on file type
        if file.filename.endswith('.pdf'):
            text_content = extract_pdf_text(content)
            file_type = "pdf"
        elif file.filename.endswith('.docx'):
            text_content = extract_docx_text(content)
            file_type = "docx"
        elif file.filename.endswith(('.txt', '.md')):
            text_content = content.decode('utf-8')
            file_type = "text"
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        
        if not text_content.strip():
            raise HTTPException(status_code=400, detail="No text content found in file")
        
        # Ingest with vector embedding
        doc_id = await agent.ingest_document(
            title=file.filename,
            content=text_content,
            file_type=file_type,
            dataset_id=dataset_id
        )
        
        return DocumentUploadResponse(
            document_id=doc_id,
            message=f"Document '{file.filename}' uploaded and indexed successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/api/ask", response_model=AnalysisResponse)
async def ask_question(request: AskRequest):
    """Run multi-step analysis workflow"""
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        # Run multi-step agent workflow
        run_id = await agent.run_multi_step_analysis(
            query=request.question,
            dataset_id=request.dataset_id
        )
        
        return AnalysisResponse(
            run_id=run_id,
            message="Multi-step analysis completed successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/api/runs/{run_id}", response_model=RunResult)
async def get_run_result(run_id: str, db: AsyncSession = Depends(get_db)):
    """Get analysis run results"""
    try:
        result = await db.execute(
            text("SELECT * FROM agent_runs WHERE id = :run_id"),
            {"run_id": run_id}
        )
        run = result.fetchone()
        
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        return RunResult(
            id=run.id,
            query=run.query,
            status=run.status,
            final_answer=run.final_answer,
            total_steps=run.total_steps or 0,
            execution_time=run.execution_time,
            retrieval_results=json.loads(run.retrieval_results) if run.retrieval_results else [],
            llm_analysis=json.loads(run.llm_analysis) if run.llm_analysis else {},
            external_actions=json.loads(run.external_actions) if run.external_actions else {}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get run: {str(e)}")

@app.get("/api/datasets/{dataset_id}/documents")
async def list_documents(dataset_id: str, db: AsyncSession = Depends(get_db)):
    """List documents in dataset"""
    try:
        result = await db.execute(
            text("SELECT id, title, file_type, created_at FROM documents WHERE dataset_id = :dataset_id ORDER BY created_at DESC"),
            {"dataset_id": dataset_id}
        )
        
        documents = []
        for row in result:
            documents.append({
                "id": row.id,
                "title": row.title,
                "file_type": row.file_type,
                "created_at": row.created_at.isoformat()
            })
        
        return {"documents": documents, "total": len(documents)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@app.get("/api/runs")
async def list_runs(limit: int = 10, db: AsyncSession = Depends(get_db)):
    """List recent analysis runs"""
    try:
        result = await db.execute(
            text("SELECT id, query, status, total_steps, execution_time, created_at FROM agent_runs ORDER BY created_at DESC LIMIT :limit"),
            {"limit": limit}
        )
        
        runs = []
        for row in result:
            runs.append({
                "id": row.id,
                "query": row.query,
                "status": row.status,
                "total_steps": row.total_steps or 0,
                "execution_time": row.execution_time,
                "created_at": row.created_at.isoformat()
            })
        
        return {"runs": runs, "total": len(runs)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list runs: {str(e)}")

# Helper functions
def extract_pdf_text(content: bytes) -> str:
    """Extract text from PDF bytes"""
    try:
        pdf_file = io.BytesIO(content)
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"Failed to extract PDF text: {e}")

def extract_docx_text(content: bytes) -> str:
    """Extract text from DOCX bytes"""
    try:
        docx_file = io.BytesIO(content)
        doc = docx.Document(docx_file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"Failed to extract DOCX text: {e}")
