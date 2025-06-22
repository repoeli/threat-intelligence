"""Facade over VirusTotalClient + Redis‑based per‑user daily quotas."""
from __future__ import annotations
import logging
import os
import time
import json as jsonlib
import hashlib
from typing import Any, Dict, Optional
import redis.asyncio as redis
from fastapi import HTTPException
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

CACHE_TTL = int(os.getenv("VT_CACHE_TTL", "3600"))

def _make_cache_key(name: str, path_params: Optional[Dict[str, Any]], params: Optional[Dict[str, Any]], json_body: Any) -> str:
    """Create a stable cache key for a VT request."""
    data = {
        "name": name,
        "path": path_params or {},
        "params": params or {},
        "json": json_body or {},
    }
    serialized = jsonlib.dumps(data, sort_keys=True, default=str)
    digest = hashlib.sha256(serialized.encode()).hexdigest()
    return f"vtc:{digest}"

LIMITS = {"free": 20, "medium": 500, "plus": 2000, "admin": 10000}

async def vt_call(uid: str, tier: str, name: str, *, path_params: Optional[Dict[str, Any]] = None,
                  params: Optional[Dict[str, Any]] = None, json: Any = None) -> Dict[str, Any]:
    r = await _r()
    key = f"vt:{uid}:{int(time.time()//86400)}"
    if await r.incr(key) > LIMITS.get(tier, 0):
        raise HTTPException(429, "daily quota exceeded")
    await r.expire(key, 86400)
    cache_key = _make_cache_key(name, path_params, params, json)
    cached = await r.get(cache_key)
    if cached:
        try:
            return jsonlib.loads(cached)
        except Exception:
            pass
    try:
        vt_client = _get_vt_client()
        result = await vt_client.call_endpoint(name, path_params=path_params, params=params, json=json)
        await r.setex(cache_key, CACHE_TTL, jsonlib.dumps(result))
        return result
    except RateLimitError as exc:
        raise HTTPException(429, "VirusTotal key limit") from exc
    except APIError as exc:
        logger.error("VT error %s", exc)
        raise HTTPException(502, str(exc))
