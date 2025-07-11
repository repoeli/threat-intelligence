import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models import ThreatIntelligenceResult, ThreatScore, IndicatorType, AnalysisStatus, ThreatLevel

class TestAdditionalEndpoints:
    def setup_method(self):
        self.client = TestClient(app)

    def _sample_result(self, indicator: str, indicator_type: IndicatorType):
        return ThreatIntelligenceResult(
            indicator=indicator,
            indicator_type=indicator_type,
            status=AnalysisStatus.COMPLETED,
            threat_score=ThreatScore(
                overall_score=0.1,
                confidence=0.9,
                threat_level=ThreatLevel.BENIGN,
                factors={}
            ),
            detection_ratio="0/0",
            reputation="clean",
            geolocation=None,
            whois_data=None,
            metadata={"analysis_id": "test"},
            raw_responses={}
        )

    def test_analyze_ip_endpoint(self):
        result = self._sample_result("1.1.1.1", IndicatorType.IP)
        with patch('backend.app.services.threat_analysis.threat_analysis_service.analyze_indicator', new=AsyncMock(return_value=result)) as mock_analyze, \
             patch('backend.app.services.database_service.db_service.store_analysis_result', new=AsyncMock()):
            resp = self.client.post('/analyze/ip/1.1.1.1')
            assert resp.status_code == 200
            data = resp.json()
            assert data['indicator'] == '1.1.1.1'
            mock_analyze.assert_awaited()

    def test_analyze_batch_endpoint(self):
        sample = self._sample_result("8.8.8.8", IndicatorType.IP)
        with patch('backend.app.services.threat_analysis.threat_analysis_service.analyze_indicator', new=AsyncMock(return_value=sample)) as mock_analyze, \
             patch('backend.app.services.database_service.db_service.store_analysis_result', new=AsyncMock()):
            payload = {"indicators": [{"value": "8.8.8.8"}, {"value": "1.1.1.1"}]}
            resp = self.client.post('/analyze/batch', json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert len(data['results']) == 2
            assert mock_analyze.await_count == 2
