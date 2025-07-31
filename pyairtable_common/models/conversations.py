"""
Database models for conversation and message management.
"""
import enum
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship, Mapped

from ..database.base import ConversationBase


class SessionStatus(enum.Enum):
    """Conversation session status enum."""
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    ERROR = "error"


class MessageRole(enum.Enum):
    """Message role enum."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ConversationSession(ConversationBase):
    """
    Conversation session model for persistent chat management.
    
    Stores high-level information about chat sessions including
    metadata, configuration, and session state.
    """
    
    __tablename__ = 'conversation_sessions'
    
    # Session identification
    session_key: Mapped[str] = Column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique session key for client identification"
    )
    
    # User and context information
    user_id: Mapped[Optional[str]] = Column(
        String(255),
        nullable=True,
        index=True,
        comment="User identifier (for future user management)"
    )
    
    base_id: Mapped[Optional[str]] = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Airtable base ID if session is base-specific"
    )
    
    table_id: Mapped[Optional[str]] = Column(
        String(255),
        nullable=True,
        comment="Airtable table ID if session is table-specific"
    )
    
    # Session metadata
    title: Mapped[Optional[str]] = Column(
        String(500),
        nullable=True,
        comment="Human-readable session title"
    )
    
    description: Mapped[Optional[str]] = Column(
        Text,
        nullable=True,
        comment="Session description or context"
    )
    
    # Session state
    status: Mapped[SessionStatus] = Column(
        SQLEnum(SessionStatus, name="session_status"),
        default=SessionStatus.ACTIVE,
        nullable=False,
        index=True,
        comment="Current session status"
    )
    
    last_activity: Mapped[datetime] = Column(
        "last_activity",
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="Timestamp of last session activity"
    )
    
    expires_at: Mapped[Optional[datetime]] = Column(
        "expires_at",
        nullable=True,
        index=True,
        comment="Session expiration timestamp"
    )
    
    # Configuration and settings
    model_config: Mapped[Optional[Dict[str, Any]]] = Column(
        JSONB,
        nullable=True,
        comment="LLM model configuration (temperature, max_tokens, etc.)"
    )
    
    system_prompt: Mapped[Optional[str]] = Column(
        Text,
        nullable=True,
        comment="Custom system prompt for this session"
    )
    
    context_data: Mapped[Optional[Dict[str, Any]]] = Column(
        JSONB,
        nullable=True,
        comment="Additional context data (Airtable schema, etc.)"
    )
    
    # Statistics
    message_count: Mapped[int] = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Total number of messages in session"
    )
    
    total_tokens: Mapped[int] = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Total tokens used in session"
    )
    
    tool_executions: Mapped[int] = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Total number of tool executions"
    )
    
    # Relationships
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )
    
    def __repr__(self) -> str:
        return f"<ConversationSession(id={self.id}, session_key={self.session_key}, status={self.status.value})>"
    
    def is_active(self) -> bool:
        """Check if session is active and not expired."""
        if self.status != SessionStatus.ACTIVE:
            return False
        
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        
        return True
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()
    
    def add_message_stats(self, token_count: int = 0, tool_executions: int = 0):
        """Update session statistics when a message is added."""
        self.message_count += 1
        self.total_tokens += token_count
        self.tool_executions += tool_executions
        self.update_activity()


class Message(ConversationBase):
    """
    Individual message model for chat conversations.
    
    Stores individual messages with their content, metadata,
    and tool execution details.
    """
    
    __tablename__ = 'messages'
    
    # Session relationship
    session_id: Mapped[UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey('conversations.conversation_sessions.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="Foreign key to conversation session"
    )
    
    session: Mapped[ConversationSession] = relationship(
        "ConversationSession",
        back_populates="messages"
    )
    
    # Message identification
    sequence_number: Mapped[int] = Column(
        Integer,
        nullable=False,
        comment="Message sequence number within session"
    )
    
    role: Mapped[MessageRole] = Column(
        SQLEnum(MessageRole, name="message_role"),
        nullable=False,
        index=True,
        comment="Message role (user, assistant, system, tool)"
    )
    
    # Message content
    content: Mapped[str] = Column(
        Text,
        nullable=False,
        comment="Message content"
    )
    
    thinking_process: Mapped[Optional[str]] = Column(
        Text,
        nullable=True,
        comment="LLM thinking process (for assistant messages)"
    )
    
    # Tool execution details
    tools_used: Mapped[Optional[List[Dict[str, Any]]]] = Column(
        JSONB,
        nullable=True,
        comment="List of tools used in this message"
    )
    
    tool_results: Mapped[Optional[List[Dict[str, Any]]]] = Column(
        JSONB,
        nullable=True,
        comment="Results from tool executions"
    )
    
    # Metadata
    token_count: Mapped[int] = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Token count for this message"
    )
    
    processing_time_ms: Mapped[Optional[int]] = Column(
        Integer,
        nullable=True,
        comment="Processing time in milliseconds"
    )
    
    model_used: Mapped[Optional[str]] = Column(
        String(100),
        nullable=True,
        comment="LLM model used for generation"
    )
    
    # Status and error handling
    is_error: Mapped[bool] = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this message represents an error"
    )
    
    error_details: Mapped[Optional[Dict[str, Any]]] = Column(
        JSONB,
        nullable=True,
        comment="Error details if is_error is True"
    )
    
    # Additional metadata
    metadata: Mapped[Optional[Dict[str, Any]]] = Column(
        JSONB,
        nullable=True,
        comment="Additional message metadata"
    )
    
    def __repr__(self) -> str:
        return f"<Message(id={self.id}, session_id={self.session_id}, role={self.role.value}, seq={self.sequence_number})>"
    
    @property
    def content_preview(self) -> str:
        """Get a preview of the message content."""
        if not self.content:
            return ""
        
        preview = self.content.strip()
        if len(preview) > 100:
            preview = preview[:97] + "..."
        
        return preview
    
    def has_tools(self) -> bool:
        """Check if message used any tools."""
        return bool(self.tools_used)
    
    def get_tool_names(self) -> List[str]:
        """Get list of tool names used in this message."""
        if not self.tools_used:
            return []
        
        return [tool.get('name', 'unknown') for tool in self.tools_used]


class ToolExecution(ConversationBase):
    """
    Detailed tool execution tracking.
    
    Stores detailed information about individual tool executions
    for analytics and debugging purposes.
    """
    
    __tablename__ = 'tool_executions'
    
    # Message relationship
    message_id: Mapped[UUID] = Column(
        UUID(as_uuid=True),
        ForeignKey('conversations.messages.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="Foreign key to message"
    )
    
    message: Mapped[Message] = relationship("Message")
    
    # Tool details
    tool_name: Mapped[str] = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Name of the executed tool"
    )
    
    tool_version: Mapped[Optional[str]] = Column(
        String(50),
        nullable=True,
        comment="Version of the tool"
    )
    
    # Execution details
    input_parameters: Mapped[Dict[str, Any]] = Column(
        JSONB,
        nullable=False,
        comment="Input parameters passed to tool"
    )
    
    output_result: Mapped[Optional[Dict[str, Any]]] = Column(
        JSONB,
        nullable=True,
        comment="Tool execution result"
    )
    
    # Performance metrics
    execution_time_ms: Mapped[int] = Column(
        Integer,
        nullable=False,
        comment="Tool execution time in milliseconds"
    )
    
    memory_usage_mb: Mapped[Optional[int]] = Column(
        Integer,
        nullable=True,
        comment="Memory usage in megabytes"
    )
    
    # Status
    success: Mapped[bool] = Column(
        Boolean,
        nullable=False,
        comment="Whether tool execution was successful"
    )
    
    error_message: Mapped[Optional[str]] = Column(
        Text,
        nullable=True,
        comment="Error message if execution failed"
    )
    
    error_type: Mapped[Optional[str]] = Column(
        String(100),
        nullable=True,
        comment="Type of error that occurred"
    )
    
    # Context
    correlation_context: Mapped[Optional[Dict[str, Any]]] = Column(
        JSONB,
        nullable=True,
        comment="Additional correlation context"
    )
    
    def __repr__(self) -> str:
        return f"<ToolExecution(id={self.id}, tool={self.tool_name}, success={self.success})>"
    
    @property
    def duration_seconds(self) -> float:
        """Get execution time in seconds."""
        return self.execution_time_ms / 1000.0