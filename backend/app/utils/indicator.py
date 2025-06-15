## `backend/app/utils/indicator.py`

"""Indicator type detection with OWASP-style hardening (same logic as before)."""
"""Robust indicator classification - extensible."""
import re, ipaddress, logging
from fastapi import HTTPException

logger = logging.getLogger("indicator_utils")

PATTERNS = {
    "ip":      re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$"),
    "url":     re.compile(r"^https?://", re.I),
    "domain":  re.compile(r"^(?!https?://)[a-z0-9.-]+\.[a-z]{2,}$", re.I),
    "hash":    re.compile(r"^[a-f0-9]{32}|[a-f0-9]{40}|[a-f0-9]{64}$", re.I),
    "email":   re.compile(r"^[\w.+-]+@[\w.-]+\.[a-z]{2,}$", re.I),
}

def determine_indicator_type(indicator: str) -> str:
    ind = indicator.strip().lower()
    if PATTERNS["ip"].match(ind):
        try: ipaddress.ip_address(ind); return "ip"
        except ValueError: pass
    for t, pat in PATTERNS.items():
        if t == "ip":
            continue
        if pat.match(ind):
            return t
    logger.warning("Unsupported indicator: %s", indicator)
    raise HTTPException(400, f"Unsupported indicator: {indicator}")