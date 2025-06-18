## `backend/app/models.py`
# ─────────────────────────────────────────────────────────────────────
# This file defines the data models used in the FastAPI application.
"""Enhanced Pydantic request/response schemas with advanced validation."""

from datetime import datetime
from typing import Literal, Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator


# ────────────────── Enhanced Enums ──────────────────
class ThreatLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BENIGN = "benign"


class IndicatorType(str, Enum):
    IP = "ip"
    DOMAIN = "domain"
    URL = "url"
    HASH = "hash"
    EMAIL = "email"


class SubscriptionTier(str, Enum):
    FREE = "free"
    MEDIUM = "medium"
    PLUS = "plus"
    ADMIN = "admin"


# ────────────────── Enhanced Request Models ──────────────────
class IndicatorRequest(BaseModel):
    indicator: str = Field(..., min_length=1, max_length=2048, description="IoC to analyse")
    user_id: str = Field(..., description="User UUID", pattern=r"^[a-f0-9\-]{36}$")
    subscription_level: SubscriptionTier = SubscriptionTier.FREE
    include_raw_data: bool = Field(False, description="Include raw API responses")
    timeout: Optional[int] = Field(30, ge=5, le=120, description="Analysis timeout in seconds")
    
    @field_validator('indicator')
    @classmethod
    def validate_indicator(cls, v):
        if not v or v.isspace():
            raise ValueError('Indicator cannot be empty or whitespace')
        return v.strip()


class BulkAnalysisRequest(BaseModel):
    indicators: List[str] = Field(..., min_items=1, max_items=100, description="List of indicators to analyze")
    user_id: str = Field(..., description="User UUID", pattern=r"^[a-f0-9\-]{36}$")
    subscription_level: SubscriptionTier = SubscriptionTier.FREE
    include_raw_data: bool = False
    timeout: Optional[int] = Field(30, ge=5, le=120)
    
    @field_validator('indicators')
    @classmethod
    def validate_indicators(cls, v):
        if not all(indicator.strip() for indicator in v):
            raise ValueError('All indicators must be non-empty')
        return [indicator.strip() for indicator in v]


class EmailRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address to validate")
    user_id: str = Field(..., description="User UUID")
    subscription_level: SubscriptionTier = SubscriptionTier.FREE

    class Config:
        json_schema_extra = {
            "example": {
                "email": "alice@example.com",
                "user_id": "12345678-1234-1234-1234-123456789012",
                "subscription_level": "free",
            }
        }


# ────────────────── Enhanced Response Models ──────────────────
class ThreatIntelligenceSource(BaseModel):
    name: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    threat_level: ThreatLevel
    last_updated: datetime
    raw_data: Optional[Dict[str, Any]] = None


class AnalysisResponse(BaseModel):
    indicator: str
    indicator_type: IndicatorType
    threat_level: ThreatLevel
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")
    sources: Dict[str, ThreatIntelligenceSource]
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)
    analysis_duration_ms: int = Field(..., ge=0, description="Analysis duration in milliseconds")
    ml_prediction: Optional[Dict[str, Any]] = None
    recommendations: List[str] = Field(default_factory=list)


class BulkAnalysisResponse(BaseModel):
    total_analyzed: int
    successful: int
    failed: int
    results: List[AnalysisResponse]
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)


class VizResponse(BaseModel):
    summary_markdown: str
    charts: Dict[str, Any]
    verdict: ThreatLevel
    analysis_metadata: Dict[str, Any] = Field(default_factory=dict)


class HealthStatus(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: Dict[str, Dict[str, Any]]
    version: str = "2.0.0"


# ───────────────────────── Enhanced Telemetry ───────────────────────────
class UsageRecord(BaseModel):
    """
    Enhanced usage tracking for analytics & billing.
    """
    user_id: str
    endpoint: str
    indicator_type: Optional[IndicatorType] = None
    processing_time_ms: int
    success: bool
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    subscription_tier: SubscriptionTier
    cache_hit: bool = False
    sources_used: List[str] = Field(default_factory=list)

    status: Literal["success", "failure"]
    response_code: int = 0

    # performance & size metrics (optional but nice for dashboards)
    response_time: float = 0.0      # seconds
    request_size: int = 0           # bytes
    response_size: int = 0          # bytes


# ────────────────── Authentication Models ──────────────────
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, description="Username or email")
    password: str = Field(..., min_length=1, description="User password")

    class Config:
        json_schema_extra = {
            "example": {
                "username": "user@example.com",
                "password": "SecurePassword123!"
            }
        }


class UserRegistration(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    subscription_level: SubscriptionTier = SubscriptionTier.FREE

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePassword123!",
                "subscription_level": "free"
            }
        }


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(default=1800, description="Token expiration in seconds")


class UserResponse(BaseModel):
    user_id: str
    email: EmailStr
    subscription_level: SubscriptionTier
    is_active: bool = True
    created_at: Optional[datetime] = None
