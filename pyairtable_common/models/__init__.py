"""Shared Pydantic models and SQLAlchemy models for PyAirtable microservices."""

# Pydantic models for API serialization
from .base import BaseModel
from .requests import ChatRequest, ToolExecutionRequest
from .responses import ChatResponse, HealthResponse
from .airtable import AirtableRecord, AirtableTable, AirtableBase

# SQLAlchemy models for database persistence
from .conversations import (
    ConversationSession,
    Message,
    ToolExecution,
    SessionStatus,
    MessageRole,
)

__all__ = [
    # Pydantic models
    "BaseModel",
    "ChatRequest",
    "ToolExecutionRequest", 
    "ChatResponse",
    "HealthResponse",
    "AirtableRecord",
    "AirtableTable",
    "AirtableBase",
    # SQLAlchemy models
    "ConversationSession",
    "Message",
    "ToolExecution",
    "SessionStatus",
    "MessageRole",
]