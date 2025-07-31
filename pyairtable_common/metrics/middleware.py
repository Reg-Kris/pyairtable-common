"""
FastAPI middleware for automatic metrics collection.

This module provides middleware that integrates with existing PyAirtable
middleware to collect HTTP request metrics automatically.
"""
import time
from typing import Callable, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import FastAPI

from ..logging import get_logger, get_correlation_id
from .core import MetricsCollector, metrics_registry

logger = get_logger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP request metrics."""
    
    def __init__(
        self,
        app,
        metrics_collector: Optional[MetricsCollector] = None,
        exclude_paths: Optional[list] = None,
        include_request_size: bool = True,
        include_response_size: bool = True
    ):
        super().__init__(app)
        self.metrics_collector = metrics_collector
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
        self.include_request_size = include_request_size
        self.include_response_size = include_response_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics."""
        
        # Skip metrics collection for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Skip if no metrics collector available
        if not self.metrics_collector:
            return await call_next(request)
        
        start_time = time.time()
        request_size = 0
        response_size = 0
        
        # Calculate request size if enabled
        if self.include_request_size:
            request_size = self._calculate_request_size(request)
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            
            # Calculate response size if enabled
            if self.include_response_size:
                response_size = self._calculate_response_size(response)
            
        except Exception as e:
            # Record error metrics
            self.metrics_collector.record_error(
                error_type=type(e).__name__,
                endpoint=request.url.path
            )
            
            # Log error with correlation ID
            correlation_id = get_correlation_id()
            logger.error(
                f"Request failed: {type(e).__name__}",
                correlation_id=correlation_id,
                method=request.method,
                path=request.url.path,
                error=str(e)
            )
            raise
        
        # Calculate duration and record metrics
        duration = time.time() - start_time
        
        self.metrics_collector.record_http_request(
            method=request.method,
            endpoint=self._normalize_endpoint(request.url.path),
            status_code=status_code,
            duration=duration,
            request_size=request_size,
            response_size=response_size
        )
        
        # Update active connections gauge (approximate)
        try:
            # This is a rough approximation - in production you might want
            # to track this more precisely
            self.metrics_collector.app_metrics.active_connections.labels(
                **metrics_registry.get_common_labels()
            ).inc()
        except Exception:
            pass  # Don't fail request if metrics update fails
        
        # Log request with correlation ID
        correlation_id = get_correlation_id()
        logger.info(
            f"Request completed",
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            duration=f"{duration:.3f}s"
        )
        
        return response
    
    def _calculate_request_size(self, request: Request) -> int:
        """Calculate approximate request size in bytes."""
        size = 0
        
        # Headers
        for name, value in request.headers.items():
            size += len(name) + len(value) + 4  # ": " and "\r\n"
        
        # Method and path
        size += len(request.method) + len(str(request.url)) + 12  # "HTTP/1.1\r\n"
        
        # Content length if available
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size += int(content_length)
            except ValueError:
                pass
        
        return size
    
    def _calculate_response_size(self, response: Response) -> int:
        """Calculate approximate response size in bytes."""
        size = 0
        
        # Headers
        for name, value in response.headers.items():
            size += len(name) + len(str(value)) + 4  # ": " and "\r\n"
        
        # Status line
        size += len(f"HTTP/1.1 {response.status_code}\r\n")
        
        # Content length if available
        content_length = response.headers.get("content-length")
        if content_length:
            try:
                size += int(content_length)
            except ValueError:
                pass
        
        return size
    
    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path for metrics (replace dynamic segments)."""
        # Replace UUIDs with placeholder
        import re
        
        # UUID pattern
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        path = re.sub(uuid_pattern, '{id}', path, flags=re.IGNORECASE)
        
        # Numeric IDs
        path = re.sub(r'/\d+(?=/|$)', '/{id}', path)
        
        # Common patterns
        path = re.sub(r'/app[A-Za-z0-9]+(?=/|$)', '/app{id}', path)  # Airtable app IDs
        path = re.sub(r'/tbl[A-Za-z0-9]+(?=/|$)', '/tbl{id}', path)  # Airtable table IDs
        path = re.sub(r'/rec[A-Za-z0-9]+(?=/|$)', '/rec{id}', path)  # Airtable record IDs
        
        return path


class AirtableMetricsMiddleware(BaseHTTPMiddleware):
    """Middleware specifically for Airtable API metrics collection."""
    
    def __init__(
        self,
        app,
        metrics_collector: Optional[MetricsCollector] = None
    ):
        super().__init__(app)
        self.metrics_collector = metrics_collector
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process Airtable-specific metrics."""
        
        if not self.metrics_collector:
            return await call_next(request)
        
        # Extract Airtable context from request
        airtable_context = self._extract_airtable_context(request)
        
        if not airtable_context:
            return await call_next(request)
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Record Airtable API metrics
            duration = time.time() - start_time
            self.metrics_collector.record_airtable_request(
                base_id=airtable_context.get('base_id', 'unknown'),
                table_name=airtable_context.get('table_name', 'unknown'),
                operation=airtable_context.get('operation', 'unknown'),
                status_code=response.status_code,
                duration=duration
            )
            
            # Check for rate limit headers
            self._check_rate_limit_headers(response, airtable_context)
            
            return response
            
        except Exception as e:
            # Record error metrics
            self.metrics_collector.record_error(
                error_type=type(e).__name__,
                endpoint=f"airtable/{airtable_context.get('operation', 'unknown')}"
            )
            raise
    
    def _extract_airtable_context(self, request: Request) -> Optional[dict]:
        """Extract Airtable context from request."""
        # This would be implemented based on your specific routing patterns
        # For example, if you have paths like /airtable/{base_id}/{table_name}
        
        path_parts = request.url.path.strip('/').split('/')
        
        # Example pattern matching - adjust based on your actual routes
        if len(path_parts) >= 3 and path_parts[0] == 'airtable':
            base_id = path_parts[1] if path_parts[1].startswith('app') else 'unknown'
            table_name = path_parts[2] if len(path_parts) > 2 else 'unknown'
            
            # Determine operation from HTTP method and path
            operation = self._determine_operation(request.method, path_parts)
            
            return {
                'base_id': base_id,
                'table_name': table_name,
                'operation': operation
            }
        
        return None
    
    def _determine_operation(self, method: str, path_parts: list) -> str:
        """Determine Airtable operation from HTTP method and path."""
        if method == 'GET':
            return 'list' if len(path_parts) <= 3 else 'get'
        elif method == 'POST':
            return 'create'
        elif method == 'PATCH':
            return 'update'
        elif method == 'PUT':
            return 'replace'
        elif method == 'DELETE':
            return 'delete'
        else:
            return 'unknown'
    
    def _check_rate_limit_headers(self, response: Response, context: dict):
        """Check response for rate limit headers and update metrics."""
        # Check for Airtable rate limit headers
        remaining_header = response.headers.get('x-ratelimit-remaining')
        if remaining_header:
            try:
                remaining = int(remaining_header)
                self.metrics_collector.update_rate_limit_remaining(
                    base_id=context.get('base_id', 'unknown'),
                    limit_type='api',
                    remaining=remaining
                )
            except ValueError:
                pass
        
        # Check if rate limited
        if response.status_code == 429:
            self.metrics_collector.record_rate_limit_hit(
                base_id=context.get('base_id', 'unknown'),
                limit_type='api'
            )


