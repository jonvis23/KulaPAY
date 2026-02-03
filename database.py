"""
Async database configuration and session management for KulaPay (SQLModel).
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()


# Use SQLite by default; override with DATABASE_URL (e.g. postgres+asyncpg://...)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./kulapay.db")


engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    """
    FastAPI dependency to provide an async database session.
    """
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """
    Initialize database - create all tables defined on SQLModel metadata.
    """
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

