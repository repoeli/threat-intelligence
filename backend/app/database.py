"""
Database configuration and setup for the threat intelligence API.
"""
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, JSON, Text, Integer, Boolean
from datetime import datetime
import asyncio


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Database engine and session setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./threat_intelligence.db")

# For PostgreSQL in production, use:
# DATABASE_URL = "postgresql+asyncpg://user:password@localhost/threat_intelligence"

engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DEBUG", "false").lower() == "true",
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_database():
    """Initialize the database by creating all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_database():
    """Close the database engine."""
    await engine.dispose()
