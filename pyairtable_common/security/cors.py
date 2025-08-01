"""
Secure CORS Configuration for PyAirtable Services
Provides production-ready CORS settings with environment-based configuration
"""

import os
import re
from typing import List, Union, Dict, Any
from urllib.parse import urlparse
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

class CORSConfig:
    """CORS configuration with security best practices"""
    
    def __init__(
        self,
        allowed_origins: Union[List[str], str] = None,
        allowed_methods: List[str] = None,
        allowed_headers: List[str] = None,
        allow_credentials: bool = True,
        max_age: int = 86400,  # 24 hours
        environment: str = "production"
    ):
        self.environment = environment
        self.allow_credentials = allow_credentials
        self.max_age = max_age
        
        # Set secure defaults based on environment
        if environment == "development":
            self.allowed_origins = self._parse_origins(allowed_origins) or [
                "http://localhost:3000",
                "http://localhost:8000", 
                "http://localhost:8080",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8000",
                "http://127.0.0.1:8080"
            ]
        else:
            # Production - no wildcards allowed
            if allowed_origins:
                self.allowed_origins = self._parse_origins(allowed_origins)
                self._validate_production_origins()
            else:
                raise ValueError(
                    "CORS_ORIGINS environment variable is required in production. "
                    "Never use '*' in production!"
                )
        
        self.allowed_methods = allowed_methods or [
            "GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"
        ]
        
        self.allowed_headers = allowed_headers or [
            "Content-Type",
            "Authorization", 
            "X-API-Key",
            "X-Request-ID",
            "X-Correlation-ID",
            "Accept",
            "Origin",
            "User-Agent"
        ]
    
    def _parse_origins(self, origins: Union[List[str], str, None]) -> List[str]:
        """Parse origins from string or list"""
        if not origins:
            return []
        
        if isinstance(origins, str):
            # Split by comma and clean up
            return [origin.strip() for origin in origins.split(",") if origin.strip()]
        
        return origins
    
    def _validate_production_origins(self):
        """Validate origins for production use"""
        for origin in self.allowed_origins:
            if origin == "*":
                raise ValueError(
                    "Wildcard CORS origins (*) are not allowed in production! "
                    "Specify exact origins in CORS_ORIGINS environment variable."
                )
            
            if not self._is_valid_origin(origin):
                logger.warning(f"Invalid CORS origin format: {origin}")
    
    def _is_valid_origin(self, origin: str) -> bool:
        """Validate origin format"""
        try:
            parsed = urlparse(origin)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False
    
    def apply_to_app(self, app: FastAPI):
        """Apply CORS configuration to FastAPI app"""
        logger.info(f"Configuring CORS for {self.environment} environment")
        logger.info(f"Allowed origins: {self.allowed_origins}")
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.allowed_origins,
            allow_credentials=self.allow_credentials,
            allow_methods=self.allowed_methods,
            allow_headers=self.allowed_headers,
            max_age=self.max_age
        )
        
        logger.info("✅ CORS middleware configured successfully")


def create_cors_config(environment: str = None) -> CORSConfig:
    """
    Create CORS configuration from environment variables
    
    Args:
        environment: Environment name (development/production)
        
    Returns:
        CORSConfig: Configured CORS settings
        
    Environment Variables:
        CORS_ORIGINS: Comma-separated list of allowed origins
        CORS_METHODS: Comma-separated list of allowed methods  
        CORS_HEADERS: Comma-separated list of allowed headers
        CORS_CREDENTIALS: Allow credentials (true/false)
        CORS_MAX_AGE: Max age for preflight cache in seconds
    """
    if not environment:
        environment = os.getenv("ENVIRONMENT", "production")
    
    origins = os.getenv("CORS_ORIGINS")
    methods = os.getenv("CORS_METHODS")
    headers = os.getenv("CORS_HEADERS") 
    credentials = os.getenv("CORS_CREDENTIALS", "true").lower() == "true"
    max_age = int(os.getenv("CORS_MAX_AGE", "86400"))
    
    methods_list = None
    if methods:
        methods_list = [method.strip() for method in methods.split(",")]
    
    headers_list = None  
    if headers:
        headers_list = [header.strip() for header in headers.split(",")]
    
    return CORSConfig(
        allowed_origins=origins,
        allowed_methods=methods_list,
        allowed_headers=headers_list,
        allow_credentials=credentials,
        max_age=max_age,
        environment=environment
    )


def setup_cors_middleware(app: FastAPI, environment: str = None):
    """
    Setup CORS middleware with secure defaults
    
    Args:
        app: FastAPI application instance
        environment: Environment name (development/production)
    """
    cors_config = create_cors_config(environment)
    cors_config.apply_to_app(app)


# Pre-defined secure CORS configurations
DEVELOPMENT_CORS = CORSConfig(environment="development")

PRODUCTION_CORS_TEMPLATE = {
    "allow_credentials": True,
    "max_age": 86400,
    "allowed_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    "allowed_headers": [
        "Content-Type",
        "Authorization",
        "X-API-Key", 
        "X-Request-ID",
        "X-Correlation-ID",
        "Accept",
        "Origin",
        "User-Agent"
    ]
}