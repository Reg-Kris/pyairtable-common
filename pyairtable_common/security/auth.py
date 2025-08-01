"""
Unified Authentication and Authorization Module for PyAirtable Services
Provides secure API key verification, JWT handling, and authentication utilities
"""

import os
import time
import hmac
import hashlib
import secrets
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from functools import wraps

import jwt
from fastapi import HTTPException, Header, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Security constants
MIN_API_KEY_LENGTH = 32
JWT_ALGORITHM = "HS256"
DEFAULT_TOKEN_EXPIRATION = 3600  # 1 hour

class AuthConfig(BaseModel):
    """Authentication configuration"""
    api_key: str
    jwt_secret: Optional[str] = None
    jwt_algorithm: str = JWT_ALGORITHM
    token_expiration: int = DEFAULT_TOKEN_EXPIRATION
    require_https: bool = True


class SecurityError(Exception):
    """Base security exception"""
    pass


class AuthenticationError(SecurityError):
    """Authentication failed"""
    pass


class AuthorizationError(SecurityError):
    """Authorization failed"""
    pass


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


def generate_secure_api_key(length: int = 64) -> str:
    """
    Generate a cryptographically secure API key
    
    Args:
        length: Length of the API key (minimum 32)
        
    Returns:
        str: Secure API key
    """
    if length < MIN_API_KEY_LENGTH:
        raise ValueError(f"API key length must be at least {MIN_API_KEY_LENGTH} characters")
    
    return secrets.token_urlsafe(length)


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
    
    # Hash both keys to ensure constant-time comparison even with different lengths
    provided_hash = hmac.new(
        b"pyairtable-key-verification",
        provided_key.encode(),
        hashlib.sha256
    ).hexdigest()
    
    expected_hash = hmac.new(
        b"pyairtable-key-verification", 
        expected_key.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return constant_time_compare(provided_hash, expected_hash)


class JWTManager:
    """JWT token management"""
    
    def __init__(self, secret_key: str, algorithm: str = JWT_ALGORITHM):
        if not secret_key or len(secret_key) < 32:
            raise ValueError("JWT secret key must be at least 32 characters long")
        
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def generate_token(self, payload: Dict[str, Any], expires_in: int = DEFAULT_TOKEN_EXPIRATION) -> str:
        """
        Generate a JWT token
        
        Args:
            payload: Token payload
            expires_in: Expiration time in seconds
            
        Returns:
            str: JWT token
        """
        now = datetime.utcnow()
        payload.update({
            'iat': now,
            'exp': now + timedelta(seconds=expires_in),
            'iss': 'pyairtable'
        })
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode a JWT token
        
        Args:
            token: JWT token to verify
            
        Returns:
            Dict[str, Any]: Decoded payload
            
        Raises:
            AuthenticationError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {e}")


class APIKeyAuth:
    """API Key authentication dependency"""
    
    def __init__(self, api_key: str, header_name: str = "X-API-Key"):
        self.api_key = api_key
        self.header_name = header_name
    
    def __call__(self, api_key: Optional[str] = Header(None, alias="X-API-Key")) -> bool:
        """Verify API key from header"""
        if not verify_api_key_secure(api_key or "", self.api_key):
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key"
            )
        return True


class JWTAuth:
    """JWT authentication dependency"""
    
    def __init__(self, jwt_manager: JWTManager):
        self.jwt_manager = jwt_manager
        self.bearer = HTTPBearer()
    
    def __call__(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> Dict[str, Any]:
        """Verify JWT token from Authorization header"""
        try:
            payload = self.jwt_manager.verify_token(credentials.credentials)
            return payload
        except AuthenticationError as e:
            raise HTTPException(status_code=401, detail=str(e))


class SecurityMiddleware:
    """Security middleware for API key validation and request logging"""
    
    def __init__(self, auth_config: AuthConfig):
        self.auth_config = auth_config
        self.jwt_manager = JWTManager(auth_config.jwt_secret) if auth_config.jwt_secret else None
    
    async def __call__(self, request: Request, call_next):
        """Process request with security checks"""
        start_time = time.time()
        
        # Log request
        logger.info(f"Request: {request.method} {request.url.path} from {request.client.host}")
        
        # Check HTTPS requirement
        if self.auth_config.require_https and request.url.scheme != "https":
            # Allow localhost for development
            if not str(request.client.host).startswith(("127.0.0.1", "localhost")):
                raise HTTPException(
                    status_code=403,
                    detail="HTTPS required"
                )
        
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(
            f"Response: {response.status_code} "
            f"in {process_time:.3f}s for {request.method} {request.url.path}"
        )
        
        return response


def require_api_key(api_key: str):
    """
    Decorator to require API key authentication
    
    Args:
        api_key: Expected API key value
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request and check for API key
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                raise AuthenticationError("Request object not found")
            
            provided_key = request.headers.get("X-API-Key")
            if not verify_api_key_secure(provided_key or "", api_key):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or missing API key"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def create_auth_dependencies(auth_config: AuthConfig):
    """
    Create authentication dependencies for FastAPI
    
    Args:
        auth_config: Authentication configuration
        
    Returns:
        Tuple of (api_key_auth, jwt_auth) dependencies
    """
    api_key_auth = APIKeyAuth(auth_config.api_key)
    jwt_auth = JWTAuth(JWTManager(auth_config.jwt_secret)) if auth_config.jwt_secret else None
    
    return api_key_auth, jwt_auth


def validate_api_key_strength(api_key: str) -> bool:
    """
    Validate API key meets security requirements
    
    Args:
        api_key: API key to validate
        
    Returns:
        bool: True if key meets requirements
    """
    if not api_key or len(api_key) < MIN_API_KEY_LENGTH:
        return False
    
    # Check for sufficient entropy (should have mixed case, numbers, special chars)
    has_lower = any(c.islower() for c in api_key)
    has_upper = any(c.isupper() for c in api_key)
    has_digit = any(c.isdigit() for c in api_key)
    has_special = any(c in "-_+=.,!@#$%^&*()[]{}|;:,.<>?" for c in api_key)
    
    return sum([has_lower, has_upper, has_digit, has_special]) >= 3


# Rate limiting utilities
class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clients: Dict[str, List[float]] = {}
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed for client"""
        now = time.time()
        cutoff = now - self.window_seconds
        
        # Clean old entries
        if client_id in self.clients:
            self.clients[client_id] = [
                timestamp for timestamp in self.clients[client_id]
                if timestamp > cutoff
            ]
        else:
            self.clients[client_id] = []
        
        # Check rate limit
        if len(self.clients[client_id]) >= self.max_requests:
            return False
        
        # Record request
        self.clients[client_id].append(now)
        return True
    
    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for client"""
        if client_id not in self.clients:
            return self.max_requests
        return max(0, self.max_requests - len(self.clients[client_id]))