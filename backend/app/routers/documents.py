"""
Document management router for DocuShield API
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
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
from app.models import User, BronzeContract, BronzeContractTextRaw, ProcessingRun, GoldContractScore, GoldFinding, GoldSuggestion, Alert
from app.core.dependencies import get_current_active_user
from app.schemas.requests import ProcessContractRequest
from app.schemas.responses import ContractAnalysisResponse
from app.services.document_processor import document_processor
from app.services.document_validator import document_classifier, DocumentCategory
from app.core.config import settings
from app.core.security import security_validator, rate_limiter
from app.routers.document_highlights import document_highlighter
from app.agents.api_interface import agent_api

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(None),
    industry_type: Optional[str] = Form(None),
    user_description: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Upload document and trigger processing pipeline with comprehensive validation"""
    try:
        # 0. Rate limiting check
        if not rate_limiter.is_allowed(f"upload_{current_user.user_id}", max_requests=50, window_seconds=3600):
            raise HTTPException(
                status_code=429,
                detail="Upload rate limit exceeded. Please try again later."
            )
        
        # 1. Security validation
        security_validator.validate_upload_file(file)
        
        # 2. Validate file basics
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
        
        # 4.5. Security content validation
        if not security_validator.validate_file_content(content, file.filename):
            raise HTTPException(
                status_code=400,
                detail="File content validation failed. The file may contain malicious content or be corrupted."
            )
        
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
        
        # 9. Classify document type (no restrictions - accept all documents)
        from app.services.document_validator import document_classifier
        
        is_valid, doc_category, classification_details = await document_classifier.classify_document(
            filename=file.filename,
            text_content=text_content,
            mime_type=file.content_type or "application/octet-stream",
            user_document_type=document_type,
            user_industry_type=industry_type
        )
        
        logger.info(f"Document classified as {doc_category.value} with confidence {classification_details['confidence']:.2f}")
        
        # Create contract record - store all files in TiDB LONGBLOB
        contract = BronzeContract(
            filename=file.filename,
            mime_type=file.content_type or "application/octet-stream",
            file_size=len(content),
            file_hash=file_hash,
            raw_bytes=content,  # Store full file content in TiDB
            owner_user_id=current_user.user_id,
            source="upload",
            status="uploaded",
            # New classification fields
            document_type=document_type,
            industry_type=industry_type,
            document_category=doc_category.value,
            user_description=user_description
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
            "status": "uploaded",
            "document_type": contract.document_type,
            "industry_type": contract.industry_type,
            "document_category": contract.document_category,
            "classification_confidence": classification_details["confidence"]
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

@router.get("/{contract_id}/content")
async def get_contract_content(
    contract_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Get contract content with text for document viewer"""
    try:
        # Get contract with text content
        result = await db.execute(
            select(BronzeContract).options(
                selectinload(BronzeContract.text_raw)
            ).where(
                (BronzeContract.contract_id == contract_id) & 
                (BronzeContract.owner_user_id == current_user.user_id)
            )
        )
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        return {
            "contract_id": contract.contract_id,
            "filename": contract.filename,
            "status": contract.status,
            "created_at": contract.created_at.isoformat() if contract.created_at else None,
            "raw_text": contract.text_raw.raw_text if contract.text_raw else None,
            "file_size": contract.file_size,
            "mime_type": contract.mime_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get contract content: {str(e)}")

@router.get("/{contract_id}/original")
async def get_original_document(
    contract_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Serve original document file directly"""
    try:
        # Get contract with raw bytes
        result = await db.execute(
            select(BronzeContract).where(
                (BronzeContract.contract_id == contract_id) & 
                (BronzeContract.owner_user_id == current_user.user_id)
            )
        )
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if not contract.raw_bytes:
            raise HTTPException(status_code=404, detail="Original document file not available")
        
        from fastapi.responses import Response
        
        # Determine content type
        content_type = contract.mime_type or "application/octet-stream"
        
        # Set appropriate headers for iframe viewing
        headers = {
            "Content-Disposition": f'inline; filename="{contract.filename}"',
            "Content-Length": str(len(contract.raw_bytes)),
            "X-Frame-Options": "SAMEORIGIN",
            "Cache-Control": "private, no-cache"
        }
        
        return Response(
            content=contract.raw_bytes,
            media_type=content_type,
            headers=headers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to serve original document: {str(e)}")


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
            select(BronzeContract).options(
                selectinload(BronzeContract.clause_spans),
                selectinload(BronzeContract.text_raw)
            ).where(
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
        
        # Get analysis results from Gold layer - query actual TiDB data
        
        # Query gold contract scores
        score_result = await db.execute(
            select(GoldContractScore).where(GoldContractScore.contract_id == contract_id)
        )
        score = score_result.scalar_one_or_none()
        
        # Query gold findings
        findings_result = await db.execute(
            select(GoldFinding).where(GoldFinding.contract_id == contract_id)
        )
        findings = findings_result.scalars().all()
        
        # Query gold suggestions
        suggestions_result = await db.execute(
            select(GoldSuggestion).where(GoldSuggestion.contract_id == contract_id)
        )
        suggestions = suggestions_result.scalars().all()
        
        # Query alerts
        alerts_result = await db.execute(
            select(Alert).where(Alert.contract_id == contract_id)
        )
        alerts = alerts_result.scalars().all()
        
        # Create highlights from clause spans for document viewer
        highlights = []
        logger.info(f"Processing {len(contract.clause_spans) if contract.clause_spans else 0} clause spans for highlights")
        
        # Get text content for pattern-based highlighting
        text_content = ""
        if contract.text_raw and contract.text_raw.raw_text:
            text_content = contract.text_raw.raw_text
        
        # Always generate pattern-based highlights first (more comprehensive)
        if text_content:
            pattern_highlights = document_highlighter.generate_highlights(text_content)
            highlights.extend(pattern_highlights)
            logger.info(f"Generated {len(pattern_highlights)} pattern-based highlights")
        
        # Add clause span highlights if available (additional coverage)
        if contract.clause_spans and len(contract.clause_spans) > 0:
            clause_highlights = []
            
            for clause_span in contract.clause_spans:
                # Map clause types to risk levels
                risk_mapping = {
                    "liability": "high",
                    "termination": "medium", 
                    "payment": "low",
                    "confidentiality": "low",
                    "intellectual_property": "high",
                    "auto_renewal": "medium",
                    "force_majeure": "low",
                    "indemnification": "high",
                    "penalty": "medium",
                    "jurisdiction": "medium"
                }
                
                risk_level = risk_mapping.get(clause_span.clause_type, "medium")
                
                clause_highlights.append({
                    "start_offset": clause_span.start_offset,
                    "end_offset": clause_span.end_offset,
                    "risk_level": risk_level,
                    "clause_type": clause_span.clause_type,
                    "title": clause_span.clause_name or f"{clause_span.clause_type.replace('_', ' ').title()} Clause",
                    "description": clause_span.snippet or f"Identified {clause_span.clause_type} clause",
                    "confidence": clause_span.confidence or 0.8,
                    "source": "clause_span"
                })
            
            highlights.extend(clause_highlights)
            logger.info(f"Added {len(clause_highlights)} clause span highlights")
        
        # Remove overlapping highlights (but be less aggressive)
        if highlights:
            original_count = len(highlights)
            highlights = document_highlighter._remove_overlaps(highlights)
            logger.info(f"Highlight deduplication: {original_count} -> {len(highlights)} highlights after overlap removal")

        # Convert highlights to findings format for consistent frontend display
        highlight_findings = []
        if highlights:
            for i, highlight in enumerate(highlights):
                highlight_findings.append({
                    "finding_id": f"highlight_{i}",
                    "type": highlight.get("clause_type", "risk_pattern"),
                    "severity": highlight.get("risk_level", "medium"),
                    "title": highlight.get("title", "Risk Pattern Detected"),
                    "description": highlight.get("description", "Pattern-based risk detection"),
                    "confidence": highlight.get("confidence", 0.8),
                    "source": "pattern_analysis",
                    "start_offset": highlight.get("start_offset"),
                    "end_offset": highlight.get("end_offset")
                })

        # Combine database findings with highlight findings
        all_findings = []
        if findings:
            all_findings.extend([
                {
                    "finding_id": finding.finding_id,
                    "type": finding.finding_type,
                    "severity": finding.severity,
                    "title": finding.title,
                    "description": finding.description,
                    "confidence": finding.confidence,
                    "source": "database"
                }
                for finding in findings
            ])
        
        # Add highlight findings
        all_findings.extend(highlight_findings)

        # Build response with actual TiDB data
        analysis_data = {
            "contract": {
                "contract_id": contract.contract_id,
                "filename": contract.filename,
                "status": contract.status,
                "created_at": contract.created_at.isoformat()
            },
            "score": {
                "overall_score": score.overall_score,
                "risk_level": score.risk_level,
                "category_scores": score.category_scores or {}
            } if score else None,
            "findings": all_findings,
            "suggestions": [
                {
                    "suggestion_id": suggestion.suggestion_id,
                    "type": suggestion.suggestion_type,
                    "title": suggestion.title,
                    "description": suggestion.description,
                    "priority": suggestion.priority,
                    "status": suggestion.status
                }
                for suggestion in suggestions
            ] if suggestions else [],
            "alerts": [
                {
                    "alert_id": alert.alert_id,
                    "type": alert.alert_type,
                    "severity": alert.severity,
                    "title": alert.title,
                    "status": alert.status,
                    "created_at": alert.created_at.isoformat()
                }
                for alert in alerts
            ] if alerts else [],
            "highlights": highlights  # Add highlights for document viewer
        }
        
        logger.info(f"📊 Analysis data retrieved for {contract_id}: "
                   f"Score: {'✓' if score else '✗'}, "
                   f"Database Findings: {len(findings) if findings else 0}, "
                   f"Pattern Highlights: {len(highlights)}, "
                   f"Total Findings: {len(all_findings)}, "
                   f"Suggestions: {len(suggestions)}, "
                   f"Alerts: {len(alerts)}")
        
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

@router.post("/{contract_id}/force-stop")
async def force_stop_processing(
    contract_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Force stop stuck processing and reset document status"""
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
                detail="Document not found or you don't have permission to modify it"
            )
        
        # Force stop processing
        logger.info(f"🛑 Force stopping processing for contract {contract_id}")
        
        # Update all running processing runs to failed
        await db.execute(
            text("""
                UPDATE processing_runs 
                SET status = 'force_stopped', 
                    error_message = 'Processing force stopped by user',
                    completed_at = NOW()
                WHERE contract_id = :contract_id 
                AND status IN ('running', 'pending')
            """),
            {"contract_id": contract_id}
        )
        
        # Update all running processing steps to failed
        await db.execute(
            text("""
                UPDATE processing_steps 
                SET status = 'force_stopped',
                    error_message = 'Processing force stopped by user'
                WHERE run_id IN (
                    SELECT run_id FROM processing_runs WHERE contract_id = :contract_id
                ) AND status IN ('running', 'pending')
            """),
            {"contract_id": contract_id}
        )
        
        # Reset contract status to uploaded so it can be processed again or deleted
        contract.status = "uploaded"
        await db.commit()
        
        return {
            "message": "Processing force stopped successfully",
            "contract_id": contract_id,
            "filename": contract.filename,
            "status": "uploaded"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to force stop processing for {contract_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to force stop processing: {str(e)}"
        )

@router.delete("/{contract_id}")
async def delete_document(
    contract_id: str,
    force: bool = False,
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
        
        # Check if document is processing and force is not set
        if contract.status == "processing" and not force:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete document while processing. Use force=true parameter or force-stop processing first."
            )
        
        # If force delete, stop processing first
        if contract.status == "processing" and force:
            logger.info(f"🛑 Force stopping processing before deletion for contract {contract_id}")
            
            # Force stop processing
            await db.execute(
                text("""
                    UPDATE processing_runs 
                    SET status = 'force_stopped', 
                        error_message = 'Processing stopped due to force delete',
                        completed_at = NOW()
                    WHERE contract_id = :contract_id 
                    AND status IN ('running', 'pending')
                """),
                {"contract_id": contract_id}
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
        
        # Get contract info for debugging
        async for db in get_operational_db():
            try:
                result = await db.execute(
                    text("SELECT filename, mime_type, file_size FROM bronze_contracts WHERE contract_id = :contract_id"),
                    {"contract_id": contract_id}
                )
                contract_info = result.fetchone()
                if contract_info:
                    logger.info(f"📄 Processing: {contract_info.filename} ({contract_info.mime_type}, {contract_info.file_size} bytes)")
            except Exception as e:
                logger.warning(f"Could not get contract info: {e}")
            finally:
                break
        
        # Set processing timeout (5 minutes for better responsiveness)
        timeout_seconds = 300  # 5 minutes
        
        # Update contract status to processing
        async for db in get_operational_db():
            try:
                await db.execute(
                    text("UPDATE bronze_contracts SET status = 'processing' WHERE contract_id = :contract_id"),
                    {"contract_id": contract_id}
                )
                await db.commit()
                logger.info(f"✅ Status updated to 'processing' for {contract_id}")
            except Exception as e:
                logger.error(f"❌ Failed to update status to processing: {e}")
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

# =============================================================================
# AGENT ENDPOINTS - AWS Bedrock AgentCore Compatible
# =============================================================================

@router.post("/{contract_id}/analyze")
async def analyze_document(
    contract_id: str,
    document_type: Optional[str] = Form(None),
    priority: str = Form("medium"),
    timeout_seconds: int = Form(60),
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """
    Perform comprehensive document analysis using standardized agents
    AWS Bedrock AgentCore compatible endpoint
    """
    try:
        # Verify document ownership
        result = await db.execute(
            select(BronzeContract).where(
                (BronzeContract.contract_id == contract_id) & 
                (BronzeContract.owner_user_id == current_user.user_id)
            )
        )
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Rate limiting
        if not rate_limiter.is_allowed(f"analyze_{current_user.user_id}", max_requests=20, window_seconds=3600):
            raise HTTPException(
                status_code=429,
                detail="Analysis rate limit exceeded. Please try again later."
            )
        
        # Perform analysis using standardized agent API
        analysis_result = await agent_api.analyze_document(
            contract_id=contract_id,
            user_id=current_user.user_id,
            document_type=document_type,
            priority=priority,
            timeout_seconds=timeout_seconds
        )
        
        return {
            "message": "Document analysis completed",
            "contract_id": contract_id,
            "filename": contract.filename,
            **analysis_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.post("/{contract_id}/search")
async def search_document(
    contract_id: str,
    query: str = Form(...),
    timeout_seconds: int = Form(90),
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """
    Search within a specific document using standardized agents
    AWS Bedrock AgentCore compatible endpoint
    """
    try:
        # Verify document ownership
        result = await db.execute(
            select(BronzeContract).where(
                (BronzeContract.contract_id == contract_id) & 
                (BronzeContract.owner_user_id == current_user.user_id)
            )
        )
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Rate limiting
        if not rate_limiter.is_allowed(f"search_{current_user.user_id}", max_requests=50, window_seconds=3600):
            raise HTTPException(
                status_code=429,
                detail="Search rate limit exceeded. Please try again later."
            )
        
        # Perform search using standardized agent API
        search_result = await agent_api.search_document(
            query=query,
            contract_id=contract_id,
            user_id=current_user.user_id,
            timeout_seconds=timeout_seconds
        )
        
        return {
            "message": "Document search completed",
            "contract_id": contract_id,
            "filename": contract.filename,
            "query": query,
            **search_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/{contract_id}/quick-analyze")
async def quick_analyze_document(
    contract_id: str,
    document_type: Optional[str] = None,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """
    Quick document analysis with minimal processing
    AWS Bedrock AgentCore compatible endpoint
    """
    try:
        # Verify document ownership
        result = await db.execute(
            select(BronzeContract).where(
                (BronzeContract.contract_id == contract_id) & 
                (BronzeContract.owner_user_id == current_user.user_id)
            )
        )
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Rate limiting
        if not rate_limiter.is_allowed(f"quick_analyze_{current_user.user_id}", max_requests=30, window_seconds=3600):
            raise HTTPException(
                status_code=429,
                detail="Quick analysis rate limit exceeded. Please try again later."
            )
        
        # Perform quick analysis
        analysis_result = await agent_api.quick_analysis(
            contract_id=contract_id,
            user_id=current_user.user_id,
            document_type=document_type
        )
        
        return {
            "message": "Quick analysis completed",
            "contract_id": contract_id,
            "filename": contract.filename,
            **analysis_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quick analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Quick analysis failed: {str(e)}")

@router.get("/{contract_id}/quick-search")
async def quick_search_document(
    contract_id: str,
    query: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """
    Quick document search with minimal processing
    AWS Bedrock AgentCore compatible endpoint
    """
    try:
        # Verify document ownership
        result = await db.execute(
            select(BronzeContract).where(
                (BronzeContract.contract_id == contract_id) & 
                (BronzeContract.owner_user_id == current_user.user_id)
            )
        )
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Rate limiting
        if not rate_limiter.is_allowed(f"quick_search_{current_user.user_id}", max_requests=60, window_seconds=3600):
            raise HTTPException(
                status_code=429,
                detail="Quick search rate limit exceeded. Please try again later."
            )
        
        # Perform quick search
        search_result = await agent_api.quick_search(
            query=query,
            contract_id=contract_id,
            user_id=current_user.user_id
        )
        
        return {
            "message": "Quick search completed",
            "contract_id": contract_id,
            "filename": contract.filename,
            "query": query,
            **search_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quick search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Quick search failed: {str(e)}")

@router.get("/agents/status")
async def get_agent_system_status(
    current_user = Depends(get_current_active_user)
):
    """
    Get agent system health and status information
    AWS Bedrock AgentCore compatible endpoint
    """
    try:
        status = agent_api.get_system_status()
        
        return {
            "message": "Agent system status retrieved",
            **status
        }
        
    except Exception as e:
        logger.error(f"Agent status check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@router.get("/agents/{agent_type}/info")
async def get_agent_info(
    agent_type: str,
    current_user = Depends(get_current_active_user)
):
    """
    Get information about a specific agent type
    AWS Bedrock AgentCore compatible endpoint
    """
    try:
        agent_info = agent_api.get_agent_info(agent_type)
        
        return {
            "message": f"Agent information for {agent_type}",
            "agent_type": agent_type,
            **agent_info
        }
        
    except Exception as e:
        logger.error(f"Agent info retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Agent info failed: {str(e)}")

@router.post("/{contract_id}/test-analysis")
async def test_document_analysis(
    contract_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """
    Test endpoint to trigger document analysis and check if findings are saved
    """
    try:
        # Verify document ownership
        result = await db.execute(
            select(BronzeContract).where(
                (BronzeContract.contract_id == contract_id) & 
                (BronzeContract.owner_user_id == current_user.user_id)
            )
        )
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Trigger the multi-agent analysis step directly
        from app.services.document_processor import document_processor
        
        analysis_result = await document_processor._step_multi_agent_analysis(
            contract_id=contract_id,
            user_id=current_user.user_id,
            db=db
        )
        
        # Check what was actually saved
        findings_result = await db.execute(
            select(GoldFinding).where(GoldFinding.contract_id == contract_id)
        )
        findings = findings_result.scalars().all()
        
        score_result = await db.execute(
            select(GoldContractScore).where(GoldContractScore.contract_id == contract_id)
        )
        score = score_result.scalar_one_or_none()
        
        return {
            "message": "Test analysis completed",
            "contract_id": contract_id,
            "analysis_result": analysis_result,
            "findings_in_db": len(findings),
            "score_in_db": score.overall_score if score else None,
            "findings_sample": [
                {
                    "type": f.finding_type,
                    "severity": f.severity,
                    "title": f.title,
                    "confidence": f.confidence
                }
                for f in findings[:3]
            ] if findings else []
        }
        
    except Exception as e:
        logger.error(f"Test analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Test analysis failed: {str(e)}")
