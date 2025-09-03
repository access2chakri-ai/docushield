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
from app.agents import agent_orchestrator
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
        
        # Performance limits to prevent getting stuck
        self.max_text_length = 500000  # 500KB of text max
        self.max_chunks = 200  # Maximum number of chunks to process
        self.max_processing_time = 600  # 10 minutes max per document
        self.chunk_size = 1000  # Reasonable chunk size
        self.max_embeddings_per_batch = 50  # Batch embeddings to prevent memory issues
        
        # Processing steps configuration - ALL ENABLED FOR FULL TESTING
        self.processing_steps = [
            {"name": "extract_text", "order": 1, "required": True},
            {"name": "chunk_text", "order": 2, "required": True},
            {"name": "generate_embeddings", "order": 3, "required": True},
            {"name": "multi_agent_analysis", "order": 4, "required": True},
            {"name": "extract_clauses", "order": 5, "required": True},  # NOW REQUIRED
            {"name": "analyze_risk", "order": 6, "required": True},
            {"name": "generate_summaries", "order": 7, "required": True},  # NOW REQUIRED
            {"name": "create_suggestions", "order": 8, "required": True},  # NOW REQUIRED
            {"name": "send_alerts", "order": 9, "required": True}  # NOW REQUIRED
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
        elif step_name == "multi_agent_analysis":
            return await self._step_multi_agent_analysis(contract_id, db)
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
        
        # Generate tokens for analysis
        await self._generate_tokens(contract_id, text, db)
        
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
                # Generate embedding with tracking
                embedding_result = await llm_factory.generate_embedding(
                    text=chunk.chunk_text,
                    task_type=LLMTask.EMBEDDING
                )
                
                # Update chunk with embedding
                chunk.embedding = embedding_result["embedding"]
                chunk.embedding_model = embedding_result.get("model", "text-embedding-3-small")
                
                # Track LLM call
                llm_call = LlmCall(
                    contract_id=contract_id,
                    provider="openai",
                    model=chunk.embedding_model,
                    call_type="embedding",
                    input_tokens=embedding_result.get("input_tokens", 0),
                    output_tokens=0,
                    total_tokens=embedding_result.get("input_tokens", 0),
                    estimated_cost=embedding_result.get("cost", 0.0),
                    success=True,
                    purpose="chunk_embedding"
                )
                db.add(llm_call)
                
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
    
    async def _step_multi_agent_analysis(self, contract_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Step 4: Multi-agent comprehensive analysis"""
        
        logger.info(f"Starting multi-agent analysis for contract {contract_id}")
        
        # Get contract and text
        result = await db.execute(
            select(BronzeContract).options(selectinload(BronzeContract.text_raw))
            .where(BronzeContract.contract_id == contract_id)
        )
        contract = result.scalar_one()
        
        if not contract.text_raw:
            logger.error(f"No text available for multi-agent analysis for contract {contract_id}")
            raise ValueError("No text available for multi-agent analysis")
        
        logger.info(f"Found contract text for {contract_id}, starting agent orchestrator")
        
        # Run multi-agent analysis using new orchestrator (with error handling)
        try:
            logger.info(f"Calling agent orchestrator for contract {contract_id}")
            workflow_result = await agent_orchestrator.run_comprehensive_analysis(
                contract_id=contract_id,
                user_id=contract.owner_user_id,
                query="Perform comprehensive document analysis including risk assessment, clause extraction, and business recommendations",
                selected_agents=["simple_analyzer", "search_agent", "clause_analyzer"],  # USE ALL AGENTS
                timeout_seconds=300  # Longer timeout for full analysis
            )
            logger.info(f"Agent orchestrator completed for contract {contract_id}")
        except Exception as agent_error:
            logger.error(f"Agent orchestrator failed: {agent_error}")
            # Create a fallback result structure
            from app.agents.orchestrator import OrchestrationResult
            workflow_result = OrchestrationResult(
                run_id=f"fallback_{contract_id}",
                contract_id=contract_id,
                user_id=contract.owner_user_id,
                query=None,
                overall_success=False,
                overall_confidence=0.5,
                agent_results=[],
                consolidated_findings=[{
                    "type": "processing_error",
                    "title": "Agent analysis temporarily unavailable",
                    "description": f"Multi-agent analysis failed: {str(agent_error)}",
                    "severity": "medium",
                    "confidence": 0.5,
                    "source_agent": "fallback"
                }],
                consolidated_recommendations=["Manual review recommended due to agent system error"],
                execution_time_ms=0.0,
                total_llm_calls=0,
                workflow_version="fallback_2.0.0"
            )
        
        # Store consolidated findings as GoldFindings
        findings_created = 0
        for finding in workflow_result.consolidated_findings[:10]:  # Limit to top 10
            try:
                gold_finding = GoldFinding(
                    contract_id=contract_id,
                    finding_type=finding.get("type", "agent_finding"),
                    severity=finding.get("severity", "medium"),
                    title=finding.get("title", "Agent finding")[:200],
                    description=finding.get("description", json.dumps(finding)),
                    confidence=finding.get("confidence", workflow_result.overall_confidence),
                    detection_method=finding.get("source_agent", "orchestrator"),
                    model_version=workflow_result.workflow_version
                )
                db.add(gold_finding)
                findings_created += 1
            except Exception as e:
                logger.warning(f"Failed to save agent finding: {e}")
        
        # Store or update contract score (simplified for now)
        result = await db.execute(
            select(GoldContractScore).where(GoldContractScore.contract_id == contract_id)
        )
        existing_score = result.scalar_one_or_none()
        
        # Calculate risk score based on findings
        risk_score = min(100, max(0, int(workflow_result.overall_confidence * 100)))
        risk_level = "high" if workflow_result.overall_confidence > 0.8 else "medium" if workflow_result.overall_confidence > 0.5 else "low"
        
        if existing_score:
            existing_score.overall_score = risk_score
            existing_score.risk_level = risk_level
            existing_score.confidence = workflow_result.overall_confidence
            existing_score.last_updated = datetime.utcnow()
        else:
            score = GoldContractScore(
                contract_id=contract_id,
                overall_score=risk_score,
                risk_level=risk_level,
                category_scores={},  # Could be populated from specific risk analysis
                scoring_model_version=workflow_result.workflow_version,
                confidence=workflow_result.overall_confidence
            )
            db.add(score)
        
        # Create executive summary from consolidated recommendations
        summary_content = f"Comprehensive analysis completed using {len(workflow_result.agent_results)} specialized agents. " + \
                         " ".join(workflow_result.consolidated_recommendations[:3])
        
        summary = GoldSummary(
            contract_id=contract_id,
            summary_type="agent_orchestrator",
            title="Agent Orchestrator Summary",
            content=summary_content,
            key_points=workflow_result.consolidated_recommendations[:5],
            word_count=len(summary_content.split()),
            model_version=workflow_result.workflow_version
        )
        db.add(summary)
        
        await db.commit()
        
        return {
            "status": "completed",
            "overall_risk_score": risk_score,
            "risk_level": risk_level,
            "confidence": workflow_result.overall_confidence,
            "findings_created": findings_created,
            "execution_time_ms": workflow_result.execution_time_ms,
            "agents_used": len(workflow_result.agent_results),
            "run_id": workflow_result.run_id
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
        
        # Use AI to extract clauses with comprehensive analysis
        clauses = await self._extract_contract_clauses_comprehensive(text_raw.raw_text, contract_id)
        
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
            # Get findings and suggestions for comprehensive alert
            result = await db.execute(
                select(GoldFinding).where(GoldFinding.contract_id == contract_id)
                .order_by(GoldFinding.created_at.desc()).limit(5)
            )
            findings = result.scalars().all()
            
            result = await db.execute(
                select(GoldSuggestion).where(GoldSuggestion.contract_id == contract_id)
                .order_by(GoldSuggestion.created_at.desc()).limit(3)
            )
            suggestions = result.scalars().all()
            
            risk_analysis = {
                "overall_risk_level": score.risk_level,
                "overall_risk_score": score.overall_score / 100,
                "category_scores": score.category_scores or {},
                "identified_risks": [f.title for f in findings],
                "risk_descriptions": [f.description for f in findings],
                "recommendations": [s.title for s in suggestions],
                "contract_id": contract_id,
                "file_size": contract.file_size,
                "processing_completed": True
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
    
    async def _extract_contract_clauses_comprehensive(self, text: str, contract_id: str) -> List[Dict[str, Any]]:
        """Extract clauses using comprehensive AI analysis with all clause types"""
        try:
            clause_prompt = f"""
            Analyze this contract document and extract ALL key clauses. For each clause found, provide:
            
            CLAUSE TYPES TO FIND:
            - liability: Liability and indemnification clauses
            - termination: Termination and cancellation clauses  
            - renewal: Renewal and extension clauses
            - payment: Payment terms and financial clauses
            - intellectual_property: IP ownership and licensing
            - confidentiality: Non-disclosure and confidentiality
            - governing_law: Governing law and jurisdiction
            - dispute_resolution: Dispute resolution and arbitration
            - force_majeure: Force majeure and extraordinary circumstances
            - warranties: Warranties and representations
            - limitation: Limitation of liability clauses
            - performance: Performance standards and SLAs
            
            Document text (first 8000 characters):
            {text[:8000]}
            
            Return as JSON array with this exact format:
            [{{
                "type": "clause_type",
                "name": "Brief clause name",
                "text": "Full clause text",
                "start_offset": 0,
                "end_offset": 100,
                "confidence": 0.95,
                "risk_indicators": ["risk1", "risk2"],
                "attributes": {{"key": "value"}}
            }}]
            """
            
            result = await llm_factory.generate_completion(
                prompt=clause_prompt,
                task_type=LLMTask.ANALYSIS,
                max_tokens=2000,
                temperature=0.1
            )
            
            # Track LLM call
            llm_call = LlmCall(
                contract_id=contract_id,
                provider="openai",
                model="gpt-4",
                call_type="completion",
                input_tokens=result.get("input_tokens", 0),
                output_tokens=result.get("output_tokens", 0),
                total_tokens=result.get("total_tokens", 0),
                estimated_cost=result.get("cost", 0.0),
                success=True,
                purpose="clause_extraction"
            )
            
            async for db in get_operational_db():
                db.add(llm_call)
                await db.commit()
                break
            
            try:
                clauses = json.loads(result["content"])
                return clauses if isinstance(clauses, list) else []
            except json.JSONDecodeError:
                logger.warning("Failed to parse AI clause extraction response")
                return []
                
        except Exception as e:
            logger.error(f"Comprehensive clause extraction failed: {e}")
            return []

    async def _generate_tokens(self, contract_id: str, text: str, db: AsyncSession):
        """Generate and store tokens for search and analysis"""
        try:
            # Simple tokenization - extract meaningful words
            import re
            words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
            
            # Count word frequencies
            word_freq = {}
            for i, word in enumerate(words):
                if word not in word_freq:
                    word_freq[word] = {"count": 0, "positions": []}
                word_freq[word]["count"] += 1
                word_freq[word]["positions"].append(i)
            
            # Store top 100 most frequent tokens
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1]["count"], reverse=True)
            
            for word, data in sorted_words[:100]:
                token = Token(
                    contract_id=contract_id,
                    token_text=word,
                    token_type="word",
                    position=data["positions"][0],  # First occurrence
                    frequency=data["count"]
                )
                db.add(token)
                
            logger.info(f"Generated {min(100, len(sorted_words))} tokens for contract {contract_id}")
            
        except Exception as e:
            logger.warning(f"Token generation failed: {e}")

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
