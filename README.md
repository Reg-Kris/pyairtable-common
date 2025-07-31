# pyairtable-common

Shared Python library for PyAirtable microservices - common utilities, models, and middleware

## Overview

This library provides shared components used across all PyAirtable microservices:
- Pydantic models for request/response validation
- Common middleware (auth, logging, correlation IDs)
- Shared utilities and helper functions
- Database models and base classes
- Configuration management
- Security utilities

## Installation

### For Development
```bash
git clone https://github.com/Reg-Kris/pyairtable-common.git
cd pyairtable-common
pip install -e .
```

### In Your Service
```bash
# Add to requirements.txt
pyairtable-common @ git+https://github.com/Reg-Kris/pyairtable-common.git@main

# Or for specific version
pyairtable-common @ git+https://github.com/Reg-Kris/pyairtable-common.git@v1.0.0
```

## Usage

```python
# Import common components
from pyairtable_common.models import ChatRequest, ChatResponse
from pyairtable_common.middleware import correlation_id_middleware
from pyairtable_common.logging import setup_structured_logging
from pyairtable_common.config import get_settings
from pyairtable_common.auth import verify_api_key
```

## Package Structure

```
pyairtable_common/
├── models/           # Shared Pydantic models
├── middleware/       # FastAPI middleware
├── auth/            # Authentication utilities
├── logging/         # Structured logging setup
├── metrics/         # Prometheus metrics
├── database/        # SQLAlchemy base classes
├── config/          # Configuration management
├── utils/           # Common utilities
└── exceptions/      # Custom exceptions
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check .

# Run type checking
mypy pyairtable_common
```

## Contributing

1. Make changes in a feature branch
2. Add tests for new functionality
3. Ensure all tests pass
4. Update version in `pyproject.toml`
5. Create pull request

## Version History

- v1.0.0 - Initial release with basic shared components