"""
LLM Factory - Multi-provider AI service supporting OpenAI, Anthropic, Gemini, and Groq
Provides unified interface with automatic fallback, load balancing, and cost optimization
"""
import json
import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from enum import Enum
import random

# Multi-provider imports
import openai
import anthropic
import google.generativeai as genai
from groq import Groq

from app.core.config import settings
from app.models import LlmCall
from app.database import get_operational_db

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    GROQ = "groq"

class LLMTask(Enum):
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    ANALYSIS = "analysis"
    SUMMARIZATION = "summarization"
    CLASSIFICATION = "classification"

class LLMFactory:
    """
    Unified LLM interface supporting multiple providers with intelligent routing
    """
    
    def __init__(self):
        self.providers = {}
        self.provider_configs = {}
        self.provider_status = {}
        self.usage_stats = {}
        
        # Initialize providers
        self._initialize_providers()
        
        # Model mappings for each provider
        self.model_mappings = {
            LLMProvider.OPENAI: {
                "completion": ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"],
                "embedding": ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"],
                "analysis": ["gpt-4", "gpt-4-turbo"],
                "summarization": ["gpt-3.5-turbo", "gpt-4"],
                "classification": ["gpt-3.5-turbo", "gpt-4"]
            },
            LLMProvider.ANTHROPIC: {
                "completion": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
                "analysis": ["claude-3-opus-20240229", "claude-3-sonnet-20240229"],
                "summarization": ["claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
                "classification": ["claude-3-haiku-20240307"]
            },
            LLMProvider.GEMINI: {
                "completion": ["gemini-pro", "gemini-pro-vision"],
                "analysis": ["gemini-pro"],
                "summarization": ["gemini-pro"],
                "classification": ["gemini-pro"]
            },
            LLMProvider.GROQ: {
                "completion": ["mixtral-8x7b-32768", "llama2-70b-4096"],
                "analysis": ["mixtral-8x7b-32768"],
                "summarization": ["llama2-70b-4096"],
                "classification": ["mixtral-8x7b-32768"]
            }
        }
        
        # Cost per 1K tokens (approximate)
        self.cost_per_1k_tokens = {
            LLMProvider.OPENAI: {"gpt-4": 0.03, "gpt-3.5-turbo": 0.002, "text-embedding-3-small": 0.00002},
            LLMProvider.ANTHROPIC: {"claude-3-opus-20240229": 0.015, "claude-3-sonnet-20240229": 0.003, "claude-3-haiku-20240307": 0.00025},
            LLMProvider.GEMINI: {"gemini-pro": 0.001},
            LLMProvider.GROQ: {"mixtral-8x7b-32768": 0.0006, "llama2-70b-4096": 0.0008}
        }
    
    def _initialize_providers(self):
        """Initialize all available LLM providers"""
        
        # OpenAI
        if settings.openai_api_key:
            try:
                self.providers[LLMProvider.OPENAI] = openai.AsyncOpenAI(api_key=settings.openai_api_key)
                self.provider_status[LLMProvider.OPENAI] = True
                logger.info("✅ OpenAI provider initialized")
            except Exception as e:
                logger.warning(f"❌ OpenAI initialization failed: {e}")
                self.provider_status[LLMProvider.OPENAI] = False
        
        # Anthropic
        if settings.anthropic_api_key:
            try:
                self.providers[LLMProvider.ANTHROPIC] = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
                self.provider_status[LLMProvider.ANTHROPIC] = True
                logger.info("✅ Anthropic provider initialized")
            except Exception as e:
                logger.warning(f"❌ Anthropic initialization failed: {e}")
                self.provider_status[LLMProvider.ANTHROPIC] = False
        
        # Google Gemini
        if settings.gemini_api_key:
            try:
                genai.configure(api_key=settings.gemini_api_key)
                self.providers[LLMProvider.GEMINI] = genai
                self.provider_status[LLMProvider.GEMINI] = True
                logger.info("✅ Gemini provider initialized")
            except Exception as e:
                logger.warning(f"❌ Gemini initialization failed: {e}")
                self.provider_status[LLMProvider.GEMINI] = False
        
        # Groq
        if settings.groq_api_key:
            try:
                self.providers[LLMProvider.GROQ] = Groq(api_key=settings.groq_api_key)
                self.provider_status[LLMProvider.GROQ] = True
                logger.info("✅ Groq provider initialized")
            except Exception as e:
                logger.warning(f"❌ Groq initialization failed: {e}")
                self.provider_status[LLMProvider.GROQ] = False
        

        
        # Initialize usage stats
        for provider in LLMProvider:
            self.usage_stats[provider] = {
                "total_calls": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "avg_latency": 0.0,
                "success_rate": 1.0,
                "last_call": None
            }
    
    async def generate_completion(
        self,
        prompt: str,
        task_type: LLMTask = LLMTask.COMPLETION,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        contract_id: Optional[str] = None,
        preferred_provider: Optional[LLMProvider] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate text completion using the best available provider
        """
        start_time = time.time()
        
        # Select provider
        provider = await self._select_provider(task_type, preferred_provider)
        if not provider:
            raise Exception("No available LLM providers")
        
        # Select model
        model = await self._select_model(provider, task_type)
        
        try:
            # Generate completion based on provider
            if provider == LLMProvider.OPENAI:
                result = await self._openai_completion(prompt, model, max_tokens, temperature, **kwargs)
            elif provider == LLMProvider.ANTHROPIC:
                result = await self._anthropic_completion(prompt, model, max_tokens, temperature, **kwargs)
            elif provider == LLMProvider.GEMINI:
                result = await self._gemini_completion(prompt, model, max_tokens, temperature, **kwargs)
            elif provider == LLMProvider.GROQ:
                result = await self._groq_completion(prompt, model, max_tokens, temperature, **kwargs)
            else:
                raise Exception(f"Unsupported provider: {provider}")
            
            # Calculate metrics
            latency = int((time.time() - start_time) * 1000)
            
            # Log the call
            await self._log_llm_call(
                provider=provider,
                model=model,
                call_type=task_type.value,
                input_tokens=result.get("input_tokens", 0),
                output_tokens=result.get("output_tokens", 0),
                latency_ms=latency,
                success=True,
                contract_id=contract_id,
                purpose=task_type.value
            )
            
            # Update usage stats
            self._update_usage_stats(provider, result.get("total_tokens", 0), latency, True)
            
            return {
                "content": result["content"],
                "provider": provider.value,
                "model": model,
                "tokens": result.get("total_tokens", 0),
                "latency_ms": latency,
                "cost": result.get("cost", 0.0)
            }
            
        except Exception as e:
            logger.error(f"LLM completion failed with {provider.value}: {e}")
            
            # Log failed call
            await self._log_llm_call(
                provider=provider,
                model=model,
                call_type=task_type.value,
                latency_ms=int((time.time() - start_time) * 1000),
                success=False,
                error_message=str(e),
                contract_id=contract_id,
                purpose=task_type.value
            )
            
            # Update usage stats
            self._update_usage_stats(provider, 0, int((time.time() - start_time) * 1000), False)
            
            # Try fallback if enabled
            if settings.llm_fallback_enabled and preferred_provider != provider:
                logger.info(f"Attempting fallback for {provider.value}")
                return await self.generate_completion(
                    prompt, task_type, max_tokens, temperature, contract_id, 
                    preferred_provider=None, **kwargs
                )
            
            raise
    
    async def generate_embedding(
        self,
        text: str,
        contract_id: Optional[str] = None,
        preferred_provider: Optional[LLMProvider] = None
    ) -> Dict[str, Any]:
        """
        Generate text embedding using the best available provider
        """
        start_time = time.time()
        
        # Select provider (prefer OpenAI for embeddings)
        provider = preferred_provider or LLMProvider.OPENAI
        if not self.provider_status.get(provider, False):
            # Fallback to any available provider with embedding support
            for p in [LLMProvider.OPENAI]:  # Only OpenAI supports embeddings currently
                if self.provider_status.get(p, False):
                    provider = p
                    break
        
        if not self.provider_status.get(provider, False):
            raise Exception("No embedding providers available")
        
        try:
            if provider == LLMProvider.OPENAI:
                result = await self._openai_embedding(text)
            else:
                raise Exception(f"Embedding not supported for {provider.value}")
            
            # Calculate metrics
            latency = int((time.time() - start_time) * 1000)
            
            # Log the call
            await self._log_llm_call(
                provider=provider,
                model=result["model"],
                call_type="embedding",
                input_tokens=result.get("input_tokens", 0),
                latency_ms=latency,
                success=True,
                contract_id=contract_id,
                purpose="embedding_generation"
            )
            
            return {
                "embedding": result["embedding"],
                "provider": provider.value,
                "model": result["model"],
                "dimensions": len(result["embedding"]),
                "latency_ms": latency
            }
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            await self._log_llm_call(
                provider=provider,
                model="unknown",
                call_type="embedding",
                latency_ms=int((time.time() - start_time) * 1000),
                success=False,
                error_message=str(e),
                contract_id=contract_id,
                purpose="embedding_generation"
            )
            raise
    
    async def _select_provider(self, task_type: LLMTask, preferred: Optional[LLMProvider] = None) -> Optional[LLMProvider]:
        """Intelligently select the best provider for the task"""
        
        # Use preferred provider if available
        if preferred and self.provider_status.get(preferred, False):
            return preferred
        
        # Use default provider if available
        default_provider = LLMProvider(settings.default_llm_provider)
        if self.provider_status.get(default_provider, False):
            return default_provider
        
        # Load balancing: select provider with lowest recent usage
        if settings.llm_load_balancing:
            available_providers = [p for p in LLMProvider if self.provider_status.get(p, False)]
            if available_providers:
                # Select provider with lowest usage
                return min(available_providers, key=lambda p: self.usage_stats[p]["total_calls"])
        
        # Fallback: select first available provider
        for provider in LLMProvider:
            if self.provider_status.get(provider, False):
                return provider
        
        return None
    
    async def _select_model(self, provider: LLMProvider, task_type: LLMTask) -> str:
        """Select the best model for the provider and task"""
        models = self.model_mappings.get(provider, {}).get(task_type.value, [])
        return models[0] if models else "default"
    
    # Provider-specific implementations
    
    async def _openai_completion(self, prompt: str, model: str, max_tokens: int, temperature: float, **kwargs) -> Dict[str, Any]:
        """OpenAI completion"""
        client = self.providers[LLMProvider.OPENAI]
        
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        total_tokens = response.usage.total_tokens
        
        cost = self.cost_per_1k_tokens[LLMProvider.OPENAI].get(model, 0.002) * (total_tokens / 1000)
        
        return {
            "content": response.choices[0].message.content,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost": cost
        }
    
    async def _anthropic_completion(self, prompt: str, model: str, max_tokens: int, temperature: float, **kwargs) -> Dict[str, Any]:
        """Anthropic completion"""
        client = self.providers[LLMProvider.ANTHROPIC]
        
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        total_tokens = input_tokens + output_tokens
        
        cost = self.cost_per_1k_tokens[LLMProvider.ANTHROPIC].get(model, 0.003) * (total_tokens / 1000)
        
        return {
            "content": response.content[0].text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost": cost
        }
    
    async def _gemini_completion(self, prompt: str, model: str, max_tokens: int, temperature: float, **kwargs) -> Dict[str, Any]:
        """Google Gemini completion"""
        genai_client = self.providers[LLMProvider.GEMINI]
        
        model_instance = genai_client.GenerativeModel(model)
        response = await asyncio.to_thread(
            model_instance.generate_content,
            prompt,
            generation_config=genai_client.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature
            )
        )
        
        # Estimate tokens (Gemini doesn't provide exact counts)
        estimated_tokens = len(prompt.split()) + len(response.text.split())
        cost = self.cost_per_1k_tokens[LLMProvider.GEMINI].get(model, 0.001) * (estimated_tokens / 1000)
        
        return {
            "content": response.text,
            "input_tokens": len(prompt.split()),
            "output_tokens": len(response.text.split()),
            "total_tokens": estimated_tokens,
            "cost": cost
        }
    
    async def _groq_completion(self, prompt: str, model: str, max_tokens: int, temperature: float, **kwargs) -> Dict[str, Any]:
        """Groq completion"""
        client = self.providers[LLMProvider.GROQ]
        
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        total_tokens = response.usage.total_tokens
        
        cost = self.cost_per_1k_tokens[LLMProvider.GROQ].get(model, 0.0006) * (total_tokens / 1000)
        
        return {
            "content": response.choices[0].message.content,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost": cost
        }
    

    
    async def _openai_embedding(self, text: str) -> Dict[str, Any]:
        """OpenAI embedding generation"""
        client = self.providers[LLMProvider.OPENAI]
        
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=text[:8000]  # Limit text length
        )
        
        return {
            "embedding": response.data[0].embedding,
            "model": "text-embedding-3-small",
            "input_tokens": len(text.split())
        }
    
    async def _log_llm_call(
        self,
        provider: LLMProvider,
        model: str,
        call_type: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: int = 0,
        success: bool = True,
        error_message: Optional[str] = None,
        contract_id: Optional[str] = None,
        purpose: Optional[str] = None
    ):
        """Log LLM call to database"""
        try:
            async for db in get_operational_db():
                total_tokens = input_tokens + output_tokens
                estimated_cost = self.cost_per_1k_tokens.get(provider, {}).get(model, 0.001) * (total_tokens / 1000)
                
                llm_call = LlmCall(
                    contract_id=contract_id,
                    provider=provider.value,
                    model=model,
                    call_type=call_type,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    estimated_cost=estimated_cost,
                    latency_ms=latency_ms,
                    success=success,
                    error_message=error_message,
                    purpose=purpose
                )
                
                db.add(llm_call)
                await db.commit()
                break
                
        except Exception as e:
            logger.error(f"Failed to log LLM call: {e}")
    
    def _update_usage_stats(self, provider: LLMProvider, tokens: int, latency: int, success: bool):
        """Update provider usage statistics"""
        stats = self.usage_stats[provider]
        
        stats["total_calls"] += 1
        stats["total_tokens"] += tokens
        
        # Update average latency
        if stats["total_calls"] > 1:
            stats["avg_latency"] = (stats["avg_latency"] * (stats["total_calls"] - 1) + latency) / stats["total_calls"]
        else:
            stats["avg_latency"] = latency
        
        # Update success rate
        if success:
            stats["success_rate"] = (stats["success_rate"] * (stats["total_calls"] - 1) + 1.0) / stats["total_calls"]
        else:
            stats["success_rate"] = (stats["success_rate"] * (stats["total_calls"] - 1) + 0.0) / stats["total_calls"]
        
        stats["last_call"] = datetime.utcnow()
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers"""
        return {
            "providers": {
                provider.value: {
                    "available": self.provider_status.get(provider, False),
                    "usage": self.usage_stats.get(provider, {}),
                    "models": list(self.model_mappings.get(provider, {}).keys())
                }
                for provider in LLMProvider
            },
            "settings": {
                "default_provider": settings.default_llm_provider,
                "fallback_enabled": settings.llm_fallback_enabled,
                "load_balancing": settings.llm_load_balancing
            }
        }

# Global LLM Factory instance
llm_factory = LLMFactory()
