# PyAirtable Metrics Collection System

A comprehensive Prometheus metrics collection system designed specifically for the PyAirtable microservices ecosystem.

## Overview

This metrics system provides:
- **Automatic HTTP request tracking** with duration, status codes, and sizes
- **Airtable API monitoring** with rate limits, quotas, and cache metrics
- **Infrastructure monitoring** for Redis, circuit breakers, and database connections
- **Business metrics** for operations, sessions, and SLA monitoring
- **Service-specific metrics** tailored for each microservice
- **Pre-built Grafana dashboards** for operational visibility
- **Docker integration** with Prometheus and Grafana stack

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Service A     │    │   Service B     │    │   Service C     │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │   Metrics   │ │    │ │   Metrics   │ │    │ │   Metrics   │ │
│ │ Middleware  │ │    │ │ Middleware  │ │    │ │ Middleware  │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ /metrics    │ │    │ │ /metrics    │ │    │ │ /metrics    │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Prometheus    │
                    │     Server      │
                    └─────────────────┘
                             │
                    ┌─────────────────┐
                    │     Grafana     │
                    │   Dashboards    │
                    └─────────────────┘
```

## Quick Start

### 1. Basic Service Integration

```python
from pyairtable_common.metrics.examples import create_service_with_full_metrics

# Create FastAPI app with full metrics integration
app = create_service_with_full_metrics(
    service_name="my-service-py",
    version="1.0.0",
    redis_url="redis://localhost:6379"
)

# Your service is now collecting metrics automatically!
```

### 2. Custom Metrics

```python
from pyairtable_common.metrics import initialize_metrics, timed

# Initialize metrics collector
metrics = initialize_metrics("my-service", "1.0.0")

# Use decorator for timing operations
@timed("database_query")
async def query_database():
    # Your database query here
    pass

# Manual metrics recording
metrics.record_airtable_request(
    base_id="appXXXXXX",
    table_name="Users",
    operation="list",
    status_code=200,
    duration=0.25
)
```

### 3. Deploy Monitoring Stack

```bash
# Export monitoring configurations
python -c "
from pyairtable_common.metrics.docker_configs import export_monitoring_configs
export_monitoring_configs('./monitoring')
"

# Start monitoring stack
cd monitoring
docker network create pyairtable-network
docker-compose -f docker-compose.monitoring.yml up -d
```

Access dashboards:
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

## Metrics Categories

### 1. HTTP Request Metrics
- `http_requests_total` - Total HTTP requests by method, endpoint, status
- `http_request_duration_seconds` - Request duration histograms
- `http_request_size_bytes` / `http_response_size_bytes` - Request/response sizes

### 2. Airtable API Metrics
- `airtable_api_requests_total` - API requests by base, table, operation
- `airtable_api_duration_seconds` - API request durations
- `airtable_rate_limit_hits_total` - Rate limit violations
- `airtable_rate_limit_remaining` - Remaining quota

### 3. Infrastructure Metrics
- `redis_operations_total` - Redis operations by type
- `circuit_breaker_state` - Circuit breaker states
- `database_connections_active` - Active DB connections

### 4. Service-Specific Metrics

#### Airtable Gateway
- `airtable_cache_operations_total` - Cache operations
- `airtable_api_quota_usage` - API quota usage percentage
- `airtable_request_queue_size` - Request queue size

#### MCP Server
- `mcp_subprocess_count` - Active subprocess count
- `mcp_tool_executions_total` - Tool execution count
- `mcp_protocol_messages_total` - Protocol message count

#### LLM Orchestrator
- `gemini_requests_total` - Gemini API requests
- `gemini_token_usage_total` - Token usage by type
- `llm_active_sessions` - Active session count

#### API Gateway
- `gateway_route_requests_total` - Routed requests
- `gateway_backend_health_status` - Backend health status

## Service Integration Examples

### Airtable Gateway Service

```python
from pyairtable_common.metrics.examples import AirtableGatewayService

service = AirtableGatewayService()
await service.initialize()

# API call with automatic metrics
result = await service.make_airtable_request(
    base_id="appXXXXXX",
    table_name="Users", 
    operation="list"
)
```

### MCP Server Service

```python
from pyairtable_common.metrics.examples import MCPServerService

service = MCPServerService()

# Create subprocess with metrics
process_id = await service.create_subprocess("tool_executor")

# Execute tool with metrics
result = await service.execute_tool("list_files", {"path": "/tmp"})
```

### LLM Orchestrator Service

```python
from pyairtable_common.metrics.examples import LLMOrchestratorService

service = LLMOrchestratorService()

# Create session with metrics
session_id = await service.create_session("chat")

# Make Gemini API call with metrics
response = await service.call_gemini_api(
    session_id=session_id,
    model="gemini-2.5-flash",
    prompt="Hello, world!"
)
```

## Middleware Integration

The metrics system integrates seamlessly with existing PyAirtable middleware:

```python
from pyairtable_common.middleware import setup_middleware
from pyairtable_common.metrics import initialize_metrics

app = FastAPI()
metrics = initialize_metrics("my-service")

setup_middleware(
    app,
    enable_correlation_id=True,  # Existing middleware
    enable_request_logging=True,  # Existing middleware  
    enable_error_handling=True,   # Existing middleware
    enable_metrics=True,          # New metrics middleware
    metrics_collector=metrics
)
```

## Grafana Dashboards

### Available Dashboards

1. **Overview Dashboard** - System-wide health, requests, latency, errors
2. **Airtable Gateway** - API usage, caching, rate limits, quotas
3. **MCP Server** - Subprocess management, tool execution, protocol messages
4. **LLM Orchestrator** - Gemini API usage, sessions, token consumption
5. **Infrastructure** - Redis, circuit breakers, system health
6. **SLA Monitoring** - Availability, error budgets, performance targets

### Dashboard Export

```python
from pyairtable_common.metrics.grafana_dashboards import export_all_dashboards

