"""
Alembic environment configuration for PyAirtable database migrations.
"""
import asyncio
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine
from alembic import context

# Import the Base and all models to ensure they're registered
from pyairtable_common.database.base import Base
from pyairtable_common.models.conversations import ConversationSession, Message, ToolExecution

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the target metadata for 'autogenerate' support
target_metadata = Base.metadata

def get_database_url():
    """Get database URL from environment or config."""
    # Try environment variables first
    url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    
    if url:
        # Convert postgres:// to postgresql+asyncpg://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif not url.startswith("postgresql+asyncpg://"):
            # Assume it needs the asyncpg driver
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    else:
        # Fallback to config file
        url = config.get_main_option("sqlalchemy.url")
    
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Include schemas in offline mode
        include_schemas=True,
        # Schema order for creation
        version_table_schema=None,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Run migrations with the given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Include schemas
        include_schemas=True,
        # Schema order for creation  
        version_table_schema=None,
        # Compare types for better autogeneration
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        # Create schemas first
        schemas = ['conversations', 'metrics', 'audit', 'config']
        for schema in schemas:
            context.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        
        context.run_migrations()


async def run_async_migrations():
    """Run migrations in async mode."""
    from sqlalchemy.ext.asyncio import create_async_engine
    
    database_url = get_database_url()
    
    # Create async engine
    connectable = create_async_engine(
        database_url,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Check if we should run in async mode
    if config.get_main_option("sqlalchemy.url", "").startswith("postgresql+asyncpg"):
        asyncio.run(run_async_migrations())
    else:
        # Fallback to sync mode
        configuration = config.get_section(config.config_ini_section)
        configuration["sqlalchemy.url"] = get_database_url()
        connectable = engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()