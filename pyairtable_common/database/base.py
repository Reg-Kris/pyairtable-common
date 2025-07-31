"""
Base SQLAlchemy models and utilities for PyAirtable services.
"""
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import Column, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import Mapped

from ..logging import get_correlation_id

# Base class for all SQLAlchemy models
Base = declarative_base()


class TimestampMixin:
    """Mixin for automatic timestamp tracking."""
    
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp"
    )
    
    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Record last update timestamp"
    )


class UUIDMixin:
    """Mixin for UUID primary keys."""
    
    id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique identifier"
    )


class CorrelationMixin:
    """Mixin for correlation ID tracking."""
    
    correlation_id: Mapped[Optional[str]] = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Request correlation ID for tracing"
    )
    
    def set_correlation_id(self, correlation_id: Optional[str] = None):
        """Set correlation ID from context or provided value."""
        if correlation_id is None:
            correlation_id = get_correlation_id()
        self.correlation_id = correlation_id


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""
    
    deleted_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Soft delete timestamp"
    )
    
    @property
    def is_deleted(self) -> bool:
        """Check if record is soft deleted."""
        return self.deleted_at is not None
    
    def soft_delete(self):
        """Mark record as soft deleted."""
        self.deleted_at = datetime.utcnow()
    
    def restore(self):
        """Restore soft deleted record."""
        self.deleted_at = None


class AuditMixin:
    """Mixin for audit trail tracking."""
    
    created_by: Mapped[Optional[str]] = Column(
        String(255),
        nullable=True,
        comment="User who created the record"
    )
    
    updated_by: Mapped[Optional[str]] = Column(
        String(255),
        nullable=True,
        comment="User who last updated the record"
    )
    
    version: Mapped[int] = Column(
        "version",
        nullable=False,
        default=1,
        comment="Optimistic locking version"
    )


class BaseModel(Base, UUIDMixin, TimestampMixin, CorrelationMixin):
    """
    Base model class with common functionality.
    
    Includes:
    - UUID primary key
    - Automatic timestamps (created_at, updated_at)
    - Correlation ID tracking
    - Abstract base (no table created)
    """
    
    __abstract__ = True
    
    def __repr__(self) -> str:
        """String representation of the model."""
        return f"<{self.__class__.__name__}(id={self.id})>"
    
    def to_dict(self, exclude: Optional[set] = None) -> Dict[str, Any]:
        """Convert model to dictionary representation."""
        exclude = exclude or set()
        result = {}
        
        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                # Handle UUID and datetime serialization
                if isinstance(value, uuid.UUID):
                    value = str(value)
                elif isinstance(value, datetime):
                    value = value.isoformat()
                result[column.name] = value
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseModel":
        """Create model instance from dictionary."""
        # Filter out keys that don't correspond to columns
        valid_columns = {column.name for column in cls.__table__.columns}
        filtered_data = {k: v for k, v in data.items() if k in valid_columns}
        
        return cls(**filtered_data)


class AuditableModel(BaseModel, AuditMixin, SoftDeleteMixin):
    """
    Auditable model with full audit trail and soft delete.
    
    Includes all BaseModel features plus:
    - Audit trail (created_by, updated_by, version)
    - Soft delete functionality
    """
    
    __abstract__ = True


class SchemaAwareMixin:
    """Mixin for models that need explicit schema specification."""
    
    @declared_attr
    def __table_args__(cls):
        """Set table arguments including schema."""
        schema = getattr(cls, '__schema__', None)
        if schema:
            return {'schema': schema}
        return {}


# Schema-specific base classes
class ConversationBase(BaseModel, SchemaAwareMixin):
    """Base class for conversation-related models."""
    __abstract__ = True
    __schema__ = 'conversations'


class MetricsBase(BaseModel, SchemaAwareMixin):
    """Base class for metrics-related models."""
    __abstract__ = True
    __schema__ = 'metrics'


class AuditBase(AuditableModel, SchemaAwareMixin):
    """Base class for audit-related models."""
    __abstract__ = True
    __schema__ = 'audit'


class ConfigBase(BaseModel, SchemaAwareMixin):
    """Base class for configuration-related models."""
    __abstract__ = True
    __schema__ = 'config'


# Utility functions for model operations
def create_all_schemas(engine):
    """Create all database schemas."""
    schemas = ['conversations', 'metrics', 'audit', 'config']
    
    with engine.begin() as conn:
        for schema in schemas:
            conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")


async def create_all_schemas_async(engine):
    """Create all database schemas asynchronously."""
    schemas = ['conversations', 'metrics', 'audit', 'config']
    
    async with engine.begin() as conn:
        for schema in schemas:
            await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")


def get_model_by_tablename(tablename: str) -> Optional[type]:
    """Get model class by table name."""
    for cls in Base.registry._class_registry.values():
        if hasattr(cls, '__tablename__') and cls.__tablename__ == tablename:
            return cls
    return None