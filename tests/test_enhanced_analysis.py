"""
tests/test_enhanced_analysis.py - Integration tests for enhanced analysis endpoints
"""

import pytest
from unittest.mock import AsyncMock, patch
import httpx
from fastapi import status

from backend.app.models import IndicatorType, ThreatVerdict, RiskLevel


@pytest.mark.asyncio
class TestEnhancedAnalysis:
    """Test enhanced analysis endpoints with fusion and ML"""

    async def test_analyze_endpoint_with_auth(self, async_client: httpx.AsyncClient, mock_auth_user):
        """Test enhanced analyze endpoint with authentication"""
        indicator_data = {"indicator": "192.168.1.100"}
        
        # Mock all the service calls
        with patch('backend.app.main.vt_call') as mock_vt, \
             patch('backend.app.main._call_abuseipdb') as mock_abuse, \
             patch('backend.app.main._call_openai') as mock_openai, \
             patch('backend.app.main.intelligence_fusion.fuse_intelligence') as mock_fusion, \
             patch('backend.app.main.ml_classifier.extract_features') as mock_features, \
             patch('backend.app.main.ml_classifier.predict_threat') as mock_predict:
            
            # Mock VT response
            mock_vt.return_value = {
                "data": {
                    "type": "ip_address",
                    "attributes": {
                        "last_analysis_stats": {
                            "malicious": 10,
                            "clean": 40,
                            "suspicious": 3,
                            "undetected": 2
                        },
                        "reputation": -5
                    }
                }
            }
            
            # Mock AbuseIPDB response
            mock_abuse.return_value = {
                "data": {
                    "abuseConfidencePercentage": 75,
                    "totalReports": 25
                }
            }
            
            # Mock OpenAI response
            mock_openai.return_value = "This IP shows malicious activity with high confidence"
            
            # Mock fusion result
            fusion_result = AsyncMock()
            fusion_result.verdict = ThreatVerdict.MALICIOUS
            fusion_result.risk_level = RiskLevel.HIGH
            fusion_result.confidence_score = 0.85
            fusion_result.summary = "Multiple sources indicate malicious activity"
            fusion_result.recommendations = ["Block this IP", "Monitor related traffic"]
            fusion_result.consensus_score = 0.8
            mock_fusion.return_value = fusion_result
            
            # Mock ML features and prediction
            mock_features.return_value = {"malicious_ratio": 0.8, "reputation_score": -5}
            mock_predict.return_value = {
                "probability_malicious": 0.85,
                "classification": "malicious",
                "confidence": 0.9
            }
            
            headers = {"Authorization": "Bearer fake_token"}
            response = await async_client.post("/analyze", json=indicator_data, headers=headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify response structure
            assert data["indicator"] == "192.168.1.100"
            assert data["indicator_type"] == "ip"
            assert data["verdict"] == "malicious"
            assert data["risk_level"] == "high"
            assert data["confidence_score"] == 0.85
            assert "analysis_summary" in data
            assert "recommendations" in data
            assert "sources" in data
            assert "fusion_metadata" in data
            
            # Verify sources are included
            assert "virustotal" in data["sources"]
            assert "abuseipdb" in data["sources"]
            assert "openai_analysis" in data["sources"]
            assert "ml_classification" in data["sources"]

    async def test_bulk_analysis_endpoint(self, async_client: httpx.AsyncClient, mock_auth_admin):
        """Test bulk analysis endpoint"""
        bulk_data = {
            "indicators": ["192.168.1.1", "example.com", "malware.exe"]
        }
        
        with patch('backend.app.main.analyze') as mock_analyze:
            # Mock individual analysis results
            mock_results = [
                AsyncMock(
                    indicator="192.168.1.1",
                    verdict=ThreatVerdict.MALICIOUS,
                    risk_level=RiskLevel.HIGH
                ),
                AsyncMock(
                    indicator="example.com",
                    verdict=ThreatVerdict.BENIGN,
                    risk_level=RiskLevel.LOW
                ),
                AsyncMock(
                    indicator="malware.exe",
                    verdict=ThreatVerdict.MALICIOUS,
                    risk_level=RiskLevel.CRITICAL
                )
            ]
            mock_analyze.side_effect = mock_results
            
            headers = {"Authorization": "Bearer admin_token"}
            response = await async_client.post("/analyze/bulk", json=bulk_data, headers=headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["total_analyzed"] == 3
            assert data["successful_analyses"] == 3
            assert len(data["results"]) == 3

    async def test_bulk_analysis_permission_denied(self, async_client: httpx.AsyncClient, mock_auth_user):
        """Test bulk analysis with insufficient permissions"""
        bulk_data = {
            "indicators": ["192.168.1.1", "example.com"]
        }
        
        headers = {"Authorization": "Bearer user_token"}
        response = await async_client.post("/analyze/bulk", json=bulk_data, headers=headers)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_analyze_unsupported_indicator(self, async_client: httpx.AsyncClient, mock_auth_user):
        """Test analysis with unsupported indicator type"""
        indicator_data = {"indicator": "not_a_valid_indicator"}
        
        headers = {"Authorization": "Bearer fake_token"}
        response = await async_client.post("/analyze", json=indicator_data, headers=headers)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_enhanced_visualize_endpoint(self, async_client: httpx.AsyncClient, mock_auth_user):
        """Test enhanced visualize endpoint with authentication"""
        indicator_data = {"indicator": "example.com"}
        
        with patch('backend.app.main.vt_call') as mock_vt, \
             patch('backend.app.main._openai_visualize') as mock_viz:
            
            mock_vt.return_value = {
                "data": {
                    "type": "domain",
                    "attributes": {
                        "last_analysis_stats": {
                            "malicious": 2,
                            "clean": 48,
                            "suspicious": 0,
                            "undetected": 5
                        }
                    }
                }
            }
            
            mock_viz.return_value = {
                "summary_markdown": "# Domain Analysis\nThis domain appears clean",
                "charts": [{"type": "bar", "data": []}],
                "verdict": "benign"
            }
            
            headers = {"Authorization": "Bearer fake_token"}
            response = await async_client.post("/api/visualize", json=indicator_data, headers=headers)
            
            assert response.status_code == status.HTTP_200_OK

    async def test_metrics_endpoint_with_permission(self, async_client: httpx.AsyncClient, mock_auth_admin):
        """Test metrics endpoint with proper permissions"""
        headers = {"Authorization": "Bearer admin_token"}
        response = await async_client.get("/metrics", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_analyses" in data
        assert "fusion_engine_version" in data

    async def test_metrics_endpoint_permission_denied(self, async_client: httpx.AsyncClient, mock_auth_user):
        """Test metrics endpoint with insufficient permissions"""
        headers = {"Authorization": "Bearer user_token"}
        response = await async_client.get("/metrics", headers=headers)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_system_status_endpoint(self, async_client: httpx.AsyncClient, mock_auth_admin):
        """Test system status endpoint"""
        headers = {"Authorization": "Bearer admin_token"}
        response = await async_client.get("/status", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "system" in data
        assert "intelligence_fusion" in data
        assert "ml_classifier" in data
        assert "external_apis" in data

    async def test_enhanced_health_endpoint(self, async_client: httpx.AsyncClient):
        """Test enhanced health check endpoint"""
        response = await async_client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "OK"
        assert "timestamp" in data
        assert "version" in data
        assert "services" in data
        assert "virustotal" in data["services"]

    async def test_virustotal_endpoints_with_auth(self, async_client: httpx.AsyncClient, mock_auth_user):
        """Test VirusTotal endpoints require authentication"""
        indicator_data = {"indicator": "5d41402abc4b2a76b9719d911017c592"}
        
        with patch('backend.app.main.vt_call') as mock_vt:
            mock_vt.return_value = {"data": {"type": "file"}}
            
            headers = {"Authorization": "Bearer fake_token"}
            response = await async_client.post("/api/virustotal/file", json=indicator_data, headers=headers)
            
            assert response.status_code == status.HTTP_200_OK
            # Verify that vt_call was called with user credentials
            mock_vt.assert_called_once()

    async def test_unauthorized_access_to_protected_endpoints(self, async_client: httpx.AsyncClient):
        """Test that protected endpoints require authentication"""
        protected_endpoints = [
            ("/analyze", {"indicator": "test.com"}),
            ("/analyze/bulk", {"indicators": ["test.com"]}),
            ("/api/virustotal/file", {"indicator": "hash123"}),
            ("/api/visualize", {"indicator": "test.com"}),
        ]
        
        for endpoint, data in protected_endpoints:
            response = await async_client.post(endpoint, json=data)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_rate_limiting_bulk_analysis(self, async_client: httpx.AsyncClient, mock_auth_user):
        """Test rate limiting on bulk analysis"""
        # Try to analyze more than 100 indicators
        bulk_data = {
            "indicators": [f"test{i}.com" for i in range(101)]
        }
        
        headers = {"Authorization": "Bearer fake_token"}
        response = await async_client.post("/analyze/bulk", json=bulk_data, headers=headers)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Maximum 100 indicators" in response.json()["detail"]


@pytest.fixture
async def mock_auth_admin():
    """Mock authenticated admin user for testing"""
    from backend.app.auth import UserRole
    
    user = AsyncMock()
    user.username = "admin"
    user.email = "admin@example.com"
    user.role = UserRole.ADMIN
    user.is_active = True
    
    with patch('backend.app.main.get_current_user', return_value=user), \
         patch('backend.app.main.require_permission', return_value=True):
        yield user
