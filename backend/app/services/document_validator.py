"""
Document Type Validation Service
Validates documents are relevant to SaaS/business context before processing
"""
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

from app.services.llm_factory import llm_factory, LLMTask

logger = logging.getLogger(__name__)

class DocumentCategory(Enum):
    """Supported document categories for processing"""
    SAAS_CONTRACT = "saas_contract"
    VENDOR_AGREEMENT = "vendor_agreement" 
    INVOICE = "invoice"
    PROCUREMENT = "procurement"
    SERVICE_AGREEMENT = "service_agreement"
    SUBSCRIPTION = "subscription"
    UNSUPPORTED = "unsupported"

class DocumentValidator:
    """
    Validates if documents are relevant for SaaS business processing
    """
    
    def __init__(self):
        # Keywords that indicate SaaS/business relevance
        self.saas_keywords = [
            "software", "saas", "service", "subscription", "license", "agreement",
            "contract", "vendor", "supplier", "procurement", "invoice", "billing",
            "terms of service", "service level", "sla", "api", "cloud", "platform",
            "application", "enterprise", "business", "commercial", "payment",
            "pricing", "fee", "cost", "renewal", "termination", "liability",
            "indemnification", "data processing", "privacy", "security",
            "intellectual property", "confidential", "non-disclosure"
        ]
        
        # Patterns that indicate non-business documents
        self.exclude_patterns = [
            r"personal.*letter", r"family.*photo", r"vacation.*plan",
            r"recipe", r"diary", r"journal", r"homework", r"assignment",
            r"creative.*writing", r"story", r"poem", r"novel",
            r"medical.*record", r"prescription", r"health.*report"
        ]

    async def validate_document(
        self, 
        filename: str, 
        text_content: str, 
        mime_type: str
    ) -> Tuple[bool, DocumentCategory, Dict[str, Any]]:
        """
        Validate if document should be processed
        
        Returns:
            (is_valid, category, validation_details)
        """
        validation_details = {
            "filename_score": 0.0,
            "content_score": 0.0,
            "ai_classification": None,
            "reason": "",
            "confidence": 0.0
        }
        
        try:
            # Step 1: Quick filename-based validation
            filename_score = self._analyze_filename(filename)
            validation_details["filename_score"] = filename_score
            
            # Step 2: Content-based keyword analysis
            content_score = self._analyze_content_keywords(text_content)
            validation_details["content_score"] = content_score
            
            # Step 3: AI-based classification for borderline cases
            combined_score = (filename_score + content_score) / 2
            
            if combined_score < 0.3:
                # Clearly not business-related
                validation_details["reason"] = "Document does not appear to be business/SaaS related"
                validation_details["confidence"] = 1.0 - combined_score
                return False, DocumentCategory.UNSUPPORTED, validation_details
            
            elif combined_score > 0.7:
                # Clearly business-related
                category = self._determine_category(filename, text_content)
                validation_details["reason"] = f"Document classified as {category.value}"
                validation_details["confidence"] = combined_score
                return True, category, validation_details
            
            else:
                # Borderline case - use AI classification
                ai_result = await self._ai_classify_document(filename, text_content[:2000])
                validation_details["ai_classification"] = ai_result
                
                is_valid = ai_result["is_business_relevant"]
                category = DocumentCategory(ai_result["category"]) if is_valid else DocumentCategory.UNSUPPORTED
                validation_details["confidence"] = ai_result["confidence"]
                validation_details["reason"] = ai_result["reasoning"]
                
                return is_valid, category, validation_details
                
        except Exception as e:
            logger.error(f"Document validation failed: {e}")
            # Fail safe - reject document if validation fails
            validation_details["reason"] = f"Validation error: {str(e)}"
            validation_details["confidence"] = 0.0
            return False, DocumentCategory.UNSUPPORTED, validation_details

    def _analyze_filename(self, filename: str) -> float:
        """Analyze filename for business relevance indicators"""
        filename_lower = filename.lower()
        
        # Check for exclude patterns
        for pattern in self.exclude_patterns:
            if re.search(pattern, filename_lower):
                return 0.0
        
        # Count SaaS/business keywords in filename
        keyword_matches = sum(1 for keyword in self.saas_keywords if keyword in filename_lower)
        
        # Specific filename patterns that indicate business documents
        business_patterns = [
            r"contract", r"agreement", r"invoice", r"quote", r"proposal",
            r"terms", r"service", r"vendor", r"supplier", r"procurement",
            r"subscription", r"license", r"sla", r"msa", r"nda"
        ]
        
        pattern_matches = sum(1 for pattern in business_patterns if re.search(pattern, filename_lower))
        
        # Calculate score (0-1)
        total_score = (keyword_matches * 0.3) + (pattern_matches * 0.7)
        return min(1.0, total_score / 3.0)  # Normalize to 0-1

    def _analyze_content_keywords(self, text_content: str) -> float:
        """Analyze text content for business relevance"""
        if not text_content or len(text_content) < 100:
            return 0.0
        
        text_lower = text_content[:3000].lower()  # Analyze first 3000 chars
        
        # Check for exclude patterns
        for pattern in self.exclude_patterns:
            if re.search(pattern, text_lower):
                return 0.0
        
        # Count keyword occurrences
        keyword_score = 0
        for keyword in self.saas_keywords:
            if keyword in text_lower:
                # Weight more important keywords higher
                if keyword in ["contract", "agreement", "service", "license", "invoice"]:
                    keyword_score += 2
                else:
                    keyword_score += 1
        
        # Look for business document structure indicators
        structure_indicators = [
            "whereas", "hereby", "party", "parties", "terms and conditions",
            "liability", "indemnification", "termination", "renewal",
            "payment terms", "invoice number", "due date", "amount due",
            "service level", "scope of work", "deliverables"
        ]
        
        structure_score = sum(2 for indicator in structure_indicators if indicator in text_lower)
        
        total_score = keyword_score + structure_score
        return min(1.0, total_score / 20.0)  # Normalize to 0-1

    def _determine_category(self, filename: str, text_content: str) -> DocumentCategory:
        """Determine specific document category"""
        combined_text = f"{filename} {text_content[:1000]}".lower()
        
        # Category classification based on keywords
        if any(word in combined_text for word in ["invoice", "bill", "payment", "amount due"]):
            return DocumentCategory.INVOICE
        elif any(word in combined_text for word in ["subscription", "recurring", "monthly", "annual"]):
            return DocumentCategory.SUBSCRIPTION
        elif any(word in combined_text for word in ["procurement", "purchase", "vendor", "supplier"]):
            return DocumentCategory.PROCUREMENT
        elif any(word in combined_text for word in ["service agreement", "sla", "service level"]):
            return DocumentCategory.SERVICE_AGREEMENT
        elif any(word in combined_text for word in ["saas", "software", "license", "platform"]):
            return DocumentCategory.SAAS_CONTRACT
        else:
            return DocumentCategory.VENDOR_AGREEMENT

    async def _ai_classify_document(self, filename: str, text_sample: str) -> Dict[str, Any]:
        """Use AI to classify borderline documents"""
        try:
            classification_prompt = f"""
            Analyze this document to determine if it's relevant for SaaS business document processing.
            
            We ONLY process these types of business documents:
            - SaaS contracts and agreements
            - Vendor/supplier agreements
            - Software licenses and subscriptions
            - Invoices and billing documents
            - Procurement documents related to SaaS/software
            - Service agreements and SLAs
            
            We DO NOT process:
            - Personal documents
            - Creative writing
            - Academic papers
            - Medical records
            - General correspondence
            - Non-business content
            
            Filename: {filename}
            Document sample: {text_sample}
            
            Respond with JSON:
            {{
                "is_business_relevant": true/false,
                "category": "saas_contract|vendor_agreement|invoice|procurement|service_agreement|subscription|unsupported",
                "confidence": 0.0-1.0,
                "reasoning": "Brief explanation"
            }}
            """
            
            result = await llm_factory.generate_completion(
                prompt=classification_prompt,
                task_type=LLMTask.CLASSIFICATION,
                max_tokens=200,
                temperature=0.1
            )
            
            import json
            classification = json.loads(result["content"])
            return classification
            
        except Exception as e:
            logger.error(f"AI classification failed: {e}")
            return {
                "is_business_relevant": False,
                "category": "unsupported",
                "confidence": 0.0,
                "reasoning": f"AI classification error: {str(e)}"
            }

# Global validator instance
document_validator = DocumentValidator()
