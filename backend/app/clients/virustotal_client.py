## `backend/app/clients/virustotal_client.py`

"""virustotal_client.py - Public-API-only wrapper (free/community tier)
────────────────────────────────────────────────────────────────────────────
• Handles VT v3 endpoints accessible with a free key (4 req/min, 500 req/day).
• Built-in leaky-bucket limiter + exponential back-off on HTTP 429.
• Exposes high-level convenience methods **and** a generic `call_endpoint()`.
• Thread-safe singleton rate-limiter, works from any async/web context via
  `asyncio.get_running_loop().run_in_executor()`.
• No external deps beyond `requests` (keep runtime slim; httpx optional).
"""
from __future__ import annotations

import datetime as _dt
import logging as _log
import threading as _th
import time as _time
from typing import Any, Dict, List, Literal, Optional, Tuple

import requests as _rq

__all__ = [
    "VirusTotalClient",
    "APIError",
    "AuthenticationError",
    "PermissionError",
    "RateLimitError",
    "PremiumEndpointError",
]

_log.basicConfig(level=_log.INFO)
logger = _log.getLogger("virustotal_client")

# ────────────────────────────── Errors ────────────────────────────────────
class APIError(Exception):
    """Base class for all VT client exceptions."""


class AuthenticationError(APIError):
    """401 (unauth) or 403 (no x‑apikey)"""


class PermissionError(APIError):
    """403 when hitting premium endpoint with free key"""


class RateLimitError(APIError):
    """Local limiter trip or HTTP 429 after retries"""


class PremiumEndpointError(APIError):
    """Endpoint not available for the community tier."""


# ─────────────────────────── Rate Limiter ────────────────────────────────
class _RateLimiter:
    """Global leaky‑bucket enforcing 4 req/min & 500 req/day (UTC)."""

    _INST: Optional["_RateLimiter"] = None
    _LOCK = _th.Lock()

    def __new__(cls, per_min: int = 4, per_day: int = 500):
        with cls._LOCK:
            if cls._INST is None:
                cls._INST = super().__new__(cls)
                cls._INST.per_min = per_min
                cls._INST.per_day = per_day
                cls._INST.calls = []  # timestamps (sec)
                cls._INST.day_count = 0
                cls._INST.day_start = _dt.date.today()
                cls._INST._mutex = _th.Lock()
            return cls._INST

    def acquire(self):
        with self._mutex:
            # reset daily window
            today = _dt.date.today()
            if today != self.day_start:
                self.day_start = today
                self.day_count = 0
                self.calls.clear()

            if self.day_count >= self.per_day:
                raise RateLimitError("Daily quota reached (500)")

            now = _time.time()
            # prune >60s
            self.calls[:] = [t for t in self.calls if now - t < 60]
            if len(self.calls) >= self.per_min:
                wait = 60 - (now - self.calls[0]) + 0.05
                logger.debug("Rate‑limit: sleeping %.2fs", wait)
                _time.sleep(wait)

            self.calls.append(_time.time())
            self.day_count += 1

# ─────────────────────── Endpoint Catalogue (free) ───────────────────────
FREE_ENDPOINTS: Dict[str, Tuple[str, str]] = {
    # Essentials
    "get_file_report": ("GET", "/files/{file_id}"),
    "upload_file": ("POST", "/files"),
    "get_upload_url": ("GET", "/files/upload_url"),
    "rescan_file": ("POST", "/files/{file_id}/analyse"),

    "scan_url": ("POST", "/urls"),
    "get_url_report": ("GET", "/urls/{url_id}"),
    "rescan_url": ("POST", "/urls/{url_id}/analyse"),

    "get_ip_report": ("GET", "/ip_addresses/{ip}"),
    "rescan_ip": ("POST", "/ip_addresses/{ip}/analyse"),

    "get_domain_report": ("GET", "/domains/{domain}"),
    "rescan_domain": ("POST", "/domains/{domain}/analyse"),

    "get_analysis": ("GET", "/analyses/{analysis_id}"),

    # Comments & votes (nice‑to‑have)
    "get_latest_comments": ("GET", "/comments"),
    "get_comment": ("GET", "/comments/{comment_id}"),
    "delete_comment": ("DELETE", "/comments/{comment_id}"),
    "add_comment_file": ("POST", "/files/{file_id}/comments"),
    "add_comment_url": ("POST", "/urls/{url_id}/comments"),
    "get_votes_file": ("GET", "/files/{file_id}/votes"),
    "add_vote_file": ("POST", "/files/{file_id}/votes"),
    "get_votes_url": ("GET", "/urls/{url_id}/votes"),
    "add_vote_url": ("POST", "/urls/{url_id}/votes"),

    # Generic relationship
    "get_relationship": ("GET", "/{object_type}/{object_id}/{relationship}"),
}


