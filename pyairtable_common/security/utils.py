"""
Security Utility Functions for PyAirtable Services
Common security patterns and helper functions
"""

import os
import re
import hashlib
import secrets
import logging
from typing import Dict, List, Optional, Any, Tuple
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .auth import AuthConfig, create_auth_dependencies, verify_api_key_secure
from .cors import setup_cors_middleware
from ..config.secrets import SecureConfigManager, get_secret

logger = logging.getLogger(__name__)

@dataclass
class ServiceSecurityConfig:
    """Complete security configuration for a service"""
    service_name: str
    api_key: str
    jwt_secret: Optional[str] = None
    cors_origins: List[str] = None
    environment: str = "production"
    require_https: bool = True


class SecuritySetupError(Exception):
    """Error during security setup"""
    pass


def validate_environment_security() -> Dict[str, Any]:
    """
    Validate security configuration in current environment
    
    Returns:
        Dict containing security status and recommendations
    """
    environment = os.getenv("ENVIRONMENT", "production")
    issues = []
    recommendations = []
    
    # Check API key configuration
    api_key = os.getenv("API_KEY")
    if not api_key:
        issues.append("API_KEY environment variable is missing")
    elif len(api_key) < 32:
        issues.append(f"API_KEY too short ({len(api_key)} chars, minimum 32)")
    
    # Check CORS configuration
    cors_origins = os.getenv("CORS_ORIGINS", "")
    if environment == "production":
        if not cors_origins:
            issues.append("CORS_ORIGINS not configured for production")
        elif "*" in cors_origins:
            issues.append("Wildcard CORS origins not allowed in production")
    
    # Check HTTPS configuration
    require_https = os.getenv("REQUIRE_HTTPS", "true").lower() == "true"
    if environment == "production" and not require_https:
        recommendations.append("Enable HTTPS requirement in production")
    
    # Check JWT secret
    jwt_secret = os.getenv("JWT_SECRET")
    if jwt_secret and len(jwt_secret) < 32:
        issues.append(f"JWT_SECRET too short ({len(jwt_secret)} chars, minimum 32)")
    
    return {
        "environment": environment,
        "issues": issues,
        "recommendations": recommendations,
        "security_score": max(0, 100 - len(issues) * 20 - len(recommendations) * 5)
    }


async def setup_service_security(
    app: FastAPI,
    service_name: str,
    config_manager: Optional[SecureConfigManager] = None
) -> ServiceSecurityConfig:
    """
    Setup complete security configuration for a service
    
    Args:
        app: FastAPI application instance
        service_name: Name of the service
        config_manager: Optional secure config manager
        
    Returns:
        ServiceSecurityConfig: Complete security configuration
        
    Raises:
        SecuritySetupError: If security setup fails
    """
    try:
        environment = os.getenv("ENVIRONMENT", "production")
        
        # Get API key from secure config or environment
        api_key = None
        jwt_secret = None
        
        if config_manager:
            try:
                api_key = await get_secret("API_KEY")
                jwt_secret = await get_secret("JWT_SECRET") if config_manager.has_secret("JWT_SECRET") else None
            except Exception as e:
                logger.error(f"Failed to get secrets from secure config: {e}")
                raise SecuritySetupError(f"Failed to retrieve secrets: {e}")
        else:
            api_key = os.getenv("API_KEY")
            jwt_secret = os.getenv("JWT_SECRET")
        
        if not api_key:
            raise SecuritySetupError("API_KEY is required but not configured")
        
        # Parse CORS origins
        cors_origins_str = os.getenv("CORS_ORIGINS", "")
        if environment == "development" and not cors_origins_str:
            cors_origins = ["http://localhost:3000", "http://localhost:8000", "http://localhost:8080"]
        else:
            cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]
        
        # Validate production CORS
        if environment == "production":
            if not cors_origins:
                raise SecuritySetupError("CORS_ORIGINS must be configured for production")
            if "*" in cors_origins:
                raise SecuritySetupError("Wildcard CORS origins not allowed in production")
        
        # Create security config
        security_config = ServiceSecurityConfig(
            service_name=service_name,
            api_key=api_key,
            jwt_secret=jwt_secret,
            cors_origins=cors_origins,
            environment=environment,
            require_https=os.getenv("REQUIRE_HTTPS", "true").lower() == "true"
        )
        
        # Setup CORS middleware
        setup_cors_middleware(app, environment)
        
        # Add security headers
        @app.middleware("http")
        async def add_security_headers(request: Request, call_next):
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
            
            # Remove server header
            if "server" in response.headers:
                del response.headers["server"]
            
            return response
        
        # Create auth dependencies
        auth_config = AuthConfig(
            api_key=api_key,
            jwt_secret=jwt_secret,
            require_https=security_config.require_https
        )
        
        api_key_auth, jwt_auth = create_auth_dependencies(auth_config)
        
        # Store in app state for use by endpoints
        app.state.security_config = security_config
        app.state.api_key_auth = api_key_auth
        app.state.jwt_auth = jwt_auth
        
        logger.info(f"✅ Security configured for {service_name} in {environment} mode")
        
        return security_config
        
    except Exception as e:
        logger.error(f"Security setup failed for {service_name}: {e}")
        raise SecuritySetupError(f"Security setup failed: {e}")


