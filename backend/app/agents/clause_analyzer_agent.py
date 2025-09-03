"""
Clause Analyzer Agent - Specialized for contract clause identification and analysis
Utilizes SilverClauseSpan table and creates comprehensive clause analysis
"""
import json
import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

from sqlalchemy import text, select, and_

from .base_agent import BaseAgent, AgentContext, AgentResult
from app.database import get_operational_db
from app.models import SilverClauseSpan, BronzeContractTextRaw
from app.services.llm_factory import LLMTask

logger = logging.getLogger(__name__)

class ClauseAnalyzerAgent(BaseAgent):
    """
    Specialized agent for identifying, analyzing, and categorizing contract clauses
    Uses existing SilverClauseSpan data and creates new clause analysis
    """
    
    def __init__(self):
        super().__init__("clause_analyzer_agent")
        
        # Clause type definitions with patterns and risk levels
        self.clause_types = {
            "liability": {
                "patterns": [
                    r"unlimited\s+liability",
                    r"liability\s+shall\s+not\s+be\s+limited",
                    r"without\s+limitation.*liability",
                    r"indemnif(y|ication)",
                    r"hold\s+harmless"
                ],
                "risk_indicators": ["unlimited", "without limitation", "full indemnification"],
                "default_risk": "high"
            },
            "termination": {
                "patterns": [
                    r"terminate.*immediately",
                    r"without\s+notice.*terminat",
                    r"at\s+will.*terminat",
                    r"breach.*terminat",
                    r"convenience.*terminat"
                ],
                "risk_indicators": ["immediate termination", "no notice", "at will"],
                "default_risk": "medium"
            },
            "auto_renewal": {
                "patterns": [
                    r"automatically\s+renew",
                    r"auto.*renew",
                    r"shall\s+renew",
                    r"unless.*notice.*renew",
                    r"evergreen.*clause"
                ],
                "risk_indicators": ["automatic renewal", "evergreen", "difficult to cancel"],
                "default_risk": "medium"
            },
            "payment_terms": {
                "patterns": [
                    r"payment.*due.*(\d+)\s+days",
                    r"net\s+(\d+)",
                    r"late.*fee",
                    r"interest.*overdue",
                    r"penalty.*late"
                ],
                "risk_indicators": ["short payment terms", "high penalties", "compound interest"],
                "default_risk": "low"
            },
            "intellectual_property": {
                "patterns": [
                    r"intellectual\s+property",
                    r"copyright.*transfer",
                    r"work\s+for\s+hire",
                    r"proprietary.*rights",
                    r"patent.*license"
                ],
                "risk_indicators": ["broad IP transfer", "work for hire", "exclusive license"],
                "default_risk": "high"
            },
            "confidentiality": {
                "patterns": [
                    r"confidential.*information",
                    r"non.?disclosure",
                    r"proprietary.*information",
                    r"trade\s+secrets",
                    r"return.*confidential"
                ],
                "risk_indicators": ["broad definition", "long duration", "residual knowledge"],
                "default_risk": "low"
            },
            "force_majeure": {
                "patterns": [
                    r"force\s+majeure",
                    r"act.*god",
                    r"beyond.*reasonable.*control",
                    r"unforeseeable.*circumstances",
                    r"pandemic.*clause"
                ],
                "risk_indicators": ["narrow definition", "no pandemic coverage", "short notice"],
                "default_risk": "medium"
            },
            "governing_law": {
                "patterns": [
                    r"governed\s+by.*law",
                    r"jurisdiction.*court",
                    r"venue.*dispute",
                    r"applicable\s+law",
                    r"forum.*selection"
                ],
                "risk_indicators": ["unfavorable jurisdiction", "mandatory arbitration", "foreign law"],
                "default_risk": "medium"
            }
        }
    
    async def analyze(self, context: AgentContext) -> AgentResult:
        """
        Main clause analysis - identifies and analyzes all contract clauses
        """
        start_time = datetime.now()
        llm_calls = 0
        
        try:
            # Get contract with text and existing clause spans
            contract = await self.get_contract_with_all_data(context.contract_id)
            if not contract or not contract.text_raw:
                return self.create_result(
                    success=False,
                    error_message="No contract text available for clause analysis"
                )
            
            # Get existing clause spans
            existing_clauses = await self.get_clause_spans_by_type(context.contract_id)
            
            # Perform comprehensive clause analysis
            text_content = contract.text_raw.raw_text
            
            # 1. Pattern-based clause detection
            pattern_clauses = await self.detect_clauses_by_patterns(text_content)
            
            # 2. AI-powered clause identification
            ai_clauses, ai_call_id = await self.identify_clauses_with_ai(text_content, context.contract_id)
            llm_calls += 1
            
            # 3. Analyze existing clauses for risks
            existing_analysis = await self.analyze_existing_clauses(existing_clauses)
            
            # 4. Deep analysis of high-risk clauses
            high_risk_analysis, risk_call_id = await self.deep_analyze_high_risk_clauses(
                pattern_clauses + ai_clauses, 
                text_content, 
                context.contract_id
            )
            llm_calls += 1
            
            # 5. Generate clause recommendations
            recommendations = await self.generate_clause_recommendations(
                pattern_clauses + ai_clauses + existing_analysis
            )
            
            # 6. Save new clause spans to database
            new_clause_ids = await self.save_new_clause_spans(
                context.contract_id, 
                pattern_clauses + ai_clauses
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Compile findings
            findings = []
            
            # Add clause detection findings
            if pattern_clauses or ai_clauses:
                findings.append({
                    "type": "clause_identification",
                    "title": f"Identified {len(pattern_clauses + ai_clauses)} clauses",
                    "description": "Comprehensive clause detection using pattern matching and AI analysis",
                    "severity": "info",
                    "confidence": 0.85,
                    "clauses": pattern_clauses + ai_clauses
                })
            
            # Add high-risk clause findings
            high_risk_clauses = [c for c in pattern_clauses + ai_clauses if c.get("risk_level") in ["high", "critical"]]
            if high_risk_clauses:
                findings.append({
                    "type": "high_risk_clauses",
                    "title": f"Found {len(high_risk_clauses)} high-risk clauses",
                    "description": "Clauses requiring immediate attention due to potential risks",
                    "severity": "high",
                    "confidence": 0.9,
                    "clauses": high_risk_clauses,
                    "detailed_analysis": high_risk_analysis
                })
            
            # Add existing clause analysis
            if existing_analysis:
                findings.append({
                    "type": "existing_clause_analysis", 
                    "title": f"Analyzed {len(existing_analysis)} existing clauses",
                    "description": "Analysis of previously identified clauses",
                    "severity": "info",
                    "confidence": 0.8,
                    "analysis": existing_analysis
                })
            
            return self.create_result(
                success=True,
                confidence=0.85,
                findings=findings,
                recommendations=recommendations,
                data_used={
                    "text_length": len(text_content),
                    "existing_clauses": len(existing_clauses),
                    "new_clauses_found": len(pattern_clauses + ai_clauses),
                    "new_clause_spans_created": len(new_clause_ids)
                },
                execution_time_ms=execution_time,
                llm_calls=llm_calls
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"Clause analyzer failed: {e}")
            
            return self.create_result(
                success=False,
                execution_time_ms=execution_time,
                llm_calls=llm_calls,
                error_message=str(e)
            )
    
    async def detect_clauses_by_patterns(self, text: str) -> List[Dict[str, Any]]:
        """Detect clauses using regex patterns"""
        detected_clauses = []
        
        try:
            for clause_type, config in self.clause_types.items():
                for pattern in config["patterns"]:
                    matches = list(re.finditer(pattern, text, re.IGNORECASE))
                    
                    for match in matches:
                        start_pos = match.start()
                        end_pos = match.end()
                        
                        # Extract surrounding context (±200 chars)
                        context_start = max(0, start_pos - 200)
                        context_end = min(len(text), end_pos + 200)
                        context = text[context_start:context_end]
                        
                        # Determine risk level based on matched text
                        matched_text = match.group().lower()
                        risk_level = config["default_risk"]
                        
                        # Check for risk indicators
                        risk_indicators = []
                        for indicator in config["risk_indicators"]:
                            if indicator.lower() in context.lower():
                                risk_indicators.append(indicator)
                                if indicator.lower() in ["unlimited", "without limitation", "immediate"]:
                                    risk_level = "critical"
                                elif indicator.lower() in ["broad", "exclusive", "mandatory"]:
                                    risk_level = "high"
                        
                        detected_clauses.append({
                            "clause_type": clause_type,
                            "clause_name": f"{clause_type.replace('_', ' ').title()} Clause",
                            "text": context,
                            "snippet": match.group(),
                            "start_offset": start_pos,
                            "end_offset": end_pos,
                            "risk_level": risk_level,
                            "risk_indicators": risk_indicators,
                            "confidence": 0.8,
                            "detection_method": "pattern_matching",
                            "pattern_matched": pattern
                        })
            
            return detected_clauses
            
        except Exception as e:
            logger.error(f"Pattern-based clause detection failed: {e}")
            return []
    
    async def identify_clauses_with_ai(self, text: str, contract_id: str) -> tuple[List[Dict[str, Any]], str]:
        """Use AI to identify clauses not caught by patterns"""
        try:
            # Limit text for AI analysis
            text_sample = text[:4000] if len(text) > 4000 else text
            
            clause_prompt = f"""
            You are a legal contract expert. Identify and analyze important clauses in this contract text.
            
            Focus on clauses that might not be obvious but are legally significant:
            - Limitation of liability clauses
            - Warranty disclaimers  
            - Assignment restrictions
            - Amendment requirements
            - Dispute resolution mechanisms
            - Data protection clauses
            - Service level agreements
            - Compliance requirements
            
            Contract text (first 4000 chars):
            {text_sample}
            
            Return a JSON array of clauses:
            [{{
                "clause_type": "liability|warranty|assignment|amendment|dispute|data_protection|sla|compliance|other",
                "clause_name": "descriptive name",
                "text": "relevant clause text (max 500 chars)",
                "risk_level": "low|medium|high|critical", 
                "risk_indicators": ["indicator1", "indicator2"],
                "confidence": 0.0-1.0,
                "business_impact": "brief description of business impact"
            }}]
            
            Only include clauses with confidence > 0.6. Limit to 10 most important clauses.
            """
            
            result, call_id = await self.call_llm_with_tracking(
                prompt=clause_prompt,
                contract_id=contract_id,
                task_type=LLMTask.ANALYSIS,
                max_tokens=2000,
                temperature=0.1
            )
            
            try:
                ai_clauses = json.loads(result["content"])
                if not isinstance(ai_clauses, list):
                    ai_clauses = []
                
                # Standardize the format and add metadata
                standardized_clauses = []
                for clause in ai_clauses:
                    if clause.get("confidence", 0) > 0.6:
                        # Find position in text
                        clause_text = clause.get("text", "")
                        if clause_text:
                            pos = text.lower().find(clause_text[:100].lower())
                            start_offset = max(0, pos) if pos >= 0 else 0
                            end_offset = start_offset + len(clause_text)
                        else:
                            start_offset = 0
                            end_offset = 100
                        
                        standardized_clauses.append({
                            "clause_type": clause.get("clause_type", "other"),
                            "clause_name": clause.get("clause_name", "AI Identified Clause"),
                            "text": clause.get("text", ""),
                            "snippet": clause.get("text", "")[:200],
                            "start_offset": start_offset,
                            "end_offset": end_offset,
                            "risk_level": clause.get("risk_level", "medium"),
                            "risk_indicators": clause.get("risk_indicators", []),
                            "confidence": clause.get("confidence", 0.7),
                            "detection_method": "ai_analysis",
                            "business_impact": clause.get("business_impact", "")
                        })
                
                return standardized_clauses, call_id
                
            except json.JSONDecodeError:
                logger.warning("Failed to parse AI clause identification response")
                return [], call_id
                
        except Exception as e:
            logger.error(f"AI clause identification failed: {e}")
            return [], ""
    
    async def analyze_existing_clauses(self, existing_clauses: List[SilverClauseSpan]) -> List[Dict[str, Any]]:
        """Analyze existing clause spans for additional insights"""
        analysis_results = []
        
        try:
            for clause in existing_clauses:
                # Analyze risk indicators
                risk_score = 0.0
                risk_factors = []
                
                if clause.risk_indicators:
                    for indicator in clause.risk_indicators:
                        if indicator.lower() in ["unlimited", "immediate", "without limitation"]:
                            risk_score += 0.3
                            risk_factors.append(f"High risk: {indicator}")
                        elif indicator.lower() in ["penalty", "forfeiture", "exclusive"]:
                            risk_score += 0.2
                            risk_factors.append(f"Medium risk: {indicator}")
                
                # Analyze clause attributes
                if clause.attributes:
                    for key, value in clause.attributes.items():
                        if key.lower() in ["penalty_amount", "liability_cap"] and isinstance(value, (int, float)):
                            if value > 100000:  # High financial impact
                                risk_score += 0.2
                                risk_factors.append(f"High financial exposure: ${value:,}")
                
                analysis_results.append({
                    "clause_id": clause.span_id,
                    "clause_type": clause.clause_type,
                    "clause_name": clause.clause_name,
                    "original_confidence": clause.confidence,
                    "risk_score": min(1.0, risk_score),
                    "risk_factors": risk_factors,
                    "attributes": clause.attributes,
                    "snippet": clause.snippet[:200]
                })
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Existing clause analysis failed: {e}")
            return []
    
    async def deep_analyze_high_risk_clauses(
        self, 
        clauses: List[Dict[str, Any]], 
        full_text: str, 
        contract_id: str
    ) -> tuple[Dict[str, Any], str]:
        """Perform deep analysis on high-risk clauses"""
        try:
            high_risk_clauses = [c for c in clauses if c.get("risk_level") in ["high", "critical"]]
            
            if not high_risk_clauses:
                return {}, ""
            
            # Prepare detailed analysis prompt
            clauses_summary = []
            for clause in high_risk_clauses[:5]:  # Limit to top 5
                clauses_summary.append({
                    "type": clause.get("clause_type"),
                    "text": clause.get("text", "")[:300],
                    "risk_level": clause.get("risk_level"),
                    "indicators": clause.get("risk_indicators", [])
                })
            
            analysis_prompt = f"""
            Perform detailed legal and business analysis of these high-risk contract clauses:
            
            {json.dumps(clauses_summary, indent=2)}
            
            For each clause, provide:
            1. Legal implications and potential consequences
            2. Business impact and financial exposure
            3. Negotiation strategies and alternatives
            4. Industry standard comparisons
            5. Risk mitigation recommendations
            
            Return as JSON:
            {{
                "overall_risk_assessment": "summary of overall risk",
                "clause_analyses": [
                    {{
                        "clause_type": "type",
                        "legal_implications": "detailed legal analysis",
                        "business_impact": "business consequences",
                        "financial_exposure": "potential costs/losses",
                        "negotiation_points": ["point1", "point2"],
                        "alternatives": ["alternative1", "alternative2"],
                        "mitigation_strategies": ["strategy1", "strategy2"]
                    }}
                ],
                "recommendations": ["rec1", "rec2"],
                "urgency_level": "low|medium|high|critical"
            }}
            """
            
            result, call_id = await self.call_llm_with_tracking(
                prompt=analysis_prompt,
                contract_id=contract_id,
                task_type=LLMTask.ANALYSIS,
                max_tokens=2500,
                temperature=0.2
            )
            
            try:
                analysis = json.loads(result["content"])
                return analysis, call_id
            except json.JSONDecodeError:
                return {"analysis": result["content"]}, call_id
                
        except Exception as e:
            logger.error(f"Deep clause analysis failed: {e}")
            return {}, ""
    
    async def generate_clause_recommendations(self, all_clauses: List[Dict[str, Any]]) -> List[str]:
        """Generate actionable recommendations based on clause analysis"""
        recommendations = []
        
        try:
            # Count clauses by risk level
            risk_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            clause_types = set()
            
            for clause in all_clauses:
                risk_level = clause.get("risk_level", "medium")
                risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1
                clause_types.add(clause.get("clause_type", "unknown"))
            
            # Generate recommendations based on findings
            if risk_counts["critical"] > 0:
                recommendations.append(f"🚨 {risk_counts['critical']} critical clause(s) require immediate legal review")
                recommendations.append("📋 Senior management approval required before contract execution")
            
            if risk_counts["high"] > 2:
                recommendations.append(f"⚠️ {risk_counts['high']} high-risk clauses need negotiation")
                recommendations.append("🔍 Consider engaging specialized legal counsel")
            
            # Specific clause type recommendations
            if "liability" in clause_types:
                recommendations.append("⚖️ Review liability and indemnification terms with legal team")
            
            if "auto_renewal" in clause_types:
                recommendations.append("📅 Set calendar reminders for renewal notice deadlines")
            
            if "termination" in clause_types:
                recommendations.append("📋 Review termination procedures and notice requirements")
            
            if "intellectual_property" in clause_types:
                recommendations.append("💡 Verify IP ownership and licensing terms with IP counsel")
            
            # General recommendations
            if len(all_clauses) > 15:
                recommendations.append("📊 Consider clause-by-clause review due to contract complexity")
            
            if not recommendations:
                recommendations.append("✅ Clause analysis complete - standard review process recommended")
            
            return recommendations[:8]  # Limit to 8 recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate clause recommendations: {e}")
            return ["Manual clause review recommended due to analysis error"]
    
    async def save_new_clause_spans(self, contract_id: str, clauses: List[Dict[str, Any]]) -> List[str]:
        """Save newly identified clauses to SilverClauseSpan table"""
        clause_ids = []
        
        try:
            async for db in get_operational_db():
                for clause_data in clauses:
                    try:
                        clause_span = SilverClauseSpan(
                            contract_id=contract_id,
                            clause_type=clause_data.get("clause_type", "other"),
                            clause_name=clause_data.get("clause_name", "Identified Clause"),
                            start_offset=clause_data.get("start_offset", 0),
                            end_offset=clause_data.get("end_offset", 100),
                            snippet=clause_data.get("text", "")[:1000],  # Limit snippet size
                            confidence=clause_data.get("confidence", 0.7),
                            attributes={
                                "risk_level": clause_data.get("risk_level"),
                                "business_impact": clause_data.get("business_impact", ""),
                                "detection_method": clause_data.get("detection_method", "agent")
                            },
                            risk_indicators=clause_data.get("risk_indicators", []),
                            extraction_method="ai",
                            model_version="2.0.0"
                        )
                        
                        db.add(clause_span)
                        await db.flush()
                        clause_ids.append(clause_span.span_id)
                        
                    except Exception as e:
                        logger.warning(f"Failed to save clause span: {e}")
                
                await db.commit()
                
            return clause_ids
            
        except Exception as e:
            logger.error(f"Failed to save clause spans: {e}")
            return []
