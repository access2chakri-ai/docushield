"""
Base Agent Class
Provides common functionality for all DocuShield agents with full TiDB integration
"""
import json
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, and_, or_
from sqlalchemy.orm import selectinload

from app.database import get_operational_db, get_sandbox_db, get_analytics_db
from app.models import (
    BronzeContract, BronzeContractTextRaw, SilverChunk, SilverClauseSpan, Token,
    GoldContractScore, GoldFinding, GoldSuggestion, GoldSummary, Alert,
    ProcessingRun, ProcessingStep, LlmCall, User
)
from app.services.llm_factory import llm_factory, LLMTask
from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class AgentContext:
    """Context passed between agents"""
    contract_id: str
    user_id: str
    query: Optional[str] = None
    previous_results: Dict[str, Any] = None
    metadata: Dict[str, Any] = None

@dataclass
class AgentResult:
    """Standardized agent result format"""
    agent_name: str
    success: bool
    confidence: float
    findings: List[Dict[str, Any]]
    recommendations: List[str]
    data_used: Dict[str, Any]  # Track which tables/data were used
    execution_time_ms: float
    llm_calls: int = 0
    error_message: Optional[str] = None

class BaseAgent(ABC):
    """
    Base class for all DocuShield agents
    Provides common TiDB operations and LLM integration
    """
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"agent.{agent_name}")
    
    @abstractmethod
    async def analyze(self, context: AgentContext) -> AgentResult:
        """Main analysis method - must be implemented by subclasses"""
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
        temperature: float = 0.1
    ) -> Tuple[Dict[str, Any], str]:
        """Call LLM and track usage"""
        start_time = datetime.now()
        
        try:
            # Add timeout and error handling for LLM calls
            import asyncio
            result = await asyncio.wait_for(
                llm_factory.generate_completion(
                    prompt=prompt,
                    task_type=task_type,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    contract_id=contract_id
                ),
                timeout=30.0  # 30 second timeout
            )
            
            # Track the call
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            call_data = {
                'provider': result.get('provider', 'openai'),
                'model': result.get('model', 'gpt-4'),
                'call_type': 'completion',
                'input_tokens': result.get('usage', {}).get('prompt_tokens', 0),
                'output_tokens': result.get('usage', {}).get('completion_tokens', 0),
                'total_tokens': result.get('usage', {}).get('total_tokens', 0),
                'latency_ms': int(execution_time),
                'success': True,
                'metadata': {'agent': self.agent_name, 'task_type': task_type.value}
            }
            
            call_id = await self.track_llm_call(contract_id, call_data)
            
            return result, call_id
            
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
            self.logger.warning(f"LLM call failed for {self.agent_name}: {e}")
            fallback_result = {
                'content': f'LLM analysis temporarily unavailable. Error: {str(e)[:100]}',
                'provider': 'fallback',
                'model': 'fallback',
                'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
            }
            return fallback_result, "fallback_call_id"
    
    # =============================================================================
    # VECTOR SEARCH METHODS
    # =============================================================================
    
    async def semantic_search_chunks(
        self, 
        query: str, 
        contract_id: str = None, 
        limit: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[Tuple[SilverChunk, float]]:
        """Perform semantic search on chunks using TiDB vector search"""
        try:
            # Generate query embedding with timeout
            import asyncio
            embedding_result = await asyncio.wait_for(
                llm_factory.generate_embedding(text=query),
                timeout=15.0  # 15 second timeout for embedding
            )
            query_embedding = embedding_result["embedding"]
            
            async for db in get_operational_db():
                # Build vector search query
                if contract_id:
                    # Search within specific contract
                    vector_search_sql = text("""
                        SELECT chunk_id, chunk_text, chunk_order, start_offset, end_offset,
                               VEC_COSINE_DISTANCE(JSON_EXTRACT(embedding, '$'), :query_embedding) as similarity
                        FROM silver_chunks 
                        WHERE contract_id = :contract_id 
                        AND embedding IS NOT NULL
                        AND VEC_COSINE_DISTANCE(JSON_EXTRACT(embedding, '$'), :query_embedding) >= :threshold
                        ORDER BY similarity DESC
                        LIMIT :limit
                    """)
                    
                    result = await db.execute(
                        vector_search_sql,
                        {
                            "contract_id": contract_id,
                            "query_embedding": json.dumps(query_embedding),
                            "threshold": similarity_threshold,
                            "limit": limit
                        }
                    )
                else:
                    # Search across all chunks
                    vector_search_sql = text("""
                        SELECT chunk_id, chunk_text, chunk_order, start_offset, end_offset, contract_id,
                               VEC_COSINE_DISTANCE(JSON_EXTRACT(embedding, '$'), :query_embedding) as similarity
                        FROM silver_chunks 
                        WHERE embedding IS NOT NULL
                        AND VEC_COSINE_DISTANCE(JSON_EXTRACT(embedding, '$'), :query_embedding) >= :threshold
                        ORDER BY similarity DESC
                        LIMIT :limit
                    """)
                    
                    result = await db.execute(
                        vector_search_sql,
                        {
                            "query_embedding": json.dumps(query_embedding),
                            "threshold": similarity_threshold,
                            "limit": limit
                        }
                    )
                
                # Convert results to SilverChunk objects with similarity scores
                chunks_with_similarity = []
                for row in result:
                    # Create a SilverChunk-like object from the row data
                    chunk_data = {
                        'chunk_id': row.chunk_id,
                        'chunk_text': row.chunk_text,
                        'chunk_order': row.chunk_order,
                        'start_offset': row.start_offset,
                        'end_offset': row.end_offset,
                        'contract_id': getattr(row, 'contract_id', contract_id)
                    }
                    
                    chunks_with_similarity.append((chunk_data, float(row.similarity)))
                
                return chunks_with_similarity
                
        except Exception as e:
            self.logger.error(f"Semantic search failed: {e}")
            # Return empty results instead of failing
            return []
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def create_result(
        self, 
        success: bool = True,
        confidence: float = 0.8,
        findings: List[Dict[str, Any]] = None,
        recommendations: List[str] = None,
        data_used: Dict[str, Any] = None,
        execution_time_ms: float = 0.0,
        llm_calls: int = 0,
        error_message: str = None
    ) -> AgentResult:
        """Create standardized agent result"""
        return AgentResult(
            agent_name=self.agent_name,
            success=success,
            confidence=confidence,
            findings=findings or [],
            recommendations=recommendations or [],
            data_used=data_used or {},
            execution_time_ms=execution_time_ms,
            llm_calls=llm_calls,
            error_message=error_message
        )
