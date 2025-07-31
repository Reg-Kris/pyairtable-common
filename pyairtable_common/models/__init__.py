"""Shared Pydantic models for PyAirtable microservices."""

from .base import BaseModel
from .requests import ChatRequest, ToolExecutionRequest
from .responses import ChatResponse, HealthResponse
from .airtable import AirtableRecord, AirtableTable, AirtableBase

__all__ = [
    "BaseModel",
    "ChatRequest",
    "ToolExecutionRequest", 
    "ChatResponse",
    "HealthResponse",
    "AirtableRecord",
    "AirtableTable",
    "AirtableBase",
]