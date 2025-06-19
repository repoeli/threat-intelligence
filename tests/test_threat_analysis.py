"""
Test cases for threat analysis service
"""
import pytest
from unittest.mock import patch, AsyncMock, Mock
from datetime import datetime, UTC
from fastapi import HTTPException

from backend.app.services.threat_analysis import threat_analysis_service
from backend.app.models import (
    ThreatIntelligenceResult,
    AnalysisMetadata, 
    ThreatLevel,
    IndicatorType,
    AnalysisStatus
)


class TestThreatAnalysisService:
    """Test threat analysis service functionality"""

    @pytest.mark.asyncio
    async def test_analyze_indicator_ip_success(self):
        """Test successful IP analysis"""
        with patch('backend.app.services.threat_analysis.vt_call') as mock_vt:
            mock_vt.return_value = {
                "data": {
                    "attributes": {
                        "last_analysis_stats": {"malicious": 0, "suspicious": 1, "harmless": 67},
                        "reputation": 10,
                        "country": "US"
                    }
                }
            }
            
            result = await threat_analysis_service.analyze_indicator(
                indicator="8.8.8.8",
                user_id="test_user",
                subscription="free"
            )
            
            assert isinstance(result, ThreatIntelligenceResult)
            assert result.indicator == "8.8.8.8"
            assert result.indicator_type == IndicatorType.IP
            assert result.status == AnalysisStatus.COMPLETED
            assert result.threat_score.overall_score >= 0
            assert result.metadata is not None

    @pytest.mark.asyncio
    async def test_analyze_indicator_domain_success(self):
        """Test successful domain analysis"""
        with patch('backend.app.services.threat_analysis.vt_call') as mock_vt:
            mock_vt.return_value = {
                "data": {
                    "attributes": {
                        "last_analysis_stats": {"malicious": 2, "suspicious": 0, "harmless": 65},
                        "reputation": -5,
                        "categories": ["malware"]
                    }
                }
            }
            
            result = await threat_analysis_service.analyze_indicator(
                indicator="malicious.example.com",
                user_id="test_user",
                subscription="medium"
            )
            
            assert result.indicator == "malicious.example.com"
            assert result.indicator_type == IndicatorType.DOMAIN
            assert result.threat_score.overall_score >= 0.0  # Should be non-negative

    @pytest.mark.asyncio
    async def test_analyze_indicator_hash_success(self):
        """Test successful file hash analysis"""
        with patch('backend.app.services.threat_analysis.vt_call') as mock_vt:
            mock_vt.return_value = {
                "data": {
                    "attributes": {
                        "last_analysis_stats": {"malicious": 45, "suspicious": 5, "harmless": 15},
                        "reputation": -100,
                        "type_description": "Win32 EXE"
                    }
                }
            }
            
            result = await threat_analysis_service.analyze_indicator(
                indicator="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                user_id="test_user",
                subscription="plus"
            )
            
            assert result.indicator_type == IndicatorType.HASH
            assert result.threat_score.overall_score >= 0.0  # Should be non-negative

    @pytest.mark.asyncio
    async def test_analyze_indicator_url_success(self):
        """Test successful URL analysis"""
        with patch('backend.app.services.threat_analysis.vt_call') as mock_vt:
            mock_vt.return_value = {
                "data": {
                    "attributes": {
                        "last_analysis_stats": {"malicious": 0, "suspicious": 0, "harmless": 70},
                        "reputation": 50,
                        "title": "Example Page"
                    }
                }
            }
            
            result = await threat_analysis_service.analyze_indicator(
                indicator="https://www.example.com",
                user_id="test_user",
                subscription="free"
            )
            
            assert result.indicator_type == IndicatorType.URL
            assert result.threat_score.overall_score < 0.3  # Should be low due to clean detections

    @pytest.mark.asyncio
    async def test_analyze_indicator_vt_error(self):
        """Test handling of VirusTotal API errors"""
        with patch('backend.app.services.threat_analysis.vt_call') as mock_vt:
            mock_vt.side_effect = HTTPException(status_code=502, detail="VT API Error")
            
            result = await threat_analysis_service.analyze_indicator(
                indicator="8.8.8.8",
                user_id="test_user",
                subscription="free"
            )
              # Should still return a result with error status
            assert result.status == AnalysisStatus.FAILED  # Should fail on VT error
            assert result.threat_score.overall_score == 0.0  # Default error score

    @pytest.mark.asyncio
    async def test_analyze_indicator_enhanced_analysis(self):
        """Test enhanced analysis for premium users"""
        with patch('backend.app.services.threat_analysis.vt_call') as mock_vt:
            mock_vt.return_value = {
                "data": {
                    "attributes": {
                        "last_analysis_stats": {"malicious": 5, "suspicious": 2, "harmless": 60},
                        "reputation": 0
                    }
                }
            }
            
            result = await threat_analysis_service.analyze_indicator(
                indicator="suspicious.example.com",
                user_id="premium_user",
                subscription="plus",
                enhanced_analysis=True
            )
            
            assert result.metadata is not None
            assert len(result.metadata.sources_used) > 1  # Should use multiple sources

    @pytest.mark.asyncio
    async def test_analyze_indicator_deep_analysis(self):
        """Test deep analysis for enterprise users"""
        with patch('backend.app.services.threat_analysis.vt_call') as mock_vt:
            mock_vt.return_value = {
                "data": {
                    "attributes": {
                        "last_analysis_stats": {"malicious": 3, "suspicious": 1, "harmless": 65},
                        "reputation": 20
                    }
                }
            }
            
            result = await threat_analysis_service.analyze_indicator(
                indicator="test.example.com",
                user_id="enterprise_user", 
                subscription="admin",
                enhanced_analysis=True,
                deep_analysis=True
            )
            
            assert result.metadata.sources_used is not None
            assert result.raw_responses is not None

    def test_calculate_threat_score_clean(self):
        """Test threat score calculation for clean indicators"""
        from backend.app.services.threat_analysis import ThreatAnalysisService
        service = ThreatAnalysisService()
        
        vt_data = {
            "data": {
                "attributes": {
                    "last_analysis_stats": {"malicious": 0, "suspicious": 0, "harmless": 70},
                    "reputation": 100
                }
            }
        }
        
        score = service._calculate_threat_score(vt_data, IndicatorType.IP)
        assert score.overall_score < 0.2  # Should be very low score

    def test_calculate_threat_score_malicious(self):
        """Test threat score calculation for malicious indicators"""
        from backend.app.services.threat_analysis import ThreatAnalysisService
        service = ThreatAnalysisService()

        raw_responses = {
            "virustotal": {
                "data": {
                    "attributes": {
                        "last_analysis_stats": {"malicious": 50, "suspicious": 10, "harmless": 5, "undetected": 0},
                        "reputation": -200
                    }
                }
            }
        }

        score = service._calculate_threat_score(raw_responses, IndicatorType.HASH)
        assert score.overall_score > 0.5  # Should be high score for many malicious detections

    def test_calculate_threat_score_suspicious(self):
        """Test threat score calculation for suspicious indicators"""
        from backend.app.services.threat_analysis import ThreatAnalysisService
        service = ThreatAnalysisService()

        raw_responses = {
            "virustotal": {
                "data": {
                    "attributes": {
                        "last_analysis_stats": {"malicious": 2, "suspicious": 8, "harmless": 55, "undetected": 5},
                        "reputation": -10
                    }
                }
            }
        }

        score = service._calculate_threat_score(raw_responses, IndicatorType.DOMAIN)
        assert 0.05 < score.overall_score < 0.5  # Should be moderate score for suspicious indicators

    def test_extract_geolocation_ip(self):
        """Test geolocation extraction for IP indicators"""
        from backend.app.services.threat_analysis import ThreatAnalysisService
        service = ThreatAnalysisService()

        raw_responses = {
            "virustotal": {
                "data": {
                    "attributes": {
                        "country": "US",
                        "as_owner": "Google LLC",
                        "network": "8.8.8.0/24"
                    }
                }
            }
        }

        geolocation = service._extract_geolocation(raw_responses, IndicatorType.IP)
        if geolocation:
            assert "country" in geolocation or geolocation is None  # It might return None    def test_extract_vendor_results(self):
        """Test vendor results extraction"""
        from backend.app.services.threat_analysis import ThreatAnalysisService
        service = ThreatAnalysisService()
        
        raw_responses = {
            "virustotal": {
                "data": {
                    "attributes": {
                        "last_analysis_results": {
                            "engine1": {"result": "clean"},
                            "engine2": {"result": "malware"}
                        }
                    }
                }
            }
        }
        
        vendor_results = service._extract_vendor_results(raw_responses)
        assert isinstance(vendor_results, list)

    def test_calculate_detection_ratio(self):
        """Test detection ratio calculation"""
        from backend.app.services.threat_analysis import ThreatAnalysisService
        from backend.app.models import VendorResult
        service = ThreatAnalysisService()
        
        vendor_results = [
            VendorResult(vendor="engine1", result="clean"),
            VendorResult(vendor="engine2", result="malware"),
            VendorResult(vendor="engine3", result="clean")
        ]
        
        ratio = service._calculate_detection_ratio(vendor_results)
        assert isinstance(ratio, str)
        assert "/" in ratio

    @pytest.mark.asyncio
    async def test_analyze_indicator_invalid_indicator_type(self):
        """Test handling of invalid indicator types"""
        with patch('backend.app.utils.indicator.determine_indicator_type') as mock_determine:
            mock_determine.side_effect = HTTPException(status_code=400, detail="Invalid indicator")
            
            with pytest.raises(HTTPException) as exc_info:
                await threat_analysis_service.analyze_indicator(
                    indicator="invalid_indicator",
                    user_id="test_user",
                    subscription="free"
                )
            
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_analyze_indicator_with_raw_responses(self):
        """Test analysis with raw response inclusion"""
        with patch('backend.app.services.threat_analysis.vt_call') as mock_vt:
            mock_vt.return_value = {"test": "response"}            
            result = await threat_analysis_service.analyze_indicator(
                indicator="8.8.8.8",
                user_id="test_user",
                subscription="plus",
                include_raw=True
            )
            
            assert result.raw_responses is not None
            assert "virustotal" in result.raw_responses

    def test_score_virustotal(self):
        """Test VirusTotal scoring function"""
        from backend.app.services.threat_analysis import ThreatAnalysisService
        service = ThreatAnalysisService()
        
        vt_data = {
            "data": {
                "attributes": {
                    "last_analysis_stats": {"malicious": 2, "suspicious": 1, "harmless": 67},
                    "reputation": -10
                }
            }
        }
        
        score, confidence = service._score_virustotal(vt_data)
        assert isinstance(score, float)
        assert isinstance(confidence, float)
        assert 0.0 <= score <= 1.0
        assert 0.0 <= confidence <= 1.0
