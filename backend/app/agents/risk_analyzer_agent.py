"""
Risk Analysis Agent - AWS Bedrock AgentCore Compatible
Specialized agent for risk assessment and compliance analysis
Enterprise-grade architecture designed for AWS Bedrock AgentCore migration
"""
import json
import logging
import re
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from .base_agent import BaseAgent, AgentContext, AgentResult, AgentStatus
from app.database import get_operational_db
from app.models import BronzeContract, GoldFinding, SilverClauseSpan
from app.services.llm_factory import llm_factory, LLMTask

logger = logging.getLogger(__name__)

class RiskAnalysisAgent(BaseAgent):
    """
    Specialized agent for risk assessment and compliance analysis - AWS Bedrock AgentCore Compatible
    Focuses on identifying business risks, compliance issues, and regulatory concerns
    """
    
    def __init__(self):
        super().__init__("risk_analysis_agent", "2.0.0")
        
        # Risk categories and patterns
        self.risk_categories = {
            "financial": {
                "patterns": [
                    r"unlimited\s+liability",
                    r"penalty|penalties",
                    r"liquidated\s+damages",
                    r"late\s+fee",
                    r"interest\s+rate",
                    r"payment\s+default"
                ],
                "severity": "high"
            },
            "legal": {
                "patterns": [
                    r"governing\s+law",
                    r"jurisdiction",
                    r"dispute\s+resolution",
                    r"arbitration",
                    r"litigation",
                    r"breach\s+of\s+contract"
                ],
                "severity": "medium"
            },
            "operational": {
                "patterns": [
                    r"service\s+level",
                    r"performance\s+standard",
                    r"delivery\s+schedule",
                    r"milestone",
                    r"deadline",
                    r"force\s+majeure"
                ],
                "severity": "medium"
            },
            "compliance": {
                "patterns": [
                    r"regulatory\s+compliance",
                    r"data\s+protection",
                    r"privacy\s+policy",
                    r"GDPR|CCPA|HIPAA",
                    r"audit\s+requirement",
                    r"certification"
                ],
                "severity": "high"
            },
            "intellectual_property": {
                "patterns": [
                    r"intellectual\s+property",
                    r"copyright\s+infringement",
                    r"patent\s+violation",
                    r"trade\s+secret",
                    r"proprietary\s+information",
                    r"license\s+violation"
                ],
                "severity": "high"
            },
            "termination": {
                "patterns": [
                    r"immediate\s+termination",
                    r"termination\s+for\s+cause",
                    r"termination\s+without\s+cause",
                    r"notice\s+period",
                    r"survival\s+clause",
                    r"post.termination"
                ],
                "severity": "medium"
            }
        }
        
        # Industry-specific risk factors
        self.industry_risks = {
            "healthcare": {
                "compliance": ["HIPAA", "FDA", "patient safety", "medical records"],
                "operational": ["patient care", "medical devices", "clinical trials"],
                "financial": ["insurance", "medicare", "billing compliance"]
            },
            "financial": {
                "compliance": ["SOX", "PCI DSS", "anti-money laundering", "KYC"],
                "operational": ["trading", "investment", "credit risk"],
                "financial": ["capital requirements", "liquidity", "market risk"]
            },
            "technology": {
                "compliance": ["GDPR", "data privacy", "cybersecurity", "software licensing"],
                "operational": ["system availability", "data backup", "security breaches"],
                "intellectual_property": ["patent infringement", "open source", "trade secrets"]
            }
        }
    
    async def _execute_analysis(self, context: AgentContext) -> AgentResult:
        """
        Execute comprehensive risk analysis
        """
        try:
            # Get contract and related data
            contract = await self._get_contract_data(context.contract_id)
            if not contract:
                return self.create_result(
                    status=AgentStatus.FAILED,
                    error_message="Contract not found"
                )
            
            # Get existing findings to avoid duplication
            existing_findings = await self._get_existing_findings(context.contract_id)
            
            # Perform risk analysis
            risk_findings = []
            llm_calls = 0
            
            # 1. Pattern-based risk detection
            if contract.text_raw:
                pattern_risks = await self._detect_pattern_risks(
                    contract.text_raw.raw_text, context.document_type
                )
                risk_findings.extend(pattern_risks)
            
            # 2. Industry-specific risk analysis
            if context.industry_type:
                industry_risks = await self._analyze_industry_risks(
                    contract, context.industry_type, context.contract_id
                )
                if industry_risks:
                    risk_findings.extend(industry_risks.get("findings", []))
                    llm_calls += 1
            
            # 3. Clause-based risk analysis
            clause_risks = await self._analyze_clause_risks(context.contract_id)
            risk_findings.extend(clause_risks)
            
            # 4. Compliance risk assessment
            compliance_risks = await self._assess_compliance_risks(
                contract, context.industry_type, context.contract_id
            )
            if compliance_risks:
                risk_findings.extend(compliance_risks.get("findings", []))
                llm_calls += 1
            
            # Generate overall risk assessment
            overall_assessment = self._generate_risk_assessment(risk_findings)
            
            # Generate recommendations
            recommendations = self._generate_risk_recommendations(
                risk_findings, overall_assessment, context.industry_type
            )
            
            return self.create_result(
                status=AgentStatus.COMPLETED,
                confidence=0.88,
                findings=risk_findings + [overall_assessment],
                recommendations=recommendations,
                data_sources=["bronze_contract", "silver_clause_spans", "gold_findings"],
                llm_calls=llm_calls
            )
            
        except Exception as e:
            logger.error(f"Risk analysis failed: {e}")
            return self.create_result(
                status=AgentStatus.FAILED,
                error_message=str(e)
            )
    
    async def _get_contract_data(self, contract_id: str) -> Optional[BronzeContract]:
        """Get contract with text data"""
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
    
    async def _get_existing_findings(self, contract_id: str) -> List[GoldFinding]:
        """Get existing findings to avoid duplication"""
        try:
            async for db in get_operational_db():
                from sqlalchemy import select
                
                result = await db.execute(
                    select(GoldFinding)
                    .where(GoldFinding.contract_id == contract_id)
                    .order_by(GoldFinding.created_at.desc())
                )
                return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get existing findings: {e}")
            return []
    
    async def _detect_pattern_risks(self, text: str, document_type: Optional[str]) -> List[Dict[str, Any]]:
        """Detect risks using pattern matching"""
        findings = []
        text_lower = text.lower()
        
        try:
            for risk_category, config in self.risk_categories.items():
                category_matches = []
                
                for pattern in config["patterns"]:
                    matches = list(re.finditer(pattern, text_lower, re.IGNORECASE))
                    
                    for match in matches:
                        # Get context around match
                        start = max(0, match.start() - 150)
                        end = min(len(text), match.end() + 150)
                        context = text[start:end].strip()
                        
                        category_matches.append({
                            "matched_text": match.group(),
                            "context": context,
                            "position": match.start(),
                            "pattern": pattern
                        })
                
                if category_matches:
                    findings.append({
                        "type": f"{risk_category}_risk",
                        "title": f"{risk_category.title()} Risk Identified",
                        "severity": config["severity"],
                        "confidence": 0.8,
                        "description": f"Found {len(category_matches)} {risk_category} risk indicators",
                        "risk_category": risk_category,
                        "matches": category_matches[:5],  # Limit matches
                        "total_matches": len(category_matches)
                    })
            
            return findings
            
        except Exception as e:
            logger.error(f"Pattern risk detection failed: {e}")
            return []
    
    async def _analyze_industry_risks(
        self, 
        contract: BronzeContract, 
        industry_type: str, 
        contract_id: str
    ) -> Optional[Dict[str, Any]]:
        """Analyze industry-specific risks using AI"""
        try:
            if not contract.text_raw:
                return None
            
            industry_config = self.industry_risks.get(industry_type.lower(), {})
            if not industry_config:
                return None
            
            # Prepare industry-specific analysis prompt
            text_sample = contract.text_raw.raw_text[:3000]
            
            analysis_prompt = f"""
            Analyze this document for {industry_type} industry-specific risks and compliance issues.
            
            Key risk areas for {industry_type}:
            - Compliance: {', '.join(industry_config.get('compliance', []))}
            - Operational: {', '.join(industry_config.get('operational', []))}
            - Financial: {', '.join(industry_config.get('financial', []))}
            
            Document excerpt:
            {text_sample}
            
            Provide analysis in JSON format:
            {{
                "findings": [
                    {{
                        "type": "industry_risk",
                        "title": "Risk title",
                        "severity": "low|medium|high|critical",
                        "confidence": 0.0-1.0,
                        "description": "Risk description",
                        "risk_category": "compliance|operational|financial",
                        "industry_specific": true
                    }}
                ],
                "overall_industry_risk": "low|medium|high|critical",
                "compliance_status": "compliant|non-compliant|unclear"
            }}
            """
            
            result, call_id = await self.call_llm_with_tracking(
                prompt=analysis_prompt,
                contract_id=contract_id,
                task_type=LLMTask.ANALYSIS,
                max_tokens=1200,
                temperature=0.1
            )
            
            try:
                return json.loads(result["content"])
            except json.JSONDecodeError:
                return {
                    "findings": [{
                        "type": "industry_analysis",
                        "title": f"{industry_type} Industry Analysis",
                        "severity": "info",
                        "confidence": 0.6,
                        "description": result["content"][:300]
                    }]
                }
                
        except Exception as e:
            logger.error(f"Industry risk analysis failed: {e}")
            return None
    
    async def _analyze_clause_risks(self, contract_id: str) -> List[Dict[str, Any]]:
        """Analyze risks from existing clause spans"""
        findings = []
        
        try:
            async for db in get_operational_db():
                from sqlalchemy import select
                
                result = await db.execute(
                    select(SilverClauseSpan)
                    .where(SilverClauseSpan.contract_id == contract_id)
                    .order_by(SilverClauseSpan.confidence.desc())
                )
                clauses = result.scalars().all()
            
            if not clauses:
                return []
            
            # Analyze high-risk clause types
            high_risk_types = ["liability", "termination", "indemnification", "penalty"]
            high_risk_clauses = []
            
            for clause in clauses:
                if clause.clause_type and any(risk_type in clause.clause_type.lower() 
                                            for risk_type in high_risk_types):
                    
                    # Assess clause-specific risks
                    risk_level = self._assess_clause_risk_level(clause)
                    
                    if risk_level in ["high", "critical"]:
                        high_risk_clauses.append({
                            "clause_id": clause.span_id,
                            "type": clause.clause_type,
                            "name": clause.clause_name,
                            "risk_level": risk_level,
                            "confidence": clause.confidence,
                            "snippet": clause.snippet[:200] if clause.snippet else "",
                            "risk_indicators": clause.risk_indicators or []
                        })
            
            if high_risk_clauses:
                findings.append({
                    "type": "clause_risk_analysis",
                    "title": f"High-risk clauses identified: {len(high_risk_clauses)}",
                    "severity": "high",
                    "confidence": 0.9,
                    "description": "These clauses present significant business risks",
                    "high_risk_clauses": high_risk_clauses
                })
            
            return findings
            
        except Exception as e:
            logger.error(f"Clause risk analysis failed: {e}")
            return []
    
    async def _assess_compliance_risks(
        self, 
        contract: BronzeContract, 
        industry_type: Optional[str], 
        contract_id: str
    ) -> Optional[Dict[str, Any]]:
        """Assess compliance risks using AI analysis"""
        try:
            if not contract.text_raw or not industry_type:
                return None
            
            text_sample = contract.text_raw.raw_text[:2500]
            
            compliance_prompt = f"""
            Assess compliance risks in this {industry_type} industry document.
            
            Document excerpt:
            {text_sample}
            
            Focus on:
            1. Regulatory compliance requirements
            2. Data protection and privacy
            3. Industry-specific standards
            4. Legal and contractual obligations
            
            Provide analysis in JSON format:
            {{
                "findings": [
                    {{
                        "type": "compliance_risk",
                        "title": "Compliance issue title",
                        "severity": "low|medium|high|critical",
                        "confidence": 0.0-1.0,
                        "description": "Detailed description",
                        "regulation": "Specific regulation or standard",
                        "remediation": "Suggested remediation"
                    }}
                ],
                "overall_compliance_score": 0.0-1.0,
                "critical_compliance_gaps": ["gap1", "gap2"]
            }}
            """
            
            result, call_id = await self.call_llm_with_tracking(
                prompt=compliance_prompt,
                contract_id=contract_id,
                task_type=LLMTask.ANALYSIS,
                max_tokens=1000,
                temperature=0.1
            )
            
            try:
                return json.loads(result["content"])
            except json.JSONDecodeError:
                return {
                    "findings": [{
                        "type": "compliance_analysis",
                        "title": "Compliance Analysis",
                        "severity": "info",
                        "confidence": 0.6,
                        "description": result["content"][:300]
                    }]
                }
                
        except Exception as e:
            logger.error(f"Compliance risk assessment failed: {e}")
            return None
    
    def _assess_clause_risk_level(self, clause: SilverClauseSpan) -> str:
        """Assess risk level of individual clause"""
        if not clause.snippet:
            return "low"
        
        snippet_lower = clause.snippet.lower()
        
        # Critical risk indicators
        critical_indicators = [
            "unlimited liability",
            "immediate termination without cause",
            "irrevocable license",
            "perpetual obligation"
        ]
        
        # High risk indicators
        high_indicators = [
            "liquidated damages",
            "penalty",
            "indemnification",
            "exclusive license",
            "non-compete"
        ]
        
        for indicator in critical_indicators:
            if indicator in snippet_lower:
                return "critical"
        
        for indicator in high_indicators:
            if indicator in snippet_lower:
                return "high"
        
        # Check confidence level
        if clause.confidence and clause.confidence < 0.6:
            return "medium"
        
        return "low"
    
    def _generate_risk_assessment(self, risk_findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate overall risk assessment"""
        if not risk_findings:
            return {
                "type": "overall_risk_assessment",
                "title": "Overall Risk Assessment: Low",
                "severity": "info",
                "confidence": 0.9,
                "description": "No significant risks identified",
                "risk_score": 0.2,
                "risk_level": "low"
            }
        
        # Count risks by severity
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for finding in risk_findings:
            severity = finding.get("severity", "low")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Calculate overall risk score
        risk_score = (
            severity_counts["critical"] * 1.0 +
            severity_counts["high"] * 0.7 +
            severity_counts["medium"] * 0.4 +
            severity_counts["low"] * 0.1
        ) / max(1, len(risk_findings))
        
        # Determine overall risk level
        if risk_score >= 0.8 or severity_counts["critical"] > 0:
            risk_level = "critical"
            title = "Overall Risk Assessment: Critical"
        elif risk_score >= 0.6 or severity_counts["high"] > 2:
            risk_level = "high"
            title = "Overall Risk Assessment: High"
        elif risk_score >= 0.3 or severity_counts["medium"] > 3:
            risk_level = "medium"
            title = "Overall Risk Assessment: Medium"
        else:
            risk_level = "low"
            title = "Overall Risk Assessment: Low"
        
        return {
            "type": "overall_risk_assessment",
            "title": title,
            "severity": risk_level,
            "confidence": 0.9,
            "description": f"Risk analysis identified {len(risk_findings)} risk factors",
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "severity_breakdown": severity_counts,
            "total_risks": len(risk_findings)
        }
    
    def _generate_risk_recommendations(
        self, 
        risk_findings: List[Dict[str, Any]], 
        overall_assessment: Dict[str, Any],
        industry_type: Optional[str]
    ) -> List[str]:
        """Generate risk-based recommendations"""
        recommendations = []
        
        risk_level = overall_assessment.get("risk_level", "low")
        severity_counts = overall_assessment.get("severity_breakdown", {})
        
        # Critical risk recommendations
        if severity_counts.get("critical", 0) > 0:
            recommendations.append("🚨 CRITICAL: Immediate legal review required before proceeding")
            recommendations.append("🚨 Address all critical risk factors before contract execution")
        
        # High risk recommendations
        if severity_counts.get("high", 0) > 0:
            recommendations.append(f"⚠️ Review {severity_counts['high']} high-risk items with legal counsel")
            recommendations.append("⚠️ Consider risk mitigation strategies and contract amendments")
        
        # Industry-specific recommendations
        if industry_type:
            recommendations.append(f"📋 Ensure compliance with {industry_type} industry regulations")
            recommendations.append(f"📋 Review {industry_type}-specific risk factors and requirements")
        
        # General recommendations based on risk level
        if risk_level in ["high", "critical"]:
            recommendations.append("🔍 Conduct thorough due diligence on counterparty")
            recommendations.append("🔍 Consider additional insurance or bonding requirements")
        elif risk_level == "medium":
            recommendations.append("📝 Document risk acceptance and mitigation measures")
            recommendations.append("📝 Establish monitoring procedures for identified risks")
        
        # Default recommendations
        if not recommendations:
            recommendations = [
                "✅ Risk analysis completed - acceptable risk level",
                "📊 Monitor for changes that could affect risk profile",
                "📋 Regular review recommended for ongoing risk management"
            ]
        
        return recommendations[:8]  # Limit to 8 recommendations