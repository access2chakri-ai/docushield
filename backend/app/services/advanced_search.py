"""
Advanced Hybrid Search Service for DocuShield
Combines semantic (vector) + keyword (full-text) search with intelligent query parsing
Supports complex queries like "Find contracts with auto-renewal clauses" and "Show invoices above $50k missing PO reference"
Now integrated with Agent Factory for consistent agent-based processing
"""
import json
import re
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, and_, or_, func
from sqlalchemy.orm import selectinload

from app.database import get_operational_db
from app.models import (
    BronzeContract, BronzeContractTextRaw, SilverChunk, SilverClauseSpan, Token,
    GoldContractScore, GoldFinding, GoldSuggestion, User
)
from app.services.llm_factory import llm_factory, LLMTask
from app.core.config import settings

logger = logging.getLogger(__name__)

class SearchType(Enum):
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    STRUCTURED = "structured"

class DocumentFilter(Enum):
    ALL = "all"
    CONTRACTS = "contracts"
    INVOICES = "invoices"
    POLICIES = "policies"
    HIGH_RISK = "high_risk"
    RECENT = "recent"
    # New document type filters
    AGREEMENTS = "agreements"
    REPORTS = "reports"
    MANUALS = "manuals"
    SPECIFICATIONS = "specifications"
    RESEARCH_PAPERS = "research_papers"
    PRESENTATIONS = "presentations"
    LEGAL_DOCUMENTS = "legal_documents"
    FORMS = "forms"
    EMAILS = "emails"
    MEMOS = "memos"

@dataclass
class SearchQuery:
    """Parsed search query with intent and filters"""
    original_query: str
    search_type: SearchType
    intent: str  # find_contracts, show_invoices, analyze_risk, etc.
    filters: Dict[str, Any]
    semantic_query: str
    keywords: List[str]
    structured_conditions: Dict[str, Any]
    document_types: List[str] = None  # Filter by document types
    industry_types: List[str] = None  # Filter by industry types

