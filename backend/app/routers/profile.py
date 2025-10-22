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
from app.services.llm_factory import LLMProvider

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

@router.post("/generate-basic-photo", response_model=ProfilePhotoResponse)
async def generate_basic_profile_photo(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Generate a basic professional profile photo using Titan G1"""
    try:
        # Generate a professional profile photo with optimized prompt (under 512 chars)
        import random
        
        # Add some variation to basic photos
        variations = [
            "professional business person, confident smile, modern suit, clean white background, corporate headshot",
            "professional executive, friendly expression, business attire, neutral gray background, office portrait",
            "business professional, approachable demeanor, formal clothing, studio lighting, corporate photo",
            "professional worker, warm smile, contemporary business wear, simple background, headshot portrait"
        ]
        
        basic_prompt = random.choice(variations)
        
        print(f"🎯 Professional profile photo generation for user: {current_user.email}")
        print(f"   Using Titan Image Generator G1 V2 with professional prompt")
        
        # Use Bedrock Titan G1 V2 only
        print(f"🔄 Using AWS Bedrock Titan Image Generator G1 V2...")
        
        try:
            result = await privacy_safe_llm.safe_generate_image(
                prompt=basic_prompt,
                size="512x512",  # Smaller size for faster generation
                quality="standard",
                style="natural",
                contract_id=None,
                preferred_provider=LLMProvider.BEDROCK
            )
            
            print(f"📊 Titan G1 V2 professional photo result: {result.get('success')}")
            
        except Exception as generation_error:
            print(f"❌ Titan G1 basic generation failed: {str(generation_error)}")
            result = {
                "success": False,
                "error": f"Basic profile photo generation failed: {str(generation_error)}"
            }
        
        if not result or not result.get("success"):
            error_msg = result.get("error", "Professional profile photo generation failed") if result else "Titan G1 V2 not available"
            print(f"❌ Professional photo error: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail="Could not generate professional profile photo. Please try the custom photo option or try again later."
            )
        
        # Store image data in database
        if result.get("image_data"):
            current_user.profile_photo_data = result["image_data"]
            current_user.profile_photo_mime_type = result.get("mime_type", "image/png")
            current_user.profile_photo_url = f"/api/profile/photo/{current_user.user_id}"
        else:
            current_user.profile_photo_url = result.get("image_url")
            
        current_user.profile_photo_prompt = "Professional headshot"
        await db.commit()
        
        return ProfilePhotoResponse(
            success=True,
            image_url=current_user.profile_photo_url,
            prompt="Professional headshot",
            model=result["model"],
            provider=result["provider"],
            estimated_cost=result["estimated_cost"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Professional profile photo generation error: {error_details}")
        raise HTTPException(status_code=500, detail=f"Professional profile photo generation failed: {str(e)}")

@router.post("/generate-photo", response_model=ProfilePhotoResponse)
async def generate_profile_photo(
    request: GenerateProfilePhotoRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_operational_db)
):
    """Generate a custom profile photo using AI image generation with Titan G1"""
    try:
        # Validate prompt length (Titan G1 V2 has 512 character limit)
        if len(request.prompt) > 400:  # Leave room for enhancement
            raise HTTPException(
                status_code=400,
                detail="Photo description is too long. Please keep it under 400 characters."
            )
        
        # Generate image using LLM Factory with better error handling
        
        print(f"🎯 Custom profile photo generation request:")
        print(f"   User: {current_user.email}")
        print(f"   User's Description: {request.prompt}")
        print(f"   Size: {request.size}")
        print(f"   Quality: {request.quality}")
        print(f"   Style: {request.style}")
        print(f"   Using Titan Image Generator G1 V2 (same AI infrastructure as document agents)")
        
        # Use only Bedrock Titan G1 for profile photos
        print(f"🔄 Using AWS Bedrock Titan Image Generator G1 V2...")
        
        try:
            result = await privacy_safe_llm.safe_generate_image(
                prompt=request.prompt,  # Use user's original prompt
                size=request.size,
                quality=request.quality,
                style=request.style,
                contract_id=None,  # Not associated with a contract
                preferred_provider=LLMProvider.BEDROCK
            )
            
            print(f"📊 Titan G1 result: {result.get('success')} - Error: {result.get('error')}")
            
        except Exception as generation_error:
            print(f"❌ Titan G1 generation failed: {str(generation_error)}")
            result = {
                "success": False,
                "error": f"Profile photo generation failed: {str(generation_error)}"
            }
        
        if not result or not result.get("success"):
            error_msg = result.get("error", "All image generation providers failed") if result else "No image generation providers available"
            print(f"❌ Final error: {error_msg}")
            
            # Provide helpful error message based on the error type
            if "bedrock" in error_msg.lower():
                detail_msg = "AWS Bedrock image generation failed. Please ensure Bedrock is properly configured with Stability AI or Titan Image models."
            elif "api key" in error_msg.lower():
                detail_msg = "Image generation API keys are not configured. Please contact your administrator."
            else:
                detail_msg = f"Profile photo generation failed: {error_msg}. Please try again with a simpler prompt."
                
            raise HTTPException(
                status_code=500,
                detail=detail_msg
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
