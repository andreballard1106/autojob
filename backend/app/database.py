"""
Database Configuration and Session Management
"""

import logging
import traceback
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

# Create async engine for PostgreSQL
# Pool size configured for concurrent job processing:
# - pool_size: base number of persistent connections
# - max_overflow: additional connections allowed during peak load
# - Total max connections = pool_size + max_overflow = 20
# This supports 5+ concurrent job processing tasks plus API requests
engine = create_async_engine(
    settings.database_url,
    echo=settings.sql_echo,  # Only log SQL when explicitly enabled
    pool_size=10,
    max_overflow=10,
    pool_pre_ping=True,
    pool_timeout=30,  # Wait up to 30 seconds for a connection
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.error(f"Database session error: {type(e).__name__}: {str(e)}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    from app.models.profile import Profile  # noqa: F401
    from app.models.job import JobApplication  # noqa: F401
    from app.models.ai_settings import AISettings  # noqa: F401
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {type(e).__name__}: {str(e)}")
        logger.error(f"Database URL: {settings.db_host}:{settings.db_port}/{settings.db_name}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        raise
