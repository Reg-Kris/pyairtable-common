"""
Database session management and repository patterns for PyAirtable services.
"""
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic, Sequence
from contextlib import asynccontextmanager
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import NoResultFound, IntegrityError

from .base import BaseModel, AuditableModel
from .engine import get_database_manager
from ..logging import get_logger
from ..exceptions import NotFoundError, ConflictError, ValidationError

logger = get_logger(__name__)

# Type variable for generic repository
ModelType = TypeVar("ModelType", bound=BaseModel)


class DatabaseSession:
    """Enhanced database session wrapper with additional utilities."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def commit(self):
        """Commit the current transaction."""
        await self.session.commit()
    
    async def rollback(self):
        """Rollback the current transaction."""
        await self.session.rollback()
    
    async def close(self):
        """Close the session."""
        await self.session.close()
    
    async def refresh(self, instance: BaseModel):
        """Refresh an instance from the database."""
        await self.session.refresh(instance)
    
    async def flush(self):
        """Flush pending changes to the database."""
        await self.session.flush()


class Repository(Generic[ModelType]):
    """Generic repository pattern for database operations."""
    
    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        self.session = session
        self.model = model
    
    async def create(self, **kwargs) -> ModelType:
        """Create a new instance."""
        try:
            instance = self.model(**kwargs)
            
            # Set correlation ID if model supports it
            if hasattr(instance, 'set_correlation_id'):
                instance.set_correlation_id()
            
            self.session.add(instance)
            await self.session.flush()
            await self.session.refresh(instance)
            
            logger.debug(
                f"Created {self.model.__name__}",
                model=self.model.__name__,
                id=str(instance.id) if hasattr(instance, 'id') else None
            )
            
            return instance
            
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Integrity error creating {self.model.__name__}", error=str(e))
            raise ConflictError(f"Failed to create {self.model.__name__} due to constraint violation")
    
    async def get_by_id(self, id: Any) -> Optional[ModelType]:
        """Get instance by ID."""
        try:
            stmt = select(self.model).where(self.model.id == id)
            
            # Add soft delete filter if model supports it
            if hasattr(self.model, 'deleted_at'):
                stmt = stmt.where(self.model.deleted_at.is_(None))
            
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} by ID", id=str(id), error=str(e))
            return None
    
    async def get_by_id_or_404(self, id: Any) -> ModelType:
        """Get instance by ID or raise NotFoundError."""
        instance = await self.get_by_id(id)
        if instance is None:
            raise NotFoundError(f"{self.model.__name__} with id {id} not found")
        return instance
    
    async def get_all(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None
    ) -> List[ModelType]:
        """Get all instances with optional pagination."""
        stmt = select(self.model)
        
        # Add soft delete filter if model supports it
        if hasattr(self.model, 'deleted_at'):
            stmt = stmt.where(self.model.deleted_at.is_(None))
        
        # Add ordering
        if order_by and hasattr(self.model, order_by):
            stmt = stmt.order_by(getattr(self.model, order_by))
        elif hasattr(self.model, 'created_at'):
            stmt = stmt.order_by(self.model.created_at.desc())
        
        # Add pagination
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def find_by(self, **filters) -> List[ModelType]:
        """Find instances by filters."""
        stmt = select(self.model)
        
        # Add filters
        for key, value in filters.items():
            if hasattr(self.model, key):
                stmt = stmt.where(getattr(self.model, key) == value)
        
        # Add soft delete filter if model supports it
        if hasattr(self.model, 'deleted_at'):
            stmt = stmt.where(self.model.deleted_at.is_(None))
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def find_one_by(self, **filters) -> Optional[ModelType]:
        """Find single instance by filters."""
        instances = await self.find_by(**filters)
        return instances[0] if instances else None
    
    async def update(self, id: Any, **kwargs) -> Optional[ModelType]:
        """Update instance by ID."""
        instance = await self.get_by_id(id)
        if instance is None:
            return None
        
        try:
            # Update fields
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            
            # Update version for optimistic locking if supported
            if hasattr(instance, 'version'):
                instance.version += 1
            
            await self.session.flush()
            await self.session.refresh(instance)
            
            logger.debug(
                f"Updated {self.model.__name__}",
                model=self.model.__name__,
                id=str(instance.id)
            )
            
            return instance
            
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"Integrity error updating {self.model.__name__}", error=str(e))
            raise ConflictError(f"Failed to update {self.model.__name__} due to constraint violation")
    
    async def delete(self, id: Any) -> bool:
        """Delete instance by ID (hard delete)."""
        instance = await self.get_by_id(id)
        if instance is None:
            return False
        
        await self.session.delete(instance)
        await self.session.flush()
        
        logger.debug(
            f"Deleted {self.model.__name__}",
            model=self.model.__name__,
            id=str(id)
        )
        
        return True
    
    async def soft_delete(self, id: Any) -> bool:
        """Soft delete instance by ID."""
        instance = await self.get_by_id(id)
        if instance is None or not hasattr(instance, 'soft_delete'):
            return False
        
        instance.soft_delete()
        await self.session.flush()
        
        logger.debug(
            f"Soft deleted {self.model.__name__}",
            model=self.model.__name__,
            id=str(id)
        )
        
        return True
    
    async def count(self, **filters) -> int:
        """Count instances with optional filters."""
        stmt = select(func.count(self.model.id))
        
        # Add filters
        for key, value in filters.items():
            if hasattr(self.model, key):
                stmt = stmt.where(getattr(self.model, key) == value)
        
        # Add soft delete filter if model supports it
        if hasattr(self.model, 'deleted_at'):
            stmt = stmt.where(self.model.deleted_at.is_(None))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def exists(self, **filters) -> bool:
        """Check if instance exists with given filters."""
        count = await self.count(**filters)
        return count > 0


class UnitOfWork:
    """Unit of Work pattern for managing transactions across multiple repositories."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._repositories: Dict[Type[BaseModel], Repository] = {}
    
    def repository(self, model: Type[ModelType]) -> Repository[ModelType]:
        """Get or create repository for model."""
        if model not in self._repositories:
            self._repositories[model] = Repository(self.session, model)
        return self._repositories[model]
    
    async def commit(self):
        """Commit the unit of work."""
        await self.session.commit()
    
    async def rollback(self):
        """Rollback the unit of work."""
        await self.session.rollback()


