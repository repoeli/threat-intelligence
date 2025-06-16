# tests/test_upstream_failure.py
import pytest, httpx
from fastapi import status

@pytest.mark.asyncio
async def test_vt_failure_returns_502(async_client: httpx.AsyncClient, monkeypatch):
    async def _raise(*_a, **_kw):
        raise Exception("VT outage")

    monkeypatch.setattr("backend.app.main.vt_call", _raise)
    
    resp = await async_client.post(
        "/api/virustotal/file",
        json={
            "indicator": "5d41402abc4b2a76b9719d911017c592",
            "user_id": "test-user-123",
            "subscription_level": "free"
        },
    )
    assert resp.status_code == status.HTTP_502_BAD_GATEWAY
    body = resp.json()
    assert body.keys() >= {"error", "ts"}