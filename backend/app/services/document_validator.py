"""
Document Classification Service
Classifies any document type based on content analysis
"""
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

from app.services.llm_factory import LLMTask
from app.services.privacy_safe_llm import safe_llm_completion

logger = logging.getLogger(__name__)

class DocumentCategory(Enum):
    """All supported document categories for processing"""
    # Business Documents
    CONTRACT = "contract"
    AGREEMENT = "agreement"
    INVOICE = "invoice"
    PROPOSAL = "proposal"
    REPORT = "report"
    POLICY = "policy"
    MANUAL = "manual"
    SPECIFICATION = "specification"
    
    # Legal Documents
    LEGAL_DOCUMENT = "legal_document"
    COMPLIANCE = "compliance"
    REGULATION = "regulation"
    
    # Technical Documents
    TECHNICAL_SPEC = "technical_spec"
    API_DOCUMENTATION = "api_documentation"
    USER_GUIDE = "user_guide"
    
    # Academic/Research
    RESEARCH_PAPER = "research_paper"
    WHITEPAPER = "whitepaper"
    CASE_STUDY = "case_study"
    
    # General Documents
    PRESENTATION = "presentation"
    MEMO = "memo"
    EMAIL = "email"
    LETTER = "letter"
    FORM = "form"
    
    # Catch-all
    GENERAL_DOCUMENT = "general_document"
    UNKNOWN = "unknown"

