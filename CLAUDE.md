# PyAirtable Common Library - Claude Context

## 🎯 Library Purpose
This is the **shared foundation** for all PyAirtable microservices - providing common models, utilities, middleware, and patterns to ensure consistency across the ecosystem. It's the DRY (Don't Repeat Yourself) principle in action.

## 🏗️ Current State
- **Status**: 🚧 New repository (just created)
- **Models**: ❌ Not implemented yet
- **Middleware**: ❌ Not implemented yet
- **Utilities**: ❌ Not implemented yet
- **Testing**: ❌ No tests yet
- **Documentation**: ⚠️ Basic README only

## 📦 Package Structure
```
pyairtable_common/
├── __init__.py
├── models/              # Shared Pydantic models
│   ├── __init__.py
│   ├── base.py         # Base model classes
│   ├── requests.py     # Common request models
│   ├── responses.py    # Common response models
│   └── airtable.py     # Airtable-specific models
├── middleware/          # FastAPI middleware
│   ├── __init__.py
│   ├── correlation.py  # Request ID tracking
│   ├── auth.py         # Authentication
│   ├── logging.py      # Request logging
│   └── errors.py       # Error handling
├── auth/               # Authentication utilities
│   ├── __init__.py
│   ├── api_key.py      # API key validation
│   └── jwt.py          # Future: JWT handling
├── logging/            # Structured logging
│   ├── __init__.py
│   ├── setup.py        # Logger configuration
│   └── formatters.py   # JSON formatting
├── metrics/            # Prometheus metrics
│   ├── __init__.py
│   ├── collectors.py   # Metric collectors
│   └── middleware.py   # Metric middleware
├── database/           # Database utilities
│   ├── __init__.py
│   ├── models.py       # SQLAlchemy base
│   └── session.py      # Session management
├── config/             # Configuration
│   ├── __init__.py
│   └── settings.py     # Pydantic settings
├── utils/              # Common utilities
│   ├── __init__.py
│   ├── retry.py        # Retry logic
│   ├── cache.py        # Caching helpers
│   └── validators.py   # Input validation
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

### Phase 2: Middleware (Next Week)
```python
# pyairtable_common/middleware/correlation.py
from fastapi import Request
import uuid

async def correlation_id_middleware(request: Request, call_next):
    request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers['X-Request-ID'] = request_id
    return response
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

## 💡 Development Tips
1. Keep it simple - utilities should be obvious
2. Document everything - this is shared code
3. Version carefully - services depend on this
4. Test thoroughly - bugs affect all services

## 🚨 Critical Rules
1. **No Breaking Changes**: Use semantic versioning
2. **Backward Compatible**: Always maintain compatibility
3. **Well Documented**: Every function needs docstrings
4. **Fully Tested**: No code without tests

Remember: This library is the **foundation** - every service depends on it. Quality and stability are paramount!