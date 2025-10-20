"""
Base Agent Class - AWS Bedrock AgentCore Compatible
Provides common functionality for all DocuShield agents with full TiDB integration
Enterprise-grade architecture designed for AWS Bedrock AgentCore migration
"""
import json
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, and_, or_
from sqlalchemy.orm import selectinload

from app.database import get_operational_db, get_sandbox_db, get_analytics_db
from app.models import (
    BronzeContract, BronzeContractTextRaw, SilverChunk, SilverClauseSpan, Token,
    GoldContractScore, GoldFinding, GoldSuggestion, GoldSummary, Alert,
    ProcessingRun, ProcessingStep, LlmCall, User
)
from app.services.llm_factory import LLMTask
from app.services.privacy_safe_llm import privacy_safe_llm, safe_llm_completion, safe_llm_embedding
from app.core.config import settings

logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    """AWS Bedrock AgentCore compatible agent status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

class AgentPriority(Enum):
    """AWS Bedrock AgentCore compatible priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class AgentContext:
    """AWS Bedrock AgentCore compatible context passed between agents"""
    contract_id: str
    user_id: str
    run_id: Optional[str] = None
    query: Optional[str] = None
    previous_results: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    # Enhanced context with document classification
    document_type: Optional[str] = None
    industry_type: Optional[str] = None
    document_category: Optional[str] = None
    user_description: Optional[str] = None
    external_enrichment: Dict[str, Any] = None
    # AWS Bedrock AgentCore compatibility fields
    priority: AgentPriority = AgentPriority.MEDIUM
    timeout_seconds: int = 60
    cache_enabled: bool = True
    session_id: Optional[str] = None

@dataclass
class AgentResult:
    """AWS Bedrock AgentCore compatible standardized agent result format"""
    agent_name: str
    agent_version: str
    status: AgentStatus
    confidence: float
    findings: List[Dict[str, Any]]
    recommendations: List[str]
    execution_time_ms: float
    memory_usage_mb: float
    llm_calls: int = 0
    data_sources: List[str] = None
    error_message: Optional[str] = None
    # AWS Bedrock AgentCore compatibility fields
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    
    @property
    def success(self) -> bool:
        """Backward compatibility property"""
        return self.status == AgentStatus.COMPLETED

