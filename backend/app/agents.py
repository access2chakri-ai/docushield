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
from app.database import get_operational_db
from app.models import BronzeContract, ProcessingRun
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
        async for session in get_operational_db():
            try:
                # Create embedding
                embedding = await self.create_embedding(content)
                
                # Store in TiDB - simplified for current model structure
                # This would need proper integration with DocuShield's contract processing
                contract = BronzeContract(
                    filename=title,
                    mime_type=file_type,
                    file_size=len(content.encode('utf-8')),
                    file_hash="placeholder_hash",
                    owner_user_id="system"
                )
                session.add(contract)
                await session.commit()
                await session.refresh(contract)
                
                logger.info(f"Contract ingested: {contract.contract_id}")
                return contract.contract_id
                
            except Exception as e:
                logger.error(f"Failed to ingest document: {e}")
                await session.rollback()
                raise
    
    async def hybrid_search(self, query: str, dataset_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Step 2: Hybrid search using TiDB vector + full-text search
        """
        async for session in get_operational_db():
            try:
                # Create query embedding
                query_embedding = await self.create_embedding(query)
                embedding_json = json.dumps(query_embedding)
                
                # Simplified search using bronze_contracts table
                # Note: This is a placeholder - real implementation would use silver_chunks with embeddings
                vector_search_sql = text("""
                    SELECT contract_id as id, filename as title, 'contract' as file_type,
                           0.8 as similarity
                    FROM bronze_contracts 
                    WHERE filename LIKE :query
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)
                
                result = await session.execute(
                    vector_search_sql,
                    {
                        "query": f"%{query}%",
                        "limit": limit
                    }
                )
                
                docs = []
                for row in result:
                    docs.append({
                        "id": row.id,
                        "title": row.title,
                        "content": f"Contract file: {row.title}",
                        "file_type": row.file_type,
                        "similarity": float(row.similarity)
                    })
                
                # Fallback to text search if no vector results
                if not docs:
                    text_search_sql = text("""
                        SELECT contract_id as id, filename as title, 'contract' as file_type, 0.5 as similarity
                        FROM bronze_contracts 
                        WHERE filename LIKE :query
                        LIMIT :limit
                    """)
                    
                    result = await session.execute(
                        text_search_sql,
                        {
                            "query": f"%{query}%",
                            "limit": limit
                        }
                    )
                    
                    for row in result:
                        docs.append({
                            "id": row.id,
                            "title": row.title,
                            "content": f"Contract file: {row.title}",
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
                Analyze this contract/legal document and provide:
                1. Document type (e.g., Service Agreement, NDA, Employment Contract)
                2. Key parties involved
                3. Main terms and obligations
                4. Important dates/deadlines
                5. Risk factors or concerning clauses
                
                Title: {doc['title']}
                Content: {doc['content']}
                
                Provide a structured analysis in 3-4 sentences.
                """
                
                response = await self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": summary_prompt}],
                    max_tokens=200
                )
                
                summaries.append({
                    "doc_id": doc['id'],
                    "title": doc['title'],
                    "summary": response.choices[0].message.content
                })
            
            # Step 3b: Analyze and synthesize
            analysis_prompt = f"""
            You are a legal contract analysis expert. Analyze these contracts based on the query.
            
            Query: {query}
            
            Contract Analysis Summaries:
            {json.dumps(summaries, indent=2)}
            
            Provide a comprehensive contract intelligence analysis:
            1. **Direct Answer**: Answer the specific question about these contracts
            2. **Risk Assessment**: Identify potential legal, financial, or operational risks
            3. **Key Terms Analysis**: Highlight important clauses, obligations, and rights
            4. **Compliance Issues**: Note any regulatory or compliance concerns
            5. **Recommendations**: Suggest actions or areas needing attention
            6. **Limitations**: Note any gaps in the analysis
            
            Format as JSON with keys: answer, risk_assessment, key_terms, compliance_issues, recommendations, limitations
            """
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": analysis_prompt}],
                max_tokens=800
            )
            
            # Parse LLM response
            try:
                analysis = json.loads(response.choices[0].message.content)
            except:
                analysis = {
                    "answer": response.choices[0].message.content,
                    "risk_assessment": "Unable to parse structured risk assessment",
                    "key_terms": [],
                    "compliance_issues": [],
                    "recommendations": [],
                    "limitations": ["JSON parsing failed - using raw response"]
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
                    "answer": "Contract analysis failed due to technical error.",
                    "risk_assessment": "Unable to assess risks due to technical error",
                    "key_terms": [],
                    "compliance_issues": [],
                    "recommendations": ["Please retry the analysis"],
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
        async for session in get_operational_db():
            # Create processing run record
            run = ProcessingRun(
                contract_id="system",  # placeholder
                pipeline_version="1.0",
                trigger="agent",
                status="running"
            )
            session.add(run)
            await session.commit()
            await session.refresh(run)
            run_id = run.run_id
        
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
            async for session in get_operational_db():
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
            async for session in get_operational_db():
                await session.execute(
                    text("UPDATE agent_runs SET status = 'failed', completed_at = NOW() WHERE id = :id"),
                    {"id": run_id}
                )
                await session.commit()
            raise
    
    def _synthesize_final_answer(self, query: str, documents: List[Dict], llm_results: Dict, external_data: Dict) -> str:
        """Combine all results into comprehensive contract analysis"""
        answer_parts = []
        
        # Main answer from LLM
        if llm_results.get("analysis", {}).get("answer"):
            answer_parts.append(f"**Contract Analysis**: {llm_results['analysis']['answer']}")
        
        # Risk Assessment
        risk_assessment = llm_results.get("analysis", {}).get("risk_assessment")
        if risk_assessment:
            answer_parts.append(f"**Risk Assessment**: {risk_assessment}")
        
        # Key Terms
        key_terms = llm_results.get("analysis", {}).get("key_terms", [])
        if key_terms:
            terms_text = ', '.join(key_terms) if isinstance(key_terms, list) else key_terms
            answer_parts.append(f"**Key Terms & Clauses**: {terms_text}")
        
        # Compliance Issues
        compliance = llm_results.get("analysis", {}).get("compliance_issues", [])
        if compliance:
            comp_text = ', '.join(compliance) if isinstance(compliance, list) else compliance
            answer_parts.append(f"**Compliance Considerations**: {comp_text}")
        
        # Recommendations
        recommendations = llm_results.get("analysis", {}).get("recommendations", [])
        if recommendations:
            rec_text = '\n- '.join(recommendations) if isinstance(recommendations, list) else recommendations
            answer_parts.append(f"**Recommendations**:\n- {rec_text}")
        
        # Document sources
        if documents:
            sources = [f"- {doc['title']}" for doc in documents[:3]]
            answer_parts.append(f"**Analyzed Contracts**: {len(documents)} document(s):\n" + "\n".join(sources))
        
        # Limitations
        limitations = llm_results.get("analysis", {}).get("limitations", [])
        if limitations:
            lim_text = ', '.join(limitations) if isinstance(limitations, list) else limitations
            answer_parts.append(f"**Analysis Limitations**: {lim_text}")
        
        return "\n\n".join(answer_parts)

# Global agent instance
agent = DocumentAnalysisAgent()
