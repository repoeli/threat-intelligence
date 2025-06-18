"""
Authentication Service for Threat Intelligence API
Provides user management, JWT token handling, and session management
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple
import jwt
import bcrypt
from fastapi import HTTPException, status
import json
import os

from ..models import (
    UserRegistration, 
    UserLogin, 
    TokenResponse, 
    UserResponse, 
    SubscriptionTier
)


class AuthService:
    """Enhanced authentication service with user management"""
    
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours default
        
        # In-memory user store (in production, this would be a database)
        self.users_db: Dict[str, Dict] = {}
        self.email_to_user_id: Dict[str, str] = {}
        
        # Load existing users if any (persist to file for demo)
        self._load_users()
    
    def _load_users(self):
        """Load users from persistent storage (demo implementation)"""
        
        try:
            users_file = "users_db.json"
            if os.path.exists(users_file):
                with open(users_file, 'r') as f:
                    data = json.load(f)
                    self.users_db = data.get('users', {})
                    self.email_to_user_id = data.get('email_index', {})
        except Exception:
            pass
    
    def _save_users(self):
        """Save users to persistent storage (demo implementation)"""
        try:
            users_file = "users_db.json"
            with open(users_file, 'w') as f:
                json.dump({
                    'users': self.users_db,
                    'email_index': self.email_to_user_id
                }, f)
        except Exception:
            pass
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def _create_access_token(self, user_id: str, email: str, subscription: SubscriptionTier) -> str:
        """Create JWT access token"""
        expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        payload = {
            "user_id": user_id,
            "email": email,
            "subscription": subscription.value,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access_token"
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Dict:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id = payload.get("user_id")
            
            if not user_id or user_id not in self.users_db:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: user not found"
                )
            
            user = self.users_db[user_id]
            if not user.get("is_active", True):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account is disabled"
                )
            
            return {
                "user_id": user_id,
                "email": payload.get("email"),
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
    
    async def register_user(self, user_data: UserRegistration) -> Tuple[UserResponse, TokenResponse]:
        """Register a new user"""
        
        # Check if email already exists
        if user_data.email in self.email_to_user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        # Generate user ID
        user_id = str(uuid.uuid4())
        
        # Hash password
        hashed_password = self._hash_password(user_data.password)
        
        # Create user record
        user_record = {
            "user_id": user_id,
            "email": user_data.email,
            "password_hash": hashed_password,
            "subscription_level": user_data.subscription_level.value,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login": None,
            "api_calls_today": 0,
            "api_calls_total": 0
        }
        
        # Store user
        self.users_db[user_id] = user_record
        self.email_to_user_id[user_data.email] = user_id
        self._save_users()
        
        # Create response objects
        user_response = UserResponse(
            user_id=user_id,
            email=user_data.email,
            subscription_level=user_data.subscription_level,
            is_active=True,
            created_at=datetime.fromisoformat(user_record["created_at"])
        )
        
        # Create access token
        access_token = self._create_access_token(
            user_id=user_id,
            email=user_data.email,
            subscription=user_data.subscription_level
        )
        
        token_response = TokenResponse(
            access_token=access_token,
            expires_in=self.access_token_expire_minutes * 60
        )
        
        return user_response, token_response
    
    async def login_user(self, login_data: UserLogin) -> Tuple[UserResponse, TokenResponse]:
        """Authenticate user and return token"""
        
        # Find user by email
        user_id = self.email_to_user_id.get(login_data.email)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        user_record = self.users_db[user_id]
        
        # Verify password
        if not self._verify_password(login_data.password, user_record["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not user_record.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled"
            )
        
        # Update last login
        user_record["last_login"] = datetime.now(timezone.utc).isoformat()
        self._save_users()
        
        # Create response objects
        subscription = SubscriptionTier(user_record["subscription_level"])
        
        user_response = UserResponse(
            user_id=user_id,
            email=login_data.email,
            subscription_level=subscription,
            is_active=user_record["is_active"],
            created_at=datetime.fromisoformat(user_record["created_at"]) if user_record.get("created_at") else None
        )
        
        # Create access token
        access_token = self._create_access_token(
            user_id=user_id,
            email=login_data.email,
            subscription=subscription
        )
        
        token_response = TokenResponse(
            access_token=access_token,
            expires_in=self.access_token_expire_minutes * 60
        )
        
        return user_response, token_response
    
    async def get_user_profile(self, user_id: str) -> UserResponse:
        """Get user profile by ID"""
        user_record = self.users_db.get(user_id)
        if not user_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse(
            user_id=user_id,
            email=user_record["email"],
            subscription_level=SubscriptionTier(user_record["subscription_level"]),
            is_active=user_record["is_active"],
            created_at=datetime.fromisoformat(user_record["created_at"]) if user_record.get("created_at") else None
        )
    
    async def update_api_usage(self, user_id: str):
        """Track API usage for rate limiting"""
        if user_id in self.users_db:
            self.users_db[user_id]["api_calls_today"] += 1
            self.users_db[user_id]["api_calls_total"] += 1
            # Note: In production, you'd reset daily counters with a background task
    
    def get_user_stats(self) -> Dict:
        """Get platform statistics"""
        total_users = len(self.users_db)
        active_users = sum(1 for user in self.users_db.values() if user.get("is_active", True))
        subscription_breakdown = {}
        
        for user in self.users_db.values():
            sub_level = user.get("subscription_level", "free")
            subscription_breakdown[sub_level] = subscription_breakdown.get(sub_level, 0) + 1
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "subscription_breakdown": subscription_breakdown
        }


# Global auth service instance
auth_service = AuthService()
