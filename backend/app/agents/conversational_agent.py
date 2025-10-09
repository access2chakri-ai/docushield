"""
Conversational AI Agent - Enhanced with MCP Integration
Handles any user query using AI agents and MCP services for comprehensive responses
"""
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from .base_agent import BaseAgent, AgentContext, AgentResult, AgentStatus
from app.services.llm_factory import LLMTask, llm_factory
from app.services.privacy_safe_llm import privacy_safe_llm, safe_llm_completion
from app.services.mcp_integration import mcp_service, MCPResult
from app.utils.privacy_safe_processing import privacy_processor, ensure_privacy_safe_content
from app.database import get_operational_db

logger = logging.getLogger(__name__)

class ConversationalAgent(BaseAgent):
    """
    Document-focused conversational agent for DocuShield
    
    PRIMARY PURPOSE: Answer questions about user's documents
    - Document analysis and insights
    - Risk assessment and compliance
    - Contract terms and obligations
    - Document comparison and search
    
    SECONDARY PURPOSE: External knowledge when needed
    - Industry context for document analysis
    - Legal precedents for contract terms
    - Regulatory updates affecting documents
    - Company information for due diligence
    """
    
    def __init__(self):
        super().__init__("conversational_agent", "1.0.0")
        
        # Document-focused query categories
        self.document_query_types = {
            "document_analysis": ["analyze", "review", "check", "examine", "assess", "analysis"],
            "risk_assessment": ["risk", "risks", "dangerous", "problematic", "concern", "high-risk", "risky"],
            "compliance": ["compliant", "compliance", "regulation", "legal", "requirement"],
            "contract_terms": ["terms", "clause", "obligation", "liability", "payment"],
            "document_search": ["find", "search", "locate", "show me", "where"],
            "comparison": ["compare", "difference", "similar", "contrast", "versus"],
            "summary": ["summarize", "summary", "overview", "key points", "main", "overall"],
            "recommendations": ["recommend", "recommendations", "suggest", "suggestions", "advice", "should"],
            "insights": ["insights", "findings", "conclusions", "takeaways", "implications"],
            "document_overview": ["document", "this document", "overall", "general", "entire"]
        }
        
        # External knowledge categories (only when no document context)
        self.external_knowledge_categories = {
            "general_legal": ["law", "legal precedent", "court case", "regulation"],
            "industry_context": ["industry", "market", "business practice", "standard"],
            "company_info": ["company", "corporation", "business", "organization"],
            "current_events": ["news", "recent", "latest", "current", "today"]
        }
    
    async def _execute_analysis(self, context: AgentContext) -> AgentResult:
        """
        Execute document-focused conversational analysis with mode support
        """
        try:
            if not context.query:
                return self._create_failure_result("No query provided")
            
            query = context.query.strip()
            chat_mode = context.metadata.get("chat_mode", "documents") if context.metadata else "documents"
            search_all = context.metadata.get("search_all_documents", False) if context.metadata else False
            
            logger.info(f"🤖 Document Chat Agent processing: {query} (mode: {chat_mode})")
            
            # Handle different chat modes
            if chat_mode == "general":
                # General mode: Allow any questions including external knowledge
                logger.info("📡 General mode: Allowing external knowledge queries")
                query_intent = self._analyze_query_intent(query, context)
                return await self._external_knowledge_response(query, context, query_intent)
            
            elif chat_mode == "all_documents" or search_all:
                # Search across all user documents
                logger.info("📚 All documents mode: Searching across user's documents")
                return await self._search_all_documents_response(query, context)
            
            else:  # chat_mode == "documents" (default)
                # Document-focused mode: Only answer about specific documents
                has_document = context.contract_id and context.contract_id != "no_document"
                
                if not has_document:
                    return await self._document_guidance_response(query, context)
                
                # Determine query intent for document analysis
                query_intent = self._analyze_query_intent(query, context)
                
                # Only allow document-focused queries in this mode
                if query_intent["type"] == "external_knowledge" and not query_intent.get("requires_external"):
                    # Block pure external queries in document mode
                    return self._create_result_with_mode_restriction(query)
                
                # Process document-focused query
                if query_intent["type"] == "document_focused" or query_intent.get("requires_external"):
                    return await self._document_focused_response(query, context, query_intent)
                else:
                    return await self._hybrid_document_response(query, context, query_intent)
                
        except Exception as e:
            logger.error(f"Document chat analysis failed: {e}")
            return self._create_failure_result(str(e))
    
    def _analyze_query_intent(self, query: str, context: AgentContext) -> Dict[str, Any]:
        """Analyze query intent to determine routing strategy"""
        query_lower = query.lower()
        
        intent = {
            "type": "document_focused",  # Default to document focus
            "confidence": 0.8,
            "requires_external": False,
            "document_operation": None,
            "external_category": None,
            "is_analytical": False,  # New flag for analytical queries
            "analysis_type": None
        }
        
        # Check for analytical queries that require overall document understanding
        analytical_patterns = [
            ("summarize", "summary"),
            ("what are the.*risk", "risk_assessment"), 
            ("what.*recommend", "recommendations"),
            ("high-risk", "risk_assessment"),
            ("key.*point", "summary"),
            ("main.*concern", "risk_assessment"),
            ("overall", "document_overview"),
            ("findings", "insights"),
            ("conclusions", "insights")
        ]
        
        for pattern, analysis_type in analytical_patterns:
            import re
            if re.search(pattern, query_lower):
                intent["is_analytical"] = True
                intent["analysis_type"] = analysis_type
                intent["document_operation"] = analysis_type
                intent["confidence"] = 0.95
                
                # Analytical queries benefit from external context for better insights
                if analysis_type in ["risk_assessment", "compliance", "recommendations"]:
                    intent["requires_external"] = True
                
                return intent
        
        # Check for document-focused queries
        for doc_type, keywords in self.document_query_types.items():
            if any(keyword in query_lower for keyword in keywords):
                intent["document_operation"] = doc_type
                intent["confidence"] = 0.9
                
                # Some document operations benefit from external context
                if doc_type in ["compliance", "risk_assessment", "recommendations"]:
                    intent["requires_external"] = True
                
                return intent
        
        # Check for explicit external knowledge requests
        external_indicators = [
            "what is", "who is", "how does", "explain", "tell me about",
            "current", "latest", "recent", "news", "market", "stock price",
            "industry trends", "legal precedent", "regulation"
        ]
        
        if any(indicator in query_lower for indicator in external_indicators):
            # Determine if it's document-related external knowledge
            document_context_indicators = [
                "contract", "agreement", "document", "clause", "term",
                "liability", "compliance", "risk", "legal requirement"
            ]
            
            if any(doc_indicator in query_lower for doc_indicator in document_context_indicators):
                intent["type"] = "hybrid"  # Document + external
                intent["requires_external"] = True
            else:
                intent["type"] = "external_knowledge"  # Pure external
                intent["confidence"] = 0.7
        
        # Categorize external knowledge type
        for category, keywords in self.external_knowledge_categories.items():
            if any(keyword in query_lower for keyword in keywords):
                intent["external_category"] = category
                break
        
        return intent
    
    async def _document_focused_response(self, query: str, context: AgentContext, intent: Dict[str, Any]) -> AgentResult:
        """
        Generate response focused on user's document with enhanced contextual search
        """
        logger.info(f"📄 Document-focused response for: {query} (doc: {context.contract_id})")
        
        findings = []
        recommendations = []
        data_sources = ["document_analysis"]
        
        try:
            # Get document text for contextual search
            document_text = await self._get_document_text(context.contract_id)
            
            # Perform contextual search for specific terms in the query
            contextual_findings = await self._perform_contextual_search(query, document_text, context.contract_id)
            
            # Get document analysis using existing document analyzer
            from .document_analyzer import DocumentAnalysisAgent
            doc_agent = DocumentAnalysisAgent()
            
            # Create context for document analysis
            doc_context = AgentContext(
                query=query,
                contract_id=context.contract_id,
                user_id=context.user_id,
                document_type=context.document_type or "contract"
            )
            
            # Get document analysis
            doc_result = await doc_agent.analyze(doc_context)
            
            # Extract document insights
            document_insights = self._extract_document_insights(doc_result, query)
            
            # Add external context if needed and beneficial
            external_context = ""
            if intent.get("requires_external", False):
                external_data = await self._get_relevant_external_context(query, intent, context)
                if external_data:
                    external_context = self._format_external_context(external_data)
                    data_sources.extend(["legal_precedents", "industry_context", "regulatory_updates"])
            
            # Generate enhanced conversational response with contextual findings
            if intent.get("is_analytical", False):
                # For analytical queries, focus more on document analyzer results
                response_text = await self._generate_analytical_document_response(
                    query, document_insights, contextual_findings, external_context, context, intent
                )
            else:
                # For specific search queries, use contextual search results
                response_text = await self._generate_enhanced_document_response(
                    query, document_insights, contextual_findings, external_context, context
                )
            
            findings.append({
                "type": "document_chat_response",
                "title": f"Document analysis for: {query}",
                "severity": "info",
                "confidence": 0.9,
                "description": response_text,
                "document_id": context.contract_id,
                "operation": intent.get("document_operation", "analysis"),
                "enhanced_with_external": bool(external_context),
                "contextual_matches": len(contextual_findings)
            })
            
            # Add contextual findings as separate findings
            for ctx_finding in contextual_findings[:3]:  # Limit to top 3
                findings.append({
                    "type": "contextual_match",
                    "title": f"Found: {ctx_finding['term']}",
                    "severity": "info",
                    "confidence": ctx_finding['relevance_score'],
                    "description": ctx_finding['context'],
                    "location": ctx_finding['location'],
                    "document_id": context.contract_id
                })
            
            # Add document-specific recommendations
            recommendations = [
                "Response based on your uploaded document with contextual analysis",
                "Ask follow-up questions about specific sections or terms",
                "Use 'compare with' to analyze multiple documents"
            ]
            
            if contextual_findings:
                recommendations.append(f"Found {len(contextual_findings)} relevant sections in your document")
            
            if external_context:
                recommendations.append("Enhanced with current industry/legal context")
            
            return AgentResult(
                agent_name=self.agent_name,
                agent_version=self.version,
                status=AgentStatus.COMPLETED,
                confidence=0.9,
                findings=findings,
                recommendations=recommendations,
                execution_time_ms=0.0,
                memory_usage_mb=0.0,
                llm_calls=1,
                data_sources=data_sources
            )
            
        except Exception as e:
            logger.error(f"Document-focused response failed: {e}")
            return self._create_failure_result(f"Document analysis failed: {e}")
    
    async def _document_guidance_response(self, query: str, context: AgentContext) -> AgentResult:
        """
        Provide guidance when user asks document questions but no document is available
        """
        logger.info(f"📋 Document guidance for: {query}")
        
        guidance_response = await self._generate_document_guidance(query)
        
        findings = [{
            "type": "document_guidance",
            "title": "Document upload required",
            "severity": "info",
            "confidence": 0.8,
            "description": guidance_response,
            "requires_document": True
        }]
        
        recommendations = [
            "Upload a document to get specific analysis",
            "Try the document upload feature",
            "Once uploaded, ask the same question for detailed insights"
        ]
        
        return AgentResult(
            agent_name=self.agent_name,
            agent_version=self.version,
            status=AgentStatus.COMPLETED,
            confidence=0.8,
            findings=findings,
            recommendations=recommendations,
            execution_time_ms=0.0,
            memory_usage_mb=0.0,
            llm_calls=1,
            data_sources=["ai_guidance"]
        )
    
    async def _external_knowledge_response(self, query: str, context: AgentContext, intent: Dict[str, Any]) -> AgentResult:
        """
        Handle pure external knowledge queries (non-document related)
        """
        logger.info(f"🌐 External knowledge response for: {query}")
        
        # This is the original enhanced response logic for non-document queries
        return await self._enhanced_response_with_mcp(query, intent.get("external_category", "general"), context)
    
    async def _hybrid_document_response(self, query: str, context: AgentContext, intent: Dict[str, Any]) -> AgentResult:
        """
        Handle queries that need both document analysis and external knowledge
        """
        logger.info(f"🔄 Hybrid response for: {query} (doc: {context.contract_id})")
        
        # Combine document analysis with external knowledge
        if context.contract_id:
            return await self._document_focused_response(query, context, intent)
        else:
            return await self._external_knowledge_response(query, context, intent)

    async def _enhanced_response_with_mcp(self, query: str, category: str, context: AgentContext) -> AgentResult:
        """
        Generate enhanced response using MCP services for external data
        """
        logger.info(f"🌐 Using MCP enhancement for {category} query: {query}")
        
        findings = []
        recommendations = []
        data_sources = ["ai_analysis"]
        
        try:
            # Get external data via MCP services
            mcp_results = await self._get_mcp_data_for_query(query, category)
            
            # Process MCP results
            external_data = []
            for source, result in mcp_results.items():
                if result.success and result.data:
                    external_data.extend(result.data if isinstance(result.data, list) else [result.data])
                    data_sources.append(source)
            
            # Generate AI response with external context
            ai_response = await self._generate_ai_response_with_context(query, external_data, category)
            
            # Create findings
            if external_data:
                findings.append({
                    "type": "enhanced_response",
                    "title": f"Response enhanced with {len(external_data)} external sources",
                    "severity": "info",
                    "confidence": 0.9,
                    "description": ai_response,
                    "external_sources": len(external_data),
                    "category": category
                })
                
                # Add source-specific findings
                for source, result in mcp_results.items():
                    if result.success and result.data:
                        findings.append({
                            "type": f"{source}_data",
                            "title": f"Data from {source.replace('_', ' ').title()}",
                            "severity": "info",
                            "confidence": 0.8,
                            "description": f"Retrieved {len(result.data) if isinstance(result.data, list) else 1} items from {source}",
                            "data": result.data,
                            "source": source
                        })
            else:
                # Fallback to AI-only response
                findings.append({
                    "type": "ai_response",
                    "title": "AI-generated response",
                    "severity": "info",
                    "confidence": 0.7,
                    "description": ai_response,
                    "note": "External data sources were not available"
                })
            
            recommendations = [
                "Response generated using multiple data sources",
                "Information is current as of the query time",
                "Ask follow-up questions for more specific details"
            ]
            
            return AgentResult(
                agent_name=self.agent_name,
                agent_version=self.version,
                status=AgentStatus.COMPLETED,
                confidence=0.9 if external_data else 0.7,
                findings=findings,
                recommendations=recommendations,
                execution_time_ms=0.0,
                memory_usage_mb=0.0,
                llm_calls=1,
                data_sources=data_sources
            )
            
        except Exception as e:
            logger.error(f"Enhanced response failed: {e}")
            # Fallback to AI-only response
            return await self._ai_only_response(query, context)
    
    async def _ai_only_response(self, query: str, context: AgentContext) -> AgentResult:
        """
        Generate response using only AI capabilities
        """
        logger.info(f"🤖 Using AI-only response for: {query}")
        
        try:
            # Generate AI response
            ai_response = await self._generate_ai_response(query)
            
            findings = [{
                "type": "ai_response",
                "title": "AI-generated response",
                "severity": "info",
                "confidence": 0.8,
                "description": ai_response,
                "query": query
            }]
            
            recommendations = [
                "Response generated using AI knowledge",
                "For real-time data, try queries with 'current' or 'latest'",
                "Ask follow-up questions for more details"
            ]
            
            return AgentResult(
                agent_name=self.agent_name,
                agent_version=self.version,
                status=AgentStatus.COMPLETED,
                confidence=0.8,
                findings=findings,
                recommendations=recommendations,
                execution_time_ms=0.0,
                memory_usage_mb=0.0,
                llm_calls=1,
                data_sources=["ai_analysis"]
            )
            
        except Exception as e:
            logger.error(f"AI response generation failed: {e}")
            return self._create_failure_result(f"AI response failed: {e}")
    
    async def _get_mcp_data_for_query(self, query: str, category: str) -> Dict[str, MCPResult]:
        """
        Get relevant MCP data based on query and category
        """
        mcp_results = {}
        
        try:
            async with mcp_service:
                # Always try web search for current information
                web_result = await mcp_service.web_search(query, max_results=5)
                mcp_results["web_search"] = web_result
                
                # Category-specific data sources
                if category in ["stock_price", "finance", "technology"]:
                    # Try to extract company name for stock data
                    company_names = self._extract_company_names_from_query(query)
                    for company in company_names[:2]:  # Limit to 2 companies
                        company_result = await mcp_service.get_company_filings(company)
                        mcp_results[f"company_data_{company}"] = company_result
                
                if category in ["news", "current"]:
                    news_result = await mcp_service.news_search(query, max_results=3)
                    mcp_results["news_search"] = news_result
                
                if category in ["legal", "regulation"]:
                    legal_result = await mcp_service.get_legal_precedents("general", query.split())
                    mcp_results["legal_precedents"] = legal_result
                
                if category in ["industry", "business"]:
                    industry_result = await mcp_service.analyze_industry_context("general", "analysis", query.split())
                    mcp_results["industry_context"] = industry_result
                
        except Exception as e:
            logger.error(f"MCP data retrieval failed: {e}")
        
        return mcp_results
    
    def _extract_company_names_from_query(self, query: str) -> List[str]:
        """Extract company names from query"""
        companies = []
        query_lower = query.lower()
        
        # Common company mappings
        company_mappings = {
            "microsoft": "Microsoft Corporation",
            "apple": "Apple Inc",
            "google": "Alphabet Inc",
            "amazon": "Amazon.com Inc",
            "tesla": "Tesla Inc",
            "meta": "Meta Platforms Inc",
            "netflix": "Netflix Inc",
            "nvidia": "NVIDIA Corporation"
        }
        
        for keyword, company_name in company_mappings.items():
            if keyword in query_lower:
                companies.append(company_name)
        
        return companies
    
    async def _generate_ai_response_with_context(self, query: str, external_data: List[Dict], category: str) -> str:
        """
        Generate AI response enhanced with external context
        """
        # Prepare context from external data
        context_info = []
        for data_item in external_data[:5]:  # Limit context
            if isinstance(data_item, dict):
                if "title" in data_item and "description" in data_item:
                    context_info.append(f"- {data_item['title']}: {data_item['description'][:200]}...")
                elif "title" in data_item:
                    context_info.append(f"- {data_item['title']}")
                else:
                    context_info.append(f"- {str(data_item)[:200]}...")
        
        context_text = "\n".join(context_info) if context_info else "No external context available"
        
        prompt = f"""
        Answer the following question using both your knowledge and the provided current information:
        
        Question: {query}
        
        Current Information:
        {context_text}
        
        Provide a comprehensive, accurate answer that:
        1. Directly answers the question
        2. Incorporates relevant current information
        3. Is conversational and helpful
        4. Mentions if information is current/recent when relevant
        
        Answer:
        """
        
        try:
            result = await safe_llm_completion(
                prompt=prompt,
                task_type=LLMTask.COMPLETION,
                max_tokens=800,
                temperature=0.3
            )
            return result["content"]
        except Exception as e:
            logger.error(f"AI response generation failed: {e}")
            return f"I can help with that question, but I'm having trouble accessing my full capabilities right now. Based on what I know: {query} - Please try rephrasing your question or ask for more specific information."
    
    def _extract_document_insights(self, doc_result: AgentResult, query: str) -> Dict[str, Any]:
        """Extract relevant insights from document analysis result"""
        insights = {
            "findings": doc_result.findings,
            "recommendations": doc_result.recommendations,
            "confidence": doc_result.confidence,
            "summary": "",
            "relevant_sections": []
        }
        
        # Extract key findings relevant to the query
        query_lower = query.lower()
        relevant_findings = []
        
        for finding in doc_result.findings:
            finding_text = (finding.get("title", "") + " " + finding.get("description", "")).lower()
            # Simple relevance check
            if any(word in finding_text for word in query_lower.split() if len(word) > 3):
                relevant_findings.append(finding)
        
        insights["relevant_findings"] = relevant_findings[:5]  # Top 5 relevant
        
        return insights
    
    async def _get_relevant_external_context(self, query: str, intent: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Get external context relevant to document analysis"""
        external_data = {}
        
        try:
            async with mcp_service:
                # Get legal precedents for compliance/risk queries
                if intent.get("document_operation") in ["compliance", "risk_assessment"]:
                    legal_result = await mcp_service.get_legal_precedents(
                        context.document_type or "contract", 
                        query.split()
                    )
                    if legal_result.success:
                        external_data["legal_precedents"] = legal_result.data
                
                # Get industry context for business documents
                if context.document_type in ["contract", "agreement", "policy"]:
                    industry_result = await mcp_service.analyze_industry_context(
                        "business", context.document_type, query.split()
                    )
                    if industry_result.success:
                        external_data["industry_context"] = industry_result.data
                
                # Get regulatory updates for compliance queries
                if "compliance" in query.lower() or "regulation" in query.lower():
                    reg_result = await mcp_service.enrich_document_context(
                        context.document_type or "contract",
                        "business",
                        query.split()
                    )
                    if reg_result.success:
                        external_data["regulatory_updates"] = reg_result.data
        
        except Exception as e:
            logger.warning(f"External context retrieval failed: {e}")
        
        return external_data
    
    def _format_external_context(self, external_data: Dict[str, Any]) -> str:
        """Format external data into context string"""
        context_parts = []
        
        if "legal_precedents" in external_data:
            context_parts.append("Legal Context: Recent legal precedents and cases")
        
        if "industry_context" in external_data:
            context_parts.append("Industry Context: Current business practices and standards")
        
        if "regulatory_updates" in external_data:
            context_parts.append("Regulatory Context: Recent regulatory changes and requirements")
        
        return "; ".join(context_parts)
    
    async def _generate_document_response(
        self, 
        query: str, 
        document_insights: Dict[str, Any], 
        external_context: str,
        context: AgentContext
    ) -> str:
        """Generate conversational response about the document"""
        
        # Prepare document context
        findings_summary = []
        for finding in document_insights.get("relevant_findings", [])[:3]:
            title = finding.get("title", "")
            desc = finding.get("description", "")[:150]
            findings_summary.append(f"- {title}: {desc}")
        
        document_context = "\n".join(findings_summary) if findings_summary else "No specific findings for this query"
        
        prompt = f"""
        You are a document intelligence assistant. Answer the user's question about their document.
        
        User Question: {query}
        
        Document Analysis Results:
        {document_context}
        
        {f"Additional Context: {external_context}" if external_context else ""}
        
        Provide a conversational, helpful response that:
        1. Directly answers their question about the document
        2. References specific findings from the analysis
        3. Explains the implications for their document
        4. Suggests next steps if relevant
        5. Maintains a professional but friendly tone
        
        Focus on their specific document and make the response actionable.
        
        Response:
        """
        
        try:
            result = await llm_factory.generate_completion(
                prompt=prompt,
                task_type=LLMTask.COMPLETION,
                max_tokens=600,
                temperature=0.3,
                contract_id=context.contract_id
            )
            return result["content"]
        except Exception as e:
            logger.error(f"Document response generation failed: {e}")
            return f"I found some information about your document regarding '{query}', but I'm having trouble generating a detailed response right now. The document analysis shows relevant findings that you can review in the detailed results."
    
    async def _get_document_text(self, contract_id: str) -> str:
        """Get the full text of a document for contextual search"""
        try:
            from app.models import BronzeContract, BronzeContractTextRaw
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            
            async for db in get_operational_db():
                result = await db.execute(
                    select(BronzeContract)
                    .options(selectinload(BronzeContract.text_raw))
                    .where(BronzeContract.contract_id == contract_id)
                )
                contract = result.scalar_one_or_none()
                
                if contract and contract.text_raw:
                    return contract.text_raw.raw_text
                
                return ""
                
        except Exception as e:
            logger.error(f"Failed to get document text for {contract_id}: {e}")
            return ""
    
    async def _perform_contextual_search(self, query: str, document_text: str, contract_id: str) -> List[Dict[str, Any]]:
        """
        Perform contextual search to find relevant terms and their surrounding context
        """
        if not document_text:
            return []
        
        try:
            import re
            
            # Extract key terms from the query
            key_terms = self._extract_search_terms(query)
            contextual_findings = []
            
            for term in key_terms:
                # Find all occurrences of the term (case-insensitive)
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                matches = list(pattern.finditer(document_text))
                
                for match in matches[:3]:  # Limit to 3 matches per term
                    start_pos = match.start()
                    end_pos = match.end()
                    
                    # Get context around the match (200 characters before and after)
                    context_start = max(0, start_pos - 200)
                    context_end = min(len(document_text), end_pos + 200)
                    context = document_text[context_start:context_end]
                    
                    # Clean up context
                    context = re.sub(r'\s+', ' ', context).strip()
                    
                    # Calculate relevance score based on query similarity
                    relevance_score = self._calculate_relevance_score(query, context)
                    
                    # Determine location in document (approximate)
                    location_percent = (start_pos / len(document_text)) * 100
                    location = f"~{location_percent:.0f}% through document"
                    
                    contextual_findings.append({
                        "term": term,
                        "context": context,
                        "location": location,
                        "relevance_score": relevance_score,
                        "position": start_pos
                    })
            
            # Sort by relevance score and return top findings
            contextual_findings.sort(key=lambda x: x['relevance_score'], reverse=True)
            return contextual_findings[:5]  # Return top 5 most relevant
            
        except Exception as e:
            logger.error(f"Contextual search failed: {e}")
            return []
    
    def _extract_search_terms(self, query: str) -> List[str]:
        """Extract key search terms from the query"""
        import re
        
        # Remove common words and extract meaningful terms
        stop_words = {
            'what', 'is', 'are', 'the', 'in', 'this', 'document', 'about', 'how', 'does',
            'can', 'you', 'tell', 'me', 'find', 'show', 'where', 'when', 'why', 'which'
        }
        
        # Extract words and phrases
        words = re.findall(r'\b\w+\b', query.lower())
        terms = [word for word in words if word not in stop_words and len(word) > 2]
        
        # For analytical queries, add broader search terms
        analytical_mappings = {
            'summarize': ['summary', 'overview', 'key', 'main', 'important'],
            'risk': ['risk', 'liability', 'danger', 'concern', 'problem', 'issue'],
            'recommend': ['recommendation', 'suggest', 'advice', 'should', 'consider'],
            'high-risk': ['risk', 'liability', 'critical', 'severe', 'dangerous'],
            'clause': ['clause', 'term', 'provision', 'section', 'article']
        }
        
        query_lower = query.lower()
        for key_term, related_terms in analytical_mappings.items():
            if key_term in query_lower:
                terms.extend(related_terms)
        
        # Also look for specific legal/business terms
        legal_terms = [
            'intellectual property', 'liability', 'termination', 'payment', 'obligation',
            'indemnification', 'confidentiality', 'non-disclosure', 'warranty', 'breach',
            'force majeure', 'governing law', 'jurisdiction', 'arbitration', 'damages',
            'compliance', 'regulation', 'penalty', 'default', 'remedy'
        ]
        
        # Check if query contains any legal terms
        for legal_term in legal_terms:
            if legal_term in query_lower:
                terms.append(legal_term)
        
        return list(set(terms))  # Remove duplicates
    
    def _calculate_relevance_score(self, query: str, context: str) -> float:
        """Calculate relevance score between query and context"""
        try:
            query_words = set(query.lower().split())
            context_words = set(context.lower().split())
            
            # Calculate Jaccard similarity
            intersection = len(query_words.intersection(context_words))
            union = len(query_words.union(context_words))
            
            if union == 0:
                return 0.0
            
            jaccard_score = intersection / union
            
            # Boost score for legal/business terms
            legal_boost = 0.0
            legal_terms = ['liability', 'intellectual', 'property', 'termination', 'payment', 'risk']
            for term in legal_terms:
                if term in context.lower():
                    legal_boost += 0.1
            
            return min(1.0, jaccard_score + legal_boost)
            
        except Exception as e:
            logger.error(f"Relevance calculation failed: {e}")
            return 0.5
    
    async def _generate_analytical_document_response(
        self, 
        query: str, 
        document_insights: Dict[str, Any], 
        contextual_findings: List[Dict[str, Any]],
        external_context: str,
        context: AgentContext,
        intent: Dict[str, Any]
    ) -> str:
        """Generate analytical response focusing on overall document insights"""
        
        # Prepare comprehensive document analysis from document analyzer results
        all_findings = document_insights.get("findings", [])
        all_recommendations = document_insights.get("recommendations", [])
        
        # Create structured analysis summary based on actual findings
        analysis_summary = []
        
        if all_findings:
            analysis_summary.append(f"Document Analysis Results: {len(all_findings)} key findings identified")
            
            # Group findings by severity for risk assessment
            high_priority_findings = []
            medium_priority_findings = []
            other_findings = []
            
            for finding in all_findings:
                severity = finding.get("severity", "").lower()
                title = finding.get("title", "Finding")
                description = finding.get("description", "")[:100]  # First 100 chars
                
                finding_summary = f"  - {title}"
                if description:
                    finding_summary += f": {description}"
                
                if severity in ["critical", "high"]:
                    high_priority_findings.append(finding_summary)
                elif severity in ["medium"]:
                    medium_priority_findings.append(finding_summary)
                else:
                    other_findings.append(finding_summary)
            
            # Add findings by priority
            if high_priority_findings:
                analysis_summary.append(f"High Priority Items ({len(high_priority_findings)}):")
                analysis_summary.extend(high_priority_findings[:3])  # Top 3
            
            if medium_priority_findings:
                analysis_summary.append(f"Medium Priority Items ({len(medium_priority_findings)}):")
                analysis_summary.extend(medium_priority_findings[:3])  # Top 3
            
            if other_findings and not high_priority_findings and not medium_priority_findings:
                analysis_summary.append("Key Findings:")
                analysis_summary.extend(other_findings[:5])  # Top 5 if no priority items
        
        analysis_text = "\n".join(analysis_summary) if analysis_summary else "Document analysis completed - no specific findings to report"
        
        # Debug logging to see what we're getting from document analyzer
        logger.info(f"📊 Analytical Response Debug:")
        logger.info(f"   Query: {query}")
        logger.info(f"   Document Type: {context.document_type}")
        logger.info(f"   Total Findings: {len(all_findings)}")
        logger.info(f"   Total Recommendations: {len(all_recommendations)}")
        logger.info(f"   Contextual Matches: {len(contextual_findings)}")
        if all_findings:
            logger.info(f"   Sample Finding: {all_findings[0].get('title', 'No title')} - {all_findings[0].get('type', 'No type')}")
        
        # If we have no meaningful analysis, try to get document content directly
        if not all_findings and not contextual_findings:
            logger.warning("⚠️ No findings from document analyzer, using document text directly")
            document_text = await self._get_document_text(context.contract_id)
            if document_text:
                analysis_text = f"Document Content Available: {len(document_text)} characters of text to analyze"
            else:
                analysis_text = "Unable to retrieve document content for analysis"
        
        # Add contextual excerpts if relevant
        contextual_summary = []
        if contextual_findings:
            contextual_summary.append(f"Relevant text excerpts found: {len(contextual_findings)}")
            for ctx_finding in contextual_findings[:2]:  # Top 2 contextual matches
                term = ctx_finding.get("term", "")
                location = ctx_finding.get("location", "")
                contextual_summary.append(f"  - '{term}' found at {location}")
        
        contextual_text = "\n".join(contextual_summary) if contextual_summary else ""
        
        # Prepare recommendations summary
        recommendations_text = ""
        if all_recommendations:
            recommendations_text = f"Key Recommendations ({len(all_recommendations)} total):\n"
            for i, rec in enumerate(all_recommendations[:5], 1):  # Top 5 recommendations
                recommendations_text += f"{i}. {rec}\n"
        
        analysis_type = intent.get("analysis_type", "general")
        
        prompt = f"""
        You are a document intelligence assistant providing analytical insights about a document.
        
        User Question: {query}
        Analysis Type: {analysis_type}
        
        Document Analysis Results:
        {analysis_text}
        
        {"Contextual Text Matches:" + chr(10) + contextual_text if contextual_text else ""}
        
        {"Document Recommendations:" + chr(10) + recommendations_text if recommendations_text else ""}
        
        {f"External Context: {external_context}" if external_context else ""}
        
        Provide a comprehensive analytical response that:
        1. Directly answers the user's analytical question
        2. Synthesizes findings from the document analysis
        3. Provides high-level insights and patterns
        4. Includes specific examples when relevant
        5. Offers actionable conclusions
        6. Maintains a professional analytical tone
        
        Focus on providing strategic insights rather than just listing findings.
        
        Response:
        """
        
        try:
            result = await llm_factory.generate_completion(
                prompt=prompt,
                task_type=LLMTask.COMPLETION,
                max_tokens=800,
                temperature=0.2,  # Lower temperature for more focused analytical responses
                contract_id=context.contract_id
            )
            return result["content"]
        except Exception as e:
            logger.error(f"Analytical document response generation failed: {e}")
            return f"I've analyzed your document regarding '{query}' and found {len(all_findings)} key findings with {len(all_recommendations)} recommendations. The analysis shows important insights about your document that you can review in the detailed results."

    async def _generate_enhanced_document_response(
        self, 
        query: str, 
        document_insights: Dict[str, Any], 
        contextual_findings: List[Dict[str, Any]],
        external_context: str,
        context: AgentContext
    ) -> str:
        """Generate enhanced conversational response with contextual findings"""
        
        # Prepare document context
        findings_summary = []
        for finding in document_insights.get("relevant_findings", [])[:3]:
            title = finding.get("title", "")
            desc = finding.get("description", "")[:150]
            findings_summary.append(f"- {title}: {desc}")
        
        document_context = "\n".join(findings_summary) if findings_summary else "No specific findings for this query"
        
        # Prepare contextual findings
        contextual_summary = []
        for ctx_finding in contextual_findings[:3]:
            term = ctx_finding.get("term", "")
            context_text = ctx_finding.get("context", "")[:200]
            location = ctx_finding.get("location", "")
            contextual_summary.append(f"- Found '{term}' at {location}: {context_text}")
        
        contextual_context = "\n".join(contextual_summary) if contextual_summary else "No specific text matches found"
        
        prompt = f"""
        You are a document intelligence assistant. Answer the user's question about their document using both analysis results and specific text excerpts.
        
        User Question: {query}
        
        Document Analysis Results:
        {document_context}
        
        Specific Text Excerpts from Document:
        {contextual_context}
        
        {f"Additional Context: {external_context}" if external_context else ""}
        
        Provide a comprehensive, conversational response that:
        1. Directly answers their question about the document
        2. References specific text excerpts when relevant
        3. Explains the implications and context
        4. Provides actionable insights
        5. Maintains a professional but friendly tone
        6. Quotes relevant sections when helpful
        
        Focus on their specific document and make the response detailed and actionable.
        
        Response:
        """
        
        try:
            result = await llm_factory.generate_completion(
                prompt=prompt,
                task_type=LLMTask.COMPLETION,
                max_tokens=800,
                temperature=0.3,
                contract_id=context.contract_id
            )
            return result["content"]
        except Exception as e:
            logger.error(f"Enhanced document response generation failed: {e}")
            return f"I found relevant information about '{query}' in your document, including specific text sections, but I'm having trouble generating a detailed response right now. The document contains relevant content that you can review in the detailed results."

    async def _generate_document_guidance(self, query: str) -> str:
        """Generate guidance when no document is available"""
        
        prompt = f"""
        A user is asking about document analysis but hasn't uploaded a document yet.
        
        Their question: {query}
        
        Provide helpful guidance that:
        1. Explains what they could learn by uploading a document
        2. Describes how the system would analyze their document for this type of question
        3. Encourages them to upload a document
        4. Gives general guidance about the topic if helpful
        
        Keep it friendly and encouraging.
        
        Response:
        """
        
        try:
            result = await llm_factory.generate_completion(
                prompt=prompt,
                task_type=LLMTask.COMPLETION,
                max_tokens=400,
                temperature=0.4
            )
            return result["content"]
        except Exception as e:
            logger.error(f"Document guidance generation failed: {e}")
            return f"To answer questions about '{query}', I'd need to analyze your specific document. Please upload a document and I can provide detailed insights about {query} in your specific context."

    async def _search_all_documents_response(self, query: str, context: AgentContext) -> AgentResult:
        """
        Search across all user's documents and provide comprehensive answer
        """
        logger.info(f"📚 Searching all documents for user: {context.user_id}")
        
        findings = []
        recommendations = []
        
        try:
            # Get all user documents from database
            from app.models import BronzeContract
            from sqlalchemy import select
            
            async for db in get_operational_db():
                result = await db.execute(
                    select(BronzeContract)
                    .where(BronzeContract.owner_user_id == context.user_id)
                    .where(BronzeContract.status == "completed")
                )
                user_documents = result.scalars().all()
            
            if not user_documents:
                return AgentResult(
                    agent_name=self.agent_name,
                    agent_version=self.version,
                    status=AgentStatus.COMPLETED,
                    confidence=1.0,
                    findings=[{
                        "type": "no_documents",
                        "title": "No documents found",
                        "severity": "info",
                        "confidence": 1.0,
                        "description": "You don't have any uploaded documents yet. Please upload documents to search across them."
                    }],
                    recommendations=["Upload documents to enable search"],
                    execution_time_ms=0.0,
                    memory_usage_mb=0.0,
                    data_sources=["database"]
                )
            
            logger.info(f"Found {len(user_documents)} documents for user")
            
            # Search across all documents using contextual search and analysis
            all_findings = []
            contextual_matches = []
            
            for doc in user_documents[:10]:  # Limit to 10 documents for performance
                try:
                    # Get document text for contextual search
                    document_text = await self._get_document_text(doc.contract_id)
                    
                    # Perform contextual search on this document
                    doc_contextual_findings = await self._perform_contextual_search(query, document_text, doc.contract_id)
                    
                    # Add document info to contextual findings
                    for ctx_finding in doc_contextual_findings:
                        ctx_finding["document_id"] = doc.contract_id
                        ctx_finding["document_name"] = doc.filename
                        contextual_matches.append(ctx_finding)
                    
                    # Create context for this document
                    doc_context = AgentContext(
                        contract_id=doc.contract_id,
                        user_id=context.user_id,
                        query=query,
                        document_type=doc.document_type or "contract"
                    )
                    
                    # Analyze this document
                    from .document_analyzer import DocumentAnalysisAgent
                    doc_agent = DocumentAnalysisAgent()
                    doc_result = await doc_agent.analyze(doc_context)
                    
                    # Collect relevant findings
                    for finding in doc_result.findings:
                        finding["document_id"] = doc.contract_id
                        finding["document_name"] = doc.filename
                        all_findings.append(finding)
                
                except Exception as e:
                    logger.warning(f"Failed to analyze document {doc.contract_id}: {e}")
                    continue
            
            # Generate comprehensive response across all documents
            response_text = await self._generate_multi_document_response(query, all_findings, contextual_matches, len(user_documents))
            
            findings.append({
                "type": "multi_document_response",
                "title": f"Analysis across {len(user_documents)} documents",
                "severity": "info",
                "confidence": 0.85,
                "description": response_text,
                "documents_searched": len(user_documents),
                "findings_found": len(all_findings),
                "contextual_matches": len(contextual_matches)
            })
            
            # Add top contextual matches as separate findings
            for ctx_match in sorted(contextual_matches, key=lambda x: x['relevance_score'], reverse=True)[:5]:
                findings.append({
                    "type": "contextual_match_multi",
                    "title": f"Found in {ctx_match['document_name']}: {ctx_match['term']}",
                    "severity": "info",
                    "confidence": ctx_match['relevance_score'],
                    "description": ctx_match['context'],
                    "location": ctx_match['location'],
                    "document_id": ctx_match['document_id'],
                    "document_name": ctx_match['document_name']
                })
            
            recommendations = [
                f"Searched across {len(user_documents)} documents",
                "Select a specific document for detailed analysis",
                "Use filters to narrow down results"
            ]
            
            return AgentResult(
                agent_name=self.agent_name,
                agent_version=self.version,
                status=AgentStatus.COMPLETED,
                confidence=0.85,
                findings=findings,
                recommendations=recommendations,
                execution_time_ms=0.0,
                memory_usage_mb=0.0,
                llm_calls=1,
                data_sources=["database", "document_analysis", "ai_synthesis"]
            )
            
        except Exception as e:
            logger.error(f"All documents search failed: {e}")
            return self._create_failure_result(f"Failed to search documents: {e}")
    
    async def _generate_multi_document_response(self, query: str, findings: List[Dict], contextual_matches: List[Dict], total_docs: int) -> str:
        """Generate response summarizing findings and contextual matches across multiple documents"""
        
        if not findings and not contextual_matches:
            return f"I searched across your {total_docs} documents but didn't find specific information related to '{query}'. Try rephrasing your question or selecting a specific document."
        
        # Summarize findings by document
        doc_summaries = {}
        for finding in findings:
            doc_name = finding.get("document_name", "Unknown")
            if doc_name not in doc_summaries:
                doc_summaries[doc_name] = {"findings": [], "contextual_matches": []}
            doc_summaries[doc_name]["findings"].append(finding)
        
        # Add contextual matches to document summaries
        for ctx_match in contextual_matches:
            doc_name = ctx_match.get("document_name", "Unknown")
            if doc_name not in doc_summaries:
                doc_summaries[doc_name] = {"findings": [], "contextual_matches": []}
            doc_summaries[doc_name]["contextual_matches"].append(ctx_match)
        
        # Prepare contextual excerpts for the prompt
        contextual_excerpts = []
        for ctx_match in sorted(contextual_matches, key=lambda x: x['relevance_score'], reverse=True)[:5]:
            doc_name = ctx_match.get("document_name", "Unknown")
            term = ctx_match.get("term", "")
            context = ctx_match.get("context", "")[:200]
            contextual_excerpts.append(f"- {doc_name}: Found '{term}' - {context}")
        
        contextual_text = "\n".join(contextual_excerpts) if contextual_excerpts else "No specific text matches found"
        
        prompt = f"""
        Provide a comprehensive answer to this query across multiple documents: {query}
        
        Documents analyzed: {total_docs}
        Documents with findings: {len(doc_summaries)}
        Total analysis findings: {len(findings)}
        Total contextual matches: {len(contextual_matches)}
        
        Specific text excerpts found:
        {contextual_text}
        
        Analysis findings summary:
        {json.dumps({k: {"findings_count": len(v["findings"]), "matches_count": len(v["contextual_matches"])} for k, v in doc_summaries.items()}, indent=2)}
        
        Provide a comprehensive response that:
        1. Directly answers the user's question using information from all documents
        2. Quotes specific text excerpts when relevant
        3. Highlights patterns or differences between documents
        4. Mentions specific documents by name when referencing information
        5. Is detailed but well-organized
        6. Provides actionable insights
        
        Response:
        """
        
        try:
            result = await llm_factory.generate_completion(
                prompt=prompt,
                task_type=LLMTask.COMPLETION,
                max_tokens=800,
                temperature=0.3
            )
            return result["content"]
        except Exception as e:
            logger.error(f"Multi-document response generation failed: {e}")
            return f"Found {len(findings)} analysis findings and {len(contextual_matches)} text matches across {len(doc_summaries)} documents related to '{query}'. The documents contain relevant information about your query."
    
    def _create_result_with_mode_restriction(self, query: str) -> AgentResult:
        """Create result explaining mode restriction"""
        return AgentResult(
            agent_name=self.agent_name,
            agent_version=self.version,
            status=AgentStatus.COMPLETED,
            confidence=1.0,
            findings=[{
                "type": "mode_restriction",
                "title": "Document mode active",
                "severity": "info",
                "confidence": 1.0,
                "description": f"Your question '{query}' appears to be a general question. In Document Mode, I can only answer questions about your uploaded documents. To ask general questions (like stock prices, news, etc.), please switch to 'General Mode'."
            }],
            recommendations=[
                "Switch to 'General Mode' for general questions",
                "Stay in 'Document Mode' to ask about your documents",
                "Use 'All Documents' to search across all your documents"
            ],
            execution_time_ms=0.0,
            memory_usage_mb=0.0,
            data_sources=["system"]
        )

    async def _generate_ai_response(self, query: str) -> str:
        """
        Generate AI response without external context
        """
        prompt = f"""
        Answer the following question comprehensively and helpfully:
        
        Question: {query}
        
        Provide a detailed, accurate answer that:
        1. Directly addresses the question
        2. Is conversational and engaging
        3. Offers additional relevant information when appropriate
        4. Suggests follow-up questions if relevant
        
        Answer:
        """
        
        try:
            result = await llm_factory.generate_completion(
                prompt=prompt,
                task_type=LLMTask.COMPLETION,
                max_tokens=600,
                temperature=0.4
            )
            return result["content"]
        except Exception as e:
            logger.error(f"AI response generation failed: {e}")
            return "I'm having trouble generating a response right now. Please try rephrasing your question or contact support if the issue persists."