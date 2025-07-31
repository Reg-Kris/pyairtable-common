"""Response models for PyAirtable microservices."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import Field
from .base import BaseModel, TimestampedModel


class ChatResponse(BaseModel):
    """Response model for chat endpoints."""
    
    response: str = Field(..., description="LLM response")
    thinking_process: Optional[str] = Field(None, description="LLM thinking process")
    tools_used: List[str] = Field(default_factory=list, description="Tools executed during response")
    session_id: str = Field(..., description="Session identifier")
    timestamp: str = Field(..., description="Response timestamp")
    
    @property
    def has_thinking(self) -> bool:
        """Check if response includes thinking process."""
        return self.thinking_process is not None and len(self.thinking_process.strip()) > 0


class HealthResponse(BaseModel):
    """Response model for health check endpoints."""
    
    status: str = Field(..., description="Service status")
    service: Optional[str] = Field(None, description="Service name")
    version: Optional[str] = Field(None, description="Service version")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Check timestamp")
    details: Optional[Dict[str, Any]] = Field(None, description="Detailed health information")


class ErrorResponse(BaseModel):
    """Response model for error cases."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Error timestamp")


class ToolExecutionResponse(BaseModel):
    """Response model for MCP tool execution."""
    
    result: Dict[str, Any] = Field(..., description="Tool execution result")
    tool: str = Field(..., description="Tool name")
    execution_time_ms: Optional[int] = Field(None, description="Execution time in milliseconds")
    success: bool = Field(True, description="Execution success status")
    error: Optional[str] = Field(None, description="Error message if failed")


class PaginatedResponse(BaseModel):
    """Response model for paginated results."""
    
    data: List[Dict[str, Any]] = Field(..., description="Result data")
    total: int = Field(..., description="Total number of items")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(50, description="Items per page")
    has_more: bool = Field(False, description="Whether more pages exist")
    
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        return (self.total + self.page_size - 1) // self.page_size


class SessionHistoryResponse(BaseModel):
    """Response model for session history."""
    
    session_id: str = Field(..., description="Session identifier")
    history: List[Dict[str, Any]] = Field(..., description="Conversation history")
    total_messages: int = Field(..., description="Total number of messages")
    created_at: Optional[str] = Field(None, description="Session creation timestamp")
    last_activity: Optional[str] = Field(None, description="Last activity timestamp")


class ServiceStatusResponse(BaseModel):
    """Response model for service status aggregation."""
    
    status: str = Field(..., description="Overall system status")
    services: List[Dict[str, Any]] = Field(..., description="Individual service statuses")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Status check timestamp")
    
    @property
    def healthy_services(self) -> int:
        """Count of healthy services."""
        return sum(1 for service in self.services if service.get('status') == 'healthy')
    
    @property
    def total_services(self) -> int:
        """Total number of services."""
        return len(self.services)