"""
Custom log formatters for structured logging.
"""
import json
import traceback
from datetime import datetime
from typing import Any, Dict, Optional

import structlog
from structlog.types import EventDict


class CustomJSONFormatter:
    """Custom JSON formatter with enhanced fields."""
    
    def __call__(self, logger: Any, method_name: str, event_dict: EventDict) -> str:
        """Format log event as JSON."""
        
        # Ensure timestamp is ISO format
        if 'timestamp' not in event_dict:
            event_dict['timestamp'] = datetime.utcnow().isoformat() + 'Z'
            
        # Add severity level mapping
        level = event_dict.get('level', 'info').upper()
        event_dict['severity'] = level
        
        # Handle exceptions
        if 'exception' in event_dict:
            exc_info = event_dict.pop('exception')
            if exc_info:
                event_dict['error'] = {
                    'type': exc_info.__class__.__name__,
                    'message': str(exc_info),
                    'traceback': traceback.format_exception(
                        type(exc_info), exc_info, exc_info.__traceback__
                    )
                }
        
        # Ensure message field exists
        if 'event' in event_dict and 'message' not in event_dict:
            event_dict['message'] = event_dict['event']
            
        return json.dumps(event_dict, default=str, ensure_ascii=False)


class RequestFormatter:
    """Formatter for HTTP request logs."""
    
    def __call__(self, logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
        """Add request context to log event."""
        
        # Extract request info if available
        request = event_dict.get('request')
        if request:
            event_dict.update({
                'http': {
                    'method': getattr(request, 'method', None),
                    'url': str(getattr(request, 'url', '')),
                    'user_agent': getattr(request.headers, 'user-agent', None) if hasattr(request, 'headers') else None,
                    'remote_addr': getattr(request.client, 'host', None) if hasattr(request, 'client') else None,
                }
            })
            
        return event_dict


class PerformanceFormatter:
    """Formatter for performance metrics."""
    
    def __call__(self, logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
        """Add performance context to log event."""
        
        # Add timing information
        duration = event_dict.get('duration')
        if duration is not None:
            event_dict['performance'] = {
                'duration_ms': round(duration * 1000, 2),
                'slow_query': duration > 1.0,  # Flag slow operations
            }
            
        return event_dict


def create_audit_logger() -> structlog.stdlib.BoundLogger:
    """Create a dedicated audit logger."""
    
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        lambda logger, method_name, event_dict: {
            **event_dict,
            'audit': True,
            'service': 'pyairtable-audit'
        },
        structlog.processors.JSONRenderer()
    ]
    
    structlog.configure_once(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger("audit")


def create_security_logger() -> structlog.stdlib.BoundLogger:
    """Create a dedicated security logger."""
    
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        lambda logger, method_name, event_dict: {
            **event_dict,
            'security': True,
            'service': 'pyairtable-security'
        },
        structlog.processors.JSONRenderer()
    ]
    
    structlog.configure_once(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger("security")