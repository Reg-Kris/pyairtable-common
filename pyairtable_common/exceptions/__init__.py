"""
Custom exceptions for PyAirtable services.
"""
from .errors import (
    PyAirtableError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ConflictError,
    RateLimitError,
    ExternalServiceError,
    AirtableAPIError,
    ConfigurationError,
    TimeoutError,
    CircuitBreakerError,
)

__all__ = [
    'PyAirtableError',
    'ValidationError',
    'AuthenticationError',
    'AuthorizationError',
    'NotFoundError',
    'ConflictError',
    'RateLimitError',
    'ExternalServiceError',
    'AirtableAPIError',
    'ConfigurationError',
    'TimeoutError',
    'CircuitBreakerError',
]