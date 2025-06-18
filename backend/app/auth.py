"""
Authentication and authorization module for the threat intelligence API.
Provides JWT-based authentication with role-based access control.
"""

from typing import Dict, Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import os

from .models import SubscriptionTier
from .services.auth_service import auth_service

# Configuration
security = HTTPBearer()


class TokenData(BaseModel):
    user_id: Optional[str] = None
    subscription: Optional[SubscriptionTier] = None
    permissions: List[str] = []


class UserIdentity(BaseModel):
    user_id: str
    subscription: SubscriptionTier
    permissions: List[str]
    is_active: bool = True


class AuthenticationError(HTTPException):
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class AuthorizationError(HTTPException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, str]:
    """
    FastAPI dependency to get current authenticated user from JWT token
    """
    return auth_service.verify_token(credentials.credentials)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Dict[str, str]:
    """
    FastAPI dependency to get current user (optional authentication)
    Returns anonymous user if no token provided
    """
    if credentials is None:
        return {"user_id": "anonymous", "subscription": "free", "email": "anonymous@example.com"}
    
    try:
        return auth_service.verify_token(credentials.credentials)
    except HTTPException:
        return {"user_id": "anonymous", "subscription": "free", "email": "anonymous@example.com"}


def require_subscription(min_tier: SubscriptionTier):
    """
    Dependency factory for subscription-level requirements
    """
    async def subscription_checker(current_user: Dict = Depends(get_current_user)) -> Dict[str, str]:
        user_tier = SubscriptionTier(current_user.get("subscription", "free"))
        
        # Define tier hierarchy (higher number = better tier)
        tier_levels = {
            SubscriptionTier.FREE: 0,
            SubscriptionTier.MEDIUM: 1,
            SubscriptionTier.PLUS: 2,
            SubscriptionTier.ADMIN: 3
        }
        
        if tier_levels.get(user_tier, 0) < tier_levels.get(min_tier, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This endpoint requires {min_tier.value} subscription or higher"
            )
        
        return current_user
    
    return subscription_checker


# Convenience dependencies for different subscription levels
require_medium = require_subscription(SubscriptionTier.MEDIUM)
require_plus = require_subscription(SubscriptionTier.PLUS)
require_admin = require_subscription(SubscriptionTier.ADMIN)


async def get_api_key_user(api_key: str = None) -> Dict[str, str]:
    """
    Alternative authentication via API key (for API clients)
    This would typically check against a database of API keys
    """
    # This is a placeholder - in production you'd validate against a database
    if api_key == os.getenv("ADMIN_API_KEY"):
        return {
            "user_id": "api_admin",
            "subscription": "admin",
            "email": "admin@api.local"
        }
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key"
    )


# Rate limiting helpers
RATE_LIMITS = {
    SubscriptionTier.FREE: {"per_minute": 5, "per_day": 100},
    SubscriptionTier.MEDIUM: {"per_minute": 20, "per_day": 1000},
    SubscriptionTier.PLUS: {"per_minute": 100, "per_day": 10000},
    SubscriptionTier.ADMIN: {"per_minute": 1000, "per_day": 100000}
}


async def check_rate_limit(current_user: Dict = Depends(get_current_user)) -> Dict[str, str]:
    """
    Check if user has exceeded their rate limit
    """
    user_tier = SubscriptionTier(current_user.get("subscription", "free"))
    limits = RATE_LIMITS.get(user_tier, RATE_LIMITS[SubscriptionTier.FREE])
    
    # In production, this would check against Redis or database
    # For now, we'll just track in the auth service
    await auth_service.update_api_usage(current_user["user_id"])
    
    return current_user


# Legacy compatibility - for the old get_identity function
def get_identity() -> Dict[str, str]:
    """Legacy function for backward compatibility"""
    return {"user_id": "anon", "subscription": "free"}
