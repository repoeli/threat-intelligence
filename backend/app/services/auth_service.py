"""
Authentication Service for Threat Intelligence API
Provides user management, JWT token handling, and session management
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple, Optional
import jwt
import os
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, Depends

from ..models import (
    UserRegistration, 
    UserLogin, 
    TokenResponse, 
    UserResponse, 
    SubscriptionTier,
    UserCreate
)
from ..database import get_db_session
from .database_service import db_service


class AuthService:
    """Enhanced authentication service with database integration"""
    
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours default
    
    def _create_access_token(self, user_id: int, email: str, username: str, subscription: SubscriptionTier) -> str:
        """Create JWT access token"""
        expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        payload = {
            "user_id": user_id,
            "email": email,
            "username": username,
            "subscription": subscription.value,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access_token"
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    async def verify_token(self, token: str, db: AsyncSession) -> Dict:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id = payload.get("user_id")
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: no user ID"
                )
            
            user = await db_service.get_user_by_id(db, user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: user not found"
                )
            
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account is disabled"
                )
            
            return {
                "user_id": user_id,
                "email": payload.get("email"),
                "username": payload.get("username"),
                "subscription": payload.get("subscription", "free")
            }
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    async def register_user(self, user_data: UserRegistration, db: AsyncSession) -> Tuple[UserResponse, TokenResponse]:
        """Register a new user"""
        
        # Check if email already exists
        existing_user = await db_service.get_user_by_email(db, user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        # Check if username already exists
        existing_username = await db_service.get_user_by_username(db, user_data.email.split('@')[0])
        username = user_data.email.split('@')[0] if not existing_username else f"{user_data.email.split('@')[0]}_{uuid.uuid4().hex[:6]}"
        
        # Create user
        user_create = UserCreate(
            username=username,
            email=user_data.email,
            password=user_data.password
        )
        
        user = await db_service.create_user(db, user_create)
        
        # Create response objects
        user_response = UserResponse(
            user_id=str(user.id),
            email=user.email,
            subscription_level=user_data.subscription_level,
            is_active=user.is_active,
            created_at=user.created_at
        )
        
        # Create access token
        access_token = self._create_access_token(
            user_id=user.id,
            email=user.email,
            username=user.username,
            subscription=user_data.subscription_level
        )
        
        token_response = TokenResponse(
            access_token=access_token,
            expires_in=self.access_token_expire_minutes * 60
        )
        
        return user_response, token_response
    
    async def login_user(self, login_data: UserLogin, db: AsyncSession) -> Tuple[UserResponse, TokenResponse]:
        """Authenticate user and return token"""
        
        # Authenticate user
        user = await db_service.authenticate_user(db, login_data.email, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled"
            )
        
        # Create response objects
        subscription = SubscriptionTier.FREE  # Default subscription for now
        
        user_response = UserResponse(
            user_id=str(user.id),
            email=user.email,
            subscription_level=subscription,
            is_active=user.is_active,
            created_at=user.created_at
        )
        
        # Create access token
        access_token = self._create_access_token(
            user_id=user.id,
            email=user.email,
            username=user.username,
            subscription=subscription
        )
        
        token_response = TokenResponse(
            access_token=access_token,
            expires_in=self.access_token_expire_minutes * 60
        )
        
        return user_response, token_response
    
    async def get_user_profile(self, user_id: int, db: AsyncSession) -> UserResponse:
        """Get user profile by ID"""
        user = await db_service.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse(
            user_id=str(user.id),
            email=user.email,
            subscription_level=SubscriptionTier.FREE,  # Default for now
            is_active=user.is_active,
            created_at=user.created_at
        )
    
    async def get_user_stats(self, db: AsyncSession) -> Dict:
        """Get platform statistics"""
        from sqlalchemy import select, func
        from ..db_models import User, AnalysisHistory
        
        # Get user counts
        total_users_result = await db.execute(select(func.count(User.id)))
        total_users = total_users_result.scalar()
        
        active_users_result = await db.execute(select(func.count(User.id)).where(User.is_active == True))
        active_users = active_users_result.scalar()
        
        # Get analysis counts
        total_analyses_result = await db.execute(select(func.count(AnalysisHistory.id)))
        total_analyses = total_analyses_result.scalar()
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_analyses": total_analyses,
            "subscription_breakdown": {"free": total_users}  # Simplified for now
        }


# Global auth service instance
auth_service = AuthService()