class DocumentClassifier:
    """
    Classifies any document type based on content analysis
    No restrictions - processes all document types
    """
    
    def __init__(self):
        # Document type indicators
        self.document_indicators = {
            "contract": ["contract", "agreement", "terms", "conditions", "party", "parties", "whereas", "hereby"],
            "invoice": ["invoice", "bill", "payment", "amount due", "total", "tax", "subtotal"],
            "report": ["report", "analysis", "findings", "summary", "conclusion", "executive summary"],
            "manual": ["manual", "guide", "instructions", "how to", "step by step", "procedure"],
            "policy": ["policy", "procedure", "guidelines", "rules", "regulations", "compliance"],
            "specification": ["specification", "requirements", "technical", "design", "architecture"],
            "research_paper": ["abstract", "introduction", "methodology", "results", "discussion", "references"],
            "presentation": ["slide", "presentation", "agenda", "overview", "outline"],
            "legal_document": ["legal", "law", "statute", "regulation", "compliance", "court", "judgment"],
            "email": ["from:", "to:", "subject:", "dear", "regards", "sincerely"],
            "memo": ["memo", "memorandum", "to:", "from:", "date:", "re:"],
            "proposal": ["proposal", "bid", "quote", "estimate", "scope of work", "deliverables"]
        }

    async def classify_document(
        self, 
        filename: str, 
        text_content: str, 
        mime_type: str,
        user_document_type: Optional[str] = None,
        user_industry_type: Optional[str] = None
    ) -> Tuple[bool, DocumentCategory, Dict[str, Any]]:
        """
        Classify any document type - no restrictions
        
        Returns:
            (is_valid, category, classification_details)
        """
        classification_details = {
            "filename_indicators": [],
            "content_indicators": [],
            "ai_classification": None,
            "user_provided_type": user_document_type,
            "user_provided_industry": user_industry_type,
            "confidence": 0.8,
            "reason": "Document accepted for processing"
        }
        
        try:
            # Always accept the document - just classify it
            category = DocumentCategory.GENERAL_DOCUMENT
            
            # Step 1: Use user-provided type if available
            if user_document_type:
                category = self._map_user_type_to_category(user_document_type)
                classification_details["reason"] = f"User specified document type: {user_document_type}"
                classification_details["confidence"] = 0.9
                return True, category, classification_details
            
            # Step 2: Analyze filename for type indicators
            filename_indicators = self._analyze_filename_indicators(filename)
            classification_details["filename_indicators"] = filename_indicators
            
            # Step 3: Analyze content for type indicators
            content_indicators = self._analyze_content_indicators(text_content)
            classification_details["content_indicators"] = content_indicators
            
            # Step 4: Determine category based on indicators
            if filename_indicators or content_indicators:
                category = self._determine_category_from_indicators(filename_indicators + content_indicators)
                classification_details["confidence"] = 0.7
            else:
                # Step 5: Use AI classification for unknown documents
                ai_result = await self._ai_classify_document(filename, text_content[:2000])
                classification_details["ai_classification"] = ai_result
                category = DocumentCategory(ai_result.get("category", "general_document"))
                classification_details["confidence"] = ai_result.get("confidence", 0.6)
                classification_details["reason"] = ai_result.get("reasoning", "AI-based classification")
            
            return True, category, classification_details
                
        except Exception as e:
            logger.error(f"Document classification failed: {e}")
            # Always accept document even if classification fails
            classification_details["reason"] = f"Classification completed with fallback: {str(e)}"
            classification_details["confidence"] = 0.5
            return True, DocumentCategory.GENERAL_DOCUMENT, classification_details

    def _analyze_filename_indicators(self, filename: str) -> List[str]:
        """Analyze filename for document type indicators"""
        filename_lower = filename.lower()
        indicators = []
        
        for doc_type, keywords in self.document_indicators.items():
            for keyword in keywords:
                if keyword in filename_lower:
                    indicators.append(doc_type)
                    break
        
        return indicators

    def _analyze_content_indicators(self, text_content: str) -> List[str]:
        """Analyze text content for document type indicators"""
        if not text_content or len(text_content) < 50:
            return []
        
        text_lower = text_content[:3000].lower()  # Analyze first 3000 chars
        indicators = []
        
        for doc_type, keywords in self.document_indicators.items():
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            if matches >= 2:  # Need at least 2 keyword matches
                indicators.append(doc_type)
        
        return indicators

    def _map_user_type_to_category(self, user_type: str) -> DocumentCategory:
        """Map user-provided document type to internal category"""
        user_type_lower = user_type.lower()
        
        # Direct mappings
        type_mappings = {
            "contract": DocumentCategory.CONTRACT,
            "agreement": DocumentCategory.AGREEMENT,
            "invoice": DocumentCategory.INVOICE,
            "proposal": DocumentCategory.PROPOSAL,
            "report": DocumentCategory.REPORT,
            "policy": DocumentCategory.POLICY,
            "manual": DocumentCategory.MANUAL,
            "specification": DocumentCategory.SPECIFICATION,
            "legal": DocumentCategory.LEGAL_DOCUMENT,
            "research": DocumentCategory.RESEARCH_PAPER,
            "whitepaper": DocumentCategory.WHITEPAPER,
            "presentation": DocumentCategory.PRESENTATION,
            "memo": DocumentCategory.MEMO,
            "email": DocumentCategory.EMAIL,
            "letter": DocumentCategory.LETTER,
            "form": DocumentCategory.FORM
        }
        
        for key, category in type_mappings.items():
            if key in user_type_lower:
                return category
        
        return DocumentCategory.GENERAL_DOCUMENT
    
    def _determine_category_from_indicators(self, indicators: List[str]) -> DocumentCategory:
        """Determine category from detected indicators"""
        if not indicators:
            return DocumentCategory.GENERAL_DOCUMENT
        
        # Count occurrences and pick most common
        indicator_counts = {}
        for indicator in indicators:
            indicator_counts[indicator] = indicator_counts.get(indicator, 0) + 1
        
        most_common = max(indicator_counts.items(), key=lambda x: x[1])[0]
        
        # Map to enum
        category_map = {
            "contract": DocumentCategory.CONTRACT,
            "invoice": DocumentCategory.INVOICE,
            "report": DocumentCategory.REPORT,
            "manual": DocumentCategory.MANUAL,
            "policy": DocumentCategory.POLICY,
            "specification": DocumentCategory.SPECIFICATION,
            "research_paper": DocumentCategory.RESEARCH_PAPER,
            "presentation": DocumentCategory.PRESENTATION,
            "legal_document": DocumentCategory.LEGAL_DOCUMENT,
            "email": DocumentCategory.EMAIL,
            "memo": DocumentCategory.MEMO,
            "proposal": DocumentCategory.PROPOSAL
        }
        
        return category_map.get(most_common, DocumentCategory.GENERAL_DOCUMENT)

    async def _ai_classify_document(self, filename: str, text_sample: str) -> Dict[str, Any]:
        """Use AI to classify any document type"""
        try:
            classification_prompt = f"""
            Analyze this document and classify its type. We accept ALL document types.
            
            Common document types:
            - contract, agreement, invoice, proposal, report
            - policy, manual, specification, legal_document
            - research_paper, whitepaper, case_study
            - presentation, memo, email, letter, form
            - technical_spec, api_documentation, user_guide
            - general_document (for anything else)
            
            Filename: {filename}
            Document sample: {text_sample}
            
            Respond with JSON:
            {{
                "category": "contract|agreement|invoice|proposal|report|policy|manual|specification|legal_document|research_paper|whitepaper|presentation|memo|email|letter|form|technical_spec|api_documentation|user_guide|general_document",
                "confidence": 0.0-1.0,
                "reasoning": "Brief explanation of classification"
            }}
            """
            
            result = await safe_llm_completion(
                prompt=classification_prompt,
                task_type=LLMTask.CLASSIFICATION,
                max_tokens=200,
                temperature=0.1,
                document_content=text_sample,
                analysis_type="document_classification"
            )
            
            import json
            classification = json.loads(result["content"])
            return classification
            
        except Exception as e:
            logger.error(f"AI classification failed: {e}")
            return {
                "category": "general_document",
                "confidence": 0.5,
                "reasoning": f"AI classification error, using fallback: {str(e)}"
            }

# Global classifier instance
document_classifier = DocumentClassifier()
