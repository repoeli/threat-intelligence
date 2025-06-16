# tests/conftest.py
import os
import asyncio
import pytest
import pytest_asyncio
import httpx
from unittest.mock import AsyncMock, patch

# ──────────────────────────────────────────────────────────────
# Put fake keys in the env *before* any backend import happens
# ──────────────────────────────────────────────────────────────
os.environ.setdefault("VT_API_KEY", "dummy_vt_key_for_testing")
os.environ.setdefault("OPENAI_API_KEY", "dummy_openai_key_for_testing")
os.environ.setdefault("ABUSEIPDB_API_KEY", "dummy_abuse_key_for_testing")
os.environ.setdefault("URLSCAN_API_KEY", "dummy_urlscan_key_for_testing")

# Global Redis mock setup to prevent Redis connection issues
class MockRedis:
    def __init__(self):
        self.data = {}
    
    async def incr(self, key):
        self.data[key] = self.data.get(key, 0) + 1
        return self.data[key]
    
    async def expire(self, key, seconds):
        return True
    
    async def get(self, key):
        return self.data.get(key)

_mock_redis_instance = MockRedis()

async def mock_redis_factory():
    return _mock_redis_instance

# Apply Redis mock globally before any imports
import backend.app.services.virustotal_service
backend.app.services.virustotal_service._r = mock_redis_factory

# ──────────────────────────────────────────────────────────────
# Now import the FastAPI app
# ──────────────────────────────────────────────────────────────
from backend.app.main import app

# ──────────────────────────────────────────────────────────────
# Async client fixture (httpx 0.25+ compatible)
# ──────────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def async_client():
    """
    Async httpx client wired to the FastAPI app.
    Uses ASGITransport for testing FastAPI applications.
    """
    transport = httpx.ASGITransport(app=app)
    
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test"
    ) as client:
        yield client

# ──────────────────────────────────────────────────────────────
# VirusTotal proxy stub (makes every VT call predictable)
# ──────────────────────────────────────────────────────────────
@pytest.fixture
def mock_vt(monkeypatch):
    """Mock VirusTotal API calls to return predictable responses."""
    async def _stub_vt_call(uid: str, tier: str, name: str, **kwargs):
        # Return different responses based on the endpoint
        if name == "get_file_report":
            return {
                "data": {
                    "id": kwargs.get("path_params", {}).get("file_id", "dummy_file_id"),
                    "type": "file",
                    "attributes": {
                        "last_analysis_stats": {
                            "malicious": 0,
                            "suspicious": 1,
                            "undetected": 60,
                            "harmless": 2
                        },
                        "sha256": "dummy_sha256",
                        "md5": "dummy_md5"
                    }
                }
            }
        elif name == "get_ip_report":
            return {
                "data": {
                    "id": kwargs.get("path_params", {}).get("ip", "192.0.2.3"),
                    "type": "ip_address",
                    "attributes": {
                        "last_analysis_stats": {"malicious": 0, "harmless": 5},
                        "country": "US",
                        "as_owner": "Test ASN"
                    }
                }
            }
        elif name == "get_domain_report":
            return {
                "data": {
                    "id": kwargs.get("path_params", {}).get("domain", "example.com"),
                    "type": "domain",
                    "attributes": {
                        "last_analysis_stats": {"malicious": 0, "harmless": 8},
                        "registrar": "Test Registrar"
                    }
                }
            }
        elif name == "get_url_report":
            return {
                "data": {
                    "id": kwargs.get("path_params", {}).get("url_id", "dummy_url_id"),
                    "type": "url",
                    "attributes": {
                        "last_analysis_stats": {"malicious": 0, "harmless": 10}
                    }
                }
            }
        elif name == "scan_url":
            return {
                "data": {
                    "type": "analysis",
                    "id": "dummy_analysis_id"
                }
            }
        else:
            # Generic response for unknown endpoints
            return {
                "data": {
                    "id": "dummy_generic_id",
                    "type": "generic",
                    "attributes": {"last_analysis_stats": {"malicious": 0}}
                }
            }

    # Patch the vt_call function from the service module
    monkeypatch.setattr("backend.app.services.virustotal_service.vt_call", _stub_vt_call)
    # Also patch it in main module if imported there
    monkeypatch.setattr("backend.app.main.vt_call", _stub_vt_call)
    return _stub_vt_call

