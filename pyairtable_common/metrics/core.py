"""
Core Prometheus metrics collection system for PyAirtable microservices.

This module provides a comprehensive metrics collection framework that integrates
with the existing logging and middleware infrastructure.
"""
import time
from typing import Dict, List, Optional, Union, Any
from contextlib import contextmanager
from functools import wraps

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    Info,
    Enum,
    CollectorRegistry,
    REGISTRY,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from ..logging import get_logger, get_correlation_id

logger = get_logger(__name__)


class MetricsRegistry:
    """Centralized registry for all PyAirtable metrics."""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or REGISTRY
        self._metrics: Dict[str, Any] = {}
        self._service_info: Dict[str, str] = {}
    
    def set_service_info(self, service_name: str, version: str = "1.0.0", **kwargs):
        """Set service information for metrics labels."""
        self._service_info = {
            "service": service_name,
            "version": version,
            **kwargs
        }
        
        # Create service info metric
        if "service_info" not in self._metrics:
            self._metrics["service_info"] = Info(
                "service_info",
                "Service information",
                registry=self.registry
            )
        
        self._metrics["service_info"].info(self._service_info)
        logger.info(f"Metrics registry initialized for service: {service_name}")
    
    def get_common_labels(self, **additional_labels) -> Dict[str, str]:
        """Get common labels for metrics."""
        labels = {
            "service": self._service_info.get("service", "unknown"),
            "version": self._service_info.get("version", "unknown"),
        }
        labels.update(additional_labels)
        return labels
    
    def create_counter(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None
    ) -> Counter:
        """Create or get existing counter metric."""
        if name in self._metrics:
            return self._metrics[name]
        
        base_labels = ["service", "version"]
        if labels:
            base_labels.extend(labels)
        
        counter = Counter(
            name,
            description,
            labelnames=base_labels,
            registry=self.registry
        )
        self._metrics[name] = counter
        return counter
    
    def create_histogram(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None,
        buckets: Optional[List[float]] = None
    ) -> Histogram:
        """Create or get existing histogram metric."""
        if name in self._metrics:
            return self._metrics[name]
        
        base_labels = ["service", "version"]
        if labels:
            base_labels.extend(labels)
        
        histogram = Histogram(
            name,
            description,
            labelnames=base_labels,
            buckets=buckets,
            registry=self.registry
        )
        self._metrics[name] = histogram
        return histogram
    
    def create_gauge(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None
    ) -> Gauge:
        """Create or get existing gauge metric."""
        if name in self._metrics:
            return self._metrics[name]
        
        base_labels = ["service", "version"]
        if labels:
            base_labels.extend(labels)
        
        gauge = Gauge(
            name,
            description,
            labelnames=base_labels,
            registry=self.registry
        )
        self._metrics[name] = gauge
        return gauge
    
    def create_summary(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None
    ) -> Summary:
        """Create or get existing summary metric."""
        if name in self._metrics:
            return self._metrics[name]
        
        base_labels = ["service", "version"]
        if labels:
            base_labels.extend(labels)
        
        summary = Summary(
            name,
            description,
            labelnames=base_labels,
            registry=self.registry
        )
        self._metrics[name] = summary
        return summary
    
    def create_enum(
        self,
        name: str,
        description: str,
        states: List[str],
        labels: Optional[List[str]] = None
    ) -> Enum:
        """Create or get existing enum metric."""
        if name in self._metrics:
            return self._metrics[name]
        
        base_labels = ["service", "version"]
        if labels:
            base_labels.extend(labels)
        
        enum_metric = Enum(
            name,
            description,
            labelnames=base_labels,
            states=states,
            registry=self.registry
        )
        self._metrics[name] = enum_metric
        return enum_metric
    
    def get_metric(self, name: str) -> Optional[Any]:
        """Get existing metric by name."""
        return self._metrics.get(name)
    
    def export_metrics(self) -> str:
        """Export all metrics in Prometheus format."""
        return generate_latest(self.registry).decode('utf-8')


# Global metrics registry instance
metrics_registry = MetricsRegistry()


