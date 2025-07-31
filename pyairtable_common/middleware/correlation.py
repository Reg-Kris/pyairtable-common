"""
Correlation ID middleware for request tracking.
"""
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..logging import set_correlation_id, get_logger

logger = get_logger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to handle correlation ID for request tracking."""
    
    def __init__(self, app, header_name: str = "X-Request-ID"):
        super().__init__(app)
        self.header_name = header_name
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with correlation ID."""
        
        # Get or generate correlation ID
        correlation_id = request.headers.get(self.header_name)
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Set in context
        set_correlation_id(correlation_id)
        
        # Add to request state
        request.state.correlation_id = correlation_id
        
        # Process request
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Add correlation ID to response headers
            response.headers[self.header_name] = correlation_id
            
            # Log request completion
            duration = time.time() - start_time
            logger.info(
                "Request completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=duration,
                correlation_id=correlation_id
            )
            
            return response
            
        except Exception as exc:
            # Log request error
            duration = time.time() - start_time
            logger.error(
                "Request failed",
                method=request.method,
                path=request.url.path,
                duration=duration,
                correlation_id=correlation_id,
                error=str(exc),
                exc_info=True
            )
            raise


async def correlation_id_middleware(request: Request, call_next: Callable) -> Response:
    """Function-based correlation ID middleware."""
    
    # Get or generate correlation ID
    correlation_id = request.headers.get("X-Request-ID")
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
    
    # Set in context and request state
    set_correlation_id(correlation_id)
    request.state.correlation_id = correlation_id
    
    # Process request
    response = await call_next(request)
    
    # Add to response headers
    response.headers["X-Request-ID"] = correlation_id
    
    return response