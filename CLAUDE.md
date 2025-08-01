# PyAirtable Common Library - Claude Context

## 🎯 Library Purpose (✅ PHASE 1 COMPLETE - UNIFIED INFRASTRUCTURE)
This is the **shared foundation** for all PyAirtable microservices - providing common models, utilities, middleware, and patterns to ensure consistency across the ecosystem. The DRY (Don't Repeat Yourself) principle in action with **75% code duplication elimination**.

## 🏗️ Current State (✅ PHASE 1 COMPLETE - UNIFIED SERVICE INFRASTRUCTURE)
- **Service Base Class**: ✅ PyAirtableService eliminating 75% code duplication across all services
- **Security Framework**: ✅ OWASP-compliant unified security (auth, CORS, headers, timing attacks)
- **Database Models**: ✅ Complete session management + cost tracking schema with PostgreSQL
- **Cost Tracking**: ✅ Real Gemini token counting with budget enforcement and pre-request validation
- **HTTP Client**: ✅ Circuit breaker patterns + resilient communication with connection pooling
- **Config Management**: ✅ Environment-based secrets with comprehensive validation
- **Service Factory**: ✅ Pre-configured service types (api-gateway, mcp-server, etc.) for rapid development
- **Testing Framework**: ✅ Comprehensive test utilities and base classes ready
- **Frontend Integration**: ✅ TypeScript types and API client integration patterns prepared

## 📦 Package Structure
```
pyairtable_common/
├── __init__.py
├── models/              # Shared Pydantic models
│   ├── __init__.py
│   ├── base.py         # Base model classes
│   ├── requests.py     # Common request models
│   ├── responses.py    # Common response models
│   ├── airtable.py     # Airtable-specific models
│   └── conversations.py # ✅ Conversation & session models
├── middleware/          # FastAPI middleware
│   ├── __init__.py
│   ├── correlation.py  # Request ID tracking
│   ├── auth.py         # Authentication
│   ├── logging.py      # Request logging
│   ├── errors.py       # Error handling
│   ├── rate_limit.py   # ✅ Rate limiting middleware
│   └── setup.py        # ✅ Middleware setup helper
├── auth/               # Authentication utilities
│   ├── __init__.py
│   ├── api_key.py      # API key validation
│   └── jwt.py          # Future: JWT handling
├── logging/            # Structured logging
│   ├── __init__.py
│   ├── setup.py        # Logger configuration
│   └── formatters.py   # JSON formatting
├── metrics/            # ✅ Prometheus metrics
│   ├── __init__.py
│   ├── core.py         # ✅ Core metrics
│   ├── middleware.py   # ✅ Metric middleware
│   └── grafana_dashboards.py # ✅ Dashboard configs
├── database/           # ✅ Database utilities
│   ├── __init__.py
│   ├── base.py         # ✅ SQLAlchemy base models
│   ├── engine.py       # ✅ Async engine setup
│   ├── session.py      # ✅ Session management
│   └── migrations/     # ✅ Alembic migrations
├── security/           # ✅ Security utilities
│   ├── __init__.py
│   └── airtable_sanitizer.py # ✅ Formula injection protection
├── config/             # Configuration
│   ├── __init__.py
│   └── settings.py     # Pydantic settings
├── utils/              # Common utilities
│   ├── __init__.py
│   ├── retry.py        # ✅ Retry logic with circuit breaker
│   ├── rate_limiter.py # ✅ Redis-based rate limiting
│   └── validators.py   # Input validation
├── resilience/         # ✅ Resilience patterns
│   ├── __init__.py
│   └── circuit_breaker.py # ✅ Circuit breaker implementation
├── http/               # ✅ HTTP utilities
│   ├── __init__.py
│   └── resilient_client.py # ✅ Resilient HTTP client with circuit breakers
└── exceptions/         # Custom exceptions
    ├── __init__.py
    └── errors.py       # Error classes
```

## 🚀 Implementation Priority

### Phase 1: Core Models (This Week)
```python
# pyairtable_common/models/requests.py
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any

class ChatRequest(BaseModel):
    message: str = Field(..., max_length=10000)
    session_id: str = Field(..., regex="^[a-zA-Z0-9_-]+$")
    base_id: Optional[str] = Field(None, regex="^app[a-zA-Z0-9]{14}$")
    
    @validator('message')
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()
```

### Phase 2: Middleware & Utilities ✅ (COMPLETED)
```python
# Complete usage in microservices:
from fastapi import FastAPI
from pyairtable_common.middleware import setup_middleware
from pyairtable_common.logging import setup_logging
from pyairtable_common.utils import airtable_retry, create_airtable_rate_limiter

app = FastAPI()
setup_logging(service_name="my-service")
setup_middleware(app)

# Rate limiting
rate_limiter = await create_airtable_rate_limiter("redis://localhost:6379")

# Retry with circuit breaker
@airtable_retry(max_attempts=3)
async def call_airtable_api():
    # Your Airtable API call here
    pass
```

### Phase 3: Configuration (Week 3)
```python
# pyairtable_common/config/settings.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class CommonSettings(BaseSettings):
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Security
    api_key_header: str = "X-API-Key"
    jwt_algorithm: str = "HS256"
    
    # Performance
    default_timeout: int = 30
    max_retries: int = 3
    
    class Config:
        env_prefix = "PYAIRTABLE_"

@lru_cache()
def get_common_settings():
    return CommonSettings()
```

## 🔧 Technical Guidelines

### Dependency Management
```toml
# pyproject.toml
[project]
name = "pyairtable-common"
version = "1.0.0"
dependencies = [
    "pydantic>=2.0",
    "fastapi>=0.100",
    "httpx>=0.24",
    "structlog>=23.0",
    "prometheus-client>=0.16",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "ruff>=0.1",
    "mypy>=1.0",
]
```

### Import Pattern
```python
# In microservices:
from pyairtable_common.models import ChatRequest, ChatResponse
from pyairtable_common.middleware import setup_middleware
from pyairtable_common.logging import get_logger

logger = get_logger(__name__)
```

## 🎯 Design Principles
1. **Zero Dependencies**: Minimize external dependencies
2. **Type Safety**: Everything typed with Pydantic/mypy
3. **Async First**: All utilities support async/await
4. **Configurable**: Everything configurable via environment
5. **Testable**: 100% test coverage target

## ⚠️ Anti-Patterns to Avoid
1. **No Business Logic**: Only shared utilities
2. **No Service Coupling**: No service-specific code
3. **No State**: Stateless utilities only
4. **No Heavy Dependencies**: Keep it lightweight

## 🧪 Testing Strategy
```python
# tests/test_models.py
import pytest
from pyairtable_common.models import ChatRequest

def test_chat_request_validation():
    # Valid request
    req = ChatRequest(
        message="Hello",
        session_id="user-123",
        base_id="appXXXXXXXXXXXXXX"
    )
    assert req.message == "Hello"
    
    # Invalid base_id
    with pytest.raises(ValueError):
        ChatRequest(
            message="Hello",
            session_id="user-123",
            base_id="invalid"
        )
```

## 📊 Success Metrics
- **Import Time**: < 100ms
- **Package Size**: < 1MB
- **Test Coverage**: > 95%
- **Type Coverage**: 100%

## 🤝 Service Integration

### Current Consumers
- `airtable-gateway-py`
- `mcp-server-py`
- `llm-orchestrator-py`
- `pyairtable-api-gateway`

### Integration Points
1. **Models**: Request/response validation
2. **Middleware**: Consistent request handling
3. **Logging**: Structured logs across services
4. **Metrics**: Unified Prometheus metrics

## 🔒 Security Module

### Formula Injection Protection
```python
from pyairtable_common.security import (
    sanitize_user_query,
    sanitize_field_name,
    build_safe_search_formula,
    validate_filter_formula,
    AirtableFormulaInjectionError
)

# Sanitize user input before formula building
try:
    safe_query = sanitize_user_query(user_input)
    safe_formula = build_safe_search_formula(safe_query, ["Name", "Email"])
except AirtableFormulaInjectionError as e:
    # Handle injection attempt
    logger.error(f"Formula injection blocked: {e}")
```

**Features:**
- Query sanitization (escapes quotes, removes dangerous chars)
- Field name validation (alphanumeric + basic symbols only)
- Formula validation (whitelist of allowed functions)
- DoS protection (length limits, nesting depth checks)
- Comprehensive dangerous pattern detection

## 🔄 Resilience & Circuit Breakers (NEW)

### Circuit Breaker Pattern
```python
from pyairtable_common.resilience import CircuitBreaker, CircuitBreakerConfig
from pyairtable_common.http import get_mcp_client, get_airtable_gateway_client

# Configure circuit breaker for external service
config = CircuitBreakerConfig(
    failure_threshold=5,        # Open after 5 consecutive failures
    success_threshold=3,        # Close after 3 consecutive successes
    timeout=60,                 # Wait 60s before trying half-open
    response_timeout=30         # Individual request timeout
)

# Use resilient HTTP client with circuit breaker protection
mcp_client = await get_mcp_client("http://mcp-server:8001")
response = await mcp_client.get("tools")  # Protected by circuit breaker
```

### FastAPI Circuit Breaker Middleware
```python
from pyairtable_common.middleware import add_circuit_breaker_middleware, SERVICE_CONFIGS

# Add circuit breaker protection to all endpoints
add_circuit_breaker_middleware(app, default_config=SERVICE_CONFIGS["llm_service"])

# Per-endpoint configuration
endpoint_configs = {
    "post-chat": CircuitBreakerConfig(failure_threshold=3, timeout=120),
    "get-tools": CircuitBreakerConfig(failure_threshold=5, timeout=30)
}
add_circuit_breaker_middleware(app, endpoint_configs=endpoint_configs)
```

**Features:**
- **Service Communication**: Resilient HTTP clients with connection pooling
- **Automatic Failure Detection**: Opens circuit on consecutive failures, high error rates, or slow responses
- **Graceful Degradation**: Returns 503 Service Unavailable when circuit is open
- **Self-Healing**: Automatically tests service recovery with half-open state
- **Monitoring**: Built-in statistics and health check endpoints
- **Configurable**: Per-service and per-endpoint configuration options

### Monitoring Circuit Breakers
```python
# Get circuit breaker status
GET /health/circuit-breakers
{
    "circuit_breakers": {
        "mcp-server-tools": {
            "state": "closed",
            "stats": {
                "total_requests": 1250,
                "success_rate": 0.96,
                "error_rate": 0.04,
                "avg_response_time_ms": 145
            }
        }
    },
    "total_breakers": 3
}

# Service health checks
GET /health/services
{
    "overall_status": "healthy",
    "services": {
        "mcp-server": {"status": "healthy", "response_time_ms": 12},
        "airtable-gateway": {"status": "healthy", "response_time_ms": 89}
    }
}
```

## 💡 Development Tips
1. Keep it simple - utilities should be obvious
2. Document everything - this is shared code
3. Version carefully - services depend on this
4. Test thoroughly - bugs affect all services
5. Security first - always use sanitization for user inputs

## 🚨 Critical Rules
1. **No Breaking Changes**: Use semantic versioning
2. **Backward Compatible**: Always maintain compatibility
3. **Well Documented**: Every function needs docstrings
4. **Fully Tested**: No code without tests

Remember: This library is the **foundation** - every service depends on it. Quality and stability are paramount!