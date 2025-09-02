"""
Digital Twin Document Processing Pipeline
Bronze → Silver → Gold processing with full observability and resumability
"""
import hashlib
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import asyncio
import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from sqlalchemy.orm import selectinload

from app.database import get_operational_db, ClusterType
from app.models import (
    BronzeContract, BronzeContractTextRaw, ProcessingRun, ProcessingStep,
    SilverChunk, SilverClauseSpan, Token,
    GoldContractScore, GoldFinding, GoldSuggestion, GoldSummary, Alert,
    LlmCall, User
)
from app.services.risk_analyzer import risk_analyzer, DocumentType, RiskLevel
from app.services.external_integrations import external_integrations
from app.services.llm_factory import llm_factory, LLMTask
from app.core.config import settings

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """
    Digital Twin Document Processing Pipeline
    Implements Bronze → Silver → Gold architecture with full observability
    """
    
    def __init__(self):
        # Using LLM Factory for multi-provider support
        self.pipeline_version = "1.0.0"
        
        # Processing steps configuration
        self.processing_steps = [
            {"name": "extract_text", "order": 1, "required": True},
            {"name": "chunk_text", "order": 2, "required": True},
            {"name": "generate_embeddings", "order": 3, "required": True},
            {"name": "extract_clauses", "order": 4, "required": False},
            {"name": "analyze_risk", "order": 5, "required": True},
            {"name": "generate_summaries", "order": 6, "required": False},
            {"name": "create_suggestions", "order": 7, "required": False},
            {"name": "send_alerts", "order": 8, "required": False}
        ]
    
    async def process_contract(
        self, 
        contract_id: str, 
        user_id: str,
        trigger: str = "manual",
        resume_from_step: Optional[str] = None
    ) -> str:
        """
        Main processing pipeline entry point
        Returns processing run ID
        """
        async for db in get_operational_db():
            try:
                # Get contract
                result = await db.execute(
                    select(BronzeContract).where(BronzeContract.contract_id == contract_id)
                )
                contract = result.scalar_one_or_none()
                
                if not contract:
                    raise ValueError(f"Contract {contract_id} not found")
                
                # Create processing run
                processing_run = ProcessingRun(
                    contract_id=contract_id,
                    pipeline_version=self.pipeline_version,
                    trigger=trigger,
                    status="running"
                )
                db.add(processing_run)
                await db.commit()
                await db.refresh(processing_run)
                
                logger.info(f"Started processing run {processing_run.run_id} for contract {contract_id}")
                
                # Create processing steps
                steps_to_run = self.processing_steps
                if resume_from_step:
                    # Resume from specific step
                    resume_order = next(
                        (step["order"] for step in self.processing_steps if step["name"] == resume_from_step),
                        1
                    )
                    steps_to_run = [step for step in self.processing_steps if step["order"] >= resume_order]
                
                # Create step records
                for step_config in steps_to_run:
                    step = ProcessingStep(
                        run_id=processing_run.run_id,
                        step_name=step_config["name"],
                        step_order=step_config["order"],
                        status="pending"
                    )
                    db.add(step)
                
                await db.commit()
                
                # Execute pipeline steps
                await self._execute_pipeline(processing_run.run_id, steps_to_run, db)
                
                # Update run status
                processing_run.status = "completed"
                processing_run.completed_at = datetime.utcnow()
                await db.commit()
                
                logger.info(f"Processing run {processing_run.run_id} completed successfully")
                return processing_run.run_id
                
            except Exception as e:
                logger.error(f"Processing failed for contract {contract_id}: {e}")
                # Update run status to failed
                if 'processing_run' in locals():
                    processing_run.status = "failed"
                    processing_run.error_message = str(e)
                    processing_run.completed_at = datetime.utcnow()
                    await db.commit()
                raise
    
    async def _execute_pipeline(self, run_id: str, steps: List[Dict], db: AsyncSession):
        """Execute pipeline steps with error handling and resumability"""
        
        for step_config in steps:
            step_name = step_config["name"]
            
            # Get step record
            result = await db.execute(
                select(ProcessingStep).where(
                    ProcessingStep.run_id == run_id,
                    ProcessingStep.step_name == step_name
                )
            )
            step = result.scalar_one()
            
            try:
                # Update step status
                step.status = "running"
                step.started_at = datetime.utcnow()
                await db.commit()
                
                # Execute step
                step_result = await self._execute_step(step_name, run_id, db)
                
                # Update step with results
                step.status = "completed"
                step.completed_at = datetime.utcnow()
                step.step_metadata = step_result
                await db.commit()
                
                logger.info(f"Step {step_name} completed for run {run_id}")
                
            except Exception as e:
                logger.error(f"Step {step_name} failed for run {run_id}: {e}")
                
                # Update step status
                step.status = "failed"
                step.error_message = str(e)
                step.completed_at = datetime.utcnow()
                await db.commit()
                
                # Check if step is required
                if step_config.get("required", True):
                    raise  # Fail the entire pipeline
                else:
                    # Skip optional step and continue
                    step.status = "skipped"
                    await db.commit()
                    continue
    
    async def _execute_step(self, step_name: str, run_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Execute individual processing step"""
        
        # Get contract for this run
        result = await db.execute(
            select(ProcessingRun).where(ProcessingRun.run_id == run_id)
        )
        run = result.scalar_one()
        contract_id = run.contract_id
        
        if step_name == "extract_text":
            return await self._step_extract_text(contract_id, db)
        elif step_name == "chunk_text":
            return await self._step_chunk_text(contract_id, db)
        elif step_name == "generate_embeddings":
            return await self._step_generate_embeddings(contract_id, db)
        elif step_name == "extract_clauses":
            return await self._step_extract_clauses(contract_id, db)
        elif step_name == "analyze_risk":
            return await self._step_analyze_risk(contract_id, db)
        elif step_name == "generate_summaries":
            return await self._step_generate_summaries(contract_id, db)
        elif step_name == "create_suggestions":
            return await self._step_create_suggestions(contract_id, db)
        elif step_name == "send_alerts":
            return await self._step_send_alerts(contract_id, db)
        else:
            raise ValueError(f"Unknown step: {step_name}")
    
    async def _step_extract_text(self, contract_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Step 1: Extract text from contract file"""
        
        # Get contract
        result = await db.execute(
            select(BronzeContract).where(BronzeContract.contract_id == contract_id)
        )
        contract = result.scalar_one()
        
        # Check if text already extracted
        result = await db.execute(
            select(BronzeContractTextRaw).where(
                BronzeContractTextRaw.contract_id == contract_id
            )
        )
        existing_text = result.scalar_one_or_none()
        
        if existing_text:
            return {"status": "already_exists", "text_length": len(existing_text.raw_text)}
        
        # Extract text based on mime type
        if not contract.raw_bytes:
            raise ValueError("No raw bytes available for text extraction")
        
        if contract.mime_type == "application/pdf":
            text_content = await self._extract_pdf_text(contract.raw_bytes)
        elif "wordprocessingml" in contract.mime_type:
            text_content = await self._extract_docx_text(contract.raw_bytes)
        elif "text/" in contract.mime_type:
            text_content = contract.raw_bytes.decode('utf-8', errors='ignore')
        else:
            raise ValueError(f"Unsupported mime type: {contract.mime_type}")
        
        if not text_content.strip():
            raise ValueError("No text content extracted from file")
        
        # Calculate hash
        text_hash = hashlib.sha256(text_content.encode()).hexdigest()
        
        # Store extracted text
        contract_text = BronzeContractTextRaw(
            contract_id=contract_id,
            raw_text=text_content,
            parser_version="1.0.0",
            text_hash=text_hash,
            language="en",  # TODO: Detect language
            page_count=None,  # TODO: Extract page count
            extraction_metadata={
                "mime_type": contract.mime_type,
                "file_size": contract.file_size,
                "extraction_method": "automated"
            }
        )
        
        db.add(contract_text)
        await db.commit()
        
        return {
            "status": "extracted",
            "text_length": len(text_content),
            "text_hash": text_hash
        }
    
    async def _step_chunk_text(self, contract_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Step 2: Chunk text for vector search"""
        
        # Get raw text
        result = await db.execute(
            select(BronzeContractTextRaw).where(
                BronzeContractTextRaw.contract_id == contract_id
            )
        )
        text_raw = result.scalar_one()
        
        # Check if chunks already exist
        result = await db.execute(
            select(SilverChunk).where(SilverChunk.contract_id == contract_id)
        )
        existing_chunks = result.scalars().all()
        
        if existing_chunks:
            return {"status": "already_exists", "chunk_count": len(existing_chunks)}
        
        # Chunk the text (simple sliding window approach)
        chunk_size = 1000  # characters
        overlap = 200  # character overlap
        
        text = text_raw.raw_text
        chunks = []
        
        start = 0
        chunk_order = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end]
            
            # Skip very short chunks at the end
            if len(chunk_text.strip()) < 100 and chunk_order > 0:
                break
            
            chunk = SilverChunk(
                contract_id=contract_id,
                chunk_text=chunk_text,
                chunk_order=chunk_order,
                start_offset=start,
                end_offset=end,
                chunk_type="text",
                language="en",
                token_count=len(chunk_text.split())
            )
            
            chunks.append(chunk)
            db.add(chunk)
            
            chunk_order += 1
            start = end - overlap  # Overlap for context
        
        await db.commit()
        
        return {
            "status": "chunked",
            "chunk_count": len(chunks),
            "total_characters": len(text)
        }
    
    async def _step_generate_embeddings(self, contract_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Step 3: Generate vector embeddings for chunks"""
        
        # Get chunks without embeddings
        result = await db.execute(
            select(SilverChunk).where(
                SilverChunk.contract_id == contract_id,
                SilverChunk.embedding.is_(None)
            )
        )
        chunks = result.scalars().all()
        
        if not chunks:
            return {"status": "already_exists", "chunk_count": 0}
        
        embeddings_generated = 0
        
        for chunk in chunks:
            try:
                # Generate embedding
                embedding = await self._create_embedding(chunk.chunk_text, contract_id)
                
                # Update chunk with embedding
                chunk.embedding = embedding
                chunk.embedding_model = "text-embedding-3-small"
                
                embeddings_generated += 1
                
                # Batch commit every 10 chunks
                if embeddings_generated % 10 == 0:
                    await db.commit()
                    
            except Exception as e:
                logger.warning(f"Failed to generate embedding for chunk {chunk.chunk_id}: {e}")
                continue
        
        await db.commit()
        
        return {
            "status": "completed",
            "embeddings_generated": embeddings_generated,
            "total_chunks": len(chunks)
        }
    
    async def _step_extract_clauses(self, contract_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Step 4: Extract and identify contract clauses"""
        
        # Get contract text
        result = await db.execute(
            select(BronzeContractTextRaw).where(
                BronzeContractTextRaw.contract_id == contract_id
            )
        )
        text_raw = result.scalar_one()
        
        # Check if clauses already extracted
        result = await db.execute(
            select(SilverClauseSpan).where(SilverClauseSpan.contract_id == contract_id)
        )
        existing_clauses = result.scalars().all()
        
        if existing_clauses:
            return {"status": "already_exists", "clause_count": len(existing_clauses)}
        
        # Use AI to extract clauses
        clauses = await self._extract_contract_clauses(text_raw.raw_text, contract_id)
        
        clause_count = 0
        for clause_data in clauses:
            try:
                clause = SilverClauseSpan(
                    contract_id=contract_id,
                    clause_type=clause_data.get("type", "unknown"),
                    clause_name=clause_data.get("name", "Unnamed clause"),
                    start_offset=clause_data.get("start_offset", 0),
                    end_offset=clause_data.get("end_offset", 100),
                    snippet=clause_data.get("text", "")[:1000],  # Limit snippet size
                    confidence=clause_data.get("confidence", 0.5),
                    attributes=clause_data.get("attributes", {}),
                    risk_indicators=clause_data.get("risk_indicators", []),
                    extraction_method="ai",
                    model_version="gpt-4"
                )
                
                db.add(clause)
                clause_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to save clause: {e}")
                continue
        
        await db.commit()
        
        return {
            "status": "completed",
            "clause_count": clause_count
        }
    
    async def _step_analyze_risk(self, contract_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Step 5: Analyze contract risks and generate scores"""
        
        # Get contract and text
        result = await db.execute(
            select(BronzeContract).options(selectinload(BronzeContract.text_raw))
            .where(BronzeContract.contract_id == contract_id)
        )
        contract = result.scalar_one()
        
        if not contract.text_raw:
            raise ValueError("No text available for risk analysis")
        
        # Check if scores already exist
        result = await db.execute(
            select(GoldContractScore).where(GoldContractScore.contract_id == contract_id)
        )
        existing_score = result.scalar_one_or_none()
        
        # Run risk analysis
        risk_analysis = await risk_analyzer.analyze_document(
            title=contract.filename,
            content=contract.text_raw.raw_text,
            doc_type=DocumentType.CONTRACT
        )
        
        # Create or update contract score
        if existing_score:
            existing_score.overall_score = int(risk_analysis["overall_risk_score"] * 100)
            existing_score.risk_level = risk_analysis["overall_risk_level"]
            existing_score.category_scores = risk_analysis.get("category_scores", {})
            existing_score.last_updated = datetime.utcnow()
        else:
            score = GoldContractScore(
                contract_id=contract_id,
                overall_score=int(risk_analysis["overall_risk_score"] * 100),
                risk_level=risk_analysis["overall_risk_level"],
                category_scores=risk_analysis.get("category_scores", {}),
                scoring_model_version="1.0.0",
                confidence=0.8
            )
            db.add(score)
        
        # Create findings
        findings_created = 0
        for risk in risk_analysis.get("identified_risks", []):
            finding = GoldFinding(
                contract_id=contract_id,
                finding_type=risk.get("type", "unknown"),
                severity=risk.get("level", "medium"),
                title=risk.get("description", "Risk identified")[:200],
                description=risk.get("evidence", "No details available"),
                confidence=risk.get("confidence", 0.5),
                detection_method="ai",
                model_version="1.0.0"
            )
            db.add(finding)
            findings_created += 1
        
        await db.commit()
        
        return {
            "status": "completed",
            "overall_score": int(risk_analysis["overall_risk_score"] * 100),
            "risk_level": risk_analysis["overall_risk_level"],
            "findings_created": findings_created
        }
    
    async def _step_generate_summaries(self, contract_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Step 6: Generate executive and detailed summaries"""
        
        # Get contract text
        result = await db.execute(
            select(BronzeContract).options(selectinload(BronzeContract.text_raw))
            .where(BronzeContract.contract_id == contract_id)
        )
        contract = result.scalar_one()
        
        # Check if summaries already exist
        result = await db.execute(
            select(GoldSummary).where(GoldSummary.contract_id == contract_id)
        )
        existing_summaries = result.scalars().all()
        
        if existing_summaries:
            return {"status": "already_exists", "summary_count": len(existing_summaries)}
        
        summaries_created = 0
        
        # Generate executive summary
        try:
            exec_summary = await self._generate_executive_summary(
                contract.text_raw.raw_text, contract_id
            )
            
            summary = GoldSummary(
                contract_id=contract_id,
                summary_type="executive",
                title="Executive Summary",
                content=exec_summary["content"],
                key_points=exec_summary.get("key_points", []),
                word_count=len(exec_summary["content"].split()),
                model_version="gpt-4"
            )
            db.add(summary)
            summaries_created += 1
            
        except Exception as e:
            logger.warning(f"Failed to generate executive summary: {e}")
        
        await db.commit()
        
        return {
            "status": "completed",
            "summaries_created": summaries_created
        }
    
    async def _step_create_suggestions(self, contract_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Step 7: Create actionable suggestions"""
        
        # Get contract findings
        result = await db.execute(
            select(GoldFinding).where(GoldFinding.contract_id == contract_id)
        )
        findings = result.scalars().all()
        
        suggestions_created = 0
        
        for finding in findings:
            if finding.severity in ["high", "critical"]:
                try:
                    suggestion = GoldSuggestion(
                        contract_id=contract_id,
                        suggestion_type="renegotiate",
                        title=f"Address {finding.title}",
                        description=f"Consider renegotiating terms related to: {finding.description}",
                        priority="high" if finding.severity == "critical" else "medium",
                        business_rationale=f"Mitigate risk: {finding.title}",
                        confidence=finding.confidence
                    )
                    db.add(suggestion)
                    suggestions_created += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to create suggestion for finding {finding.finding_id}: {e}")
        
        await db.commit()
        
        return {
            "status": "completed",
            "suggestions_created": suggestions_created
        }
    
    async def _step_send_alerts(self, contract_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Step 8: Send alerts for high-risk contracts"""
        
        # Get contract score
        result = await db.execute(
            select(GoldContractScore).where(GoldContractScore.contract_id == contract_id)
        )
        score = result.scalar_one_or_none()
        
        if not score or score.risk_level not in ["high", "critical"]:
            return {"status": "no_alerts_needed", "risk_level": score.risk_level if score else "unknown"}
        
        # Get contract details
        result = await db.execute(
            select(BronzeContract).where(BronzeContract.contract_id == contract_id)
        )
        contract = result.scalar_one()
        
        # Create alert record
        alert = Alert(
            contract_id=contract_id,
            alert_type="risk_detected",
            severity=score.risk_level,
            title=f"High Risk Contract: {contract.filename}",
            message=f"Contract {contract.filename} has been flagged with {score.risk_level} risk level (score: {score.overall_score}/100)",
            channels=["slack", "email"] if score.risk_level == "critical" else ["slack"],
            status="pending"
        )
        db.add(alert)
        await db.commit()
        
        # Send external alerts
        try:
            risk_analysis = {
                "overall_risk_level": score.risk_level,
                "overall_risk_score": score.overall_score / 100,
                "identified_risks": [],  # Would be populated from findings
                "recommendations": []  # Would be populated from suggestions
            }
            
            alert_results = await external_integrations.send_risk_alert(
                document_title=contract.filename,
                risk_analysis=risk_analysis,
                document_id=contract_id
            )
            
            # Update alert delivery status
            alert.delivery_status = alert_results
            alert.status = "sent" if any(alert_results.values()) else "failed"
            await db.commit()
            
        except Exception as e:
            logger.error(f"Failed to send external alerts: {e}")
            alert.status = "failed"
            await db.commit()
        
        return {
            "status": "completed",
            "alert_sent": alert.status == "sent",
            "delivery_status": alert.delivery_status
        }
    
    # Helper methods
    async def _extract_pdf_text(self, content: bytes) -> str:
        """Extract text from PDF bytes"""
        try:
            import io
            import PyPDF2
            
            pdf_file = io.BytesIO(content)
            reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            raise Exception(f"Failed to extract PDF text: {e}")
    
    async def _extract_docx_text(self, content: bytes) -> str:
        """Extract text from DOCX bytes"""
        try:
            import io
            import docx
            
            docx_file = io.BytesIO(content)
            doc = docx.Document(docx_file)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            raise Exception(f"Failed to extract DOCX text: {e}")
    
    async def _create_embedding(self, text: str, contract_id: str) -> List[float]:
        """Create vector embedding with LLM call tracking"""
        try:
            # Use LLM Factory for embedding generation
            result = await llm_factory.generate_embedding(
                text=text,
                contract_id=contract_id
            )
            
            return result["embedding"]
            
        except Exception as e:
            logger.error(f"Failed to create embedding: {e}")
            
            # Return dummy embedding for demo
            return [0.0] * 1536
    
    async def _extract_contract_clauses(self, text: str, contract_id: str) -> List[Dict[str, Any]]:
        """Extract contract clauses using AI"""
        try:
            clause_prompt = f"""
            Extract key clauses from this contract. Return a JSON array with this format:
            [{{
                "type": "liability|termination|renewal|payment|ip|confidentiality",
                "name": "descriptive name",
                "text": "actual clause text (first 500 chars)",
                "start_offset": 0,
                "end_offset": 100,
                "confidence": 0.8,
                "attributes": {{"key": "value"}},
                "risk_indicators": ["indicator1", "indicator2"]
            }}]
            
            Contract text (first 3000 chars):
            {text[:3000]}
            """
            
            result = await llm_factory.generate_completion(
                prompt=clause_prompt,
                task_type=LLMTask.ANALYSIS,
                max_tokens=1500,
                temperature=0.1,
                contract_id=contract_id
            )
            
            try:
                clauses = json.loads(result["content"])
                return clauses if isinstance(clauses, list) else []
            except json.JSONDecodeError:
                logger.warning("Failed to parse clause extraction response")
                return []
                
        except Exception as e:
            logger.error(f"Clause extraction failed: {e}")
            return []
    
    async def _generate_executive_summary(self, text: str, contract_id: str) -> Dict[str, Any]:
        """Generate executive summary using AI"""
        try:
            summary_prompt = f"""
            Create an executive summary of this contract. Return JSON:
            {{
                "content": "2-3 paragraph executive summary",
                "key_points": ["point1", "point2", "point3"]
            }}
            
            Contract text (first 2000 chars):
            {text[:2000]}
            """
            
            result = await llm_factory.generate_completion(
                prompt=summary_prompt,
                task_type=LLMTask.SUMMARIZATION,
                max_tokens=800,
                temperature=0.3,
                contract_id=contract_id
            )
            
            try:
                summary = json.loads(result["content"])
                return summary
            except json.JSONDecodeError:
                return {
                    "content": result["content"],
                    "key_points": []
                }
                
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return {
                "content": "Summary generation failed due to technical error.",
                "key_points": []
            }

# Global document processor instance
document_processor = DocumentProcessor()
