"""
Authentication and authorization module for the threat intelligence API.
Provides JWT-based authentication with role-based access control.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, List
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from pydantic import BaseModel
import os
from enum import Enum

from .models import SubscriptionTier

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        subscription: str = payload.get("subscription", "free")
        permissions: List[str] = payload.get("permissions", [])
        
        if user_id is None:
            raise AuthenticationError("Invalid token payload")
        
        return TokenData(
            user_id=user_id,
            subscription=SubscriptionTier(subscription),
            permissions=permissions
        )
    except jwt.PyJWTError:
        raise AuthenticationError("Invalid token")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserIdentity:
    """Extract user identity from JWT token."""
    token_data = verify_token(credentials.credentials)
    
    # In a real implementation, you would fetch user details from database
    # For now, we'll return the token data as user identity
    return UserIdentity(
        user_id=token_data.user_id,
        subscription=token_data.subscription,
        permissions=token_data.permissions
    )


async def get_anonymous_user() -> UserIdentity:
    """Create anonymous user identity for testing/demo purposes."""
    return UserIdentity(
        user_id="anonymous",
        subscription=SubscriptionTier.FREE,
        permissions=["read:basic"]
    )


def require_subscription(min_tier: SubscriptionTier = SubscriptionTier.FREE):
    """Dependency to enforce minimum subscription tier."""
    def wrapper(user: UserIdentity = Depends(get_current_user)):
        tier_hierarchy = [
            SubscriptionTier.FREE,
            SubscriptionTier.MEDIUM,
            SubscriptionTier.PLUS,
            SubscriptionTier.ADMIN
        ]
        
        if tier_hierarchy.index(user.subscription) < tier_hierarchy.index(min_tier):
            raise AuthorizationError(f"Requires {min_tier.value} subscription or higher")
        
        return user
    return wrapper


def require_permission(permission: str):
    """Dependency to enforce specific permissions."""
    def wrapper(user: UserIdentity = Depends(get_current_user)):
        if permission not in user.permissions and "admin:all" not in user.permissions:
            raise AuthorizationError(f"Missing required permission: {permission}")
        
        return user
    return wrapper


class PermissionChecker:
    """Helper class for checking multiple permissions."""
    
    @staticmethod
    def can_access_bulk_analysis(user: UserIdentity) -> bool:
        return (user.subscription in [SubscriptionTier.PLUS, SubscriptionTier.ADMIN] or
                "bulk:analysis" in user.permissions)
    
    @staticmethod
    def can_access_ml_predictions(user: UserIdentity) -> bool:
        return (user.subscription in [SubscriptionTier.PLUS, SubscriptionTier.ADMIN] or
                "ml:predictions" in user.permissions)
    
    @staticmethod
    def can_access_analytics(user: UserIdentity) -> bool:
        return (user.subscription in [SubscriptionTier.PLUS, SubscriptionTier.ADMIN] or
                "analytics:read" in user.permissions)
    
    @staticmethod
    def can_manage_tenants(user: UserIdentity) -> bool:
        return (user.subscription == SubscriptionTier.ADMIN or
                "admin:tenants" in user.permissions)


# Rate limiting by subscription tier
RATE_LIMITS = {
    SubscriptionTier.FREE: {"requests_per_hour": 100, "concurrent_requests": 2},
    SubscriptionTier.MEDIUM: {"requests_per_hour": 1000, "concurrent_requests": 5},
    SubscriptionTier.PLUS: {"requests_per_hour": 10000, "concurrent_requests": 20},
    SubscriptionTier.ADMIN: {"requests_per_hour": -1, "concurrent_requests": -1}  # Unlimited
}


def get_rate_limit(subscription: SubscriptionTier) -> Dict[str, int]:
    """Get rate limits for a subscription tier."""
    return RATE_LIMITS.get(subscription, RATE_LIMITS[SubscriptionTier.FREE])


# ────────────────── Enums ──────────────────
class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class Permission(str, Enum):
    READ_BASIC = "read:basic"
    READ_ADVANCED = "read:advanced"
    WRITE_BASIC = "write:basic"
    WRITE_ADVANCED = "write:advanced"
    ADMIN_ALL = "admin:all"
    BULK_ANALYSIS = "bulk:analysis"
    ML_PREDICTIONS = "ml:predictions"
    ANALYTICS_READ = "analytics:read"
    ADMIN_TENANTS = "admin:tenants"


class AuthService:
    """Authentication service for user management."""
    
    def __init__(self):
        self.users_db = {}  # In-memory storage for demo
    
    async def register_user(self, registration_data: dict) -> dict:
        """Register a new user."""
        from .models import UserRegistration
        
        user_reg = UserRegistration(**registration_data)
        email = user_reg.email
        
        if email in self.users_db:
            raise ValueError("User already exists")
        
        user_id = f"user_{len(self.users_db) + 1}"
        hashed_password = get_password_hash(user_reg.password)
        
        self.users_db[email] = {
            "user_id": user_id,
            "email": email,
            "hashed_password": hashed_password,
            "subscription_level": user_reg.subscription_level,
            "role": UserRole.USER,
            "permissions": [Permission.READ_BASIC],
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        
        return {
            "user_id": user_id,
            "email": email,
            "subscription_level": user_reg.subscription_level
        }
    
    async def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        """Authenticate user credentials."""
        user = self.users_db.get(username)
        if not user:
            return None
        
        if not verify_password(password, user["hashed_password"]):
            return None
        
        return user
    
    async def create_access_token_for_user(self, user: dict) -> str:
        """Create access token for authenticated user."""
        token_data = {
            "sub": user["user_id"],
            "subscription": user["subscription_level"].value,
            "permissions": [p.value for p in user["permissions"]],
            "role": user["role"].value
        }
        return create_access_token(token_data)


# Global auth service instance
auth_service = AuthService()
