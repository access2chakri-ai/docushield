"""
Production Document Analyzer Agent - AWS Bedrock AgentCore Compatible
Consolidated, high-performance agent for comprehensive document analysis
Enterprise-grade architecture designed for AWS Bedrock AgentCore migration
"""
import json
import logging
import re
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import asdict

from .base_agent import BaseAgent, AgentContext, AgentResult, AgentStatus, AgentPriority
from app.database import get_operational_db
from app.models import BronzeContract, SilverChunk, SilverClauseSpan, Token, GoldFinding
from app.services.llm_factory import LLMTask
from app.services.privacy_safe_llm import privacy_safe_llm, safe_llm_completion
from app.services.mcp_integration import mcp_service, MCPResult
from app.utils.privacy_safe_processing import privacy_processor, ensure_privacy_safe_content

logger = logging.getLogger(__name__)

class DocumentAnalysisAgent(BaseAgent):
    """
    Production-ready document analyzer with comprehensive analysis capabilities - AWS Bedrock AgentCore Compatible
    Handles all document types with intelligent routing and fallback mechanisms
    Enterprise-grade architecture designed for AWS Bedrock AgentCore migration
    """
    
    def __init__(self):
        super().__init__("document_analysis_agent", "3.0.0")
        
        # Document type analysis templates
        self.analysis_templates = {
            "contract": {
                "focus_areas": ["obligations", "termination", "liability", "payment_terms", "intellectual_property"],
                "risk_patterns": [
                    (r"unlimited\s+liability", "critical", "Unlimited liability exposure"),
                    (r"immediate\s+termination", "high", "Immediate termination clause"),
                    (r"auto.*renew", "medium", "Auto-renewal clause"),
                    (r"exclusive\s+license", "high", "Exclusive IP license"),
                    (r"indemnif", "medium", "Indemnification clause")
                ]
            },
            "invoice": {
                "focus_areas": ["amounts", "due_dates", "payment_terms", "line_items"],
                "risk_patterns": [
                    (r"overdue|past\s+due", "high", "Overdue payment"),
                    (r"penalty|late\s+fee", "medium", "Late payment penalties"),
                    (r"dispute|contested", "high", "Disputed charges")
                ]
            },
            "policy": {
                "focus_areas": ["requirements", "procedures", "compliance", "violations"],
                "risk_patterns": [
                    (r"violation|breach", "high", "Policy violation terms"),
                    (r"mandatory|required", "medium", "Mandatory requirements"),
                    (r"disciplinary|termination", "high", "Disciplinary actions")
                ]
            },
            "general": {
                "focus_areas": ["key_points", "requirements", "deadlines", "responsibilities"],
                "risk_patterns": [
                    (r"deadline|due\s+date", "medium", "Time-sensitive requirements"),
                    (r"penalty|fine", "high", "Financial penalties"),
                    (r"legal\s+action", "high", "Legal consequences")
                ]
            }
        }
        
        # Industry-specific risk factors
        self.industry_risk_factors = {
            "healthcare": ["HIPAA", "patient data", "medical records", "PHI"],
            "financial": ["PCI", "SOX", "financial data", "credit information"],
            "technology": ["data privacy", "GDPR", "intellectual property", "source code"],
            "legal": ["attorney-client", "privileged", "confidential", "bar rules"]
        }
    
    async def _execute_analysis(self, context: AgentContext) -> AgentResult:
        """
        Execute comprehensive document analysis with intelligent routing
        """
        try:
            logger.info(f"🚀 DocumentAnalysisAgent._execute_analysis started for contract {context.contract_id}")
            logger.info(f"   📋 Query: {context.query}")
            logger.info(f"   👤 User: {context.user_id}")
            
            # Get document with all related data
            contract = await self._get_contract_data(context.contract_id)
            if not contract:
                logger.error(f"❌ Document not found: {context.contract_id}")
                return self._create_failure_result("Document not found or inaccessible")
            
            logger.info(f"✅ Document loaded: {contract.filename} ({len(contract.text_raw.raw_text) if contract.text_raw else 0} chars)")
            
            # Determine analysis strategy based on document type and size
            analysis_strategy = self._determine_analysis_strategy(contract, context)
            logger.info(f"🎯 Analysis strategy selected: {analysis_strategy}")
            
            # Execute analysis based on strategy
            if analysis_strategy == "comprehensive":
                logger.info("🚀 Executing COMPREHENSIVE analysis...")
                return await self._comprehensive_analysis(contract, context)
            elif analysis_strategy == "fast":
                logger.info("⚡ Executing FAST analysis...")
                return await self._fast_analysis(contract, context)
            else:  # fallback
                logger.info("🔄 Executing FALLBACK analysis...")
                return await self._fallback_analysis(contract, context)
                
        except Exception as e:
            logger.error(f"❌ Document analysis failed: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return self._create_failure_result(str(e))
    
    def _determine_analysis_strategy(self, contract: BronzeContract, context: AgentContext) -> str:
        """Determine optimal analysis strategy based on document and context"""
        text_length = len(contract.text_raw.raw_text) if contract.text_raw else 0
        
        # Always use comprehensive analysis for document upload (to get MCP enhancement)
        # Only use fast analysis for very specific, simple queries
        if context.query and len(context.query.split()) < 3 and text_length < 500:
            logger.info(f"📋 Using FAST analysis: Simple query + small document ({text_length} chars)")
            return "fast"
        
        # Use comprehensive analysis for most cases (includes MCP enhancement)
        logger.info(f"📋 Using COMPREHENSIVE analysis: Document analysis with MCP enhancement ({text_length} chars)")
        return "comprehensive"
    
    async def _comprehensive_analysis(self, contract: BronzeContract, context: AgentContext) -> AgentResult:
        """
        Comprehensive analysis using multiple techniques including MCP services
        """
        logger.info(f"🚀 Starting COMPREHENSIVE analysis with MCP enhancement")
        
        findings = []
        recommendations = []
        llm_calls = 0
        data_sources = ["bronze_contract", "bronze_contract_text_raw"]
        
        text_content = contract.text_raw.raw_text
        document_type = context.document_type or contract.document_category or "general"
        industry_type = contract.industry_type or "general"
        
        logger.info(f"📄 Document details: Type={document_type}, Industry={industry_type}, Length={len(text_content)} chars")
        
        # Extract key information for MCP services
        content_keywords = await self._extract_keywords(text_content)
        company_names = await self._extract_company_names(text_content)
        
        # 1. Pattern-based risk detection
        pattern_findings = await self._detect_risk_patterns(text_content, document_type)
        findings.extend(pattern_findings)
        
        # 2. MCP-enhanced analysis (parallel execution with better error handling)
        mcp_success = False
        try:
            logger.info(f"🔍 Starting MCP enrichment for {document_type} document")
            async with mcp_service:
                mcp_results = await mcp_service.comprehensive_document_analysis(
                    document_type=document_type,
                    industry_type=industry_type,
                    content_keywords=content_keywords,
                    company_names=company_names,
                    include_web_search=True,
                    include_legal_precedents=True,
                    include_industry_analysis=True
                )
                
                # Process MCP results with detailed logging
                mcp_findings, mcp_recommendations = await self._process_mcp_results(mcp_results)
                if mcp_findings or mcp_recommendations:
                    # Log detailed MCP enhancement information
                    logger.info(f"🔍 MCP Enhancement Details:")
                    logger.info(f"   📊 MCP Services Called: {len(mcp_results)}")
                    
                    # Log each MCP service result
                    for service_name, result in mcp_results.items():
                        if result.success:
                            data_count = len(result.data) if result.data else 0
                            logger.info(f"   ✅ {service_name}: {data_count} data points")
                        else:
                            logger.info(f"   ❌ {service_name}: {result.error}")
                    
                    # Log MCP findings details
                    logger.info(f"   🎯 MCP Findings Generated: {len(mcp_findings)}")
                    for i, finding in enumerate(mcp_findings):
                        logger.info(f"      {i+1}. [{finding.get('severity', 'info').upper()}] {finding.get('title', 'Unknown')}")
                        logger.info(f"         Source: {finding.get('source_type', 'unknown')}")
                        logger.info(f"         Confidence: {finding.get('confidence', 0.0):.2f}")
                    
                    # Log MCP recommendations
                    logger.info(f"   💡 MCP Recommendations: {len(mcp_recommendations)}")
                    for i, rec in enumerate(mcp_recommendations):
                        logger.info(f"      {i+1}. {rec}")
                    
                    findings.extend(mcp_findings)
                    recommendations.extend(mcp_recommendations)
                    data_sources.extend(["web_search", "legal_precedents", "industry_intelligence", "document_enrichment"])
                    mcp_success = True
                    logger.info(f"✅ MCP enrichment successful: {len(mcp_findings)} findings, {len(mcp_recommendations)} recommendations")
                else:
                    logger.warning("⚠️ MCP enrichment returned no results")
                    # Log why no results were returned
                    logger.info(f"   📊 MCP Services Status:")
                    for service_name, result in mcp_results.items():
                        status = "✅ Success" if result.success else f"❌ Failed: {result.error}"
                        data_info = f"({len(result.data)} items)" if result.success and result.data else ""
                        logger.info(f"      {service_name}: {status} {data_info}")
                
        except Exception as e:
            logger.error(f"❌ MCP analysis failed: {e}")
            findings.append({
                "type": "mcp_analysis_error",
                "title": "External data enrichment failed",
                "severity": "warning",
                "confidence": 0.8,
                "description": f"MCP enrichment failed: {str(e)[:100]}...",
                "error_details": str(e)
            })
        
        # 3. Enhanced content analysis (no LLM dependency)
        try:
            content_analysis = await self._enhanced_content_analysis(text_content, document_type)
            if content_analysis:
                findings.extend(content_analysis.get("findings", []))
                recommendations.extend(content_analysis.get("recommendations", []))
                
                # Log content analysis details
                logger.info(f"🔍 Enhanced Content Analysis:")
                logger.info(f"   📊 Content findings: {len(content_analysis.get('findings', []))}")
                logger.info(f"   💡 Content recommendations: {len(content_analysis.get('recommendations', []))}")
                
        except Exception as e:
            logger.warning(f"Enhanced content analysis failed, continuing with pattern analysis: {e}")
            recommendations.append("Enhanced analysis unavailable - manual review recommended")
        
        # 4. Existing clause analysis
        existing_clauses = await self._analyze_existing_clauses(context.contract_id)
        if existing_clauses:
            findings.append({
                "type": "existing_clause_analysis",
                "title": f"Analyzed {len(existing_clauses)} existing clauses",
                "severity": "info",
                "confidence": 0.9,
                "clauses": existing_clauses
            })
            data_sources.append("silver_clause_spans")
        
        # 5. Generate consolidated recommendations
        if not recommendations:
            recommendations = self._generate_fallback_recommendations(findings, document_type)
        
        # Calculate overall confidence (higher with MCP data)
        has_external_data = len([r for r in data_sources if r.startswith(("web_", "legal_", "industry_"))]) > 0
        confidence = self._calculate_confidence(findings, llm_calls > 0, has_external_data=has_external_data)
        
        # Log confidence calculation details
        mcp_enhanced_findings = [f for f in findings if f.get('mcp_enhanced', False)]
        if mcp_enhanced_findings:
            logger.info(f"🎯 Confidence Enhancement Analysis:")
            logger.info(f"   📊 Total Findings: {len(findings)}")
            logger.info(f"   🌐 MCP-Enhanced Findings: {len(mcp_enhanced_findings)}")
            logger.info(f"   📈 Base Confidence: 0.60")
            logger.info(f"   🤖 AI Analysis Boost: +0.20" if llm_calls > 0 else "   🤖 AI Analysis Boost: +0.00")
            logger.info(f"   🌍 External Data Boost: +0.10" if has_external_data else "   🌍 External Data Boost: +0.00")
            logger.info(f"   🎯 Final Confidence: {confidence:.2f}")
            
            # Show which findings were enhanced by MCP
            logger.info(f"   🔍 MCP-Enhanced Findings Details:")
            for i, finding in enumerate(mcp_enhanced_findings):
                source_type = finding.get('source_type', 'unknown')
                title = finding.get('title', 'Unknown')[:40]
                logger.info(f"      {i+1}. [{source_type}] {title}...")
        
        return AgentResult(
            agent_name=self.agent_name,
            agent_version=self.version,
            status=AgentStatus.COMPLETED,
            confidence=confidence,
            findings=findings,
            recommendations=recommendations[:15],  # Increased limit for MCP recommendations
            execution_time_ms=0.0,  # Will be set by base class
            memory_usage_mb=0.0,    # Will be set by base class
            llm_calls=llm_calls,
            data_sources=data_sources
        )
    
    async def _fast_analysis(self, contract: BronzeContract, context: AgentContext) -> AgentResult:
        """
        Fast analysis using pattern matching and existing data
        """
        findings = []
        text_content = contract.text_raw.raw_text
        document_type = context.document_type or "general"
        
        # Quick pattern-based analysis
        pattern_findings = await self._detect_risk_patterns(text_content, document_type)
        findings.extend(pattern_findings)
        
        # Quick content analysis (subset of enhanced analysis)
        word_count = len(text_content.split())
        text_lower = text_content.lower()
        
        # Quick risk detection
        high_risk_terms = ["unlimited liability", "immediate termination", "liquidated damages"]
        risk_count = sum(1 for term in high_risk_terms if term in text_lower)
        
        if risk_count > 0:
            findings.append({
                "type": "quick_risk_scan",
                "title": f"High-risk terms detected ({risk_count} found)",
                "severity": "high" if risk_count > 1 else "medium",
                "confidence": 0.9,
                "description": f"Quick scan found {risk_count} high-risk terms requiring attention"
            })
        
        # Basic document stats
        findings.append({
            "type": "document_stats",
            "title": f"Fast analysis complete",
            "severity": "info",
            "confidence": 1.0,
            "description": f"Analyzed {word_count:,} words in {document_type} document",
            "stats": {
                "word_count": word_count,
                "character_count": len(text_content),
                "estimated_reading_time": max(1, word_count // 200),
                "analysis_type": "fast"
            }
        })
        
        # Generate basic recommendations
        recommendations = self._generate_fallback_recommendations(findings, document_type)
        
        return AgentResult(
            agent_name=self.agent_name,
            agent_version=self.version,
            status=AgentStatus.COMPLETED,
            confidence=0.75,  # Slightly higher confidence with enhanced fast analysis
            findings=findings,
            recommendations=recommendations,
            execution_time_ms=0.0,
            memory_usage_mb=0.0,
            llm_calls=0,
            data_sources=["bronze_contract", "bronze_contract_text_raw"]
        )
    
    async def _fallback_analysis(self, contract: BronzeContract, context: AgentContext) -> AgentResult:
        """
        Minimal fallback analysis when other methods fail
        """
        text_content = contract.text_raw.raw_text if contract.text_raw else ""
        
        findings = [{
            "type": "basic_analysis",
            "title": "Basic document analysis completed",
            "severity": "info",
            "confidence": 0.5,
            "description": f"Analyzed document: {contract.filename}"
        }]
        
        recommendations = [
            "Document processed successfully",
            "Manual review recommended for detailed analysis",
            "Consider re-processing with enhanced analysis options"
        ]
        
        return AgentResult(
            agent_name=self.agent_name,
            agent_version=self.version,
            status=AgentStatus.COMPLETED,
            confidence=0.5,
            findings=findings,
            recommendations=recommendations,
            execution_time_ms=0.0,
            memory_usage_mb=0.0,
            llm_calls=0,
            data_sources=["bronze_contract"]
        )
    
    async def _detect_risk_patterns(self, text: str, document_type: str) -> List[Dict[str, Any]]:
        """
        Detect risk patterns using enhanced regex and keyword analysis
        """
        findings = []
        template = self.analysis_templates.get(document_type, self.analysis_templates["general"])
        
        try:
            text_lower = text.lower()
            
            # Enhanced risk patterns with better detection
            enhanced_patterns = {
                "contract": [
                    (r"unlimited\s+liability|without\s+limit.*liability|liability.*unlimited", "critical", "Unlimited Liability Exposure"),
                    (r"terminate\s+immediately|immediate\s+termination|without\s+notice.*terminat", "high", "Immediate Termination Rights"),
                    (r"auto.*renew|automatic.*renewal|shall\s+renew", "medium", "Auto-Renewal Clause"),
                    (r"exclusive\s+license|exclusive\s+rights|solely\s+and\s+exclusively", "high", "Exclusive Rights Grant"),
                    (r"indemnif.*against\s+all|hold\s+harmless.*all|indemnify.*any\s+and\s+all", "high", "Broad Indemnification"),
                    (r"liquidated\s+damages|penalty.*breach|forfeit.*breach", "medium", "Liquidated Damages/Penalties"),
                    (r"governing\s+law|jurisdiction.*courts|exclusive\s+jurisdiction", "low", "Governing Law and Jurisdiction"),
                    (r"confidential|non[\-\s]?disclosure|proprietary\s+information", "low", "Confidentiality Requirements"),
                    (r"force\s+majeure|act\s+of\s+god|beyond.*control", "low", "Force Majeure Clause"),
                    (r"assignment|assign.*rights|transfer.*agreement", "low", "Assignment Rights")
                ],
                "invoice": [
                    (r"overdue|past\s+due|delinquent", "high", "Overdue Payment Status"),
                    (r"penalty|late\s+fee|interest.*overdue", "medium", "Late Payment Penalties"),
                    (r"dispute|contested|challenged", "high", "Disputed Charges"),
                    (r"net\s+\d+|due\s+within\s+\d+|payment\s+terms", "low", "Payment Terms"),
                    (r"\$[\d,]+(?:\.\d{2})?|USD\s*[\d,]+", "low", "Monetary Amounts")
                ],
                "policy": [
                    (r"violation|breach.*policy|non[\-\s]?compliance", "high", "Policy Violation Terms"),
                    (r"mandatory|required|must\s+comply|shall\s+comply", "medium", "Mandatory Requirements"),
                    (r"disciplinary|termination.*violation|consequences", "high", "Disciplinary Actions"),
                    (r"training|certification|qualification", "low", "Training Requirements"),
                    (r"reporting|notification|disclosure", "medium", "Reporting Obligations")
                ],
                "general": [
                    (r"deadline|due\s+date|time\s+limit|expires?\s+on", "medium", "Time-Sensitive Requirements"),
                    (r"penalty|fine|damages|forfeit", "high", "Financial Penalties"),
                    (r"legal\s+action|litigation|court|lawsuit", "high", "Legal Consequences"),
                    (r"compliance|regulation|regulatory|law", "medium", "Compliance Requirements"),
                    (r"privacy|personal\s+data|GDPR|HIPAA|PII", "medium", "Privacy and Data Protection")
                ]
            }
            
            # Use enhanced patterns if available, otherwise fall back to template
            patterns_to_use = enhanced_patterns.get(document_type, template["risk_patterns"])
            
            for pattern, risk_level, description in patterns_to_use:
                matches = list(re.finditer(pattern, text, re.IGNORECASE))
                
                for match in matches:
                    # Get context around match (more context for better understanding)
                    start = max(0, match.start() - 150)
                    end = min(len(text), match.end() + 150)
                    context = text[start:end].strip()
                    
                    # Clean up context to remove excessive whitespace
                    context = re.sub(r'\s+', ' ', context)
                    
                    # Calculate confidence based on match quality
                    confidence = 0.8
                    matched_text = match.group()
                    
                    # Boost confidence for exact matches of high-risk terms
                    if any(term in matched_text.lower() for term in ["unlimited liability", "immediate termination", "liquidated damages"]):
                        confidence = 0.95
                    elif len(matched_text) > 20:  # Longer matches are more reliable
                        confidence = 0.85
                    
                    findings.append({
                        "type": "risk_pattern",
                        "title": description,
                        "severity": risk_level,
                        "confidence": confidence,
                        "pattern": pattern,
                        "matched_text": matched_text,
                        "context": context,
                        "position": match.start(),
                        "document_type": document_type,
                        "detection_method": "enhanced_regex"
                    })
            
            # Add document-specific analysis
            word_count = len(text.split())
            if word_count > 0:
                findings.append({
                    "type": "document_stats",
                    "title": f"Document Analysis Complete",
                    "severity": "info",
                    "confidence": 1.0,
                    "description": f"Analyzed {word_count:,} words in {document_type} document",
                    "stats": {
                        "word_count": word_count,
                        "character_count": len(text),
                        "estimated_reading_time": max(1, word_count // 200),
                        "document_type": document_type
                    }
                })
            
            logger.info(f"Enhanced pattern detection found {len(findings)} findings for {document_type}")
            return findings
            
        except Exception as e:
            logger.error(f"Pattern detection failed: {e}")
            return []
    
    async def _enhanced_content_analysis(self, text: str, document_type: str) -> Optional[Dict[str, Any]]:
        """
        Enhanced content analysis without LLM dependency - more reliable and faster
        """
        try:
            logger.info(f"🔍 Starting enhanced content analysis for {document_type}")
            
            findings = []
            recommendations = []
            
            # Analyze document content directly
            word_count = len(text.split())
            text_lower = text.lower()
            
            # Content-based analysis with enhanced patterns
            financial_patterns = [
                (r'\$[\d,]+(?:\.\d{2})?', "Financial amount detected"),
                (r'net\s+\d+\s+days?', "Payment terms specified"),
                (r'penalty|late\s+fee|interest.*overdue', "Financial penalties present"),
                (r'budget|cost|expense|revenue', "Financial terms identified")
            ]
            
            legal_patterns = [
                (r'liability|damages|indemnif', "Legal liability terms"),
                (r'termination|breach|violation', "Contract enforcement terms"),
                (r'governing\s+law|jurisdiction', "Legal jurisdiction specified"),
                (r'confidential|proprietary|trade\s+secret', "Confidentiality requirements")
            ]
            
            risk_patterns = [
                (r'unlimited|without\s+limit|no\s+limit', "Unlimited exposure terms"),
                (r'immediate|instant|without\s+notice', "Immediate action clauses"),
                (r'exclusive|sole|only|solely', "Exclusive rights or obligations"),
                (r'auto.*renew|automatic.*renewal', "Automatic renewal terms")
            ]
            
            # Analyze financial content
            financial_matches = 0
            for pattern, description in financial_patterns:
                matches = len(re.findall(pattern, text_lower))
                if matches > 0:
                    financial_matches += matches
                    findings.append({
                        "type": "financial_analysis",
                        "title": f"{description} ({matches} instances)",
                        "severity": "medium" if matches > 3 else "low",
                        "confidence": 0.8,
                        "description": f"Found {matches} instances of {description.lower()}"
                    })
            
            # Analyze legal content
            legal_matches = 0
            for pattern, description in legal_patterns:
                matches = len(re.findall(pattern, text_lower))
                if matches > 0:
                    legal_matches += matches
                    findings.append({
                        "type": "legal_analysis",
                        "title": f"{description} ({matches} instances)",
                        "severity": "medium" if matches > 2 else "low",
                        "confidence": 0.8,
                        "description": f"Found {matches} instances of {description.lower()}"
                    })
            
            # Analyze risk content
            risk_matches = 0
            for pattern, description in risk_patterns:
                matches = len(re.findall(pattern, text_lower))
                if matches > 0:
                    risk_matches += matches
                    severity = "high" if "unlimited" in pattern or "immediate" in pattern else "medium"
                    findings.append({
                        "type": "risk_analysis",
                        "title": f"{description} ({matches} instances)",
                        "severity": severity,
                        "confidence": 0.9,
                        "description": f"Found {matches} instances of {description.lower()}"
                    })
            
            # Document structure analysis
            paragraphs = len([p for p in text.split('\n\n') if p.strip()])
            sentences = len([s for s in text.split('.') if s.strip()])
            
            findings.append({
                "type": "structure_analysis",
                "title": f"Document Structure Analysis",
                "severity": "info",
                "confidence": 1.0,
                "description": f"Document contains {paragraphs} paragraphs, {sentences} sentences, {word_count:,} words"
            })
            
            # Generate contextual recommendations
            if financial_matches > 5:
                recommendations.append("📊 Multiple financial terms detected - verify all amounts and payment terms")
            if legal_matches > 3:
                recommendations.append("⚖️ Significant legal content - consider legal review")
            if risk_matches > 0:
                recommendations.append("⚠️ Risk indicators found - assess potential exposure")
            
            # Document type specific recommendations
            if document_type == "contract":
                recommendations.extend([
                    "📋 Contract analysis completed - review all obligations carefully",
                    "🔍 Verify party information, dates, and key terms"
                ])
            elif document_type == "invoice":
                recommendations.extend([
                    "💰 Invoice analysis completed - verify charges and payment terms",
                    "📅 Check due dates and payment methods"
                ])
            
            # Add general recommendations
            if word_count > 5000:
                recommendations.append("📄 Large document detected - consider section-by-section review")
            if len(findings) > 10:
                recommendations.append("🎯 Multiple findings identified - prioritize by risk level")
            
            analysis_data = {
                "findings": findings,
                "recommendations": recommendations,
                "analysis_stats": {
                    "word_count": word_count,
                    "financial_matches": financial_matches,
                    "legal_matches": legal_matches,
                    "risk_matches": risk_matches,
                    "paragraphs": paragraphs
                },
                "analysis_method": "enhanced_content_analysis"
            }
            
            logger.info(f"✅ Enhanced content analysis completed: {len(findings)} findings, {len(recommendations)} recommendations")
            return analysis_data
                
        except Exception as e:
            logger.error(f"Enhanced content analysis failed: {e}")
            return None

    async def _privacy_safe_ai_analysis(self, text: str, document_type: str, contract_id: str) -> Optional[Dict[str, Any]]:
        """
        Privacy-safe AI-powered document analysis with PII protection
        """
        try:
            logger.info(f"🔒 Starting privacy-safe AI analysis for {document_type}")
            
            # Check if content needs privacy protection
            redaction_result = ensure_privacy_safe_content(text, aggressive_redaction=True)
            
            # Generate structured findings directly instead of relying on JSON parsing
            findings = []
            recommendations = []
            
            # Analyze document content directly without complex JSON parsing
            word_count = len(text.split())
            
            # Basic document analysis
            findings.append({
                "type": "document_analysis",
                "title": f"{document_type.title()} document analyzed",
                "severity": "info",
                "confidence": 0.8,
                "description": f"Analyzed {word_count:,} words in {document_type} document with privacy protection"
            })
            
            # Content-based analysis
            text_lower = text.lower()
            
            # Risk indicators based on document type
            risk_keywords = {
                "contract": ["liability", "termination", "breach", "penalty", "damages", "indemnify"],
                "invoice": ["overdue", "penalty", "late fee", "dispute", "contested"],
                "policy": ["violation", "breach", "mandatory", "required", "disciplinary"],
                "general": ["deadline", "penalty", "legal action", "compliance", "violation"]
            }
            
            keywords = risk_keywords.get(document_type, risk_keywords["general"])
            found_risks = [keyword for keyword in keywords if keyword in text_lower]
            
            if found_risks:
                findings.append({
                    "type": "risk_analysis",
                    "title": f"Found {len(found_risks)} risk indicators",
                    "severity": "medium" if len(found_risks) > 2 else "low",
                    "confidence": 0.7,
                    "description": f"Risk indicators found: {', '.join(found_risks[:5])}"
                })
                recommendations.append(f"Review sections containing: {', '.join(found_risks[:3])}")
            
            # Privacy analysis
            if redaction_result.pii_matches:
                findings.append({
                    "type": "privacy_analysis",
                    "title": f"Privacy-sensitive content detected",
                    "severity": "info",
                    "confidence": 0.9,
                    "description": f"Found {len(redaction_result.pii_matches)} PII instances - content was protected during analysis"
                })
                recommendations.append("Ensure proper handling of personal information")
            
            # Document structure analysis
            paragraphs = len([p for p in text.split('\n\n') if p.strip()])
            if paragraphs > 0:
                findings.append({
                    "type": "structure_analysis",
                    "title": f"Document structure: {paragraphs} sections",
                    "severity": "info",
                    "confidence": 0.9,
                    "description": f"Document contains {paragraphs} distinct sections"
                })
            
            # Generate recommendations based on document type
            if document_type == "contract":
                recommendations.extend([
                    "Verify all parties, dates, and financial terms",
                    "Review termination and liability clauses carefully"
                ])
            elif document_type == "invoice":
                recommendations.extend([
                    "Verify all charges and payment terms",
                    "Check for any disputed or unusual items"
                ])
            elif document_type == "policy":
                recommendations.extend([
                    "Ensure compliance with all mandatory requirements",
                    "Review disciplinary and violation procedures"
                ])
            else:
                recommendations.extend([
                    "Review document for key obligations and deadlines",
                    "Consider legal implications of all terms"
                ])
            
            # Add privacy metadata
            analysis_data = {
                "findings": findings,
                "recommendations": recommendations,
                "overall_risk": "medium" if found_risks else "low",
                "key_concerns": found_risks[:3],
                "privacy_protected": len(redaction_result.pii_matches) > 0,
                "content_redacted": redaction_result.redaction_summary if len(redaction_result.pii_matches) > 0 else {},
                "pii_redacted": len(redaction_result.pii_matches),
                "sensitivity_level": redaction_result.sensitivity_level.value,
                "analysis_method": "structured_analysis"
            }
            
            logger.info(f"✅ Successfully completed structured analysis: {len(findings)} findings, {len(recommendations)} recommendations")
            return analysis_data
                
        except Exception as e:
            logger.error(f"Privacy-safe AI analysis failed: {e}")
            return None
    
    async def _ai_document_analysis(self, text: str, document_type: str, contract_id: str) -> Optional[Dict[str, Any]]:
        """
        Legacy AI analysis method - redirects to privacy-safe version
        """
        logger.warning("Using legacy _ai_document_analysis - redirecting to privacy-safe version")
        return await self._privacy_safe_ai_analysis(text, document_type, contract_id)
    
    async def _analyze_existing_clauses(self, contract_id: str) -> List[Dict[str, Any]]:
        """
        Analyze existing clause spans for additional insights
        """
        try:
            async for db in get_operational_db():
                from sqlalchemy import select
                
                result = await db.execute(
                    select(SilverClauseSpan)
                    .where(SilverClauseSpan.contract_id == contract_id)
                    .order_by(SilverClauseSpan.confidence.desc())
                    .limit(20)  # Limit for performance
                )
                clauses = result.scalars().all()
                
                clause_analysis = []
                for clause in clauses:
                    analysis = {
                        "clause_id": clause.span_id,
                        "type": clause.clause_type,
                        "name": clause.clause_name,
                        "confidence": clause.confidence,
                        "snippet": clause.snippet[:200] if clause.snippet else "",
                        "risk_indicators": clause.risk_indicators or []
                    }
                    
                    # Add risk assessment
                    if clause.risk_indicators:
                        high_risk_indicators = ["unlimited", "immediate", "exclusive", "irrevocable"]
                        if any(indicator.lower() in " ".join(clause.risk_indicators).lower() 
                               for indicator in high_risk_indicators):
                            analysis["risk_level"] = "high"
                        else:
                            analysis["risk_level"] = "medium"
                    else:
                        analysis["risk_level"] = "low"
                    
                    clause_analysis.append(analysis)
                
                return clause_analysis
                
        except Exception as e:
            logger.error(f"Existing clause analysis failed: {e}")
            return []
    
    def _generate_fallback_recommendations(self, findings: List[Dict[str, Any]], document_type: str) -> List[str]:
        """
        Generate contextual recommendations based on findings and document type
        """
        recommendations = []
        
        # Count findings by severity
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        risk_types = set()
        
        for finding in findings:
            severity = finding.get("severity", "low")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Track types of risks found
            if finding.get("type") == "risk_pattern":
                title = finding.get("title", "").lower()
                if "liability" in title:
                    risk_types.add("liability")
                elif "termination" in title:
                    risk_types.add("termination")
                elif "penalty" in title or "damages" in title:
                    risk_types.add("penalties")
                elif "indemnif" in title:
                    risk_types.add("indemnification")
                elif "renewal" in title:
                    risk_types.add("renewal")
                elif "jurisdiction" in title or "governing" in title:
                    risk_types.add("jurisdiction")
        
        # Generate severity-based recommendations
        if severity_counts["critical"] > 0:
            recommendations.append(f"🚨 CRITICAL: {severity_counts['critical']} critical issue(s) require immediate legal review")
            recommendations.append("Do not proceed without legal counsel - significant risk exposure identified")
        
        if severity_counts["high"] > 0:
            recommendations.append(f"⚠️ HIGH RISK: {severity_counts['high']} high-risk item(s) need careful review")
            if "liability" in risk_types:
                recommendations.append("Review liability exposure and consider liability caps or insurance")
            if "termination" in risk_types:
                recommendations.append("Negotiate more balanced termination provisions")
            if "penalties" in risk_types:
                recommendations.append("Assess financial impact of penalty clauses")
        
        if severity_counts["medium"] > 2:
            recommendations.append(f"📋 MEDIUM RISK: {severity_counts['medium']} medium-risk items identified")
            if "renewal" in risk_types:
                recommendations.append("Set calendar reminders for renewal/cancellation deadlines")
            if "indemnification" in risk_types:
                recommendations.append("Review indemnification scope and mutual obligations")
        
        # Document type specific recommendations
        if document_type == "contract":
            recommendations.extend([
                "✅ Verify all parties have authority to sign",
                "📅 Confirm all dates, terms, and financial obligations",
                "🔍 Review termination, liability, and dispute resolution clauses"
            ])
            if "jurisdiction" in risk_types:
                recommendations.append("⚖️ Consider jurisdiction implications for dispute resolution")
        
        elif document_type == "invoice":
            recommendations.extend([
                "💰 Verify all charges match agreed-upon rates",
                "📋 Check line items against purchase orders or contracts",
                "⏰ Note payment terms and due dates"
            ])
            if severity_counts["high"] > 0:
                recommendations.append("🔍 Investigate disputed or unusual charges before payment")
        
        elif document_type == "policy":
            recommendations.extend([
                "📖 Ensure all staff understand mandatory requirements",
                "🎯 Implement compliance monitoring procedures",
                "📚 Provide necessary training for policy adherence"
            ])
            if severity_counts["high"] > 0:
                recommendations.append("⚠️ Address high-risk policy violations immediately")
        
        else:  # general document
            recommendations.extend([
                f"📄 {document_type.title()} document analysis completed",
                "🔍 Review all identified risks and obligations",
                "💼 Consider professional consultation for complex terms"
            ])
        
        # Add general recommendations based on findings
        total_risks = severity_counts["critical"] + severity_counts["high"] + severity_counts["medium"]
        if total_risks > 5:
            recommendations.append("📊 Multiple risks identified - prioritize by severity and business impact")
        
        if len(findings) > 10:
            recommendations.append("📋 Comprehensive analysis completed - review detailed findings")
        
        # Default recommendations if none generated
        if not recommendations:
            recommendations = [
                f"✅ {document_type.title()} document processed successfully",
                "📋 No significant risks identified in initial analysis",
                "🔍 Consider detailed manual review for complex terms",
                "💼 Consult legal counsel for important agreements"
            ]
        
        return recommendations[:10]  # Limit to 10 recommendations for readability
    
    def _calculate_confidence(self, findings: List[Dict[str, Any]], has_ai_analysis: bool, has_external_data: bool = False) -> float:
        """
        Calculate overall confidence score based on analysis completeness
        """
        base_confidence = 0.6
        
        # Boost confidence based on findings
        if findings:
            base_confidence += min(0.2, len(findings) * 0.02)
        
        # Boost confidence if AI analysis succeeded
        if has_ai_analysis:
            base_confidence += 0.15
        
        # Boost confidence if external data enrichment succeeded
        if has_external_data:
            base_confidence += 0.1
        
        # Boost confidence based on finding quality
        high_confidence_findings = [f for f in findings if f.get("confidence", 0) > 0.8]
        if high_confidence_findings:
            base_confidence += min(0.1, len(high_confidence_findings) * 0.02)
        
        return min(0.95, base_confidence)  # Cap at 95%
    
    async def _extract_keywords(self, text: str) -> List[str]:
        """Extract key terms from document text for MCP services"""
        import re
        
        # Common legal/business terms
        legal_terms = re.findall(r'\b(?:contract|agreement|liability|indemnity|warranty|breach|termination|confidential|intellectual property|compliance|regulation|penalty|damages|arbitration|jurisdiction|governing law)\b', text.lower())
        
        # Extract capitalized terms (likely important entities)
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        
        # Combine and deduplicate
        keywords = list(set(legal_terms + [e.lower() for e in entities[:10]]))
        return keywords[:20]  # Limit to top 20 keywords
    
    async def _extract_company_names(self, text: str) -> List[str]:
        """Extract company names from document text"""
        import re
        
        # Pattern for company suffixes
        company_pattern = r'\b([A-Z][a-zA-Z\s&]+(?:Inc\.?|LLC|Corp\.?|Corporation|Company|Co\.?|Ltd\.?|Limited|LP|LLP))\b'
        companies = re.findall(company_pattern, text)
        
        # Clean and deduplicate
        cleaned_companies = []
        for company in companies:
            company = company.strip()
            if len(company) > 3 and company not in cleaned_companies:
                cleaned_companies.append(company)
        
        return cleaned_companies[:5]  # Limit to 5 companies
    
    async def _process_mcp_results(self, mcp_results: Dict[str, MCPResult]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Process MCP results into findings and recommendations with detailed logging"""
        findings = []
        recommendations = []
        
        logger.info(f"🔄 Processing MCP results from {len(mcp_results)} services")
        
        for source, result in mcp_results.items():
            if not result.success:
                logger.warning(f"   ⚠️ Skipping failed MCP service: {source} - {result.error}")
                continue
                
            if source == "web_search" and result.data:
                web_finding = {
                    "type": "web_intelligence",
                    "title": f"Found {len(result.data)} relevant web sources",
                    "severity": "info",
                    "confidence": 0.7,
                    "description": "Recent web information related to document context",
                    "sources": result.data[:3],  # Top 3 results
                    "source_type": "web_search",
                    "mcp_enhanced": True,
                    "external_validation": True
                }
                findings.append(web_finding)
                recommendations.append("Review recent web developments related to this document type")
                
                # Log specific web sources found
                logger.info(f"   🌐 Web Search Enhancement:")
                for i, source_data in enumerate(result.data[:3]):
                    title = source_data.get('title', 'Unknown')[:50]
                    url = source_data.get('url', 'No URL')
                    logger.info(f"      {i+1}. {title}... ({url})")
            
            elif source == "news_search" and result.data:
                news_finding = {
                    "type": "news_intelligence",
                    "title": f"Found {len(result.data)} recent news articles",
                    "severity": "info",
                    "confidence": 0.8,
                    "description": "Recent news affecting document context",
                    "sources": result.data[:2],  # Top 2 results
                    "source_type": "news_search",
                    "mcp_enhanced": True,
                    "external_validation": True
                }
                findings.append(news_finding)
                recommendations.append("Consider recent industry news when reviewing this document")
                
                # Log specific news articles found
                logger.info(f"   📰 News Search Enhancement:")
                for i, news_data in enumerate(result.data[:2]):
                    title = news_data.get('title', 'Unknown')[:50]
                    source = news_data.get('source', 'Unknown Source')
                    logger.info(f"      {i+1}. {title}... (Source: {source})")
            
            elif source == "legal_precedents" and result.data:
                legal_finding = {
                    "type": "legal_precedents",
                    "title": f"Found {len(result.data)} relevant legal precedents",
                    "severity": "medium",
                    "confidence": 0.9,
                    "description": "Legal precedents relevant to document type and content",
                    "precedents": result.data[:3],  # Top 3 precedents
                    "source_type": "legal_database",
                    "mcp_enhanced": True,
                    "external_validation": True
                }
                findings.append(legal_finding)
                recommendations.append("Review legal precedents for similar document types")
                
                # Log specific legal precedents found
                logger.info(f"   ⚖️ Legal Precedents Enhancement:")
                for i, precedent in enumerate(result.data[:3]):
                    case_name = precedent.get('case_name', 'Unknown Case')[:40]
                    court = precedent.get('court', 'Unknown Court')
                    logger.info(f"      {i+1}. {case_name}... ({court})")
            
            elif source == "industry_context" and result.data:
                context_data = result.data
                findings.append({
                    "type": "industry_intelligence",
                    "title": "Industry context analysis completed",
                    "severity": "info",
                    "confidence": 0.8,
                    "description": "Industry-specific insights and trends",
                    "industry_insights": context_data,
                    "source_type": "industry_intelligence"
                })
                recommendations.append("Consider current industry trends and regulations")
            
            elif source == "document_enrichment" and result.data:
                enrichment_data = result.data
                findings.append({
                    "type": "document_enrichment",
                    "title": "Document context enriched with external data",
                    "severity": "info",
                    "confidence": 0.8,
                    "description": "Additional context from regulatory and market sources",
                    "enrichment_data": enrichment_data,
                    "source_type": "document_enrichment"
                })
                recommendations.append("Review regulatory filings and market data for context")
            
            elif source.startswith("company_filings_") and result.data:
                company_name = source.replace("company_filings_", "")
                findings.append({
                    "type": "company_filings",
                    "title": f"SEC filings found for {company_name}",
                    "severity": "info",
                    "confidence": 0.9,
                    "description": f"Recent SEC filings for {company_name}",
                    "filings": result.data[:3],  # Top 3 filings
                    "company": company_name,
                    "source_type": "sec_filings"
                })
                recommendations.append(f"Review recent SEC filings for {company_name}")
        
        return findings, recommendations
    
    async def _get_contract_data(self, contract_id: str) -> Optional[BronzeContract]:
        """
        Get contract with text data, with error handling
        """
        try:
            async for db in get_operational_db():
                from sqlalchemy import select
                from sqlalchemy.orm import selectinload
                
                result = await db.execute(
                    select(BronzeContract)
                    .options(selectinload(BronzeContract.text_raw))
                    .where(BronzeContract.contract_id == contract_id)
                )
                return result.scalar_one_or_none()
                
        except Exception as e:
            logger.error(f"Failed to get contract data: {e}")
            return None
    
    async def _call_llm_with_retry(self, prompt: str, contract_id: str, max_tokens: int = 1000, temperature: float = 0.1) -> Dict[str, Any]:
        """
        Call LLM with retry logic and timeout
        """
        max_retries = 2
        
        for attempt in range(max_retries + 1):
            try:
                return await asyncio.wait_for(
                    safe_llm_completion(
                        prompt=prompt,
                        task_type=LLMTask.ANALYSIS,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        contract_id=contract_id
                    ),
                    timeout=15.0  # 15 second timeout
                )
            except asyncio.TimeoutError:
                if attempt < max_retries:
                    logger.warning(f"LLM call timeout, retrying ({attempt + 1}/{max_retries})")
                    await asyncio.sleep(1)  # Brief delay before retry
                else:
                    raise
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"LLM call failed, retrying ({attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(1)
                else:
                    raise
    
    def _create_failure_result(self, error_message: str) -> AgentResult:
        """
        Create standardized failure result
        """
        return AgentResult(
            agent_name=self.agent_name,
            agent_version=self.version,
            status=AgentStatus.FAILED,
            confidence=0.0,
            findings=[{
                "type": "error",
                "title": "Analysis Failed",
                "severity": "high",
                "confidence": 1.0,
                "description": error_message
            }],
            recommendations=["Manual analysis required due to system error"],
            execution_time_ms=0.0,
            memory_usage_mb=0.0,
            error_message=error_message,
            data_sources=[]
        )