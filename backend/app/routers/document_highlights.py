"""
Document highlighting service for risk visualization
"""
import re
import logging
from typing import List, Dict, Any, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class DocumentHighlighter:
    """
    Service to generate risk highlights for document viewer
    """
    
    def __init__(self):
        # Risk patterns for highlighting - based on common contract risks
        self.risk_patterns = {
            # High Risk Patterns
            "liability_unlimited": {
                "pattern": r"unlimited\s+liability|unlimited\s+damages|without\s+limit|no\s+limit\s+on\s+damages",
                "risk_level": RiskLevel.HIGH,
                "clause_type": "liability",
                "title": "Unlimited Liability",
                "description": "This clause exposes your organization to unlimited financial liability"
            },
            "immediate_termination": {
                "pattern": r"terminate\s+immediately|without\s+notice|instant\s+termination|terminate\s+at\s+will",
                "risk_level": RiskLevel.HIGH,
                "clause_type": "termination",
                "title": "Immediate Termination",
                "description": "Contract can be terminated immediately without notice"
            },
            "indemnification_broad": {
                "pattern": r"indemnify.*against\s+all|hold\s+harmless.*all|indemnify.*any\s+and\s+all",
                "risk_level": RiskLevel.HIGH,
                "clause_type": "indemnification",
                "title": "Broad Indemnification",
                "description": "Broad indemnification clause that may expose you to significant liability"
            },
            "exclusive_jurisdiction": {
                "pattern": r"exclusive\s+jurisdiction|sole\s+jurisdiction|courts?\s+of.*shall\s+have\s+exclusive",
                "risk_level": RiskLevel.MEDIUM,
                "clause_type": "jurisdiction",
                "title": "Exclusive Jurisdiction",
                "description": "Legal disputes must be resolved in specific courts only"
            },
            
            # Medium Risk Patterns
            "auto_renewal": {
                "pattern": r"automatically\s+renew|auto[\-\s]?renew|shall\s+renew|automatic\s+renewal",
                "risk_level": RiskLevel.MEDIUM,
                "clause_type": "auto_renewal",
                "title": "Auto-Renewal Clause",
                "description": "Contract will automatically renew unless cancelled"
            },
            "penalty_clause": {
                "pattern": r"penalty|liquidated\s+damages|forfeit|late\s+fee|interest\s+on\s+overdue",
                "risk_level": RiskLevel.MEDIUM,
                "clause_type": "penalty",
                "title": "Penalty/Late Fee",
                "description": "Financial penalties may apply for non-compliance or late payment"
            },
            "intellectual_property": {
                "pattern": r"intellectual\s+property|IP\s+rights|proprietary\s+information|trade\s+secrets",
                "risk_level": RiskLevel.MEDIUM,
                "clause_type": "intellectual_property",
                "title": "Intellectual Property",
                "description": "Important intellectual property terms that require review"
            },
            "data_retention": {
                "pattern": r"data\s+retention|retain.*data|store.*information|data\s+storage",
                "risk_level": RiskLevel.MEDIUM,
                "clause_type": "data_retention",
                "title": "Data Retention",
                "description": "Terms regarding how long data will be stored"
            },
            
            # Low Risk but Important Patterns
            "governing_law": {
                "pattern": r"governing\s+law|governed\s+by|laws\s+of|jurisdiction\s+of",
                "risk_level": RiskLevel.LOW,
                "clause_type": "governing_law",
                "title": "Governing Law",
                "description": "Specifies which jurisdiction's laws apply"
            },
            "force_majeure": {
                "pattern": r"force\s+majeure|act\s+of\s+god|beyond.*control|unforeseeable",
                "risk_level": RiskLevel.LOW,
                "clause_type": "force_majeure",
                "title": "Force Majeure",
                "description": "Clause addressing unforeseeable circumstances"
            },
            "confidentiality": {
                "pattern": r"confidential|non[\-\s]?disclosure|NDA|proprietary\s+information",
                "risk_level": RiskLevel.LOW,
                "clause_type": "confidentiality",
                "title": "Confidentiality",
                "description": "Confidentiality and non-disclosure requirements"
            },
            "payment_terms": {
                "pattern": r"payment\s+terms|due\s+within|net\s+\d+|payment\s+due|invoice\s+date",
                "risk_level": RiskLevel.LOW,
                "clause_type": "payment",
                "title": "Payment Terms",
                "description": "Payment schedule and terms"
            }
        }
    
    def generate_highlights(self, text: str) -> List[Dict[str, Any]]:
        """
        Generate risk highlights for document text
        """
        highlights = []
        
        try:
            # Search for each risk pattern
            for pattern_name, pattern_config in self.risk_patterns.items():
                pattern = pattern_config["pattern"]
                
                # Find all matches with case-insensitive search
                for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                    start_pos = match.start()
                    end_pos = match.end()
                    matched_text = match.group()
                    
                    # Expand context slightly for better highlighting
                    context_start = max(0, start_pos - 10)
                    context_end = min(len(text), end_pos + 10)
                    
                    # Find word boundaries for cleaner highlighting
                    while context_start > 0 and text[context_start].isalnum():
                        context_start -= 1
                    while context_end < len(text) and text[context_end].isalnum():
                        context_end += 1
                    
                    highlight = {
                        "start_offset": start_pos,
                        "end_offset": end_pos,
                        "risk_level": pattern_config["risk_level"].value,
                        "clause_type": pattern_config["clause_type"],
                        "title": pattern_config["title"],
                        "description": pattern_config["description"],
                        "confidence": self._calculate_confidence(matched_text, pattern),
                        "matched_text": matched_text,
                        "context": text[context_start:context_end].strip()
                    }
                    
                    highlights.append(highlight)
            
            # Remove overlapping highlights (keep higher risk ones)
            highlights = self._remove_overlaps(highlights)
            
            # Sort by position in document
            highlights.sort(key=lambda x: x["start_offset"])
            
            logger.info(f"Generated {len(highlights)} highlights from text patterns")
            return highlights
            
        except Exception as e:
            logger.error(f"Error generating highlights: {e}")
            return []
    
    def _calculate_confidence(self, matched_text: str, pattern: str) -> float:
        """
        Calculate confidence score for a pattern match
        """
        # Base confidence
        confidence = 0.7
        
        # Adjust based on match quality
        if len(matched_text) > 20:  # Longer matches are more reliable
            confidence += 0.1
        
        # Check for exact keyword matches (higher confidence)
        high_confidence_keywords = [
            "unlimited liability", "terminate immediately", "auto-renewal",
            "liquidated damages", "indemnify", "governing law"
        ]
        
        for keyword in high_confidence_keywords:
            if keyword.lower() in matched_text.lower():
                confidence += 0.2
                break
        
        return min(confidence, 1.0)
    
    def _remove_overlaps(self, highlights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove overlapping highlights, keeping higher risk ones
        """
        if not highlights:
            return highlights
        
        # Sort by start position
        sorted_highlights = sorted(highlights, key=lambda x: x["start_offset"])
        
        # Risk level priority (higher number = higher priority)
        risk_priority = {
            RiskLevel.CRITICAL.value: 4,
            RiskLevel.HIGH.value: 3,
            RiskLevel.MEDIUM.value: 2,
            RiskLevel.LOW.value: 1
        }
        
        filtered_highlights = []
        
        for current in sorted_highlights:
            # Check for overlaps with existing highlights
            overlaps = False
            
            for existing in filtered_highlights:
                if self._highlights_overlap(current, existing):
                    # If current has higher priority, replace existing
                    current_priority = risk_priority.get(current["risk_level"], 1)
                    existing_priority = risk_priority.get(existing["risk_level"], 1)
                    
                    if current_priority > existing_priority:
                        filtered_highlights.remove(existing)
                        filtered_highlights.append(current)
                    
                    overlaps = True
                    break
            
            if not overlaps:
                filtered_highlights.append(current)
        
        return filtered_highlights
    
    def _highlights_overlap(self, h1: Dict[str, Any], h2: Dict[str, Any]) -> bool:
        """
        Check if two highlights overlap
        """
        return not (h1["end_offset"] <= h2["start_offset"] or h2["end_offset"] <= h1["start_offset"])

# Global highlighter instance
document_highlighter = DocumentHighlighter()
