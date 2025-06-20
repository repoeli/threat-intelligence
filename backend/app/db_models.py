"""
Database models for the threat intelligence API.
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, JSON, Text, Integer, Boolean, ForeignKey
from datetime import datetime, timezone
from .database import Base


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationship to analysis history
    analysis_history = relationship("AnalysisHistory", back_populates="user", cascade="all, delete-orphan")


class AnalysisHistory(Base):
    """Model to store threat analysis history."""
    __tablename__ = "analysis_history"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    indicator: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    indicator_type: Mapped[str] = mapped_column(String(50), nullable=False)
    threat_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    analysis_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    sources: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationship to user
    user = relationship("User", back_populates="analysis_history")


class APIKey(Base):
    """Model to store API keys for external services."""
    __tablename__ = "api_keys"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    service_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    key_name: Mapped[str] = mapped_column(String(100), nullable=False)
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class SystemMetrics(Base):
    """Model to store system metrics and statistics."""
    __tablename__ = "system_metrics"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    metric_value: Mapped[str] = mapped_column(Text, nullable=False)
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)  # counter, gauge, histogram
    tags: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
