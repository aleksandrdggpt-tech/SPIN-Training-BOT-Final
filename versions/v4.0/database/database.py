"""
Database connection and session management for SPIN Training Bot v4.
Uses SQLAlchemy with async support.

Supports:
- PostgreSQL (via asyncpg) - production (Railway)
- SQLite (via aiosqlite) - development/testing (only if DEV_MODE=1)
"""

import logging
import os
import re
from typing import AsyncGenerator, Any, Dict
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

# Log original DATABASE_URL (without sensitive data for security)
original_database_url = DATABASE_URL
safe_original_url = original_database_url.split('@')[-1] if '@' in original_database_url else original_database_url[:50]
logger.info(f"Original DATABASE_URL: {safe_original_url}...")

# Convert postgres:// to postgresql+asyncpg:// (Railway/Heroku compatibility)
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+asyncpg://', 1)
    logger.info("Converted postgres:// to postgresql+asyncpg://")
elif DATABASE_URL.startswith('postgresql://') and '+asyncpg' not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)
    logger.info("Converted postgresql:// to postgresql+asyncpg://")

# Remove sslmode from URL if present (asyncpg doesn't support it in URL)
# We'll pass SSL settings via connect_args instead
# CRITICAL: asyncpg does NOT support sslmode parameter - it causes TypeError
if DATABASE_URL.startswith('postgresql+asyncpg://'):
    # Check if sslmode is present before removal
    had_sslmode = 'sslmode=' in DATABASE_URL
    original_url = DATABASE_URL
    
    # Remove sslmode using multiple methods to be absolutely sure
    # Method 1: Remove sslmode=value pattern (most common)
    DATABASE_URL = re.sub(r'[?&]sslmode=[^&]*', '', DATABASE_URL)
    # Method 2: Remove sslmode if it's the only parameter
    DATABASE_URL = re.sub(r'\?sslmode=[^&]*$', '', DATABASE_URL)
    DATABASE_URL = re.sub(r'&sslmode=[^&]*', '', DATABASE_URL)
    # Clean up trailing ? or & if left
    DATABASE_URL = DATABASE_URL.rstrip('?&')
    
    if had_sslmode:
        safe_cleaned_url = DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL[:50]
        logger.info(f"Removed sslmode parameter from DATABASE_URL (asyncpg doesn't support it)")
        logger.info(f"Cleaned DATABASE_URL: {safe_cleaned_url}...")

# Pool configuration for Railway (small pool, no overflow)
DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '5'))
DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '0'))

# Determine if we need SSL (for PostgreSQL on Railway)
is_postgres = DATABASE_URL.startswith('postgresql+asyncpg://')
connect_args = {}

if is_postgres:
    # Railway PostgreSQL requires SSL but uses self-signed certificates
    # asyncpg uses 'ssl' parameter (True or SSL object), not 'sslmode' in URL
    # CRITICAL: asyncpg does NOT support sslmode parameter - it causes TypeError
    # We must use 'ssl' parameter with SSL context that doesn't verify certificates
    import ssl
    
    # Create SSL context that doesn't verify certificates (Railway uses self-signed certs)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connect_args['ssl'] = ssl_context
    
    # CRITICAL FIX: SQLAlchemy automatically passes query parameters from URL to connect_args
    # We need to intercept and filter sslmode before it reaches asyncpg
    # Use monkey-patching of asyncpg.connect - this is the most reliable approach
    import asyncpg
    
    # Store original asyncpg.connect before patching
    _original_asyncpg_connect = asyncpg.connect
    
    # Create wrapper that filters sslmode
    async def _filtered_asyncpg_connect(*args: Any, **kwargs: Any) -> Any:
        """
        Wrapper around asyncpg.connect that filters out sslmode parameter.
        SQLAlchemy passes query parameters from URL to connect_args, including sslmode.
        asyncpg does NOT support sslmode, so we must remove it.
        """
        # Remove sslmode if present (asyncpg doesn't support it)
        if 'sslmode' in kwargs:
            logger.warning("Removing sslmode from connect args (asyncpg doesn't support it)")
            del kwargs['sslmode']
        # Ensure ssl is set for Railway PostgreSQL
        if 'ssl' not in kwargs:
            kwargs['ssl'] = True
        # Call original asyncpg.connect with filtered kwargs
        return await _original_asyncpg_connect(*args, **kwargs)
    
    # Monkey-patch asyncpg.connect to use our filtered version
    asyncpg.connect = _filtered_asyncpg_connect
    logger.info("Monkey-patched asyncpg.connect to filter sslmode parameter")

# Create async engine with controlled pool
engine_kwargs = {
    'echo': False,
    'future': True,
    'poolclass': QueuePool,
    'pool_size': DB_POOL_SIZE,
    'max_overflow': DB_MAX_OVERFLOW,
    'pool_pre_ping': True,
    'pool_recycle': 3600,  # Recycle connections every hour
}
# Add connect_args only if we have SSL settings for PostgreSQL
if connect_args:
    engine_kwargs['connect_args'] = connect_args

# Log final configuration (without sensitive data)
safe_url = DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL[:50]
logger.info(f"Database engine created: {safe_url}... (pool_size={DB_POOL_SIZE}, max_overflow={DB_MAX_OVERFLOW})")
if connect_args:
    logger.debug(f"Connect args keys: {list(connect_args.keys())}")
if is_postgres:
    logger.info("Using monkey-patched asyncpg.connect to filter sslmode from connect args")
    # Log host and port for debugging connection issues
    try:
        from urllib.parse import urlparse
        parsed = urlparse(DATABASE_URL)
        logger.info(f"Database host: {parsed.hostname}, port: {parsed.port}")
    except Exception as e:
        logger.warning(f"Could not parse DATABASE_URL for logging: {e}")

engine = create_async_engine(DATABASE_URL, **engine_kwargs)

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
