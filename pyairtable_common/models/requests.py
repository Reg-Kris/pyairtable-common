"""Request models for PyAirtable microservices."""

from typing import Optional, Dict, Any, List
from pydantic import Field, validator
from .base import BaseModel


class ChatRequest(BaseModel):
    """Request model for chat endpoints."""
    
    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    session_id: str = Field(..., regex=r"^[a-zA-Z0-9_-]+$", description="Session identifier")
    base_id: Optional[str] = Field(None, regex=r"^app[a-zA-Z0-9]{14}$", description="Airtable base ID")
    thinking_budget: Optional[int] = Field(None, ge=0, le=10, description="LLM thinking budget")
    
    @validator('message')
    def validate_message(cls, v: str) -> str:
        """Validate and clean message."""
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()
    
    @validator('session_id')
    def validate_session_id(cls, v: str) -> str:
        """Validate session ID format."""
        if len(v) > 100:
            raise ValueError('Session ID too long')
        return v


class ToolExecutionRequest(BaseModel):
    """Request model for MCP tool execution."""
    
    tool_name: str = Field(..., min_length=1, max_length=100, description="Name of tool to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    
    @validator('tool_name')
    def validate_tool_name(cls, v: str) -> str:
        """Validate tool name format."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Tool name must be alphanumeric with underscores/hyphens')
        return v


class AirtableRecordRequest(BaseModel):
    """Request model for Airtable record operations."""
    
    base_id: str = Field(..., regex=r"^app[a-zA-Z0-9]{14}$", description="Airtable base ID")
    table_id: str = Field(..., min_length=1, max_length=100, description="Table ID or name")
    fields: Dict[str, Any] = Field(..., description="Record fields")
    
    @validator('fields')
    def validate_fields(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate field values."""
        if not v:
            raise ValueError('Fields cannot be empty')
        
        # Check for reserved field names
        reserved = {'id', 'createdTime'}
        for field_name in v.keys():
            if field_name in reserved:
                raise ValueError(f'Field name "{field_name}" is reserved')
        
        return v


class SearchRequest(BaseModel):
    """Request model for search operations."""
    
    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    fields: Optional[List[str]] = Field(None, description="Fields to search in")
    max_results: int = Field(50, ge=1, le=1000, description="Maximum results to return")
    
    @validator('query')
    def validate_query(cls, v: str) -> str:
        """Validate search query."""
        return v.strip()
    
    @validator('fields')
    def validate_fields(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate field list."""
        if v is not None:
            # Remove duplicates and empty strings
            v = list(set(field.strip() for field in v if field.strip()))
            if not v:
                return None
        return v