# tests/test_analyze_full.py
import pytest, httpx, json
from fastapi import status

@pytest.mark.asyncio
async def test_analyze_merges_all_sources(async_client: httpx.AsyncClient, mock_all_services):
    """Test that /analyze endpoint merges all available threat intelligence sources for IP."""
    resp = await async_client.post("/analyze", json={
        "indicator": "192.0.2.3",
        "user_id": "test-user-123",
        "subscription_level": "free"
    })
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    
    # Verify all expected sources are present
    expected_keys = {"virustotal", "abuseipdb", "openai_analysis"}
    assert expected_keys.issubset(set(data.keys()))
    
    # Verify data structure
    assert "data" in data["virustotal"]
    assert "data" in data["abuseipdb"]
    assert isinstance(data["openai_analysis"], str)
