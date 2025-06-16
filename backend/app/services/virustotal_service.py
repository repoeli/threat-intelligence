"""Facade over VirusTotalClient + Redis‑based per‑user daily quotas.

Uses **redis-py’s built‑in asyncio API** (`import redis.asyncio as redis`), so we
no longer depend on the deprecated *aioredis* package.
"""
from __future__ import annotations
import asyncio
import logging, os, time
from typing import Any, Dict, Optional
import redis.asyncio as redis
from fastapi import HTTPException, status
from ..clients.virustotal_client import APIError, RateLimitError, VirusTotalClient

logger = logging.getLogger("vt_service")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
_redis: redis.Redis | None = None
_vt: VirusTotalClient | None = None

def _get_vt_client() -> VirusTotalClient:
    """Lazy initialization of VirusTotal client."""
    global _vt
    if _vt is None:
        vt_key = os.getenv("VIRUSTOTAL_API_KEY", "")
        if not vt_key:
            raise HTTPException(503, "VirusTotal API key not configured")
        _vt = VirusTotalClient(vt_key)
    return _vt

async def _r() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = await redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    return _redis

LIMITS = {"free": 20, "medium": 500, "plus": 2000, "admin": 10000}

async def vt_call(uid: str, tier: str, name: str, *, path_params: Optional[Dict[str, Any]] = None,
                  params: Optional[Dict[str, Any]] = None, json: Any = None) -> Dict[str, Any]:
    r = await _r()
    key = f"vt:{uid}:{int(time.time()//86400)}"
    if await r.incr(key) > LIMITS.get(tier, 0):
        raise HTTPException(429, "daily quota exceeded")
    await r.expire(key, 86400)
    try:
        vt_client = _get_vt_client()
        return await vt_client.call_endpoint(name, path_params=path_params, params=params, json=json)
    except RateLimitError as exc:
        raise HTTPException(429, "VirusTotal key limit") from exc
    except APIError as exc:
        logger.error("VT error %s", exc)
        raise HTTPException(502, str(exc))

async def main():
    async def _hit():
        response = await vt_call("some_uid", "free", "some_name")
        assert response.status_code == status.HTTP_200_OK

    tasks = [asyncio.create_task(_hit()) for _ in range(10)]
    responses = await asyncio.gather(*tasks)
    assert all(r.status_code == status.HTTP_200_OK for r in responses)

# ----------------------------------------------------------------------------