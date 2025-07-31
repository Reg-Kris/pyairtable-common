"""
Database migration utilities using Alembic.
"""
import os
import asyncio
from pathlib import Path
from typing import Optional
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text

from .engine import get_database_manager
from ..logging import get_logger

logger = get_logger(__name__)


class MigrationManager:
    """Manages database migrations using Alembic."""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url
        self.migrations_dir = Path(__file__).parent / "migrations"
        self.alembic_ini = self.migrations_dir / "alembic.ini"
    
    def get_alembic_config(self) -> Config:
        """Get Alembic configuration."""
        config = Config(str(self.alembic_ini))
        
        # Set database URL from environment or parameter
        if self.database_url:
            config.set_main_option("sqlalchemy.url", self.database_url)
        else:
            db_manager = get_database_manager()
            config.set_main_option("sqlalchemy.url", db_manager.database_url)
        
        # Set script location
        config.set_main_option("script_location", str(self.migrations_dir))
        
        return config
    
    async def create_schemas(self):
        """Create database schemas if they don't exist."""
        db_manager = get_database_manager()
        
        schemas = ['conversations', 'metrics', 'audit', 'config']
        
        async with db_manager.get_session() as session:
            for schema in schemas:
                await session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
                logger.info(f"Ensured schema exists: {schema}")
            
            await session.commit()
    
    def init_migrations(self):
        """Initialize Alembic migrations (creates initial migration structure)."""
        config = self.get_alembic_config()
        
        try:
            command.init(config, str(self.migrations_dir))
            logger.info("Initialized Alembic migrations")
        except Exception as e:
            logger.error(f"Failed to initialize migrations: {e}")
            raise
    
    def create_migration(self, message: str, autogenerate: bool = True):
        """Create a new migration."""
        config = self.get_alembic_config()
        
        try:
            command.revision(
                config,
                message=message,
                autogenerate=autogenerate
            )
            logger.info(f"Created migration: {message}")
        except Exception as e:
            logger.error(f"Failed to create migration: {e}")
            raise
    
    async def upgrade_database(self, revision: str = "head"):
        """Upgrade database to specified revision."""
        # Create schemas first
        await self.create_schemas()
        
        config = self.get_alembic_config()
        
        try:
            command.upgrade(config, revision)
            logger.info(f"Upgraded database to revision: {revision}")
        except Exception as e:
            logger.error(f"Failed to upgrade database: {e}")
            raise
    
    def downgrade_database(self, revision: str):
        """Downgrade database to specified revision."""
        config = self.get_alembic_config()
        
        try:
            command.downgrade(config, revision)
            logger.info(f"Downgraded database to revision: {revision}")
        except Exception as e:
            logger.error(f"Failed to downgrade database: {e}")
            raise
    
    def get_current_revision(self) -> Optional[str]:
        """Get current database revision."""
        config = self.get_alembic_config()
        
        try:
            from alembic.runtime.migration import MigrationContext
            from alembic.script import ScriptDirectory
            
            script = ScriptDirectory.from_config(config)
            
            def get_revision(connection):
                context = MigrationContext.configure(connection)
                return context.get_current_revision()
            
            db_manager = get_database_manager()
            # This would need to be synchronous - consider using a sync connection
            # For now, return None and implement async version separately
            return None
            
        except Exception as e:
            logger.error(f"Failed to get current revision: {e}")
            return None
    
    def get_migration_history(self):
        """Get migration history."""
        config = self.get_alembic_config()
        
        try:
            command.history(config)
        except Exception as e:
            logger.error(f"Failed to get migration history: {e}")
            raise
    
    def show_current_revision(self):
        """Show current revision."""
        config = self.get_alembic_config()
        
        try:
            command.current(config)
        except Exception as e:
            logger.error(f"Failed to show current revision: {e}")
            raise


# Global migration manager instance
_migration_manager: Optional[MigrationManager] = None


def get_migration_manager(database_url: Optional[str] = None) -> MigrationManager:
    """Get or create migration manager instance."""
    global _migration_manager
    
    if _migration_manager is None:
        _migration_manager = MigrationManager(database_url)
    
    return _migration_manager


# Convenience functions
async def create_database_schemas():
    """Create all database schemas."""
    manager = get_migration_manager()
    await manager.create_schemas()


async def upgrade_database(revision: str = "head"):
    """Upgrade database to latest revision."""
    manager = get_migration_manager()
    await manager.upgrade_database(revision)


def create_migration(message: str, autogenerate: bool = True):
    """Create a new database migration."""
    manager = get_migration_manager()
    manager.create_migration(message, autogenerate)


async def initialize_database():
    """Initialize database with schemas and run all migrations."""
    logger.info("Initializing PyAirtable database...")
    
    try:
        # Create schemas first
        await create_database_schemas()
        
        # Run migrations
        await upgrade_database()
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


# CLI-style functions for direct use
def cli_create_migration(message: str):
    """CLI function to create migration."""
    try:
        create_migration(message)
        print(f"✅ Created migration: {message}")
    except Exception as e:
        print(f"❌ Failed to create migration: {e}")


def cli_upgrade_database():
    """CLI function to upgrade database."""
    try:
        asyncio.run(upgrade_database())
        print("✅ Database upgraded successfully")
    except Exception as e:
        print(f"❌ Failed to upgrade database: {e}")


def cli_initialize_database():
    """CLI function to initialize database."""
    try:
        asyncio.run(initialize_database())
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m pyairtable_common.database.migrations <command>")
        print("Commands:")
        print("  init                    - Initialize database")
        print("  upgrade                 - Upgrade to latest")
        print("  create <message>        - Create new migration")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "init":
        cli_initialize_database()
    elif command == "upgrade":
        cli_upgrade_database()
    elif command == "create" and len(sys.argv) > 2:
        message = " ".join(sys.argv[2:])
        cli_create_migration(message)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)