# Export all dashboards to JSON files
export_all_dashboards("./dashboards")
```

## Alerting

### Pre-configured Alerts

- **ServiceDown** - Service unavailable for >1 minute
- **HighErrorRate** - Error rate >10% for 5 minutes
- **HighLatency** - P95 latency >2 seconds for 5 minutes
- **AirtableRateLimitHit** - Rate limit violations detected
- **CircuitBreakerOpen** - Circuit breaker opened
- **LowCacheHitRatio** - Cache hit ratio <70% for 10 minutes

### Alert Configuration

Alerts are sent via Slack webhooks. Configure in `alertmanager.yml`:

```yaml
receivers:
  - name: "web.hook"
    slack_configs:
      - api_url: "YOUR_SLACK_WEBHOOK_URL"
        channel: "#alerts"
```

## Performance Considerations

### Minimal Overhead Design
- Metrics collection adds <1ms per request
- Async-compatible collectors
- Efficient Redis operations
- Prometheus client optimizations

### Resource Usage
- Memory: ~10MB per service for metrics storage
- CPU: <1% overhead for metrics collection
- Network: ~100KB/min per service for scraping

### Best Practices
- Use histogram buckets appropriate for your latency ranges
- Limit high-cardinality labels (user IDs, etc.)
- Set appropriate scrape intervals (15s default)
- Monitor metrics endpoint performance

## Configuration

### Environment Variables

```bash
# Service configuration
SERVICE_NAME=my-service-py
SERVICE_VERSION=1.0.0

# Redis configuration (for rate limiting metrics)
REDIS_URL=redis://localhost:6379

# Metrics configuration
METRICS_ENABLED=true
METRICS_ENDPOINT=/metrics
```

### Prometheus Configuration

```yaml
scrape_configs:
  - job_name: 'pyairtable-my-service'
    static_configs:
      - targets: ['my-service:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

## Troubleshooting

### Common Issues

1. **Metrics endpoint returns 404**
   - Ensure metrics middleware is enabled
   - Check that `create_metrics_endpoint()` was called

2. **No data in Grafana**
   - Verify Prometheus is scraping endpoints
   - Check service health endpoints
   - Ensure correct time ranges

3. **High cardinality warnings**
   - Review label usage in custom metrics
   - Avoid user IDs or request IDs as labels
   - Use sampling for high-frequency events

4. **Performance degradation**
   - Check metrics collection overhead
   - Review histogram bucket configurations
   - Monitor `/metrics` endpoint response time

### Debug Commands

```bash
# Check metrics endpoint
curl http://localhost:8000/metrics

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check Grafana health
curl http://localhost:3000/api/health
```

## Advanced Usage

### Custom Metrics

```python
from pyairtable_common.metrics import metrics_registry

# Create custom counter
custom_counter = metrics_registry.create_counter(
    "custom_operations_total",
    "Custom business operations",
    labels=["operation_type", "status"]
)

# Use custom metric
labels = metrics_registry.get_common_labels(
    operation_type="data_sync",
    status="success"
)
custom_counter.labels(**labels).inc()
```

### Integration with Circuit Breakers

```python
from pyairtable_common.metrics.integrations import create_metrics_enabled_circuit_breaker

# Create circuit breaker with metrics
circuit_breaker = create_metrics_enabled_circuit_breaker(
    circuit_name="external_api",
    metrics_collector=metrics,
    failure_threshold=5,
    timeout=60.0
)

@circuit_breaker
async def call_external_api():
    # Your API call here
    pass
```

### Integration with Rate Limiters

```python
from pyairtable_common.metrics.integrations import create_metrics_enabled_airtable_limiter

# Create rate limiter with metrics
rate_limiter = create_metrics_enabled_airtable_limiter(redis_client, metrics)

# Rate limiting automatically records metrics
result = await rate_limiter.check_base_limit("appXXXXXX")
```

## Migration Guide

### From No Metrics

1. Add metrics dependency: `prometheus-client>=0.21.0` (already in pyproject.toml)
2. Update service initialization:
   ```python
   # Before
   app = FastAPI()
   
   # After  
   from pyairtable_common.metrics.examples import create_service_with_full_metrics
   app = create_service_with_full_metrics("my-service")
   ```

3. Deploy monitoring stack
4. Import Grafana dashboards

### From Custom Metrics

1. Replace custom metrics with pyairtable-common metrics
2. Update middleware configuration
3. Migrate dashboard configurations
4. Update alerting rules

## Contributing

### Adding New Metrics

1. Define metric in appropriate service config class
2. Add recording methods
3. Update dashboard configurations
4. Add alerting rules if needed
5. Update documentation

### Testing Metrics

```python
import pytest
from pyairtable_common.metrics import initialize_metrics

def test_metrics_collection():
    metrics = initialize_metrics("test-service")
    
    # Record test metric
    metrics.record_http_request(
        method="GET",
        endpoint="/test",
        status_code=200,
        duration=0.1
    )
    
    # Export and verify
    metrics_output = metrics.export_metrics()
    assert "http_requests_total" in metrics_output
```

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- Create GitHub issues for bugs
- Check troubleshooting section first
- Review Prometheus and Grafana documentation
- Consult PyAirtable team for architecture questions