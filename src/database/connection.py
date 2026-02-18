"""Database connection and session management"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from contextlib import contextmanager

from src.config.settings import settings
from src.config.constants import DATABASE_CONFIG

# Create database engine
engine = create_engine(
    settings.database_url,
    pool_size=DATABASE_CONFIG["pool_size"],
    max_overflow=DATABASE_CONFIG["max_overflow"],
    pool_timeout=DATABASE_CONFIG["pool_timeout"],
    pool_recycle=DATABASE_CONFIG["pool_recycle"],
    echo=settings.log_level.upper() == "DEBUG",
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


@contextmanager
def get_db() -> Session:
    """
    Context manager for database sessions.
    The caller is responsible for committing; the context manager
    only rolls back on exception and always closes the session.

    Usage:
        with get_db() as db:
            db.query(Model).all()
            db.commit()
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
