"""
Privacy-Safe Document Processing Module
Ensures PII and sensitive data is protected before sending to external LLM APIs
Compliant with GDPR, HIPAA, SOX, and other privacy regulations
"""
import re
import json
import logging
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class PIIType(Enum):
    """Types of PII that need protection"""
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"
    NAME = "name"
    DATE_OF_BIRTH = "date_of_birth"
    BANK_ACCOUNT = "bank_account"
    MEDICAL_ID = "medical_id"
    IP_ADDRESS = "ip_address"
    FINANCIAL_ACCOUNT = "financial_account"
    PASSPORT = "passport"
    DRIVER_LICENSE = "driver_license"
    CUSTOM_ID = "custom_id"

class SensitivityLevel(Enum):
    """Document sensitivity levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    TOP_SECRET = "top_secret"

@dataclass
class PIIMatch:
    """Represents a detected PII instance"""
    pii_type: PIIType
    original_value: str
    replacement_token: str
    start_pos: int
    end_pos: int
    confidence: float
    context: str

@dataclass
class RedactionResult:
    """Result of PII redaction process"""
    redacted_text: str
    pii_matches: List[PIIMatch]
    redaction_map: Dict[str, str]  # token -> original value
    sensitivity_level: SensitivityLevel
    safe_for_external_api: bool
    redaction_summary: Dict[str, int]

class PrivacySafeProcessor:
    """
    Main class for privacy-safe document processing
    Handles PII detection, redaction, and safe content generation
    """
    
    def __init__(self):
        self.pii_patterns = self._initialize_pii_patterns()
        self.sensitive_keywords = self._initialize_sensitive_keywords()
        self.redaction_cache = {}
        
    def _initialize_pii_patterns(self) -> Dict[PIIType, List[Tuple[str, float]]]:
        """Initialize regex patterns for PII detection with confidence scores"""
        return {
            PIIType.SSN: [
                (r'\b\d{3}-\d{2}-\d{4}\b', 0.95),
                (r'\b\d{3}\s\d{2}\s\d{4}\b', 0.90),
                (r'\b\d{9}\b', 0.70),  # Lower confidence for 9 digits
            ],
            PIIType.CREDIT_CARD: [
                (r'\b4\d{3}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', 0.95),  # Visa
                (r'\b5[1-5]\d{2}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', 0.95),  # MasterCard
                (r'\b3[47]\d{2}[\s-]?\d{6}[\s-]?\d{5}\b', 0.95),  # Amex
                (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', 0.80),  # Generic
            ],
            PIIType.EMAIL: [
                (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 0.95),
            ],
            PIIType.PHONE: [
                (r'\b\(\d{3}\)\s?\d{3}-\d{4}\b', 0.95),
                (r'\b\d{3}-\d{3}-\d{4}\b', 0.90),
                (r'\b\d{3}\.\d{3}\.\d{4}\b', 0.90),
                (r'\b\+1[\s-]?\d{3}[\s-]?\d{3}[\s-]?\d{4}\b', 0.95),
            ],
            PIIType.ADDRESS: [
                (r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Place|Pl)\b', 0.85),
                (r'\b\d+\s+[A-Za-z\s]+,\s*[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?\b', 0.90),
            ],
            PIIType.DATE_OF_BIRTH: [
                (r'\b(?:DOB|Date of Birth|Born)[\s:]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b', 0.90),
                (r'\b(?:DOB|Date of Birth|Born)[\s:]*([A-Za-z]+ \d{1,2}, \d{4})\b', 0.90),
            ],
            PIIType.BANK_ACCOUNT: [
                (r'\b(?:Account|Acct)[\s#:]*(\d{8,17})\b', 0.80),
                (r'\b(?:Routing|ABA)[\s#:]*(\d{9})\b', 0.85),
            ],
            PIIType.MEDICAL_ID: [
                (r'\b(?:Patient ID|Medical Record|MRN)[\s#:]*([A-Z0-9]{6,15})\b', 0.85),
                (r'\b(?:Insurance|Policy)[\s#:]*([A-Z0-9]{8,20})\b', 0.75),
            ],
            PIIType.IP_ADDRESS: [
                (r'\b(?:\d{1,3}\.){3}\d{1,3}\b', 0.90),
                (r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b', 0.95),  # IPv6
            ],
            PIIType.PASSPORT: [
                (r'\b[A-Z]{1,2}\d{6,9}\b', 0.75),
                (r'\bPassport[\s#:]*([A-Z0-9]{6,12})\b', 0.85),
            ],
            PIIType.DRIVER_LICENSE: [
                (r'\b(?:DL|Driver License|License)[\s#:]*([A-Z0-9]{8,15})\b', 0.80),
            ],
        }
    
    def _initialize_sensitive_keywords(self) -> Dict[str, float]:
        """Initialize sensitive keywords that indicate confidential content"""
        return {
            # Legal/Confidential
            'confidential': 0.9,
            'proprietary': 0.9,
            'trade secret': 0.95,
            'attorney-client': 0.95,
            'privileged': 0.9,
            'classified': 0.95,
            'restricted': 0.8,
            'internal only': 0.85,
            
            # Financial
            'salary': 0.8,
            'compensation': 0.8,
            'bonus': 0.7,
            'financial statements': 0.85,
            'tax return': 0.9,
            'credit report': 0.9,
            'bank statement': 0.9,
            
            # Medical/Health
            'medical record': 0.95,
            'patient': 0.8,
            'diagnosis': 0.9,
            'treatment': 0.8,
            'prescription': 0.85,
            'health information': 0.9,
            'phi': 0.95,  # Protected Health Information
            
            # Personal
            'social security': 0.95,
            'passport': 0.9,
            'driver license': 0.85,
            'birth certificate': 0.9,
            'personal information': 0.8,
            'pii': 0.95,  # Personally Identifiable Information
        }
    
    def detect_pii(self, text: str) -> List[PIIMatch]:
        """Detect all PII instances in text"""
        pii_matches = []
        
        for pii_type, patterns in self.pii_patterns.items():
            for pattern, confidence in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    # Get context around the match
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    context = text[start:end]
                    
                    # Generate replacement token
                    token = f"[{pii_type.value.upper()}_{uuid.uuid4().hex[:8]}]"
                    
                    pii_match = PIIMatch(
                        pii_type=pii_type,
                        original_value=match.group(),
                        replacement_token=token,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=confidence,
                        context=context
                    )
                    
                    pii_matches.append(pii_match)
        
        # Sort by position (reverse order for replacement)
        return sorted(pii_matches, key=lambda x: x.start_pos, reverse=True)
    
    def detect_names(self, text: str) -> List[PIIMatch]:
        """Detect potential names using pattern matching"""
        name_matches = []
        
        # Pattern for potential names (capitalized words)
        name_patterns = [
            (r'\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b', 0.70),  # First Last
            (r'\b[A-Z][a-z]{2,}\s+[A-Z]\.\s+[A-Z][a-z]{2,}\b', 0.80),  # First M. Last
            (r'\b(?:Mr|Mrs|Ms|Dr|Prof)\.?\s+[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?\b', 0.85),  # Title Name
        ]
        
        # Common first names (sample - in production, use comprehensive list)
        common_names = {
            'john', 'jane', 'michael', 'sarah', 'david', 'mary', 'robert', 'jennifer',
            'william', 'elizabeth', 'james', 'patricia', 'charles', 'linda', 'joseph',
            'barbara', 'thomas', 'susan', 'christopher', 'jessica', 'daniel', 'karen'
        }
        
        for pattern, base_confidence in name_patterns:
            matches = re.finditer(pattern, text)
            
            for match in matches:
                matched_text = match.group()
                
                # Increase confidence if contains common name
                confidence = base_confidence
                if any(name in matched_text.lower() for name in common_names):
                    confidence = min(0.95, confidence + 0.15)
                
                # Skip if it looks like a company name
                if any(suffix in matched_text for suffix in ['Inc', 'LLC', 'Corp', 'Ltd']):
                    continue
                
                token = f"[NAME_{uuid.uuid4().hex[:8]}]"
                
                name_match = PIIMatch(
                    pii_type=PIIType.NAME,
                    original_value=matched_text,
                    replacement_token=token,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=confidence,
                    context=text[max(0, match.start()-30):match.end()+30]
                )
                
                name_matches.append(name_match)
        
        return name_matches
    
    def assess_sensitivity_level(self, text: str, pii_matches: List[PIIMatch]) -> SensitivityLevel:
        """Assess document sensitivity level based on content"""
        text_lower = text.lower()
        
        # Check for explicit sensitivity markers
        if any(marker in text_lower for marker in ['top secret', 'classified', 'eyes only']):
            return SensitivityLevel.TOP_SECRET
        
        if any(marker in text_lower for marker in ['restricted', 'confidential', 'proprietary']):
            return SensitivityLevel.RESTRICTED
        
        # Check PII density and types
        high_risk_pii = [PIIType.SSN, PIIType.CREDIT_CARD, PIIType.MEDICAL_ID, PIIType.PASSPORT]
        high_risk_count = sum(1 for match in pii_matches if match.pii_type in high_risk_pii)
        
        if high_risk_count > 0:
            return SensitivityLevel.RESTRICTED
        
        # Check for sensitive keywords
        sensitive_score = 0
        for keyword, weight in self.sensitive_keywords.items():
            if keyword in text_lower:
                sensitive_score += weight
        
        if sensitive_score > 2.0:
            return SensitivityLevel.CONFIDENTIAL
        elif sensitive_score > 1.0:
            return SensitivityLevel.INTERNAL
        else:
            return SensitivityLevel.PUBLIC
    
    def redact_pii(self, text: str, aggressive_mode: bool = True) -> RedactionResult:
        """
        Redact PII from text and return safe version for external APIs
        
        Args:
            text: Original text to redact
            aggressive_mode: If True, redact more aggressively (recommended for external APIs)
        """
        logger.info(f"🔒 Starting PII redaction (aggressive_mode={aggressive_mode})")
        
        # Detect all PII
        pii_matches = self.detect_pii(text)
        
        # Detect names if in aggressive mode
        if aggressive_mode:
            name_matches = self.detect_names(text)
            pii_matches.extend(name_matches)
        
        # Remove overlapping matches (keep highest confidence)
        pii_matches = self._remove_overlapping_matches(pii_matches)
        
        # Assess sensitivity level
        sensitivity_level = self.assess_sensitivity_level(text, pii_matches)
        
        # Perform redaction
        redacted_text = text
        redaction_map = {}
        
        for match in pii_matches:
            redacted_text = (
                redacted_text[:match.start_pos] + 
                match.replacement_token + 
                redacted_text[match.end_pos:]
            )
            redaction_map[match.replacement_token] = match.original_value
        
        # Generate redaction summary
        redaction_summary = {}
        for match in pii_matches:
            pii_type = match.pii_type.value
            redaction_summary[pii_type] = redaction_summary.get(pii_type, 0) + 1
        
        # Determine if safe for external API
        safe_for_external_api = (
            sensitivity_level in [SensitivityLevel.PUBLIC, SensitivityLevel.INTERNAL] and
            len(pii_matches) == 0
        ) or (
            aggressive_mode and 
            sensitivity_level != SensitivityLevel.TOP_SECRET
        )
        
        logger.info(f"🔒 PII redaction complete:")
        logger.info(f"   📊 PII instances found: {len(pii_matches)}")
        logger.info(f"   🔐 Sensitivity level: {sensitivity_level.value}")
        logger.info(f"   ✅ Safe for external API: {safe_for_external_api}")
        logger.info(f"   📋 Redaction summary: {redaction_summary}")
        
        return RedactionResult(
            redacted_text=redacted_text,
            pii_matches=pii_matches,
            redaction_map=redaction_map,
            sensitivity_level=sensitivity_level,
            safe_for_external_api=safe_for_external_api,
            redaction_summary=redaction_summary
        )
    
    def _remove_overlapping_matches(self, matches: List[PIIMatch]) -> List[PIIMatch]:
        """Remove overlapping PII matches, keeping highest confidence ones"""
        if not matches:
            return matches
        
        # Sort by confidence (descending) then by position
        sorted_matches = sorted(matches, key=lambda x: (-x.confidence, x.start_pos))
        
        non_overlapping = []
        for match in sorted_matches:
            # Check if this match overlaps with any already selected
            overlaps = False
            for selected in non_overlapping:
                if (match.start_pos < selected.end_pos and 
                    match.end_pos > selected.start_pos):
                    overlaps = True
                    break
            
            if not overlaps:
                non_overlapping.append(match)
        
        # Sort back by position for replacement
        return sorted(non_overlapping, key=lambda x: x.start_pos, reverse=True)
    
    def create_safe_summary(self, text: str, max_length: int = 1000) -> str:
        """
        Create a safe summary of the document for external API analysis
        Removes PII and sensitive content while preserving analytical value
        """
        # First redact PII
        redaction_result = self.redact_pii(text, aggressive_mode=True)
        
        if not redaction_result.safe_for_external_api:
            # For highly sensitive documents, create generic summary
            return self._create_generic_summary(text, redaction_result.sensitivity_level)
        
        # Create safe summary from redacted text
        redacted_text = redaction_result.redacted_text
        
        # Extract key structural elements safely
        safe_elements = []
        
        # Document type indicators
        doc_type_indicators = self._extract_document_type_indicators(redacted_text)
        if doc_type_indicators:
            safe_elements.append(f"Document type indicators: {', '.join(doc_type_indicators)}")
        
        # Key sections/headings
        headings = self._extract_safe_headings(redacted_text)
        if headings:
            safe_elements.append(f"Key sections: {', '.join(headings[:5])}")
        
        # Document structure
        structure_info = self._analyze_document_structure(redacted_text)
        safe_elements.append(structure_info)
        
        # Combine elements
        safe_summary = ". ".join(safe_elements)
        
        # Truncate if needed
        if len(safe_summary) > max_length:
            safe_summary = safe_summary[:max_length-3] + "..."
        
        return safe_summary
    
    def _create_generic_summary(self, text: str, sensitivity_level: SensitivityLevel) -> str:
        """Create generic summary for highly sensitive documents"""
        word_count = len(text.split())
        char_count = len(text)
        
        return (
            f"Sensitive document ({sensitivity_level.value}) with {word_count:,} words "
            f"and {char_count:,} characters. Contains PII or confidential information "
            f"that cannot be processed by external APIs. Manual review required."
        )
    
    def _extract_document_type_indicators(self, text: str) -> List[str]:
        """Extract safe document type indicators"""
        indicators = []
        text_lower = text.lower()
        
        type_patterns = {
            'contract': ['agreement', 'contract', 'terms and conditions'],
            'invoice': ['invoice', 'bill', 'payment due', 'amount owed'],
            'policy': ['policy', 'procedure', 'guidelines', 'rules'],
            'report': ['report', 'analysis', 'findings', 'summary'],
            'legal': ['whereas', 'party', 'jurisdiction', 'governing law'],
            'financial': ['financial', 'accounting', 'revenue', 'expenses']
        }
        
        for doc_type, patterns in type_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                indicators.append(doc_type)
        
        return indicators[:3]  # Limit to top 3
    
    def _extract_safe_headings(self, text: str) -> List[str]:
        """Extract document headings that don't contain PII"""
        headings = []
        
        # Pattern for headings (lines that are all caps or title case)
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if (len(line) > 5 and len(line) < 100 and 
                (line.isupper() or line.istitle()) and
                not any(char.isdigit() for char in line) and  # Avoid lines with numbers
                '[' not in line):  # Avoid redacted content
                headings.append(line)
        
        return headings[:10]  # Limit to 10 headings
    
    def _analyze_document_structure(self, text: str) -> str:
        """Analyze document structure safely"""
        lines = text.split('\n')
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        
        return (
            f"Document structure: {len(lines)} lines, {len(paragraphs)} paragraphs, "
            f"{len(text.split())} words"
        )
    
    def restore_pii(self, redacted_text: str, redaction_map: Dict[str, str]) -> str:
        """Restore original PII from redacted text using redaction map"""
        restored_text = redacted_text
        
        for token, original_value in redaction_map.items():
            restored_text = restored_text.replace(token, original_value)
        
        return restored_text
    
    def is_safe_for_external_api(self, text: str) -> Tuple[bool, str]:
        """
        Quick check if text is safe for external API without full redaction
        Returns (is_safe, reason)
        """
        # Quick PII check
        for pii_type, patterns in self.pii_patterns.items():
            for pattern, _ in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return False, f"Contains {pii_type.value}"
        
        # Quick sensitivity check
        text_lower = text.lower()
        for keyword in ['confidential', 'restricted', 'classified', 'proprietary']:
            if keyword in text_lower:
                return False, f"Contains sensitive keyword: {keyword}"
        
        return True, "No obvious PII or sensitive content detected"

