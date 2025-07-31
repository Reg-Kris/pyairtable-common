"""
Service-specific metrics configurations for PyAirtable microservices.

This module provides pre-configured metrics setups for each service in the
PyAirtable ecosystem, including custom metrics and integration patterns.
"""
from typing import Dict, List, Optional, Any
from .core import MetricsCollector, metrics_registry
from .integrations import (
    create_metrics_enabled_redis,
    create_metrics_enabled_airtable_limiter,
    create_metrics_enabled_circuit_breaker,
    CacheMetrics
)

from ..logging import get_logger

logger = get_logger(__name__)


class AirtableGatewayMetrics:
    """Metrics configuration for airtable-gateway-py service."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.cache_metrics = CacheMetrics(metrics_collector)
        self._setup_custom_metrics()
    
    def _setup_custom_metrics(self):
        """Setup custom metrics for Airtable Gateway."""
        
        # API response caching metrics
        self.cache_operations = self.metrics.registry.create_counter(
            "airtable_cache_operations_total",
            "Total cache operations for Airtable responses",
            labels=["operation", "base_id", "table_name", "result"]
        )
        
        # Airtable API quota tracking
        self.api_quota_usage = self.metrics.registry.create_gauge(
            "airtable_api_quota_usage",
            "Current API quota usage percentage",
            labels=["base_id", "quota_type"]
        )
        
        # Request queuing metrics
        self.request_queue_size = self.metrics.registry.create_gauge(
            "airtable_request_queue_size",
            "Current size of request queue",
            labels=["base_id"]
        )
        
        # Webhook processing metrics
        self.webhook_events_total = self.metrics.registry.create_counter(
            "airtable_webhook_events_total",
            "Total webhook events processed",
            labels=["base_id", "event_type", "status"]
        )
    
    def record_cache_operation(self, operation: str, base_id: str, table_name: str, result: str):
        """Record cache operation with Airtable context."""
        labels = self.metrics.registry.get_common_labels(
            operation=operation,
            base_id=base_id,
            table_name=table_name,
            result=result
        )
        self.cache_operations.labels(**labels).inc()
        
        # Also record in general cache metrics
        if result == 'hit':
            self.cache_metrics.record_hit()
        elif result == 'miss':
            self.cache_metrics.record_miss()
    
    def update_api_quota_usage(self, base_id: str, quota_type: str, usage_percentage: float):
        """Update API quota usage."""
        labels = self.metrics.registry.get_common_labels(
            base_id=base_id,
            quota_type=quota_type
        )
        self.api_quota_usage.labels(**labels).set(usage_percentage)
    
    def update_request_queue_size(self, base_id: str, size: int):
        """Update request queue size."""
        labels = self.metrics.registry.get_common_labels(base_id=base_id)
        self.request_queue_size.labels(**labels).set(size)
    
    def record_webhook_event(self, base_id: str, event_type: str, status: str):
        """Record webhook event processing."""
        labels = self.metrics.registry.get_common_labels(
            base_id=base_id,
            event_type=event_type,
            status=status
        )
        self.webhook_events_total.labels(**labels).inc()


class MCPServerMetrics:
    """Metrics configuration for mcp-server-py service."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self._setup_custom_metrics()
    
    def _setup_custom_metrics(self):
        """Setup custom metrics for MCP Server."""
        
        # Subprocess management metrics
        self.subprocess_count = self.metrics.registry.create_gauge(
            "mcp_subprocess_count",
            "Current number of active subprocesses",
            labels=["process_type"]
        )
        
        self.subprocess_creation_total = self.metrics.registry.create_counter(
            "mcp_subprocess_creation_total",
            "Total subprocess creations",
            labels=["process_type", "status"]
        )
        
        self.subprocess_duration_seconds = self.metrics.registry.create_histogram(
            "mcp_subprocess_duration_seconds",
            "Subprocess lifetime duration",
            labels=["process_type"],
            buckets=[1, 5, 10, 30, 60, 300, 600, 1800, 3600]
        )
        
        # Protocol message metrics
        self.protocol_messages_total = self.metrics.registry.create_counter(
            "mcp_protocol_messages_total",
            "Total MCP protocol messages",
            labels=["message_type", "direction", "status"]
        )
        
        self.protocol_message_size_bytes = self.metrics.registry.create_histogram(
            "mcp_protocol_message_size_bytes",
            "MCP protocol message size in bytes",
            labels=["message_type", "direction"],
            buckets=[100, 1000, 10000, 100000, 1000000]
        )
        
        # Tool execution metrics
        self.tool_executions_total = self.metrics.registry.create_counter(
            "mcp_tool_executions_total", 
            "Total tool executions",
            labels=["tool_name", "status"]
        )
        
        self.tool_execution_duration_seconds = self.metrics.registry.create_histogram(
            "mcp_tool_execution_duration_seconds",
            "Tool execution duration",
            labels=["tool_name"],
            buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0]
        )
    
    def update_subprocess_count(self, process_type: str, count: int):
        """Update subprocess count."""
        labels = self.metrics.registry.get_common_labels(process_type=process_type)
        self.subprocess_count.labels(**labels).set(count)
    
    def record_subprocess_creation(self, process_type: str, status: str):
        """Record subprocess creation."""
        labels = self.metrics.registry.get_common_labels(
            process_type=process_type,
            status=status
        )
        self.subprocess_creation_total.labels(**labels).inc()
    
    def record_subprocess_duration(self, process_type: str, duration: float):
        """Record subprocess duration."""
        labels = self.metrics.registry.get_common_labels(process_type=process_type)
        self.subprocess_duration_seconds.labels(**labels).observe(duration)
    
    def record_protocol_message(self, message_type: str, direction: str, status: str, size_bytes: int = 0):
        """Record protocol message."""
        labels = self.metrics.registry.get_common_labels(
            message_type=message_type,
            direction=direction,
            status=status
        )
        self.protocol_messages_total.labels(**labels).inc()
        
        if size_bytes > 0:
            size_labels = self.metrics.registry.get_common_labels(
                message_type=message_type,
                direction=direction
            )
            self.protocol_message_size_bytes.labels(**size_labels).observe(size_bytes)
    
    def record_tool_execution(self, tool_name: str, status: str, duration: float):
        """Record tool execution."""
        execution_labels = self.metrics.registry.get_common_labels(
            tool_name=tool_name,
            status=status
        )
        self.tool_executions_total.labels(**execution_labels).inc()
        
        duration_labels = self.metrics.registry.get_common_labels(tool_name=tool_name)
        self.tool_execution_duration_seconds.labels(**duration_labels).observe(duration)