# ──────────────────────────────────────────────────────────────
# AbuseIPDB stub
# ──────────────────────────────────────────────────────────────
@pytest.fixture
def mock_abuseipdb(monkeypatch):
    """Mock AbuseIPDB API calls."""
    async def _stub_abuseipdb(ip: str):
        return {
            "data": {
                "ipAddress": ip,
                "abuseConfidenceScore": 0,
                "countryCode": "US",
                "usageType": "Data Center/Web Hosting/Transit",
                "totalReports": 0
            }
        }
    
    monkeypatch.setattr("backend.app.main._call_abuseipdb", _stub_abuseipdb)
    return _stub_abuseipdb

# ──────────────────────────────────────────────────────────────
# OpenAI helper stubs (analysis + visualisation)
# ──────────────────────────────────────────────────────────────
@pytest.fixture
def mock_openai(monkeypatch):
    """Mock OpenAI API calls for analysis and visualization."""
    async def _stub_openai_analysis(*args, **kwargs):
        return "Based on the analysis, this indicator appears benign with no immediate security concerns. No further action required at this time."

    async def _stub_openai_visualize(*args, **kwargs):
        return {
            "summary_markdown": "### Analysis Summary\n\nThe indicator shows no malicious activity based on available threat intelligence sources.",
            "verdict": "benign",
            "charts": {
                "analysis_stats": {
                    "type": "bar",
                    "data": {
                        "labels": ["Malicious", "Suspicious", "Harmless", "Undetected"],
                        "datasets": [{
                            "label": "Detection Count",
                            "data": [0, 1, 5, 60],
                            "backgroundColor": ["#ff6384", "#ff9f40", "#36a2eb", "#c9cbcf"]
                        }]
                    }
                },
                "engine_donut": {
                    "type": "doughnut",
                    "data": {
                        "labels": ["Clean", "Suspicious"],
                        "datasets": [{
                            "data": [65, 1],
                            "backgroundColor": ["#36a2eb", "#ff9f40"]
                        }]
                    }
                }
            }
        }

    monkeypatch.setattr("backend.app.main._call_openai", _stub_openai_analysis)
    monkeypatch.setattr("backend.app.main._openai_visualize", _stub_openai_visualize)
    return {"analysis": _stub_openai_analysis, "visualize": _stub_openai_visualize}

# ──────────────────────────────────────────────────────────────
# URLScan stub
# ──────────────────────────────────────────────────────────────
@pytest.fixture
def mock_urlscan(monkeypatch):
    """Mock URLScan API calls."""
    async def _stub_urlscan_result(scan_id: str):
        return {
            "task": {"uuid": scan_id},
            "page": {
                "url": "https://example.com",
                "domain": "example.com",
                "country": "US",
                "server": "nginx"
            },
            "stats": {
                "malicious": 0,
                "suspicious": 0
            }
        }
    
    monkeypatch.setattr("backend.app.main.urlscan_result", _stub_urlscan_result)
    return _stub_urlscan_result

# ──────────────────────────────────────────────────────────────
# Composite fixture for full testing
# ──────────────────────────────────────────────────────────────
@pytest.fixture
def mock_all_services(mock_vt, mock_abuseipdb, mock_openai, mock_urlscan):
    """Convenience fixture that enables all service mocks."""
    return {
        "vt": mock_vt,
        "abuseipdb": mock_abuseipdb,
        "openai": mock_openai,
        "urlscan": mock_urlscan
    }

# ──────────────────────────────────────────────────────────────
# Available fixtures: _class_event_loop, _function_event_loop, _module_event_loop, _package_event_loop, _session_event_loop, anyio_backend, anyio_backend_name, anyio_backend_options, async_client, cache, capfd, capfdbinary, caplog, capsys, capsysbinary, capteesys, doctest_namespace, event_loop_policy, free_tcp_port, free_tcp_port_factory, free_udp_port, free_udp_port_factory, mock_vt_client, monkeypatch, pytestconfig, record_property, record_testsuite_property, record_xml_attribute, recwarn, respx_mock, tmp_path, tmp_path_factory, tmpdir, tmpdir_factory, unused_tcp_port, unused_tcp_port_factory, unused_udp_port, unused_udp_port_factory
