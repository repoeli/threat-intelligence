## `backend/app/models.py`
# ─────────────────────────────────────────────────────────────────────
# This file defines the data models used in the FastAPI application.
"""Pydantic request / response schemas + telemetry record."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


# ────────────────── public request / response ──────────────────
class IndicatorRequest(BaseModel):
    indicator: str = Field(..., description="IoC to analyse")
    user_id: str = Field(..., description="User UUID")
    subscription_level: Literal["free", "medium", "plus", "admin"] = "free"


class EmailRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address to validate")
    user_id: str = Field(..., description="User UUID")
    subscription_level: Literal["free", "medium", "plus", "admin"] = "free"

    class Config:
        schema_extra = {
            "example": {
                "email": "alice@example.com",
                "user_id": "12345678-1234-1234-1234-123456789012",
                "subscription_level": "free",
            }
        }


class VizResponse(BaseModel):
    summary_markdown: str
    charts: dict[str, object]
    verdict: str


# ───────────────────────── telemetry ───────────────────────────
class UsageRecord(BaseModel):
    """
    Captures one request/response round-trip for analytics & billing.

    * You can serialise this as JSON for a log stream or map it to a
      SQLModel table later — the schema is forward-compatible with both.
    """
    user_id: str
    endpoint: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    status: Literal["success", "failure"]
    response_code: int = 0

    # performance & size metrics (optional but nice for dashboards)
    response_time: float = 0.0      # seconds
    request_size: int = 0           # bytes
    response_size: int = 0          # bytes
