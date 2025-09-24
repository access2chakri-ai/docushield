"""
LLM Factory router for DocuShield API
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from app.core.dependencies import get_current_active_user
from app.schemas.requests import LLMRequest, GenerateProfilePhotoRequest
from app.services.llm_factory import llm_factory, LLMProvider, LLMTask

router = APIRouter(prefix="/api/llm", tags=["llm"])

@router.post("/completion")
async def llm_completion(
    request: LLMRequest,
    current_user = Depends(get_current_active_user)
):
    """Generate completion using LLM Factory"""
    try:
        provider = LLMProvider(request.provider) if request.provider else None
        task_type = LLMTask(request.task_type)
        
        result = await llm_factory.generate_completion(
            prompt=request.prompt,
            task_type=task_type,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            preferred_provider=provider
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM completion failed: {str(e)}")

@router.post("/embedding")
async def llm_embedding(
    text: str, 
    provider: Optional[str] = None,
    current_user = Depends(get_current_active_user)
):
    """Generate embedding using LLM Factory"""
    try:
        provider_enum = LLMProvider(provider) if provider else None
        
        result = await llm_factory.generate_embedding(
            text=text,
            preferred_provider=provider_enum
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")

@router.get("/providers/status")
async def get_provider_status(current_user = Depends(get_current_active_user)):
    """Get status of LLM providers"""
    try:
        status = llm_factory.get_provider_status()
        return {
            "providers": status,
            "user_id": current_user.user_id,
            "timestamp": "2024-01-01T00:00:00Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Provider status check failed: {str(e)}")

@router.get("/usage")
async def get_llm_usage_stats(current_user = Depends(get_current_active_user)):
    """Get LLM usage statistics"""
    try:
        usage_stats = getattr(llm_factory, 'usage_stats', {})
        return {
            "user_id": current_user.user_id,
            "usage_stats": usage_stats,
            "timestamp": "2024-01-01T00:00:00Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Usage stats failed: {str(e)}")

@router.post("/generate-image")
async def generate_image(
    request: GenerateProfilePhotoRequest,
    current_user = Depends(get_current_active_user)
):
    """Generate image using LLM Factory"""
    try:
        result = await llm_factory.generate_image(
            prompt=request.prompt,
            size=request.size,
            quality=request.quality,
            style=request.style,
            preferred_provider=LLMProvider.OPENAI
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")
