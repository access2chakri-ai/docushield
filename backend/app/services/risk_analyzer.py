"""
AI-powered Risk Analysis and Clause Detection System
Specialized analysis for contracts, invoices, and policy documents
"""
import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
import asyncio

from app.core.config import settings
from app.services.llm_factory import LLMTask, llm_factory
from app.services.privacy_safe_llm import safe_llm_completion

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class DocumentType(Enum):
    CONTRACT = "contract"
    INVOICE = "invoice"
    POLICY = "policy"
    LEGAL = "legal"
    FINANCIAL = "financial"
    OTHER = "other"

class ClauseType(Enum):
    LIABILITY = "liability"
    TERMINATION = "termination"
    AUTO_RENEWAL = "auto_renewal"
    PAYMENT_TERMS = "payment_terms"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    CONFIDENTIALITY = "confidentiality"
    INDEMNIFICATION = "indemnification"
    FORCE_MAJEURE = "force_majeure"
    GOVERNING_LAW = "governing_law"
    DISPUTE_RESOLUTION = "dispute_resolution"

class RiskAnalyzer:
    """
    AI-powered risk analysis engine for document intelligence
    """
    
    def __init__(self):
        # Using LLM Factory for multi-provider support
        pass
        
        # Risk patterns for different document types
        self.risk_patterns = {
            DocumentType.CONTRACT: {
                "liability_unlimited": {
                    "pattern": r"unlimited\s+liability|unlimited\s+damages|without\s+limit",
                    "risk_level": RiskLevel.HIGH,
                    "description": "Unlimited liability clause detected"
                },
                "auto_renewal": {
                    "pattern": r"automatically\s+renew|auto[\-\s]?renew|shall\s+renew",
                    "risk_level": RiskLevel.MEDIUM,
                    "description": "Auto-renewal clause detected"
                },
                "short_termination": {
                    "pattern": r"terminate\s+immediately|without\s+notice",
                    "risk_level": RiskLevel.HIGH,
                    "description": "Immediate termination clause"
                },
                "penalty_clause": {
                    "pattern": r"penalty|liquidated\s+damages|forfeit",
                    "risk_level": RiskLevel.MEDIUM,
                    "description": "Penalty or liquidated damages clause"
                }
            },
            DocumentType.INVOICE: {
                "overdue_payment": {
                    "pattern": r"overdue|past\s+due|late\s+payment",
                    "risk_level": RiskLevel.MEDIUM,
                    "description": "Overdue payment indication"
                },
                "high_amount": {
                    "pattern": r"\$\s*[0-9]{1,3}(?:,\d{3})*(?:\.\d{2})?",
                    "risk_level": RiskLevel.LOW,
                    "description": "High amount transaction",
                    "threshold": 50000  # $50k threshold
                },
                "missing_po": {
                    "pattern": r"purchase\s+order|P\.?O\.?\s*#?|PO\s*#?",
                    "risk_level": RiskLevel.MEDIUM,
                    "description": "Missing purchase order reference",
                    "inverse": True  # Risk when pattern is NOT found
                }
            },
            DocumentType.POLICY: {
                "compliance_gap": {
                    "pattern": r"non[\-\s]?compliant|violation|breach",
                    "risk_level": RiskLevel.HIGH,
                    "description": "Compliance violation indicated"
                },
                "outdated_policy": {
                    "pattern": r"effective\s+date|last\s+updated|revision\s+date",
                    "risk_level": RiskLevel.MEDIUM,
                    "description": "Policy date verification needed"
                }
            }
        }
    
    def _parse_llm_response(self, result: Any, expected_type: str = "list") -> Optional[Any]:
        """
        Robust parsing of LLM responses from safe_llm_completion
        
        Args:
            result: The result from safe_llm_completion
            expected_type: "list" or "dict" - what we expect to parse
            
        Returns:
            Parsed JSON object or None if parsing fails
        """
        try:
            content = None
            
            # Handle different response formats
            if isinstance(result, dict):
                if "content" in result:
                    content = result["content"]
                elif "text" in result:
                    content = result["text"]
                else:
                    # Try to use the dict directly
                    content = json.dumps(result)
                    
            elif isinstance(result, (tuple, list)) and len(result) > 0:
                # Handle tuple/list responses
                first_element = result[0]
                
                if isinstance(first_element, dict):
                    if "content" in first_element:
                        content = first_element["content"]
                    elif "text" in first_element:
                        content = first_element["text"]
                    else:
                        content = json.dumps(first_element)
                        
                elif isinstance(first_element, list) and len(first_element) > 0:
                    # Handle nested list structure
                    nested = first_element[0]
                    if isinstance(nested, dict):
                        if "content" in nested:
                            content = nested["content"]
                        elif "text" in nested:
                            content = nested["text"]
                        else:
                            content = json.dumps(nested)
                    else:
                        content = str(nested)
                else:
                    content = str(first_element)
                    
            elif isinstance(result, str):
                content = result
            else:
                content = str(result)
            
            if not content:
                logger.warning("No content found in LLM response")
                return None
            
            # Clean the content string
            content = content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            elif content.startswith('```'):
                content = content.replace('```', '').strip()
            
            # Try to find JSON in the content if it's mixed with other text
            json_start = content.find('{') if expected_type == "dict" else content.find('[')
            if json_start >= 0:
                if expected_type == "dict":
                    json_end = content.rfind('}') + 1
                else:
                    json_end = content.rfind(']') + 1
                
                if json_end > json_start:
                    json_content = content[json_start:json_end]
                    try:
                        parsed = json.loads(json_content)
                        logger.debug(f"Successfully parsed {expected_type} from LLM response")
                        return parsed
                    except json.JSONDecodeError:
                        pass
            
            # Try to parse the entire content as JSON
            try:
                parsed = json.loads(content)
                logger.debug(f"Successfully parsed entire content as {expected_type}")
                return parsed
            except json.JSONDecodeError:
                pass
            
            # If all JSON parsing fails, try to extract structured data from text
            if expected_type == "list":
                # Try to create a simple list from text content
                logger.info("JSON parsing failed, creating structured fallback for list")
                return []
            else:
                # Try to create a simple dict from text content
                logger.info("JSON parsing failed, creating structured fallback for dict")
                return {"content": content, "parsed": False}
                
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return None
    
    def _validate_and_clean_clauses(self, clauses: List[Dict]) -> List[Dict[str, Any]]:
        """Validate and clean clause extraction results"""
        cleaned_clauses = []
        
        for clause in clauses:
            if not isinstance(clause, dict):
                continue
                
            # Ensure required fields exist
            cleaned_clause = {
                "type": clause.get("type", "unknown"),
                "text": clause.get("text", "")[:500],  # Limit text length
                "section": clause.get("section", ""),
                "risk_indicators": clause.get("risk_indicators", [])
            }
            
            # Only add if we have meaningful content
            if cleaned_clause["text"].strip():
                cleaned_clauses.append(cleaned_clause)
        
        return cleaned_clauses
    
    def _validate_and_clean_risks(self, risks: List[Dict]) -> List[Dict[str, Any]]:
        """Validate and clean AI risk assessment results"""
        cleaned_risks = []
        
        for risk in risks:
            if not isinstance(risk, dict):
                continue
                
            # Ensure required fields exist with defaults
            cleaned_risk = {
                "type": risk.get("type", "general_risk"),
                "level": risk.get("level", "medium"),
                "description": risk.get("description", "Risk identified")[:300],  # Limit description
                "impact": risk.get("impact", "Potential business impact"),
                "confidence": min(max(float(risk.get("confidence", 0.5)), 0.0), 1.0)  # Clamp 0-1
            }
            
            # Validate risk level
            valid_levels = ["low", "medium", "high", "critical"]
            if cleaned_risk["level"] not in valid_levels:
                cleaned_risk["level"] = "medium"
            
            cleaned_risks.append(cleaned_risk)
        
        return cleaned_risks
    
    async def analyze_document(self, title: str, content: str, doc_type: Optional[DocumentType] = None) -> Dict[str, Any]:
        """
        Comprehensive risk analysis of a document
        """
        try:
            # Auto-detect document type if not provided
            if not doc_type:
                doc_type = await self._detect_document_type(title, content)
            
            # Extract clauses and risks
            clauses = await self._extract_clauses(content, doc_type)
            risks = await self._assess_risks(content, doc_type, clauses)
            
            # Generate AI-powered insights
            ai_analysis = await self._generate_ai_insights(title, content, doc_type, risks)
            
            # Calculate overall risk score
            overall_risk = self._calculate_overall_risk(risks)
            
            analysis_result = {
                "document_type": doc_type.value,
                "overall_risk_level": overall_risk.value,
                "overall_risk_score": self._risk_to_score(overall_risk),
                "detected_clauses": clauses,
                "identified_risks": risks,
                "ai_insights": ai_analysis,
                "recommendations": self._generate_recommendations(risks, doc_type),
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "requires_review": overall_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            }
            
            logger.info(f"Risk analysis completed for {title}: {overall_risk.value} risk")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Risk analysis failed for {title}: {e}")
            import traceback
            logger.error(f"Risk analysis traceback: {traceback.format_exc()}")
            
            return {
                "document_type": "unknown",
                "overall_risk_level": "medium",
                "overall_risk_score": 0.5,
                "detected_clauses": [],
                "identified_risks": [],
                "ai_insights": {
                    "error": f"Analysis failed: {str(e)}",
                    "executive_summary": "Analysis encountered an error but basic processing completed.",
                    "key_concerns": ["System error during analysis"],
                    "business_impact": "Manual review required due to analysis error.",
                    "recommended_actions": ["Manual document review", "Retry analysis if needed"]
                },
                "recommendations": ["Manual review recommended due to analysis error", "Check document format and try again"],
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "requires_review": True,
                "error_details": str(e)
            }
    
    async def _detect_document_type(self, title: str, content: str) -> DocumentType:
        """Auto-detect document type using AI and keywords"""
        try:
            # Keyword-based detection
            title_lower = title.lower()
            content_sample = content[:1000].lower()
            
            if any(keyword in title_lower for keyword in ['contract', 'agreement', 'terms']):
                return DocumentType.CONTRACT
            elif any(keyword in title_lower for keyword in ['invoice', 'bill', 'receipt']):
                return DocumentType.INVOICE
            elif any(keyword in title_lower for keyword in ['policy', 'procedure', 'guideline']):
                return DocumentType.POLICY
            elif any(keyword in content_sample for keyword in ['whereas', 'party', 'agreement', 'contract']):
                return DocumentType.CONTRACT
            elif any(keyword in content_sample for keyword in ['invoice', 'amount due', 'payment terms']):
                return DocumentType.INVOICE
            elif any(keyword in content_sample for keyword in ['policy', 'compliance', 'procedure']):
                return DocumentType.POLICY
            else:
                return DocumentType.OTHER
                
        except Exception as e:
            logger.warning(f"Document type detection failed: {e}")
            return DocumentType.OTHER
    
    async def _extract_clauses(self, content: str, doc_type: DocumentType) -> List[Dict[str, Any]]:
        """Extract key clauses from document using AI"""
        try:
            if doc_type not in [DocumentType.CONTRACT, DocumentType.LEGAL]:
                return []
            
            # Use AI to extract clauses
            clause_prompt = f"""
            Extract key clauses from this {doc_type.value} document. Focus on:
            - Liability and indemnification clauses
            - Termination and renewal clauses
            - Payment and financial terms
            - Intellectual property clauses
            - Confidentiality provisions
            
            Document content (first 2000 chars):
            {content[:2000]}
            
            Return as JSON array with format:
            [{{"type": "clause_type", "text": "clause text", "section": "section name", "risk_indicators": ["indicator1", "indicator2"]}}]
            """
            
            result = await safe_llm_completion(
                prompt=clause_prompt,
                task_type=LLMTask.ANALYSIS,
                max_tokens=1000,
                temperature=0.1
            )
            
            # Use robust parsing
            clauses = self._parse_llm_response(result, expected_type="list")
            if clauses is not None and isinstance(clauses, list):
                # Validate and clean the results
                cleaned_clauses = self._validate_and_clean_clauses(clauses)
                logger.info(f"Successfully extracted and validated {len(cleaned_clauses)} clauses from AI response")
                return cleaned_clauses
            else:
                logger.info("AI clause extraction returned no valid clauses, using pattern-based fallback")
                return []
                
        except Exception as e:
            logger.error(f"Clause extraction failed: {e}")
            return []
    
    async def _assess_risks(self, content: str, doc_type: DocumentType, clauses: List[Dict]) -> List[Dict[str, Any]]:
        """Assess risks using pattern matching and AI analysis"""
        risks = []
        
        try:
            # Pattern-based risk detection
            if doc_type in self.risk_patterns:
                patterns = self.risk_patterns[doc_type]
                
                for risk_name, risk_config in patterns.items():
                    pattern = risk_config["pattern"]
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    
                    # Handle inverse patterns (risk when pattern NOT found)
                    if risk_config.get("inverse", False):
                        if not matches:
                            risks.append({
                                "type": risk_name,
                                "level": risk_config["risk_level"].value,
                                "description": risk_config["description"],
                                "evidence": "Pattern not found in document",
                                "confidence": 0.7
                            })
                    else:
                        if matches:
                            # Check threshold for numeric patterns
                            if "threshold" in risk_config:
                                amounts = [float(re.sub(r'[^\d.]', '', match)) for match in matches if re.search(r'\d', match)]
                                if amounts and max(amounts) >= risk_config["threshold"]:
                                    risks.append({
                                        "type": risk_name,
                                        "level": risk_config["risk_level"].value,
                                        "description": f"{risk_config['description']} (${max(amounts):,.2f})",
                                        "evidence": f"Found amounts: {matches}",
                                        "confidence": 0.8
                                    })
                            else:
                                risks.append({
                                    "type": risk_name,
                                    "level": risk_config["risk_level"].value,
                                    "description": risk_config["description"],
                                    "evidence": f"Found matches: {matches[:3]}",  # Limit evidence
                                    "confidence": 0.8
                                })
            
            # AI-powered risk assessment
            ai_risks = await self._ai_risk_assessment(content, doc_type, clauses)
            risks.extend(ai_risks)
            
            return risks
            
        except Exception as e:
            logger.error(f"Risk assessment failed: {e}")
            return risks
    
    async def _ai_risk_assessment(self, content: str, doc_type: DocumentType, clauses: List[Dict]) -> List[Dict[str, Any]]:
        """AI-powered risk assessment"""
        try:
            risk_prompt = f"""
            Analyze this {doc_type.value} document for potential risks and red flags.
            
            Focus on:
            1. Financial risks (payment terms, penalties, liability)
            2. Legal risks (unfavorable terms, compliance issues)
            3. Operational risks (termination, performance requirements)
            4. Strategic risks (IP ownership, exclusivity)
            
            Document content (first 1500 chars):
            {content[:1500]}
            
            Detected clauses: {json.dumps(clauses[:5])}
            
            Return JSON array:
            [{{"type": "risk_category", "level": "low/medium/high/critical", "description": "risk description", "impact": "potential impact", "confidence": 0.0-1.0}}]
            """
            
            result = await safe_llm_completion(
                prompt=risk_prompt,
                task_type=LLMTask.ANALYSIS,
                max_tokens=800,
                temperature=0.2
            )
            
            # Use robust parsing
            ai_risks = self._parse_llm_response(result, expected_type="list")
            if ai_risks is not None and isinstance(ai_risks, list):
                # Validate and clean the results
                cleaned_risks = self._validate_and_clean_risks(ai_risks)
                logger.info(f"Successfully extracted and validated {len(cleaned_risks)} AI-identified risks")
                return cleaned_risks
            else:
                logger.info("AI risk assessment returned no valid risks, continuing with pattern-based analysis")
                return []
                
        except Exception as e:
            logger.error(f"AI risk assessment failed: {e}")
            return []
    
    async def _generate_ai_insights(self, title: str, content: str, doc_type: DocumentType, risks: List[Dict]) -> Dict[str, Any]:
        """Generate AI-powered insights and explanations"""
        try:
            insights_prompt = f"""
            Provide executive insights for this {doc_type.value} document analysis.
            
            Document: {title}
            Identified risks: {len(risks)} risks found
            
            High-level risks: {[r for r in risks if r.get('level') in ['high', 'critical']]}
            
            Provide:
            1. Executive summary (2-3 sentences)
            2. Key concerns (top 3)
            3. Business impact assessment
            4. Recommended actions
            
            Return as JSON:
            {{
                "executive_summary": "summary",
                "key_concerns": ["concern1", "concern2", "concern3"],
                "business_impact": "impact assessment",
                "recommended_actions": ["action1", "action2"]
            }}
            """
            
            result = await safe_llm_completion(
                prompt=insights_prompt,
                task_type=LLMTask.ANALYSIS,
                max_tokens=500,
                temperature=0.3
            )
            
            # Use robust parsing
            insights = self._parse_llm_response(result, expected_type="dict")
            if insights is not None and isinstance(insights, dict) and insights.get("parsed", True):
                logger.info("Successfully generated AI insights")
                return insights
            else:
                logger.info("AI insights generation failed, using structured fallback")
                return {
                    "executive_summary": "Document analysis completed with risk assessment.",
                    "key_concerns": [r.get("description", "Risk identified") for r in risks[:3]],
                    "business_impact": "Review recommended based on identified risks.",
                    "recommended_actions": ["Review flagged clauses", "Consult legal team if needed"],
                    "analysis_method": "fallback_structured"
                }
                
        except Exception as e:
            logger.error(f"AI insights generation failed: {e}")
            return {
                "error": f"Insights generation failed: {str(e)}",
                "executive_summary": "Analysis completed with errors.",
                "key_concerns": [],
                "business_impact": "Manual review recommended.",
                "recommended_actions": ["Manual document review required"]
            }
    
    def _calculate_overall_risk(self, risks: List[Dict[str, Any]]) -> RiskLevel:
        """Calculate overall risk level from individual risks"""
        if not risks:
            return RiskLevel.LOW
        
        # Count risks by level
        risk_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for risk in risks:
            level = risk.get("level", "low")
            if level in risk_counts:
                risk_counts[level] += 1
        
        # Determine overall risk
        if risk_counts["critical"] > 0:
            return RiskLevel.CRITICAL
        elif risk_counts["high"] >= 2:
            return RiskLevel.CRITICAL
        elif risk_counts["high"] >= 1:
            return RiskLevel.HIGH
        elif risk_counts["medium"] >= 3:
            return RiskLevel.HIGH
        elif risk_counts["medium"] >= 1:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _risk_to_score(self, risk_level: RiskLevel) -> float:
        """Convert risk level to numeric score (0.0 - 1.0)"""
        risk_scores = {
            RiskLevel.LOW: 0.2,
            RiskLevel.MEDIUM: 0.5,
            RiskLevel.HIGH: 0.8,
            RiskLevel.CRITICAL: 1.0
        }
        return risk_scores.get(risk_level, 0.5)
    
    def _generate_recommendations(self, risks: List[Dict], doc_type: DocumentType) -> List[str]:
        """Generate actionable recommendations based on risks"""
        recommendations = []
        
        # High-level recommendations based on risk levels
        high_risk_count = len([r for r in risks if r.get("level") in ["high", "critical"]])
        
        if high_risk_count > 0:
            recommendations.append("🚨 Immediate legal review recommended for high-risk clauses")
            recommendations.append("📋 Document approval workflow required before signing")
        
        # Document-type specific recommendations
        if doc_type == DocumentType.CONTRACT:
            if any("liability" in r.get("type", "") for r in risks):
                recommendations.append("⚖️ Review liability and indemnification terms")
            if any("termination" in r.get("type", "") for r in risks):
                recommendations.append("📅 Negotiate termination notice period")
        
        elif doc_type == DocumentType.INVOICE:
            if any("overdue" in r.get("type", "") for r in risks):
                recommendations.append("💰 Follow up on overdue payments immediately")
            if any("missing_po" in r.get("type", "") for r in risks):
                recommendations.append("📝 Verify purchase order authorization")
        
        elif doc_type == DocumentType.POLICY:
            if any("compliance" in r.get("type", "") for r in risks):
                recommendations.append("✅ Compliance audit required")
            if any("outdated" in r.get("type", "") for r in risks):
                recommendations.append("🔄 Policy update and review cycle needed")
        
        # Default recommendations if none specific
        if not recommendations:
            recommendations.append("✅ Document appears to have acceptable risk levels")
            recommendations.append("📊 Continue monitoring for changes")
        
        return recommendations

# Global risk analyzer instance
risk_analyzer = RiskAnalyzer()
