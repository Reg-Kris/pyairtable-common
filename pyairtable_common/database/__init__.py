"""
Database utilities and SQLAlchemy integration for PyAirtable services.
"""
from .base import (
    Base,
    BaseModel,
    AuditableModel,
    TimestampMixin,
    UUIDMixin,
    CorrelationMixin,
    SoftDeleteMixin,
    AuditMixin,
    ConversationBase,
    MetricsBase,
    AuditBase,
    ConfigBase,
    create_all_schemas,
    create_all_schemas_async,
)
from .engine import (
    DatabaseManager,
    get_database_manager,
    get_db_session,
)
from .session import (
    Repository,
    UnitOfWork,
    get_unit_of_work,
    get_repository,
    health_check_database,
    get_database_info,
)

__all__ = [
    # Base classes and mixins
    'Base',
    'BaseModel',
    'AuditableModel',
    'TimestampMixin',
    'UUIDMixin',
    'CorrelationMixin',
    'SoftDeleteMixin',
    'AuditMixin',
    'ConversationBase',
    'MetricsBase',
    'AuditBase',
    'ConfigBase',
    'create_all_schemas',
    'create_all_schemas_async',
    # Engine and connection management
    'DatabaseManager',
    'get_database_manager',
    'get_db_session',
    # Repository and session management
    'Repository',
    'UnitOfWork',
    'get_unit_of_work',
    'get_repository',
    'health_check_database',
    'get_database_info',
]