class BaseAgent(ABC):
    """
    AWS Bedrock AgentCore compatible base class for all DocuShield agents
    Provides common TiDB operations and LLM integration with enterprise-grade reliability
    """
    
    def __init__(self, agent_name: str, version: str = "1.0.0"):
        self.agent_name = agent_name
        self.version = version
        self.logger = logging.getLogger(f"agent.{agent_name}")
        self._cache = {}
        
        # AWS Bedrock AgentCore compatibility metadata
        self.bedrock_metadata = {
            "agent_type": "document_processing",
            "framework_version": "docushield_v3",
            "bedrock_compatible": True,
            "supported_models": ["claude-3", "gpt-4", "bedrock-titan"],
            "capabilities": ["analysis", "search", "summarization", "classification"]
        }
    
    async def analyze(self, context: AgentContext) -> AgentResult:
        """
        Main analysis method with comprehensive error handling and monitoring
        AWS Bedrock AgentCore compatible
        """
        start_time = datetime.now()
        memory_start = self._get_memory_usage()
        
        try:
            # Validate context
            self._validate_context(context)
            
            # Check cache if enabled
            if context.cache_enabled:
                cached_result = self._get_cached_result(context)
                if cached_result:
                    self.logger.info(f"Returning cached result for {self.agent_name}")
                    return cached_result
            
            # Execute analysis with timeout
            result = await asyncio.wait_for(
                self._execute_analysis(context),
                timeout=context.timeout_seconds
            )
            
            # Set execution metrics
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            memory_usage = self._get_memory_usage() - memory_start
            
            result.execution_time_ms = execution_time
            result.memory_usage_mb = memory_usage
            result.session_id = context.session_id
            result.trace_id = context.run_id
            
            # Cache successful results
            if context.cache_enabled and result.status == AgentStatus.COMPLETED:
                self._cache_result(context, result)
            
            return result
            
        except asyncio.TimeoutError:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            memory_usage = self._get_memory_usage() - memory_start
            
            return self._create_error_result(
                context, AgentStatus.TIMEOUT, 
                f"Agent execution timed out after {context.timeout_seconds}s",
                execution_time, memory_usage
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            memory_usage = self._get_memory_usage() - memory_start
            
            self.logger.error(f"Agent {self.agent_name} failed: {e}")
            return self._create_error_result(
                context, AgentStatus.FAILED, str(e), execution_time, memory_usage
            )
    
    @abstractmethod
    async def _execute_analysis(self, context: AgentContext) -> AgentResult:
        """Internal analysis method - must be implemented by subclasses"""
        pass
    
    # =============================================================================
    # TiDB DATA ACCESS METHODS - Full Schema Utilization
    # =============================================================================
    
    async def get_contract_with_all_data(self, contract_id: str) -> Optional[BronzeContract]:
        """Get contract with all related data from all layers"""
        async for db in get_operational_db():
            result = await db.execute(
                select(BronzeContract)
                .options(
                    selectinload(BronzeContract.text_raw),
                    selectinload(BronzeContract.chunks),
                    selectinload(BronzeContract.clause_spans),
                    selectinload(BronzeContract.scores),
                    selectinload(BronzeContract.findings),
                    selectinload(BronzeContract.suggestions),
                    selectinload(BronzeContract.summaries),
                    selectinload(BronzeContract.alerts),
                    selectinload(BronzeContract.processing_runs)
                )
                .where(BronzeContract.contract_id == contract_id)
            )
            return result.scalar_one_or_none()
    
    async def get_contract_chunks_with_embeddings(self, contract_id: str) -> List[SilverChunk]:
        """Get all chunks with embeddings for vector operations"""
        async for db in get_operational_db():
            result = await db.execute(
                select(SilverChunk)
                .where(
                    and_(
                        SilverChunk.contract_id == contract_id,
                        SilverChunk.embedding.is_not(None)
                    )
                )
                .order_by(SilverChunk.chunk_order)
            )
            return result.scalars().all()
    

    
    async def _generate_missing_embeddings_for_contract(self, contract_id: str):
        """Generate embeddings for chunks that don't have them"""
        try:
            from sqlalchemy import select
            from app.database import get_operational_db
            
            async for db in get_operational_db():
                # Get chunks without embeddings
                chunks_result = await db.execute(
                    select(SilverChunk).where(
                        and_(
                            SilverChunk.contract_id == contract_id,
                            SilverChunk.embedding.is_(None)
                        )
                    ).limit(10)  # Limit to 10 chunks to avoid overwhelming
                )
                chunks_without_embeddings = chunks_result.scalars().all()
                
                if not chunks_without_embeddings:
                    self.logger.info(f"No chunks without embeddings found for contract {contract_id}")
                    return
                
                self.logger.info(f"Generating embeddings for {len(chunks_without_embeddings)} chunks")
                
                # Generate embeddings
                for chunk in chunks_without_embeddings:
                    try:
                        embedding_result = await safe_llm_embedding(
                            text=chunk.chunk_text,
                            contract_id=contract_id
                        )
                        
                        if embedding_result and "embedding" in embedding_result:
                            chunk.embedding = embedding_result["embedding"]
                            chunk.embedding_model = f"{embedding_result['provider']}:{embedding_result['model']}"
                            self.logger.info(f"Generated embedding for chunk {chunk.chunk_id}")
                        else:
                            self.logger.error(f"Failed to generate embedding for chunk {chunk.chunk_id}")
                            
                    except Exception as e:
                        self.logger.error(f"Error generating embedding for chunk {chunk.chunk_id}: {e}")
                
                # Commit changes
                await db.commit()
                self.logger.info(f"Successfully generated and stored embeddings for contract {contract_id}")
                break
                
        except Exception as e:
            self.logger.error(f"Error generating missing embeddings: {e}")

    async def _generate_missing_embeddings_for_contract(self, contract_id: str):
        """Generate embeddings for chunks that don't have them"""
        try:
            from sqlalchemy import select, and_
            from app.database import get_operational_db
            from app.models import SilverChunk
            from app.services.llm_factory import llm_factory
            
            async for db in get_operational_db():
                # Find chunks without embeddings for this contract
                chunks_query = select(SilverChunk).where(
                    and_(
                        SilverChunk.contract_id == contract_id,
                        SilverChunk.embedding.is_(None)
                    )
                ).limit(10)  # Limit to prevent overwhelming
                
                result = await db.execute(chunks_query)
                chunks_without_embeddings = result.scalars().all()
                
                if not chunks_without_embeddings:
                    self.logger.info(f"No chunks without embeddings found for contract {contract_id}")
                    return
                
                self.logger.info(f"Generating embeddings for {len(chunks_without_embeddings)} chunks in contract {contract_id}")
                
                # Generate embeddings for each chunk
                for chunk in chunks_without_embeddings:
                    try:
                        embedding_result = await safe_llm_embedding(
                            text=chunk.chunk_text,
                            contract_id=contract_id
                        )
                        
                        if embedding_result and "embedding" in embedding_result:
                            chunk.embedding = embedding_result["embedding"]
                            chunk.embedding_model = f"{embedding_result['provider']}:{embedding_result['model']}"
                            self.logger.debug(f"Generated embedding for chunk {chunk.chunk_id}")
                        else:
                            self.logger.warning(f"Failed to generate embedding for chunk {chunk.chunk_id}")
                            
                    except Exception as e:
                        self.logger.error(f"Error generating embedding for chunk {chunk.chunk_id}: {e}")
                        continue
                
                # Commit the changes
                try:
                    await db.commit()
                    self.logger.info(f"Successfully generated and saved embeddings for contract {contract_id}")
                except Exception as e:
                    self.logger.error(f"Failed to save embeddings: {e}")
                    await db.rollback()
                
                break  # Exit the async for loop
                
        except Exception as e:
            self.logger.error(f"Failed to generate missing embeddings for contract {contract_id}: {e}")

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            import math
            
            # Convert to lists if needed
            if not isinstance(vec1, list):
                vec1 = list(vec1)
            if not isinstance(vec2, list):
                vec2 = list(vec2)
            
            # Ensure vectors are same length
            if len(vec1) != len(vec2):
                self.logger.warning(f"Vector length mismatch: {len(vec1)} vs {len(vec2)}")
                return 0.0
            
            # Ensure all values are floats
            vec1 = [float(x) for x in vec1]
            vec2 = [float(x) for x in vec2]
            
            # Calculate dot product
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            
            # Calculate magnitudes
            magnitude1 = math.sqrt(sum(a * a for a in vec1))
            magnitude2 = math.sqrt(sum(a * a for a in vec2))
            
            if magnitude1 == 0 or magnitude2 == 0:
                self.logger.warning("Zero magnitude vector detected")
                return 0.0
            
            similarity = dot_product / (magnitude1 * magnitude2)
            return max(0.0, min(1.0, similarity))  # Clamp to [0, 1]
            
        except Exception as e:
            self.logger.error(f"Cosine similarity calculation failed: {e}")
            return 0.0
    
    async def get_contract_tokens(self, contract_id: str, token_types: List[str] = None) -> List[Token]:
        """Get tokens for keyword analysis"""
        async for db in get_operational_db():
            query = select(Token).where(Token.contract_id == contract_id)
            
            if token_types:
                query = query.where(Token.token_type.in_(token_types))
            
            result = await db.execute(query.order_by(Token.frequency.desc()))
            return result.scalars().all()
    
    async def get_clause_spans_by_type(self, contract_id: str, clause_types: List[str] = None) -> List[SilverClauseSpan]:
        """Get clause spans, optionally filtered by type"""
        async for db in get_operational_db():
            query = select(SilverClauseSpan).where(SilverClauseSpan.contract_id == contract_id)
            
            if clause_types:
                query = query.where(SilverClauseSpan.clause_type.in_(clause_types))
            
            result = await db.execute(query.order_by(SilverClauseSpan.confidence.desc()))
            return result.scalars().all()
    
    async def get_contract_with_all_data(self, contract_id: str):
        """Get contract with all related data (text, chunks, etc.)"""
        try:
            from sqlalchemy.orm import selectinload
            from app.database import get_operational_db
            from app.models import BronzeContract
            
            async for db in get_operational_db():
                result = await db.execute(
                    select(BronzeContract)
                    .options(
                        selectinload(BronzeContract.text_raw),
                        selectinload(BronzeContract.chunks),
                        selectinload(BronzeContract.clause_spans),
                        selectinload(BronzeContract.scores)
                    )
                    .where(BronzeContract.contract_id == contract_id)
                )
                return result.scalars().first()
                
        except Exception as e:
            self.logger.error(f"Failed to get contract {contract_id}: {e}")
            return None

    async def get_existing_findings(self, contract_id: str, finding_types: List[str] = None) -> List[GoldFinding]:
        """Get existing findings to avoid duplication"""
        async for db in get_operational_db():
            query = select(GoldFinding).where(GoldFinding.contract_id == contract_id)
            
            if finding_types:
                query = query.where(GoldFinding.finding_type.in_(finding_types))
            
            result = await db.execute(query.order_by(GoldFinding.created_at.desc()))
            return result.scalars().all()
    
    async def get_processing_history(self, contract_id: str) -> List[ProcessingRun]:
        """Get processing history for this contract"""
        async for db in get_operational_db():
            result = await db.execute(
                select(ProcessingRun)
                .options(selectinload(ProcessingRun.steps))
                .where(ProcessingRun.contract_id == contract_id)
                .order_by(ProcessingRun.started_at.desc())
            )
            return result.scalars().all()
    
    # =============================================================================
    # DATA WRITING METHODS
    # =============================================================================
    
    async def save_findings(self, contract_id: str, findings: List[Dict[str, Any]]) -> List[str]:
        """Save findings to GoldFinding table"""
        finding_ids = []
        
        async for db in get_operational_db():
            for finding_data in findings:
                try:
                    finding = GoldFinding(
                        contract_id=contract_id,
                        finding_type=finding_data.get('type', 'general'),
                        severity=finding_data.get('severity', 'medium'),
                        title=finding_data.get('title', 'Finding')[:200],
                        description=finding_data.get('description', ''),
                        impact_category=finding_data.get('impact_category'),
                        estimated_impact=finding_data.get('estimated_impact'),
                        confidence=finding_data.get('confidence', 0.5),
                        detection_method=self.agent_name,
                        model_version="2.0.0"
                    )
                    
                    db.add(finding)
                    await db.flush()
                    finding_ids.append(finding.finding_id)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to save finding: {e}")
            
            await db.commit()
        
        return finding_ids
    
    async def save_suggestions(self, contract_id: str, suggestions: List[Dict[str, Any]]) -> List[str]:
        """Save suggestions to GoldSuggestion table"""
        suggestion_ids = []
        
        async for db in get_operational_db():
            for suggestion_data in suggestions:
                try:
                    suggestion = GoldSuggestion(
                        contract_id=contract_id,
                        suggestion_type=suggestion_data.get('type', 'general'),
                        title=suggestion_data.get('title', 'Suggestion')[:200],
                        description=suggestion_data.get('description', ''),
                        suggested_text=suggestion_data.get('suggested_text'),
                        priority=suggestion_data.get('priority', 'medium'),
                        business_rationale=suggestion_data.get('business_rationale'),
                        estimated_benefit=suggestion_data.get('estimated_benefit'),
                        confidence=suggestion_data.get('confidence', 0.5),
                        model_version="2.0.0"
                    )
                    
                    db.add(suggestion)
                    await db.flush()
                    suggestion_ids.append(suggestion.suggestion_id)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to save suggestion: {e}")
            
            await db.commit()
        
        return suggestion_ids
    
    async def save_summary(self, contract_id: str, summary_data: Dict[str, Any]) -> str:
        """Save summary to GoldSummary table"""
        async for db in get_operational_db():
            summary = GoldSummary(
                contract_id=contract_id,
                summary_type=summary_data.get('type', self.agent_name),
                title=summary_data.get('title', f'{self.agent_name} Summary'),
                content=summary_data.get('content', ''),
                key_points=summary_data.get('key_points', []),
                word_count=len(summary_data.get('content', '').split()),
                model_version="2.0.0"
            )
            
            db.add(summary)
            await db.commit()
            await db.refresh(summary)
            
            return summary.summary_id
    
    async def create_alert(self, contract_id: str, alert_data: Dict[str, Any]) -> str:
        """Create alert in Alert table"""
        async for db in get_operational_db():
            alert = Alert(
                contract_id=contract_id,
                alert_type=alert_data.get('type', 'agent_alert'),
                severity=alert_data.get('severity', 'medium'),
                title=alert_data.get('title', f'{self.agent_name} Alert'),
                message=alert_data.get('message', ''),
                payload=alert_data.get('payload', {}),
                channels=alert_data.get('channels', ['system'])
            )
            
            db.add(alert)
            await db.commit()
            await db.refresh(alert)
            
            return alert.alert_id
    
    async def track_llm_call(self, contract_id: str, call_data: Dict[str, Any]) -> str:
        """Track LLM usage in LlmCall table"""
        async for db in get_operational_db():
            llm_call = LlmCall(
                contract_id=contract_id,
                provider=call_data.get('provider', 'openai'),
                model=call_data.get('model', 'gpt-4'),
                call_type=call_data.get('call_type', 'completion'),
                input_tokens=call_data.get('input_tokens', 0),
                output_tokens=call_data.get('output_tokens', 0),
                total_tokens=call_data.get('total_tokens', 0),
                estimated_cost=call_data.get('estimated_cost', 0.0),
                latency_ms=call_data.get('latency_ms', 0),
                success=call_data.get('success', True),
                error_message=call_data.get('error_message'),
                purpose=f"{self.agent_name}_analysis",
                call_metadata=call_data.get('metadata', {})
            )
            
            db.add(llm_call)
            await db.commit()
            await db.refresh(llm_call)
            
            return llm_call.call_id
    
    # =============================================================================
    # LLM INTEGRATION METHODS
    # =============================================================================
    
    async def call_llm_with_tracking(
        self, 
        prompt: str, 
        contract_id: str,
        task_type: LLMTask = LLMTask.ANALYSIS,
        max_tokens: int = 1000,
        temperature: float = 0.1,
        document_content: Optional[str] = None,
        analysis_type: str = "general"
    ) -> str:
        """Call LLM with privacy protection and usage tracking"""
        start_time = datetime.now()
        
        try:
            # Use privacy-safe LLM service
            import asyncio
            result = await asyncio.wait_for(
                privacy_safe_llm.safe_generate_completion(
                    prompt=prompt,
                    task_type=task_type,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    contract_id=contract_id,
                    document_content=document_content,
                    analysis_type=analysis_type
                ),
                timeout=90.0  # 90 second timeout
            )
            
            # Track the call with privacy metadata
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            call_data = {
                'provider': result.get('provider', 'bedrock'),
                'model': result.get('model', 'nova-lite'),
                'call_type': 'completion',
                'input_tokens': result.get('tokens', 0),
                'output_tokens': result.get('tokens', 0),
                'total_tokens': result.get('tokens', 0),
                'latency_ms': int(execution_time),
                'success': True,
                'metadata': {
                    'agent': self.agent_name, 
                    'task_type': task_type.value,
                    'privacy_protected': result.get('privacy_protected', False),
                    'redaction_applied': result.get('redaction_applied', False),
                    'pii_redacted': result.get('pii_redacted', 0)
                }
            }
            
            call_id = await self.track_llm_call(contract_id, call_data)
            
            # Log privacy protection details
            if result.get('privacy_protected'):
                self.logger.info(f"🔒 Privacy-protected LLM call completed:")
                self.logger.info(f"   🛡️ Provider: {result.get('provider')}")
                self.logger.info(f"   📊 PII redacted: {result.get('pii_redacted', 0)}")
                self.logger.info(f"   🔐 Sensitivity: {result.get('sensitivity_level', 'unknown')}")
            
            # Return just the text content for backward compatibility
            # Handle different response formats from LLM service
            if isinstance(result, dict):
                response_text = result.get('content', result.get('text', ''))
            elif isinstance(result, (tuple, list)):
                response_text = result[0] if len(result) > 0 else ''
            else:
                response_text = result
            
            # Ensure we always return a string
            return str(response_text) if response_text is not None else ''
            
        except Exception as e:
            # Track failed call
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            call_data = {
                'call_type': 'completion',
                'latency_ms': int(execution_time),
                'success': False,
                'error_message': str(e),
                'metadata': {'agent': self.agent_name, 'task_type': task_type.value}
            }
            
            try:
                await self.track_llm_call(contract_id, call_data)
            except:
                pass  # Don't fail if tracking fails
            
            # Return a fallback response instead of raising
            self.logger.warning(f"Privacy-safe LLM call failed for {self.agent_name}: {e}")
            # Return just the fallback text content for backward compatibility
            return f'LLM analysis temporarily unavailable. Error: {str(e)[:100]}'
    
    # =============================================================================
    # VECTOR SEARCH METHODS
    # =============================================================================
    
    async def semantic_search_chunks(
        self, 
        query: str, 
        contract_id: str = None, 
        limit: int = 5,
        similarity_threshold: float = 0.01,
        user_id: str = None
    ) -> List[Tuple[Any, float]]:
        """Perform semantic search on chunks using Python-based cosine similarity"""
        try:
            # Generate query embedding with privacy protection
            import asyncio
            embedding_result = await asyncio.wait_for(
                privacy_safe_llm.safe_generate_embedding(
                    text=query,
                    contract_id=contract_id
                ),
                timeout=15.0  # 15 second timeout for embedding
            )
            query_embedding = embedding_result["embedding"]
            
            async for db in get_operational_db():
                # Get chunks with embeddings using SQLAlchemy ORM
                from sqlalchemy import select, and_
                from app.models import SilverChunk
                
                if contract_id:
                    # Search within specific contract
                    query_stmt = select(SilverChunk).where(
                        and_(
                            SilverChunk.contract_id == contract_id,
                            SilverChunk.embedding.is_not(None)
                        )
                    )
                else:
                    # Search across all user's chunks
                    from app.models import BronzeContract
                    query_stmt = select(SilverChunk).join(BronzeContract).where(
                        and_(
                            BronzeContract.owner_user_id == user_id if user_id else True,
                            SilverChunk.embedding.is_not(None)
                        )
                    ).limit(1000)  # Limit to prevent memory issues
                
                result = await db.execute(query_stmt)
                chunks = result.scalars().all()
                
                if not chunks:
                    self.logger.warning(f"No chunks with embeddings found for contract {contract_id}")
                    return []
                
                # Calculate similarities using Python
                chunks_with_similarity = []
                self.logger.info(f"Processing {len(chunks)} chunks for similarity calculation")
                
                for i, chunk in enumerate(chunks):
                    try:
                        # Parse embedding from JSON if needed
                        chunk_embedding = chunk.embedding
                        if isinstance(chunk_embedding, str):
                            chunk_embedding = json.loads(chunk_embedding)
                        elif not isinstance(chunk_embedding, list):
                            chunk_embedding = list(chunk_embedding)
                        
                        # Calculate cosine similarity
                        similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                        
                        # Log similarity for debugging
                        if i < 5:  # Log first 5 chunks
                            self.logger.info(f"Chunk {i+1} similarity: {similarity:.4f} (threshold: {similarity_threshold})")
                            self.logger.info(f"  Text preview: {chunk.chunk_text[:100]}...")
                        
                        if similarity >= similarity_threshold:
                            chunks_with_similarity.append((chunk, similarity))
                            self.logger.info(f"✅ Chunk {chunk.chunk_id} added with similarity {similarity:.4f}")
                            
                    except Exception as e:
                        self.logger.warning(f"Error processing chunk {chunk.chunk_id}: {e}")
                        continue
                
                self.logger.info(f"Found {len(chunks_with_similarity)} chunks above threshold {similarity_threshold}")
                
                # Sort by similarity and return top results
                chunks_with_similarity.sort(key=lambda x: x[1], reverse=True)
                return chunks_with_similarity[:limit]
                
        except Exception as e:
            self.logger.error(f"Semantic search failed: {e}")
            import traceback
            self.logger.error(f"Full error trace: {traceback.format_exc()}")
            # Return empty results instead of failing
            return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            import math
            
            # Ensure vectors are the same length
            if len(vec1) != len(vec2):
                self.logger.warning(f"Vector length mismatch: {len(vec1)} vs {len(vec2)}")
                return 0.0
            
            # Calculate dot product
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            
            # Calculate magnitudes
            magnitude1 = math.sqrt(sum(a * a for a in vec1))
            magnitude2 = math.sqrt(sum(a * a for a in vec2))
            
            # Avoid division by zero
            if magnitude1 == 0.0 or magnitude2 == 0.0:
                return 0.0
            
            # Calculate cosine similarity
            similarity = dot_product / (magnitude1 * magnitude2)
            
            # Ensure result is between -1 and 1
            return max(-1.0, min(1.0, similarity))
            
        except Exception as e:
            self.logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    # =============================================================================
    # HELPER METHODS - AWS Bedrock AgentCore Compatible
    # =============================================================================
    
    def _validate_context(self, context: AgentContext):
        """Validate agent context"""
        if not context.contract_id:
            raise ValueError("contract_id is required")
        if not context.user_id:
            raise ValueError("user_id is required")
    
    def _get_cache_key(self, context: AgentContext) -> str:
        """Generate cache key for context"""
        key_parts = [
            self.agent_name,
            context.contract_id,
            context.query or "no_query",
            context.document_type or "no_type"
        ]
        return "_".join(key_parts)
    
    def _get_cached_result(self, context: AgentContext) -> Optional[AgentResult]:
        """Get cached result if available"""
        cache_key = self._get_cache_key(context)
        return self._cache.get(cache_key)
    
    def clear_cache(self):
        """Clear all cached results"""
        self._cache.clear()
        self.logger.info(f"Cleared cache for {self.agent_name}")
    
    def _cache_result(self, context: AgentContext, result: AgentResult):
        """Cache successful result"""
        cache_key = self._get_cache_key(context)
        self._cache[cache_key] = result
        
        # Simple cache size management
        if len(self._cache) > 100:
            # Remove oldest entries
            keys_to_remove = list(self._cache.keys())[:20]
            for key in keys_to_remove:
                del self._cache[key]
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def _create_error_result(
        self, 
        context: AgentContext, 
        status: AgentStatus, 
        error_message: str,
        execution_time: float,
        memory_start: float
    ) -> AgentResult:
        """Create standardized error result"""
        return AgentResult(
            agent_name=self.agent_name,
            agent_version=self.version,
            status=status,
            confidence=0.0,
            findings=[{
                "type": "error",
                "title": f"{self.agent_name} Error",
                "severity": "high",
                "confidence": 1.0,
                "description": error_message
            }],
            recommendations=["Manual review required due to agent error"],
            execution_time_ms=execution_time,
            memory_usage_mb=memory_start,
            error_message=error_message,
            session_id=context.session_id,
            trace_id=context.run_id
        )
    
    def _create_failure_result(self, error_message: str) -> AgentResult:
        """Create failure result with minimal information"""
        return AgentResult(
            agent_name=self.agent_name,
            agent_version=self.version,
            status=AgentStatus.FAILED,
            confidence=0.0,
            findings=[{
                "type": "error",
                "title": "Processing Failed",
                "severity": "high",
                "confidence": 1.0,
                "description": error_message
            }],
            recommendations=["Please try again or contact support"],
            execution_time_ms=0.0,
            memory_usage_mb=0.0,
            error_message=error_message,
            data_sources=[]
        )
    
    async def call_llm_with_tracking(
        self, 
        prompt: str, 
        contract_id: str,
        task_type: LLMTask = LLMTask.ANALYSIS,
        max_tokens: int = 1000,
        temperature: float = 0.1,
        document_content: Optional[str] = None,
        analysis_type: str = "general"
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Privacy-safe LLM call with automatic tracking
        Returns (result_list, call_id) for backward compatibility
        """
        try:
            result = await safe_llm_completion(
                prompt=prompt,
                task_type=task_type,
                max_tokens=max_tokens,
                temperature=temperature,
                contract_id=contract_id,
                document_content=document_content,
                analysis_type=analysis_type
            )
            
            # Convert to expected format for backward compatibility
            result_list = [{
                "content": result.get("content", ""),
                "provider": result.get("provider", "unknown"),
                "model": result.get("model", "unknown"),
                "privacy_protected": result.get("privacy_protected", True),
                "pii_redacted": result.get("pii_redacted", 0),
                "sensitivity_level": result.get("sensitivity_level", "unknown")
            }]
            
            # Generate a call ID for tracking
            call_id = f"call_{contract_id}_{int(datetime.now().timestamp())}"
            
            return result_list, call_id
            
        except Exception as e:
            self.logger.error(f"Privacy-safe LLM call failed: {e}")
            # Return fallback response
            fallback_result = [{
                "content": f"Analysis temporarily unavailable: {str(e)[:100]}",
                "provider": "fallback",
                "model": "fallback",
                "privacy_protected": True,
                "error": str(e)
            }]
            return fallback_result, "fallback_call_id"

    def create_result(
        self, 
        status: AgentStatus = AgentStatus.COMPLETED,
        confidence: float = 0.8,
        findings: List[Dict[str, Any]] = None,
        recommendations: List[str] = None,
        data_sources: List[str] = None,
        execution_time_ms: float = 0.0,
        memory_usage_mb: float = 0.0,
        llm_calls: int = 0,
        error_message: str = None,
        session_id: str = None,
        trace_id: str = None
    ) -> AgentResult:
        """Create standardized agent result - AWS Bedrock AgentCore compatible"""
        return AgentResult(
            agent_name=self.agent_name,
            agent_version=self.version,
            status=status,
            confidence=confidence,
            findings=findings or [],
            recommendations=recommendations or [],
            execution_time_ms=execution_time_ms,
            memory_usage_mb=memory_usage_mb,
            llm_calls=llm_calls,
            data_sources=data_sources or [],
            error_message=error_message,
            session_id=session_id,
            trace_id=trace_id
        )
