"""
tests/test_auth.py - Authentication and authorization tests
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
import httpx
from fastapi import status, HTTPException

from backend.app.services.auth_service import auth_service
from backend.app.models import LoginRequest, UserRegistration, UserLogin, SubscriptionTier
from backend.app.database import AsyncSessionLocal
from backend.app.services.database_service import db_service
import bcrypt


@pytest.mark.asyncio
class TestAuthService:
    """Test AuthService class directly"""
    
    def setup_method(self):
        """Setup for each test method"""
        # Use the global auth service instance
        self.auth_service = auth_service
        # Note: With database backend, we don't clear users in tests
        # Tests should be isolated and use test database or unique data
        
    async def test_register_user_success(self):
        """Test successful user registration"""
        import uuid
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        user_data = UserRegistration(
            email=unique_email, 
            password="securepassword123",
            subscription_level=SubscriptionTier.FREE
        )
        
        async with AsyncSessionLocal() as db:
            user_response, token_response = await self.auth_service.register_user(user_data, db)
            
            assert user_response.email == unique_email
            assert user_response.subscription_level == SubscriptionTier.FREE
            assert user_response.user_id is not None
            assert token_response.access_token is not None
            
            # Verify user was added to database
            user = await db_service.get_user_by_email(db, unique_email)
            assert user is not None
            assert user.email == unique_email

    async def test_register_user_duplicate_email(self):
        """Test registration with duplicate email"""
        import uuid
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        user_data = UserRegistration(
            email=unique_email, 
            password="securepassword123",
            subscription_level=SubscriptionTier.FREE
        )
        
        async with AsyncSessionLocal() as db:
            # Register first user
            await self.auth_service.register_user(user_data, db)
            
            # Try to register same email again
            with pytest.raises(HTTPException) as exc_info:
                await self.auth_service.register_user(user_data, db)
            assert exc_info.value.status_code == 409

    async def test_authenticate_user_success(self):
        """Test successful user authentication"""
        import uuid
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        user_reg_data = UserRegistration(
            email=unique_email, 
            password="securepassword123",
            subscription_level=SubscriptionTier.FREE
        )
        
        async with AsyncSessionLocal() as db:
            # Register user first
            await self.auth_service.register_user(user_reg_data, db)
            
            # Login user
            login_data = UserLogin(email=unique_email, password="securepassword123")
            user_response, token_response = await self.auth_service.login_user(login_data, db)
            
            assert user_response is not None
            assert user_response.email == unique_email
            assert user_response.subscription_level == SubscriptionTier.FREE
            assert token_response.access_token is not None

    async def test_authenticate_user_invalid_credentials(self):
        """Test authentication with invalid credentials"""
        import uuid
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        user_reg_data = UserRegistration(
            email=unique_email, 
            password="securepassword123",
            subscription_level=SubscriptionTier.FREE
        )
        
        async with AsyncSessionLocal() as db:
            # Register user first
            await self.auth_service.register_user(user_reg_data, db)
            
            # Try to authenticate with wrong password
            login_data = UserLogin(email=unique_email, password="wrongpassword")
            with pytest.raises(HTTPException) as exc_info:
                await self.auth_service.login_user(login_data, db)
            assert exc_info.value.status_code == 401
        
        async with AsyncSessionLocal() as db:
            # Try to authenticate non-existent user
            login_data = UserLogin(email="nonexistent@example.com", password="anypassword")
            with pytest.raises(HTTPException) as exc_info:
                await self.auth_service.login_user(login_data, db)
            assert exc_info.value.status_code == 401

    async def test_create_access_token_for_user(self):
        """Test access token creation"""
        import uuid
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        user_reg_data = UserRegistration(
            email=unique_email, 
            password="securepassword123",
            subscription_level=SubscriptionTier.FREE
        )
        
        async with AsyncSessionLocal() as db:
            # Register user
            user_response, token_response = await self.auth_service.register_user(user_reg_data, db)
            
            # Check token properties
            assert isinstance(token_response.access_token, str)
            assert len(token_response.access_token) > 0
            assert token_response.token_type == "bearer"


class TestPasswordUtilities:
    """Test password hashing and verification using auth service"""
    
    def test_password_hash_and_verify(self):
        """Test password hashing and verification"""
        password = "testpassword123"
        
        # Hash password using database service
        hashed = db_service._hash_password(password)
        assert hashed != password
        assert len(hashed) > 0
        
        # Verify correct password
        assert db_service._verify_password(password, hashed) is True
        
        # Verify incorrect password
        assert db_service._verify_password("wrongpassword", hashed) is False

    def test_different_hashes_for_same_password(self):
        """Test that same password produces different hashes (salt)"""
        password = "testpassword123"
        
        hash1 = db_service._hash_password(password)
        hash2 = db_service._hash_password(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        
        # But both should verify correctly
        assert db_service._verify_password(password, hash1) is True
        assert db_service._verify_password(password, hash2) is True


class TestBcryptDirect:
    """Test bcrypt functions directly"""

    def test_bcrypt_password_hashing(self):
        """Test bcrypt password hashing"""
        password = "testpassword123"
        
        # Hash password using bcrypt directly
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        # Verify password
        assert bcrypt.checkpw(password.encode('utf-8'), hashed) is True
        assert bcrypt.checkpw("wrongpassword".encode('utf-8'), hashed) is False


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