@dataclass
class SearchResult:
    """Individual search result"""
    document_id: str
    title: str
    document_type: str
    content_snippet: str
    relevance_score: float
    match_type: str  # semantic, keyword, clause, metadata
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
    Advanced search service with hybrid capabilities and intelligent query parsing
    """
    
    def __init__(self):
        # Query pattern recognition for intelligent parsing
        self.query_patterns = {
            "find_contracts": [
                r"find\s+contracts?\s+with\s+(.+)",
                r"show\s+me\s+contracts?\s+that\s+(.+)",
                r"contracts?\s+containing\s+(.+)",
                r"search\s+for\s+contracts?\s+(.+)"
            ],
            "find_invoices": [
                r"find\s+invoices?\s+(.+)",
                r"show\s+invoices?\s+(.+)",
                r"invoices?\s+above\s+\$?(\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"invoices?\s+over\s+\$?(\d+(?:,\d{3})*(?:\.\d{2})?)"
            ],
            "risk_analysis": [
                r"high\s+risk\s+(.+)",
                r"risky\s+(.+)",
                r"dangerous\s+(.+)",
                r"problematic\s+(.+)"
            ],
            "clause_search": [
                r"(.+)\s+clauses?",
                r"clauses?\s+about\s+(.+)",
                r"terms\s+related\s+to\s+(.+)"
            ],
            "amount_filter": [
                r"above\s+\$?(\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"over\s+\$?(\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"more\s+than\s+\$?(\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"exceeding\s+\$?(\d+(?:,\d{3})*(?:\.\d{2})?)"
            ],
            "missing_elements": [
                r"missing\s+(.+)",
                r"without\s+(.+)",
                r"lacking\s+(.+)",
                r"no\s+(.+)"
            ]
        }
        
        # Common clause types for enhanced search
        self.clause_types = {
            "auto-renewal": ["auto-renewal", "automatic renewal", "automatically renew", "auto renew"],
            "liability": ["liability", "indemnification", "damages", "unlimited liability"],
            "termination": ["termination", "terminate", "end agreement", "cancel"],
            "payment": ["payment terms", "payment", "invoice", "billing"],
            "confidentiality": ["confidentiality", "non-disclosure", "nda", "confidential"],
            "intellectual_property": ["intellectual property", "ip", "copyright", "trademark"],
            "force_majeure": ["force majeure", "act of god", "unforeseeable circumstances"],
            "governing_law": ["governing law", "jurisdiction", "legal venue"]
        }
    
    async def search(
        self, 
        query: str, 
        user_id: str,
        search_type: SearchType = SearchType.HYBRID,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        document_types: Optional[List[str]] = None,
        industry_types: Optional[List[str]] = None
    ) -> SearchResponse:
        """
        Main search interface with intelligent query parsing and hybrid search
        Now uses Agent Factory for consistent agent-based processing
        """
        start_time = datetime.now()
        
        try:
            # Parse the query to understand intent and extract filters
            parsed_query = await self._parse_query(query, search_type, filters or {})
            
            # Add document type and industry filters
            if document_types:
                parsed_query.document_types = document_types
            if industry_types:
                parsed_query.industry_types = industry_types
            
            # Use agent-based search for all queries
            results = await self._execute_agent_search(parsed_query, user_id, limit)
            
            # Calculate search time
            search_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Generate search suggestions
            suggestions = await self._generate_suggestions(query, results)
            
            return SearchResponse(
                query=query,
                results=results,
                total_results=len(results),
                search_time_ms=search_time,
                search_type=parsed_query.search_type,
                applied_filters=parsed_query.filters,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return SearchResponse(
                query=query,
                results=[],
                total_results=0,
                search_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                search_type=search_type,
                applied_filters={},
                suggestions=[f"Search error: {str(e)}"]
            )
    
    async def _parse_query(self, query: str, search_type: SearchType, filters: Dict[str, Any]) -> SearchQuery:
        """
        Parse natural language query to extract intent, filters, and search parameters
        """
        query_lower = query.lower().strip()
        
        # Detect intent from query patterns
        intent = "general_search"
        structured_conditions = {}
        keywords = []
        semantic_query = query
        
        # Check for contract-specific queries
        for pattern in self.query_patterns["find_contracts"]:
            match = re.search(pattern, query_lower)
            if match:
                intent = "find_contracts"
                filters["document_type"] = "contract"
                semantic_query = match.group(1) if match.groups() else query
                break
        
        # Check for invoice-specific queries
        for pattern in self.query_patterns["find_invoices"]:
            match = re.search(pattern, query_lower)
            if match:
                intent = "find_invoices"
                filters["document_type"] = "invoice"
                if match.groups() and match.group(1).replace(',', '').isdigit():
                    # Extract amount filter
                    amount = float(match.group(1).replace(',', ''))
                    structured_conditions["min_amount"] = amount
                break
        
        # Check for risk-related queries
        for pattern in self.query_patterns["risk_analysis"]:
            match = re.search(pattern, query_lower)
            if match:
                intent = "risk_analysis"
                filters["risk_level"] = ["high", "critical"]
                semantic_query = match.group(1) if match.groups() else query
                break
        
        # Check for clause-specific queries
        for pattern in self.query_patterns["clause_search"]:
            match = re.search(pattern, query_lower)
            if match:
                intent = "clause_search"
                clause_term = match.group(1) if match.groups() else query
                
                # Map to known clause types
                for clause_type, terms in self.clause_types.items():
                    if any(term in clause_term for term in terms):
                        structured_conditions["clause_type"] = clause_type
                        break
                
                semantic_query = clause_term
                break
        
        # Extract amount filters
        for pattern in self.query_patterns["amount_filter"]:
            match = re.search(pattern, query_lower)
            if match:
                amount = float(match.group(1).replace(',', ''))
                structured_conditions["min_amount"] = amount
        
        # Extract missing element filters
        for pattern in self.query_patterns["missing_elements"]:
            match = re.search(pattern, query_lower)
            if match:
                missing_element = match.group(1)
                if "po" in missing_element or "purchase order" in missing_element:
                    structured_conditions["missing_po"] = True
                elif "reference" in missing_element:
                    structured_conditions["missing_reference"] = True
        
        # Extract keywords for hybrid search
        keywords = [word for word in query_lower.split() if len(word) > 2 and word not in ["the", "and", "or", "with", "for", "in", "on", "at", "to", "from"]]
        
        return SearchQuery(
            original_query=query,
            search_type=search_type,
            intent=intent,
            filters=filters,
            semantic_query=semantic_query,
            keywords=keywords,
            structured_conditions=structured_conditions
        )
    
    def _should_use_search_agent(self, query: SearchQuery) -> bool:
        """
        Determine if the query should use the search agent
        The search agent can handle all types of queries including complex ones
        """
        # Always use search agent - it's more capable than legacy search
        return True
    
    async def _execute_agent_search(self, query: SearchQuery, user_id: str, limit: int) -> List[SearchResult]:
        """
        Execute search using the agent factory's search agent
        """
        try:
            # Import here to avoid circular imports
            from app.agents.agent_factory import agent_factory, AgentContext
            
            # Get the search agent from the factory
            search_agent = agent_factory.get_document_search_agent()
            if not search_agent:
                logger.warning("Search agent not available, falling back to legacy search")
                return await self._execute_search(query, user_id, limit)
            
            # Get user's documents to search through
            async for db in get_operational_db():
                # Get all user documents for multi-document search
                documents_query = select(BronzeContract).where(
                    BronzeContract.owner_user_id == user_id
                ).limit(50)  # Limit to prevent overwhelming the agent
                
                result = await db.execute(documents_query)
                contracts = result.scalars().all()
                
                if not contracts:
                    return []
                
                # Execute search for each document and aggregate results
                all_results = []
                
                for contract in contracts:
                    try:
                        # Create enhanced query that includes structured conditions
                        enhanced_query = self._create_enhanced_query(query)
                        
                        # Create agent context for this document
                        context = AgentContext(
                            contract_id=contract.contract_id,
                            user_id=user_id,
                            query=enhanced_query
                        )
                        
                        # Execute agent search
                        agent_result = await search_agent.analyze(context)
                        
                        if agent_result.status == "COMPLETED" and agent_result.findings:
                            # Convert agent findings to SearchResult format
                            for finding in agent_result.findings:
                                search_result = SearchResult(
                                    document_id=contract.contract_id,
                                    title=contract.filename,
                                    document_type=self._determine_document_type(contract.filename),
                                    content_snippet=finding.get("content", "")[:300],
                                    relevance_score=finding.get("confidence", 0.5),
                                    match_type=finding.get("type", "agent_search"),
                                    highlights=[finding.get("title", "")],
                                    metadata={
                                        "agent_finding": True,
                                        "finding_type": finding.get("type"),
                                        "line_number": finding.get("line_number"),
                                        "similarity_score": finding.get("similarity_score"),
                                        "chunk_order": finding.get("chunk_order"),
                                        "created_at": contract.created_at.isoformat() if contract.created_at else None
                                    }
                                )
                                all_results.append(search_result)
                    
                    except Exception as e:
                        logger.warning(f"Agent search failed for contract {contract.contract_id}: {e}")
                        continue
                
                # Sort by relevance and return top results
                all_results.sort(key=lambda x: x.relevance_score, reverse=True)
                return all_results[:limit]
                
        except Exception as e:
            logger.error(f"Agent search execution failed: {e}")
            # Fallback to legacy search
            return await self._execute_search(query, user_id, limit)
    
    def _create_enhanced_query(self, query: SearchQuery) -> str:
        """
        Create an enhanced query that includes structured conditions for the agent
        This allows the agent to understand complex requirements like amounts and missing references
        """
        enhanced_parts = [query.semantic_query or query.original_query]
        
        # Add structured conditions as natural language
        if query.structured_conditions.get("min_amount"):
            amount = query.structured_conditions["min_amount"]
            enhanced_parts.append(f"with amounts above ${amount:,.2f}")
        
        if query.structured_conditions.get("missing_po"):
            enhanced_parts.append("that are missing purchase order references")
        
        if query.structured_conditions.get("missing_reference"):
            enhanced_parts.append("that are missing reference numbers")
        
        if query.structured_conditions.get("clause_type"):
            clause_type = query.structured_conditions["clause_type"]
            enhanced_parts.append(f"containing {clause_type.replace('_', ' ')} clauses")
        
        # Add document type filters
        if query.filters.get("document_type"):
            doc_type = query.filters["document_type"]
            enhanced_parts.append(f"in {doc_type} documents")
        
        return " ".join(enhanced_parts)
    
    def _determine_document_type(self, filename: str) -> str:
        """Determine document type from filename"""
        filename_lower = filename.lower()
        
        if any(term in filename_lower for term in ["contract", "agreement", "terms"]):
            return "contract"
        elif any(term in filename_lower for term in ["invoice", "bill", "receipt"]):
            return "invoice"
        elif any(term in filename_lower for term in ["policy", "procedure"]):
            return "policy"
        elif any(term in filename_lower for term in ["report", "analysis"]):
            return "report"
        else:
            return "document"
    
    async def _execute_search(self, query: SearchQuery, user_id: str, limit: int) -> List[SearchResult]:
        """
        Execute search based on parsed query intent
        """
        if query.intent == "find_contracts":
            return await self._search_contracts(query, user_id, limit)
        elif query.intent == "find_invoices":
            return await self._search_invoices(query, user_id, limit)
        elif query.intent == "risk_analysis":
            return await self._search_high_risk_documents(query, user_id, limit)
        elif query.intent == "clause_search":
            return await self._search_clauses(query, user_id, limit)
        else:
            return await self._hybrid_search(query, user_id, limit)
    
    async def _search_contracts(self, query: SearchQuery, user_id: str, limit: int) -> List[SearchResult]:
        """
        Search for contracts with specific criteria
        """
        async for db in get_operational_db():
            results = []
            
            # Build base query for contracts
            base_query = select(BronzeContract).options(
                selectinload(BronzeContract.text_raw),
                selectinload(BronzeContract.scores),
                selectinload(BronzeContract.clause_spans)
            ).where(
                BronzeContract.owner_user_id == user_id
            )
            
            # Apply document type filter if specified
            if query.filters.get("document_type") == "contract":
                # Use filename patterns to identify contracts
                base_query = base_query.where(
                    or_(
                        BronzeContract.filename.ilike('%contract%'),
                        BronzeContract.filename.ilike('%agreement%'),
                        BronzeContract.filename.ilike('%terms%'),
                        BronzeContract.mime_type == 'application/pdf'  # Assume PDFs might be contracts
                    )
                )
            
            # Execute base query
            result = await db.execute(base_query.limit(limit))
            contracts = result.scalars().all()
            
            # For each contract, check if it matches the semantic criteria
            for contract in contracts:
                if not contract.text_raw:
                    continue
                
                # Check for specific clause types if specified
                clause_match = False
                if query.structured_conditions.get("clause_type"):
                    clause_type = query.structured_conditions["clause_type"]
                    clause_terms = self.clause_types.get(clause_type, [])
                    
                    # Check in text content
                    text_content = contract.text_raw.raw_text.lower()
                    if any(term in text_content for term in clause_terms):
                        clause_match = True
                    
                    # Check in extracted clauses
                    for clause_span in contract.clause_spans:
                        if clause_span.clause_type == clause_type or any(term in clause_span.snippet.lower() for term in clause_terms):
                            clause_match = True
                            break
                
                # If we're looking for specific clauses and didn't find them, skip
                if query.structured_conditions.get("clause_type") and not clause_match:
                    continue
                
                # Calculate semantic similarity if we have embeddings
                semantic_score = 0.7  # Default score
                if contract.chunks:
                    semantic_score = await self._calculate_semantic_similarity(
                        query.semantic_query, contract.chunks[:3]  # Check first 3 chunks
                    )
                
                # Create search result
                snippet = contract.text_raw.raw_text[:300] + "..." if len(contract.text_raw.raw_text) > 300 else contract.text_raw.raw_text
                
                highlights = []
                if clause_match:
                    highlights.append(f"Contains {query.structured_conditions.get('clause_type', 'relevant')} clauses")
                
                # Add keyword highlights
                for keyword in query.keywords:
                    if keyword in contract.text_raw.raw_text.lower():
                        highlights.append(f"Keyword: {keyword}")
                
                result_item = SearchResult(
                    document_id=contract.contract_id,
                    title=contract.filename,
                    document_type="contract",
                    content_snippet=snippet,
                    relevance_score=semantic_score,
                    match_type="semantic+clause" if clause_match else "semantic",
                    highlights=highlights,
                    metadata={
                        "file_size": contract.file_size,
                        "created_at": contract.created_at.isoformat() if contract.created_at else None,
                        "risk_level": contract.scores.risk_level if contract.scores else "unknown",
                        "clause_count": len(contract.clause_spans)
                    }
                )
                
                results.append(result_item)
            
            # Sort by relevance score
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            return results[:limit]
    
    async def _search_invoices(self, query: SearchQuery, user_id: str, limit: int) -> List[SearchResult]:
        """
        Search for invoices with amount and reference filters
        """
        async for db in get_operational_db():
            results = []
            
            # Build base query for invoice-like documents
            base_query = select(BronzeContract).options(
                selectinload(BronzeContract.text_raw)
            ).where(
                BronzeContract.owner_user_id == user_id,
                or_(
                    BronzeContract.filename.ilike('%invoice%'),
                    BronzeContract.filename.ilike('%bill%'),
                    BronzeContract.filename.ilike('%receipt%'),
                    BronzeContract.filename.ilike('%payment%')
                )
            )
            
            result = await db.execute(base_query.limit(limit * 2))  # Get more to filter
            contracts = result.scalars().all()
            
            for contract in contracts:
                if not contract.text_raw:
                    continue
                
                text_content = contract.text_raw.raw_text
                
                # Extract amounts from document
                amount_pattern = r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
                amounts = [float(match.replace(',', '')) for match in re.findall(amount_pattern, text_content)]
                max_amount = max(amounts) if amounts else 0
                
                # Apply amount filter if specified
                min_amount = query.structured_conditions.get("min_amount", 0)
                if min_amount > 0 and max_amount < min_amount:
                    continue
                
                # Check for missing PO reference if specified
                missing_po = query.structured_conditions.get("missing_po", False)
                if missing_po:
                    po_patterns = [r'purchase\s+order', r'P\.?O\.?\s*#?', r'PO\s*#?']
                    has_po = any(re.search(pattern, text_content, re.IGNORECASE) for pattern in po_patterns)
                    if has_po:
                        continue  # Skip if PO reference is found (we want missing PO)
                
                # Calculate relevance score
                relevance_score = 0.8
                if amounts:
                    # Boost score for documents with amounts
                    relevance_score += 0.1
                if missing_po:
                    relevance_score += 0.1
                
                # Create highlights
                highlights = []
                if amounts:
                    highlights.append(f"Amount: ${max_amount:,.2f}")
                if missing_po and not any(re.search(pattern, text_content, re.IGNORECASE) for pattern in po_patterns):
                    highlights.append("Missing PO reference")
                
                snippet = text_content[:300] + "..." if len(text_content) > 300 else text_content
                
                result_item = SearchResult(
                    document_id=contract.contract_id,
                    title=contract.filename,
                    document_type="invoice",
                    content_snippet=snippet,
                    relevance_score=relevance_score,
                    match_type="structured",
                    highlights=highlights,
                    metadata={
                        "max_amount": max_amount,
                        "amounts_found": len(amounts),
                        "has_po_reference": not missing_po or any(re.search(pattern, text_content, re.IGNORECASE) for pattern in po_patterns),
                        "created_at": contract.created_at.isoformat() if contract.created_at else None
                    }
                )
                
                results.append(result_item)
            
            # Sort by amount (descending) then by relevance
            results.sort(key=lambda x: (x.metadata.get("max_amount", 0), x.relevance_score), reverse=True)
            return results[:limit]
    
    async def _search_high_risk_documents(self, query: SearchQuery, user_id: str, limit: int) -> List[SearchResult]:
        """
        Search for high-risk documents
        """
        async for db in get_operational_db():
            # Query high-risk documents
            base_query = select(BronzeContract).options(
                selectinload(BronzeContract.text_raw),
                selectinload(BronzeContract.scores),
                selectinload(BronzeContract.findings)
            ).join(GoldContractScore).where(
                BronzeContract.owner_user_id == user_id,
                GoldContractScore.risk_level.in_(["high", "critical"])
            )
            
            result = await db.execute(base_query.limit(limit))
            contracts = result.scalars().all()
            
            results = []
            for contract in contracts:
                # Create highlights from findings
                highlights = []
                if contract.findings:
                    for finding in contract.findings[:3]:  # Top 3 findings
                        highlights.append(f"Risk: {finding.title}")
                
                snippet = ""
                if contract.text_raw:
                    snippet = contract.text_raw.raw_text[:300] + "..." if len(contract.text_raw.raw_text) > 300 else contract.text_raw.raw_text
                
                result_item = SearchResult(
                    document_id=contract.contract_id,
                    title=contract.filename,
                    document_type="contract",
                    content_snippet=snippet,
                    relevance_score=contract.scores.overall_score / 100 if contract.scores else 0.5,
                    match_type="risk_analysis",
                    highlights=highlights,
                    metadata={
                        "risk_level": contract.scores.risk_level if contract.scores else "unknown",
                        "risk_score": contract.scores.overall_score if contract.scores else 0,
                        "findings_count": len(contract.findings),
                        "created_at": contract.created_at.isoformat() if contract.created_at else None
                    }
                )
                
                results.append(result_item)
            
            # Sort by risk score (descending)
            results.sort(key=lambda x: x.metadata.get("risk_score", 0), reverse=True)
            return results[:limit]
    
    async def _search_clauses(self, query: SearchQuery, user_id: str, limit: int) -> List[SearchResult]:
        """
        Search for specific clauses across documents
        """
        async for db in get_operational_db():
            results = []
            
            # Search in extracted clauses
            clause_query = select(SilverClauseSpan).options(
                selectinload(SilverClauseSpan.contract)
            ).join(BronzeContract).where(
                BronzeContract.owner_user_id == user_id
            )
            
            # Apply clause type filter if specified
            if query.structured_conditions.get("clause_type"):
                clause_query = clause_query.where(
                    SilverClauseSpan.clause_type == query.structured_conditions["clause_type"]
                )
            
            # Apply text search on clause content
            if query.keywords:
                keyword_conditions = []
                for keyword in query.keywords:
                    keyword_conditions.append(SilverClauseSpan.snippet.ilike(f'%{keyword}%'))
                clause_query = clause_query.where(or_(*keyword_conditions))
            
            result = await db.execute(clause_query.limit(limit))
            clauses = result.scalars().all()
            
            for clause in clauses:
                highlights = [f"Clause type: {clause.clause_type}"]
                
                # Add keyword highlights
                for keyword in query.keywords:
                    if keyword in clause.snippet.lower():
                        highlights.append(f"Keyword: {keyword}")
                
                result_item = SearchResult(
                    document_id=clause.contract.contract_id,
                    title=f"{clause.contract.filename} - {clause.clause_name}",
                    document_type="clause",
                    content_snippet=clause.snippet,
                    relevance_score=clause.confidence,
                    match_type="clause",
                    highlights=highlights,
                    metadata={
                        "clause_type": clause.clause_type,
                        "clause_name": clause.clause_name,
                        "confidence": clause.confidence,
                        "document_title": clause.contract.filename,
                        "risk_indicators": clause.risk_indicators
                    }
                )
                
                results.append(result_item)
            
            # Sort by confidence
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            return results[:limit]
    
    async def _hybrid_search(self, query: SearchQuery, user_id: str, limit: int) -> List[SearchResult]:
        """
        General hybrid search combining semantic and keyword search
        """
        async for db in get_operational_db():
            results = []
            
            # Get user documents
            base_query = select(BronzeContract).options(
                selectinload(BronzeContract.text_raw),
                selectinload(BronzeContract.chunks),
                selectinload(BronzeContract.scores)
            ).where(
                BronzeContract.owner_user_id == user_id
            )
            
            # Apply document type filters
            if query.document_types:
                document_type_conditions = []
                for doc_type in query.document_types:
                    document_type_conditions.append(BronzeContract.document_category == doc_type)
                    document_type_conditions.append(BronzeContract.document_type.ilike(f'%{doc_type}%'))
                base_query = base_query.where(or_(*document_type_conditions))
            
            # Apply industry type filters
            if query.industry_types:
                industry_conditions = []
                for industry in query.industry_types:
                    industry_conditions.append(BronzeContract.industry_type.ilike(f'%{industry}%'))
                base_query = base_query.where(or_(*industry_conditions))
            
            result = await db.execute(base_query.limit(limit * 2))
            contracts = result.scalars().all()
            
            for contract in contracts:
                if not contract.text_raw:
                    continue
                
                # Calculate keyword match score
                text_content = contract.text_raw.raw_text.lower()
                keyword_score = 0
                matched_keywords = []
                
                for keyword in query.keywords:
                    if keyword in text_content:
                        keyword_score += 1
                        matched_keywords.append(keyword)
                
                keyword_score = keyword_score / len(query.keywords) if query.keywords else 0
                
                # Calculate semantic similarity if we have embeddings
                semantic_score = 0
                if contract.chunks:
                    semantic_score = await self._calculate_semantic_similarity(
                        query.semantic_query, contract.chunks[:3]
                    )
                
                # Combine scores (weighted hybrid)
                combined_score = (semantic_score * 0.6) + (keyword_score * 0.4)
                
                # Skip low-relevance results
                if combined_score < 0.1:
                    continue
                
                # Create highlights
                highlights = []
                for keyword in matched_keywords:
                    highlights.append(f"Keyword: {keyword}")
                
                if contract.scores and contract.scores.risk_level in ["high", "critical"]:
                    highlights.append(f"Risk: {contract.scores.risk_level}")
                
                snippet = text_content[:300] + "..." if len(text_content) > 300 else text_content
                
                result_item = SearchResult(
                    document_id=contract.contract_id,
                    title=contract.filename,
                    document_type=contract.document_category or "document",
                    content_snippet=snippet,
                    relevance_score=combined_score,
                    match_type="hybrid",
                    highlights=highlights,
                    metadata={
                        "keyword_score": keyword_score,
                        "semantic_score": semantic_score,
                        "matched_keywords": matched_keywords,
                        "risk_level": contract.scores.risk_level if contract.scores else "unknown",
                        "created_at": contract.created_at.isoformat() if contract.created_at else None,
                        "document_type": contract.document_type,
                        "document_category": contract.document_category,
                        "industry_type": contract.industry_type,
                        "user_description": contract.user_description
                    }
                )
                
                results.append(result_item)
            
            # Sort by combined relevance score
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            return results[:limit]
    
    async def _calculate_semantic_similarity(self, query: str, chunks: List[SilverChunk]) -> float:
        """
        Calculate semantic similarity between query and document chunks
        """
        try:
            # Generate query embedding
            query_result = await llm_factory.generate_embedding(text=query)
            query_embedding = query_result["embedding"]
            
            max_similarity = 0.0
            
            for chunk in chunks:
                if chunk.embedding:
                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(query_embedding, chunk.embedding)
                    max_similarity = max(max_similarity, similarity)
            
            return max_similarity
            
        except Exception as e:
            logger.warning(f"Semantic similarity calculation failed: {e}")
            return 0.5  # Default similarity
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            import math
            
            # Ensure vectors are same length
            if len(vec1) != len(vec2):
                return 0.0
            
            # Calculate dot product
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            
            # Calculate magnitudes
            magnitude1 = math.sqrt(sum(a * a for a in vec1))
            magnitude2 = math.sqrt(sum(a * a for a in vec2))
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            return dot_product / (magnitude1 * magnitude2)
            
        except Exception:
            return 0.0
    
    async def _generate_suggestions(self, query: str, results: List[SearchResult]) -> List[str]:
        """
        Generate search suggestions based on query and results
        """
        suggestions = []
        
        # If no results, suggest broader search
        if not results:
            suggestions.append("Try using broader search terms")
            suggestions.append("Check spelling and try synonyms")
            suggestions.append("Use filters to narrow down document types")
        
        # Suggest related searches based on query
        query_lower = query.lower()
        
        if "contract" in query_lower:
            suggestions.extend([
                "Search for 'high risk contracts'",
                "Find 'contracts with liability clauses'",
                "Show 'recent contract agreements'"
            ])
        
        if "invoice" in query_lower:
            suggestions.extend([
                "Find 'invoices above $10000'",
                "Search 'invoices missing PO reference'",
                "Show 'overdue payment invoices'"
            ])
        
        if "risk" in query_lower:
            suggestions.extend([
                "Show 'critical risk documents'",
                "Find 'liability risks'",
                "Search 'compliance issues'"
            ])
        
        return suggestions[:5]  # Limit to 5 suggestions

# Global advanced search service instance
advanced_search_service = AdvancedSearchService()
