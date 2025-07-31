"""
Rate limiting middleware for FastAPI applications.
"""
import hashlib
from typing import Callable, Dict, Any, Optional

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from ..utils.rate_limiter import RateLimiter, AirtableRateLimiter
from ..logging import get_logger
from ..exceptions import RateLimitError

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Generic rate limiting middleware."""
    
    def __init__(
        self,
        app,
        rate_limiter: RateLimiter,
        default_limit: int = 60,
        default_window: int = 60,
        algorithm: str = "sliding_window",
        key_func: Optional[Callable[[Request], str]] = None,
        exclude_paths: list = None
    ):
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.default_limit = default_limit
        self.default_window = default_window
        self.algorithm = algorithm
        self.key_func = key_func or self._default_key_func
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
    
    def _default_key_func(self, request: Request) -> str:
        """Default key function using client IP."""
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting to request."""
        
        # Skip rate limiting for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Generate rate limit key
        key = self.key_func(request)
        
        try:
            # Check rate limit
            result = await self.rate_limiter.is_allowed(
                identifier=key,
                limit=self.default_limit,
                window_seconds=self.default_window,
                algorithm=self.algorithm
            )
            
            if not result["allowed"]:
                logger.warning(
                    "Rate limit exceeded",
                    key=key,
                    path=request.url.path,
                    limit=result["limit"],
                    retry_after=result["retry_after"]
                )
                
                # Return 429 Too Many Requests
                response = Response(
                    content='{"error": "Rate limit exceeded"}',
                    status_code=429,
                    media_type="application/json"
                )
                
                # Add rate limit headers
                response.headers["X-RateLimit-Limit"] = str(result["limit"])
                response.headers["X-RateLimit-Remaining"] = str(result["remaining"])
                response.headers["X-RateLimit-Reset"] = str(int(result["reset_time"]))
                response.headers["Retry-After"] = str(result["retry_after"])
                
                return response
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers to successful responses
            response.headers["X-RateLimit-Limit"] = str(result["limit"])
            response.headers["X-RateLimit-Remaining"] = str(result["remaining"])
            response.headers["X-RateLimit-Reset"] = str(int(result["reset_time"]))
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Continue without rate limiting if Redis is down
            return await call_next(request)


class AirtableRateLimitMiddleware(BaseHTTPMiddleware):
    """Airtable-specific rate limiting middleware."""
    
    def __init__(
        self,
        app,
        airtable_limiter: AirtableRateLimiter,
        exclude_paths: list = None
    ):
        super().__init__(app)
        self.airtable_limiter = airtable_limiter
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
    
    def _extract_base_id(self, path: str) -> Optional[str]:
        """Extract base ID from request path."""
        parts = path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] == "bases":
            return parts[1]
        return None
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for rate limiting key."""
        return hashlib.sha256(api_key.encode()).hexdigest()[:12]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply Airtable-specific rate limiting."""
        
        # Skip rate limiting for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Get API key from headers
        api_key = request.headers.get("x-api-key")
        if not api_key:
            return await call_next(request)
        
        try:
            # Check global rate limit first
            api_key_hash = self._hash_api_key(api_key)
            global_result = await self.airtable_limiter.check_global_limit(api_key_hash)
            
            if not global_result["allowed"]:
                return self._create_rate_limit_response(global_result, "global")
            
            # Check base-specific rate limit if applicable
            base_id = self._extract_base_id(request.url.path)
            if base_id:
                base_result = await self.airtable_limiter.check_base_limit(base_id)
                
                if not base_result["allowed"]:
                    return self._create_rate_limit_response(base_result, f"base:{base_id}")
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            if base_id:
                base_result = await self.airtable_limiter.check_base_limit(base_id)
                response.headers["X-RateLimit-Base-Limit"] = str(base_result["limit"])
                response.headers["X-RateLimit-Base-Remaining"] = str(base_result["remaining"])
            
            response.headers["X-RateLimit-Global-Limit"] = str(global_result["limit"])
            response.headers["X-RateLimit-Global-Remaining"] = str(global_result["remaining"])
            
            return response
            
        except Exception as e:
            logger.error(f"Airtable rate limiting error: {e}")
            # Continue without rate limiting if Redis is down
            return await call_next(request)
    
    def _create_rate_limit_response(self, result: Dict[str, Any], limit_type: str) -> Response:
        """Create rate limit error response."""
        logger.warning(
            f"Airtable rate limit exceeded",
            limit_type=limit_type,
            limit=result["limit"],
            retry_after=result["retry_after"]
        )
        
        response = Response(
            content=f'{{"error": "Rate limit exceeded for {limit_type}"}}',
            status_code=429,
            media_type="application/json"
        )
        
        response.headers["X-RateLimit-Limit"] = str(result["limit"])
        response.headers["X-RateLimit-Remaining"] = str(result["remaining"])
        response.headers["X-RateLimit-Reset"] = str(int(result["reset_time"]))
        response.headers["Retry-After"] = str(result["retry_after"])
        
        return response


def api_key_rate_limit_key(request: Request) -> str:
    """Rate limit key based on API key."""
    api_key = request.headers.get("x-api-key", "anonymous")
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:12]
    return f"api_key:{key_hash}"


def user_rate_limit_key(request: Request) -> str:
    """Rate limit key based on user ID."""
    user_id = request.headers.get("x-user-id")
    if user_id:
        return f"user:{user_id}"
    
    # Fallback to API key
    return api_key_rate_limit_key(request)


def service_rate_limit_key(service_name: str) -> Callable[[Request], str]:
    """Rate limit key for internal service calls."""
    def key_func(request: Request) -> str:
        return f"service:{service_name}"
    return key_func