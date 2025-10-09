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
                "pattern": r"automatically\s+renew|auto[\-\s]?renew|shall\s+renew|automatic\s+renewal|renew\s+automatically",
                "risk_level": RiskLevel.MEDIUM,
                "clause_type": "auto_renewal",
                "title": "Auto-Renewal Clause",
                "description": "Contract will automatically renew unless cancelled"
            },
            "penalty_clause": {
                "pattern": r"penalty|liquidated\s+damages|forfeit|late\s+fee|interest\s+on\s+overdue|breach\s+penalty",
                "risk_level": RiskLevel.MEDIUM,
                "clause_type": "penalty",
                "title": "Penalty/Late Fee",
                "description": "Financial penalties may apply for non-compliance or late payment"
            },
            "intellectual_property": {
                "pattern": r"intellectual\s+property|IP\s+rights|proprietary\s+information|trade\s+secrets|copyright|patent|trademark",
                "risk_level": RiskLevel.MEDIUM,
                "clause_type": "intellectual_property",
                "title": "Intellectual Property",
                "description": "Important intellectual property terms that require review"
            },
            "data_retention": {
                "pattern": r"data\s+retention|retain.*data|store.*information|data\s+storage|personal\s+data|GDPR|privacy",
                "risk_level": RiskLevel.MEDIUM,
                "clause_type": "data_retention",
                "title": "Data Retention",
                "description": "Terms regarding how long data will be stored"
            },
            "limitation_liability": {
                "pattern": r"limitation\s+of\s+liability|limit.*liability|liability.*limited|maximum\s+liability",
                "risk_level": RiskLevel.MEDIUM,
                "clause_type": "liability_limitation",
                "title": "Liability Limitation",
                "description": "Clause limiting liability exposure"
            },
            "warranty_disclaimer": {
                "pattern": r"disclaimer|no\s+warranty|without\s+warranty|as\s+is|merchantability|fitness\s+for\s+purpose",
                "risk_level": RiskLevel.MEDIUM,
                "clause_type": "warranty",
                "title": "Warranty Disclaimer",
                "description": "Warranty disclaimers and limitations"
            },
            "service_level": {
                "pattern": r"service\s+level|SLA|uptime|availability|performance\s+standard|response\s+time",
                "risk_level": RiskLevel.MEDIUM,
                "clause_type": "service_level",
                "title": "Service Level Agreement",
                "description": "Service level commitments and standards"
            },
            
            # Low Risk but Important Patterns
            "governing_law": {
                "pattern": r"governing\s+law|governed\s+by|laws\s+of|jurisdiction\s+of|applicable\s+law",
                "risk_level": RiskLevel.LOW,
                "clause_type": "governing_law",
                "title": "Governing Law",
                "description": "Specifies which jurisdiction's laws apply"
            },
            "force_majeure": {
                "pattern": r"force\s+majeure|act\s+of\s+god|beyond.*control|unforeseeable|natural\s+disaster",
                "risk_level": RiskLevel.LOW,
                "clause_type": "force_majeure",
                "title": "Force Majeure",
                "description": "Clause addressing unforeseeable circumstances"
            },
            "confidentiality": {
                "pattern": r"confidential|non[\-\s]?disclosure|NDA|proprietary\s+information|trade\s+secret",
                "risk_level": RiskLevel.LOW,
                "clause_type": "confidentiality",
                "title": "Confidentiality",
                "description": "Confidentiality and non-disclosure requirements"
            },
            "payment_terms": {
                "pattern": r"payment\s+terms|due\s+within|net\s+\d+|payment\s+due|invoice\s+date|billing\s+cycle",
                "risk_level": RiskLevel.LOW,
                "clause_type": "payment",
                "title": "Payment Terms",
                "description": "Payment schedule and terms"
            },
            "term_duration": {
                "pattern": r"term\s+of|duration|effective\s+period|contract\s+period|expires?\s+on|valid\s+until",
                "risk_level": RiskLevel.LOW,
                "clause_type": "term",
                "title": "Contract Term",
                "description": "Contract duration and term specifications"
            },
            "notice_requirements": {
                "pattern": r"notice|notification|written\s+notice|days?\s+notice|prior\s+notice|advance\s+notice",
                "risk_level": RiskLevel.LOW,
                "clause_type": "notice",
                "title": "Notice Requirements",
                "description": "Requirements for providing notice"
            },
            "assignment": {
                "pattern": r"assignment|assign|transfer|delegate|successor|binding\s+upon",
                "risk_level": RiskLevel.LOW,
                "clause_type": "assignment",
                "title": "Assignment Rights",
                "description": "Rights to assign or transfer the contract"
            },
            "severability": {
                "pattern": r"severability|severable|invalid|unenforceable|remainder\s+shall",
                "risk_level": RiskLevel.LOW,
                "clause_type": "severability",
                "title": "Severability",
                "description": "Clause ensuring contract remains valid if parts are invalid"
            },
            
            # Financial and monetary patterns
            "monetary_amounts": {
                "pattern": r'\$[\d,]+(?:\.\d{2})?|USD?\s*[\d,]+(?:\.\d{2})?|[\d,]+(?:\.\d{2})?\s*dollars?|[\d,]+(?:\.\d{2})?\s*USD',
                "risk_level": RiskLevel.LOW,
                "clause_type": "financial",
                "title": "Monetary Amount",
                "description": "Specific monetary amount mentioned in the document"
            },
            "payment_amounts": {
                "pattern": r'amount\s+of\s+\$?[\d,]+|sum\s+of\s+\$?[\d,]+|total\s+of\s+\$?[\d,]+|payment\s+of\s+\$?[\d,]+|fee\s+of\s+\$?[\d,]+|cost\s+of\s+\$?[\d,]+|price\s+of\s+\$?[\d,]+|value\s+of\s+\$?[\d,]+|worth\s+\$?[\d,]+|budget\s+of\s+\$?[\d,]+|limit\s+of\s+\$?[\d,]+|maximum\s+of\s+\$?[\d,]+|minimum\s+of\s+\$?[\d,]+|not\s+to\s+exceed\s+\$?[\d,]+|up\s+to\s+\$?[\d,]+',
                "risk_level": RiskLevel.MEDIUM,
                "clause_type": "financial",
                "title": "Payment Amount",
                "description": "Payment or financial obligation amount"
            },
            "financial_terms": {
                "pattern": r'compensation|salary|wage|revenue|profit|loss|budget|expense|invoice|bill|charge|rate|financial|monetary|currency|cash|funds|capital|investment|liability|debt|credit|balance|tax|penalty|interest|discount|refund|bonus|commission|premium|deposit|damages',
                "risk_level": RiskLevel.LOW,
                "clause_type": "financial",
                "title": "Financial Terms",
                "description": "Financial or monetary terms and conditions"
            },
            "payment_schedule": {
                "pattern": r'net\s+\d+\s+days?|due\s+within\s+\d+\s+days?|payment\s+terms?|billing\s+cycle|invoice\s+date|due\s+date|payment\s+schedule|installment\s+plan|monthly\s+payment|quarterly\s+payment|annual\s+payment|milestone\s+payments?|progress\s+payments?',
                "risk_level": RiskLevel.MEDIUM,
                "clause_type": "payment_terms",
                "title": "Payment Schedule",
                "description": "Payment timing and schedule requirements"
            },
            "late_fees": {
                "pattern": r'late\s+fee|late\s+payment|interest\s+on\s+overdue|penalty\s+for\s+late\s+payment|overdue\s+amount|outstanding\s+balance',
                "risk_level": RiskLevel.MEDIUM,
                "clause_type": "penalty",
                "title": "Late Payment Penalties",
                "description": "Penalties and fees for late payments"
            }
        }
    
    def generate_highlights(self, text: str, highlight_type: str = "risk") -> List[Dict[str, Any]]:
        """
        Generate highlights for document text
        
        Args:
            text: Document text to analyze
            highlight_type: Type of highlighting - "risk", "financial", or "all"
        """
        highlights = []
        
        try:
            patterns_to_use = self.risk_patterns
            
            # Filter patterns based on highlight type
            if highlight_type == "financial":
                patterns_to_use = {k: v for k, v in self.risk_patterns.items() 
                                 if v["clause_type"] in ["financial", "payment_terms", "penalty"]}
            elif highlight_type == "risk":
                patterns_to_use = {k: v for k, v in self.risk_patterns.items() 
                                 if v["clause_type"] not in ["financial", "payment_terms"]}
            # "all" uses all patterns
            
            # Search for each pattern
            for pattern_name, pattern_config in patterns_to_use.items():
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
                        "context": text[context_start:context_end].strip(),
                        "highlight_type": highlight_type,
                        "pattern_name": pattern_name
                    }
                    
                    highlights.append(highlight)
            
            # Remove overlapping highlights (keep higher risk ones)
            highlights = self._remove_overlaps(highlights)
            
            # Sort by position in document
            highlights.sort(key=lambda x: x["start_offset"])
            
            logger.info(f"Generated {len(highlights)} {highlight_type} highlights from text patterns")
            return highlights
            
        except Exception as e:
            logger.error(f"Error generating highlights: {e}")
            return []
    
    def generate_financial_highlights(self, text: str, query: str = None) -> List[Dict[str, Any]]:
        """
        Generate financial-specific highlights for document text
        
        Args:
            text: Document text to analyze
            query: Optional search query to focus highlighting
        """
        highlights = []
        
        try:
            # Enhanced financial patterns for better detection
            financial_patterns = {
                "currency_amounts": r'\$[\d,]+(?:\.\d{2})?|\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars?|USD|usd)\b',
                "payment_references": r'\b(?:payment|fee|cost|price|amount|sum|total|charge|rate|salary|wage|compensation|revenue|profit|budget|expense|invoice|bill)\s+(?:of\s+)?\$?[\d,]+(?:\.\d{2})?\b',
                "financial_terms": r'\b(?:liability|damages|penalty|interest|discount|refund|bonus|commission|premium|deposit|escrow|retainer|advance|installment|lump\s+sum|net\s+amount|gross\s+amount|deductible|coverage|limit|maximum|minimum|cap)\b',
                "payment_timing": r'\b(?:net\s+\d+\s+days?|due\s+within\s+\d+\s+days?|monthly|quarterly|annually|upfront|advance|milestone|progress|final\s+payment|balance\s+due|overdue)\b',
                "percentage_rates": r'\b\d+(?:\.\d+)?%\s*(?:per\s+)?(?:annum|annual|monthly|daily|interest|rate|fee|commission|penalty)?\b'
            }
            
            # If query is provided, check if it's financial-related
            is_financial_query = False
            if query:
                financial_keywords = ['dollar', 'dollars', 'amount', 'money', 'cost', 'price', 'fee', 'payment', 'financial', 'monetary']
                is_financial_query = any(keyword in query.lower() for keyword in financial_keywords)
            
            # Search for financial patterns
            for pattern_name, pattern in financial_patterns.items():
                for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                    start_pos = match.start()
                    end_pos = match.end()
                    matched_text = match.group()
                    
                    # Get surrounding context
                    context_start = max(0, start_pos - 50)
                    context_end = min(len(text), end_pos + 50)
                    context = text[context_start:context_end].strip()
                    
                    # Determine highlight importance
                    risk_level = RiskLevel.LOW
                    if pattern_name in ["currency_amounts", "payment_references"]:
                        risk_level = RiskLevel.MEDIUM
                    elif "penalty" in matched_text.lower() or "damages" in matched_text.lower():
                        risk_level = RiskLevel.HIGH
                    
                    highlight = {
                        "start_offset": start_pos,
                        "end_offset": end_pos,
                        "risk_level": risk_level.value,
                        "clause_type": "financial",
                        "title": f"Financial Term: {pattern_name.replace('_', ' ').title()}",
                        "description": f"Financial content: {matched_text}",
                        "confidence": 0.9 if is_financial_query else 0.7,
                        "matched_text": matched_text,
                        "context": context,
                        "highlight_type": "financial",
                        "pattern_name": pattern_name,
                        "is_query_related": is_financial_query
                    }
                    
                    highlights.append(highlight)
            
            # Remove overlapping highlights
            highlights = self._remove_overlaps(highlights)
            
            # Sort by position in document
            highlights.sort(key=lambda x: x["start_offset"])
            
            logger.info(f"Generated {len(highlights)} financial highlights")
            return highlights
            
        except Exception as e:
            logger.error(f"Error generating financial highlights: {e}")
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
        Remove overlapping highlights, keeping higher risk ones but being less aggressive
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
            # Check for significant overlaps with existing highlights (more than 50% overlap)
            should_add = True
            to_remove = []
            
            for i, existing in enumerate(filtered_highlights):
                overlap_ratio = self._calculate_overlap_ratio(current, existing)
                
                # Only consider it an overlap if more than 50% of the text overlaps
                if overlap_ratio > 0.5:
                    current_priority = risk_priority.get(current["risk_level"], 1)
                    existing_priority = risk_priority.get(existing["risk_level"], 1)
                    
                    if current_priority > existing_priority:
                        # Replace existing with current
                        to_remove.append(i)
                    else:
                        # Keep existing, don't add current
                        should_add = False
                        break
            
            # Remove highlights that should be replaced
            for i in reversed(to_remove):
                filtered_highlights.pop(i)
            
            if should_add:
                filtered_highlights.append(current)
        
        logger.info(f"Highlight deduplication: {len(highlights)} -> {len(filtered_highlights)} highlights")
        return filtered_highlights
    
    def _calculate_overlap_ratio(self, h1: Dict[str, Any], h2: Dict[str, Any]) -> float:
        """
        Calculate the ratio of overlap between two highlights
        """
        start1, end1 = h1["start_offset"], h1["end_offset"]
        start2, end2 = h2["start_offset"], h2["end_offset"]
        
        # Calculate overlap
        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)
        
        if overlap_start >= overlap_end:
            return 0.0  # No overlap
        
        overlap_length = overlap_end - overlap_start
        min_length = min(end1 - start1, end2 - start2)
        
        return overlap_length / min_length if min_length > 0 else 0.0
    
    def _highlights_overlap(self, h1: Dict[str, Any], h2: Dict[str, Any]) -> bool:
        """
        Check if two highlights overlap
        """
        return not (h1["end_offset"] <= h2["start_offset"] or h2["end_offset"] <= h1["start_offset"])

