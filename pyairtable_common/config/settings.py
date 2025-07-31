"""Shared configuration settings for PyAirtable microservices."""

from typing import Optional, List
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class CommonSettings(BaseSettings):
    """Common settings shared across all PyAirtable services."""
    
    model_config = SettingsConfigDict(
        env_prefix="PYAIRTABLE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"  # json or text
    
    # Security
    api_key_header: str = "X-API-Key"
    jwt_algorithm: str = "HS256"
    jwt_secret_key: Optional[str] = None
    
    # Performance
    default_timeout: int = 30
    max_retries: int = 3
    retry_backoff_factor: float = 0.5
    connection_pool_size: int = 100
    
    # Rate Limiting
    default_rate_limit: str = "60/minute"
    burst_rate_limit: str = "120/minute"
    
    # Caching
    cache_ttl_seconds: int = 300  # 5 minutes
    cache_max_size: int = 1000
    
    # Monitoring
    metrics_enabled: bool = True
    metrics_port: int = 9090
    health_check_timeout: int = 5
    
    # CORS
    cors_origins: List[str] = ["*"]
    cors_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "PATCH"]
    cors_headers: List[str] = ["*"]
    
    # Database (if used)
    database_pool_size: int = 20
    database_max_overflow: int = 30
    database_pool_timeout: int = 30
    
    # Redis (if used)
    redis_max_connections: int = 50
    redis_socket_timeout: int = 5
    redis_socket_connect_timeout: int = 5


class ServiceSettings(CommonSettings):
    """Base class for service-specific settings."""
    
    # Service Identity
    service_name: str = "pyairtable-service"
    service_version: str = "1.0.0"
    service_port: int = 8000
    
    # External Dependencies
    airtable_token: Optional[str] = None
    gemini_api_key: Optional[str] = None
    
    # Service URLs (for inter-service communication)
    airtable_gateway_url: str = "http://airtable-gateway:8002"
    mcp_server_url: str = "http://mcp-server:8001"
    llm_orchestrator_url: str = "http://llm-orchestrator:8003"
    api_gateway_url: str = "http://api-gateway:8000"
    
    # Database URLs
    postgres_url: Optional[str] = None
    redis_url: Optional[str] = None


@lru_cache()
def get_settings() -> CommonSettings:
    """Get cached common settings instance."""
    return CommonSettings()


@lru_cache()
def get_service_settings() -> ServiceSettings:
    """Get cached service settings instance."""
    return ServiceSettings()