"""
tests/test_auth.py - Authentication and authorization tests
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
import httpx
from fastapi import status, HTTPException

from backend.app.auth import AuthService, UserRole, Permission, auth_service, verify_password, get_password_hash
from backend.app.models import LoginRequest, UserRegistration


@pytest.mark.asyncio
class TestAuthService:
    """Test AuthService class directly"""

    def setup_method(self):
        """Setup for each test method"""
        self.auth_service = AuthService()

    async def test_register_user_success(self):
        """Test successful user registration"""
        user_data = {
            "email": "test@example.com", 
            "password": "securepassword123",
            "subscription_level": "free"
        }
        
        result = await self.auth_service.register_user(user_data)
        
        assert result["email"] == "test@example.com"
        assert result["subscription_level"] == "free"
        assert "user_id" in result
        
        # Verify user was added to database
        assert "test@example.com" in self.auth_service.users_db

    async def test_register_user_duplicate_email(self):
        """Test registration with duplicate email"""
        user_data = {
            "email": "test@example.com", 
            "password": "securepassword123",
            "subscription_level": "free"
        }
        
        # Register first user
        await self.auth_service.register_user(user_data)
        
        # Try to register same email again
        with pytest.raises(ValueError, match="User already exists"):
            await self.auth_service.register_user(user_data)

    async def test_authenticate_user_success(self):
        """Test successful user authentication"""
        user_data = {
            "email": "test@example.com", 
            "password": "securepassword123",
            "subscription_level": "free"
        }
        
        # Register user first
        await self.auth_service.register_user(user_data)
        
        # Authenticate user
        user = await self.auth_service.authenticate_user("test@example.com", "securepassword123")
        
        assert user is not None
        assert user["email"] == "test@example.com"
        assert user["subscription_level"] == "free"

    async def test_authenticate_user_invalid_credentials(self):
        """Test authentication with invalid credentials"""
        user_data = {
            "email": "test@example.com", 
            "password": "securepassword123",
            "subscription_level": "free"
        }
        
        # Register user first
        await self.auth_service.register_user(user_data)
        
        # Try to authenticate with wrong password
        user = await self.auth_service.authenticate_user("test@example.com", "wrongpassword")
        assert user is None
        
        # Try to authenticate non-existent user
        user = await self.auth_service.authenticate_user("nonexistent@example.com", "anypassword")
        assert user is None

    async def test_create_access_token_for_user(self):
        """Test access token creation"""
        user_data = {
            "email": "test@example.com", 
            "password": "securepassword123",
            "subscription_level": "free"
        }
        
        # Register and authenticate user
        await self.auth_service.register_user(user_data)
        user = await self.auth_service.authenticate_user("test@example.com", "securepassword123")
        
        # Create access token
        token = await self.auth_service.create_access_token_for_user(user)
        
        assert isinstance(token, str)
        assert len(token) > 0


class TestPasswordUtilities:
    """Test password hashing and verification"""

    def test_password_hash_and_verify(self):
        """Test password hashing and verification"""
        password = "testpassword123"
        
        # Hash password
        hashed = get_password_hash(password)
        assert hashed != password
        assert len(hashed) > 0
        
        # Verify correct password
        assert verify_password(password, hashed) is True
        
        # Verify incorrect password
        assert verify_password("wrongpassword", hashed) is False

    def test_different_hashes_for_same_password(self):
        """Test that same password produces different hashes (salt)"""
        password = "testpassword123"
        
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestEnums:
    """Test authentication enums"""

    def test_user_role_enum(self):
        """Test UserRole enum values"""
        assert UserRole.USER == "user"
        assert UserRole.ADMIN == "admin"
        assert UserRole.MODERATOR == "moderator"

    def test_permission_enum(self):
        """Test Permission enum values"""
        assert Permission.READ_BASIC == "read:basic"
        assert Permission.ADMIN_ALL == "admin:all"
        assert Permission.BULK_ANALYSIS == "bulk:analysis"


@pytest.mark.asyncio
class TestAuthModels:
    """Test authentication models"""

    def test_login_request_model(self):
        """Test LoginRequest model"""
        data = {
            "username": "testuser",
            "password": "testpass123"
        }
        
        login_req = LoginRequest(**data)
        assert login_req.username == "testuser"
        assert login_req.password == "testpass123"

    def test_user_registration_model(self):
        """Test UserRegistration model"""
        data = {
            "email": "test@example.com",
            "password": "testpass123",
            "subscription_level": "free"
        }
        
        user_reg = UserRegistration(**data)
        assert user_reg.email == "test@example.com"
        assert user_reg.password == "testpass123"
        assert user_reg.subscription_level == "free"

    def test_user_registration_model_defaults(self):
        """Test UserRegistration model with defaults"""
        data = {
            "email": "test@example.com",
            "password": "testpass123"
        }
        
        user_reg = UserRegistration(**data)
        assert user_reg.subscription_level == "free"  # Default value
