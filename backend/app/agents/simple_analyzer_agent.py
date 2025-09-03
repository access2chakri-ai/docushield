"""
Simple Analyzer Agent - Basic document analysis without LLM dependencies
For debugging and fallback scenarios
"""
import logging
from typing import Dict, List, Any
from datetime import datetime

from .base_agent import BaseAgent, AgentContext, AgentResult

logger = logging.getLogger(__name__)

class SimpleAnalyzerAgent(BaseAgent):
    """
    Simple analyzer that performs basic document analysis without LLM calls
    Used for debugging and when LLM services are unavailable
    """
    
    def __init__(self):
        super().__init__("simple_analyzer_agent")
        
        # Basic keywords to look for
        self.risk_keywords = {
            "high": ["unlimited liability", "immediate termination", "without notice", "penalty", "forfeiture"],
            "medium": ["auto-renewal", "evergreen", "exclusive", "non-compete", "confidential"],
            "low": ["payment terms", "delivery", "warranty", "support", "maintenance"]
        }
    
    async def analyze(self, context: AgentContext) -> AgentResult:
        """
        Simple analysis without LLM calls
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Starting simple analysis for contract {context.contract_id}")
            
            # Get contract with text
            contract = await self.get_contract_with_all_data(context.contract_id)
            if not contract or not contract.text_raw:
                return self.create_result(
                    success=False,
                    error_message="No contract text available"
                )
            
            text_content = contract.text_raw.raw_text.lower()
            self.logger.info(f"Analyzing {len(text_content)} characters of text")
            
            # Simple keyword-based analysis
            findings = []
            risk_score = 0.0
            
            for risk_level, keywords in self.risk_keywords.items():
                for keyword in keywords:
                    if keyword.lower() in text_content:
                        severity_map = {"high": 0.8, "medium": 0.6, "low": 0.4}
                        risk_score += severity_map.get(risk_level, 0.5)
                        
                        findings.append({
                            "type": "keyword_detection",
                            "title": f"Found {risk_level} risk keyword: {keyword}",
                            "description": f"Detected potential {risk_level} risk keyword '{keyword}' in document",
                            "severity": risk_level,
                            "confidence": 0.7,
                            "keyword": keyword
                        })
            
            # Normalize risk score
            risk_score = min(1.0, risk_score / 10.0)
            
            # Generate basic recommendations
            recommendations = []
            if risk_score > 0.7:
                recommendations.append("High risk indicators detected - legal review recommended")
            elif risk_score > 0.4:
                recommendations.append("Medium risk detected - consider contract modifications")
            else:
                recommendations.append("Low risk detected - standard review process")
            
            if len(findings) > 5:
                recommendations.append("Multiple risk factors identified - comprehensive review needed")
            
            # Add basic document stats
            word_count = len(text_content.split())
            findings.append({
                "type": "document_stats",
                "title": f"Document contains {word_count} words",
                "description": f"Basic document statistics: {word_count} words, {len(text_content)} characters",
                "severity": "info",
                "confidence": 1.0,
                "word_count": word_count
            })
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.info(f"Simple analysis completed in {execution_time:.2f}ms")
            
            return self.create_result(
                success=True,
                confidence=0.8,  # Simple analysis has moderate confidence
                findings=findings,
                recommendations=recommendations,
                data_used={
                    "text_length": len(text_content),
                    "keywords_checked": sum(len(kws) for kws in self.risk_keywords.values()),
                    "risk_score": risk_score
                },
                execution_time_ms=execution_time,
                llm_calls=0  # No LLM calls
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.error(f"Simple analysis failed: {e}")
            
            return self.create_result(
                success=False,
                execution_time_ms=execution_time,
                error_message=str(e)
            )
