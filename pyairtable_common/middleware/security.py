"""
Security middleware for FastAPI applications
Adds standard security headers to all responses
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time
import secrets
import hmac
import hashlib


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self'"
        )
        
        # Remove server header for security
        if "server" in response.headers:
            del response.headers["server"]
        
        return response


def constant_time_compare(a: str, b: str) -> bool:
    """
    Constant-time string comparison to prevent timing attacks
    
    Args:
        a: First string to compare
        b: Second string to compare
        
    Returns:
        bool: True if strings are equal, False otherwise
    """
    if len(a) != len(b):
        return False
    
    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)
    
    return result == 0


def verify_api_key_secure(provided_key: str, expected_key: str) -> bool:
    """
    Secure API key verification using constant-time comparison
    
    Args:
        provided_key: API key provided in request
        expected_key: Expected API key value
        
    Returns:
        bool: True if keys match, False otherwise
    """
    if not provided_key or not expected_key:
        return False
    
    return constant_time_compare(provided_key, expected_key)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware"""
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host
        now = time.time()
        
        # Clean old entries
        cutoff = now - self.period
        self.clients = {
            ip: [timestamp for timestamp in timestamps if timestamp > cutoff]
            for ip, timestamps in self.clients.items()
        }
        
        # Check rate limit
        client_requests = self.clients.get(client_ip, [])
        if len(client_requests) >= self.calls:
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded"},
                headers={
                    "Retry-After": str(self.period),
                    "X-RateLimit-Limit": str(self.calls),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now + self.period))
                }
            )
        
        # Record request
        client_requests.append(now)
        self.clients[client_ip] = client_requests
        
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = max(0, self.calls - len(client_requests))
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + self.period))
        
        return response


def setup_security_middleware(app, rate_limit_calls: int = 100, rate_limit_period: int = 60):
    """
    Setup security middleware for FastAPI application
    
    Args:
        app: FastAPI application instance
        rate_limit_calls: Number of calls allowed per period
        rate_limit_period: Time period in seconds
    """
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware, calls=rate_limit_calls, period=rate_limit_period)