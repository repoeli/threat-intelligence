# tests/test_concurrency.py
import asyncio, pytest, httpx
from fastapi import status

@pytest.mark.asyncio
async def test_concurrent_requests(async_client: httpx.AsyncClient, mock_vt):
    async def _hit():        return await async_client.post(
            "/api/virustotal/file",
            json={
                "indicator": "5d41402abc4b2a76b9719d911017c592",
                "user_id": "test-user-123",
                "subscription_level": "free"
            },
        )

    tasks = [asyncio.create_task(_hit()) for _ in range(10)]
    responses = await asyncio.gather(*tasks)
    assert all(r.status_code == status.HTTP_200_OK for r in responses)
