"""
Database connection and session management for DotMac Analytics.
"""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from .config import get_config
from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)

# Global engine and session factory
_engine = None
_SessionLocal = None


def init_database():
    """Initialize database engine and session factory."""
    global _engine, _SessionLocal

    config = get_config()

    try:
        _engine = create_engine(
            config.database.url,
            poolclass=QueuePool,
            pool_size=config.database.pool_size,
            max_overflow=config.database.max_overflow,
            pool_timeout=config.database.pool_timeout,
            echo=config.database.echo
        )

        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_engine
        )

        logger.info("Database initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise ConfigurationError(f"Database initialization failed: {str(e)}")


def get_engine():
    """Get database engine."""
    if _engine is None:
        init_database()
    return _engine


def get_session_factory():
    """Get session factory."""
    if _SessionLocal is None:
        init_database()
    return _SessionLocal


def get_session() -> Session:
    """Get database session."""
    SessionLocal = get_session_factory()
    return SessionLocal()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions."""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_tables():
    """Create all database tables."""
    from ..models import dashboards, datasets, events, metrics, reports, segments

    engine = get_engine()

    # Create tables for all models
    events.Base.metadata.create_all(bind=engine)
    metrics.Base.metadata.create_all(bind=engine)
    datasets.Base.metadata.create_all(bind=engine)
    dashboards.Base.metadata.create_all(bind=engine)
    reports.Base.metadata.create_all(bind=engine)
    segments.Base.metadata.create_all(bind=engine)

    logger.info("Database tables created successfully")


def drop_tables():
    """Drop all database tables."""
    from ..models import dashboards, datasets, events, metrics, reports, segments

    engine = get_engine()

    # Drop tables for all models
    segments.Base.metadata.drop_all(bind=engine)
    reports.Base.metadata.drop_all(bind=engine)
    dashboards.Base.metadata.drop_all(bind=engine)
    datasets.Base.metadata.drop_all(bind=engine)
    metrics.Base.metadata.drop_all(bind=engine)
    events.Base.metadata.drop_all(bind=engine)

    logger.info("Database tables dropped successfully")


def check_connection() -> bool:
    """Check database connection health."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
