"""
FastAPI dependencies for authentication and authorization
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.auth import extract_user_from_token, UserInToken
from app.database import get_operational_db
from app.models import User

# HTTP Bearer token scheme
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_operational_db)
) -> UserInToken:
    """
    Dependency to get current authenticated user from JWT token
    """
    # Extract user info from token
    user_in_token = extract_user_from_token(credentials.credentials)
    
    # Verify user exists and is active in database
    result = await db.execute(
        select(User).where(
            (User.user_id == user_in_token.user_id) & 
            (User.is_active == True)
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_in_token

async def get_current_active_user(
    current_user: UserInToken = Depends(get_current_user)
) -> UserInToken:
    """
    Dependency to get current active user (additional check)
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    return current_user

def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[UserInToken]:
    """
    Optional authentication - returns None if no token provided
    """
    if not credentials:
        return None
    
    try:
        return extract_user_from_token(credentials.credentials)
    except HTTPException:
        return None
