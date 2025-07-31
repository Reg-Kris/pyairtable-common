"""
Database engine and connection management for PyAirtable services.
"""
import os
from typing import Any, Dict, Optional, AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import event
from sqlalchemy.engine import Engine

from ..logging import get_logger
from ..config.settings import get_common_settings

logger = get_logger(__name__)


class DatabaseManager:
    """Manages database connections and sessions for PyAirtable services."""
    
    def __init__(
        self,
        database_url: Optional[str] = None,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        echo: bool = False
    ):
        self.database_url = database_url or self._get_database_url()
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.echo = echo
        
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
    
    def _get_database_url(self) -> str:
        """Get database URL from environment or settings."""
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
            # Fallback to default local development URL
            url = "postgresql+asyncpg://postgres:postgres@localhost:5432/pyairtable_platform"
        
        return url
    
    @property
    def engine(self) -> AsyncEngine:
        """Get or create the database engine."""
        if self._engine is None:
            self._engine = create_async_engine(
                self.database_url,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_timeout=self.pool_timeout,
                pool_recycle=self.pool_recycle,
                echo=self.echo,
                # Connection arguments for asyncpg
                connect_args={
                    "server_settings": {
                        "application_name": "pyairtable_service",
                    }
                }
            )
            logger.info(
                "Database engine created",
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                database_url=self._mask_credentials(self.database_url)
            )
        
        return self._engine
    
    @property
    def session_factory(self) -> async_sessionmaker:
        """Get or create the session factory."""
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False
            )
        
        return self._session_factory
    
    async def create_session(self) -> AsyncSession:
        """Create a new database session."""
        return self.session_factory()
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session with automatic cleanup."""
        session = await self.create_session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check database connectivity and return health status."""
        try:
            async with self.get_session() as session:
                # Test basic connectivity
                result = await session.execute("SELECT 1 as health_check")
                health_result = result.scalar()
                
                if health_result == 1:
                    return {
                        "status": "healthy",
                        "database": "connected",
                        "url": self._mask_credentials(self.database_url)
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "database": "connection_error",
                        "error": "Unexpected health check result"
                    }
        
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "database": "connection_failed",
                "error": str(e),
                "url": self._mask_credentials(self.database_url)
            }
    
    async def close(self):
        """Close the database engine and all connections."""
        if self._engine:
            await self._engine.dispose()
            logger.info("Database engine closed")
    
    def _mask_credentials(self, url: str) -> str:
        """Mask sensitive credentials in database URL for logging."""
        if "@" in url:
            parts = url.split("@")
            if len(parts) == 2:
                schema_and_creds = parts[0]
                host_and_db = parts[1]
                
                if "://" in schema_and_creds:
                    schema, creds = schema_and_creds.split("://", 1)
                    if ":" in creds:
                        user, _ = creds.split(":", 1)
                        return f"{schema}://{user}:****@{host_and_db}"
        
        return url


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager(
    database_url: Optional[str] = None,
    **kwargs
) -> DatabaseManager:
    """Get or create the global database manager instance."""
    global _db_manager
    
    if _db_manager is None:
        settings = get_common_settings()
        
        # Use provided URL or get from settings/environment
        if database_url is None:
            database_url = getattr(settings, 'database_url', None)
        
        _db_manager = DatabaseManager(
            database_url=database_url,
            pool_size=getattr(settings, 'database_pool_size', 10),
            max_overflow=getattr(settings, 'database_max_overflow', 20),
            pool_timeout=getattr(settings, 'database_pool_timeout', 30),
            pool_recycle=getattr(settings, 'database_pool_recycle', 3600),
            echo=getattr(settings, 'database_echo', False)
        )
    
    return _db_manager


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency function for FastAPI to get database session."""
    db_manager = get_database_manager()
    async with db_manager.get_session() as session:
        yield session


# Connection event listeners for better logging
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set connection-level settings."""
    if hasattr(dbapi_connection, 'execute'):
        # This would be for SQLite, but we're using PostgreSQL
        pass


@event.listens_for(Engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log when a connection is checked out from the pool."""
    logger.debug("Database connection checked out from pool")