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
from .security import (
    SecurityHeadersMiddleware,
    setup_security_middleware,
    constant_time_compare,
    verify_api_key_secure
)
from .setup import setup_middleware
from .circuit_breaker import CircuitBreakerMiddleware, add_circuit_breaker_middleware, SERVICE_CONFIGS

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
    'SecurityHeadersMiddleware',
    'setup_security_middleware',
    'constant_time_compare',
    'verify_api_key_secure',
    'setup_middleware',
    'CircuitBreakerMiddleware',
    'add_circuit_breaker_middleware',
    'SERVICE_CONFIGS',
]