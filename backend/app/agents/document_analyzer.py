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
from app.services.llm_factory import llm_factory, LLMTask

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
            # Get document with all related data
            contract = await self._get_contract_data(context.contract_id)
            if not contract:
                return self._create_failure_result("Document not found or inaccessible")
            
            # Determine analysis strategy based on document type and size
            analysis_strategy = self._determine_analysis_strategy(contract, context)
            
            # Execute analysis based on strategy
            if analysis_strategy == "comprehensive":
                return await self._comprehensive_analysis(contract, context)
            elif analysis_strategy == "fast":
                return await self._fast_analysis(contract, context)
            else:  # fallback
                return await self._fallback_analysis(contract, context)
                
        except Exception as e:
            logger.error(f"Document analysis failed: {e}")
            return self._create_failure_result(str(e))
    
    def _determine_analysis_strategy(self, contract: BronzeContract, context: AgentContext) -> str:
        """Determine optimal analysis strategy based on document and context"""
        text_length = len(contract.text_raw.raw_text) if contract.text_raw else 0
        
        # Fast analysis for simple queries or small documents
        if (context.query and len(context.query.split()) < 5) or text_length < 1000:
            return "fast"
        
        # Comprehensive analysis for complex documents and high priority
        if context.priority in [AgentPriority.CRITICAL, AgentPriority.HIGH] or text_length > 10000:
            return "comprehensive"
        
        # Fallback for edge cases
        return "fallback"
    
    async def _comprehensive_analysis(self, contract: BronzeContract, context: AgentContext) -> AgentResult:
        """
        Comprehensive analysis using multiple techniques
        """
        findings = []
        recommendations = []
        llm_calls = 0
        data_sources = ["bronze_contract", "bronze_contract_text_raw"]
        
        text_content = contract.text_raw.raw_text
        document_type = context.document_type or contract.document_category or "general"
        
        # 1. Pattern-based risk detection
        pattern_findings = await self._detect_risk_patterns(text_content, document_type)
        findings.extend(pattern_findings)
        
        # 2. AI-powered analysis (with fallback)
        try:
            ai_analysis = await self._ai_document_analysis(text_content, document_type, context.contract_id)
            if ai_analysis:
                findings.extend(ai_analysis.get("findings", []))
                recommendations.extend(ai_analysis.get("recommendations", []))
                llm_calls += 1
        except Exception as e:
            logger.warning(f"AI analysis failed, continuing with pattern analysis: {e}")
            recommendations.append("AI analysis unavailable - manual review recommended")
        
        # 3. Existing clause analysis
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
        
        # 4. Generate consolidated recommendations
        if not recommendations:
            recommendations = self._generate_fallback_recommendations(findings, document_type)
        
        # Calculate overall confidence
        confidence = self._calculate_confidence(findings, llm_calls > 0)
        
        return AgentResult(
            agent_name=self.agent_name,
            agent_version=self.version,
            status=AgentStatus.COMPLETED,
            confidence=confidence,
            findings=findings,
            recommendations=recommendations[:10],  # Limit recommendations
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
        
        # Basic document stats
        word_count = len(text_content.split())
        findings.append({
            "type": "document_stats",
            "title": f"Document contains {word_count:,} words",
            "severity": "info",
            "confidence": 1.0,
            "stats": {
                "word_count": word_count,
                "character_count": len(text_content),
                "estimated_reading_time": max(1, word_count // 200)
            }
        })
        
        # Generate basic recommendations
        recommendations = self._generate_fallback_recommendations(findings, document_type)
        
        return AgentResult(
            agent_name=self.agent_name,
            agent_version=self.version,
            status=AgentStatus.COMPLETED,
            confidence=0.7,  # Lower confidence for fast analysis
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
        Detect risk patterns using regex and keyword analysis
        """
        findings = []
        template = self.analysis_templates.get(document_type, self.analysis_templates["general"])
        
        try:
            text_lower = text.lower()
            
            for pattern, risk_level, description in template["risk_patterns"]:
                matches = list(re.finditer(pattern, text_lower, re.IGNORECASE))
                
                for match in matches:
                    # Get context around match
                    start = max(0, match.start() - 100)
                    end = min(len(text), match.end() + 100)
                    context = text[start:end].strip()
                    
                    findings.append({
                        "type": "risk_pattern",
                        "title": description,
                        "severity": risk_level,
                        "confidence": 0.8,
                        "pattern": pattern,
                        "matched_text": match.group(),
                        "context": context,
                        "position": match.start()
                    })
            
            return findings
            
        except Exception as e:
            logger.error(f"Pattern detection failed: {e}")
            return []
    
    async def _ai_document_analysis(self, text: str, document_type: str, contract_id: str) -> Optional[Dict[str, Any]]:
        """
        AI-powered document analysis with robust error handling
        """
        try:
            # Limit text for AI analysis to prevent token overflow
            text_sample = text[:4000] if len(text) > 4000 else text
            
            analysis_prompt = f"""
            Analyze this {document_type} document for key risks, obligations, and important terms.
            
            Document excerpt:
            {text_sample}
            
            Provide analysis in JSON format:
            {{
                "findings": [
                    {{
                        "type": "risk|obligation|term|concern",
                        "title": "Brief title",
                        "severity": "low|medium|high|critical",
                        "confidence": 0.0-1.0,
                        "description": "Detailed explanation"
                    }}
                ],
                "recommendations": [
                    "Specific actionable recommendation"
                ],
                "overall_risk": "low|medium|high|critical",
                "key_concerns": ["concern1", "concern2"]
            }}
            
            Focus on practical business implications and actionable insights.
            """
            
            result, call_id = await self._call_llm_with_retry(
                prompt=analysis_prompt,
                contract_id=contract_id,
                max_tokens=1500,
                temperature=0.1
            )
            
            try:
                return json.loads(result["content"])
            except json.JSONDecodeError:
                # Return structured fallback if JSON parsing fails
                return {
                    "findings": [{
                        "type": "ai_analysis",
                        "title": "AI Analysis Result",
                        "severity": "info",
                        "confidence": 0.6,
                        "description": result["content"][:500]
                    }],
                    "recommendations": ["Review AI analysis output manually"]
                }
                
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return None
    
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
        Generate fallback recommendations based on findings
        """
        recommendations = []
        
        # Count findings by severity
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for finding in findings:
            severity = finding.get("severity", "low")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Generate recommendations based on severity
        if severity_counts["critical"] > 0:
            recommendations.append(f"🚨 {severity_counts['critical']} critical issue(s) require immediate attention")
            recommendations.append("Seek legal counsel before proceeding")
        
        if severity_counts["high"] > 0:
            recommendations.append(f"⚠️ {severity_counts['high']} high-risk item(s) need review")
            recommendations.append("Consider negotiating problematic terms")
        
        if severity_counts["medium"] > 2:
            recommendations.append(f"📋 {severity_counts['medium']} medium-risk items identified")
            recommendations.append("Review terms carefully before signing")
        
        # Document type specific recommendations
        if document_type == "contract":
            recommendations.append("Verify all parties, dates, and financial terms")
            recommendations.append("Ensure termination and liability clauses are acceptable")
        elif document_type == "invoice":
            recommendations.append("Verify all charges and payment terms")
            recommendations.append("Check for any disputed or unusual items")
        
        # Default recommendations if none generated
        if not recommendations:
            recommendations = [
                f"Document analysis completed for {document_type}",
                "Review findings and take appropriate action",
                "Consider professional consultation if needed"
            ]
        
        return recommendations[:8]  # Limit to 8 recommendations
    
    def _calculate_confidence(self, findings: List[Dict[str, Any]], has_ai_analysis: bool) -> float:
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
        
        # Boost confidence based on finding quality
        high_confidence_findings = [f for f in findings if f.get("confidence", 0) > 0.8]
        if high_confidence_findings:
            base_confidence += min(0.1, len(high_confidence_findings) * 0.02)
        
        return min(0.95, base_confidence)  # Cap at 95%
    
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
    
    async def _call_llm_with_retry(self, prompt: str, contract_id: str, max_tokens: int = 1000, temperature: float = 0.1) -> Tuple[Dict[str, Any], str]:
        """
        Call LLM with retry logic and timeout
        """
        max_retries = 2
        
        for attempt in range(max_retries + 1):
            try:
                return await asyncio.wait_for(
                    llm_factory.generate_completion(
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
            error_message=error_message
        )