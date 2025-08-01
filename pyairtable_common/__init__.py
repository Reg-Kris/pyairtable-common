"""
PyAirtable Common Library

Shared utilities, models, and middleware for PyAirtable microservices.
"""

__version__ = "1.0.0"
__author__ = "PyAirtable Team"

# Export commonly used items for easy imports
from .models import ChatRequest, ChatResponse
from .config import get_settings

# Service base class and factory patterns - NEW
from .service import PyAirtableService, ServiceConfig, create_service, ServiceFactory

__all__ = [
    "ChatRequest",
    "ChatResponse", 
    "get_settings",
    # Service infrastructure
    "PyAirtableService",
    "ServiceConfig", 
    "create_service",
    "ServiceFactory",
]