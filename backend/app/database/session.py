"""Database connection engine and session lifecycle management."""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("app.database.session")

_engine = None
_SessionLocal = None


def get_engine():
    """Retrieve or initialize the SQLAlchemy database engine with connection pooling."""
    global _engine
    if _engine is not None:
        return _engine

    settings = get_settings()
    db_url = settings.database_url

    # Check dialect for appropriate pool configuration
    if "sqlite" in db_url:
        _engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            echo=settings.database_echo,
            poolclass=NullPool,
        )
    else:
        _engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
            pool_recycle=settings.database_pool_recycle,
            pool_pre_ping=True,  # Test connections prior to checkout
            echo=settings.database_echo,
        )

    logger.info(
        "Database engine initialized",
        extra={"url": str(_engine.url), "pool": type(_engine.pool).__name__},
    )
    return _engine


def get_session_factory():
    """Retrieve or initialize the sessionmaker bound to the engine."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
            expire_on_commit=False,
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a managed database session with transaction boundary."""
    session_factory = get_session_factory()
    session: Session = session_factory()
    try:
        yield session
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.error(
            "Transaction rolled back due to error",
            extra={"error": str(exc)},
            exc_info=True,
        )
        raise
    finally:
        session.close()


def set_custom_engine(custom_engine):
    """Override engine and sessionmaker (primarily for testing fixtures)."""
    global _engine, _SessionLocal
    _engine = custom_engine
    _SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=_engine,
        expire_on_commit=False,
    )
