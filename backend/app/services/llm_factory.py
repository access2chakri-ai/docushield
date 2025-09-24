"""
LLM Factory - Multi-provider AI service supporting OpenAI, Anthropic, Gemini, Groq, and Amazon Bedrock
Provides unified interface with automatic fallback, load balancing, and cost optimization
Default provider is Amazon Bedrock with Nova Lite model
"""
import json
import logging
import asyncio
import time
import base64
import httpx
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from enum import Enum
import random
from io import BytesIO
import os

# Load environment variables from .env file FIRST
try:
    from dotenv import load_dotenv
    # Load .env file from the backend directory
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    load_dotenv(env_path)
    print(f"✅ LLM Factory: Loaded .env file from: {env_path}")
except ImportError:
    print("⚠️ LLM Factory: python-dotenv not installed. Install with: pip install python-dotenv")
except Exception as e:
    print(f"⚠️ LLM Factory: Could not load .env file: {e}")

# Multi-provider imports
import openai
import anthropic
from google import genai
from google.genai import types
from groq import Groq
import boto3

from app.core.config import settings
from app.models import LlmCall
from app.database import get_operational_db

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    GROQ = "groq"
    BEDROCK = "bedrock"

class LLMTask(Enum):
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    IMAGE_GENERATION = "image_generation"
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
                "image_generation": ["dall-e-3", "dall-e-2"],
                "analysis": ["gpt-4", "gpt-4-turbo"],
                "summarization": ["gpt-3.5-turbo", "gpt-4"],
                "classification": ["gpt-3.5-turbo", "gpt-4"]
            },
            LLMProvider.ANTHROPIC: {
                "completion": ["claude-opus-4-20250514", "claude-sonnet-4-20250514", "claude-3-5-haiku-20241022"],
                "analysis": ["claude-opus-4-20250514", "claude-sonnet-4-20250514"],
                "summarization": ["claude-sonnet-4-20250514", "claude-3-5-haiku-20241022"],
                "classification": ["claude-3-5-haiku-20241022"]
            },
            LLMProvider.GEMINI: {
                "completion": ["gemini-pro", "gemini-pro-vision"],
                "image_generation": ["gemini-2.5-flash-image-preview"],
                "analysis": ["gemini-pro"],
                "summarization": ["gemini-pro"],
                "classification": ["gemini-pro"]
            },
            LLMProvider.GROQ: {
                "completion": ["mixtral-8x7b-32768", "llama2-70b-4096"],
                "analysis": ["mixtral-8x7b-32768"],
                "summarization": ["llama2-70b-4096"],
                "classification": ["mixtral-8x7b-32768"]
            },
            LLMProvider.BEDROCK: {
                "completion": ["amazon.nova-lite-v1:0", "amazon.nova-micro-v1:0"],
                "analysis": ["amazon.nova-lite-v1:0"],
                "summarization": ["amazon.nova-lite-v1:0"],
                "classification": ["amazon.nova-lite-v1:0"],
                "embedding": ["amazon.titan-embed-text-v2:0"]
            }
        }
        
        # Cost per 1K tokens (approximate)
        self.cost_per_1k_tokens = {
            LLMProvider.OPENAI: {"gpt-4": 0.03, "gpt-3.5-turbo": 0.002, "text-embedding-3-small": 0.00002},
            LLMProvider.ANTHROPIC: {"claude-opus-4-20250514": 0.015, "claude-sonnet-4-20250514": 0.003, "claude-3-5-haiku-20241022": 0.00025},
            LLMProvider.GEMINI: {"gemini-pro": 0.001},
            LLMProvider.GROQ: {"mixtral-8x7b-32768": 0.0006, "llama2-70b-4096": 0.0008},
            LLMProvider.BEDROCK: {"amazon.nova-lite-v1:0": 0.0006, "amazon.nova-micro-v1:0": 0.00035, "amazon.titan-embed-text-v2:0": 0.0001}
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
        
        # Amazon Bedrock
        try:
            logger.info("🔧 Initializing Amazon Bedrock...")
            
            # Check if AWS credentials are available (via env vars, IAM role, or config file)
            # AWS credentials can be set via:
            # 1. Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN
            # 2. AWS credentials file (~/.aws/credentials)
            # 3. IAM role (if running on EC2)
            # 4. AWS SSO
            
            # Create Bedrock Runtime client - boto3 will automatically find credentials
            self.providers[LLMProvider.BEDROCK] = boto3.client(
                service_name="bedrock-runtime",
                region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")  # Use configured region or default
            )
            
            # Test the connection by creating a separate bedrock client for model listing
            try:
                # Use bedrock (not bedrock-runtime) client for listing models
                bedrock_client = boto3.client(
                    service_name="bedrock",
                    region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
                )
                response = bedrock_client.list_foundation_models()
                self.provider_status[LLMProvider.BEDROCK] = True
                logger.info("✅ Amazon Bedrock provider initialized successfully")
            except Exception as test_e:
                logger.warning(f"⚠️ Amazon Bedrock credentials test failed: {test_e}")
                self.provider_status[LLMProvider.BEDROCK] = False
                
        except Exception as e:
            logger.error(f"❌ Amazon Bedrock initialization failed: {e}")
            import traceback
            logger.error(f"Full error trace: {traceback.format_exc()}")
            self.provider_status[LLMProvider.BEDROCK] = False

        
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
        
        # Select provider (prefer Bedrock for completions, OpenAI for embeddings)
        if preferred_provider:
            provider = preferred_provider
        elif task_type == LLMTask.EMBEDDING:
            provider = LLMProvider.BEDROCK  # Use Bedrock Titan for embeddings
        else:
            provider = LLMProvider.BEDROCK  # Use Bedrock for everything else
            
        # Validate provider is available
        if not self.provider_status.get(provider, False):
            # Fallback to any available provider
            provider = await self._select_provider(task_type, None)
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
            elif provider == LLMProvider.BEDROCK:
                result = await self._bedrock_completion(prompt, model, max_tokens, temperature, **kwargs)
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
            latency = int((time.time() - start_time) * 1000)
            logger.error(f"LLM completion failed with {provider.value}: {str(e)}")
            
            # Log failed call
            await self._log_llm_call(
                provider=provider,
                model=model,
                call_type=task_type.value,
                latency_ms=latency,
                success=False,
                error_message=str(e),
                contract_id=contract_id,
                purpose=task_type.value
            )
            
            # Update usage stats
            self._update_usage_stats(provider, 0, latency, False)
            
            # Try fallback if enabled
            if hasattr(settings, 'llm_fallback_enabled') and settings.llm_fallback_enabled and preferred_provider != provider:
                logger.info(f"Attempting fallback for {provider.value}")
                return await self.generate_completion(
                    prompt, task_type, max_tokens, temperature, contract_id, 
                    preferred_provider=None, **kwargs
                )
            
            raise e
            
    async def generate_image(
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
        Generate image using DALL-E or other image generation models
        """
        start_time = time.time()
        
        # Use preferred provider or default to Gemini
        provider = preferred_provider or LLMProvider.GEMINI
        
        # Use only Gemini for image generation
        available_providers = [LLMProvider.GEMINI]
        if provider not in available_providers:
            provider = LLMProvider.GEMINI
            logger.warning(f"Image generation not supported for {preferred_provider.value if preferred_provider else 'None'}, using Gemini")
        
        # Check if selected provider is available
        provider_available = False
        if provider in self.provider_status:
            status = self.provider_status[provider]
            # Handle both dict and bool formats
            if isinstance(status, dict):
                provider_available = status.get("available", False)
            else:
                provider_available = bool(status)
        
        if not provider_available:
            # Force Gemini to be available for image generation
            logger.info("Forcing Gemini provider for image generation")
            provider = LLMProvider.GEMINI
        
        # Select model
        model = await self._select_model(provider, LLMTask.IMAGE_GENERATION)
        
        try:
            # Generate image using ONLY Gemini
            if provider != LLMProvider.GEMINI:
                raise Exception(f"Only Gemini image generation is supported, got: {provider.value}")
                
            result = await self._gemini_image_generation(prompt, model, size, quality, style)
            
            if not result.get("success"):
                logger.error(f"Gemini image generation failed: {result.get('error')}")
                raise Exception(f"Gemini image generation failed: {result.get('error')}")
            
            # Calculate metrics
            latency = int((time.time() - start_time) * 1000)
            result["latency_ms"] = latency
            
            # Log the call
            await self._log_llm_call(
                provider=provider,
                model=model,
                call_type="image_generation",
                estimated_cost=result["estimated_cost"],
                latency_ms=latency,
                success=True,
                purpose="profile_photo_generation",
                contract_id=contract_id
            )
            
            return result
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            latency = int((time.time() - start_time) * 1000)
            logger.error(f"Image generation failed with {provider.value}: {str(e)}")
            print(f"Full image generation error: {error_details}")
            
            # Log failed call
            await self._log_llm_call(
                provider=provider,
                model=model,
                call_type="image_generation",
                latency_ms=latency,
                success=False,
                error_message=str(e),
                purpose="profile_photo_generation",
                contract_id=contract_id
            )
            
            raise e
    
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
        
        # Select provider (prefer Bedrock Titan, fallback to OpenAI for embeddings)
        provider = preferred_provider or LLMProvider.BEDROCK
        if not self.provider_status.get(provider, False):
            # Fallback to any available provider with embedding support
            for p in [LLMProvider.BEDROCK, LLMProvider.OPENAI]:  # Bedrock Titan and OpenAI support embeddings
                if self.provider_status.get(p, False):
                    provider = p
                    break
        
        if not self.provider_status.get(provider, False):
            raise Exception("No embedding providers available")
        
        try:
            if provider == LLMProvider.OPENAI:
                result = await self._openai_embedding(text)
            elif provider == LLMProvider.BEDROCK:
                result = await self._bedrock_embedding(text)
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
    
    async def _bedrock_completion(self, prompt: str, model: str, max_tokens: int, temperature: float, **kwargs) -> Dict[str, Any]:
        """Amazon Bedrock completion using Converse API"""
        client = self.providers[LLMProvider.BEDROCK]
        
        response = await asyncio.to_thread(
            client.converse,
            modelId=model,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={
                "maxTokens": max_tokens,
                "temperature": temperature
            }
        )
        
        # Extract token usage
        usage = response.get('usage', {})
        input_tokens = usage.get('inputTokens', 0)
        output_tokens = usage.get('outputTokens', 0)
        total_tokens = input_tokens + output_tokens
        
        # Calculate cost
        cost = self.cost_per_1k_tokens[LLMProvider.BEDROCK].get(model, 0.0006) * (total_tokens / 1000)
        
        # Extract content
        content = ""
        if response.get('output', {}).get('message', {}).get('content'):
            for content_block in response['output']['message']['content']:
                if content_block.get('text'):
                    content += content_block['text']
        
        return {
            "content": content,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost": cost
        }
    
    async def _bedrock_embedding(self, text: str) -> Dict[str, Any]:
        """Amazon Bedrock embedding generation using Titan Embeddings V2"""
        client = self.providers[LLMProvider.BEDROCK]
        model = "amazon.titan-embed-text-v2:0"
        
        response = await asyncio.to_thread(
            client.invoke_model,
            modelId=model,
            body=json.dumps({
                "inputText": text[:8000]  # Limit text length
            })
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        embedding = response_body.get('embedding', [])
        
        return {
            "embedding": embedding,
            "model": model,
            "input_tokens": len(text.split())
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

    async def _openai_image_generation(self, prompt: str, model: str, size: str, quality: str, style: str) -> Dict[str, Any]:
        """Generate image using OpenAI DALL-E"""
        client = self.providers[LLMProvider.OPENAI]
        
        response = await client.images.generate(
            model=model,
            prompt=prompt,
            size=size,
            quality=quality,
            style=style,
            n=1
        )
        
        # Extract image URL and download image data
        image_url = response.data[0].url if response.data else None
        image_data = None
        mime_type = "image/png"
        
        if image_url:
            # Download the image data
            async with httpx.AsyncClient() as http_client:
                img_response = await http_client.get(image_url)
                if img_response.status_code == 200:
                    image_data = img_response.content
                    # Determine MIME type from content-type header
                    content_type = img_response.headers.get("content-type", "image/png")
                    mime_type = content_type
        
        return {
            "success": True,
            "image_url": image_url,
            "image_data": image_data,
            "mime_type": mime_type,
            "prompt": prompt,
            "model": model,
            "provider": "openai",
            "size": size,
            "quality": quality,
            "style": style,
            "estimated_cost": 0.04 if model == "dall-e-3" else 0.02
        }

    async def _gemini_image_generation(self, prompt: str, model: str, size: str = "1024x1024", quality: str = "standard", style: str = "vivid") -> Dict[str, Any]:
        """Generate image using Gemini 2.5 Flash Image Preview with Vertex AI"""
        try:
            # Check for GOOGLE_CLOUD_API_KEY for Vertex AI
            api_key = None
            if hasattr(settings, 'google_cloud_api_key') and settings.google_cloud_api_key:
                api_key = settings.google_cloud_api_key
                print("✅ Using GOOGLE_CLOUD_API_KEY...")
            elif hasattr(settings, 'google_api_key') and settings.google_api_key:
                api_key = settings.google_api_key
                print("✅ Using GOOGLE_API_KEY...")
            elif hasattr(settings, 'gemini_api_key') and settings.gemini_api_key:
                api_key = settings.gemini_api_key
                print("✅ Using GEMINI_API_KEY...")
            
            if not api_key:
                print("❌ Google Cloud API key not configured - image generation will fail")
                raise Exception("Google Cloud API key is required for image generation. Please set GOOGLE_CLOUD_API_KEY environment variable.")
            
            # Create Gemini client for global endpoint (required for preview models)
            print(f"🌍 Using Gemini with global endpoint for preview model: {model}")
            
            # For preview models, use the standard genai.Client without vertex AI
            # The global endpoint is used automatically for preview models
            client = genai.Client(api_key=api_key)
            
            # Enhance prompt for professional profile photo with style preferences
            style_descriptor = "vibrant and dynamic" if style == "vivid" else "natural and realistic"
            quality_descriptor = "ultra high resolution" if quality == "hd" else "high quality"
            
            enhanced_prompt = f"Create a professional headshot portrait photo: {prompt}. {quality_descriptor}, studio lighting, clean background, professional appearance, realistic human face, corporate style, {style_descriptor} appearance."
            
            logger.info(f"Generating image with Gemini: {enhanced_prompt}")
            print(f"🎨 Gemini generation - Size: {size}, Quality: {quality}, Style: {style}")
            
            # Create content with proper structure for image generation
            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part(text=enhanced_prompt)]
                )
            ]

            # Configure generation settings
            generate_content_config = types.GenerateContentConfig(
                temperature=1,
                top_p=0.95,
                max_output_tokens=32768,
                response_modalities=["TEXT", "IMAGE"],
                safety_settings=[
                    types.SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH",
                        threshold="OFF"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_DANGEROUS_CONTENT",
                        threshold="OFF"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        threshold="OFF"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT",
                        threshold="OFF"
                    )
                ],
            )

            # Generate image using Gemini 2.5 Flash Image Preview
            response = client.models.generate_content(
                model=model,  # Should be "gemini-2.5-flash-image-preview"
                contents=contents,
                config=generate_content_config,
            )
            
            # Extract image data from response
            image_data = None
            mime_type = "image/png"
            
            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    # Get the raw image data
                    image_data = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/png"
                    logger.info(f"Successfully generated image with Gemini, size: {len(image_data)} bytes")
                    break
            
            if not image_data:
                return {
                    "success": False,
                    "error": "No image data received from Gemini",
                    "image_data": None,
                    "mime_type": None,
                    "prompt": prompt,
                    "model": model,
                    "provider": "gemini",
                    "estimated_cost": 0.01
                }
            
            return {
                "success": True,
                "image_url": None,  # No URL, we have the data directly
                "image_data": image_data,
                "mime_type": mime_type,
                "prompt": prompt,
                "model": model,
                "provider": "gemini",
                "size": size,
                "quality": quality,
                "style": style,
                "estimated_cost": 0.01  # Estimated cost for Gemini image generation
            }
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Gemini image generation failed: {str(e)}")
            print(f"Gemini error details: {error_details}")
            return {
                "success": False,
                "error": f"Gemini image generation failed: {str(e)}",
                "image_data": None,
                "mime_type": None,
                "prompt": prompt,
                "model": model,
                "provider": "gemini",
                "estimated_cost": 0.0
            }
    
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