# ──────────────────────────── The Client ────────────────────────────────
class VirusTotalClient:
    BASE_URL = "https://www.virustotal.com/api/v3"

    def __init__(self, api_key: str, *, user_agent: str | None = None,
                 backoff_cap: int = 120, session: Optional[_rq.Session] = None,
                 rl: Optional[_RateLimiter] = None):
        if not api_key:
            raise AuthenticationError("API key required")
        self.api_key = api_key.strip()
        self.headers = {
            "x-apikey": self.api_key,
            "User-Agent": user_agent or "vt-client/1.0 (+https://github.com)"
        }
        self._sess = session or _rq.Session()
        self._rl = rl or _RateLimiter()
        self._backoff_cap = backoff_cap

    # ────────────────── High‑level helpers (syntactic sugar) ────────────
    def get_file_report(self, file_id: str):
        return self.call_endpoint("get_file_report", path_params={"file_id": file_id})

    def get_domain_report(self, domain: str):
        return self.call_endpoint("get_domain_report", path_params={"domain": domain})

    def get_ip_report(self, ip: str):
        return self.call_endpoint("get_ip_report", path_params={"ip": ip})

    def get_url_report(self, url_id: str):
        return self.call_endpoint("get_url_report", path_params={"url_id": url_id})

    def scan_url(self, url: str):
        return self.call_endpoint("scan_url", json={"url": url})

    # ───────────────────────── Generic public call ─────────────────────
    def call_endpoint(self, name: str, *, path_params: Dict[str, Any] | None = None,
                       params: Dict[str, Any] | None = None, json: Any = None,
                       files: Any = None) -> Dict[str, Any]:
        if name not in FREE_ENDPOINTS:
            raise PremiumEndpointError(f"{name} is not available for free tier")
        method, path_tpl = FREE_ENDPOINTS[name]
        path = path_tpl.format(**(path_params or {}))
        return self._request(method, path, params=params, json=json, files=files)

    # ─────────────────── Internal HTTP + retry logic ───────────────────
    def _request(self, method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"], path: str,
                 *, params: Dict[str, Any] | None = None, json: Any = None,
                 data: Any = None, files: Any = None) -> Dict[str, Any]:
        self._rl.acquire()
        url = f"{self.BASE_URL}{path}"
        attempt = 0
        while True:
            attempt += 1
            resp = self._sess.request(
                method,
                url,
                headers=self.headers,
                params=params,
                json=json,
                data=data,
                files=files,
                timeout=30,
            )
            if resp.status_code == 429:
                if attempt > 5:
                    raise RateLimitError("HTTP 429 – too many retries")
                retry_after = int(resp.headers.get("Retry-After", "60"))
                sleep = min(retry_after * attempt, self._backoff_cap)
                logger.warning("VT 429 (attempt %d) – sleeping %ds", attempt, sleep)
                _time.sleep(sleep)
                continue
            if resp.status_code in {401, 403}:
                raise AuthenticationError(resp.text)
            if resp.status_code >= 500 and attempt < 3:
                _time.sleep(2 ** attempt)
                continue
            if not resp.ok:
                raise APIError(f"VT error {resp.status_code}: {resp.text[:200]}")
            try:
                return resp.json()
            except Exception as exc:
                raise APIError(f"JSON decode error: {exc}") from exc