class ApplicationMetrics:
    """Standard application metrics for PyAirtable services."""
    
    def __init__(self, registry: MetricsRegistry = None):
        self.registry = registry or metrics_registry
        self._initialize_metrics()
    
    def _initialize_metrics(self):
        """Initialize standard application metrics."""
        
        # Request metrics
        self.http_requests_total = self.registry.create_counter(
            "http_requests_total",
            "Total HTTP requests",
            labels=["method", "endpoint", "status_code"]
        )
        
        self.http_request_duration_seconds = self.registry.create_histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            labels=["method", "endpoint", "status_code"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        )
        
        self.http_request_size_bytes = self.registry.create_histogram(
            "http_request_size_bytes",
            "HTTP request size in bytes",
            labels=["method", "endpoint"],
            buckets=[100, 1000, 10000, 100000, 1000000]
        )
        
        self.http_response_size_bytes = self.registry.create_histogram(
            "http_response_size_bytes",
            "HTTP response size in bytes",
            labels=["method", "endpoint", "status_code"],
            buckets=[100, 1000, 10000, 100000, 1000000]
        )
        
        # Error metrics
        self.errors_total = self.registry.create_counter(
            "errors_total",
            "Total errors by type",
            labels=["error_type", "endpoint"]
        )
        
        # Performance metrics
        self.active_connections = self.registry.create_gauge(
            "active_connections",
            "Current active connections"
        )
        
        # Business metrics
        self.business_operations_total = self.registry.create_counter(
            "business_operations_total",
            "Total business operations",
            labels=["operation_type", "status"]
        )
        
        self.business_operation_duration_seconds = self.registry.create_histogram(
            "business_operation_duration_seconds",
            "Business operation duration in seconds",
            labels=["operation_type"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        )


class AirtableMetrics:
    """Airtable-specific metrics."""
    
    def __init__(self, registry: MetricsRegistry = None):
        self.registry = registry or metrics_registry
        self._initialize_metrics()
    
    def _initialize_metrics(self):
        """Initialize Airtable-specific metrics."""
        
        # API usage metrics
        self.airtable_api_requests_total = self.registry.create_counter(
            "airtable_api_requests_total",
            "Total Airtable API requests",
            labels=["base_id", "table_name", "operation", "status_code"]
        )
        
        self.airtable_api_duration_seconds = self.registry.create_histogram(
            "airtable_api_duration_seconds",
            "Airtable API request duration in seconds",
            labels=["base_id", "table_name", "operation"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
        )
        
        # Rate limiting metrics
        self.airtable_rate_limit_hits_total = self.registry.create_counter(
            "airtable_rate_limit_hits_total",
            "Total rate limit hits",
            labels=["base_id", "limit_type"]
        )
        
        self.airtable_rate_limit_remaining = self.registry.create_gauge(
            "airtable_rate_limit_remaining",
            "Remaining rate limit quota",
            labels=["base_id", "limit_type"]
        )
        
        # Cache metrics
        self.cache_operations_total = self.registry.create_counter(
            "cache_operations_total",
            "Total cache operations",
            labels=["operation", "result"]
        )
        
        self.cache_hit_ratio = self.registry.create_gauge(
            "cache_hit_ratio",
            "Cache hit ratio"
        )


class InfrastructureMetrics:
    """Infrastructure and system metrics."""
    
    def __init__(self, registry: MetricsRegistry = None):
        self.registry = registry or metrics_registry
        self._initialize_metrics()
    
    def _initialize_metrics(self):
        """Initialize infrastructure metrics."""
        
        # Redis metrics
        self.redis_operations_total = self.registry.create_counter(
            "redis_operations_total",
            "Total Redis operations",
            labels=["operation", "result"]
        )
        
        self.redis_connection_pool_size = self.registry.create_gauge(
            "redis_connection_pool_size",
            "Redis connection pool size",
            labels=["pool_type"]
        )
        
        # Database metrics
        self.database_connections_active = self.registry.create_gauge(
            "database_connections_active",
            "Active database connections"
        )
        
        self.database_query_duration_seconds = self.registry.create_histogram(
            "database_query_duration_seconds",
            "Database query duration in seconds",
            labels=["query_type"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]
        )
        
        # Circuit breaker metrics
        self.circuit_breaker_state = self.registry.create_enum(
            "circuit_breaker_state",
            "Circuit breaker state",
            states=["closed", "open", "half_open"],
            labels=["circuit_name"]
        )
        
        self.circuit_breaker_failures_total = self.registry.create_counter(
            "circuit_breaker_failures_total",
            "Total circuit breaker failures",
            labels=["circuit_name"]
        )


class MetricsCollector:
    """Main metrics collector that coordinates all metric types."""
    
    def __init__(self, service_name: str, version: str = "1.0.0"):
        self.service_name = service_name
        self.version = version
        
        # Initialize registry
        metrics_registry.set_service_info(service_name, version)
        
        # Initialize metric collectors
        self.app_metrics = ApplicationMetrics()
        self.airtable_metrics = AirtableMetrics()
        self.infra_metrics = InfrastructureMetrics()
        
        logger.info(f"MetricsCollector initialized for {service_name} v{version}")
    
    def record_http_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
        request_size: int = 0,
        response_size: int = 0
    ):
        """Record HTTP request metrics."""
        labels = self._get_http_labels(method, endpoint, status_code)
        
        self.app_metrics.http_requests_total.labels(**labels).inc()
        self.app_metrics.http_request_duration_seconds.labels(**labels).observe(duration)
        
        if request_size > 0:
            req_labels = self._get_http_labels(method, endpoint)
            self.app_metrics.http_request_size_bytes.labels(**req_labels).observe(request_size)
        
        if response_size > 0:
            self.app_metrics.http_response_size_bytes.labels(**labels).observe(response_size)
    
    def record_error(self, error_type: str, endpoint: str = "unknown"):
        """Record error metrics."""
        labels = self._get_error_labels(error_type, endpoint)
        self.app_metrics.errors_total.labels(**labels).inc()
    
    def record_airtable_request(
        self,
        base_id: str,
        table_name: str,
        operation: str,
        status_code: int,
        duration: float
    ):
        """Record Airtable API request metrics."""
        labels = self._get_airtable_labels(base_id, table_name, operation, status_code)
        
        self.airtable_metrics.airtable_api_requests_total.labels(**labels).inc()
        
        duration_labels = self._get_airtable_labels(base_id, table_name, operation)
        self.airtable_metrics.airtable_api_duration_seconds.labels(**duration_labels).observe(duration)
    
    def record_rate_limit_hit(self, base_id: str, limit_type: str):
        """Record rate limit hit."""
        labels = self._get_rate_limit_labels(base_id, limit_type)
        self.airtable_metrics.airtable_rate_limit_hits_total.labels(**labels).inc()
    
    def update_rate_limit_remaining(self, base_id: str, limit_type: str, remaining: int):
        """Update remaining rate limit quota."""
        labels = self._get_rate_limit_labels(base_id, limit_type)
        self.airtable_metrics.airtable_rate_limit_remaining.labels(**labels).set(remaining)
    
    def record_cache_operation(self, operation: str, result: str):
        """Record cache operation."""
        labels = self._get_cache_labels(operation, result)
        self.airtable_metrics.cache_operations_total.labels(**labels).inc()
    
    def update_cache_hit_ratio(self, ratio: float):
        """Update cache hit ratio."""
        labels = metrics_registry.get_common_labels()
        self.airtable_metrics.cache_hit_ratio.labels(**labels).set(ratio)
    
    def _get_http_labels(self, method: str, endpoint: str, status_code: int = None) -> Dict[str, str]:
        """Get HTTP metric labels."""
        labels = metrics_registry.get_common_labels(
            method=method.upper(),
            endpoint=endpoint
        )
        if status_code is not None:
            labels["status_code"] = str(status_code)
        return labels
    
    def _get_error_labels(self, error_type: str, endpoint: str) -> Dict[str, str]:
        """Get error metric labels."""
        return metrics_registry.get_common_labels(
            error_type=error_type,
            endpoint=endpoint
        )
    
    def _get_airtable_labels(self, base_id: str, table_name: str, operation: str, status_code: int = None) -> Dict[str, str]:
        """Get Airtable metric labels."""
        labels = metrics_registry.get_common_labels(
            base_id=base_id,
            table_name=table_name,
            operation=operation
        )
        if status_code is not None:
            labels["status_code"] = str(status_code)
        return labels
    
    def _get_rate_limit_labels(self, base_id: str, limit_type: str) -> Dict[str, str]:
        """Get rate limit metric labels."""
        return metrics_registry.get_common_labels(
            base_id=base_id,
            limit_type=limit_type
        )
    
    def _get_cache_labels(self, operation: str, result: str) -> Dict[str, str]:
        """Get cache metric labels."""
        return metrics_registry.get_common_labels(
            operation=operation,
            result=result
        )
    
    @contextmanager
    def time_operation(self, operation_type: str):
        """Context manager to time business operations."""
        start_time = time.time()
        labels = metrics_registry.get_common_labels(operation_type=operation_type)
        
        try:
            yield
            # Operation succeeded
            self.app_metrics.business_operations_total.labels(
                **labels, status="success"
            ).inc()
        except Exception as e:
            # Operation failed
            self.app_metrics.business_operations_total.labels(
                **labels, status="failure"
            ).inc()
            raise
        finally:
            duration = time.time() - start_time
            self.app_metrics.business_operation_duration_seconds.labels(**labels).observe(duration)
    
    def export_metrics(self) -> str:
        """Export all metrics in Prometheus format."""
        return metrics_registry.export_metrics()


def timed(operation_type: str = None):
    """Decorator to time function execution and record metrics."""
    def decorator(func):
        nonlocal operation_type
        if operation_type is None:
            operation_type = f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Try to get metrics collector from first argument if it's a class instance
            collector = None
            if args and hasattr(args[0], '_metrics_collector'):
                collector = args[0]._metrics_collector
            
            if collector:
                with collector.time_operation(operation_type):
                    return await func(*args, **kwargs)
            else:
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Try to get metrics collector from first argument if it's a class instance
            collector = None
            if args and hasattr(args[0], '_metrics_collector'):
                collector = args[0]._metrics_collector
            
            if collector:
                with collector.time_operation(operation_type):
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Convenience function to initialize metrics for a service
def initialize_metrics(service_name: str, version: str = "1.0.0") -> MetricsCollector:
    """Initialize metrics collection for a service."""
    return MetricsCollector(service_name, version)