class LLMOrchestratorMetrics:
    """Metrics configuration for llm-orchestrator-py service."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self._setup_custom_metrics()
    
    def _setup_custom_metrics(self):
        """Setup custom metrics for LLM Orchestrator."""
        
        # Gemini API metrics
        self.gemini_requests_total = self.metrics.registry.create_counter(
            "gemini_requests_total",
            "Total Gemini API requests",
            labels=["model", "operation", "status_code"]
        )
        
        self.gemini_request_duration_seconds = self.metrics.registry.create_histogram(
            "gemini_request_duration_seconds",
            "Gemini API request duration",
            labels=["model", "operation"],
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0]
        )
        
        self.gemini_token_usage = self.metrics.registry.create_counter(
            "gemini_token_usage_total",
            "Total tokens used by Gemini API",  
            labels=["model", "token_type"]
        )
        
        # Session management metrics
        self.active_sessions = self.metrics.registry.create_gauge(
            "llm_active_sessions",
            "Current number of active LLM sessions"
        )
        
        self.session_duration_seconds = self.metrics.registry.create_histogram(
            "llm_session_duration_seconds",
            "LLM session duration",
            buckets=[60, 300, 600, 1800, 3600, 7200, 14400]
        )
        
        # Conversation metrics
        self.conversation_turns_total = self.metrics.registry.create_counter(
            "llm_conversation_turns_total",
            "Total conversation turns",
            labels=["session_type"]
        )
        
        self.message_length_chars = self.metrics.registry.create_histogram(
            "llm_message_length_chars",
            "Message length in characters",
            labels=["message_type"],
            buckets=[100, 500, 1000, 5000, 10000, 50000, 100000]
        )
    
    def record_gemini_request(self, model: str, operation: str, status_code: int, duration: float):
        """Record Gemini API request."""
        labels = self.metrics.registry.get_common_labels(
            model=model,
            operation=operation,
            status_code=str(status_code)
        )
        self.gemini_requests_total.labels(**labels).inc()
        
        duration_labels = self.metrics.registry.get_common_labels(
            model=model,
            operation=operation
        )
        self.gemini_request_duration_seconds.labels(**duration_labels).observe(duration)
    
    def record_token_usage(self, model: str, token_type: str, count: int):
        """Record token usage."""
        labels = self.metrics.registry.get_common_labels(
            model=model,
            token_type=token_type
        )
        self.gemini_token_usage.labels(**labels).inc(count)
    
    def update_active_sessions(self, count: int):
        """Update active session count."""
        labels = self.metrics.registry.get_common_labels()
        self.active_sessions.labels(**labels).set(count)
    
    def record_session_duration(self, duration: float):
        """Record session duration."""
        labels = self.metrics.registry.get_common_labels()
        self.session_duration_seconds.labels(**labels).observe(duration)
    
    def record_conversation_turn(self, session_type: str):
        """Record conversation turn."""
        labels = self.metrics.registry.get_common_labels(session_type=session_type)
        self.conversation_turns_total.labels(**labels).inc()
    
    def record_message_length(self, message_type: str, length: int):
        """Record message length."""
        labels = self.metrics.registry.get_common_labels(message_type=message_type)
        self.message_length_chars.labels(**labels).observe(length)


class APIGatewayMetrics:
    """Metrics configuration for pyairtable-api-gateway service."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self._setup_custom_metrics()
    
    def _setup_custom_metrics(self):
        """Setup custom metrics for API Gateway."""
        
        # Request routing metrics
        self.route_requests_total = self.metrics.registry.create_counter(
            "gateway_route_requests_total",
            "Total routed requests",
            labels=["source_service", "target_service", "route", "status"]
        )
        
        self.route_duration_seconds = self.metrics.registry.create_histogram(
            "gateway_route_duration_seconds", 
            "Request routing duration",
            labels=["source_service", "target_service", "route"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
        )
        
        # Load balancing metrics
        self.backend_requests_total = self.metrics.registry.create_counter(
            "gateway_backend_requests_total",
            "Total backend requests",
            labels=["backend_service", "backend_instance", "status"]
        )
        
        self.backend_health_status = self.metrics.registry.create_enum(
            "gateway_backend_health_status",
            "Backend service health status",
            states=["healthy", "unhealthy", "unknown"],
            labels=["backend_service", "backend_instance"]
        )
        
        # Authentication metrics
        self.auth_requests_total = self.metrics.registry.create_counter(
            "gateway_auth_requests_total",
            "Total authentication requests",
            labels=["auth_type", "status"]
        )
    
    def record_route_request(self, source_service: str, target_service: str, route: str, status: str, duration: float):
        """Record routed request."""
        labels = self.metrics.registry.get_common_labels(
            source_service=source_service,
            target_service=target_service,
            route=route,
            status=status
        )
        self.route_requests_total.labels(**labels).inc()
        
        duration_labels = self.metrics.registry.get_common_labels(
            source_service=source_service,
            target_service=target_service,
            route=route
        )
        self.route_duration_seconds.labels(**duration_labels).observe(duration)
    
    def record_backend_request(self, backend_service: str, backend_instance: str, status: str):
        """Record backend request."""
        labels = self.metrics.registry.get_common_labels(
            backend_service=backend_service,
            backend_instance=backend_instance,
            status=status
        )
        self.backend_requests_total.labels(**labels).inc()
    
    def update_backend_health(self, backend_service: str, backend_instance: str, health: str):
        """Update backend health status."""
        labels = self.metrics.registry.get_common_labels(
            backend_service=backend_service,
            backend_instance=backend_instance
        )
        self.backend_health_status.labels(**labels).state(health)
    
    def record_auth_request(self, auth_type: str, status: str):
        """Record authentication request."""
        labels = self.metrics.registry.get_common_labels(
            auth_type=auth_type,
            status=status
        )
        self.auth_requests_total.labels(**labels).inc()


# Service configuration factory
SERVICE_METRIC_CONFIGS = {
    "airtable-gateway-py": AirtableGatewayMetrics,
    "mcp-server-py": MCPServerMetrics,
    "llm-orchestrator-py": LLMOrchestratorMetrics,
    "pyairtable-api-gateway": APIGatewayMetrics,
}


def create_service_metrics(service_name: str, metrics_collector: MetricsCollector) -> Optional[Any]:
    """Create service-specific metrics configuration."""
    if service_name in SERVICE_METRIC_CONFIGS:
        config_class = SERVICE_METRIC_CONFIGS[service_name]
        return config_class(metrics_collector)
    else:
        logger.warning(f"No specific metrics configuration for service: {service_name}")
        return None


def get_service_metrics_summary(service_name: str) -> Dict[str, List[str]]:
    """Get summary of metrics available for a service."""
    summaries = {
        "airtable-gateway-py": {
            "counters": [
                "airtable_cache_operations_total",
                "airtable_webhook_events_total"
            ],
            "gauges": [
                "airtable_api_quota_usage",
                "airtable_request_queue_size"
            ],
            "histograms": []
        },
        "mcp-server-py": {
            "counters": [
                "mcp_subprocess_creation_total",
                "mcp_protocol_messages_total",
                "mcp_tool_executions_total"
            ],
            "gauges": [
                "mcp_subprocess_count"
            ],
            "histograms": [
                "mcp_subprocess_duration_seconds",
                "mcp_protocol_message_size_bytes",
                "mcp_tool_execution_duration_seconds"
            ]
        },
        "llm-orchestrator-py": {
            "counters": [
                "gemini_requests_total",
                "gemini_token_usage_total",
                "llm_conversation_turns_total"
            ],
            "gauges": [
                "llm_active_sessions"
            ],
            "histograms": [
                "gemini_request_duration_seconds",
                "llm_session_duration_seconds",
                "llm_message_length_chars"
            ]
        },
        "pyairtable-api-gateway": {
            "counters": [
                "gateway_route_requests_total",
                "gateway_backend_requests_total",
                "gateway_auth_requests_total"
            ],
            "gauges": [],
            "histograms": [
                "gateway_route_duration_seconds"
            ],
            "enums": [
                "gateway_backend_health_status"
            ]
        }
    }
    
    return summaries.get(service_name, {"counters": [], "gauges": [], "histograms": [], "enums": []})