# Global instance
privacy_processor = PrivacySafeProcessor()

def ensure_privacy_safe_content(text: str, aggressive_redaction: bool = True) -> RedactionResult:
    """
    Convenience function to ensure content is privacy-safe
    
    Args:
        text: Original text content
        aggressive_redaction: Whether to use aggressive PII detection
    
    Returns:
        RedactionResult with safe content for external APIs
    """
    return privacy_processor.redact_pii(text, aggressive_mode=aggressive_redaction)

def create_safe_analysis_prompt(original_text: str, analysis_type: str = "general") -> Tuple[str, RedactionResult]:
    """
    Create a safe prompt for LLM analysis that protects PII
    
    Args:
        original_text: Original document text
        analysis_type: Type of analysis (contract, invoice, policy, etc.)
    
    Returns:
        Tuple of (safe_prompt, redaction_result)
    """
    # Redact PII from original text
    redaction_result = ensure_privacy_safe_content(original_text, aggressive_redaction=True)
    
    if not redaction_result.safe_for_external_api:
        # Create generic analysis prompt for sensitive documents
        safe_prompt = f"""
        Analyze this {analysis_type} document structure and provide general insights.
        
        Document Summary: {privacy_processor.create_safe_summary(original_text)}
        
        Please provide:
        1. General document type assessment
        2. Structural analysis
        3. Common risk patterns for this document type
        4. General recommendations
        
        Note: This document contains sensitive information that has been redacted for privacy.
        """
    else:
        # Use redacted content for analysis
        safe_prompt = f"""
        Analyze this {analysis_type} document for key insights and risks.
        
        Document Content:
        {redaction_result.redacted_text[:3000]}  # Limit content length
        
        Please provide:
        1. Key findings and risks
        2. Important terms and conditions
        3. Recommendations for review
        4. Potential concerns or red flags
        
        Note: Some content has been redacted for privacy protection.
        """
    
    return safe_prompt, redaction_result