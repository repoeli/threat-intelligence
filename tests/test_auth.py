"""
tests/test_auth.py - Authentication and authorization tests
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
import httpx
from fastapi import status, HTTPException

from backend.app.auth import AuthService, UserRole, Permission, auth_service
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
        # First register a user
        user_data = {
            "email": "test@example.com", 
            "password": "securepassword123",
            "subscription_level": "free"
        }
        await self.auth_service.register_user(user_data)
          # Now authenticate
        user = await self.auth_service.authenticate_user("test@example.com", "securepassword123")
        
        assert user is not None
        assert user["email"] == "test@example.com"
        assert user["subscription_level"].value == "free"

    async def test_authenticate_user_invalid_credentials(self):
        """Test authentication with invalid credentials"""
        # First register a user
        user_data = {
            "email": "test@example.com", 
            "password": "securepassword123",
            "subscription_level": "free"
        }
        await self.auth_service.register_user(user_data)
        
        # Try to authenticate with wrong password
        user = await self.auth_service.authenticate_user("test@example.com", "wrongpassword")
        
        assert user is None

    async def test_authenticate_nonexistent_user(self):
        """Test authentication of non-existent user"""
        user = await self.auth_service.authenticate_user("nonexistent@example.com", "password123")
        
        assert user is None

    async def test_create_access_token_for_user(self):
        """Test creating access token for authenticated user"""
        # First register a user
        user_data = {
            "email": "test@example.com", 
            "password": "securepassword123",
            "subscription_level": "free"
        }
        await self.auth_service.register_user(user_data)
        
        # Authenticate the user
        user = await self.auth_service.authenticate_user("test@example.com", "securepassword123")
        
        # Create access token
        token = await self.auth_service.create_access_token_for_user(user)
        
        assert isinstance(token, str)
        assert len(token) > 0

# Test utilities
from backend.app.auth import verify_password, get_password_hash


@pytest.mark.asyncio
class TestPasswordUtilities:
    """Test password hashing and verification utilities"""

    def test_password_hashing_and_verification(self):
        """Test password hashing and verification work correctly"""
        password = "securepassword123"
        
        # Hash the password
        hashed = get_password_hash(password)
        
        # Verify correct password
        assert verify_password(password, hashed) is True
        
        # Verify incorrect password
        assert verify_password("wrongpassword", hashed) is False

    def test_different_passwords_produce_different_hashes(self):
        """Test that different passwords produce different hashes"""
        password1 = "password123"
        password2 = "password456"
        
        hash1 = get_password_hash(password1)
        hash2 = get_password_hash(password2)
        
        assert hash1 != hash2

    def test_same_password_produces_different_hashes(self):
        """Test that same password produces different hashes (salt)"""
        password = "password123"
        
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True
