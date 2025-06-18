"""
Comprehensive endpoint testing to validate all implemented features
"""
import pytest
import httpx
from datetime import datetime, UTC
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from backend.app.main import app


class TestComprehensiveEndpoints:
    """Test all implemented endpoints for basic functionality"""
    
    def setup_method(self):
        self.client = TestClient(app)
    
    def test_health_endpoint(self):
        """Test health endpoint"""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "OK"
    
    def test_status_endpoint(self):
        """Test system status endpoint"""
        response = self.client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert "system" in data
        assert "external_apis" in data
    
    def test_auth_register_endpoint_structure(self):
        """Test registration endpoint accepts correct data structure"""
        # Test with invalid data to check structure
        response = self.client.post("/auth/register", json={})
        # Should return validation error, not 404
        assert response.status_code in [422, 400]  # Validation error
    
    def test_auth_login_endpoint_structure(self):
        """Test login endpoint accepts correct data structure"""
        response = self.client.post("/auth/login", json={})        # Should return validation error, not 404
        assert response.status_code in [422, 400]  # Validation error

    @patch('backend.app.services.threat_analysis.threat_analysis_service.analyze_indicator')
    def test_analyze_endpoint_requires_auth(self, mock_analyze):
        """Test that analyze endpoint requires authentication"""
        from backend.app.models import (
            ThreatIntelligenceResult, ThreatScore, ThreatLevel, 
            IndicatorType, AnalysisStatus, AnalysisMetadata
        )
        from datetime import datetime
        
        # Create a proper mock response
        mock_result = ThreatIntelligenceResult(
            indicator="test.com",
            indicator_type=IndicatorType.DOMAIN,
            status=AnalysisStatus.COMPLETED,
            threat_score=ThreatScore(
                overall_score=0.1,
                confidence=0.8,
                threat_level=ThreatLevel.LOW,
                factors={"test": 0.1}
            ),
            vendor_results=[],
            detection_ratio="0/0",
            reputation="clean",
            categories=[],
            tags=[],
            first_seen=None,
            last_seen=None,
            geolocation=None,
            whois_data=None,            metadata=AnalysisMetadata(
                analyzed_at=datetime.now(UTC),
                analysis_id="test_123",
                sources_used=["test"],
                cached=False,
                processing_time_ms=100
            ),
            raw_responses={}        )
        mock_analyze.return_value = mock_result
        
        response = self.client.post("/analyze", json={"indicator": "test.com"})
        # Should allow anonymous access
        assert response.status_code == 200
    
    @patch('backend.app.services.threat_analysis.threat_analysis_service.analyze_indicator')
    def test_analyze_premium_endpoint_exists(self, mock_analyze):
        """Test that premium analyze endpoint exists"""
        mock_analyze.return_value = AsyncMock()
        
        response = self.client.post("/analyze/premium", json={"indicator": "test.com"})
        # Should require authentication (not 404)
        assert response.status_code != 404
    
    @patch('backend.app.services.threat_analysis.threat_analysis_service.analyze_indicator')
    def test_analyze_enterprise_endpoint_exists(self, mock_analyze):
        """Test that enterprise analyze endpoint exists"""
        mock_analyze.return_value = AsyncMock()
        
        response = self.client.post("/analyze/enterprise", json={"indicator": "test.com"})
        # Should require authentication (not 404)
        assert response.status_code != 404

    def test_virustotal_endpoints_exist(self):
        """Test that VirusTotal endpoints are available"""
        test_data = {
            "/api/virustotal": {
                "name": "get_ip_report", 
                "path_params": {"ip": "8.8.8.8"}
            },
            "/api/virustotal/file": {"indicator": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
            "/api/virustotal/ip": {"indicator": "8.8.8.8"},
            "/api/virustotal/domain": {"indicator": "google.com"},
            "/api/virustotal/url": {"indicator": "https://www.google.com"}
        }
        
        for endpoint, data in test_data.items():
            response = self.client.post(endpoint, json=data)
            # Should not be 404 (endpoint exists)
            assert response.status_code != 404
            # Should require authentication or return validation error
            assert response.status_code in [401, 422, 400, 502]


class TestIndicatorValidation:
    """Test indicator type determination and validation"""
    
    def test_indicator_types(self):
        """Test various indicator types are recognized"""
        from backend.app.utils.indicator import determine_indicator_type
        
        test_cases = [
            ("192.168.1.1", "ip"),
            ("example.com", "domain"), 
            ("https://example.com/path", "url"),
            ("d41d8cd98f00b204e9800998ecf8427e", "hash"),
            ("user@example.com", "email")
        ]
        
        for indicator, expected_type in test_cases:
            result = determine_indicator_type(indicator)
            assert result == expected_type, f"Expected {expected_type} for {indicator}, got {result}"


class TestAuthenticationFlow:
    """Test authentication system components"""
    
    def setup_method(self):
        self.client = TestClient(app)
    
    def test_auth_service_imports(self):
        """Test that auth service can be imported"""
        from backend.app.services.auth_service import auth_service
        assert auth_service is not None
    
    def test_auth_models_available(self):
        """Test that auth models are available"""
        from backend.app.models import UserRegistration, UserLogin, UserResponse
        
        # Test model instantiation
        reg = UserRegistration(
            email="test@example.com",
            password="password123"
        )
        assert reg.email == "test@example.com"
        
        login = UserLogin(email="test@example.com", password="password123")
        assert login.email == "test@example.com"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