@asynccontextmanager
async def get_unit_of_work():
    """Get unit of work with automatic session management."""
    db_manager = get_database_manager()
    async with db_manager.get_session() as session:
        uow = UnitOfWork(session)
        try:
            yield uow
            await uow.commit()
        except Exception:
            await uow.rollback()
            raise


@asynccontextmanager
async def get_repository(model: Type[ModelType]) -> Repository[ModelType]:
    """Get repository with automatic session management."""
    db_manager = get_database_manager()
    async with db_manager.get_session() as session:
        repository = Repository(session, model)
        try:
            yield repository
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Utility functions for common database operations
async def health_check_database() -> Dict[str, Any]:
    """Perform database health check."""
    db_manager = get_database_manager()
    return await db_manager.health_check()


async def get_database_info() -> Dict[str, Any]:
    """Get database connection information."""
    db_manager = get_database_manager()
    
    try:
        async with db_manager.get_session() as session:
            # Get PostgreSQL version
            result = await session.execute("SELECT version()")
            version = result.scalar()
            
            # Get database size
            result = await session.execute(
                "SELECT pg_size_pretty(pg_database_size(current_database()))"
            )
            size = result.scalar()
            
            return {
                "status": "connected",
                "version": version,
                "database_size": size,
                "url": db_manager._mask_credentials(db_manager.database_url)
            }
    
    except Exception as e:
        logger.error("Failed to get database info", error=str(e))
        return {
            "status": "error",
            "error": str(e)
        }