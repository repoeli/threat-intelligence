## `backend/app/models.py`
# ─────────────────────────────────────────────────────────────────────
# This file defines the data models used in the FastAPI application.
from pydantic import BaseModel, Field
from typing import Dict, Any

class IndicatorRequest(BaseModel):
    indicator: str = Field(..., description="IoC to analyze")

class VizResponse(BaseModel):
    summary_markdown: str
    charts: Dict[str, Any]
    verdict: str