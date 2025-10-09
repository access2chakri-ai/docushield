"""
Privacy-Safe LLM Service
Wrapper around LLM Factory that ensures all external API calls are privacy-protected
Automatically redacts PII and sensitive content before sending to external providers
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from app.services.llm_factory import LLMFactory, LLMProvider, LLMTask
from app.utils.privacy_safe_processing import (
    privacy_processor, 
    ensure_privacy_safe_content, 
    create_safe_analysis_prompt,
    RedactionResult,
    SensitivityLevel
)
from app.core.config import settings

logger = logging.getLogger(__name__)

class PrivacySafeLLMService:
    """
    Privacy-safe wrapper for LLM services
    Ensures all content is properly redacted before external API calls
    """
    
    def __init__(self):
        self.llm_factory = LLMFactory()
        self.redaction_cache = {}
        
        # Providers that are considered "external" and need privacy protection
        self.external_providers = {
            LLMProvider.OPENAI,
            LLMProvider.ANTHROPIC,
            LLMProvider.GEMINI,
            LLMProvider.GROQ
        }
        
        # Providers that are considered "internal" (like local models or AWS Bedrock in VPC)
        self.internal_providers = {
            LLMProvider.BEDROCK  # Assuming Bedrock is configured in private VPC
        }
    
    async def safe_generate_completion(
        self,
        prompt: str,
        task_type: LLMTask = LLMTask.COMPLETION,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        contract_id: Optional[str] = None,
        preferred_provider: Optional[LLMProvider] = None,
        document_content: Optional[str] = None,
        analysis_type: str = "general",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate completion with automatic privacy protection
        
        Args:
            prompt: Base prompt (may contain PII)
            document_content: Document content to analyze (may contain PII)
            analysis_type: Type of analysis for context
            Other args: Same as LLMFactory.generate_completion
        """
        start_time = datetime.now()
        
        # Determine which provider will be used
        effective_provider = preferred_provider or self._get_default_provider(task_type)
        
        # Check if provider requires privacy protection
        needs_privacy_protection = effective_provider in self.external_providers
        
        if needs_privacy_protection:
            logger.info(f"🔒 Privacy protection required for {effective_provider.value}")
            
            # Process document content if provided
            if document_content:
                safe_prompt, redaction_result = create_safe_analysis_prompt(
                    document_content, analysis_type
                )
                
                # Log privacy protection details
                logger.info(f"🔒 Privacy Protection Applied:")
                logger.info(f"   📊 PII instances redacted: {len(redaction_result.pii_matches)}")
                logger.info(f"   🔐 Sensitivity level: {redaction_result.sensitivity_level.value}")
                logger.info(f"   ✅ Safe for external API: {redaction_result.safe_for_external_api}")
                
                if redaction_result.redaction_summary:
                    logger.info(f"   📋 Redacted PII types: {redaction_result.redaction_summary}")
                
                # Store redaction info for potential restoration
                if contract_id:
                    self.redaction_cache[contract_id] = redaction_result
                
            else:
                # Process standalone prompt
                redaction_result = ensure_privacy_safe_content(prompt)
                safe_prompt = redaction_result.redacted_text
                
                if not redaction_result.safe_for_external_api:
                    logger.warning(f"⚠️ Prompt contains sensitive content, using generic analysis")
                    safe_prompt = self._create_generic_prompt(prompt, task_type)
            
            # Use the safe prompt
            final_prompt = safe_prompt
            
        else:
            logger.info(f"🔓 Using internal provider {effective_provider.value} - no redaction needed")
            # For internal providers, use original content
            final_prompt = document_content if document_content else prompt
            redaction_result = None
        
        try:
            # Call the underlying LLM factory
            result = await self.llm_factory.generate_completion(
                prompt=final_prompt,
                task_type=task_type,
                max_tokens=max_tokens,
                temperature=temperature,
                contract_id=contract_id,
                preferred_provider=effective_provider,
                **kwargs
            )
            
            # Add privacy metadata to result
            result["privacy_protected"] = needs_privacy_protection
            result["redaction_applied"] = redaction_result is not None
            
            if redaction_result:
                result["sensitivity_level"] = redaction_result.sensitivity_level.value
                result["pii_redacted"] = len(redaction_result.pii_matches)
                result["redaction_summary"] = redaction_result.redaction_summary
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"✅ Safe LLM completion completed in {execution_time:.0f}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Safe LLM completion failed: {e}")
            raise
    
    async def safe_generate_embedding(
        self,
        text: str,
        contract_id: Optional[str] = None,
        preferred_provider: Optional[LLMProvider] = None
    ) -> Dict[str, Any]:
        """
        Generate embedding with privacy protection
        """
        # Determine provider
        effective_provider = preferred_provider or self._get_default_provider(LLMTask.EMBEDDING)
        needs_privacy_protection = effective_provider in self.external_providers
        
        if needs_privacy_protection:
            logger.info(f"🔒 Privacy protection for embedding generation")
            
            # For embeddings, we need to be more careful as redaction changes semantic meaning
            # Check if content is safe first
            is_safe, reason = privacy_processor.is_safe_for_external_api(text)
            
            if not is_safe:
                logger.warning(f"⚠️ Text not safe for external embedding: {reason}")
                
                # For unsafe content, create a safe summary for embedding
                safe_text = privacy_processor.create_safe_summary(text, max_length=500)
                logger.info(f"🔒 Using safe summary for embedding: {len(safe_text)} chars")
            else:
                safe_text = text
                logger.info(f"✅ Text is safe for external embedding")
            
            final_text = safe_text
        else:
            logger.info(f"🔓 Using internal provider for embedding - no redaction needed")
            final_text = text
        
        try:
            result = await self.llm_factory.generate_embedding(
                text=final_text,
                contract_id=contract_id,
                preferred_provider=effective_provider
            )
            
            result["privacy_protected"] = needs_privacy_protection
            result["text_modified"] = needs_privacy_protection and final_text != text
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Safe embedding generation failed: {e}")
            raise
    
    async def safe_generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        style: str = "vivid",
        contract_id: Optional[str] = None,
        preferred_provider: Optional[LLMProvider] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate image with privacy protection for prompts
        """
        effective_provider = preferred_provider or LLMProvider.GEMINI
        needs_privacy_protection = effective_provider in self.external_providers
        
        if needs_privacy_protection:
            logger.info(f"🔒 Privacy protection for image generation")
            
            # Redact PII from image prompt
            redaction_result = ensure_privacy_safe_content(prompt)
            
            if not redaction_result.safe_for_external_api:
                logger.warning(f"⚠️ Image prompt contains sensitive content")
                # Create generic prompt
                safe_prompt = "Generate a professional business document illustration"
            else:
                safe_prompt = redaction_result.redacted_text
            
            final_prompt = safe_prompt
        else:
            final_prompt = prompt
        
        try:
            result = await self.llm_factory.generate_image(
                prompt=final_prompt,
                size=size,
                quality=quality,
                style=style,
                contract_id=contract_id,
                preferred_provider=effective_provider,
                **kwargs
            )
            
            result["privacy_protected"] = needs_privacy_protection
            result["prompt_modified"] = needs_privacy_protection and final_prompt != prompt
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Safe image generation failed: {e}")
            raise
    
    def _get_default_provider(self, task_type: LLMTask) -> LLMProvider:
        """Get default provider for task type, preferring internal providers"""
        
        # For embeddings, prefer Bedrock Titan (internal)
        if task_type == LLMTask.EMBEDDING:
            return LLMProvider.BEDROCK
        
        # For other tasks, prefer Bedrock (internal) if available
        if hasattr(settings, 'default_llm_provider'):
            default = LLMProvider(settings.default_llm_provider)
            if default in self.internal_providers:
                return default
        
        # Fallback to Bedrock as internal provider
        return LLMProvider.BEDROCK
    
    def _create_generic_prompt(self, original_prompt: str, task_type: LLMTask) -> str:
        """Create generic prompt for sensitive content"""
        
        if task_type == LLMTask.ANALYSIS:
            return """
            Analyze a business document and provide general insights about:
            1. Document structure and type
            2. Common risk patterns for this document category
            3. General recommendations for review
            4. Best practices for this document type
            
            Note: Specific content has been redacted for privacy protection.
            """
        elif task_type == LLMTask.SUMMARIZATION:
            return """
            Provide a general summary framework for business documents including:
            1. Key sections typically found
            2. Important elements to review
            3. Common terms and conditions
            4. Standard recommendations
            
            Note: Specific content has been redacted for privacy protection.
            """
        else:
            return """
            Provide general business document guidance and best practices.
            Note: Specific content has been redacted for privacy protection.
            """
    
    def get_redaction_info(self, contract_id: str) -> Optional[RedactionResult]:
        """Get redaction information for a contract"""
        return self.redaction_cache.get(contract_id)
    
    def clear_redaction_cache(self, contract_id: Optional[str] = None):
        """Clear redaction cache for specific contract or all"""
        if contract_id:
            self.redaction_cache.pop(contract_id, None)
        else:
            self.redaction_cache.clear()
    
    async def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers with privacy classification"""
        base_status = self.llm_factory.get_provider_status()
        
        # Add privacy classification to each provider
        if "providers" in base_status:
            for provider_name, status in base_status["providers"].items():
                try:
                    provider_enum = LLMProvider(provider_name)
                    status["privacy_classification"] = (
                        "external" if provider_enum in self.external_providers 
                        else "internal"
                    )
                    status["requires_redaction"] = provider_enum in self.external_providers
                except ValueError:
                    status["privacy_classification"] = "unknown"
                    status["requires_redaction"] = True  # Err on the side of caution
        
        return base_status

# Global instance
privacy_safe_llm = PrivacySafeLLMService()

# Convenience functions for backward compatibility
async def safe_llm_completion(
    prompt: str,
    task_type: LLMTask = LLMTask.COMPLETION,
    max_tokens: int = 1000,
    temperature: float = 0.7,
    contract_id: Optional[str] = None,
    document_content: Optional[str] = None,
    analysis_type: str = "general",
    **kwargs
) -> Dict[str, Any]:
    """Convenience function for safe LLM completion"""
    return await privacy_safe_llm.safe_generate_completion(
        prompt=prompt,
        task_type=task_type,
        max_tokens=max_tokens,
        temperature=temperature,
        contract_id=contract_id,
        document_content=document_content,
        analysis_type=analysis_type,
        **kwargs
    )

async def safe_llm_embedding(
    text: str,
    contract_id: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Convenience function for safe embedding generation"""
    return await privacy_safe_llm.safe_generate_embedding(
        text=text,
        contract_id=contract_id,
        **kwargs
    )