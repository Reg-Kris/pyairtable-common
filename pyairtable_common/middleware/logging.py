"""
Request logging middleware.
"""
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request logging."""
    
    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details."""
        
        # Skip logging for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        start_time = time.time()
        
        # Log request start
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log successful response
            logger.info(
                "Request completed successfully",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=duration,
                response_size=response.headers.get("content-length"),
            )
            
            return response
            
        except Exception as exc:
            # Calculate duration
            duration = time.time() - start_time
            
            # Log error response
            logger.error(
                "Request failed with exception",
                method=request.method,
                path=request.url.path,
                duration=duration,
                error_type=type(exc).__name__,
                error_message=str(exc),
                exc_info=True
            )
            
            raise


async def request_logging_middleware(request: Request, call_next: Callable) -> Response:
    """Function-based request logging middleware."""
    
    # Skip health checks and metrics
    if request.url.path in ["/health", "/metrics"]:
        return await call_next(request)
    
    start_time = time.time()
    
    # Log request
    logger.info(
        "Processing request",
        method=request.method,
        path=request.url.path,
        client_ip=request.client.host if request.client else None,
    )
    
    try:
        response = await call_next(request)
        
        duration = time.time() - start_time
        logger.info(
            "Request processed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=duration,
        )
        
        return response
        
    except Exception as exc:
        duration = time.time() - start_time
        logger.error(
            "Request processing failed",
            method=request.method,
            path=request.url.path,
            duration=duration,
            error=str(exc),
            exc_info=True
        )
        raise