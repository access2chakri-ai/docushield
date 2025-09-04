"""
Document management router for DocuShield API
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import List, Optional
import asyncio
import hashlib
import logging
import io
from datetime import datetime, timedelta

# Import PDF and DOCX processing libraries
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import docx
except ImportError:
    docx = None

from app.database import get_operational_db
from app.models import User, BronzeContract, BronzeContractTextRaw, ProcessingRun
from app.core.dependencies import get_current_active_user
from app.schemas.requests import ProcessContractRequest
from app.schemas.responses import ContractAnalysisResponse
from app.services.document_processor import document_processor
from app.services.document_validator import document_validator, DocumentCategory
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Upload document and trigger processing pipeline with comprehensive validation"""
    try:
        # 1. Validate file basics
        if not file.filename:
            raise HTTPException(
                status_code=400, 
                detail="No filename provided"
            )
        
        # 2. Check file extension and type
        allowed_extensions = {'.pdf', '.docx', '.doc', '.txt', '.md'}
        file_extension = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        
        if f'.{file_extension}' not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_extension}. DocuShield supports: PDF, DOCX, DOC, TXT, MD files for document analysis."
            )
        
        # 3. Validate MIME type
        allowed_mime_types = {
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/msword',
            'text/plain',
            'text/markdown',
            'application/octet-stream'  # For some valid files
        }
        
        if file.content_type and file.content_type not in allowed_mime_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported content type: {file.content_type}. Please upload document files (PDF, Word, Text) for analysis."
            )
        
        # 4. Read file content with size check during read
        content = bytearray()
        max_size = 50 * 1024 * 1024  # Reduced to 50MB for better performance
        chunk_size = 1024 * 1024  # 1MB chunks
        
        max_iterations = settings.max_file_read_iterations  # Safety limit to prevent infinite loops
        iteration_count = 0
        
        while iteration_count < max_iterations:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            
            if len(content) + len(chunk) > max_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size is 50MB for optimal processing performance. Your file appears to be larger."
                )
            
            content.extend(chunk)
            iteration_count += 1
            
        if iteration_count >= max_iterations:
            raise HTTPException(
                status_code=413,
                detail="File reading exceeded maximum iterations. File may be corrupted."
            )
        
        content = bytes(content)
        
        # 5. Validate minimum file size (avoid empty files)
        if len(content) < 100:  # Less than 100 bytes
            raise HTTPException(
                status_code=400,
                detail="File appears to be empty or too small. Please upload a document with actual content."
            )
        
        # 6. Basic content validation for document context
        if file_extension == 'txt' or file_extension == 'md':
            try:
                text_content = content.decode('utf-8', errors='ignore')
                if len(text_content.strip()) < 50:
                    raise HTTPException(
                        status_code=400,
                        detail="Document content is too short. Please upload documents with substantial text content for analysis."
                    )
                
                # Check if it looks like a document (has some structure)
                if not any(keyword in text_content.lower() for keyword in [
                    'contract', 'agreement', 'terms', 'conditions', 'policy', 'document',
                    'shall', 'party', 'service', 'payment', 'liability', 'clause'
                ]):
                    logger.warning(f"File {file.filename} may not be a business document")
                    # Don't block, but log for monitoring
                    
            except Exception as e:
                logger.warning(f"Could not validate text content: {e}")
        
        # 7. Check user's document quota (prevent abuse)
        user_doc_count = await db.execute(
            text("SELECT COUNT(*) FROM bronze_contracts WHERE owner_user_id = :user_id"),
            {"user_id": current_user.user_id}
        )
        doc_count = user_doc_count.scalar()
        
        if doc_count >= 100:  # Limit per user
            raise HTTPException(
                status_code=429,
                detail="Document limit reached. You can upload up to 100 documents. Please delete some documents before uploading new ones."
            )
        
        file_hash = hashlib.sha256(content).hexdigest()
        
        # Check for duplicates
        result = await db.execute(
            select(BronzeContract).where(
                (BronzeContract.file_hash == file_hash) & 
                (BronzeContract.owner_user_id == current_user.user_id)
            )
        )
        existing_contract = result.scalar_one_or_none()
        
        if existing_contract:
            return {
                "message": "File already exists",
                "contract_id": existing_contract.contract_id,
                "filename": existing_contract.filename,
                "status": "duplicate"
            }
        
        # 8. Extract text content for business validation
        text_content = ""
        try:
            if file.content_type == "application/pdf":
                text_content = await _extract_pdf_text(content)
            elif "wordprocessingml" in file.content_type:
                text_content = await _extract_docx_text(content)
            elif "text/" in file.content_type:
                text_content = content.decode('utf-8', errors='ignore')
            else:
                text_content = content.decode('utf-8', errors='ignore')
        except Exception as e:
            logger.warning(f"Text extraction failed for validation: {e}")
            text_content = ""
        
        # 9. Validate document type and business relevance
        is_valid, doc_category, validation_details = await document_validator.validate_document(
            filename=file.filename,
            text_content=text_content,
            mime_type=file.content_type or "application/octet-stream"
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Document not suitable for processing",
                    "reason": validation_details["reason"],
                    "supported_types": [
                        "SaaS contracts and agreements",
                        "Vendor/supplier agreements", 
                        "Software licenses and subscriptions",
                        "Invoices and billing documents",
                        "Procurement documents (SaaS/software related)",
                        "Service agreements and SLAs"
                    ],
                    "confidence": validation_details["confidence"],
                    "filename_score": validation_details["filename_score"],
                    "content_score": validation_details["content_score"]
                }
            )
        
        logger.info(f"Document validated as {doc_category.value} with confidence {validation_details['confidence']:.2f}")
        
        # Create contract record - store all files in TiDB LONGBLOB
        contract = BronzeContract(
            filename=file.filename,
            mime_type=file.content_type or "application/octet-stream",
            file_size=len(content),
            file_hash=file_hash,
            raw_bytes=content,  # Store full file content in TiDB
            owner_user_id=current_user.user_id,
            source="upload",
            status="uploaded"
        )
        
        logger.info(f"Storing file in TiDB: {file.filename} ({len(content)} bytes)")
        db.add(contract)
        await db.commit()
        await db.refresh(contract)
        
        # Trigger background processing
        background_tasks.add_task(
            process_contract_background, 
            contract.contract_id, 
            current_user.user_id
        )
        
        return {
            "message": "File uploaded successfully and processing started",
            "contract_id": contract.contract_id,
            "filename": contract.filename,
            "file_size": contract.file_size,
            "status": "uploaded"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("")
async def list_documents(
    limit: int = 50, 
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Get list of uploaded documents - JWT authenticated"""
    try:
        # Exclude raw_bytes from listing to prevent memory issues with large files
        result = await db.execute(
            select(
                BronzeContract.contract_id,
                BronzeContract.filename,
                BronzeContract.mime_type,
                BronzeContract.file_size,
                BronzeContract.status,
                BronzeContract.created_at,
                BronzeContract.source,
                BronzeContract.retry_count,
                BronzeContract.last_retry_at,
                BronzeContract.max_retries
            )
            .where(BronzeContract.owner_user_id == current_user.user_id)
            .order_by(BronzeContract.created_at.desc())
            .limit(limit)
        )
        contracts = result.all()
        
        documents = []
        for contract in contracts:
            documents.append({
                "contract_id": contract.contract_id,
                "filename": contract.filename,
                "mime_type": contract.mime_type,
                "file_size": contract.file_size,
                "status": contract.status,
                "created_at": contract.created_at.isoformat(),
                "source": contract.source,
                "retry_count": contract.retry_count,
                "last_retry_at": contract.last_retry_at.isoformat() if contract.last_retry_at else None,
                "max_retries": contract.max_retries
            })
        
        return {
            "documents": documents,
            "total": len(documents),
            "user_id": current_user.user_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve documents: {str(e)}")

@router.get("/{contract_id}/status")
async def get_contract_status(
    contract_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Get real-time processing status for a contract"""
    try:
        # Get contract
        result = await db.execute(
            select(BronzeContract).where(
                BronzeContract.contract_id == contract_id,
                BronzeContract.owner_user_id == current_user.user_id
            )
        )
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        # Get latest processing run
        result = await db.execute(
            select(ProcessingRun).where(
                ProcessingRun.contract_id == contract_id
            ).order_by(ProcessingRun.started_at.desc()).limit(1)
        )
        latest_run = result.scalar_one_or_none()
        
        return {
            "contract_id": contract.contract_id,
            "filename": contract.filename,
            "status": contract.status,
            "error_message": latest_run.error_message if latest_run and latest_run.error_message else None,
            "last_updated": contract.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get contract status: {str(e)}")

@router.post("/retry-processing")
async def retry_processing(
    request: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Retry processing for a failed document without re-uploading"""
    try:
        contract_id = request.get("contract_id")
        if not contract_id:
            raise HTTPException(status_code=400, detail="contract_id is required")
        
        # Get contract and verify ownership
        result = await db.execute(
            select(BronzeContract).where(
                BronzeContract.contract_id == contract_id,
                BronzeContract.owner_user_id == current_user.user_id
            )
        )
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        # Check current status
        if contract.status == "completed":
            raise HTTPException(
                status_code=400, 
                detail="Document already processed successfully. No retry needed."
            )
        
        if contract.status == "processing":
            raise HTTPException(
                status_code=400, 
                detail="Document is currently being processed. Please wait."
            )
        
        # Check retry limits
        if contract.retry_count >= (contract.max_retries or settings.max_retry_attempts):
            raise HTTPException(
                status_code=429,
                detail=f"Maximum retry limit reached ({contract.max_retries or settings.max_retry_attempts} attempts). "
                       f"Please contact support if you believe this document should be processable."
            )
        
        # Check cooldown period
        if contract.last_retry_at:
            cooldown_period = timedelta(minutes=settings.retry_cooldown_minutes)
            time_since_last_retry = datetime.utcnow() - contract.last_retry_at
            
            if time_since_last_retry < cooldown_period:
                remaining_time = cooldown_period - time_since_last_retry
                remaining_minutes = int(remaining_time.total_seconds() / 60)
                raise HTTPException(
                    status_code=429,
                    detail=f"Please wait {remaining_minutes} more minutes before retrying. "
                           f"Cooldown period helps prevent system overload."
                )
        
        # Check for persistent validation failures
        if contract.status == "validation_failed" and contract.retry_count >= 1:
            raise HTTPException(
                status_code=422,
                detail="Document validation keeps failing. This document type may not be supported. "
                       "Please ensure you're uploading a business document (SaaS contract, invoice, etc.)"
            )
        
        # Update retry tracking
        contract.retry_count = (contract.retry_count or 0) + 1
        contract.last_retry_at = datetime.utcnow()
        contract.status = "processing"
        await db.commit()
        
        # Trigger background processing again
        background_tasks.add_task(
            process_contract_background, 
            contract.contract_id, 
            current_user.user_id
        )
        
        logger.info(f"🔄 Retry processing started for contract {contract_id} by user {current_user.user_id}")
        
        return {
            "message": "Processing retry started successfully",
            "contract_id": contract.contract_id,
            "filename": contract.filename,
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Retry processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Retry processing failed: {str(e)}")

@router.get("/{contract_id}/analysis")
async def get_contract_analysis(
    contract_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Get comprehensive contract analysis results"""
    try:
        # Get contract with all related data
        result = await db.execute(
            select(BronzeContract).where(
                (BronzeContract.contract_id == contract_id) & 
                (BronzeContract.owner_user_id == current_user.user_id)
            )
        )
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        # Get processing runs
        runs_result = await db.execute(
            select(ProcessingRun)
            .where(ProcessingRun.contract_id == contract_id)
            .order_by(ProcessingRun.started_at.desc())
        )
        runs = runs_result.scalars().all()
        
        # Get analysis results from Gold layer
        analysis_data = {
            "contract_id": contract.contract_id,
            "filename": contract.filename,
            "status": contract.status,
            "file_size": contract.file_size,
            "mime_type": contract.mime_type,
            "created_at": contract.created_at.isoformat(),
            "processing_runs": [
                {
                    "run_id": run.run_id,
                    "status": run.status,
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                    "pipeline_version": run.pipeline_version
                }
                for run in runs
            ],
            "scores": None,
            "findings": [],
            "suggestions": [],
            "summaries": []
        }
        
        return analysis_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis retrieval failed: {str(e)}")

@router.post("/process")
async def process_contract(
    request: ProcessContractRequest,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Trigger contract processing pipeline"""
    try:
        # Verify contract belongs to user
        result = await db.execute(
            select(BronzeContract).where(
                (BronzeContract.contract_id == request.contract_id) & 
                (BronzeContract.owner_user_id == current_user.user_id)
            )
        )
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        # Trigger processing
        processing_result = await document_processor.process_contract(
            contract_id=request.contract_id,
            trigger=request.trigger,
            resume_from_step=request.resume_from_step
        )
        
        return {
            "message": "Processing started successfully",
            "processing_run_id": processing_result.get("run_id"),
            "contract_id": request.contract_id,
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@router.delete("/{contract_id}")
async def delete_document(
    contract_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Delete a document and all its associated data"""
    try:
        # Get the contract
        result = await db.execute(
            select(BronzeContract).where(
                BronzeContract.contract_id == contract_id,
                BronzeContract.owner_user_id == current_user.user_id
            )
        )
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise HTTPException(
                status_code=404,
                detail="Document not found or you don't have permission to delete it"
            )
        
        # Delete all associated data in correct order (respecting foreign keys)
        # 1. Delete alerts
        await db.execute(
            text("DELETE FROM alerts WHERE contract_id = :contract_id"),
            {"contract_id": contract_id}
        )
        
        # 2. Delete LLM calls
        await db.execute(
            text("DELETE FROM llm_calls WHERE contract_id = :contract_id"),
            {"contract_id": contract_id}
        )
        
        # 3. Delete gold layer data
        await db.execute(
            text("DELETE FROM gold_summaries WHERE contract_id = :contract_id"),
            {"contract_id": contract_id}
        )
        
        await db.execute(
            text("DELETE FROM gold_suggestions WHERE contract_id = :contract_id"),
            {"contract_id": contract_id}
        )
        
        await db.execute(
            text("DELETE FROM gold_findings WHERE contract_id = :contract_id"),
            {"contract_id": contract_id}
        )
        
        await db.execute(
            text("DELETE FROM gold_contract_scores WHERE contract_id = :contract_id"),
            {"contract_id": contract_id}
        )
        
        # 4. Delete silver layer data
        await db.execute(
            text("DELETE FROM tokens WHERE contract_id = :contract_id"),
            {"contract_id": contract_id}
        )
        
        await db.execute(
            text("DELETE FROM silver_clause_spans WHERE contract_id = :contract_id"),
            {"contract_id": contract_id}
        )
        
        await db.execute(
            text("DELETE FROM silver_chunks WHERE contract_id = :contract_id"),
            {"contract_id": contract_id}
        )
        
        # 5. Delete processing data
        await db.execute(
            text("DELETE FROM processing_steps WHERE run_id IN (SELECT run_id FROM processing_runs WHERE contract_id = :contract_id)"),
            {"contract_id": contract_id}
        )
        
        await db.execute(
            text("DELETE FROM processing_runs WHERE contract_id = :contract_id"),
            {"contract_id": contract_id}
        )
        
        # 6. Delete bronze layer data
        await db.execute(
            text("DELETE FROM bronze_contract_text_raw WHERE contract_id = :contract_id"),
            {"contract_id": contract_id}
        )
        
        # 7. Finally delete the main contract record
        await db.delete(contract)
        await db.commit()
        
        logger.info(f"Successfully deleted document {contract_id} ({contract.filename}) for user {current_user.user_id}")
        
        return {
            "message": "Document deleted successfully",
            "contract_id": contract_id,
            "filename": contract.filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document {contract_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )

# Helper functions for text extraction
async def _extract_pdf_text(content: bytes) -> str:
    """Extract text from PDF bytes"""
    if PyPDF2 is None:
        raise ImportError("PyPDF2 is required for PDF text extraction")
    
    try:
        
        pdf_file = io.BytesIO(content)
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        logger.warning(f"PDF text extraction failed: {e}")
        return ""

async def _extract_docx_text(content: bytes) -> str:
    """Extract text from DOCX bytes"""
    if docx is None:
        raise ImportError("python-docx is required for DOCX text extraction")
    
    try:
        
        docx_file = io.BytesIO(content)
        doc = docx.Document(docx_file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        logger.warning(f"DOCX text extraction failed: {e}")
        return ""

# Background task function
async def process_contract_background(contract_id: str, user_id: str):
    """Background task to process uploaded contract with timeout protection"""
    try:
        logger.info(f"🔄 Starting background processing for contract {contract_id}")
        
        # Set processing timeout (10 minutes max)
        timeout_seconds = 600  # 10 minutes
        
        # Update contract status to processing
        async for db in get_operational_db():
            try:
                await db.execute(
                    text("UPDATE bronze_contracts SET status = 'processing' WHERE contract_id = :contract_id"),
                    {"contract_id": contract_id}
                )
                await db.commit()
            finally:
                break  # Prevent infinite loop
        
        try:
            # Process the contract with timeout
            result = await asyncio.wait_for(
                document_processor.process_contract(
                    contract_id=contract_id,
                    user_id=user_id,
                    trigger="upload"
                ),
                timeout=timeout_seconds
            )
            
            # Update status to completed
            async for db in get_operational_db():
                try:
                    await db.execute(
                        text("UPDATE bronze_contracts SET status = 'completed' WHERE contract_id = :contract_id"),
                        {"contract_id": contract_id}
                    )
                    await db.commit()
                finally:
                    break  # Prevent infinite loop
            
            logger.info(f"✅ Background processing completed for contract {contract_id}")
            
        except asyncio.TimeoutError:
            logger.error(f"⏰ Processing timeout for contract {contract_id} after {timeout_seconds} seconds")
            
            # Update status to timeout
            async for db in get_operational_db():
                try:
                    await db.execute(
                        text("UPDATE bronze_contracts SET status = 'timeout' WHERE contract_id = :contract_id"),
                        {"contract_id": contract_id}
                    )
                    await db.commit()
                finally:
                    break  # Prevent infinite loop
            
            raise HTTPException(
                status_code=408,
                detail=f"Document processing timed out after {timeout_seconds//60} minutes. The document may be too complex or large."
            )
        
    except Exception as e:
        logger.error(f"❌ Background processing failed for contract {contract_id}: {e}")
        
        # Update status to failed
        try:
            async for db in get_operational_db():
                try:
                    await db.execute(
                        text("UPDATE bronze_contracts SET status = 'failed' WHERE contract_id = :contract_id"),
                        {"contract_id": contract_id}
                    )
                    await db.commit()
                finally:
                    break  # Prevent infinite loop
        except Exception as db_error:
            logger.error(f"Failed to update contract status: {db_error}")
