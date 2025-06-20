"""
Test cases for authentication and authorization dependencies
"""
import pytest
import os
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from backend.app.auth import (
    get_current_user,
    get_current_user_optional,
    require_medium,
    require_plus,
    get_api_key_user,
    check_rate_limit,
    AuthenticationError,
    AuthorizationError,
    TokenData,
    UserIdentity,
    RATE_LIMITS
)
from backend.app.models import SubscriptionTier


class TestAuthDependencies:
    """Test authentication and authorization dependencies"""
    
    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self):
        """Test get_current_user with valid JWT token"""
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid_jwt_token"
        )
        
        from backend.app.database import AsyncSessionLocal
        
        with patch('backend.app.services.auth_service.auth_service.verify_token') as mock_verify:
            mock_verify.return_value = {
                "user_id": "12345",
                "subscription": "medium",
                "email": "test@example.com"
            }
            
            async with AsyncSessionLocal() as mock_db:
                result = await get_current_user(mock_credentials, mock_db)
                
                assert result["user_id"] == "12345"
                assert result["subscription"] == "medium"
                assert result["email"] == "test@example.com"
                # Note: verify_token now takes both token and db parameters
                mock_verify.assert_called_once_with("valid_jwt_token", mock_db)

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test get_current_user with invalid JWT token"""
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid_jwt_token"
        )
        
        with patch('backend.app.services.auth_service.auth_service.verify_token') as mock_verify:
            mock_verify.side_effect = HTTPException(
                status_code=401, 
                detail="Invalid token"
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials)            
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_optional_no_credentials(self):
        """Test get_current_user_optional with no credentials"""
        result = await get_current_user_optional(None)
        assert result["user_id"] == "anonymous"
        assert result["subscription"] == "free"
        assert result["email"] == "anonymous@example.com"

    @pytest.mark.asyncio
    async def test_get_current_user_optional_valid_credentials(self):
        """Test get_current_user_optional with valid credentials"""
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid_token"
        )
        
        with patch('backend.app.services.auth_service.auth_service.verify_token') as mock_verify:
            mock_verify.return_value = {
                "user_id": "12345",
                "subscription": "free"
            }
            
            result = await get_current_user_optional(mock_credentials)
            assert result["user_id"] == "12345"

    @pytest.mark.asyncio
    async def test_get_api_key_user_valid(self):
        """Test API key authentication with valid key"""
        valid_key = "test_admin_key_123"
        with patch.dict(os.environ, {"ADMIN_API_KEY": valid_key}):
            result = await get_api_key_user(valid_key)
            
            assert result["user_id"] == "api_admin"
            assert result["subscription"] == "admin"
            assert result["email"] == "admin@api.local"

    @pytest.mark.asyncio
    async def test_get_api_key_user_invalid(self):
        """Test API key authentication with invalid key"""
        with patch.dict(os.environ, {"ADMIN_API_KEY": "correct_key"}):
            with pytest.raises(HTTPException) as exc_info:
                await get_api_key_user("wrong_key")
            
            assert exc_info.value.status_code == 401
            assert "Invalid API key" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_check_rate_limit(self):
        """Test rate limit checking"""
        mock_user = {
            "user_id": "12345",
            "subscription": "medium"
        }
        
        from backend.app.database import AsyncSessionLocal
        
        async with AsyncSessionLocal() as mock_db:
            # Rate limiting is simplified in the current implementation
            result = await check_rate_limit(mock_user, mock_db)
            assert result == mock_user

    def test_rate_limits_configuration(self):
        """Test that rate limits are properly configured"""
        assert SubscriptionTier.FREE in RATE_LIMITS
        assert SubscriptionTier.MEDIUM in RATE_LIMITS
        assert SubscriptionTier.PLUS in RATE_LIMITS
        assert SubscriptionTier.ADMIN in RATE_LIMITS
        
        # Check that higher tiers have higher limits
        free_limit = RATE_LIMITS[SubscriptionTier.FREE]["per_minute"]
        medium_limit = RATE_LIMITS[SubscriptionTier.MEDIUM]["per_minute"]
        plus_limit = RATE_LIMITS[SubscriptionTier.PLUS]["per_minute"]
        admin_limit = RATE_LIMITS[SubscriptionTier.ADMIN]["per_minute"]
        
        assert free_limit < medium_limit < plus_limit < admin_limit

    def test_token_data_model(self):
        """Test TokenData model"""
        token_data = TokenData(
            user_id="12345",
            subscription=SubscriptionTier.MEDIUM,
            permissions=["read", "write"]
        )
        
        assert token_data.user_id == "12345"
        assert token_data.subscription == SubscriptionTier.MEDIUM
        assert len(token_data.permissions) == 2

    def test_user_identity_model(self):
        """Test UserIdentity model"""
        user_identity = UserIdentity(
            user_id="12345",
            subscription=SubscriptionTier.PLUS,
            permissions=["read", "write", "admin"],
            is_active=True
        )
        
        assert user_identity.user_id == "12345"
        assert user_identity.subscription == SubscriptionTier.PLUS
        assert user_identity.is_active is True
        assert len(user_identity.permissions) == 3

    def test_authentication_error(self):
        """Test AuthenticationError exception"""
        error = AuthenticationError("Test authentication failed")
        assert error.detail == "Test authentication failed"
        assert error.status_code == 401

    def test_authorization_error(self):
        """Test AuthorizationError exception"""
        error = AuthorizationError("Test authorization failed") 
        assert error.detail == "Test authorization failed"
        assert error.status_code == 403
