"""
Test cases for VirusTotal service
"""
import pytest
import os
from unittest.mock import patch, AsyncMock, Mock
from fastapi import HTTPException

from backend.app.services.virustotal_service import vt_call, _get_vt_client, LIMITS
from backend.app.clients.virustotal_client import APIError, RateLimitError, VirusTotalClient


class TestVirusTotalService:
    """Test VirusTotal service functionality"""
    
    @pytest.mark.asyncio
    async def test_vt_call_success(self):
        """Test successful VirusTotal API call"""
        mock_response = {
            "data": {
                "id": "8.8.8.8",
                "type": "ip_address",
                "attributes": {"reputation": 0}
            }
        }
        
        with patch('backend.app.services.virustotal_service._r') as mock_redis:
            with patch('backend.app.services.virustotal_service._get_vt_client') as mock_get_client:
                # Setup mocks
                mock_redis_instance = AsyncMock()
                mock_redis_instance.incr.return_value = 1  # First call of the day
                mock_redis_instance.expire.return_value = True
                mock_redis.return_value = mock_redis_instance
                
                mock_vt_client = AsyncMock()
                mock_vt_client.call_endpoint.return_value = mock_response
                mock_get_client.return_value = mock_vt_client
                
                # Make the call
                result = await vt_call(
                    uid="test_user",
                    tier="free",
                    name="get_ip_report",
                    path_params={"ip": "8.8.8.8"}
                )
                
                # Verify result
                assert result == mock_response
                
                # Verify Redis calls
                mock_redis_instance.incr.assert_called_once()
                mock_redis_instance.expire.assert_called_once()
                
                # Verify VT client call
                mock_vt_client.call_endpoint.assert_called_once_with(
                    "get_ip_report",
                    path_params={"ip": "8.8.8.8"},
                    params=None,
                    json=None
                )
    
    @pytest.mark.asyncio
    async def test_vt_call_quota_exceeded(self):
        """Test quota exceeded error"""
        with patch('backend.app.services.virustotal_service._r') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis_instance.incr.return_value = 25  # Exceeds free tier limit of 20
            mock_redis.return_value = mock_redis_instance
            
            with pytest.raises(HTTPException) as exc_info:
                await vt_call(
                    uid="test_user",
                    tier="free",
                    name="get_ip_report",
                    path_params={"ip": "8.8.8.8"}
                )
            
            assert exc_info.value.status_code == 429
            assert "daily quota exceeded" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_vt_call_rate_limit_error(self):
        """Test VirusTotal rate limit error handling"""
        with patch('backend.app.services.virustotal_service._r') as mock_redis:
            with patch('backend.app.services.virustotal_service._get_vt_client') as mock_get_client:
                # Setup Redis mock (within quota)
                mock_redis_instance = AsyncMock()
                mock_redis_instance.incr.return_value = 1
                mock_redis.return_value = mock_redis_instance
                
                # Setup VT client mock to raise rate limit error
                mock_vt_client = AsyncMock()
                mock_vt_client.call_endpoint.side_effect = RateLimitError("Rate limit exceeded")
                mock_get_client.return_value = mock_vt_client
                
                with pytest.raises(HTTPException) as exc_info:
                    await vt_call(
                        uid="test_user",
                        tier="medium",
                        name="get_ip_report",
                        path_params={"ip": "8.8.8.8"}
                    )
                
                assert exc_info.value.status_code == 429
                assert "VirusTotal key limit" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_vt_call_api_error(self):
        """Test VirusTotal API error handling"""
        with patch('backend.app.services.virustotal_service._r') as mock_redis:
            with patch('backend.app.services.virustotal_service._get_vt_client') as mock_get_client:
                # Setup Redis mock (within quota)
                mock_redis_instance = AsyncMock()
                mock_redis_instance.incr.return_value = 1
                mock_redis.return_value = mock_redis_instance
                  # Setup VT client mock to raise API error
                mock_vt_client = AsyncMock()
                mock_vt_client.call_endpoint.side_effect = APIError("API Error")
                mock_get_client.return_value = mock_vt_client
                
                with pytest.raises(HTTPException) as exc_info:
                    await vt_call(
                        uid="test_user",
                        tier="plus",
                        name="get_ip_report",
                        path_params={"ip": "8.8.8.8"}
                    )
                
                assert exc_info.value.status_code == 502
                assert "API Error" in str(exc_info.value.detail)

    def test_get_vt_client_with_api_key(self):
        """Test VirusTotal client initialization with API key"""
        with patch.dict(os.environ, {"VIRUSTOTAL_API_KEY": "test_api_key"}):
            # Reset the global client to ensure fresh initialization
            import backend.app.services.virustotal_service as vt_service
            vt_service._vt = None
            
            client = _get_vt_client()
            
            assert client is not None
            assert isinstance(client, VirusTotalClient)
    
    def test_get_vt_client_without_api_key(self):
        """Test VirusTotal client initialization without API key"""
        with patch.dict(os.environ, {}, clear=True):
            # Reset the global client 
            import backend.app.services.virustotal_service as vt_service
            vt_service._vt = None
            
            with pytest.raises(HTTPException) as exc_info:
                _get_vt_client()
            
            assert exc_info.value.status_code == 503
            assert "VirusTotal API key not configured" in str(exc_info.value.detail)
            
            assert exc_info.value.status_code == 503
            assert "VirusTotal API key not configured" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_vt_call_different_tiers(self):
        """Test quota limits for different subscription tiers"""
        test_cases = [
            ("free", 20),
            ("medium", 500),
            ("plus", 2000),
            ("admin", 10000)
        ]
        
        for tier, expected_limit in test_cases:
            assert LIMITS[tier] == expected_limit
    
    @pytest.mark.asyncio
    async def test_vt_call_with_all_parameters(self):
        """Test VirusTotal call with all parameter types"""
        mock_response = {"success": True}
        
        with patch('backend.app.services.virustotal_service._r') as mock_redis:
            with patch('backend.app.services.virustotal_service._get_vt_client') as mock_get_client:
                # Setup mocks
                mock_redis_instance = AsyncMock()
                mock_redis_instance.incr.return_value = 1
                mock_redis.return_value = mock_redis_instance
                
                mock_vt_client = AsyncMock()
                mock_vt_client.call_endpoint.return_value = mock_response
                mock_get_client.return_value = mock_vt_client
                
                # Make call with all parameter types
                result = await vt_call(
                    uid="test_user",
                    tier="admin",
                    name="scan_url",
                    path_params={"id": "scan123"},
                    params={"include_details": True},
                    json={"url": "https://example.com"}
                )
                
                assert result == mock_response
                
                mock_vt_client.call_endpoint.assert_called_once_with(
                    "scan_url",
                    path_params={"id": "scan123"},
                    params={"include_details": True},
                    json={"url": "https://example.com"}
                )
    
    @pytest.mark.asyncio
    async def test_redis_key_format(self):
        """Test that Redis keys are formatted correctly for daily quotas"""
        with patch('backend.app.services.virustotal_service._r') as mock_redis:
            with patch('backend.app.services.virustotal_service._get_vt_client') as mock_get_client:
                with patch('time.time', return_value=1640995200):  # Fixed timestamp
                    mock_redis_instance = AsyncMock()
                    mock_redis_instance.incr.return_value = 1
                    mock_redis.return_value = mock_redis_instance
                    
                    mock_vt_client = AsyncMock()
                    mock_vt_client.call_endpoint.return_value = {"success": True}
                    mock_get_client.return_value = mock_vt_client
                    
                    await vt_call(
                        uid="test_user_123",
                        tier="medium",
                        name="get_ip_report",
                        path_params={"ip": "8.8.8.8"}
                    )
                    
                    # Verify Redis key format: vt:user_id:day_timestamp
                    expected_day = int(1640995200 // 86400)  # Day number since epoch
                    expected_key = f"vt:test_user_123:{expected_day}"
                    
                    mock_redis_instance.incr.assert_called_once_with(expected_key)
                    mock_redis_instance.expire.assert_called_once_with(expected_key, 86400)


class TestLimitsConfiguration:
    """Test subscription tier limits configuration"""
    
    def test_limits_exist_for_all_tiers(self):
        """Test that limits are defined for all subscription tiers"""
        expected_tiers = ["free", "medium", "plus", "admin"]
        
        for tier in expected_tiers:
            assert tier in LIMITS
            assert isinstance(LIMITS[tier], int)
            assert LIMITS[tier] > 0
    
    def test_limits_hierarchy(self):
        """Test that higher tiers have higher limits"""
        assert LIMITS["free"] < LIMITS["medium"]
        assert LIMITS["medium"] < LIMITS["plus"]
        assert LIMITS["plus"] < LIMITS["admin"]
