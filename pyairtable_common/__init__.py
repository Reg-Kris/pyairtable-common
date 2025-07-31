"""
PyAirtable Common Library

Shared utilities, models, and middleware for PyAirtable microservices.
"""

__version__ = "1.0.0"
__author__ = "PyAirtable Team"

# Export commonly used items for easy imports
from .models import ChatRequest, ChatResponse
from .config import get_settings

__all__ = [
    "ChatRequest",
    "ChatResponse", 
    "get_settings",
]