# tests/conftest.py
import os
import asyncio
import pytest
import pytest_asyncio
import httpx
from unittest.mock import AsyncMock, patch

# Set environment variables BEFORE any imports
os.environ.setdefault("VIRUSTOTAL_API_KEY", "dummy_vt_key_for_testing")
os.environ.setdefault("OPENAI_API_KEY", "dummy_openai_key_for_testing")
os.environ.setdefault("ABUSEIPDB_API_KEY", "dummy_abuse_key_for_testing")
os.environ.setdefault("URLSCAN_API_KEY", "dummy_urlscan_key_for_testing")

# Global Redis mock to prevent connection issues
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

# Apply Redis mock globally before imports
import backend.app.services.virustotal_service
backend.app.services.virustotal_service._r = mock_redis_factory

# Now import the FastAPI app
from backend.app.main import app

@pytest_asyncio.fixture
async def async_client():
    """AsyncClient with ASGITransport for FastAPI testing."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

@pytest.fixture
def mock_vt(monkeypatch):
    """Mock VirusTotal API calls."""
    async def _stub_vt_call(uid: str, tier: str, name: str, **kwargs):
        if name == "get_file_report":
            return {
                "data": {
                    "id": kwargs.get("path_params", {}).get("file_id", "dummy_file_id"),
                    "type": "file",
                    "attributes": {
                        "last_analysis_stats": {"malicious": 0, "suspicious": 1, "undetected": 60, "harmless": 2},
                        "sha256": "dummy_sha256"
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
                        "country": "US"
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
                    "attributes": {"last_analysis_stats": {"malicious": 0, "harmless": 10}}
                }
            }
        else:
            return {"data": {"id": "dummy_id", "type": "generic", "attributes": {"last_analysis_stats": {"malicious": 0}}}}

    monkeypatch.setattr("backend.app.services.virustotal_service.vt_call", _stub_vt_call)
    return _stub_vt_call

@pytest.fixture
def mock_openai(monkeypatch):
    """Mock OpenAI API calls."""
    async def _stub_openai_analysis(*args, **kwargs):
        return "Analysis indicates benign behavior with no immediate threats detected."

    async def _stub_openai_visualize(*args, **kwargs):
        return {
            "summary_markdown": "### Analysis Summary\n\nIndicator appears benign based on threat intelligence.",
            "verdict": "benign",
            "charts": {
                "analysis_stats": {
                    "type": "bar",
                    "data": {
                        "labels": ["Malicious", "Suspicious", "Harmless", "Undetected"],
                        "datasets": [{"label": "Detection Count", "data": [0, 1, 5, 60]}]
                    }
                },
                "engine_donut": {
                    "type": "doughnut",
                    "data": {"labels": ["Clean", "Suspicious"], "datasets": [{"data": [65, 1]}]}
                }
            }
        }

    monkeypatch.setattr("backend.app.main._call_openai", _stub_openai_analysis)
    monkeypatch.setattr("backend.app.main._openai_visualize", _stub_openai_visualize)
    return {"analysis": _stub_openai_analysis, "visualize": _stub_openai_visualize}

@pytest.fixture
def mock_abuseipdb(monkeypatch):
    """Mock AbuseIPDB API calls."""
    async def _stub_abuseipdb(ip: str):
        return {
            "data": {
                "ipAddress": ip,
                "abuseConfidenceScore": 0,
                "countryCode": "US",
                "totalReports": 0
            }
        }
    
    monkeypatch.setattr("backend.app.main._call_abuseipdb", _stub_abuseipdb)
    return _stub_abuseipdb

@pytest.fixture
def mock_all_services(mock_vt, mock_abuseipdb, mock_openai):
    """Convenience fixture enabling all service mocks."""
    return {"vt": mock_vt, "abuseipdb": mock_abuseipdb, "openai": mock_openai}


# ═══════════════════════════ NEW AUTHENTICATION FIXTURES ═══════════════════════════

@pytest.fixture
def mock_auth_user():
    """Mock authenticated regular user for testing"""
    from backend.app.models import SubscriptionTier
    
    user_data = {
        "user_id": "test_user",
        "subscription": "free",
        "permissions": [],
        "subscription_tier": SubscriptionTier.FREE
    }
    
    with patch('backend.app.main.get_current_user', return_value=user_data):
        yield user_data


@pytest.fixture
def mock_auth_analyst():
    """Mock authenticated analyst user for testing"""
    from backend.app.auth import User, UserRole
    from datetime import datetime
    
    user = User(
        username="analyst",
        email="analyst@example.com", 
        password_hash="hashed_password",
        role=UserRole.ANALYST,
        is_active=True,
        created_at=datetime.utcnow()
    )
    
    with patch('backend.app.main.get_current_user', return_value=user), \
         patch('backend.app.main.require_permission', return_value=True):
        yield user


@pytest.fixture
def mock_auth_admin():
    """Mock authenticated admin user for testing"""
    from backend.app.models import SubscriptionTier
    
    admin_data = {
        "user_id": "admin_user",
        "subscription": "admin",
        "permissions": ["admin", "read", "write"],
        "subscription_tier": SubscriptionTier.PLUS
    }
    
    with patch('backend.app.main.get_current_user', return_value=admin_data), \
         patch('backend.app.main.require_permission', return_value=True):
        yield admin_data


@pytest.fixture
def mock_database():
    """Mock database operations for testing"""
    # This would mock database operations if we had a real database
    # For now, just provide a placeholder
    mock_db = AsyncMock()
    mock_db.users = AsyncMock()
    mock_db.analyses = AsyncMock()
    mock_db.historical_data = AsyncMock()
    
    yield mock_db


@pytest.fixture
def performance_test_data():
    """Generate test data for performance testing"""
    return {
        "indicators": {
            "ips": ["8.8.8.8", "1.1.1.1", "192.168.1.1", "10.0.0.1"],
            "domains": ["example.com", "google.com", "test.com", "malware.example"],
            "urls": ["https://example.com/test", "http://malware.example/payload"],
            "hashes": [
                "5d41402abc4b2a76b9719d911017c592",
                "098f6bcd4621d373cade4e832627b4f6", 
                "e3b0c44298fc1c149afbf4c8996fb924"
            ]
        },
        "expected_response_times": {
            "health": 0.1,
            "auth": 0.5,
            "analysis": 2.0,
            "bulk_analysis": 10.0
        }
    }


@pytest.fixture
def integration_test_config():
    """Configuration for integration tests"""
    return {
        "test_timeout": 30,
        "max_concurrent_requests": 50,
        "rate_limit_test_count": 100,
        "bulk_analysis_max_size": 100
    }


# ═══════════════════════════ PYTEST CONFIGURATION ═══════════════════════════

def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "benchmark: mark test as a benchmark test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "auth: mark test as requiring authentication"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names"""
    for item in items:
        # Add markers based on test file names
        if "test_performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
        if "test_auth" in str(item.fspath):
            item.add_marker(pytest.mark.auth)
        if "test_enhanced_analysis" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add markers based on test function names
        if "benchmark" in item.name:
            item.add_marker(pytest.mark.benchmark)


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Automatically setup test environment for all tests"""
    # Ensure all required environment variables are set
    required_env_vars = {
        "VIRUSTOTAL_API_KEY": "dummy_vt_key_for_testing",
        "OPENAI_API_KEY": "dummy_openai_key_for_testing", 
        "ABUSEIPDB_API_KEY": "dummy_abuse_key_for_testing",
        "URLSCAN_API_KEY": "dummy_urlscan_key_for_testing",
        "JWT_SECRET_KEY": "test_jwt_secret_key_for_testing_only",
        "JWT_ALGORITHM": "HS256",
        "JWT_EXPIRE_MINUTES": "1440"
    }
    
    for var, value in required_env_vars.items():
        if not os.environ.get(var):
            os.environ[var] = value
    
    yield
    
    # Cleanup if needed
    pass


@pytest.fixture
def sample_analysis_data():
    """Sample data for analysis testing"""
    return {
        "virustotal_response": {
            "data": {
                "type": "domain",
                "id": "example.com",
                "attributes": {
                    "last_analysis_stats": {
                        "malicious": 2,
                        "clean": 83,
                        "suspicious": 1,
                        "undetected": 4
                    },
                    "reputation": 5,
                    "registrar": "Example Registrar Inc.",
                    "creation_date": 1234567890
                }
            }
        },
        "abuseipdb_response": {
            "data": {
                "ipAddress": "192.168.1.1",
                "abuseConfidencePercentage": 0,
                "countryCode": "US",
                "totalReports": 0,
                "isPublic": False            }
        },
        "openai_response": "Analysis indicates this is a benign indicator with low risk profile"
    }
