"""
Structured logging setup with correlation ID support.
"""
import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional

import structlog
from structlog.types import EventDict

# Context variable for correlation ID
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)

def set_correlation_id(cid: Optional[str] = None) -> str:
    """Set correlation ID in context."""
    if cid is None:
        cid = str(uuid.uuid4())
    correlation_id.set(cid)
    return cid

def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context."""
    return correlation_id.get()

def add_correlation_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add correlation ID to log event."""
    cid = get_correlation_id()
    if cid:
        event_dict['correlation_id'] = cid
    return event_dict

def add_service_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add service context to log event."""
    event_dict.setdefault('service', 'pyairtable-common')
    return event_dict

def setup_logging(
    service_name: str = "pyairtable-service",
    log_level: str = "INFO",
    log_format: str = "json",
    enable_console: bool = True
) -> None:
    """
    Setup structured logging with correlation ID support.
    
    Args:
        service_name: Name of the service for log context
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_format: Format type ('json' or 'console')
        enable_console: Whether to enable console output
    """
    
    # Configure structlog processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_correlation_id,
        add_service_context,
    ]
    
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.processors.CallsiteParameterAdder())
        processors.append(structlog.dev.ConsoleRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout if enable_console else None,
        level=getattr(logging, log_level.upper()),
    )
    
    # Set service name in context
    logger = structlog.get_logger()
    logger = logger.bind(service=service_name)
    
    return logger

def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """Get a logger instance with the given name."""
    return structlog.get_logger(name)