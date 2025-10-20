"""
Advanced Search Service for DocuShield
Production-ready search service with configurable thresholds and dynamic filtering
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
import os

logger = logging.getLogger(__name__)

class SearchType(Enum):
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"

@dataclass
class SearchResult:
    """Individual search result"""
    document_id: str
    title: str
    document_type: str
    content_snippet: str
    relevance_score: float
    match_type: str
    highlights: List[str]
    metadata: Dict[str, Any]

@dataclass
class SearchResponse:
    """Complete search response"""
    query: str
    results: List[SearchResult]
    total_results: int
    search_time_ms: float
    search_type: SearchType
    applied_filters: Dict[str, Any]
    suggestions: List[str]

class AdvancedSearchService:
    """
    Production-ready search service with configurable parameters
    """
    
    def __init__(self):
        # Configurable thresholds from environment or defaults
        self.min_confidence_threshold = float(os.getenv("SEARCH_MIN_CONFIDENCE", "0.05"))
        self.max_content_snippet_length = int(os.getenv("SEARCH_SNIPPET_LENGTH", "500"))
        self.default_result_limit = int(os.getenv("SEARCH_DEFAULT_LIMIT", "20"))
        self.max_result_limit = int(os.getenv("SEARCH_MAX_LIMIT", "100"))
        self.search_timeout_seconds = float(os.getenv("SEARCH_TIMEOUT", "90.0"))
        
        # Dynamic filtering configuration
        self.excluded_finding_types = set(os.getenv("SEARCH_EXCLUDED_TYPES", "no_results,no_documents,no_matches").split(","))
        
        logger.info(f"AdvancedSearchService initialized with min_confidence={self.min_confidence_threshold}, "
                   f"snippet_length={self.max_content_snippet_length}, timeout={self.search_timeout_seconds}s")
    
    async def search(
        self, 
        query: str, 
        user_id: str,
        search_type: SearchType = SearchType.HYBRID,
        limit: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        document_types: Optional[List[str]] = None,
        industry_types: Optional[List[str]] = None,
        min_confidence: Optional[float] = None
    ) -> SearchResponse:
        """
        Production-ready search interface with configurable parameters
        """
        start_time = datetime.now()
        
        # Validate and set parameters
        effective_limit = min(limit or self.default_result_limit, self.max_result_limit)
        effective_min_confidence = min_confidence or self.min_confidence_threshold
        
        # Input validation
        if not query or not query.strip():
            return self._create_error_response(query, start_time, "Empty query provided")
        
        if not user_id:
            return self._create_error_response(query, start_time, "User ID required")
        
        try:
            # Import here to avoid circular imports
            from app.agents.agent_factory import agent_factory, AgentContext
            from app.agents.base_agent import AgentStatus
            import asyncio
            
            # Get the search agent with timeout
            search_agent = agent_factory.get_document_search_agent()
            if not search_agent:
                raise Exception("Search agent not available - check agent factory configuration")
            
            # Create enhanced context
            context = AgentContext(
                contract_id="all",  # Multi-document search
                user_id=user_id,
                query=query.strip(),
                cache_enabled=False,
                document_type=document_types[0] if document_types else None,
                industry_type=industry_types[0] if industry_types else None
            )
            
            # Execute search with timeout
            agent_result = await asyncio.wait_for(
                search_agent.analyze(context),
                timeout=self.search_timeout_seconds
            )
            
            # Process and filter results
            results = self._process_agent_results(
                agent_result, 
                effective_min_confidence, 
                effective_limit,
                filters or {}
            )
            
            # Generate suggestions based on results
            suggestions = self._generate_search_suggestions(query, results, agent_result)
            
            # Calculate search time
            search_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return SearchResponse(
                query=query,
                results=results,
                total_results=len(results),
                search_time_ms=search_time,
                search_type=search_type,
                applied_filters=self._build_applied_filters(filters, document_types, industry_types, effective_min_confidence),
                suggestions=suggestions
            )
            
        except asyncio.TimeoutError:
            logger.error(f"Search timeout after {self.search_timeout_seconds}s for query '{query}'")
            return self._create_error_response(query, start_time, f"Search timeout after {self.search_timeout_seconds}s")
            
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return self._create_error_response(query, start_time, str(e))
    
    def _process_agent_results(
        self, 
        agent_result, 
        min_confidence: float, 
        limit: int,
        filters: Dict[str, Any]
    ) -> List[SearchResult]:
        """Process and filter agent results into SearchResult objects"""
        from app.agents.base_agent import AgentStatus
        
        results = []
        
        if not agent_result or agent_result.status != AgentStatus.COMPLETED or not agent_result.findings:
            return results
        
        for finding in agent_result.findings:
            # Skip excluded finding types (configurable)
            if finding.get("type") in self.excluded_finding_types:
                continue
            
            # Apply confidence threshold
            confidence = finding.get("confidence", 0.0)
            if confidence < min_confidence:
                continue
            
            # Apply additional filters if specified
            if not self._passes_filters(finding, filters):
                continue
            
            # Build dynamic highlights
            highlights = self._build_highlights(finding)
            
            # Create search result
            results.append(SearchResult(
                document_id=finding.get("document_id", "unknown"),
                title=finding.get("document_title", "Unknown Document"),
                document_type=finding.get("document_type", "document"),
                content_snippet=self._truncate_content(finding.get("content", "")),
                relevance_score=confidence,
                match_type=finding.get("type", "semantic"),
                highlights=highlights,
                metadata=self._clean_metadata(finding)
            ))
        
        # Sort by relevance and apply limit
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:limit]
    
    def _build_highlights(self, finding: Dict[str, Any]) -> List[str]:
        """Build dynamic highlights based on finding type and available data"""
        highlights = []
        
        # First, use the highlights array from the search agent if available
        agent_highlights = finding.get("highlights", [])
        if agent_highlights:
            highlights.extend(agent_highlights)
        
        # Add additional context-specific highlights
        finding_type = finding.get("type", "")
        
        if finding_type == "semantic_match":
            semantic_highlights = finding.get("semantic_highlights", [])
            if semantic_highlights and not agent_highlights:
                highlights.extend(semantic_highlights)
                
        elif finding_type == "keyword_match":
            matched_keywords = finding.get("matched_keywords", [])
            if matched_keywords and not agent_highlights:
                highlights.extend(matched_keywords)
        
        # Add financial highlights if present
        financial_highlights = finding.get("financial_highlights", [])
        if financial_highlights:
            for fh in financial_highlights:
                if isinstance(fh, dict) and "matched_text" in fh:
                    highlights.append(fh["matched_text"])
        
        # If no highlights found, use match explanation or title
        if not highlights:
            explanation = finding.get("match_explanation", finding.get("title", "Match found"))
            highlights.append(explanation)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_highlights = []
        for highlight in highlights:
            if highlight and highlight not in seen:
                seen.add(highlight)
                unique_highlights.append(highlight)
        
        return unique_highlights[:10]  # Limit to 10 highlights
    
    def _passes_filters(self, finding: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if finding passes additional filters"""
        if not filters:
            return True
        
        # Document type filter
        if "document_type" in filters:
            doc_type = finding.get("document_type", "").lower()
            allowed_types = [t.lower() for t in filters["document_type"]] if isinstance(filters["document_type"], list) else [filters["document_type"].lower()]
            if doc_type not in allowed_types:
                return False
        
        # Risk level filter
        if "risk_level" in filters:
            risk_level = finding.get("risk_level", "").lower()
            allowed_risks = [r.lower() for r in filters["risk_level"]] if isinstance(filters["risk_level"], list) else [filters["risk_level"].lower()]
            if risk_level not in allowed_risks:
                return False
        
        return True
    
    def _truncate_content(self, content: str) -> str:
        """Truncate content to configured length"""
        if len(content) <= self.max_content_snippet_length:
            return content
        return content[:self.max_content_snippet_length] + "..."
    
    def _clean_metadata(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and prepare metadata for response"""
        # Remove internal fields and keep only relevant metadata
        excluded_keys = {"content", "semantic_highlights", "matched_keywords", "match_explanation"}
        return {k: v for k, v in finding.items() if k not in excluded_keys}
    
    def _generate_search_suggestions(self, query: str, results: List[SearchResult], agent_result) -> List[str]:
        """Generate dynamic search suggestions based on results"""
        suggestions = []
        
        if not results:
            suggestions.extend([
                "Try different search terms",
                "Use more specific keywords",
                "Check document availability"
            ])
        elif len(results) < 3:
            suggestions.extend([
                "Try broader search terms",
                "Use synonyms or related terms"
            ])
        else:
            suggestions.extend([
                f"Found {len(results)} relevant results",
                "Refine search for more specific results"
            ])
        
        return suggestions[:3]  # Limit suggestions
    
    def _build_applied_filters(
        self, 
        filters: Optional[Dict[str, Any]], 
        document_types: Optional[List[str]], 
        industry_types: Optional[List[str]], 
        min_confidence: float
    ) -> Dict[str, Any]:
        """Build applied filters summary"""
        applied = {}
        
        if filters:
            applied.update(filters)
        
        if document_types:
            applied["document_types"] = document_types
        
        if industry_types:
            applied["industry_types"] = industry_types
        
        applied["min_confidence"] = min_confidence
        
        return applied
    
    def _create_error_response(self, query: str, start_time: datetime, error_message: str) -> SearchResponse:
        """Create standardized error response"""
        search_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return SearchResponse(
            query=query,
            results=[],
            total_results=0,
            search_time_ms=search_time,
            search_type=SearchType.HYBRID,
            applied_filters={},
            suggestions=[f"Search error: {error_message}"]
        )

# Create singleton instance
advanced_search_service = AdvancedSearchService()