def setup_metrics_middleware(
    app: FastAPI,
    metrics_collector: MetricsCollector,
    enable_http_metrics: bool = True,
    enable_airtable_metrics: bool = False,
    exclude_paths: Optional[list] = None
) -> None:
    """
    Setup metrics middleware for FastAPI application.
    
    Args:
        app: FastAPI application instance
        metrics_collector: MetricsCollector instance
        enable_http_metrics: Enable HTTP request metrics
        enable_airtable_metrics: Enable Airtable-specific metrics
        exclude_paths: Paths to exclude from metrics collection
    """
    
    # Add middleware in reverse order (last added = first executed)
    
    if enable_airtable_metrics:
        app.add_middleware(
            AirtableMetricsMiddleware,
            metrics_collector=metrics_collector
        )
        logger.info("Airtable metrics middleware enabled")
    
    if enable_http_metrics:
        app.add_middleware(
            MetricsMiddleware,
            metrics_collector=metrics_collector,
            exclude_paths=exclude_paths
        )
        logger.info("HTTP metrics middleware enabled")


def create_metrics_endpoint(app: FastAPI, metrics_collector: MetricsCollector):
    """Create /metrics endpoint for Prometheus scraping."""
    
    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        """Prometheus metrics endpoint."""
        from prometheus_client import CONTENT_TYPE_LATEST
        from starlette.responses import Response
        
        metrics_data = metrics_collector.export_metrics()
        return Response(
            content=metrics_data,
            media_type=CONTENT_TYPE_LATEST
        )
    
    logger.info("Metrics endpoint created at /metrics")