"""
PostgreSQL-based session repository for conversation management
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import selectinload
import json
import logging

from .models import ConversationSession, ConversationMessage, ApiUsageLog
from .session import get_async_session

logger = logging.getLogger(__name__)


class PostgreSQLSessionRepository:
    """
    PostgreSQL-based session repository for persistent conversation storage
    
    This repository provides the same interface as the Redis-based session manager
    but stores data in PostgreSQL for better durability, querying, and analytics.
    """
    
    def __init__(self, session_timeout: int = 3600):
        self.session_timeout = session_timeout
    
    async def initialize(self):
        """Initialize the repository (placeholder for compatibility)"""
        logger.info("PostgreSQL session repository initialized")
    
    async def close(self):
        """Close the repository (placeholder for compatibility)"""
        logger.info("PostgreSQL session repository closed")
    
    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """
        Get session from PostgreSQL or create new one
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Dict containing session data with history
        """
        async with get_async_session() as db:
            try:
                # Get session
                result = await db.execute(
                    select(ConversationSession).where(
                        and_(
                            ConversationSession.session_id == session_id,
                            ConversationSession.is_active == True,
                            or_(
                                ConversationSession.expires_at.is_(None),
                                ConversationSession.expires_at > datetime.now(timezone.utc)
                            )
                        )
                    )
                )\n                session = result.scalar_one_or_none()
                
                if session:
                    # Update last activity
                    session.last_activity = datetime.now(timezone.utc)
                    await db.commit()
                    
                    # Get message history
                    history = await self._get_session_history(db, session_id)
                    
                    # Convert to compatible format
                    session_data = session.to_dict()
                    session_data["history"] = history
                    
                    logger.debug(f"Retrieved session {session_id} from PostgreSQL")
                    return session_data
                else:
                    # Create new session
                    return await self._create_new_session(db, session_id)
                    
            except Exception as e:
                logger.error(f"Error retrieving session {session_id}: {e}")
                await db.rollback()
                # Return new session as fallback
                return await self._create_new_session(db, session_id)
    
    async def _create_new_session(self, db: AsyncSession, session_id: str) -> Dict[str, Any]:
        """Create a new session in PostgreSQL"""
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.session_timeout)
            
            session = ConversationSession(
                session_id=session_id,
                expires_at=expires_at
            )
            
            db.add(session)
            await db.commit()
            
            session_data = session.to_dict()
            session_data["history"] = []
            
            logger.info(f"Created new session {session_id} in PostgreSQL")
            return session_data
            
        except Exception as e:
            logger.error(f"Error creating session {session_id}: {e}")
            await db.rollback()
            # Return minimal session data
            return {
                "session_id": session_id,
                "history": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_activity": datetime.now(timezone.utc).isoformat(),
                "is_active": True,
                "total_messages": 0,
                "metadata": {}
            }
    
    async def _get_session_history(self, db: AsyncSession, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get message history for a session"""
        try:
            result = await db.execute(
                select(ConversationMessage)
                .where(ConversationMessage.session_id == session_id)
                .order_by(ConversationMessage.timestamp.asc())
                .limit(limit)
            )
            
            messages = result.scalars().all()
            return [msg.to_dict() for msg in messages]
            
        except Exception as e:
            logger.error(f"Error getting history for session {session_id}: {e}")
            return []
    
    async def add_message(self, session_id: str, role: str, message: str, 
                         tools_used: List[str] = None, **kwargs):
        """
        Add a message to the session history
        
        Args:
            session_id: Session identifier
            role: Message role ('user', 'assistant', 'system')
            message: Message content
            tools_used: List of tools used (optional)
            **kwargs: Additional message metadata
        """
        async with get_async_session() as db:
            try:
                # Create message record
                msg = ConversationMessage(
                    session_id=session_id,
                    role=role,
                    message=message,
                    tools_used=tools_used or [],
                    token_count=kwargs.get('token_count', 0),
                    cost=kwargs.get('cost', '0.00'),
                    thinking_process=kwargs.get('thinking_process'),
                    response_time_ms=kwargs.get('response_time_ms'),
                    model_used=kwargs.get('model_used'),
                    metadata=kwargs.get('metadata', {})
                )
                
                db.add(msg)
                
                # Update session stats
                await db.execute(
                    update(ConversationSession)
                    .where(ConversationSession.session_id == session_id)
                    .values(
                        last_activity=datetime.now(timezone.utc),
                        total_messages=ConversationSession.total_messages + 1,
                        total_tokens_used=ConversationSession.total_tokens_used + kwargs.get('token_count', 0)
                    )
                )
                
                await db.commit()
                logger.debug(f"Added {role} message to session {session_id}")
                
            except Exception as e:
                logger.error(f"Error adding message to session {session_id}: {e}")
                await db.rollback()
    
    async def clear_session(self, session_id: str) -> bool:
        """
        Clear a session (mark as inactive and optionally delete messages)
        
        Args:
            session_id: Session to clear
            
        Returns:
            bool: True if session was cleared, False otherwise
        """
        async with get_async_session() as db:
            try:
                # Mark session as inactive
                result = await db.execute(
                    update(ConversationSession)
                    .where(ConversationSession.session_id == session_id)
                    .values(is_active=False)
                )
                
                # Optionally delete old messages (keep for analytics)
                # await db.execute(
                #     delete(ConversationMessage)
                #     .where(ConversationMessage.session_id == session_id)
                # )
                
                await db.commit()
                
                cleared = result.rowcount > 0
                if cleared:
                    logger.info(f"Cleared session {session_id}")
                
                return cleared
                
            except Exception as e:
                logger.error(f"Error clearing session {session_id}: {e}")
                await db.rollback()
                return False
    
    async def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get only the history of a session"""
        async with get_async_session() as db:
            return await self._get_session_history(db, session_id)
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Cleanup expired sessions
        
        Returns:
            int: Number of sessions cleaned up
        """
        async with get_async_session() as db:
            try:
                # Mark expired sessions as inactive
                result = await db.execute(
                    update(ConversationSession)
                    .where(
                        and_(
                            ConversationSession.is_active == True,
                            ConversationSession.expires_at < datetime.now(timezone.utc)
                        )
                    )
                    .values(is_active=False)
                )
                
                await db.commit()
                
                cleaned_count = result.rowcount
                if cleaned_count > 0:
                    logger.info(f"Cleaned up {cleaned_count} expired sessions")
                
                return cleaned_count
                
            except Exception as e:
                logger.error(f"Error during session cleanup: {e}")
                await db.rollback()
                return 0
    
    async def get_session_analytics(self, user_id: Optional[str] = None, 
                                  days: int = 7) -> Dict[str, Any]:
        """
        Get session analytics for monitoring and reporting
        
        Args:
            user_id: Filter by specific user (optional)
            days: Number of days to include in analytics
            
        Returns:
            Dict containing analytics data
        """
        async with get_async_session() as db:
            try:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
                
                # Base query conditions
                conditions = [ConversationSession.created_at >= cutoff_date]
                if user_id:
                    conditions.append(ConversationSession.user_id == user_id)
                
                # Total sessions
                total_sessions_result = await db.execute(
                    select(ConversationSession)
                    .where(and_(*conditions))
                )
                total_sessions = len(total_sessions_result.scalars().all())
                
                # Active sessions
                active_conditions = conditions + [ConversationSession.is_active == True]
                active_sessions_result = await db.execute(
                    select(ConversationSession)
                    .where(and_(*active_conditions))
                )
                active_sessions = len(active_sessions_result.scalars().all())
                
                return {
                    "total_sessions": total_sessions,
                    "active_sessions": active_sessions,
                    "period_days": days,
                    "user_id": user_id,
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error generating session analytics: {e}")
                return {
                    "total_sessions": 0,
                    "active_sessions": 0,
                    "period_days": days,
                    "user_id": user_id,
                    "error": str(e)
                }