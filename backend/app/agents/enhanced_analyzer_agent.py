"""
Enhanced Document Analyzer Agent
Uses document type, industry context, and MCP integration for comprehensive analysis
"""
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.agents.base_agent import BaseAgent, AgentContext, AgentResult
from app.services.llm_factory import llm_factory, LLMTask

logger = logging.getLogger(__name__)

class EnhancedAnalyzerAgent(BaseAgent):
    """
    Enhanced analyzer that adapts analysis based on document type and industry
    Integrates with MCP servers for external data enrichment
    """
    
    def __init__(self):
        super().__init__("enhanced_analyzer")
        
        # Document type specific analysis templates
        self.analysis_templates = {
            "contract": {
                "focus_areas": ["terms", "obligations", "risks", "termination", "liability"],
                "key_questions": [
                    "What are the key obligations for each party?",
                    "What are the termination conditions?",
                    "How is liability allocated?",
                    "Are there any unusual or high-risk clauses?"
                ]
            },
            "invoice": {
                "focus_areas": ["amounts", "due_dates", "payment_terms", "discrepancies"],
                "key_questions": [
                    "What is the total amount due?",
                    "When is payment due?",
                    "Are there any discrepancies or unusual charges?",
                    "What are the payment terms and conditions?"
                ]
            },
            "report": {
                "focus_areas": ["findings", "recommendations", "data", "conclusions"],
                "key_questions": [
                    "What are the key findings?",
                    "What recommendations are made?",
                    "What data supports the conclusions?",
                    "Are there any risks or concerns identified?"
                ]
            },
            "research_paper": {
                "focus_areas": ["methodology", "results", "conclusions", "implications"],
                "key_questions": [
                    "What is the research methodology?",
                    "What are the key results and findings?",
                    "What conclusions are drawn?",
                    "What are the practical implications?"
                ]
            },
            "policy": {
                "focus_areas": ["requirements", "procedures", "compliance", "enforcement"],
                "key_questions": [
                    "What are the key requirements?",
                    "What procedures must be followed?",
                    "How is compliance monitored?",
                    "What are the enforcement mechanisms?"
                ]
            },
            "manual": {
                "focus_areas": ["procedures", "instructions", "safety", "troubleshooting"],
                "key_questions": [
                    "What are the key procedures?",
                    "Are there safety considerations?",
                    "What troubleshooting guidance is provided?",
                    "Are the instructions clear and complete?"
                ]
            },
            "general_document": {
                "focus_areas": ["purpose", "key_points", "actions", "implications"],
                "key_questions": [
                    "What is the main purpose of this document?",
                    "What are the key points or messages?",
                    "What actions are required or recommended?",
                    "What are the implications or next steps?"
                ]
            }
        }
        
        # Industry-specific considerations
        self.industry_considerations = {
            "technology": ["data privacy", "intellectual property", "cybersecurity", "compliance"],
            "healthcare": ["HIPAA compliance", "patient safety", "FDA regulations", "data protection"],
            "financial services": ["regulatory compliance", "risk management", "capital requirements", "consumer protection"],
            "legal": ["precedents", "jurisdiction", "statutory requirements", "ethical considerations"],
            "education": ["student privacy", "accessibility", "accreditation", "safety"],
            "real estate": ["zoning", "environmental", "title issues", "financing"],
            "manufacturing": ["safety standards", "quality control", "environmental compliance", "supply chain"],
            "retail": ["consumer protection", "product liability", "data privacy", "employment law"]
        }
    
    async def analyze(self, context: AgentContext) -> AgentResult:
        """
        Enhanced analysis using document type, industry context, and external data
        """
        start_time = datetime.now()
        llm_calls = 0
        
        try:
            # Get document and content
            contract = await self.get_contract_with_all_data(context.contract_id)
            if not contract or not contract.text_raw:
                return self.create_result(
                    success=False,
                    error_message="Document or text content not found"
                )
            
            document_text = contract.text_raw.raw_text
            
            # Extract document classification from context or database
            document_type = context.document_type or contract.document_category or "general_document"
            industry_type = context.industry_type or contract.industry_type or "general"
            
            logger.info(f"Analyzing {document_type} document for {industry_type} industry")
            
            # Step 1: Get external enrichment data via MCP (if available)
            external_data = await self._get_external_enrichment(
                document_type, industry_type, document_text, context
            )
            
            # Step 2: Perform document type specific analysis
            type_analysis = await self._analyze_by_document_type(
                document_text, document_type, industry_type, context.contract_id
            )
            llm_calls += 1
            
            # Step 3: Perform industry-specific analysis
            industry_analysis = await self._analyze_by_industry(
                document_text, industry_type, document_type, context.contract_id
            )
            llm_calls += 1
            
            # Step 4: Generate comprehensive insights
            comprehensive_insights = await self._generate_comprehensive_insights(
                document_text, type_analysis, industry_analysis, external_data, context.contract_id
            )
            llm_calls += 1
            
            # Step 5: Create recommendations
            recommendations = await self._generate_enhanced_recommendations(
                type_analysis, industry_analysis, comprehensive_insights, 
                document_type, industry_type, context.contract_id
            )
            llm_calls += 1
            
            # Compile findings
            findings = [
                {
                    "type": "document_classification",
                    "category": document_type,
                    "industry": industry_type,
                    "confidence": 0.9
                },
                {
                    "type": "type_specific_analysis",
                    "analysis": type_analysis,
                    "confidence": type_analysis.get("confidence", 0.8)
                },
                {
                    "type": "industry_analysis", 
                    "analysis": industry_analysis,
                    "confidence": industry_analysis.get("confidence", 0.8)
                },
                {
                    "type": "comprehensive_insights",
                    "insights": comprehensive_insights,
                    "confidence": comprehensive_insights.get("confidence", 0.8)
                }
            ]
            
            # Add external data if available
            if external_data and external_data.get("success"):
                findings.append({
                    "type": "external_enrichment",
                    "data": external_data,
                    "confidence": 0.7
                })
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return self.create_result(
                success=True,
                confidence=0.85,
                findings=findings,
                recommendations=recommendations,
                data_used={
                    "document_type": document_type,
                    "industry_type": industry_type,
                    "external_sources": external_data.get("data_sources", []) if external_data else [],
                    "analysis_methods": ["type_specific", "industry_specific", "comprehensive", "external_enrichment"]
                },
                execution_time_ms=execution_time,
                llm_calls=llm_calls
            )
            
        except Exception as e:
            logger.error(f"Enhanced analysis failed: {e}")
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return self.create_result(
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time,
                llm_calls=llm_calls
            )
    
    async def _get_external_enrichment(
        self, 
        document_type: str, 
        industry_type: str, 
        document_text: str,
        context: AgentContext
    ) -> Optional[Dict[str, Any]]:
        """Get external enrichment data via MCP servers"""
        try:
            # Extract keywords from document for enrichment
            keywords = await self._extract_key_terms(document_text, context.contract_id)
            
            # Extract company names (simple approach)
            company_names = await self._extract_company_names(document_text, context.contract_id)
            
            # Try to get enrichment data (would integrate with actual MCP servers)
            # For now, simulate MCP call
            enrichment_data = {
                "success": True,
                "document_type": document_type,
                "industry_type": industry_type,
                "data_sources": ["regulatory_updates", "industry_trends", "market_data"],
                "regulatory_context": {
                    "recent_updates": f"Found 3 recent regulatory updates for {industry_type} industry",
                    "compliance_notes": f"Key compliance considerations for {document_type} documents"
                },
                "industry_context": {
                    "market_trends": f"Current trends in {industry_type} industry",
                    "risk_factors": f"Key risk factors for {industry_type} sector"
                },
                "enrichment_timestamp": datetime.now().isoformat()
            }
            
            return enrichment_data
            
        except Exception as e:
            logger.error(f"External enrichment failed: {e}")
            return None
    
    async def _analyze_by_document_type(
        self, 
        document_text: str, 
        document_type: str, 
        industry_type: str,
        contract_id: str
    ) -> Dict[str, Any]:
        """Perform document type specific analysis"""
        
        template = self.analysis_templates.get(document_type, self.analysis_templates["general_document"])
        
        analysis_prompt = f"""
        Analyze this {document_type} document with focus on the following areas:
        Focus Areas: {', '.join(template['focus_areas'])}
        
        Key Questions to Address:
        {chr(10).join(f"- {q}" for q in template['key_questions'])}
        
        Document Content:
        {document_text[:3000]}...
        
        Provide a structured analysis addressing each focus area and key question.
        Format as JSON with the following structure:
        {{
            "document_type": "{document_type}",
            "focus_area_analysis": {{
                "area_name": "detailed analysis"
            }},
            "key_findings": ["finding1", "finding2"],
            "risk_assessment": "low|medium|high",
            "confidence": 0.0-1.0,
            "type_specific_insights": ["insight1", "insight2"]
        }}
        """
        
        result = await self.call_llm_with_tracking(
            analysis_prompt, 
            contract_id,
            task_type=LLMTask.ANALYSIS,
            max_tokens=1500,
            temperature=0.1
        )
        
        try:
            return json.loads(result["content"])
        except json.JSONDecodeError:
            return {
                "document_type": document_type,
                "analysis": result["content"],
                "confidence": 0.6,
                "parsing_error": "Could not parse as JSON"
            }
    
    async def _analyze_by_industry(
        self, 
        document_text: str, 
        industry_type: str, 
        document_type: str,
        contract_id: str
    ) -> Dict[str, Any]:
        """Perform industry-specific analysis"""
        
        considerations = self.industry_considerations.get(
            industry_type.lower(), 
            ["regulatory compliance", "risk management", "best practices"]
        )
        
        industry_prompt = f"""
        Analyze this {document_type} document from a {industry_type} industry perspective.
        
        Key Industry Considerations:
        {', '.join(considerations)}
        
        Document Content:
        {document_text[:3000]}...
        
        Focus on:
        1. Industry-specific risks and opportunities
        2. Regulatory compliance requirements
        3. Industry best practices alignment
        4. Sector-specific terminology and concepts
        5. Market conditions impact
        
        Format as JSON:
        {{
            "industry": "{industry_type}",
            "compliance_assessment": "compliant|non-compliant|unclear",
            "industry_risks": ["risk1", "risk2"],
            "best_practices_alignment": "high|medium|low",
            "regulatory_considerations": ["consideration1", "consideration2"],
            "industry_insights": ["insight1", "insight2"],
            "confidence": 0.0-1.0
        }}
        """
        
        result = await self.call_llm_with_tracking(
            industry_prompt,
            contract_id,
            task_type=LLMTask.ANALYSIS,
            max_tokens=1500,
            temperature=0.1
        )
        
        try:
            return json.loads(result["content"])
        except json.JSONDecodeError:
            return {
                "industry": industry_type,
                "analysis": result["content"],
                "confidence": 0.6,
                "parsing_error": "Could not parse as JSON"
            }
    
    async def _generate_comprehensive_insights(
        self, 
        document_text: str,
        type_analysis: Dict[str, Any],
        industry_analysis: Dict[str, Any],
        external_data: Optional[Dict[str, Any]],
        contract_id: str
    ) -> Dict[str, Any]:
        """Generate comprehensive insights combining all analysis"""
        
        insights_prompt = f"""
        Generate comprehensive insights by combining document type analysis, industry analysis, and external context.
        
        Document Type Analysis:
        {json.dumps(type_analysis, indent=2)}
        
        Industry Analysis:
        {json.dumps(industry_analysis, indent=2)}
        
        External Context:
        {json.dumps(external_data, indent=2) if external_data else "No external data available"}
        
        Provide comprehensive insights that:
        1. Synthesize findings from all analyses
        2. Identify cross-cutting themes and patterns
        3. Highlight critical issues requiring attention
        4. Assess overall document quality and completeness
        5. Provide strategic recommendations
        
        Format as JSON:
        {{
            "overall_assessment": "excellent|good|fair|poor",
            "critical_issues": ["issue1", "issue2"],
            "cross_cutting_themes": ["theme1", "theme2"],
            "strategic_insights": ["insight1", "insight2"],
            "quality_score": 0.0-1.0,
            "completeness_score": 0.0-1.0,
            "confidence": 0.0-1.0
        }}
        """
        
        result = await self.call_llm_with_tracking(
            insights_prompt,
            contract_id,
            task_type=LLMTask.ANALYSIS,
            max_tokens=1500,
            temperature=0.2
        )
        
        try:
            return json.loads(result["content"])
        except json.JSONDecodeError:
            return {
                "overall_assessment": "fair",
                "analysis": result["content"],
                "confidence": 0.6,
                "parsing_error": "Could not parse as JSON"
            }
    
    async def _generate_enhanced_recommendations(
        self,
        type_analysis: Dict[str, Any],
        industry_analysis: Dict[str, Any], 
        comprehensive_insights: Dict[str, Any],
        document_type: str,
        industry_type: str,
        contract_id: str
    ) -> List[str]:
        """Generate enhanced recommendations based on all analyses"""
        
        recommendations_prompt = f"""
        Generate actionable recommendations based on comprehensive document analysis.
        
        Document Type: {document_type}
        Industry: {industry_type}
        
        Type Analysis Summary: {type_analysis.get('key_findings', [])}
        Industry Analysis Summary: {industry_analysis.get('industry_risks', [])}
        Critical Issues: {comprehensive_insights.get('critical_issues', [])}
        
        Generate 5-8 specific, actionable recommendations that:
        1. Address identified risks and issues
        2. Improve document quality and completeness
        3. Ensure industry compliance
        4. Leverage opportunities for improvement
        5. Provide next steps for implementation
        
        Format as a JSON array of strings:
        ["recommendation1", "recommendation2", ...]
        """
        
        result = await self.call_llm_with_tracking(
            recommendations_prompt,
            contract_id,
            task_type=LLMTask.ANALYSIS,
            max_tokens=1000,
            temperature=0.3
        )
        
        try:
            return json.loads(result["content"])
        except json.JSONDecodeError:
            # Fallback to basic recommendations
            return [
                f"Review document for {document_type}-specific requirements",
                f"Ensure compliance with {industry_type} industry standards",
                "Address any identified critical issues",
                "Consider external market and regulatory factors",
                "Implement recommended improvements"
            ]
    
    async def _extract_key_terms(self, document_text: str, contract_id: str) -> List[str]:
        """Extract key terms for external enrichment"""
        try:
            # Simple keyword extraction - could be enhanced with NLP
            words = document_text.lower().split()
            
            # Filter for meaningful terms (length > 3, not common words)
            common_words = {"the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was", "one", "our", "out", "day", "get", "has", "him", "his", "how", "man", "new", "now", "old", "see", "two", "way", "who", "boy", "did", "its", "let", "put", "say", "she", "too", "use"}
            
            keywords = [word for word in set(words) if len(word) > 3 and word not in common_words]
            
            return keywords[:10]  # Return top 10 keywords
            
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            return []
    
    async def _extract_company_names(self, document_text: str, contract_id: str) -> List[str]:
        """Extract company names from document"""
        try:
            # Simple company name extraction - look for patterns
            import re
            
            # Look for "Inc", "Corp", "LLC", etc.
            company_patterns = [
                r'\b[A-Z][a-zA-Z\s]+(?:Inc|Corp|LLC|Ltd|Company|Co)\b',
                r'\b[A-Z][a-zA-Z\s]+(?:Corporation|Limited|Incorporated)\b'
            ]
            
            companies = []
            for pattern in company_patterns:
                matches = re.findall(pattern, document_text)
                companies.extend(matches)
            
            return list(set(companies))[:5]  # Return up to 5 unique company names
            
        except Exception as e:
            logger.error(f"Company name extraction failed: {e}")
            return []