"""
Custom exceptions for PyAirtable services.
"""
from typing import Any, Dict, List, Optional


class PyAirtableError(Exception):
    """Base exception for PyAirtable services."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "status_code": self.status_code,
            "error_code": self.error_code,
            "details": self.details,
        }


class ValidationError(PyAirtableError):
    """Validation error."""
    
    def __init__(
        self,
        message: str,
        errors: Optional[List[Dict[str, Any]]] = None,
        field: Optional[str] = None
    ):
        super().__init__(message, status_code=422, error_code="VALIDATION_ERROR")
        self.errors = errors or []
        self.field = field


class AuthenticationError(PyAirtableError):
    """Authentication error."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401, error_code="AUTH_ERROR")


class AuthorizationError(PyAirtableError):
    """Authorization error."""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, status_code=403, error_code="ACCESS_DENIED")


class NotFoundError(PyAirtableError):
    """Resource not found error."""
    
    def __init__(self, message: str = "Resource not found", resource_type: Optional[str] = None):
        super().__init__(message, status_code=404, error_code="NOT_FOUND")
        self.resource_type = resource_type


class ConflictError(PyAirtableError):
    """Resource conflict error."""
    
    def __init__(self, message: str = "Resource conflict", resource_id: Optional[str] = None):
        super().__init__(message, status_code=409, error_code="CONFLICT")
        self.resource_id = resource_id


class RateLimitError(PyAirtableError):
    """Rate limit exceeded error."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None
    ):
        super().__init__(message, status_code=429, error_code="RATE_LIMIT")
        self.retry_after = retry_after


class ExternalServiceError(PyAirtableError):
    """External service error."""
    
    def __init__(
        self,
        message: str,
        service_name: str,
        status_code: int = 502,
        upstream_status: Optional[int] = None
    ):
        super().__init__(message, status_code=status_code, error_code="EXTERNAL_SERVICE_ERROR")
        self.service_name = service_name
        self.upstream_status = upstream_status


class AirtableAPIError(ExternalServiceError):
    """Airtable API specific error."""
    
    def __init__(
        self,
        message: str,
        airtable_error_type: Optional[str] = None,
        upstream_status: Optional[int] = None
    ):
        super().__init__(
            message,
            service_name="airtable",
            status_code=502,
            upstream_status=upstream_status
        )
        self.airtable_error_type = airtable_error_type


class ConfigurationError(PyAirtableError):
    """Configuration error."""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(message, status_code=500, error_code="CONFIG_ERROR")
        self.config_key = config_key


class TimeoutError(PyAirtableError):
    """Operation timeout error."""
    
    def __init__(self, message: str = "Operation timed out", timeout_seconds: Optional[float] = None):
        super().__init__(message, status_code=408, error_code="TIMEOUT")
        self.timeout_seconds = timeout_seconds


class CircuitBreakerError(PyAirtableError):
    """Circuit breaker open error."""
    
    def __init__(self, message: str = "Service temporarily unavailable", service_name: Optional[str] = None):
        super().__init__(message, status_code=503, error_code="CIRCUIT_BREAKER_OPEN")
        self.service_name = service_name