"""
Profile management router for DocuShield API
"""
from fastapi import APIRouter, HTTPException, status, Depends, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import io

from app.database import get_operational_db
from app.models import User
from app.core.auth import get_password_hash, verify_password
from app.core.dependencies import get_current_active_user
from app.schemas.requests import UpdateProfileRequest, ChangePasswordRequest, GenerateProfilePhotoRequest
from app.schemas.responses import UserResponse, ProfilePhotoResponse
from app.services.privacy_safe_llm import privacy_safe_llm

router = APIRouter(prefix="/api/profile", tags=["profile"])

@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_active_user)):
    """Get current user profile information"""
    return UserResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        name=current_user.name,
        is_active=current_user.is_active,
        profile_photo_url=current_user.profile_photo_url,
        profile_photo_prompt=current_user.profile_photo_prompt,
        created_at=str(current_user.created_at)
    )

@router.put("/update", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Update user profile information"""
    try:
        # Update only provided fields
        if request.name is not None:
            current_user.name = request.name
        if request.profile_photo_url is not None:
            current_user.profile_photo_url = request.profile_photo_url
        if request.profile_photo_prompt is not None:
            current_user.profile_photo_prompt = request.profile_photo_prompt
        
        await db.commit()
        await db.refresh(current_user)
        
        return UserResponse(
            user_id=current_user.user_id,
            email=current_user.email,
            name=current_user.name,
            is_active=current_user.is_active,
            profile_photo_url=current_user.profile_photo_url,
            profile_photo_prompt=current_user.profile_photo_prompt,
            created_at=str(current_user.created_at)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile update failed: {str(e)}")

@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Change user password"""
    try:
        # Verify current password
        if not verify_password(request.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Validate new password
        if len(request.new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 8 characters long"
            )
        
        # Update password
        current_user.password_hash = get_password_hash(request.new_password)
        await db.commit()
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Password change failed: {str(e)}")

@router.post("/generate-photo", response_model=ProfilePhotoResponse)
async def generate_profile_photo(
    request: GenerateProfilePhotoRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Generate a profile photo using AI image generation"""
    try:
        # Enhance the prompt for better profile photos
        enhanced_prompt = f"Professional headshot portrait of a person, {request.prompt}, high quality, studio lighting, clean background, professional appearance"
        
        # Generate image using LLM Factory (Try Gemini first, fallback to OpenAI)
        from app.services.llm_factory import LLMProvider
        
        print(f"🎯 Profile photo generation request:")
        print(f"   Prompt: {request.prompt}")
        print(f"   Size: {request.size}")
        print(f"   Quality: {request.quality}")
        print(f"   Style: {request.style}")
        
        result = await privacy_safe_llm.safe_generate_image(
            prompt=enhanced_prompt,
            size=request.size,
            quality=request.quality,
            style=request.style,
            contract_id=None,  # Not associated with a contract
            preferred_provider=LLMProvider.GEMINI  # Use ONLY Gemini for image generation
        )
        
        print(f"📊 Generation result: {result.get('success')} - Provider: {result.get('provider')} - Error: {result.get('error')}")
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Image generation failed")
            )
        
        # Store image data in database instead of URL
        if result.get("image_data"):
            current_user.profile_photo_data = result["image_data"]
            current_user.profile_photo_mime_type = result.get("mime_type", "image/png")
            current_user.profile_photo_url = f"/api/profile/photo/{current_user.user_id}"  # Internal URL
        else:
            # Fallback to URL if no image data (shouldn't happen with new implementation)
            current_user.profile_photo_url = result.get("image_url")
            
        current_user.profile_photo_prompt = request.prompt
        await db.commit()
        
        return ProfilePhotoResponse(
            success=True,
            image_url=current_user.profile_photo_url,  # Use our internal URL
            prompt=request.prompt,
            model=result["model"],
            provider=result["provider"],
            estimated_cost=result["estimated_cost"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Profile photo generation error: {error_details}")
        raise HTTPException(status_code=500, detail=f"Profile photo generation failed: {str(e)}")

@router.delete("/photo")
async def remove_profile_photo(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Remove current profile photo"""
    try:
        current_user.profile_photo_url = None
        current_user.profile_photo_data = None
        current_user.profile_photo_mime_type = None
        current_user.profile_photo_prompt = None
        await db.commit()
        
        return {"message": "Profile photo removed successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Photo removal failed: {str(e)}")

@router.get("/photo/{user_id}")
async def get_profile_photo(
    user_id: str,
    db: AsyncSession = Depends(get_operational_db)
):
    """Serve profile photo from database"""
    try:
        # Get user and their profile photo data
        result = await db.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.profile_photo_data:
            raise HTTPException(status_code=404, detail="Profile photo not found")
        
        # Return image as streaming response
        return StreamingResponse(
            io.BytesIO(user.profile_photo_data),
            media_type=user.profile_photo_mime_type or "image/png"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to serve image: {str(e)}")