# Global highlighter instance
document_highlighter = DocumentHighlighter()

# API endpoints for highlighting
from fastapi import APIRouter, Query, HTTPException
from typing import Optional

router = APIRouter(prefix="/api/highlights", tags=["highlights"])

@router.get("/generate")
async def generate_document_highlights(
    text: str = Query(..., description="Document text to highlight"),
    highlight_type: str = Query("risk", description="Type of highlighting: risk, financial, or all"),
    query: Optional[str] = Query(None, description="Search query for context-aware highlighting")
):
    """
    Generate highlights for document text
    """
    try:
        if highlight_type == "financial":
            highlights = document_highlighter.generate_financial_highlights(text, query)
        else:
            highlights = document_highlighter.generate_highlights(text, highlight_type)
        
        return {
            "highlights": highlights,
            "total_count": len(highlights),
            "highlight_type": highlight_type,
            "query": query
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating highlights: {str(e)}")

@router.get("/financial")
async def generate_financial_highlights(
    text: str = Query(..., description="Document text to analyze for financial content"),
    query: Optional[str] = Query(None, description="Financial search query for context")
):
    """
    Generate financial-specific highlights for document text
    """
    try:
        highlights = document_highlighter.generate_financial_highlights(text, query)
        
        # Group highlights by type for better organization
        grouped_highlights = {}
        for highlight in highlights:
            pattern_name = highlight.get("pattern_name", "other")
            if pattern_name not in grouped_highlights:
                grouped_highlights[pattern_name] = []
            grouped_highlights[pattern_name].append(highlight)
        
        return {
            "highlights": highlights,
            "grouped_highlights": grouped_highlights,
            "total_count": len(highlights),
            "financial_terms_found": len(grouped_highlights),
            "query": query
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating financial highlights: {str(e)}")
