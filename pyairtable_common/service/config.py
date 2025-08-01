"""
Service configuration for PyAirtable services.
"""

from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from fastapi import FastAPI


@dataclass
class ServiceConfig:
    """Configuration class for PyAirtable services."""
    
    # Service Identity
    title: str
    description: str
    version: str = "1.0.0"
    service_name: str = "pyairtable-service"
    port: int = 8000
    
    # Security Configuration
    api_key: Optional[str] = None
    api_key_header: str = "X-API-Key"
    enable_security_headers: bool = True
    enable_rate_limiting: bool = True
    rate_limit_calls: int = 100
    rate_limit_period: int = 60
    
    # CORS Configuration
    cors_origins: List[str] = field(default_factory=lambda: [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8080"
    ])
    cors_methods: List[str] = field(default_factory=lambda: [
        "GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"
    ])
    cors_headers: List[str] = field(default_factory=lambda: [
        "Content-Type", "Authorization", "X-API-Key", "X-Request-ID"
    ])
    
    # Middleware Configuration
    enable_correlation_id: bool = True
    enable_request_logging: bool = True
    enable_error_handling: bool = True
    enable_metrics: bool = False
    correlation_header: str = "X-Request-ID"
    exclude_log_paths: List[str] = field(default_factory=lambda: [
        "/health", "/metrics", "/docs", "/redoc", "/openapi.json"
    ])
    
    # Health Check Configuration
    health_endpoint: str = "/health"
    enable_health_check: bool = True
    health_check_dependencies: List[Callable] = field(default_factory=list)
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"  # json or text
    
    # Lifespan Configuration
    startup_tasks: List[Callable] = field(default_factory=list)
    shutdown_tasks: List[Callable] = field(default_factory=list)
    
    # Custom Configuration
    custom_middleware: List[tuple] = field(default_factory=list)  # (middleware_class, kwargs)
    custom_routes: List[tuple] = field(default_factory=list)  # (router, prefix, tags)
    
    # FastAPI Configuration Overrides
    fastapi_kwargs: Dict[str, Any] = field(default_factory=dict)
    
    def get_fastapi_kwargs(self) -> Dict[str, Any]:
        """Get FastAPI initialization kwargs."""
        kwargs = {
            "title": self.title,
            "description": self.description,
            "version": self.version,
            **self.fastapi_kwargs
        }
        return kwargs