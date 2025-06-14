## `backend/app/utils/indicator.py`

"""Indicator type detection with OWASP‑style hardening (same logic as before)."""
import re, ipaddress, tldextract
from fastapi import HTTPException

def determine_indicator_type(indicator: str) -> str:
    # (implementation unchanged – paste your validated version here)
    ...
