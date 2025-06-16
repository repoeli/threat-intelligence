"""tests/test_app.py – core smoke‑tests (pytest‑asyncio).
Relies on fixtures in tests/conftest.py; no inline monkey‑patching.
Run: pytest -q
"""

import pytest
import httpx
import respx
from fastapi import status

# ───────────────────────────────────────────────────────────────────
# Health Check Tests
# ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint(async_client: httpx.AsyncClient):
    """Test the health check endpoint returns 200 OK."""
    response = await async_client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "OK"}

# ───────────────────────────────────────────────────────────────────
# VirusTotal Endpoint Tests
# ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_vt_file_endpoint(async_client: httpx.AsyncClient, mock_vt):
    """Test VirusTotal file analysis endpoint."""
    payload = {
        "indicator": "5d41402abc4b2a76b9719d911017c592",
        "user_id": "test-user-123",
        "subscription_level": "free"
    }
    response = await async_client.post("/api/virustotal/file", json=payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "data" in data
    assert data["data"]["type"] == "file"
    assert "last_analysis_stats" in data["data"]["attributes"]

@pytest.mark.asyncio
async def test_vt_ip_endpoint(async_client: httpx.AsyncClient, mock_vt):
    """Test VirusTotal IP analysis endpoint."""
    payload = {
        "indicator": "192.0.2.3",
        "user_id": "test-user-123",
        "subscription_level": "free"
    }
    response = await async_client.post("/api/virustotal/ip", json=payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "data" in data
    assert data["data"]["type"] == "ip_address"

@pytest.mark.asyncio
async def test_vt_domain_endpoint(async_client: httpx.AsyncClient, mock_vt):
    """Test VirusTotal domain analysis endpoint."""
    payload = {
        "indicator": "example.com",
        "user_id": "test-user-123",
        "subscription_level": "free"
    }
    response = await async_client.post("/api/virustotal/domain", json=payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "data" in data
    assert data["data"]["type"] == "domain"

@pytest.mark.asyncio
async def test_vt_url_endpoint(async_client: httpx.AsyncClient, mock_vt):
    """Test VirusTotal URL analysis endpoint."""
    payload = {
        "indicator": "https://example.com",
        "user_id": "test-user-123",
        "subscription_level": "free"
    }
    response = await async_client.post("/api/virustotal/url", json=payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "data" in data

# ───────────────────────────────────────────────────────────────────
# Analyze Endpoint Tests (Multi-source)
# ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_ip_merges_all_sources(async_client: httpx.AsyncClient, mock_all_services):
    """Test that /analyze endpoint merges all available threat intelligence sources for IP."""
    payload = {
        "indicator": "192.0.2.3",
        "user_id": "test-user-123",
        "subscription_level": "free"
    }
    response = await async_client.post("/analyze", json=payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Verify all expected sources are present
    expected_keys = {"virustotal", "abuseipdb", "openai_analysis"}
    assert expected_keys.issubset(set(data.keys()))
    
    # Verify data structure
    assert "data" in data["virustotal"]
    assert "data" in data["abuseipdb"]
    assert isinstance(data["openai_analysis"], str)

@pytest.mark.asyncio
async def test_analyze_domain(async_client: httpx.AsyncClient, mock_all_services):
    """Test analyze endpoint with domain indicator."""
    payload = {
        "indicator": "example.com",
        "user_id": "test-user-123",
        "subscription_level": "free"
    }
    response = await async_client.post("/analyze", json=payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "virustotal" in data
    assert "openai_analysis" in data

@pytest.mark.asyncio
async def test_analyze_hash(async_client: httpx.AsyncClient, mock_all_services):
    """Test analyze endpoint with file hash."""
    payload = {
        "indicator": "5d41402abc4b2a76b9719d911017c592",
        "user_id": "test-user-123",
        "subscription_level": "free"
    }
    response = await async_client.post("/analyze", json=payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "virustotal" in data
    assert "openai_analysis" in data

# ───────────────────────────────────────────────────────────────────
# Visualization Endpoint Tests
# ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_visualize_endpoint(async_client: httpx.AsyncClient, mock_all_services):
    """Test the visualization endpoint returns proper Chart.js configuration."""
    payload = {
        "indicator": "example.com",
        "user_id": "test-user-123",
        "subscription_level": "free"
    }
    response = await async_client.post("/api/visualize", json=payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Verify required keys
    required_keys = {"summary_markdown", "charts", "verdict"}
    assert set(data.keys()) == required_keys
    
    # Verify charts structure
    assert "analysis_stats" in data["charts"]
    assert "engine_donut" in data["charts"]
    
    # Verify chart types
    assert data["charts"]["analysis_stats"]["type"] == "bar"
    assert data["charts"]["engine_donut"]["type"] == "doughnut"

@pytest.mark.asyncio
async def test_visualize_ip_indicator(async_client: httpx.AsyncClient, mock_all_services):
    """Test visualization with IP indicator."""
    payload = {
        "indicator": "192.0.2.3",
        "user_id": "test-user-123",
        "subscription_level": "free"
    }
    response = await async_client.post("/api/visualize", json=payload)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["verdict"] == "benign"
    assert "### Analysis Summary" in data["summary_markdown"]

# ───────────────────────────────────────────────────────────────────
# Error Handling Tests
# ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("indicator,endpoint,expected_status", [
    ("not.an.ip.address", "/api/virustotal/ip", status.HTTP_400_BAD_REQUEST),
    ("invalid_domain_no_tld", "/api/virustotal/domain", status.HTTP_400_BAD_REQUEST),
    ("notahexhash", "/api/virustotal/file", status.HTTP_400_BAD_REQUEST),
    ("", "/api/virustotal/ip", status.HTTP_400_BAD_REQUEST),
    ("   ", "/api/virustotal/ip", status.HTTP_400_BAD_REQUEST),
])
@pytest.mark.asyncio
async def test_invalid_indicators(async_client: httpx.AsyncClient, indicator, endpoint, expected_status):
    """Test various invalid indicators return appropriate error codes."""
    payload = {
        "indicator": indicator,
        "user_id": "test-user-123",
        "subscription_level": "free"
    }
    response = await async_client.post(endpoint, json=payload)
    assert response.status_code == expected_status

@pytest.mark.asyncio
async def test_invalid_indicator_analyze(async_client: httpx.AsyncClient):
    """Test analyze endpoint with invalid indicator."""
    payload = {
        "indicator": "invalid!!indicator",
        "user_id": "test-user-123",
        "subscription_level": "free"
    }
    response = await async_client.post("/analyze", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.asyncio
async def test_missing_indicator_field(async_client: httpx.AsyncClient):
    """Test endpoints with missing indicator field."""
    response = await async_client.post("/api/virustotal/ip", json={})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

# ───────────────────────────────────────────────────────────────────
# URLScan Endpoint Tests
# ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_urlscan_scan_endpoint(async_client: httpx.AsyncClient):
    """Test URLScan scan submission endpoint."""
    with respx.mock(base_url="https://urlscan.io") as urlscan_mock:
        urlscan_mock.post("/api/v1/scan/").respond(200, json={
            "message": "Submission successful",
            "uuid": "test-uuid"
        })
        
        payload = {"url": "https://example.com"}
        response = await async_client.post("/api/urlscan/scan", json=payload)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "uuid" in data

@pytest.mark.asyncio
async def test_urlscan_result_endpoint(async_client: httpx.AsyncClient):
    """Test URLScan result retrieval endpoint."""
    with respx.mock(base_url="https://urlscan.io") as urlscan_mock:
        urlscan_mock.get("/api/v1/result/test-uuid").respond(200, json={
            "task": {"uuid": "test-uuid"},
            "page": {"url": "https://example.com"}
        })
        
        response = await async_client.get("/api/urlscan/result/test-uuid")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["task"]["uuid"] == "test-uuid"

# ───────────────────────────────────────────────────────────────────
# Integration Tests
# ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_workflow_ip_analysis(async_client: httpx.AsyncClient, mock_all_services):
    """Test complete workflow: analyze IP -> visualize results."""
    ip_indicator = "192.0.2.3"
      # Step 1: Analyze the IP
    analyze_response = await async_client.post("/analyze", json={
        "indicator": ip_indicator,
        "user_id": "test-user-123",
        "subscription_level": "free"
    })
    assert analyze_response.status_code == status.HTTP_200_OK
    
    # Step 2: Visualize the results
    viz_response = await async_client.post("/api/visualize", json={
        "indicator": ip_indicator,
        "user_id": "test-user-123",
        "subscription_level": "free"
    })
    assert viz_response.status_code == status.HTTP_200_OK
    
    viz_data = viz_response.json()
    assert viz_data["verdict"] == "benign"
    assert "charts" in viz_data

@pytest.mark.asyncio
async def test_concurrent_requests_different_indicators(async_client: httpx.AsyncClient, mock_all_services):
    """Test concurrent requests with different indicators."""
    import asyncio    
    indicators = [
        "192.0.2.3",
        "example.com", 
        "5d41402abc4b2a76b9719d911017c592"
    ]
    
    async def analyze_indicator(indicator):
        return await async_client.post("/analyze", json={
            "indicator": indicator,
            "user_id": "test-user-123",
            "subscription_level": "free"
        })
    
    tasks = [analyze_indicator(ind) for ind in indicators]
    responses = await asyncio.gather(*tasks)
    
    # All requests should succeed
    for response in responses:
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "virustotal" in data
        assert "openai_analysis" in data