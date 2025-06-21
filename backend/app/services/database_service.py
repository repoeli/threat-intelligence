"""
Database service for user management and analysis history.
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from passlib.context import CryptContext

from ..db_models import User, AnalysisHistory, APIKey, SystemMetrics
from ..models import UserCreate, UserResponse, ThreatIntelligenceResult


class DatabaseService:
    """Service for database operations."""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def _hash_password(self, password: str) -> str:
        """Hash a password."""
        return self.pwd_context.hash(password)
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    async def create_user(self, db: AsyncSession, user_data: UserCreate) -> User:
        """Create a new user."""
        hashed_password = self._hash_password(user_data.password)
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            is_active=True,
            is_admin=getattr(user_data, 'is_admin', False),
            created_at=datetime.now(timezone.utc)        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user
    
    async def get_user_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        """Get user by username."""
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, db: AsyncSession, user_id: int) -> Optional[User]:
        """Get user by ID."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    async def authenticate_user(self, db: AsyncSession, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = await self.get_user_by_email(db, email)
        if not user or not self._verify_password(password, user.hashed_password):
            return None
        
        # Update last login
        user.last_login = datetime.now(timezone.utc)
        await db.commit()
        return user
    
    async def update_user_last_login(self, db: AsyncSession, user_id: int) -> None:
        """Update user's last login timestamp."""
        user = await self.get_user_by_id(db, user_id)
        if user:
            user.last_login = datetime.now(timezone.utc)
            await db.commit()
    
    async def store_analysis_result(
        self, 
        db: AsyncSession, 
        user_id: int, 
        indicator: str, 
        indicator_type: str, 
        result: ThreatIntelligenceResult
    ) -> AnalysisHistory:
        """Store threat analysis result in database."""
        analysis_record = AnalysisHistory(
            user_id=user_id,
            indicator=indicator,
            indicator_type=indicator_type,
            threat_score=result.threat_score.score,
            risk_level=result.threat_score.risk_level.value,
            analysis_data={
                "summary": result.summary,
                "threat_score": {
                    "score": result.threat_score.score,
                    "risk_level": result.threat_score.risk_level.value,
                    "confidence": result.threat_score.confidence,
                    "reasoning": result.threat_score.reasoning
                },
                "recommendations": result.recommendations,
                "metadata": result.metadata
            },
            sources={
                "virustotal": result.sources.get("virustotal", {}),
                "internal": result.sources.get("internal", {})
            },
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(analysis_record)
        await db.commit()
        await db.refresh(analysis_record)
        return analysis_record
    
    async def get_user_analysis_history(
        self, 
        db: AsyncSession, 
        user_id: int, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[AnalysisHistory]:
        """Get user's analysis history."""
        result = await db.execute(
            select(AnalysisHistory)
            .where(AnalysisHistory.user_id == user_id)
            .order_by(desc(AnalysisHistory.created_at))
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    async def get_analysis_by_id(self, db: AsyncSession, analysis_id: int) -> Optional[AnalysisHistory]:
        """Get analysis record by ID."""
        result = await db.execute(
            select(AnalysisHistory)
            .options(selectinload(AnalysisHistory.user))
            .where(AnalysisHistory.id == analysis_id)
        )
        return result.scalar_one_or_none()
    
    async def get_recent_analyses(self, db: AsyncSession, limit: int = 10) -> List[AnalysisHistory]:
        """Get recent analyses across all users (for admin)."""
        result = await db.execute(
            select(AnalysisHistory)
            .options(selectinload(AnalysisHistory.user))
            .order_by(desc(AnalysisHistory.created_at))
            .limit(limit)
        )
        return result.scalars().all()
    
    async def store_metric(
        self, 
        db: AsyncSession, 
        metric_name: str, 
        metric_value: str, 
        metric_type: str = "counter",
        tags: Optional[Dict[str, Any]] = None
    ) -> SystemMetrics:
        """Store system metric."""
        metric = SystemMetrics(
            metric_name=metric_name,
            metric_value=metric_value,
            metric_type=metric_type,
            tags=tags or {},
            timestamp=datetime.now(timezone.utc)
        )
        
        db.add(metric)
        await db.commit()
        await db.refresh(metric)
        return metric


# Global database service instance
db_service = DatabaseService()
