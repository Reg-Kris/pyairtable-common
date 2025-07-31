"""
Prometheus metrics collection system for PyAirtable microservices.

This module provides comprehensive metrics collection including:
- HTTP request metrics (duration, count, size)
- Airtable API metrics (requests, rate limits, cache)
- Infrastructure metrics (Redis, database, circuit breakers)
- Business metrics (operations, SLA monitoring)

Usage:
    from pyairtable_common.metrics import initialize_metrics, setup_metrics_middleware
    
    # Initialize metrics collector
    metrics = initialize_metrics("my-service", "1.0.0")
    
    # Setup middleware
    setup_metrics_middleware(app, metrics)
"""

from .core import (
    MetricsRegistry,
    MetricsCollector,
    ApplicationMetrics,
    AirtableMetrics,
    InfrastructureMetrics,
    initialize_metrics,
    timed,
    metrics_registry
)

from .middleware import (
    MetricsMiddleware,
    AirtableMetricsMiddleware,
    setup_metrics_middleware,
    create_metrics_endpoint
)

from .integrations import (
    RedisMetricsCollector,
    MetricsEnabledRedis,
    MetricsEnabledRateLimiter,
    MetricsEnabledAirtableRateLimiter,
    MetricsEnabledCircuitBreaker,
    CacheMetrics,
    create_metrics_enabled_redis,
    create_metrics_enabled_rate_limiter,
    create_metrics_enabled_airtable_limiter,
    create_metrics_enabled_circuit_breaker
)

from .service_configs import (
    AirtableGatewayMetrics,
    MCPServerMetrics,
    LLMOrchestratorMetrics,
    APIGatewayMetrics,
    create_service_metrics,
    get_service_metrics_summary
)

__all__ = [
    # Core metrics
    "MetricsRegistry",
    "MetricsCollector", 
    "ApplicationMetrics",
    "AirtableMetrics",
    "InfrastructureMetrics",
    "initialize_metrics",
    "timed",
    "metrics_registry",
    
    # Middleware
    "MetricsMiddleware",
    "AirtableMetricsMiddleware", 
    "setup_metrics_middleware",
    "create_metrics_endpoint",
    
    # Integrations
    "RedisMetricsCollector",
    "MetricsEnabledRedis",
    "MetricsEnabledRateLimiter",
    "MetricsEnabledAirtableRateLimiter",
    "MetricsEnabledCircuitBreaker",
    "CacheMetrics",
    "create_metrics_enabled_redis",
    "create_metrics_enabled_rate_limiter",
    "create_metrics_enabled_airtable_limiter",
    "create_metrics_enabled_circuit_breaker",
    
    # Service configurations
    "AirtableGatewayMetrics",
    "MCPServerMetrics",
    "LLMOrchestratorMetrics",
    "APIGatewayMetrics",
    "create_service_metrics",
    "get_service_metrics_summary"
]