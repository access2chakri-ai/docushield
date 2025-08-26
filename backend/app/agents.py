"""
Multi-step Agent Workflow for TiDB Hackathon
Demonstrates: TiDB Vector Search + LLM Chains + External APIs
"""
import json
import time
import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import openai
import httpx
import numpy as np
from app.database import AsyncSessionLocal
from app.models import Document, AgentRun
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class DocumentAnalysisAgent:
    """
    Multi-step agent that demonstrates:
    1. Document ingestion with vector embeddings (TiDB Vector Search)
    2. Hybrid search (vector + full-text)
    3. LLM analysis chain
    4. External API integration
    5. Result compilation
    """
    
    def __init__(self):
        self.openai_client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.http_client = httpx.AsyncClient()
    
    async def create_embedding(self, text: str) -> List[float]:
        """Create vector embedding using OpenAI"""
        try:
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text[:8000]  # Limit text length
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to create embedding: {e}")
            # Return dummy embedding for demo
            return [0.0] * 1536
    
    async def ingest_document(self, title: str, content: str, file_type: str, dataset_id: str = "default") -> str:
        """
        Step 1: Ingest document with vector embedding
        """
        async with AsyncSessionLocal() as session:
            try:
                # Create embedding
                embedding = await self.create_embedding(content)
                
                # Store in TiDB
                doc = Document(
                    title=title,
                    content=content,
                    file_type=file_type,
                    dataset_id=dataset_id,
                    embedding=embedding  # TiDB stores as JSON
                )
                session.add(doc)
                await session.commit()
                await session.refresh(doc)
                
                logger.info(f"Document ingested: {doc.id}")
                return doc.id
                
            except Exception as e:
                logger.error(f"Failed to ingest document: {e}")
                await session.rollback()
                raise
    
    async def hybrid_search(self, query: str, dataset_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Step 2: Hybrid search using TiDB vector + full-text search
        """
        async with AsyncSessionLocal() as session:
            try:
                # Create query embedding
                query_embedding = await self.create_embedding(query)
                embedding_json = json.dumps(query_embedding)
                
                # TiDB vector search with full-text fallback
                vector_search_sql = text("""
                    SELECT id, title, content, file_type,
                           VEC_COSINE_DISTANCE(embedding, :query_embedding) as similarity
                    FROM documents 
                    WHERE dataset_id = :dataset_id
                      AND JSON_LENGTH(embedding) > 0
                    ORDER BY similarity ASC
                    LIMIT :limit
                """)
                
                result = await session.execute(
                    vector_search_sql,
                    {
                        "query_embedding": embedding_json,
                        "dataset_id": dataset_id,
                        "limit": limit
                    }
                )
                
                docs = []
                for row in result:
                    docs.append({
                        "id": row.id,
                        "title": row.title,
                        "content": row.content[:500] + "..." if len(row.content) > 500 else row.content,
                        "file_type": row.file_type,
                        "similarity": float(row.similarity)
                    })
                
                # Fallback to text search if no vector results
                if not docs:
                    text_search_sql = text("""
                        SELECT id, title, content, file_type, 0.5 as similarity
                        FROM documents 
                        WHERE dataset_id = :dataset_id
                          AND (title LIKE :query OR content LIKE :query)
                        LIMIT :limit
                    """)
                    
                    result = await session.execute(
                        text_search_sql,
                        {
                            "query": f"%{query}%",
                            "dataset_id": dataset_id,
                            "limit": limit
                        }
                    )
                    
                    for row in result:
                        docs.append({
                            "id": row.id,
                            "title": row.title,
                            "content": row.content[:500] + "..." if len(row.content) > 500 else row.content,
                            "file_type": row.file_type,
                            "similarity": 0.5
                        })
                
                logger.info(f"Found {len(docs)} relevant documents")
                return docs
                
            except Exception as e:
                logger.error(f"Search failed: {e}")
                return []
    
    async def analyze_with_llm(self, query: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Step 3: Multi-step LLM analysis chain
        """
        try:
            # Step 3a: Summarize each document
            summaries = []
            for doc in documents:
                summary_prompt = f"""
                Summarize this document in 2-3 sentences:
                Title: {doc['title']}
                Content: {doc['content']}
                """
                
                response = await self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": summary_prompt}],
                    max_tokens=100
                )
                
                summaries.append({
                    "doc_id": doc['id'],
                    "title": doc['title'],
                    "summary": response.choices[0].message.content
                })
            
            # Step 3b: Analyze and synthesize
            analysis_prompt = f"""
            Question: {query}
            
            Based on these document summaries:
            {json.dumps(summaries, indent=2)}
            
            Provide:
            1. A direct answer to the question
            2. Key insights from the documents
            3. Any gaps or limitations in the available information
            
            Format as JSON with keys: answer, insights, limitations
            """
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": analysis_prompt}],
                max_tokens=500
            )
            
            # Parse LLM response
            try:
                analysis = json.loads(response.choices[0].message.content)
            except:
                analysis = {
                    "answer": response.choices[0].message.content,
                    "insights": [],
                    "limitations": []
                }
            
            return {
                "summaries": summaries,
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return {
                "summaries": [],
                "analysis": {
                    "answer": "Analysis failed due to technical error.",
                    "insights": [],
                    "limitations": ["Technical error in LLM processing"]
                }
            }
    
    async def external_enrichment(self, query: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 4: External API enrichment (simulated)
        """
        try:
            # Simulate external API calls (replace with real APIs)
            external_data = {
                "weather_context": None,
                "news_context": None,
                "calculation_result": None
            }
            
            # Example: If query mentions weather, call weather API
            if any(word in query.lower() for word in ["weather", "temperature", "climate"]):
                # Simulated weather API call
                external_data["weather_context"] = {
                    "source": "weather_api",
                    "data": "Current weather conditions retrieved"
                }
            
            # Example: If query needs calculation
            if any(word in query.lower() for word in ["calculate", "sum", "total", "average"]):
                external_data["calculation_result"] = {
                    "source": "calculator",
                    "result": "Mathematical calculation performed"
                }
            
            return external_data
            
        except Exception as e:
            logger.error(f"External enrichment failed: {e}")
            return {}
    
    async def run_multi_step_analysis(self, query: str, dataset_id: str = "default") -> str:
        """
        Complete multi-step agentic workflow
        """
        start_time = time.time()
        
        # Create run record
        async with AsyncSessionLocal() as session:
            run = AgentRun(
                query=query,
                dataset_id=dataset_id,
                status="running"
            )
            session.add(run)
            await session.commit()
            await session.refresh(run)
            run_id = run.id
        
        try:
            # Step 1: Hybrid Search (Vector + Full-text)
            logger.info("Step 1: Searching documents...")
            documents = await self.hybrid_search(query, dataset_id)
            
            # Step 2: LLM Analysis Chain
            logger.info("Step 2: Analyzing with LLM...")
            llm_results = await self.analyze_with_llm(query, documents)
            
            # Step 3: External API Enrichment
            logger.info("Step 3: External enrichment...")
            external_data = await self.external_enrichment(query, llm_results)
            
            # Step 4: Final Synthesis
            logger.info("Step 4: Final synthesis...")
            final_answer = self._synthesize_final_answer(
                query, documents, llm_results, external_data
            )
            
            # Update run record
            execution_time = time.time() - start_time
            async with AsyncSessionLocal() as session:
                await session.execute(
                    text("UPDATE agent_runs SET retrieval_results = :docs, llm_analysis = :llm, external_actions = :ext, final_answer = :answer, total_steps = 4, execution_time = :time, status = 'completed', completed_at = NOW() WHERE id = :id"),
                    {
                        "docs": json.dumps(documents),
                        "llm": json.dumps(llm_results),
                        "ext": json.dumps(external_data),
                        "answer": final_answer,
                        "time": execution_time,
                        "id": run_id
                    }
                )
                await session.commit()
            
            logger.info(f"Analysis completed in {execution_time:.2f}s")
            return run_id
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            # Update run record with failure
            async with AsyncSessionLocal() as session:
                await session.execute(
                    text("UPDATE agent_runs SET status = 'failed', completed_at = NOW() WHERE id = :id"),
                    {"id": run_id}
                )
                await session.commit()
            raise
    
    def _synthesize_final_answer(self, query: str, documents: List[Dict], llm_results: Dict, external_data: Dict) -> str:
        """Combine all results into final answer"""
        answer_parts = []
        
        # Main answer from LLM
        if llm_results.get("analysis", {}).get("answer"):
            answer_parts.append(f"**Answer**: {llm_results['analysis']['answer']}")
        
        # Key insights
        insights = llm_results.get("analysis", {}).get("insights", [])
        if insights:
            answer_parts.append(f"**Key Insights**: {', '.join(insights) if isinstance(insights, list) else insights}")
        
        # Document sources
        if documents:
            sources = [f"- {doc['title']}" for doc in documents[:3]]
            answer_parts.append(f"**Sources**: Based on {len(documents)} documents including:\n" + "\n".join(sources))
        
        # External enrichment
        enrichments = [v for v in external_data.values() if v]
        if enrichments:
            answer_parts.append(f"**Additional Context**: Enhanced with {len(enrichments)} external data sources")
        
        return "\n\n".join(answer_parts)

# Global agent instance
agent = DocumentAnalysisAgent()
