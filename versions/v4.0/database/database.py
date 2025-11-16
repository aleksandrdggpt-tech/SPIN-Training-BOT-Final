"""
Database connection and session management for SPIN Training Bot v4.
Uses SQLAlchemy with async support.

Supports:
- PostgreSQL (via asyncpg) - production (Railway)
- SQLite (via aiosqlite) - development/testing (only if DEV_MODE=1)
"""

import logging
import os
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)
from sqlalchemy.pool import QueuePool

from .base_models import Base

logger = logging.getLogger(__name__)

# Database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL', '')
DEV_MODE = os.getenv('DEV_MODE', '0') == '1'
WRITE_PID_FILE = os.getenv('WRITE_PID_FILE', '0') == '1'

# Fallback to SQLite only in development mode
if not DATABASE_URL and DEV_MODE:
    DATABASE_URL = 'sqlite+aiosqlite:///./spin_bot.db'
    logger.warning("Using SQLite database (DEV_MODE enabled). This should not be used in production!")

# Validate DATABASE_URL for production
if not DATABASE_URL:
    logger.critical("DATABASE_URL is not set and DEV_MODE is disabled. Cannot start bot.")
    raise ValueError("DATABASE_URL environment variable is required. Set DEV_MODE=1 for local SQLite development.")

# Convert postgres:// to postgresql+asyncpg:// (Railway/Heroku compatibility)
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+asyncpg://', 1)
elif DATABASE_URL.startswith('postgresql://') and '+asyncpg' not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)

# Add sslmode=require for PostgreSQL connections (Railway requirement)
if DATABASE_URL.startswith('postgresql+asyncpg://') and 'sslmode' not in DATABASE_URL:
    sep = '&' if '?' in DATABASE_URL else '?'
    DATABASE_URL = DATABASE_URL + f"{sep}sslmode=require"

# Pool configuration for Railway (small pool, no overflow)
DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '5'))
DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '0'))

# Create async engine with controlled pool
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    poolclass=QueuePool,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections every hour
)

logger.info(f"Database engine created: {DATABASE_URL[:50]}... (pool_size={DB_POOL_SIZE}, max_overflow={DB_MAX_OVERFLOW})")

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session as async context manager.

    Usage:
        async with get_session() as session:
            # Your database operations
            result = await session.execute(select(User))
            pass
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """
    Initialize database: create all tables.
    Should be called once at application startup.
    """
    logger.info("Initializing database...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"ERROR in init_db(): {e}")
        raise


async def close_db() -> None:
    """
    Close database connection.
    Should be called on application shutdown.
    """
    logger.info("Closing database connection...")
    try:
        await engine.dispose()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"ERROR in close_db(): {e}")
