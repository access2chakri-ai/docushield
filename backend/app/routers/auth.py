"""
Authentication router for DocuShield API
"""
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_operational_db
from app.models import User
from app.core.auth import (
    get_password_hash, 
    verify_password, 
    create_tokens, 
    verify_token
)
from app.core.dependencies import get_current_active_user
from app.schemas.requests import UserRegistrationRequest, UserLoginRequest, RefreshTokenRequest
from app.schemas.responses import Token, UserResponse

router = APIRouter(prefix="/api/auth", tags=["authentication"])

@router.post("/register", response_model=Token)
async def register_user(request: UserRegistrationRequest, db: AsyncSession = Depends(get_operational_db)):
    """Register a new user with JWT token response"""
    try:
        # Check if user already exists
        result = await db.execute(
            select(User).where(User.email == request.email)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(status_code=400, detail="User with this email already exists")
        
        # Create new user with hashed password
        hashed_password = get_password_hash(request.password)
        user = User(
            email=request.email,
            name=request.name,
            password_hash=hashed_password
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Create JWT tokens
        user_data = {
            "user_id": user.user_id,
            "email": user.email,
            "name": user.name,
            "is_active": user.is_active
        }
        tokens = create_tokens(user_data)
        
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post("/login", response_model=Token)
async def login_user(request: UserLoginRequest, db: AsyncSession = Depends(get_operational_db)):
    """Login user with JWT token response"""
    try:
        # Find user by email
        result = await db.execute(
            select(User).where(User.email == request.email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Verify password
        if not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user account"
            )
        
        # Create JWT tokens
        user_data = {
            "user_id": user.user_id,
            "email": user.email,
            "name": user.name,
            "is_active": user.is_active
        }
        tokens = create_tokens(user_data)
        
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_operational_db)):
    """Refresh access token using refresh token"""
    try:
        # Verify refresh token
        payload = verify_token(request.refresh_token, "refresh")
        
        # Extract user data from payload
        user_data = {
            "user_id": payload.get("user_id"),
            "email": payload.get("email"),
            "name": payload.get("name"),
            "is_active": payload.get("is_active", True)
        }
        
        # Verify user still exists and is active
        result = await db.execute(
            select(User).where(
                (User.user_id == user_data["user_id"]) & 
                (User.is_active == True)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
    
        # Create new tokens
        tokens = create_tokens(user_data)
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token refresh failed: {str(e)}")

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return UserResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        name=current_user.name,
        is_active=current_user.is_active,
        profile_photo_url=current_user.profile_photo_url,
        profile_photo_prompt=current_user.profile_photo_prompt,
        created_at=str(current_user.created_at)
    )

@router.post("/logout")
async def logout_user(current_user = Depends(get_current_active_user)):
    """Logout user (client should discard tokens)"""
    return {"message": "Successfully logged out"}

@router.post("/request-password-reset")
async def request_password_reset(
    email: str,
    db: AsyncSession = Depends(get_operational_db)
):
    """Request password reset - sends reset token to user's email"""
    try:
        # Find user by email
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        # Always return success to prevent email enumeration
        if not user:
            return {"message": "If the email exists, a password reset link has been sent"}
        
        # In a real implementation, you would:
        # 1. Generate a secure reset token
        # 2. Store it with expiration time
        # 3. Send email with reset link
        # For now, we'll just log it (remove in production)
        import secrets
        reset_token = secrets.token_urlsafe(32)
        
        # TODO: Implement proper email sending and token storage
        # This is a placeholder implementation
        return {"message": "If the email exists, a password reset link has been sent"}
        
    except Exception as e:
        # Don't reveal internal errors
        return {"message": "If the email exists, a password reset link has been sent"}

@router.post("/reset-password-with-token")
async def reset_password_with_token(
    reset_token: str,
    new_password: str,
    db: AsyncSession = Depends(get_operational_db)
):
    """Reset password using a valid reset token"""
    # TODO: Implement token validation logic
    # This endpoint should:
    # 1. Validate the reset token
    # 2. Check if it's not expired
    # 3. Find the associated user
    # 4. Update the password
    # 5. Invalidate the token
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Password reset with token not yet implemented. Please contact administrator."
    )