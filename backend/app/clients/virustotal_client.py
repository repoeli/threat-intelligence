"""
virustotal_client.py  -  Async wrapper for VirusTotal v3 (public / free tier)

Key points
──────────
• 4 req/min · 500 req/day — enforced *locally* so we never hit VT 429.
• httpx.AsyncClient  - no ThreadPool.
• Exponential back-off **with 10-25 % jitter** on 429.
• Circuit-breaker stub: after N consecutive 5xx we pause for COOLDOWN.
• Pydantic validators for the few high-level helpers we expose.
• NO per-user billing logic here — that lives in virustotal_service + Redis.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any, Dict, Literal, Optional, Tuple

import httpx
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("vt_client")

# ───────────────────────────── Errors ────────────────────────────────────
class APIError(Exception):
    """Generic API failure (4xx/5xx other than 401/403/429)."""


class AuthenticationError(APIError):
    """Invalid or missing API key (401/403)."""


class RateLimitError(APIError):
    """Our local limiter or VT’s remote limiter tripped (429)."""


class PremiumEndpointError(APIError):
    """Tried to call an enterprise-only endpoint with a free key."""


# ────────────────────────── Endpoint catalog ─────────────────────────────
FREE_ENDPOINTS: Dict[str, Tuple[str, str]] = {
    # Essentials
    "get_file_report": ("GET", "/files/{file_id}"),
    "scan_url": ("POST", "/urls"),
    "get_url_report": ("GET", "/urls/{url_id}"),
    "get_ip_report": ("GET", "/ip_addresses/{ip}"),
    "get_domain_report": ("GET", "/domains/{domain}"),
    "get_analysis": ("GET", "/analyses/{analysis_id}"),
    # Generic relationship
    "get_relationship": ("GET", "/{object_type}/{object_id}/{relationship}"),
}

# ────────────────────────── Simple validators ────────────────────────────
class _FileID(BaseModel):
    file_id: str = Field(..., min_length=32, max_length=64)

    @field_validator("file_id")
    @classmethod
    def _hex(cls, v):  # noqa: N805
        if not all(c in "0123456789abcdefABCDEF" for c in v):
            raise ValueError("file_id must be hex-encoded")
        return v


class _URLID(BaseModel):
    url_id: str

    @field_validator("url_id")
    @classmethod
    def _b64(cls, v):  # noqa: N805
        if "/" in v or "+" in v:
            raise ValueError("url_id must be URL-safe base64 (no / or +)")
        return v


# ─────────────────────────── Local rate-limiter ──────────────────────────
class _LeakyBucket:
    """Process-local limiter: 4 req/min, 500 req/day."""

    def __init__(self, per_min: int = 4, per_day: int = 500):
        self.per_min = per_min
        self.per_day = per_day
        self.minute_timestamps: list[float] = []
        self.day_count = 0
        self.day_key = int(time.time() // 86_400)
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.time()
            today = int(now // 86_400)
            if today != self.day_key:
                self.day_key = today
                self.day_count = 0
                self.minute_timestamps.clear()

            if self.day_count >= self.per_day:
                raise RateLimitError("Daily key quota reached (500)")

            # prune >60 s
            self.minute_timestamps = [t for t in self.minute_timestamps if now - t < 60]
            if len(self.minute_timestamps) >= self.per_min:
                sleep_for = 60 - (now - self.minute_timestamps[0]) + 0.05
                logger.debug("VT key limiter: sleeping %.2fs", sleep_for)
                await asyncio.sleep(sleep_for)

            self.minute_timestamps.append(now)
            self.day_count += 1


# ────────────────────────── Circuit-breaker stub ─────────────────────────
class _CircuitBreaker:
    """Simple consecutive-error breaker (optional)."""

    THRESHOLD = 5
    COOLDOWN = 60  # seconds

    def __init__(self) -> None:
        self.failures = 0
        self.block_until = 0.0

    async def before_request(self) -> None:
        if time.time() < self.block_until:
            raise APIError("Circuit breaker: VT marked as down temporarily")

    async def after_response(self, success: bool) -> None:
        if success:
            self.failures = 0
            return
        self.failures += 1
        if self.failures >= self.THRESHOLD:
            self.block_until = time.time() + self.COOLDOWN
            logger.warning("Circuit breaker: opened for %ds", self.COOLDOWN)


# ───────────────────────────── The client ────────────────────────────────
class VirusTotalClient:
    BASE_URL = "https://www.virustotal.com/api/v3"

    def __init__(
        self,
        api_key: str,
        *,
        rl: Optional[_LeakyBucket] = None,
        session: Optional[httpx.AsyncClient] = None,
    ) -> None:
        if not api_key:
            raise AuthenticationError("API key required")

        self._rl = rl or _LeakyBucket()
        self._cb = _CircuitBreaker()
        self._client = session or httpx.AsyncClient(
            headers={"x-apikey": api_key.strip(), "User-Agent": "vt-saas/0.2"}
        )

    # ───────────── convenient wrappers (optional) ──────────────
    async def get_file_report(self, file_id: str) -> dict[str, Any]:
        fid = _FileID(file_id=file_id).file_id
        return await self.call_endpoint("get_file_report", path_params={"file_id": fid})

    async def get_url_report(self, url_id: str) -> dict[str, Any]:
        uid = _URLID(url_id=url_id).url_id
        return await self.call_endpoint("get_url_report", path_params={"url_id": uid})

    # ───────────────────── main generic call ────────────────────
    async def call_endpoint(
        self,
        name: str,
        *,
        path_params: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        json: Any = None,
    ) -> dict[str, Any]:
        if name not in FREE_ENDPOINTS:
            raise PremiumEndpointError(f"{name} is enterprise-only")

        method, path_tpl = FREE_ENDPOINTS[name]
        path = path_tpl.format(**(path_params or {}))

        # local limiter
        await self._rl.acquire()
        await self._cb.before_request()

        url = f"{self.BASE_URL}{path}"
        attempt = 0

        while True:
            attempt += 1
            resp = await self._client.request(
                method,
                url,
                params=params,
                json=json,
                timeout=30,
            )

            if resp.status_code == 429:
                # jitter 10-25 % so multiple workers don’t hammer at once
                back = min(60 * attempt, 120)
                jitter = back * random.uniform(0.1, 0.25)
                await asyncio.sleep(back + jitter)
                continue

            if resp.status_code in (401, 403):
                raise AuthenticationError(resp.text)

            # VT occasionally returns 5xx; retry up to 3×
            if resp.status_code >= 500 and attempt < 3:
                await asyncio.sleep(2**attempt)
                continue

            # 4xx that we don’t explicitly handle
            if resp.status_code >= 400:
                await self._cb.after_response(False)
                raise APIError(f"VT error {resp.status_code}: {resp.text[:200]}")

            await self._cb.after_response(True)
            return resp.json()