"""
Database connection management for LockZone AI Floorplan.
Handles SQLAlchemy engine creation, session management, and connection verification.
"""

import os
import sys
import logging
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

# Get DATABASE_URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL')

# Handle Render's postgres:// vs postgresql:// URL format
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# SQLAlchemy Base for model declarations
Base = declarative_base()

# Engine and SessionLocal will be initialized when needed
engine = None
SessionLocal = None


def get_engine():
    """Get or create the SQLAlchemy engine."""
    global engine
    
    if engine is not None:
        return engine
    
    if not DATABASE_URL:
        logger.error("DATABASE_URL environment variable is not set!")
        logger.error("Please set DATABASE_URL to your PostgreSQL connection string.")
        logger.error("Example: postgresql://user:password@host:port/database")
        raise RuntimeError(
            "DATABASE_URL not configured. Cannot connect to PostgreSQL database. "
            "Please set the DATABASE_URL environment variable."
        )
    
    try:
        engine = create_engine(
            DATABASE_URL,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=300,    # Recycle connections after 5 minutes
            echo=False           # Set to True for SQL debugging
        )
        logger.info(f"Database engine created successfully")
        return engine
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        raise RuntimeError(f"Failed to connect to database: {e}")


def get_session_factory():
    """Get or create the session factory."""
    global SessionLocal
    
    if SessionLocal is not None:
        return SessionLocal
    
    eng = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    return SessionLocal


def get_db():
    """
    Dependency for FastAPI/Flask routes to get a database session.
    Yields a session and ensures it's closed after use.
    """
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """
    Context manager for getting a database session.
    Use this in non-route code.
    
    Example:
        with get_db_session() as db:
            customers = db.query(Customer).all()
    """
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_db_connection():
    """
    Verify that the database connection is working.
    Returns True if connection is successful, raises exception otherwise.
    """
    try:
        eng = get_engine()
        with eng.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        logger.info("Database connection verified successfully")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise RuntimeError(f"Cannot connect to database: {e}")


def init_db():
    """
    Initialize the database by creating all tables.
    This should be called at application startup after migrations.
    """
    # Import models to ensure they're registered with Base
    from database import models  # noqa: F401
    
    eng = get_engine()
    Base.metadata.create_all(bind=eng)
    logger.info("Database tables created/verified")


def is_db_configured():
    """Check if DATABASE_URL is configured (without failing)."""
    return bool(DATABASE_URL)


# Initialize engine and session factory at module load if DATABASE_URL is set
if DATABASE_URL:
    try:
        engine = get_engine()
        SessionLocal = get_session_factory()
    except Exception as e:
        logger.warning(f"Database initialization deferred: {e}")

