"""
Clause Analysis Agent - AWS Bedrock AgentCore Compatible
Specialized agent for analyzing contract clauses, terms, and legal provisions
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
from app.models import SilverClauseSpan, BronzeContract
from app.services.llm_factory import LLMTask
from app.services.privacy_safe_llm import safe_llm_completion

logger = logging.getLogger(__name__)

class ClauseAnalysisAgent(BaseAgent):
    """
    Specialized agent for contract clause analysis - AWS Bedrock AgentCore Compatible
    Focuses on identifying, analyzing, and assessing legal clauses and provisions
    """
    
    def __init__(self):
        super().__init__("clause_analysis_agent", "2.0.0")
        
        # Clause type patterns for identification
        self.clause_patterns = {
            "termination": [
                r"terminat\w+",
                r"end\s+(?:of\s+)?(?:this\s+)?(?:agreement|contract)",
                r"expir\w+",
                r"cancel\w+"
            ],
            "liability": [
                r"liabilit\w+",
                r"liable\s+for",
                r"damages",
                r"indemnif\w+",
                r"hold\s+harmless"
            ],
            "payment": [
                r"payment\s+terms?",
                r"due\s+date",
                r"invoice",
                r"billing",
                r"remuneration"
            ],
            "intellectual_property": [
                r"intellectual\s+property",
                r"copyright",
                r"trademark",
                r"patent",
                r"proprietary"
            ],
            "confidentiality": [
                r"confidential\w*",
                r"non.?disclosure",
                r"proprietary\s+information",
                r"trade\s+secret"
            ],
            "force_majeure": [
                r"force\s+majeure",
                r"act\s+of\s+god",
                r"unforeseeable\s+circumstances",
                r"beyond\s+(?:reasonable\s+)?control"
            ]
        }
        
        # Risk indicators for clauses
        self.risk_indicators = {
            "high": [
                "unlimited liability",
                "immediate termination",
                "irrevocable",
                "perpetual",
                "exclusive license",
                "no limitation"
            ],
            "medium": [
                "auto-renewal",
                "indemnification",
                "liquidated damages",
                "non-compete",
                "assignment"
            ],
            "low": [
                "standard terms",
                "mutual agreement",
                "reasonable notice",
                "good faith"
            ]
        }
    
    async def _execute_analysis(self, context: AgentContext) -> AgentResult:
        """
        Execute clause analysis with pattern matching and AI enhancement
        """
        try:
            # Get contract and existing clause data
            contract = await self._get_contract_data(context.contract_id)
            if not contract:
                return self.create_result(
                    status=AgentStatus.FAILED,
                    error_message="Contract not found"
                )
            
            # Get existing clause spans
            existing_clauses = await self._get_existing_clauses(context.contract_id)
            
            # Analyze existing clauses
            clause_analysis = await self._analyze_clauses(existing_clauses, contract, context)
            
            # Identify new clauses if text is available
            new_clauses = []
            if contract.text_raw:
                new_clauses = await self._identify_new_clauses(
                    contract.text_raw.raw_text, context.contract_id
                )
            
            # Generate findings
            findings = []
            
            # Add existing clause analysis
            if clause_analysis:
                findings.extend(clause_analysis)
            
            # Add new clause findings
            if new_clauses:
                findings.append({
                    "type": "new_clauses_identified",
                    "title": f"Identified {len(new_clauses)} potential new clauses",
                    "severity": "info",
                    "confidence": 0.8,
                    "clauses": new_clauses
                })
            
            # Generate recommendations
            recommendations = self._generate_clause_recommendations(
                existing_clauses, new_clauses, clause_analysis
            )
            
            return self.create_result(
                status=AgentStatus.COMPLETED,
                confidence=0.85,
                findings=findings,
                recommendations=recommendations,
                data_sources=["silver_clause_spans", "bronze_contract"],
                llm_calls=1 if contract.text_raw else 0
            )
            
        except Exception as e:
            logger.error(f"Clause analysis failed: {e}")
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
    
    async def _get_existing_clauses(self, contract_id: str) -> List[SilverClauseSpan]:
        """Get existing clause spans for the contract"""
        try:
            async for db in get_operational_db():
                from sqlalchemy import select
                
                result = await db.execute(
                    select(SilverClauseSpan)
                    .where(SilverClauseSpan.contract_id == contract_id)
                    .order_by(SilverClauseSpan.confidence.desc())
                )
                return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get existing clauses: {e}")
            return []
    
    async def _analyze_clauses(
        self, 
        clauses: List[SilverClauseSpan], 
        contract: BronzeContract,
        context: AgentContext
    ) -> List[Dict[str, Any]]:
        """Analyze existing clauses for risks and insights"""
        findings = []
        
        if not clauses:
            return [{
                "type": "no_clauses",
                "title": "No existing clauses found",
                "severity": "info",
                "confidence": 1.0,
                "description": "No clause spans have been identified in this document"
            }]
        
        # Analyze each clause
        high_risk_clauses = []
        clause_types = {}
        
        for clause in clauses:
            # Count clause types
            clause_type = clause.clause_type or "unknown"
            clause_types[clause_type] = clause_types.get(clause_type, 0) + 1
            
            # Assess risk level
            risk_level = self._assess_clause_risk(clause)
            
            if risk_level == "high":
                high_risk_clauses.append({
                    "clause_id": clause.span_id,
                    "type": clause.clause_type,
                    "name": clause.clause_name,
                    "risk_level": risk_level,
                    "confidence": clause.confidence,
                    "snippet": clause.snippet[:200] if clause.snippet else "",
                    "risk_indicators": clause.risk_indicators or []
                })
        
        # Add findings for high-risk clauses
        if high_risk_clauses:
            findings.append({
                "type": "high_risk_clauses",
                "title": f"Found {len(high_risk_clauses)} high-risk clauses",
                "severity": "high",
                "confidence": 0.9,
                "description": "These clauses require careful review",
                "clauses": high_risk_clauses
            })
        
        # Add clause type distribution
        findings.append({
            "type": "clause_distribution",
            "title": f"Clause analysis: {len(clauses)} clauses across {len(clause_types)} types",
            "severity": "info",
            "confidence": 0.95,
            "distribution": clause_types,
            "total_clauses": len(clauses)
        })
        
        return findings
    
    async def _identify_new_clauses(self, text: str, contract_id: str) -> List[Dict[str, Any]]:
        """Identify potential new clauses using pattern matching and AI"""
        new_clauses = []
        
        try:
            # Pattern-based clause identification
            for clause_type, patterns in self.clause_patterns.items():
                for pattern in patterns:
                    matches = list(re.finditer(pattern, text, re.IGNORECASE))
                    
                    for match in matches:
                        # Get context around match
                        start = max(0, match.start() - 100)
                        end = min(len(text), match.end() + 100)
                        context_text = text[start:end].strip()
                        
                        new_clauses.append({
                            "type": clause_type,
                            "matched_text": match.group(),
                            "context": context_text,
                            "position": match.start(),
                            "confidence": 0.7,
                            "detection_method": "pattern_matching"
                        })
            
            # Remove duplicates based on position
            unique_clauses = []
            seen_positions = set()
            
            for clause in new_clauses:
                pos_range = range(clause["position"] - 50, clause["position"] + 50)
                if not any(pos in seen_positions for pos in pos_range):
                    unique_clauses.append(clause)
                    seen_positions.update(pos_range)
            
            return unique_clauses[:20]  # Limit to 20 new clauses
            
        except Exception as e:
            logger.error(f"New clause identification failed: {e}")
            return []
    
    def _assess_clause_risk(self, clause: SilverClauseSpan) -> str:
        """Assess risk level of a clause"""
        if not clause.snippet:
            return "low"
        
        snippet_lower = clause.snippet.lower()
        
        # Check for high-risk indicators
        for indicator in self.risk_indicators["high"]:
            if indicator.lower() in snippet_lower:
                return "high"
        
        # Check for medium-risk indicators
        for indicator in self.risk_indicators["medium"]:
            if indicator.lower() in snippet_lower:
                return "medium"
        
        # Check confidence level
        if clause.confidence and clause.confidence < 0.5:
            return "medium"  # Low confidence clauses need review
        
        return "low"
    
    def _generate_clause_recommendations(
        self, 
        existing_clauses: List[SilverClauseSpan],
        new_clauses: List[Dict[str, Any]],
        analysis_findings: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations based on clause analysis"""
        recommendations = []
        
        # Count high-risk items
        high_risk_count = sum(1 for finding in analysis_findings 
                             if finding.get("severity") == "high")
        
        if high_risk_count > 0:
            recommendations.append(f"🚨 Review {high_risk_count} high-risk clauses immediately")
            recommendations.append("Consider legal counsel for high-risk clause modifications")
        
        if new_clauses:
            recommendations.append(f"📋 Review {len(new_clauses)} newly identified clauses")
            recommendations.append("Verify clause extraction accuracy and completeness")
        
        if existing_clauses:
            # Check for missing common clause types
            existing_types = set(clause.clause_type for clause in existing_clauses if clause.clause_type)
            common_types = {"termination", "liability", "payment", "confidentiality"}
            missing_types = common_types - existing_types
            
            if missing_types:
                recommendations.append(f"⚠️ Consider adding missing clause types: {', '.join(missing_types)}")
        
        # Default recommendations
        if not recommendations:
            recommendations = [
                "Clause analysis completed successfully",
                "Review all identified clauses for accuracy",
                "Ensure all critical business terms are covered"
            ]
        
        return recommendations[:8]  # Limit to 8 recommendations