"""
FastAPI middleware for common functionality.
"""
from .correlation import CorrelationIdMiddleware, correlation_id_middleware
from .logging import LoggingMiddleware, request_logging_middleware
from .errors import ErrorHandlingMiddleware, error_handling_middleware
from .rate_limit import (
    RateLimitMiddleware,
    AirtableRateLimitMiddleware,
    api_key_rate_limit_key,
    user_rate_limit_key,
    service_rate_limit_key,
)
from .setup import setup_middleware

__all__ = [
    'CorrelationIdMiddleware',
    'correlation_id_middleware',
    'LoggingMiddleware',
    'request_logging_middleware',
    'ErrorHandlingMiddleware',
    'error_handling_middleware',
    'RateLimitMiddleware',
    'AirtableRateLimitMiddleware',
    'api_key_rate_limit_key',
    'user_rate_limit_key',
    'service_rate_limit_key',
    'setup_middleware',
]