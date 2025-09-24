"""
Search Agent - Specialized for document discovery and retrieval
Utilizes SilverChunk embeddings, Token indexing, and full-text search
"""
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from sqlalchemy import text, select, and_, or_
from sqlalchemy.orm import selectinload

from .base_agent import BaseAgent, AgentContext, AgentResult
from app.database import get_operational_db
from app.models import BronzeContract, SilverChunk, Token, SilverClauseSpan
from app.services.llm_factory import llm_factory, LLMTask

logger = logging.getLogger(__name__)

class SearchAgent(BaseAgent):
    """
    Specialized agent for intelligent document search and retrieval
    Uses TiDB Vector Search, full-text search, and token analysis
    """
    
    def __init__(self):
        super().__init__("search_agent")
        
        # Search type weights for hybrid scoring
        self.search_weights = {
            "semantic": 0.4,    # Vector similarity
            "keyword": 0.3,     # Token matching
            "clause": 0.2,      # Clause relevance
            "metadata": 0.1     # File metadata
        }
    
    async def analyze(self, context: AgentContext) -> AgentResult:
        """
        Main search analysis - finds relevant documents and content
        """
        start_time = datetime.now()
        
        try:
            query = context.query
            if not query:
                return self.create_result(
                    success=False,
                    error_message="No search query provided"
                )
            
            # Multi-modal search approach
            search_results = await self.hybrid_search(
                query=query,
                user_id=context.user_id,
                contract_id=context.contract_id,
                limit=10
            )
            
            # Analyze search patterns and generate insights
            search_insights = await self.analyze_search_patterns(query, search_results)
            
            # Generate search recommendations
            recommendations = await self.generate_search_recommendations(query, search_results)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            findings = [{
                "type": "search_results",
                "title": f"Found {len(search_results)} relevant documents",
                "description": f"Hybrid search for '{query}' returned {len(search_results)} results",
                "severity": "info",
                "confidence": search_insights.get("overall_confidence", 0.8),
                "results": search_results,
                "search_insights": search_insights
            }]
            
            return self.create_result(
                success=True,
                confidence=search_insights.get("overall_confidence", 0.8),
                findings=findings,
                recommendations=recommendations,
                data_used={
                    "silver_chunks": search_insights.get("chunks_searched", 0),
                    "tokens_analyzed": search_insights.get("tokens_analyzed", 0),
                    "clauses_matched": search_insights.get("clauses_matched", 0)
                },
                execution_time_ms=execution_time,
                llm_calls=1  # For search pattern analysis
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"Search agent analysis failed: {e}")
            
            return self.create_result(
                success=False,
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    async def hybrid_search(
        self, 
        query: str, 
        user_id: str,
        contract_id: str = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining semantic, keyword, clause, and metadata search
        """
        try:
            # 1. Semantic search using vector embeddings
            semantic_results = await self.semantic_search_with_scores(query, contract_id, limit)
            
            # 2. Keyword search using token analysis
            keyword_results = await self.keyword_search_with_tokens(query, user_id, contract_id, limit)
            
            # 3. Clause-based search
            clause_results = await self.clause_search(query, user_id, contract_id, limit)
            
            # 4. Metadata search
            metadata_results = await self.metadata_search(query, user_id, contract_id, limit)
            
            # 5. Combine and rank results
            combined_results = await self.combine_search_results([
                ("semantic", semantic_results),
                ("keyword", keyword_results), 
                ("clause", clause_results),
                ("metadata", metadata_results)
            ])
            
            return combined_results[:limit]
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []
    
    async def semantic_search_with_scores(
        self, 
        query: str, 
        contract_id: str = None, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Semantic search using TiDB vector embeddings"""
        try:
            chunks_with_similarity = await self.semantic_search_chunks(
                query=query,
                contract_id=contract_id,
                limit=limit,
                similarity_threshold=0.5
            )
            
            results = []
            for chunk_data, similarity in chunks_with_similarity:
                results.append({
                    "contract_id": chunk_data["contract_id"],
                    "chunk_id": chunk_data["chunk_id"],
                    "content": chunk_data["chunk_text"],
                    "score": similarity,
                    "match_type": "semantic",
                    "start_offset": chunk_data["start_offset"],
                    "end_offset": chunk_data["end_offset"]
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    async def semantic_search_chunks(
        self,
        query: str,
        contract_id: str = None,
        limit: int = 10,
        similarity_threshold: float = 0.5
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Perform TiDB vector search on chunk embeddings
        Returns list of (chunk_data, similarity_score) tuples
        """
        try:
            # Generate query embedding
            embedding_result = await llm_factory.generate_embedding(
                text=query,
                task_type=LLMTask.EMBEDDING
            )
            query_embedding = embedding_result["embedding"]
            
            async for db in get_operational_db():
                # Build base query
                base_query = select(
                    SilverChunk.chunk_id,
                    SilverChunk.contract_id,
                    SilverChunk.chunk_text,
                    SilverChunk.start_offset,
                    SilverChunk.end_offset,
                    SilverChunk.chunk_order,
                    SilverChunk.embedding
                ).where(
                    SilverChunk.embedding.is_not(None)  # Only chunks with embeddings
                )
                
                # Add contract filter if specified
                if contract_id:
                    base_query = base_query.where(SilverChunk.contract_id == contract_id)
                
                # Execute query
                result = await db.execute(base_query)
                chunks = result.all()
                
                if not chunks:
                    logger.warning(f"No chunks with embeddings found for query: {query[:50]}")
                    return []
                
                # Calculate cosine similarity for each chunk
                chunk_similarities = []
                for chunk in chunks:
                    if chunk.embedding:
                        similarity = self._calculate_cosine_similarity(
                            query_embedding, 
                            chunk.embedding
                        )
                        
                        if similarity >= similarity_threshold:
                            chunk_data = {
                                "chunk_id": chunk.chunk_id,
                                "contract_id": chunk.contract_id,
                                "chunk_text": chunk.chunk_text,
                                "start_offset": chunk.start_offset,
                                "end_offset": chunk.end_offset,
                                "chunk_order": chunk.chunk_order
                            }
                            chunk_similarities.append((chunk_data, similarity))
                
                # Sort by similarity score (descending) and limit
                chunk_similarities.sort(key=lambda x: x[1], reverse=True)
                return chunk_similarities[:limit]
                
        except Exception as e:
            logger.error(f"TiDB vector search failed: {e}")
            return []
    
    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            import numpy as np
            
            # Convert to numpy arrays
            a = np.array(vec1)
            b = np.array(vec2)
            
            # Calculate cosine similarity
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            similarity = dot_product / (norm_a * norm_b)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Cosine similarity calculation failed: {e}")
            return 0.0
    
    async def keyword_search_with_tokens(
        self, 
        query: str, 
        user_id: str,
        contract_id: str = None, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Keyword search using token analysis"""
        try:
            # Extract keywords from query
            query_tokens = query.lower().split()
            
            async for db in get_operational_db():
                # Build token search query
                if contract_id:
                    token_query = select(Token).where(
                        and_(
                            Token.contract_id == contract_id,
                            Token.token_text.in_(query_tokens)
                        )
                    ).order_by(Token.frequency.desc())
                else:
                    # Search across user's documents
                    token_query = select(Token).join(BronzeContract).where(
                        and_(
                            BronzeContract.owner_user_id == user_id,
                            Token.token_text.in_(query_tokens)
                        )
                    ).order_by(Token.frequency.desc())
                
                result = await db.execute(token_query.limit(limit * 2))
                tokens = result.scalars().all()
                
                # Group by contract and calculate scores
                contract_scores = {}
                for token in tokens:
                    cid = token.contract_id
                    if cid not in contract_scores:
                        contract_scores[cid] = {
                            "score": 0,
                            "matched_tokens": [],
                            "total_frequency": 0
                        }
                    
                    # Score based on frequency and query relevance
                    token_score = token.frequency * (1.0 if token.token_text in query_tokens else 0.5)
                    contract_scores[cid]["score"] += token_score
                    contract_scores[cid]["matched_tokens"].append(token.token_text)
                    contract_scores[cid]["total_frequency"] += token.frequency
                
                # Convert to results format
                results = []
                for contract_id, score_data in sorted(
                    contract_scores.items(), 
                    key=lambda x: x[1]["score"], 
                    reverse=True
                )[:limit]:
                    results.append({
                        "contract_id": contract_id,
                        "score": min(1.0, score_data["score"] / 100.0),  # Normalize score
                        "match_type": "keyword",
                        "matched_tokens": score_data["matched_tokens"],
                        "total_frequency": score_data["total_frequency"]
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
    
    async def clause_search(
        self, 
        query: str, 
        user_id: str,
        contract_id: str = None, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for relevant clauses"""
        try:
            # Map query terms to clause types
            clause_type_mapping = {
                "liability": ["liability", "indemnification"],
                "termination": ["termination", "terminate"],
                "renewal": ["auto_renewal", "renewal"],
                "payment": ["payment_terms", "payment"],
                "confidentiality": ["confidentiality", "nda"],
                "ip": ["intellectual_property", "ip"],
                "force majeure": ["force_majeure"],
                "governing": ["governing_law"]
            }
            
            relevant_clause_types = []
            query_lower = query.lower()
            
            for clause_category, clause_types in clause_type_mapping.items():
                if any(term in query_lower for term in clause_types):
                    relevant_clause_types.extend(clause_types)
            
            if not relevant_clause_types:
                return []
            
            async for db in get_operational_db():
                # Search for relevant clauses
                if contract_id:
                    clause_query = select(SilverClauseSpan).where(
                        and_(
                            SilverClauseSpan.contract_id == contract_id,
                            SilverClauseSpan.clause_type.in_(relevant_clause_types)
                        )
                    ).order_by(SilverClauseSpan.confidence.desc())
                else:
                    clause_query = select(SilverClauseSpan).join(BronzeContract).where(
                        and_(
                            BronzeContract.owner_user_id == user_id,
                            SilverClauseSpan.clause_type.in_(relevant_clause_types)
                        )
                    ).order_by(SilverClauseSpan.confidence.desc())
                
                result = await db.execute(clause_query.limit(limit))
                clauses = result.scalars().all()
                
                results = []
                for clause in clauses:
                    results.append({
                        "contract_id": clause.contract_id,
                        "clause_id": clause.span_id,
                        "content": clause.snippet,
                        "score": clause.confidence,
                        "match_type": "clause",
                        "clause_type": clause.clause_type,
                        "clause_name": clause.clause_name,
                        "risk_indicators": clause.risk_indicators or []
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"Clause search failed: {e}")
            return []
    
    async def metadata_search(
        self, 
        query: str, 
        user_id: str,
        contract_id: str = None, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search based on file metadata (filename, mime type, etc.)"""
        try:
            async for db in get_operational_db():
                # Build metadata search query
                base_query = select(BronzeContract).where(BronzeContract.owner_user_id == user_id)
                
                if contract_id:
                    base_query = base_query.where(BronzeContract.contract_id == contract_id)
                
                # Search in filename and mime type
                metadata_query = base_query.where(
                    or_(
                        BronzeContract.filename.ilike(f"%{query}%"),
                        BronzeContract.mime_type.ilike(f"%{query}%")
                    )
                ).order_by(BronzeContract.created_at.desc())
                
                result = await db.execute(metadata_query.limit(limit))
                contracts = result.scalars().all()
                
                results = []
                for contract in contracts:
                    # Calculate metadata relevance score
                    filename_match = query.lower() in contract.filename.lower()
                    mimetype_match = query.lower() in contract.mime_type.lower()
                    
                    score = 0.0
                    if filename_match:
                        score += 0.8
                    if mimetype_match:
                        score += 0.4
                    
                    results.append({
                        "contract_id": contract.contract_id,
                        "filename": contract.filename,
                        "score": min(1.0, score),
                        "match_type": "metadata",
                        "mime_type": contract.mime_type,
                        "file_size": contract.file_size,
                        "created_at": contract.created_at.isoformat() if contract.created_at else None
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"Metadata search failed: {e}")
            return []
    
    async def combine_search_results(self, search_results: List[Tuple[str, List[Dict]]]) -> List[Dict[str, Any]]:
        """Combine and rank results from different search methods"""
        try:
            # Aggregate results by contract_id
            contract_results = {}
            
            for search_type, results in search_results:
                weight = self.search_weights.get(search_type, 0.1)
                
                for result in results:
                    contract_id = result["contract_id"]
                    
                    if contract_id not in contract_results:
                        contract_results[contract_id] = {
                            "contract_id": contract_id,
                            "combined_score": 0.0,
                            "match_types": [],
                            "details": {},
                            "best_content": ""
                        }
                    
                    # Add weighted score
                    weighted_score = result["score"] * weight
                    contract_results[contract_id]["combined_score"] += weighted_score
                    
                    # Track match types
                    if result["match_type"] not in contract_results[contract_id]["match_types"]:
                        contract_results[contract_id]["match_types"].append(result["match_type"])
                    
                    # Store details for each search type
                    contract_results[contract_id]["details"][search_type] = result
                    
                    # Keep best content snippet
                    if "content" in result and len(result["content"]) > len(contract_results[contract_id]["best_content"]):
                        contract_results[contract_id]["best_content"] = result["content"]
            
            # Sort by combined score
            sorted_results = sorted(
                contract_results.values(),
                key=lambda x: x["combined_score"],
                reverse=True
            )
            
            return sorted_results
            
        except Exception as e:
            logger.error(f"Failed to combine search results: {e}")
            return []
    
    async def analyze_search_patterns(self, query: str, results: List[Dict]) -> Dict[str, Any]:
        """Analyze search patterns and generate insights using LLM"""
        try:
            if not results:
                return {
                    "overall_confidence": 0.0,
                    "pattern_analysis": "No results found",
                    "search_quality": "poor"
                }
            
            # Prepare analysis data
            analysis_prompt = f"""
            Analyze this search query and results to provide insights:
            
            Query: "{query}"
            Results found: {len(results)}
            Match types: {list(set([r.get('match_types', []) for r in results]))}
            
            Top 3 results:
            {json.dumps(results[:3], indent=2, default=str)}
            
            Provide analysis as JSON:
            {{
                "search_intent": "what the user is looking for",
                "result_quality": "excellent|good|fair|poor",
                "confidence": 0.0-1.0,
                "patterns": ["pattern1", "pattern2"],
                "suggestions": ["suggestion1", "suggestion2"]
            }}
            """
            
            llm_result, call_id = await self.call_llm_with_tracking(
                prompt=analysis_prompt,
                contract_id=results[0]["contract_id"] if results else "system",
                task_type=LLMTask.ANALYSIS,
                max_tokens=500
            )
            
            try:
                insights = json.loads(llm_result["content"])
                insights.update({
                    "chunks_searched": sum(1 for r in results if "chunk_id" in r.get("details", {}).get("semantic", {})),
                    "tokens_analyzed": sum(len(r.get("details", {}).get("keyword", {}).get("matched_tokens", [])) for r in results),
                    "clauses_matched": sum(1 for r in results if "clause" in r.get("match_types", []))
                })
                
                return insights
                
            except json.JSONDecodeError:
                return {
                    "overall_confidence": 0.7,
                    "pattern_analysis": llm_result["content"],
                    "search_quality": "fair"
                }
                
        except Exception as e:
            logger.error(f"Search pattern analysis failed: {e}")
            return {
                "overall_confidence": 0.5,
                "pattern_analysis": f"Analysis failed: {str(e)}",
                "search_quality": "unknown"
            }
    
    async def generate_search_recommendations(self, query: str, results: List[Dict]) -> List[str]:
        """Generate context-appropriate recommendations"""
        recommendations = []
        
        # Check if this is a summary/analysis query vs. a search query
        is_analysis_query = any(word in query.lower() for word in [
            'summarize', 'summary', 'key findings', 'overview', 'main points', 
            'analyze', 'analysis', 'what does', 'tell me about'
        ])
        
        if is_analysis_query:
            # For analysis queries, provide document insights rather than search tips
            if results:
                recommendations.extend([
                    "Document analysis completed using multi-modal search",
                    "Review identified clauses and risk factors",
                    "Consider legal consultation for high-risk items"
                ])
            else:
                recommendations.extend([
                    "No specific content found for this query",
                    "Try asking about specific contract sections",
                    "Consider reviewing the full document manually"
                ])
        else:
            # For search queries, provide search improvement tips
            if not results:
                recommendations.extend([
                    "Try broader search terms",
                    "Check spelling and try synonyms", 
                    "Use document type filters",
                    "Try searching for specific clause types"
                ])
            elif len(results) < 3:
                recommendations.extend([
                    "Try related keywords",
                    "Search across different document types",
                    "Use semantic search with descriptive phrases"
                ])
            else:
                # Analyze result diversity
                match_types = set()
                for result in results:
                    match_types.update(result.get("match_types", []))
                
                if len(match_types) == 1:
                    recommendations.append(f"Results only from {list(match_types)[0]} search - try broader terms")
                
                if "semantic" not in match_types:
                    recommendations.append("Try descriptive phrases for semantic search")
                
                if "clause" not in match_types:
                    recommendations.append("Search for specific clause types (liability, termination, etc.)")
        
        return recommendations[:3]  # Limit recommendations
