"""
Alembic migration environment configuration.
Configured to use DATABASE_URL from environment and our SQLAlchemy models.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our models and Base
from database.connection import Base, DATABASE_URL
from database import models  # noqa: F401 - Import to register models

# Alembic Config object
config = context.config

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the target metadata for autogenerate support
target_metadata = Base.metadata


def get_url():
    """Get database URL from environment."""
    url = os.environ.get('DATABASE_URL')
    if url and url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    return url


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    This generates SQL scripts without connecting to the database.
    """
    url = get_url()
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    This connects to the database and runs migrations directly.
    """
    url = get_url()
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    
    connectable = create_engine(url, poolclass=pool.NullPool)

    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
