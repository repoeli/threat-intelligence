"""Facade over VirusTotalClient + Redis‑based per‑user daily quotas.

Uses **redis-py’s built‑in asyncio API** (`import redis.asyncio as redis`), so we
no longer depend on the deprecated *aioredis* package.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

import redis.asyncio as redis  # modern async client (redis>=5.0)
from fastapi import HTTPException

from ..clients.virustotal_client import APIError, RateLimitError, VirusTotalClient

VT_KEY = os.getenv("VIRUSTOTAL_API_KEY", "")
_vt = VirusTotalClient(VT_KEY)

logger = logging.getLogger("vt_service")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
_redis: redis.Redis | None = None


async def _r() -> redis.Redis:
    """Return a singleton async Redis connection pool."""
    global _redis
    if _redis is None:
        _redis = await redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    return _redis

# hard daily limits per subscription tier
LIMITS = {
    "free": 20,
    "medium": 500,
    "plus": 2000,
    "admin": 10000,
}


async def vt_call(
    uid: str,
    tier: str,
    name: str,
    *,
    path_params: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    json: Any = None,
) -> Dict[str, Any]:
    """Enforce quota then delegate to VirusTotalClient.call()."""

    # ── quota enforcement --------------------------------------------------
    r = await _r()
    key = f"vt:{uid}:{int(time.time() // 86400)}"  # daily bucket per user
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, 86400)
    if count > LIMITS.get(tier, 0):
        raise HTTPException(429, "daily quota for your tier exceeded")

    # ── proxy call ----------------------------------------------------------
    try:
        return await _vt.call(name, path_params=path_params, params=params, json=json)
    except RateLimitError as exc:
        raise HTTPException(429, "VirusTotal key rate‑limit hit, try later") from exc
    except APIError as exc:
        logger.error("VT API error for user %s: %s", uid, exc)
        raise HTTPException(502, str(exc))

# ----------------------------------------------------------------------------