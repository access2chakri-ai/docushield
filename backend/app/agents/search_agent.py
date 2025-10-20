"""
Document Search Agent - Production Ready with Privacy Protection
Enterprise-grade semantic and keyword search with AWS Bedrock AgentCore compatibility
Enhanced with privacy-safe processing to prevent PII exposure to LLMs
"""
import json
import logging
import asyncio
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from .base_agent import BaseAgent, AgentContext, AgentStatus
from app.services.llm_factory import LLMTask
from app.services.privacy_safe_llm import privacy_safe_llm, safe_llm_completion
from app.services.mcp_integration import mcp_service, MCPResult
from app.utils.privacy_safe_processing import privacy_processor, ensure_privacy_safe_content

logger = logging.getLogger(__name__)

class DocumentSearchAgent(BaseAgent):
    """
    Production document search agent with AWS Bedrock AgentCore compatibility
    Handles semantic search, keyword search, and document retrieval with high performance
    """
    
    def __init__(self):
        super().__init__("document_search_agent", "2.0.0")
        
        # Production configuration with minimal env vars
        self.config = {
            'semantic_threshold': float(os.getenv("SEMANTIC_THRESHOLD", "0.05")),
            'keyword_threshold': float(os.getenv("KEYWORD_THRESHOLD", "0.3")),
            'max_results': int(os.getenv("MAX_RESULTS", "20")),
            'max_chunks': int(os.getenv("MAX_CHUNKS", "10")),
            'max_documents': int(os.getenv("MAX_DOCUMENTS", "50"))
        }
        
        # Best practice defaults (no env vars needed)
        self.fuzzy_threshold = 0.7
        self.fuzzy_penalty = 0.8
        self.short_query_limit = 3
        self.min_fuzzy_length = 3
        self.max_char_diff = 2
        self.exact_score = 1.0
        self.partial_score = 0.5
        
        # Query type indicators
        self.semantic_indicators = ["explain", "what", "how", "why", "meaning", "understand", "describe"]
        self.keyword_indicators = ["find", "show", "list", "where", "clause", "section"]
        self.external_indicators = ["recent", "latest", "current", "news", "regulation", "law", "precedent"]
        
        # Keep minimal patterns for fallback only
        self.financial_patterns = {
            'monetary_amounts': [
                r'\$[\d,]+(?:\.\d{2})?',  # $1,000.00
                r'[\d,]+(?:\.\d{2})?\s*dollars?',  # 1000 dollars
            ],
            'financial_terms': [
                r'payment', r'cost', r'fee', r'amount', r'money', r'dollar'
            ]
        }
        
        # Business query patterns for structured searches
        self.business_patterns = {
            'missing_signatures': [
                r'documents?\s+with\s+missing\s+signatures?',
                r'unsigned\s+documents?',
                r'documents?\s+without\s+signatures?',
                r'no\s+signatures?'
            ],
            'expiring_contracts': [
                r'contracts?\s+expiring\s+soon',
                r'contracts?\s+about\s+to\s+expire',
                r'expiring\s+agreements?',
                r'contracts?\s+ending\s+soon'
            ],
            'recent_uploads': [
                r'recent(ly)?\s+uploaded\s+documents?',
                r'new\s+documents?',
                r'latest\s+uploads?',
                r'recently\s+added\s+documents?'
            ],
            'high_risk_documents': [
                r'high\s+risk\s+documents?',
                r'risky\s+contracts?',
                r'dangerous\s+agreements?',
                r'problematic\s+documents?'
            ],
            'pending_review': [
                r'documents?\s+pending\s+review',
                r'unreviewed\s+documents?',
                r'documents?\s+awaiting\s+review',
                r'needs?\s+review'
            ]
        }
        
        logger.info(f"DocumentSearchAgent initialized - semantic: {self.config['semantic_threshold']}, "
                   f"keyword: {self.config['keyword_threshold']}, max: {self.config['max_results']}")
    
    def _extract_response_text(self, response) -> str:
        """Helper method to extract text from LLM response regardless of format"""
        if isinstance(response, tuple):
            # Handle tuple return type (result_list, call_id)
            if len(response) > 0 and isinstance(response[0], list) and len(response[0]) > 0:
                return response[0][0].get("content", "") if isinstance(response[0][0], dict) else str(response[0][0])
            return ""
        elif isinstance(response, str):
            return response
        elif isinstance(response, dict):
            return response.get("content", "")
        else:
            return str(response) if response is not None else ""
    
    async def _execute_analysis(self, context: AgentContext):
        """
        Execute search analysis based on query type and context
        Supports both single-document and multi-document search
        """
        try:
            if not context.query:
                logger.error("❌ No query provided to search agent")
                return self.create_result(
                    status=AgentStatus.FAILED,
                    error_message="Search query is required"
                )
            
            logger.info(f"🔍 Search agent executing analysis for query: '{context.query}', contract_id: '{context.contract_id}'")
            
            # Check if this is a multi-document search (no contract_id specified)
            if not context.contract_id or context.contract_id == "all":
                logger.info("📚 Multi-document search detected")
                result = await self._multi_document_search(context)
                logger.info(f"📚 Multi-document search completed with {len(result.findings) if result and result.findings else 0} findings")
                return result
            
            # Single document search with LLM-powered strategy selection
            # Use LLM to determine optimal search strategy
            search_type = await self._determine_search_type(context.query)
            logger.info(f"🎯 LLM determined search type: {search_type} for query '{context.query}'")
            
            if search_type == "business":
                logger.info("💼 Executing intelligent business query search")
                return await self._business_search(context)
            elif search_type == "semantic":
                logger.info("🧠 Executing enhanced semantic search")
                return await self._semantic_search(context)
            elif search_type == "keyword":
                logger.info("🔤 Executing smart keyword search")
                return await self._keyword_search(context)
            else:  # hybrid
                logger.info("🔀 Executing intelligent hybrid search")
                return await self._hybrid_search(context)
                
        except Exception as e:
            logger.error(f"Search execution failed: {e}")
            return self.create_result(
                status=AgentStatus.FAILED,
                error_message=str(e)
            )
    
    async def _determine_search_type(self, query: str) -> str:
        """Use LLM to determine optimal search strategy based on query analysis"""
        try:
            prompt = f"""
            Analyze this search query and determine the best search strategy.
            
            Query: "{query}"
            
            Choose the optimal search type:
            - "semantic": for conceptual, exploratory, or meaning-based queries
            - "keyword": for specific term searches or exact phrase matching
            - "hybrid": for complex queries that benefit from both approaches
            - "business": for structured business queries (signatures, expiring contracts, etc.)
            
            Consider:
            - Query complexity and intent
            - Whether user wants exact matches or conceptual understanding
            - Domain (legal, financial, employment, etc.)
            
            Return only one word: semantic, keyword, hybrid, or business
            """
            
            response = await self.call_llm_with_tracking(
                prompt=prompt,
                contract_id="search_strategy",
                task_type=LLMTask.ANALYSIS,
                max_tokens=50,
                temperature=0.1
            )
            
            if response and response.strip().lower() in ['semantic', 'keyword', 'hybrid', 'business']:
                return response.strip().lower()
            
        except Exception as e:
            logger.warning(f"LLM search type determination failed: {e}")
        
        # Fallback to rule-based logic
        return self._determine_search_type_fallback(query)
    
    def _determine_search_type_fallback(self, query: str) -> str:
        """Fallback rule-based search type determination"""
        query_lower = query.lower()
        words = query_lower.split()
        
        # Check for business queries first (use fallback for sync method)
        business_type = self._detect_business_query_fallback(query_lower)
        if business_type and business_type != "none":
            return "business"
        
        # Short queries use hybrid for better coverage
        if len(words) <= self.short_query_limit:
            return "hybrid"
        
        # Longer queries use semantic search
        return "semantic"
    
    async def _detect_business_query(self, query: str) -> str:
        """Use LLM to detect business query types intelligently"""
        try:
            prompt = f"""
            Analyze if this is a structured business query and classify it.
            
            Query: "{query}"
            
            Business query types:
            - missing_signatures: documents without signatures
            - expiring_contracts: contracts about to expire
            - recent_uploads: recently added documents
            - high_risk_documents: high-risk or problematic documents
            - pending_review: documents awaiting review
            - none: not a business query
            
            Return only the type name or "none":
            """
            
            response = await self.call_llm_with_tracking(
                prompt=prompt,
                contract_id="business_query_detection",
                task_type=LLMTask.ANALYSIS,
                max_tokens=50,
                temperature=0.1
            )
            
            # Handle both string and tuple return types
            response_text = ""
            if isinstance(response, tuple):
                response_text = response[0][0].get("content", "") if response[0] else ""
            elif isinstance(response, str):
                response_text = response
            elif isinstance(response, dict):
                response_text = response.get("content", "")
            
            if response_text and response_text.strip().lower() != "none":
                business_types = ['missing_signatures', 'expiring_contracts', 'recent_uploads', 'high_risk_documents', 'pending_review']
                detected_type = response_text.strip().lower()
                if detected_type in business_types:
                    return detected_type
            
        except Exception as e:
            logger.warning(f"LLM business query detection failed: {e}")
        
        # Fallback to pattern matching
        return self._detect_business_query_fallback(query)
    
    def _detect_business_query_fallback(self, query: str) -> str:
        """Fallback pattern-based business query detection"""
        import re
        
        for business_type, patterns in self.business_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    return business_type
        return None
    
    async def _detect_financial_query(self, query: str) -> bool:
        """Use LLM to intelligently detect financial/monetary queries"""
        try:
            prompt = f"""
            Determine if this search query is related to financial or monetary content.
            
            Query: "{query}"
            
            Financial queries include:
            - Money amounts, payments, costs, fees
            - Financial terms, budgets, expenses
            - Compensation, salaries, wages
            - Invoices, bills, charges
            - Financial penalties, damages
            - Investment, liability, debt
            
            Return only: true or false
            """
            
            response = await self.call_llm_with_tracking(
                prompt=prompt,
                contract_id="financial_detection",
                task_type=LLMTask.ANALYSIS,
                max_tokens=10,
                temperature=0.1
            )
            
            if response and response.strip().lower() == "true":
                return True
            elif response and response.strip().lower() == "false":
                return False
            
        except Exception as e:
            logger.warning(f"LLM financial detection failed: {e}")
        
        # Fallback to pattern matching
        return self._detect_financial_query_fallback(query)
    
    def _detect_financial_query_fallback(self, query: str) -> bool:
        """Fallback pattern-based financial query detection"""
        import re
        
        query_lower = query.lower()
        
        # Check for direct financial keywords
        financial_keywords = [
            'dollar', 'dollars', 'amount', 'money', 'cost', 'price', 'fee', 'payment',
            'salary', 'wage', 'compensation', 'revenue', 'profit', 'budget', 'expense',
            'invoice', 'bill', 'charge', 'rate', 'value', 'worth', 'financial', 'monetary'
        ]
        
        # Check for financial keywords
        if any(keyword in query_lower for keyword in financial_keywords):
            return True
        
        # Check for monetary patterns
        for category, patterns in self.financial_patterns.items():
            for pattern in patterns[:5]:  # Limit patterns for fallback
                if re.search(pattern, query, re.IGNORECASE):
                    return True
        
        return False
    
    async def _extract_financial_highlights(self, query: str, content: str) -> List[Dict[str, Any]]:
        """Use LLM to extract financial-related highlights from content"""
        try:
            # PRIVACY-SAFE: Don't send document content to LLM
            # Instead, use LLM to generate financial term patterns based on query only
            prompt = f"""
            Based on this search query, generate a list of financial terms to look for in documents.
            
            Query: "{query}"
            
            Generate relevant financial search terms including:
            - Dollar amounts and currency references
            - Payment-related terms
            - Financial concepts and terminology
            - Cost and pricing terms
            
            Return 10-15 search terms separated by commas (no document content needed):
            """
            
            response = await self.call_llm_with_tracking(
                prompt=prompt,
                contract_id="financial_highlighting",
                task_type=LLMTask.ANALYSIS,
                max_tokens=200,
                temperature=0.1
            )
            
            if response and response.strip():
                highlights = []
                # Parse LLM-generated search terms (no document content was sent)
                financial_terms = [term.strip() for term in response.split(',') if term.strip()]
                
                # Search for these terms in content locally (privacy-safe)
                import re
                for term in financial_terms:
                    if term.lower() in content.lower():
                        pattern = re.compile(re.escape(term), re.IGNORECASE)
                        for match in pattern.finditer(content):
                            highlights.append({
                                "start_offset": match.start(),
                                "end_offset": match.end(),
                                "matched_text": match.group(),
                                "context": content[max(0, match.start()-50):match.end()+50],
                                "highlight_type": "financial",
                                "category": "llm_generated_terms",
                                "confidence": 0.9,
                                "match_explanation": f"Financial term '{match.group()}' found using LLM-generated search terms"
                            })
                
                return self._deduplicate_highlights(highlights)
            
        except Exception as e:
            logger.warning(f"LLM financial highlighting failed: {e}")
        
        # Fallback to pattern matching
        return self._extract_financial_highlights_fallback(query, content)
    
    def _extract_financial_highlights_fallback(self, query: str, content: str) -> List[Dict[str, Any]]:
        """Fallback financial highlighting using minimal patterns"""
        import re
        
        highlights = []
        
        # Use minimal patterns for fallback
        for category, patterns in self.financial_patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    highlights.append({
                        "start_offset": match.start(),
                        "end_offset": match.end(),
                        "matched_text": match.group(),
                        "context": content[max(0, match.start()-50):match.end()+50],
                        "highlight_type": "financial",
                        "category": category,
                        "confidence": 0.7,
                        "match_explanation": f"Financial pattern match: {match.group()}"
                    })
        
        return self._deduplicate_highlights(highlights)
    
    def _deduplicate_highlights(self, highlights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate and overlapping highlights"""
        if not highlights:
            return highlights
        
        # Sort by position
        sorted_highlights = sorted(highlights, key=lambda x: x["start_offset"])
        
        filtered_highlights = []
        for current in sorted_highlights:
            # Check for overlaps with existing highlights
            should_add = True
            for existing in filtered_highlights:
                # Check if they overlap significantly (more than 50% overlap)
                overlap_start = max(current["start_offset"], existing["start_offset"])
                overlap_end = min(current["end_offset"], existing["end_offset"])
                
                if overlap_start < overlap_end:
                    overlap_length = overlap_end - overlap_start
                    current_length = current["end_offset"] - current["start_offset"]
                    existing_length = existing["end_offset"] - existing["start_offset"]
                    
                    # If more than 50% overlap, skip this highlight
                    if overlap_length > min(current_length, existing_length) * 0.5:
                        should_add = False
                        break
            
            if should_add:
                filtered_highlights.append(current)
        
        return filtered_highlights
    
    async def _expand_query_for_semantic_search(self, query: str) -> str:
        """Expand query with synonyms and related terms for better semantic matching"""
        try:
            prompt = f"""
            Expand this search query with relevant synonyms, related terms, and legal/business concepts to improve semantic search.
            
            Original query: "{query}"
            
            Provide an expanded version that includes:
            - Synonyms and alternative phrasings
            - Related legal/business terms
            - Common variations
            
            Keep it concise and relevant. Return only the expanded query:
            """
            
            response = await self.call_llm_with_tracking(
                prompt=prompt,
                contract_id="query_expansion",
                task_type=LLMTask.ANALYSIS,
                max_tokens=100,
                temperature=0.3
            )
            
            if response and response.strip():
                expanded = response.strip()
                # Ensure we don't make it too long
                if len(expanded) > len(query) * 3:
                    return query
                return expanded
            
        except Exception as e:
            logger.warning(f"Query expansion failed: {e}")
        
        return query
    
    def _merge_and_rank_chunks(self, primary_chunks: List[Tuple[Any, float]], expanded_chunks: List[Tuple[Any, float]]) -> List[Tuple[Any, float]]:
        """Merge and rank chunks from multiple searches, removing duplicates"""
        try:
            # Combine all chunks
            all_chunks = list(primary_chunks) + list(expanded_chunks)
            
            if not all_chunks:
                return []
            
            # Remove duplicates based on chunk content
            seen_content = set()
            unique_chunks = []
            
            for chunk, similarity in all_chunks:
                # Use chunk text as deduplication key
                chunk_text = getattr(chunk, 'chunk_text', str(chunk))[:100]  # First 100 chars
                
                if chunk_text not in seen_content:
                    seen_content.add(chunk_text)
                    unique_chunks.append((chunk, similarity))
            
            # Sort by similarity score (highest first)
            unique_chunks.sort(key=lambda x: x[1], reverse=True)
            
            logger.info(f"🔀 Merged {len(all_chunks)} chunks into {len(unique_chunks)} unique results")
            
            return unique_chunks
            
        except Exception as e:
            logger.warning(f"Chunk merging failed: {e}")
            # Return primary chunks as fallback
            return primary_chunks
    
    async def _generate_no_results_recommendations(self, query: str) -> List[str]:
        """Generate smart recommendations when no results are found"""
        try:
            prompt = f"""
            A user searched for "{query}" but no results were found.
            Provide 3-5 helpful search suggestions or alternative queries they could try.
            
            Focus on:
            - Alternative keywords or phrases
            - Broader or more specific terms
            - Common legal/business terminology
            - Document sections they might check
            
            Return as a simple list, one suggestion per line:
            """
            
            response = await self.call_llm_with_tracking(
                prompt=prompt,
                contract_id="search_recommendations",
                task_type=LLMTask.ANALYSIS,
                max_tokens=200,
                temperature=0.3
            )
            
            if response and response.strip():
                # Split response into lines and clean up
                suggestions = [line.strip() for line in response.strip().split('\n') if line.strip()]
                return suggestions[:5]  # Limit to 5 suggestions
            
        except Exception as e:
            logger.warning(f"Failed to generate search recommendations: {e}")
        
        # Fallback recommendations
        return [
            "Try using broader search terms",
            "Check for alternative spellings or synonyms",
            "Search for related concepts or categories",
            "Use specific document section names",
            "Try keyword search instead of semantic search"
        ]
    
    async def _generate_smart_recommendations(self, query: str, results_count: int) -> List[str]:
        """Generate smart recommendations based on search results"""
        try:
            if results_count == 0:
                return await self._generate_no_results_recommendations(query)
            
            # Simple recommendations based on results count - no LLM needed
            if results_count > 10:
                return [
                    "Try more specific search terms to narrow results",
                    "Use filters to focus on specific document sections",
                    "Search for exact phrases using quotes",
                    "Look for related legal concepts or clauses"
                ]
            else:
                return [
                    "Try broader search terms for more results",
                    "Search for synonyms or related concepts", 
                    "Check different document sections",
                    "Use semantic search for conceptual matches"
                ]
            
        except Exception as e:
            logger.warning(f"Failed to generate smart recommendations: {e}")
            return [
                "Try different search terms",
                "Check document sections",
                "Use broader or more specific queries"
            ]
    
    async def _semantic_search(self, context: AgentContext):
        """Enhanced semantic search using LLM analysis and vector embeddings"""
        try:
            logger.info(f"🧠 Starting enhanced semantic search for query: '{context.query}' in contract: {context.contract_id}")
            
            # Use LLM to analyze and expand query for better semantic matching
            expanded_query = await self._expand_query_for_semantic_search(context.query)
            
            # Perform vector search with both original and expanded queries
            primary_chunks = await self.semantic_search_chunks(
                query=context.query,
                contract_id=context.contract_id,
                limit=self.config['max_chunks'],
                similarity_threshold=self.config['semantic_threshold'],
                user_id=context.user_id
            )
            
            # Search with expanded query if different
            expanded_chunks = []
            if expanded_query != context.query:
                expanded_chunks = await self.semantic_search_chunks(
                    query=expanded_query,
                    contract_id=context.contract_id,
                    user_id=context.user_id,
                    limit=self.config['max_chunks'] // 2,
                    similarity_threshold=self.config['semantic_threshold'] * 0.9
                )
            
            # Combine and deduplicate results using cosine similarity
            all_chunks = self._merge_and_rank_chunks(primary_chunks, expanded_chunks)
            
            logger.info(f"🔍 Enhanced semantic search returned {len(all_chunks)} results")
            
            if not all_chunks:
                # Generate smart recommendations using LLM
                smart_recommendations = await self._generate_no_results_recommendations(context.query)
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
                    recommendations=smart_recommendations,
                    llm_calls=2,
                    data_sources=["embeddings", "llm_analysis"]
                )
            
            # Process results with LLM-enhanced highlighting
            findings = []
            llm_calls = 2  # Query expansion + recommendations
            is_financial_query = await self._detect_financial_query(context.query)
            
            for chunk, similarity in all_chunks:
                # Use LLM for intelligent highlighting
                semantic_highlights = await self._extract_semantic_highlights(context.query, chunk.chunk_text)
                llm_calls += 1
                
                # Add financial highlights if this is a financial query
                financial_highlights = []
                if is_financial_query:
                    financial_highlights = await self._extract_financial_highlights(context.query, chunk.chunk_text)
                
                # Combine all highlights for frontend
                all_highlights = semantic_highlights.copy()
                if financial_highlights:
                    all_highlights.extend([h["matched_text"] for h in financial_highlights])
                
                finding = {
                    "type": "semantic_match",
                    "title": f"Semantic match (similarity: {similarity:.2f})",
                    "severity": "info",
                    "confidence": similarity,
                    "content": chunk.chunk_text[:500],
                    "similarity_score": similarity,
                    "chunk_order": chunk.chunk_order,
                    "chunk_id": chunk.chunk_id,
                    "highlights": all_highlights,  # LLM-enhanced highlights
                    "semantic_highlights": semantic_highlights,
                    "expanded_query": expanded_query if expanded_query != context.query else None,
                    "match_explanation": f"Content semantically similar to '{context.query}' (cosine similarity: {similarity:.1%})"
                }
                
                # Add financial highlights if found
                if financial_highlights:
                    finding["financial_highlights"] = financial_highlights
                    finding["has_financial_content"] = True
                    finding["match_explanation"] += f" - Contains {len(financial_highlights)} financial terms"
                
                findings.append(finding)
            
            # Generate smart recommendations using LLM
            recommendations = await self._generate_smart_recommendations(context.query, len(all_chunks))
            llm_calls += 1
            
            return self.create_result(
                status=AgentStatus.COMPLETED,
                confidence=0.8 + (len(all_chunks) / self.config['max_chunks']) * 0.2,
                findings=findings,
                recommendations=recommendations,
                llm_calls=llm_calls,
                data_sources=["silver_chunks", "embeddings", "llm_analysis"]
            )
            
        except Exception as e:
            logger.error(f"Enhanced semantic search failed: {e}")
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
            
            # Use LLM to analyze query and expand search terms intelligently
            is_financial_query = await self._detect_financial_query(context.query)
            expanded_terms = await self._expand_search_terms(context.query, is_financial_query)
            query_terms = expanded_terms
            
            # If it's a financial query, expand search terms to include financial synonyms
            if is_financial_query:
                financial_synonyms = {
                    'dollar': ['dollars', 'usd', 'currency', 'money'],
                    'dollars': ['dollar', 'usd', 'currency', 'money'],
                    'amount': ['sum', 'total', 'value', 'cost', 'price', 'fee'],
                    'money': ['dollars', 'currency', 'funds', 'cash', 'payment'],
                    'cost': ['price', 'fee', 'charge', 'expense', 'amount'],
                    'price': ['cost', 'fee', 'charge', 'rate', 'amount'],
                    'payment': ['fee', 'charge', 'cost', 'amount', 'sum'],
                    'fee': ['cost', 'charge', 'payment', 'amount'],
                    'total': ['sum', 'amount', 'aggregate', 'grand total'],
                    'sum': ['total', 'amount', 'aggregate']
                }
                
                expanded_terms = set(query_terms)
                for term in query_terms:
                    if term in financial_synonyms:
                        expanded_terms.update(financial_synonyms[term])
                query_terms = list(expanded_terms)
            
            # Find keyword matches with fuzzy matching for typos
            matches = []
            lines = text.split('\n')
            
            for i, line in enumerate(lines):
                line_lower = line.lower()
                line_words = line_lower.split()
                
                # Check for exact matches first
                exact_match = any(term in line_lower for term in query_terms)
                
                # For financial queries, also check for monetary patterns
                financial_match = False
                if is_financial_query and not exact_match:
                    import re
                    for category, patterns in self.financial_patterns.items():
                        for pattern in patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                financial_match = True
                                break
                        if financial_match:
                            break
                
                # Check for fuzzy matches with production defaults
                fuzzy_match = False
                if not exact_match and not financial_match:
                    for query_term in query_terms:
                        if len(query_term) > self.min_fuzzy_length:
                            for line_word in line_words:
                                if (len(line_word) > self.min_fuzzy_length and 
                                    abs(len(query_term) - len(line_word)) <= self.max_char_diff):
                                    # Character overlap check
                                    overlap = len(set(query_term) & set(line_word))
                                    if overlap >= min(len(query_term), len(line_word)) * self.fuzzy_threshold:
                                        fuzzy_match = True
                                        break
                        if fuzzy_match:
                            break
                
                if exact_match or fuzzy_match or financial_match:
                    # Get context around match
                    start_line = max(0, i - 2)
                    end_line = min(len(lines), i + 3)
                    context_text = '\n'.join(lines[start_line:end_line])
                    
                    relevance = self._calculate_keyword_relevance(line_lower, query_terms)
                    
                    # Boost relevance for financial matches in financial queries
                    if financial_match and is_financial_query:
                        relevance = max(relevance, 0.8)  # High relevance for financial pattern matches
                    elif fuzzy_match and not exact_match:
                        relevance *= self.fuzzy_penalty
                    
                    # Only include matches above threshold
                    if relevance >= self.config['keyword_threshold']:
                        match_type = "exact" if exact_match else ("financial" if financial_match else "fuzzy")
                        matches.append({
                            "line_number": i + 1,
                            "matched_line": line.strip(),
                            "context": context_text,
                            "relevance": relevance,
                            "match_type": match_type,
                            "is_financial": financial_match or (is_financial_query and exact_match)
                        })
            
            # Sort by relevance
            matches.sort(key=lambda x: x["relevance"], reverse=True)
            matches = matches[:self.config['max_results']]
            
            # Create findings
            findings = []
            for match in matches:
                match_type = match.get("match_type", "exact")
                is_financial_match = match.get("is_financial", False)
                
                # Extract exactly what keywords were matched
                matched_keywords = self._extract_matched_keywords(context.query, match["matched_line"])
                
                # Create appropriate title based on match type
                if match_type == "financial":
                    title = f"Financial content match on line {match['line_number']}"
                elif match_type == "fuzzy":
                    title = f"Fuzzy keyword match on line {match['line_number']}"
                else:
                    title = f"Exact keyword match on line {match['line_number']}"
                
                # Prepare highlights for frontend
                all_highlights = matched_keywords.copy()
                
                finding = {
                    "type": "keyword_match",
                    "title": title,
                    "severity": "info",
                    "confidence": match["relevance"],
                    "content": match["context"],
                    "line_number": match["line_number"],
                    "matched_text": match["matched_line"],
                    "match_type": match_type,
                    "matched_keywords": matched_keywords,
                    "highlights": all_highlights,  # For frontend highlighting
                    "is_financial": is_financial_match
                }
                
                # Add financial highlights if this is a financial query
                if is_financial_query:
                    financial_highlights = await self._extract_financial_highlights(context.query, match["context"])
                    if financial_highlights:
                        finding["financial_highlights"] = financial_highlights
                        finding["has_financial_content"] = True
                        # Add financial terms to highlights
                        finding["highlights"].extend([h["matched_text"] for h in financial_highlights])
                
                # Create appropriate match explanation
                if match_type == "financial":
                    finding["match_explanation"] = f"Found financial content related to '{context.query}'"
                elif match_type == "fuzzy":
                    finding["match_explanation"] = f"Found fuzzy matches for: {', '.join(matched_keywords)}"
                else:
                    finding["match_explanation"] = f"Found exact matches for: {', '.join(matched_keywords)}"
                
                if is_financial_match and len(finding.get("financial_highlights", [])) > 0:
                    finding["match_explanation"] += f" - Contains {len(finding['financial_highlights'])} financial terms"
                
                findings.append(finding)
            
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
    
    async def _business_search(self, context: AgentContext):
        """Execute business logic queries like missing signatures, expiring contracts, etc."""
        try:
            business_type = await self._detect_business_query(context.query.lower())
            if not business_type or business_type == "none":
                # Fallback to hybrid search if business type not detected
                return await self._hybrid_search(context)
            
            logger.info(f"💼 Executing business query: {business_type}")
            
            # Import database models
            from sqlalchemy import select, and_, or_, func
            from sqlalchemy.orm import selectinload
            from app.database import get_operational_db
            from app.models import BronzeContract, GoldContractScore
            from datetime import datetime, timedelta
            
            async for db in get_operational_db():
                findings = []
                
                if business_type == 'missing_signatures':
                    # Find documents without signatures
                    query = select(BronzeContract).options(
                        selectinload(BronzeContract.scores)
                    ).where(
                        and_(
                            BronzeContract.owner_user_id == context.user_id,
                            or_(
                                BronzeContract.signature_status == 'unsigned',
                                BronzeContract.signature_status.is_(None),
                                BronzeContract.signature_count == 0
                            )
                        )
                    ).limit(self.config['max_results'])
                    
                elif business_type == 'expiring_contracts':
                    # Find contracts expiring in next 30 days
                    thirty_days = datetime.now() + timedelta(days=30)
                    query = select(BronzeContract).options(
                        selectinload(BronzeContract.scores)
                    ).where(
                        and_(
                            BronzeContract.owner_user_id == context.user_id,
                            BronzeContract.expiry_date.is_not(None),
                            BronzeContract.expiry_date <= thirty_days,
                            BronzeContract.expiry_date >= datetime.now()
                        )
                    ).order_by(BronzeContract.expiry_date).limit(self.config['max_results'])
                    
                elif business_type == 'recent_uploads':
                    # Find recently uploaded documents (last 7 days)
                    seven_days_ago = datetime.now() - timedelta(days=7)
                    query = select(BronzeContract).options(
                        selectinload(BronzeContract.scores)
                    ).where(
                        and_(
                            BronzeContract.owner_user_id == context.user_id,
                            BronzeContract.created_at >= seven_days_ago
                        )
                    ).order_by(BronzeContract.created_at.desc()).limit(self.config['max_results'])
                    
                elif business_type == 'high_risk_documents':
                    # Find high risk documents
                    query = select(BronzeContract).options(
                        selectinload(BronzeContract.scores)
                    ).where(
                        and_(
                            BronzeContract.owner_user_id == context.user_id,
                            BronzeContract.scores.has(
                                or_(
                                    GoldContractScore.risk_level == 'high',
                                    GoldContractScore.risk_level == 'critical',
                                    GoldContractScore.overall_score >= 0.7
                                )
                            )
                        )
                    ).limit(self.config['max_results'])
                    
                elif business_type == 'pending_review':
                    # Find documents pending review
                    query = select(BronzeContract).options(
                        selectinload(BronzeContract.scores)
                    ).where(
                        and_(
                            BronzeContract.owner_user_id == context.user_id,
                            or_(
                                BronzeContract.review_status == 'pending',
                                BronzeContract.review_status.is_(None),
                                BronzeContract.reviewed_at.is_(None)
                            )
                        )
                    ).limit(self.config['max_results'])
                    
                else:
                    # Fallback to hybrid search
                    return await self._hybrid_search(context)
                
                # Execute query
                result = await db.execute(query)
                contracts = result.scalars().all()
                
                # Convert to findings
                for contract in contracts:
                    finding_data = {
                        "type": f"business_{business_type}",
                        "title": f"Business Query Result: {contract.filename}",
                        "severity": "info",
                        "confidence": 0.95,  # High confidence for business queries
                        "content": f"Document: {contract.filename}",
                        "document_id": contract.contract_id,
                        "document_title": contract.filename,
                        "document_type": contract.document_category or "document",
                        "created_at": contract.created_at.isoformat() if contract.created_at else None,
                        "business_query_type": business_type
                    }
                    
                    # Add specific business context
                    if business_type == 'missing_signatures':
                        finding_data["match_explanation"] = f"Document missing signatures (status: {contract.signature_status or 'unknown'})"
                    elif business_type == 'expiring_contracts':
                        finding_data["match_explanation"] = f"Contract expires: {contract.expiry_date}"
                        finding_data["expiry_date"] = contract.expiry_date.isoformat() if contract.expiry_date else None
                    elif business_type == 'recent_uploads':
                        finding_data["match_explanation"] = f"Recently uploaded: {contract.created_at}"
                    elif business_type == 'high_risk_documents':
                        risk_info = "High risk document"
                        if contract.scores:
                            risk_info = f"Risk level: {contract.scores.risk_level}, Score: {contract.scores.overall_score}"
                        finding_data["match_explanation"] = risk_info
                        finding_data["risk_level"] = contract.scores.risk_level if contract.scores else "unknown"
                        finding_data["risk_score"] = contract.scores.overall_score if contract.scores else None
                    elif business_type == 'pending_review':
                        finding_data["match_explanation"] = f"Pending review (status: {contract.review_status or 'not reviewed'})"
                    
                    findings.append(finding_data)
                
                # Generate recommendations
                recommendations = []
                if business_type == 'missing_signatures':
                    recommendations = [
                        f"Found {len(findings)} documents missing signatures",
                        "Review and obtain required signatures",
                        "Check signature requirements for each document"
                    ]
                elif business_type == 'expiring_contracts':
                    recommendations = [
                        f"Found {len(findings)} contracts expiring soon",
                        "Review expiration dates and renewal requirements",
                        "Contact relevant parties for renewals"
                    ]
                elif business_type == 'recent_uploads':
                    recommendations = [
                        f"Found {len(findings)} recently uploaded documents",
                        "Review new documents for completeness",
                        "Ensure proper categorization and processing"
                    ]
                elif business_type == 'high_risk_documents':
                    recommendations = [
                        f"Found {len(findings)} high-risk documents",
                        "Review risk factors and mitigation strategies",
                        "Consider legal consultation for high-risk items"
                    ]
                elif business_type == 'pending_review':
                    recommendations = [
                        f"Found {len(findings)} documents pending review",
                        "Prioritize review of pending documents",
                        "Assign reviewers and set deadlines"
                    ]
                
                return self.create_result(
                    status=AgentStatus.COMPLETED,
                    confidence=0.95,
                    findings=findings,
                    recommendations=recommendations,
                    llm_calls=0,  # No LLM calls for business queries
                    data_sources=["bronze_contract", "gold_contract_score"]
                )
                
        except Exception as e:
            logger.error(f"Business search failed: {e}")
            return self.create_result(
                status=AgentStatus.FAILED,
                error_message=f"Business search error: {e}"
            )
    
    async def _hybrid_search(self, context: AgentContext):
        """Combine semantic and keyword search with MCP-enhanced external search"""
        try:
            logger.info(f"🔀 Starting hybrid search for query: '{context.query}'")
            
            # Run internal searches in parallel
            logger.info("🚀 Launching semantic and keyword search tasks in parallel")
            semantic_task = self._semantic_search(context)
            keyword_task = self._keyword_search(context)
            
            # Run MCP-enhanced search if query suggests external context would be helpful
            mcp_task = None
            if self._should_use_external_search(context.query):
                mcp_task = self._mcp_enhanced_search(context)
            
            # Gather all results
            tasks = [semantic_task, keyword_task]
            if mcp_task:
                tasks.append(mcp_task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            semantic_result = results[0] if not isinstance(results[0], Exception) else None
            keyword_result = results[1] if not isinstance(results[1], Exception) else None
            mcp_result = results[2] if len(results) > 2 and not isinstance(results[2], Exception) else None
            
            # Log results from each search type
            if semantic_result:
                logger.info(f"🧠 Semantic search: {semantic_result.status}, {len(semantic_result.findings)} findings")
            else:
                logger.warning("🧠 Semantic search failed or returned None")
                
            if keyword_result:
                logger.info(f"🔤 Keyword search: {keyword_result.status}, {len(keyword_result.findings)} findings")
            else:
                logger.warning("🔤 Keyword search failed or returned None")
            
            # Combine results
            combined_findings = []
            combined_recommendations = []
            total_llm_calls = 0
            data_sources = ["silver_chunks", "bronze_contract_text_raw", "embeddings"]
            
            if semantic_result and semantic_result.status == AgentStatus.COMPLETED:
                combined_findings.extend(semantic_result.findings)
                combined_recommendations.extend(semantic_result.recommendations)
                total_llm_calls += semantic_result.llm_calls
            
            if keyword_result and keyword_result.status == AgentStatus.COMPLETED:
                combined_findings.extend(keyword_result.findings)
                combined_recommendations.extend(keyword_result.recommendations)
                total_llm_calls += keyword_result.llm_calls
            
            if mcp_result and mcp_result.status == AgentStatus.COMPLETED:
                combined_findings.extend(mcp_result.findings)
                combined_recommendations.extend(mcp_result.recommendations)
                total_llm_calls += mcp_result.llm_calls
                data_sources.extend(["web_search", "news_search", "legal_precedents"])
            
            # Remove duplicates and rank
            unique_findings = self._deduplicate_findings(combined_findings)
            unique_recommendations = list(set(combined_recommendations))
            
            # Higher confidence with external data
            confidence = 0.9 if mcp_result and len(unique_findings) > 0 else (0.85 if len(unique_findings) > 0 else 0.3)
            
            return self.create_result(
                status=AgentStatus.COMPLETED,
                confidence=confidence,
                findings=unique_findings,
                recommendations=unique_recommendations[:10],  # Increased for MCP results
                llm_calls=total_llm_calls,
                data_sources=data_sources
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
            # Exact matches get configured score
            if term in text:
                score += self.exact_score
            
            # Partial matches get configured score
            for word in text_words:
                if term in word:
                    score += self.partial_score
        
        # Normalize by text length
        return min(1.0, score / max(1, len(text_words) / 10))
    
    def _should_use_external_search(self, query: str) -> bool:
        """Determine if query would benefit from external search"""
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in self.external_indicators)
    
    async def _mcp_enhanced_search(self, context: AgentContext):
        """Perform MCP-enhanced search using external sources"""
        try:
            # Extract document context if available
            document_type = context.document_type or "contract"
            industry_type = getattr(context, 'industry_type', None) or "general"
            
            async with mcp_service:
                mcp_results = await mcp_service.search_enhanced_query(
                    query=context.query,
                    document_type=document_type,
                    industry_type=industry_type,
                    include_news=True,
                    include_legal=True
                )
            
            # Process MCP results into findings
            findings = []
            recommendations = []
            
            for source, result in mcp_results.items():
                if not result.success or not result.data:
                    continue
                
                if source == "web_search":
                    findings.append({
                        "type": "external_web_search",
                        "title": f"Found {len(result.data)} relevant web results",
                        "severity": "info",
                        "confidence": 0.7,
                        "description": f"Web search results for: {context.query}",
                        "results": result.data[:5],  # Top 5 results
                        "source_type": "web_search",
                        "query": context.query
                    })
                    recommendations.append("Review external web sources for additional context")
                
                elif source == "news_search":
                    findings.append({
                        "type": "external_news_search",
                        "title": f"Found {len(result.data)} recent news articles",
                        "severity": "info",
                        "confidence": 0.8,
                        "description": f"Recent news related to: {context.query}",
                        "results": result.data[:3],  # Top 3 results
                        "source_type": "news_search",
                        "query": context.query
                    })
                    recommendations.append("Consider recent news developments in your analysis")
                
                elif source == "legal_precedents":
                    findings.append({
                        "type": "legal_precedents_search",
                        "title": f"Found {len(result.data)} legal precedents",
                        "severity": "medium",
                        "confidence": 0.9,
                        "description": f"Legal precedents related to: {context.query}",
                        "results": result.data[:3],  # Top 3 results
                        "source_type": "legal_database",
                        "query": context.query
                    })
                    recommendations.append("Review legal precedents for similar cases")
                
                elif source == "industry_context":
                    findings.append({
                        "type": "industry_context_search",
                        "title": "Industry context analysis",
                        "severity": "info",
                        "confidence": 0.8,
                        "description": f"Industry insights for: {context.query}",
                        "results": result.data,
                        "source_type": "industry_intelligence",
                        "query": context.query
                    })
                    recommendations.append("Consider industry-specific context and trends")
            
            if not findings:
                findings.append({
                    "type": "external_search_no_results",
                    "title": "No external results found",
                    "severity": "info",
                    "confidence": 0.5,
                    "description": f"External search completed but no relevant results found for: {context.query}",
                    "query": context.query
                })
            
            return self.create_result(
                status=AgentStatus.COMPLETED,
                confidence=0.8 if findings else 0.3,
                findings=findings,
                recommendations=recommendations,
                llm_calls=0,  # MCP calls don't count as LLM calls
                data_sources=["web_search", "news_search", "legal_precedents", "industry_intelligence"]
            )
            
        except Exception as e:
            logger.warning(f"MCP-enhanced search failed: {e}")
            return self.create_result(
                status=AgentStatus.COMPLETED,
                confidence=0.3,
                findings=[{
                    "type": "external_search_error",
                    "title": "External search unavailable",
                    "severity": "warning",
                    "confidence": 0.5,
                    "description": "External search services are currently unavailable",
                    "error": str(e)
                }],
                recommendations=["External search unavailable - rely on internal document search"],
                llm_calls=0,
                data_sources=[]
            )
    
    async def _multi_document_search(self, context: AgentContext):
        """
        Search across multiple documents for the user
        Handles semantic queries like "what is the next renewal documents"
        """
        try:
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            from app.database import get_operational_db
            from app.models import BronzeContract
            
            logger.info(f"📚 Starting multi-document search for user: {context.user_id}, query: '{context.query}'")
            
            # Check if this is a business query first
            business_type = await self._detect_business_query(context.query.lower())
            if business_type and business_type != "none":
                logger.info(f"💼 Multi-document business query detected: {business_type}")
                # Create a temporary context for business search
                business_context = AgentContext(
                    contract_id=None,
                    user_id=context.user_id,
                    query=context.query
                )
                return await self._business_search(business_context)
            
            # Get all user documents
            async for db in get_operational_db():
                documents_query = select(BronzeContract).options(
                    selectinload(BronzeContract.text_raw),
                    selectinload(BronzeContract.chunks),
                    selectinload(BronzeContract.scores)
                ).where(
                    BronzeContract.owner_user_id == context.user_id
                ).limit(self.config['max_documents'])  # Configurable limit
                
                result = await db.execute(documents_query)
                contracts = result.scalars().all()
                
                logger.info(f"📚 Found {len(contracts)} documents for user {context.user_id}")
                
                if not contracts:
                    logger.warning("📚 No documents found for user")
                    return self.create_result(
                        status=AgentStatus.COMPLETED,
                        confidence=0.3,
                        findings=[{
                            "type": "no_documents",
                            "title": "No documents found",
                            "severity": "info",
                            "confidence": 0.8,
                            "description": "No documents available for search"
                        }],
                        recommendations=["Upload documents to search"],
                        llm_calls=0,
                        data_sources=[]
                    )
                
                # Search each document
                all_findings = []
                
                for contract in contracts:
                    # Create context for this document
                    doc_context = AgentContext(
                        contract_id=contract.contract_id,
                        user_id=context.user_id,
                        query=context.query
                    )
                    
                    # Determine search type
                    search_type = await self._determine_search_type(context.query)
                    
                    # Perform search based on type
                    if search_type == "semantic":
                        doc_result = await self._semantic_search(doc_context)
                    elif search_type == "keyword":
                        doc_result = await self._keyword_search(doc_context)
                    else:
                        doc_result = await self._hybrid_search(doc_context)
                    
                    # Add document info to findings
                    logger.info(f"📄 Document {contract.filename}: status={doc_result.status}, findings={len(doc_result.findings)}")
                    
                    if doc_result.status == AgentStatus.COMPLETED and doc_result.findings:
                        for finding in doc_result.findings:
                            # Log finding type for debugging
                            logger.info(f"  Finding type: {finding.get('type')}, confidence: {finding.get('confidence', 0)}")
                            
                            # Skip "no_results" findings
                            if finding.get("type") == "no_results":
                                logger.info(f"  Skipping no_results finding")
                                continue
                            
                            # Add document metadata
                            finding["document_id"] = contract.contract_id
                            finding["document_title"] = contract.filename
                            finding["document_type"] = contract.document_category or "document"
                            finding["created_at"] = contract.created_at.isoformat() if contract.created_at else None
                            
                            # Add risk info if available
                            if contract.scores:
                                finding["risk_level"] = contract.scores.risk_level
                                finding["risk_score"] = contract.scores.overall_score
                            
                            all_findings.append(finding)
                
                # Sort by confidence/relevance
                all_findings.sort(key=lambda x: x.get("confidence", 0), reverse=True)
                
                # Deduplicate and limit
                logger.info(f"📊 Before deduplication: {len(all_findings)} findings")
                unique_findings = self._deduplicate_findings(all_findings)
                logger.info(f"📊 After deduplication: {len(unique_findings)} findings")
                
                if not unique_findings:
                    return self.create_result(
                        status=AgentStatus.COMPLETED,
                        confidence=0.3,
                        findings=[{
                            "type": "no_matches",
                            "title": "No matches found",
                            "severity": "info",
                            "confidence": 0.5,
                            "description": f"No matches found for '{context.query}' across {len(contracts)} documents"
                        }],
                        recommendations=[
                            "Try different search terms",
                            "Use more specific keywords",
                            "Check document content"
                        ],
                        llm_calls=0,
                        data_sources=["bronze_contract", "silver_chunks"]
                    )
                
                # Generate recommendations
                recommendations = [
                    f"Found {len(unique_findings)} matches across {len(set(f.get('document_id') for f in unique_findings))} documents",
                    "Review each match for relevance",
                    "Click on document titles to view full content"
                ]
                
                return self.create_result(
                    status=AgentStatus.COMPLETED,
                    confidence=0.85,
                    findings=unique_findings[:20],  # Top 20 results
                    recommendations=recommendations,
                    llm_calls=len(contracts),  # One per document
                    data_sources=["bronze_contract", "silver_chunks", "embeddings"]
                )
                
        except Exception as e:
            logger.error(f"Multi-document search failed: {e}")
            return self.create_result(
                status=AgentStatus.FAILED,
                error_message=f"Multi-document search error: {e}"
            )
    
    def _deduplicate_findings(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate findings and rank by relevance"""
        if not findings:
            return []
        
        seen_content = set()
        unique_findings = []
        
        # Sort by confidence first, but treat 0.0 as a valid confidence
        sorted_findings = sorted(findings, key=lambda x: x.get("confidence", 0), reverse=True)
        
        for finding in sorted_findings:
            # Use a combination of content and document for deduplication
            content = finding.get("content", "")
            doc_id = finding.get("document_id", "")
            
            # Create a more specific key to avoid over-deduplication
            if content:
                content_key = f"{doc_id}:{content[:50]}"  # Shorter content key with doc ID
            else:
                # For findings without content, use title or type
                content_key = f"{doc_id}:{finding.get('title', '')}:{finding.get('type', '')}"
            
            if content_key not in seen_content or len(unique_findings) < 5:  # Always keep at least 5 findings
                seen_content.add(content_key)
                unique_findings.append(finding)
        
        return unique_findings[:20]  # Increased limit to 20 unique findings
    
    async def _extract_semantic_highlights(self, query: str, content: str) -> List[str]:
        """PRIVACY-SAFE: Generate search terms using LLM, then find them locally in content"""
        try:
            # PRIVACY-SAFE: Only send query to LLM, never document content
            prompt = f"""
            Based on this search query, generate relevant search terms to look for in documents.
            
            Query: "{query}"
            
            Generate 8-12 semantically related search terms:
            - For employment queries: employee, work, job, staff, personnel, hire, etc.
            - For financial queries: payment, cost, amount, fee, money, budget, etc.
            - For legal queries: contract, clause, term, agreement, liability, etc.
            - Include synonyms and related concepts
            
            Return terms separated by commas:
            """
            
            response = await self.call_llm_with_tracking(
                prompt=prompt,
                contract_id="semantic_terms_generation",
                task_type=LLMTask.ANALYSIS,
                max_tokens=150,
                temperature=0.2
            )
            
            if response and response.strip():
                # Parse LLM-generated search terms (no document content was sent)
                llm_terms = [term.strip().lower() for term in response.split(',') if term.strip()]
                
                # Search for these terms locally in content (privacy-safe)
                highlights = []
                content_lower = content.lower()
                
                # Add original query words
                query_words = [word.strip().lower() for word in query.split() if len(word.strip()) > 2]
                all_search_terms = list(set(query_words + llm_terms))
                
                # Find terms that exist in content
                import re
                for term in all_search_terms:
                    if term in content_lower:
                        # Find actual case-preserved version
                        pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
                        matches = pattern.findall(content)
                        highlights.extend(matches)
                
                # Remove duplicates while preserving order
                seen = set()
                unique_highlights = []
                for highlight in highlights:
                    if highlight.lower() not in seen:
                        seen.add(highlight.lower())
                        unique_highlights.append(highlight)
                
                return unique_highlights[:10]
            
        except Exception as e:
            logger.warning(f"LLM semantic term generation failed: {e}")
        
        # Fallback to basic query word matching (privacy-safe)
        return self._extract_semantic_highlights_fallback(query, content)
    
    def _extract_semantic_highlights_fallback(self, query: str, content: str) -> List[str]:
        """Privacy-safe fallback highlighting using local patterns only"""
        query_words = query.lower().split()
        highlights = []
        
        # Enhanced concept mapping (local only, no LLM)
        concept_terms = {
            'employment': ['employee', 'employees', 'employment', 'work', 'job', 'staff', 'personnel', 'hire', 'salary', 'wage'],
            'financial': ['payment', 'cost', 'price', 'fee', 'amount', 'money', 'dollar', 'revenue', 'expense', 'budget'],
            'legal': ['contract', 'agreement', 'clause', 'term', 'condition', 'liability', 'breach', 'compliance'],
            'time': ['date', 'day', 'month', 'year', 'period', 'duration', 'deadline']
        }
        
        # Find direct query matches
        import re
        for word in query_words:
            if len(word) > 2 and word in content.lower():
                pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
                matches = pattern.findall(content)
                highlights.extend(matches)
        
        # Find concept-related terms
        for concept, terms in concept_terms.items():
            if any(term in query.lower() for term in [concept] + terms[:3]):
                for term in terms[:5]:
                    if term in content.lower():
                        pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
                        matches = pattern.findall(content)
                        highlights.extend(matches[:2])  # Limit per term
        
        # Remove duplicates
        seen = set()
        unique_highlights = []
        for highlight in highlights:
            if highlight.lower() not in seen:
                seen.add(highlight.lower())
                unique_highlights.append(highlight)
        
        return unique_highlights[:8]
    
    def _extract_matched_keywords(self, query: str, matched_line: str) -> List[str]:
        """Extract exactly which keywords from the query were found in the matched line"""
        query_terms = query.lower().split()
        matched_line_lower = matched_line.lower()
        matched_keywords = []
        
        for term in query_terms:
            if term in matched_line_lower:
                matched_keywords.append(term)
            else:
                # Check for fuzzy matches (simple approach)
                words_in_line = matched_line_lower.split()
                for word in words_in_line:
                    if len(term) > 3 and len(word) > 3:
                        # Simple character overlap check for fuzzy matching
                        overlap = len(set(term) & set(word))
                        if overlap >= min(len(term), len(word)) * 0.7:
                            matched_keywords.append(f"{word}~{term}")  # Show fuzzy match
        
        return matched_keywords
    
    async def _expand_search_terms(self, query: str, is_financial: bool) -> List[str]:
        """Use LLM to intelligently expand search terms"""
        try:
            domain_context = "financial and monetary" if is_financial else "legal and business"
            
            prompt = f"""
            Expand this search query into relevant search terms for {domain_context} documents.
            
            Query: "{query}"
            
            Generate 5-10 search terms that include:
            1. Original query words
            2. Synonyms and related terms
            3. Domain-specific terminology
            4. Alternative phrasings
            
            For employment queries: include employee, work, job, staff, personnel, etc.
            For financial queries: include payment, cost, amount, fee, money, etc.
            For legal queries: include contract, clause, term, agreement, etc.
            
            Return terms separated by commas:
            """
            
            response = await self.call_llm_with_tracking(
                prompt=prompt,
                contract_id="term_expansion",
                task_type=LLMTask.ANALYSIS,
                max_tokens=200,
                temperature=0.2
            )
            
            if response and response.strip():
                # Parse expanded terms
                expanded_terms = [term.strip().lower() for term in response.split(',') if term.strip()]
                # Add original query terms
                original_terms = [term.strip().lower() for term in query.split() if term.strip()]
                
                # Combine and deduplicate
                all_terms = list(set(original_terms + expanded_terms))
                return all_terms[:15]  # Limit to prevent overwhelming
            
        except Exception as e:
            logger.warning(f"Term expansion failed: {e}")
        
        # Fallback to original query terms
        return [term.strip().lower() for term in query.split() if term.strip()]
    
    async def _rank_findings_with_llm(self, query: str, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Use LLM to intelligently rank search findings by relevance"""
        try:
            if len(findings) <= 3:
                return findings  # No need to rank small result sets
            
            # PRIVACY-SAFE: Prepare findings summary without document content
            findings_summary = []
            for i, finding in enumerate(findings[:8]):
                summary = {
                    "index": i,
                    "title": finding.get('title', ''),
                    "confidence": finding.get('confidence', 0.5),
                    "match_type": finding.get('type', 'unknown'),
                    "similarity_score": finding.get('similarity_score', 0),
                    "has_highlights": len(finding.get('highlights', [])) > 0,
                    "highlight_count": len(finding.get('highlights', []))
                }
                findings_summary.append(summary)
            
            prompt = f"""
            Rank these search results by relevance to the query based on metadata only (no document content).
            
            Query: "{query}"
            
            Results to rank (metadata only):
            {json.dumps(findings_summary, indent=2)}
            
            Rank by:
            - Confidence scores and similarity scores
            - Match type relevance to query
            - Number of highlights found
            
            Return the indices of the top 5 most relevant results in order.
            Format as a simple list: [0, 3, 1, 4, 2]
            """
            
            response = await self.call_llm_with_tracking(
                prompt=prompt,
                contract_id="result_ranking",
                task_type=LLMTask.ANALYSIS,
                max_tokens=100,
                temperature=0.1
            )
            
            if response and response.strip():
                try:
                    # Parse the ranking
                    import ast
                    ranking = ast.literal_eval(response.strip())
                    if isinstance(ranking, list) and all(isinstance(i, int) for i in ranking):
                        # Reorder findings based on LLM ranking
                        ranked_findings = []
                        for idx in ranking:
                            if 0 <= idx < len(findings):
                                ranked_findings.append(findings[idx])
                        
                        # Add any remaining findings
                        used_indices = set(ranking)
                        for i, finding in enumerate(findings):
                            if i not in used_indices:
                                ranked_findings.append(finding)
                        
                        return ranked_findings
                except (ValueError, SyntaxError):
                    logger.warning("Failed to parse LLM ranking response")
            
        except Exception as e:
            logger.warning(f"LLM ranking failed: {e}")
        
        # Fallback: sort by confidence
        return sorted(findings, key=lambda x: x.get('confidence', 0), reverse=True)