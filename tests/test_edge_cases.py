# tests/test_edge_cases.py
import pytest, httpx
from fastapi import status

@pytest.mark.parametrize(
    "indicator, expected",
    [
        ("",         status.HTTP_400_BAD_REQUEST),   # empty
        ("   ",      status.HTTP_400_BAD_REQUEST),   # whitespace  
        (None,       status.HTTP_422_UNPROCESSABLE_ENTITY),   # null json value - Pydantic validation
        ("invalid!!",status.HTTP_400_BAD_REQUEST),   # bad chars
    ],
)
@pytest.mark.asyncio
async def test_invalid_inputs(async_client: httpx.AsyncClient, indicator, expected):    # note: None must be sent as JSON null, so build payload directly
    r = await async_client.post("/api/virustotal/ip", json={
        "indicator": indicator,
        "user_id": "test-user-123",
        "subscription_level": "free"
    })
    assert r.status_code == expected