def create_secure_headers() -> Dict[str, str]:
    """
    Create secure HTTP headers
    
    Returns:
        Dict of security headers
    """
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY", 
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self'"
        ),
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "X-Permitted-Cross-Domain-Policies": "none"
    }


def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """
    Mask sensitive data for logging
    
    Args:
        data: Sensitive data to mask
        mask_char: Character to use for masking
        visible_chars: Number of characters to leave visible
        
    Returns:
        Masked string
    """
    if not data or len(data) <= visible_chars:
        return mask_char * len(data) if data else ""
    
    visible_start = visible_chars // 2
    visible_end = visible_chars - visible_start
    
    if visible_end == 0:
        return data[:visible_start] + mask_char * (len(data) - visible_start)
    else:
        return (
            data[:visible_start] + 
            mask_char * (len(data) - visible_chars) + 
            data[-visible_end:]
        )


def generate_request_id() -> str:
    """
    Generate a unique request ID for tracing
    
    Returns:
        Unique request ID
    """
    return secrets.token_hex(8)


def hash_client_ip(ip: str, salt: str = "pyairtable-client-salt") -> str:
    """
    Hash client IP for privacy-preserving rate limiting
    
    Args:
        ip: Client IP address
        salt: Salt for hashing
        
    Returns:
        Hashed IP
    """
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()[:16]


@asynccontextmanager
async def secure_lifespan(app: FastAPI, service_name: str):
    """
    Async context manager for secure service lifespan
    
    Args:
        app: FastAPI application
        service_name: Name of the service
    """
    try:
        # Startup
        logger.info(f"🔐 Starting secure {service_name} service...")
        
        # Validate security configuration
        security_status = validate_environment_security()
        if security_status["issues"]:
            logger.error(f"Security validation failed: {security_status['issues']}")
            raise SecuritySetupError("Security validation failed")
        
        if security_status["recommendations"]:
            logger.warning(f"Security recommendations: {security_status['recommendations']}")
        
        logger.info(f"Security score: {security_status['security_score']}/100")
        
        yield
        
    except Exception as e:
        logger.error(f"Security setup failed: {e}")
        raise
    finally:
        # Cleanup
        logger.info(f"🔐 Shutting down secure {service_name} service...")


def create_api_key_verifier(expected_key: str):
    """
    Create a reusable API key verification function
    
    Args:
        expected_key: Expected API key value
        
    Returns:
        Verification function
    """
    def verify(provided_key: Optional[str]) -> bool:
        """Verify provided API key"""
        return verify_api_key_secure(provided_key or "", expected_key)
    
    return verify


def sanitize_log_data(data: Any) -> Any:
    """
    Sanitize data for safe logging (remove sensitive information)
    
    Args:
        data: Data to sanitize
        
    Returns:
        Sanitized data safe for logging
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in ["password", "secret", "token", "key", "auth"]):
                sanitized[key] = mask_sensitive_data(str(value))
            else:
                sanitized[key] = sanitize_log_data(value)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_log_data(item) for item in data]
    else:
        return data


# Security audit utilities
def audit_endpoint_security(app: FastAPI) -> Dict[str, Any]:
    """
    Audit endpoint security configuration
    
    Args:
        app: FastAPI application
        
    Returns:
        Security audit results
    """
    results = {
        "endpoints": [],
        "security_issues": [],
        "recommendations": []
    }
    
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            endpoint_info = {
                "path": route.path,
                "methods": list(route.methods),
                "has_auth": False,
                "has_rate_limit": False
            }
            
            # Check for authentication dependencies
            if hasattr(route, 'dependant') and route.dependant:
                for dependency in route.dependant.dependencies:
                    if 'auth' in str(dependency.call).lower():
                        endpoint_info["has_auth"] = True
                        break
            
            results["endpoints"].append(endpoint_info)
            
            # Flag endpoints without authentication
            if not endpoint_info["has_auth"] and route.path not in ["/health", "/metrics", "/docs", "/openapi.json"]:
                results["security_issues"].append(f"Endpoint {route.path} lacks authentication")
    
    return results