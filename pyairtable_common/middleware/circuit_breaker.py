"""
Circuit breaker middleware for FastAPI applications
"""

import asyncio
import logging
import time
from typing import Callable, Optional, Any, Dict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from fastapi import status

from ..resilience import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerException, circuit_breaker_registry

logger = logging.getLogger(__name__)


class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add circuit breaker protection to API endpoints
    
    Features:
    - Per-endpoint circuit breakers
    - Automatic failure detection
    - Graceful degradation responses
    - Monitoring and metrics
    """
    
    def __init__(
        self,
        app,
        default_config: Optional[CircuitBreakerConfig] = None,
        endpoint_configs: Optional[Dict[str, CircuitBreakerConfig]] = None
    ):
        super().__init__(app)
        self.default_config = default_config or CircuitBreakerConfig(
            failure_threshold=5,
            success_threshold=3,
            timeout=60,
            response_timeout=30
        )
        self.endpoint_configs = endpoint_configs or {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through circuit breaker protection
        """
        # Skip circuit breaker for health checks and monitoring endpoints
        if self._should_skip_circuit_breaker(request.url.path):
            return await call_next(request)
        
        # Create circuit breaker name based on endpoint
        endpoint_name = self._get_endpoint_name(request)
        config = self.endpoint_configs.get(endpoint_name, self.default_config)
        
        # Get or create circuit breaker
        breaker = await circuit_breaker_registry.get_breaker(endpoint_name, config)
        
        # Add circuit breaker info to request state
        request.state.circuit_breaker = breaker
        request.state.endpoint_name = endpoint_name
        
        # Execute request through circuit breaker
        async def execute_request():
            return await call_next(request)
        
        start_time = time.time()
        
        try:
            # Execute through circuit breaker
            response = await breaker.call(execute_request)
            
            # Log successful request
            response_time_ms = int((time.time() - start_time) * 1000)
            logger.debug(f"Circuit breaker success: {endpoint_name} ({response_time_ms}ms)")
            
            return response
            
        except CircuitBreakerException as e:
            # Circuit breaker is open - return service unavailable
            logger.warning(f"Circuit breaker open for {endpoint_name}: {e}")
            
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "error": "Service temporarily unavailable",
                    "message": "The service is experiencing issues and is temporarily unavailable. Please try again later.",
                    "circuit_breaker": {
                        "endpoint": endpoint_name,
                        "state": e.state.value,
                        "error_rate": e.stats.error_rate(),
                        "consecutive_failures": e.stats.consecutive_failures,
                        "retry_after": breaker.current_timeout
                    },
                    "timestamp": time.time()
                },
                headers={
                    "Retry-After": str(breaker.current_timeout),
                    "X-Circuit-Breaker-State": e.state.value
                }
            )
            
        except Exception as e:
            # Log and re-raise other exceptions
            response_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Circuit breaker error for {endpoint_name} ({response_time_ms}ms): {e}")
            raise
    
    def _should_skip_circuit_breaker(self, path: str) -> bool:
        """
        Determine if circuit breaker should be skipped for this path
        """
        skip_patterns = [
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/favicon.ico"
        ]
        
        return any(pattern in path for pattern in skip_patterns)
    
    def _get_endpoint_name(self, request: Request) -> str:
        """
        Generate circuit breaker name for the endpoint
        """
        method = request.method.lower()
        path = request.url.path
        
        # Normalize path (replace path parameters with placeholders)
        normalized_path = self._normalize_path(path)
        
        return f"{method}-{normalized_path.replace('/', '-').strip('-')}"
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize path by replacing dynamic segments with placeholders
        """
        # Simple pattern recognition for common REST patterns
        segments = path.split('/')
        normalized_segments = []
        
        for segment in segments:
            if not segment:
                continue
            
            # Check if segment looks like an ID (UUID, numeric, etc.)
            if (segment.isdigit() or 
                len(segment) == 36 and '-' in segment or  # UUID-like
                segment.startswith('session-') or
                segment.startswith('user-') or
                segment.startswith('app')):  # Airtable app ID
                normalized_segments.append('{id}')
            else:
                normalized_segments.append(segment)
        
        return '/' + '/'.join(normalized_segments)


def add_circuit_breaker_middleware(
    app,
    default_config: Optional[CircuitBreakerConfig] = None,
    endpoint_configs: Optional[Dict[str, CircuitBreakerConfig]] = None
):
    """
    Add circuit breaker middleware to FastAPI application
    
    Args:
        app: FastAPI application instance
        default_config: Default circuit breaker configuration
        endpoint_configs: Per-endpoint circuit breaker configurations
    """
    app.add_middleware(
        CircuitBreakerMiddleware,
        default_config=default_config,
        endpoint_configs=endpoint_configs
    )
    
    logger.info("✅ Circuit breaker middleware added to FastAPI application")


# Predefined configurations for common service types
SERVICE_CONFIGS = {
    "llm_service": CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout=120,  # LLM calls can take longer
        response_timeout=60,
        error_rate_threshold=0.3,  # 30% error rate
        slow_request_threshold=10000  # 10 seconds
    ),
    
    "api_gateway": CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=3,
        timeout=60,
        response_timeout=30,
        error_rate_threshold=0.5,  # 50% error rate
        slow_request_threshold=5000  # 5 seconds
    ),
    
    "database_service": CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout=30,
        response_timeout=10,
        error_rate_threshold=0.2,  # 20% error rate
        slow_request_threshold=2000  # 2 seconds
    ),
    
    "external_api": CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=3,
        timeout=300,  # External APIs can be unreliable
        response_timeout=30,
        error_rate_threshold=0.6,  # 60% error rate
        slow_request_threshold=15000  # 15 seconds
    )
}