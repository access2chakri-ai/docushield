"""
Document Search Agent - Production Ready
Enterprise-grade semantic and keyword search with AWS Bedrock AgentCore compatibility
"""
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from .base_agent import BaseAgent, AgentContext, AgentStatus
from app.services.llm_factory import llm_factory, LLMTask

logger = logging.getLogger(__name__)

class DocumentSearchAgent(BaseAgent):
    """
    Production document search agent with AWS Bedrock AgentCore compatibility
    Handles semantic search, keyword search, and document retrieval with high performance
    """
    
    def __init__(self):
        super().__init__("document_search_agent", "2.0.0")
        self.search_cache = {}
        self.max_results = 20
    
    async def _execute_analysis(self, context: AgentContext):
        """
        Execute search analysis based on query type and context
        """
        try:
            if not context.query:
                return self.create_result(
                    status=AgentStatus.FAILED,
                    error_message="Search query is required"
                )
            
            # Determine search strategy
            search_type = self._determine_search_type(context.query)
            
            if search_type == "semantic":
                return await self._semantic_search(context)
            elif search_type == "keyword":
                return await self._keyword_search(context)
            else:  # hybrid
                return await self._hybrid_search(context)
                
        except Exception as e:
            logger.error(f"Search execution failed: {e}")
            return self.create_result(
                status=AgentStatus.FAILED,
                error_message=str(e)
            )
    
    def _determine_search_type(self, query: str) -> str:
        """Determine optimal search strategy based on query characteristics"""
        query_lower = query.lower()
        
        # Keyword search for specific terms
        keyword_indicators = ["find", "show", "list", "where", "clause", "section"]
        if any(indicator in query_lower for indicator in keyword_indicators):
            return "keyword"
        
        # Semantic search for conceptual queries
        semantic_indicators = ["explain", "what", "how", "why", "meaning", "understand"]
        if any(indicator in query_lower for indicator in semantic_indicators):
            return "semantic"
        
        # Hybrid for complex queries
        return "hybrid"
    
    async def _semantic_search(self, context: AgentContext):
        """Perform semantic search using vector embeddings"""
        try:
            # Get semantic matches
            chunks_with_similarity = await self.semantic_search_chunks(
                query=context.query,
                contract_id=context.contract_id,
                limit=10,
                similarity_threshold=0.6
            )
            
            if not chunks_with_similarity:
                return self.create_result(
                    status=AgentStatus.COMPLETED,
                    confidence=0.3,
                    findings=[{
                        "type": "no_results",
                        "title": "No semantic matches found",
                        "severity": "info",
                        "confidence": 0.8,
                        "description": f"No content found matching '{context.query}'"
                    }],
                    recommendations=["Try different search terms or keywords"],
                    llm_calls=1,
                    data_sources=["embeddings"]
                )
            
            # Process results
            findings = []
            for chunk_data, similarity in chunks_with_similarity:
                findings.append({
                    "type": "semantic_match",
                    "title": f"Relevant content (similarity: {similarity:.2f})",
                    "severity": "info",
                    "confidence": similarity,
                    "content": chunk_data["chunk_text"][:500],
                    "similarity_score": similarity,
                    "chunk_order": chunk_data["chunk_order"]
                })
            
            recommendations = [
                f"Found {len(chunks_with_similarity)} relevant sections",
                "Review highlighted content for detailed information",
                "Ask follow-up questions for specific details"
            ]
            
            return self.create_result(
                status=AgentStatus.COMPLETED,
                confidence=0.8,
                findings=findings,
                recommendations=recommendations,
                llm_calls=2,
                data_sources=["silver_chunks", "embeddings"]
            )
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return self.create_result(
                status=AgentStatus.FAILED,
                error_message=f"Semantic search error: {e}"
            )
    
    async def _keyword_search(self, context: AgentContext):
        """Perform keyword-based search"""
        try:
            # Get contract text
            contract = await self.get_contract_with_all_data(context.contract_id)
            if not contract or not contract.text_raw:
                return self.create_result(
                    status=AgentStatus.FAILED,
                    error_message="Document not found"
                )
            
            text = contract.text_raw.raw_text
            query_terms = context.query.lower().split()
            
            # Find keyword matches
            matches = []
            lines = text.split('\n')
            
            for i, line in enumerate(lines):
                line_lower = line.lower()
                if any(term in line_lower for term in query_terms):
                    # Get context around match
                    start_line = max(0, i - 2)
                    end_line = min(len(lines), i + 3)
                    context_text = '\n'.join(lines[start_line:end_line])
                    
                    matches.append({
                        "line_number": i + 1,
                        "matched_line": line.strip(),
                        "context": context_text,
                        "relevance": self._calculate_keyword_relevance(line_lower, query_terms)
                    })
            
            # Sort by relevance
            matches.sort(key=lambda x: x["relevance"], reverse=True)
            matches = matches[:self.max_results]
            
            # Create findings
            findings = []
            for match in matches:
                findings.append({
                    "type": "keyword_match",
                    "title": f"Match on line {match['line_number']}",
                    "severity": "info",
                    "confidence": match["relevance"],
                    "content": match["context"],
                    "line_number": match["line_number"],
                    "matched_text": match["matched_line"]
                })
            
            recommendations = [
                f"Found {len(matches)} keyword matches",
                "Review context around each match",
                "Use semantic search for conceptual queries"
            ]
            
            return self.create_result(
                status=AgentStatus.COMPLETED,
                confidence=0.7,
                findings=findings,
                recommendations=recommendations,
                llm_calls=0,
                data_sources=["bronze_contract_text_raw"]
            )
            
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return self.create_result(
                status=AgentStatus.FAILED,
                error_message=f"Keyword search error: {e}"
            )
    
    async def _hybrid_search(self, context: AgentContext):
        """Combine semantic and keyword search for comprehensive results"""
        try:
            # Run both searches in parallel
            semantic_task = self._semantic_search(context)
            keyword_task = self._keyword_search(context)
            
            semantic_result, keyword_result = await asyncio.gather(
                semantic_task, keyword_task, return_exceptions=True
            )
            
            # Handle exceptions
            if isinstance(semantic_result, Exception):
                semantic_result = None
            if isinstance(keyword_result, Exception):
                keyword_result = None
            
            # Combine results
            combined_findings = []
            combined_recommendations = []
            total_llm_calls = 0
            
            if semantic_result and semantic_result.status == AgentStatus.COMPLETED:
                combined_findings.extend(semantic_result.findings)
                combined_recommendations.extend(semantic_result.recommendations)
                total_llm_calls += semantic_result.llm_calls
            
            if keyword_result and keyword_result.status == AgentStatus.COMPLETED:
                combined_findings.extend(keyword_result.findings)
                combined_recommendations.extend(keyword_result.recommendations)
                total_llm_calls += keyword_result.llm_calls
            
            # Remove duplicates and rank
            unique_findings = self._deduplicate_findings(combined_findings)
            unique_recommendations = list(set(combined_recommendations))
            
            confidence = 0.85 if len(unique_findings) > 0 else 0.3
            
            return self.create_result(
                status=AgentStatus.COMPLETED,
                confidence=confidence,
                findings=unique_findings,
                recommendations=unique_recommendations[:8],
                llm_calls=total_llm_calls,
                data_sources=["silver_chunks", "bronze_contract_text_raw", "embeddings"]
            )
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return self.create_result(
                status=AgentStatus.FAILED,
                error_message=f"Hybrid search error: {e}"
            )
    
    def _calculate_keyword_relevance(self, text: str, query_terms: List[str]) -> float:
        """Calculate relevance score for keyword matches"""
        score = 0.0
        text_words = text.split()
        
        for term in query_terms:
            # Exact matches get higher score
            if term in text:
                score += 1.0
            
            # Partial matches get lower score
            for word in text_words:
                if term in word:
                    score += 0.5
        
        # Normalize by text length
        return min(1.0, score / max(1, len(text_words) / 10))
    
    def _deduplicate_findings(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate findings and rank by relevance"""
        seen_content = set()
        unique_findings = []
        
        # Sort by confidence first
        sorted_findings = sorted(findings, key=lambda x: x.get("confidence", 0), reverse=True)
        
        for finding in sorted_findings:
            content_key = finding.get("content", "")[:100]  # First 100 chars as key
            
            if content_key not in seen_content:
                seen_content.add(content_key)
                unique_findings.append(finding)
        
        return unique_findings[:15]  # Limit to 15 unique findings