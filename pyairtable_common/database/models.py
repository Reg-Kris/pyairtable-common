"""
Database models for PyAirtable microservices
"""

from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, Index, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from datetime import datetime
import uuid

from .base import Base


class ConversationSession(Base):
    """Model for conversation sessions"""
    __tablename__ = "conversation_sessions"
    
    # Primary key
    session_id = Column(String(255), primary_key=True, index=True)
    
    # Session metadata
    user_id = Column(String(255), index=True, nullable=True)  # Future: user identification
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Session configuration
    base_id = Column(String(255), nullable=True)  # Airtable base ID
    thinking_budget = Column(Integer, default=5)
    max_tokens = Column(Integer, default=4000)
    temperature = Column(String(10), default="0.1")
    
    # Session state
    is_active = Column(Boolean, default=True, index=True)
    total_messages = Column(Integer, default=0)
    total_tokens_used = Column(Integer, default=0)
    total_cost = Column(String(20), default="0.00")  # Store as string to avoid float precision issues
    
    # Metadata
    metadata = Column(JSON, default=dict)  # Additional session data
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_session_user_created', 'user_id', 'created_at'),
        Index('ix_session_activity_active', 'last_activity', 'is_active'),
        Index('ix_session_expires', 'expires_at'),
    )
    
    def to_dict(self):
        """Convert to dictionary format compatible with existing session manager"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "base_id": self.base_id,
            "thinking_budget": self.thinking_budget,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "is_active": self.is_active,
            "total_messages": self.total_messages,
            "total_tokens_used": self.total_tokens_used,
            "total_cost": self.total_cost,
            "metadata": self.metadata or {}
        }


class ConversationMessage(Base):
    """Model for individual messages within conversations"""
    __tablename__ = "conversation_messages"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key to session
    session_id = Column(String(255), nullable=False, index=True)
    
    # Message content
    role = Column(String(50), nullable=False, index=True)  # 'user', 'assistant', 'system'
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Message metadata
    tools_used = Column(JSON, default=list)  # List of tool names used
    token_count = Column(Integer, default=0)
    cost = Column(String(20), default="0.00")  # Individual message cost
    thinking_process = Column(Text, nullable=True)  # Gemini thinking output
    
    # Performance tracking
    response_time_ms = Column(Integer, nullable=True)  # Response time in milliseconds
    model_used = Column(String(100), nullable=True)  # e.g., "gemini-2.5-flash"
    
    # Metadata
    metadata = Column(JSON, default=dict)
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_message_session_timestamp', 'session_id', 'timestamp'),
        Index('ix_message_role_timestamp', 'role', 'timestamp'),
        Index('ix_message_session_role', 'session_id', 'role'),
    )
    
    def to_dict(self):
        """Convert to dictionary format compatible with existing session manager"""
        return {
            "id": str(self.id),
            "session_id": self.session_id,
            "role": self.role,
            "message": self.message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "tools_used": self.tools_used or [],
            "token_count": self.token_count,
            "cost": self.cost,
            "thinking_process": self.thinking_process,
            "response_time_ms": self.response_time_ms,
            "model_used": self.model_used,
            "metadata": self.metadata or {}
        }


class ApiUsageLog(Base):
    """Model for API usage tracking and cost monitoring"""
    __tablename__ = "api_usage_logs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Request identification
    session_id = Column(String(255), nullable=True, index=True)
    user_id = Column(String(255), nullable=True, index=True)
    correlation_id = Column(String(255), nullable=True, index=True)
    
    # API call details
    service_name = Column(String(100), nullable=False, index=True)  # 'gemini', 'airtable', etc.
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Usage metrics
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost = Column(String(20), default="0.00")
    
    # Performance metrics
    response_time_ms = Column(Integer, nullable=True)
    status_code = Column(Integer, nullable=True)
    success = Column(Boolean, default=True, index=True)
    
    # Additional data
    model_used = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    metadata = Column(JSON, default=dict)
    
    # Indexes for analytics and cost tracking
    __table_args__ = (
        Index('ix_usage_service_timestamp', 'service_name', 'timestamp'),
        Index('ix_usage_user_timestamp', 'user_id', 'timestamp'),
        Index('ix_usage_session_timestamp', 'session_id', 'timestamp'),
        Index('ix_usage_cost_timestamp', 'cost', 'timestamp'),
        Index('ix_usage_success_timestamp', 'success', 'timestamp'),
    )
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "session_id": self.session_id,
            "user_id": self.user_id,
            "correlation_id": self.correlation_id,
            "service_name": self.service_name,
            "endpoint": self.endpoint,
            "method": self.method,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost": self.cost,
            "response_time_ms": self.response_time_ms,
            "status_code": self.status_code,
            "success": self.success,
            "model_used": self.model_used,
            "error_message": self.error_message,
            "metadata": self.metadata or {}
        }


class SessionBudget(Base):
    """Model for session-level budget limits and tracking"""
    __tablename__ = "session_budgets"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Budget identification
    session_id = Column(String(255), nullable=False, unique=True, index=True)
    
    # Budget configuration
    budget_limit = Column(String(20), nullable=False)  # Decimal stored as string
    spent_amount = Column(String(20), default="0.00")  # Decimal stored as string
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    reset_at = Column(DateTime(timezone=True), nullable=True)  # For recurring budgets
    
    # Budget settings
    is_active = Column(Boolean, default=True)
    alert_threshold = Column(Float, default=0.8)  # Alert at 80%
    reset_period = Column(String(20), default="session")  # 'session', 'daily', 'weekly', 'monthly'
    
    # Metadata
    metadata = Column(JSON, default=dict)
    
    # Indexes
    __table_args__ = (
        Index('ix_session_budget_active', 'is_active'),
        Index('ix_session_budget_created', 'created_at'),
    )
    
    def to_dict(self):
        """Convert to dictionary"""
        from decimal import Decimal
        return {
            "id": str(self.id),
            "session_id": self.session_id,
            "budget_limit": self.budget_limit,
            "spent_amount": self.spent_amount,
            "remaining": str(Decimal(self.budget_limit) - Decimal(self.spent_amount)),
            "usage_percent": float((Decimal(self.spent_amount) / Decimal(self.budget_limit)) * 100),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "reset_at": self.reset_at.isoformat() if self.reset_at else None,
            "is_active": self.is_active,
            "alert_threshold": self.alert_threshold,
            "reset_period": self.reset_period,
            "metadata": self.metadata or {}
        }


class UserBudget(Base):
    """Model for user-level budget limits and tracking"""
    __tablename__ = "user_budgets"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Budget identification
    user_id = Column(String(255), nullable=False, index=True)
    
    # Budget configuration
    budget_limit = Column(String(20), nullable=False)  # Decimal stored as string
    spent_amount = Column(String(20), default="0.00")  # Decimal stored as string
    
    # Time period for budget (allows multiple budgets per user)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    reset_period = Column(String(20), default="monthly")  # 'daily', 'weekly', 'monthly'
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Budget settings
    is_active = Column(Boolean, default=True)
    alert_threshold = Column(Float, default=0.8)  # Alert at 80%
    
    # Metadata
    metadata = Column(JSON, default=dict)
    
    # Indexes
    __table_args__ = (
        Index('ix_user_budget_period', 'user_id', 'period_start', 'period_end'),
        Index('ix_user_budget_active', 'is_active'),
        Index('ix_user_budget_created', 'created_at'),
        # Unique constraint for active budgets per user per period
        Index('ix_user_budget_unique_active', 'user_id', 'reset_period', 'is_active', unique=True),
    )
    
    def to_dict(self):
        """Convert to dictionary"""
        from decimal import Decimal
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "budget_limit": self.budget_limit,
            "spent_amount": self.spent_amount,
            "remaining": str(Decimal(self.budget_limit) - Decimal(self.spent_amount)),
            "usage_percent": float((Decimal(self.spent_amount) / Decimal(self.budget_limit)) * 100),
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "reset_period": self.reset_period,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
            "alert_threshold": self.alert_threshold,
            "metadata": self.metadata or {}
        }


class BudgetAlert(Base):
    """Model for budget alert history and notifications"""
    __tablename__ = "budget_alerts"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Alert identification
    session_id = Column(String(255), nullable=True, index=True)
    user_id = Column(String(255), nullable=True, index=True)
    budget_type = Column(String(20), nullable=False)  # 'session' or 'user'
    
    # Alert details
    alert_type = Column(String(50), nullable=False)  # 'threshold_exceeded', 'budget_exceeded', 'budget_reset'
    threshold_percent = Column(Float, nullable=True)  # Threshold that triggered alert
    current_usage = Column(String(20), nullable=False)  # Current spending
    budget_limit = Column(String(20), nullable=False)  # Budget limit at time of alert
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Alert status
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional data
    message = Column(Text, nullable=True)
    metadata = Column(JSON, default=dict)
    
    # Indexes
    __table_args__ = (
        Index('ix_alert_session_created', 'session_id', 'created_at'),
        Index('ix_alert_user_created', 'user_id', 'created_at'),
        Index('ix_alert_type_created', 'alert_type', 'created_at'),
        Index('ix_alert_acknowledged', 'is_acknowledged'),
    )
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "session_id": self.session_id,
            "user_id": self.user_id,
            "budget_type": self.budget_type,
            "alert_type": self.alert_type,
            "threshold_percent": self.threshold_percent,
            "current_usage": self.current_usage,
            "budget_limit": self.budget_limit,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_acknowledged": self.is_acknowledged,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "message": self.message,
            "metadata": self.metadata or {}
        }