"""
Middleware setup utilities.
"""
from fastapi import FastAPI

from .correlation import CorrelationIdMiddleware
from .logging import LoggingMiddleware
from .errors import ErrorHandlingMiddleware


def setup_middleware(
    app: FastAPI,
    enable_correlation_id: bool = True,
    enable_request_logging: bool = True,
    enable_error_handling: bool = True,
    correlation_header: str = "X-Request-ID",
    exclude_log_paths: list = None
) -> None:
    """
    Setup common middleware for FastAPI application.
    
    Args:
        app: FastAPI application instance
        enable_correlation_id: Enable correlation ID middleware
        enable_request_logging: Enable request logging middleware
        enable_error_handling: Enable error handling middleware
        correlation_header: Header name for correlation ID
        exclude_log_paths: Paths to exclude from request logging
    """
    
    if exclude_log_paths is None:
        exclude_log_paths = ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
    
    # Add middleware in reverse order (last added = first executed)
    
    if enable_error_handling:
        app.add_middleware(ErrorHandlingMiddleware)
    
    if enable_request_logging:
        app.add_middleware(LoggingMiddleware, exclude_paths=exclude_log_paths)
    
    if enable_correlation_id:
        app.add_middleware(CorrelationIdMiddleware, header_name=correlation_header)