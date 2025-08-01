"""
Database-backed budget management repository
"""

import logging
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy import select, update, and_, or_
from sqlalchemy.exc import IntegrityError

from ..database import get_async_session
from ..database.models import SessionBudget, UserBudget, BudgetAlert

logger = logging.getLogger(__name__)


class BudgetRepository:
    """
    Database-backed repository for budget management with persistence
    """
    
    async def create_session_budget(
        self,
        session_id: str,
        budget_limit: Decimal,
        alert_threshold: float = 0.8,
        reset_period: str = "session"
    ) -> Dict[str, Any]:
        """
        Create a new session budget
        
        Args:
            session_id: Session identifier
            budget_limit: Budget limit amount
            alert_threshold: Alert threshold (0.0 to 1.0)
            reset_period: Reset period ('session', 'daily', 'weekly', 'monthly')
            
        Returns:
            Dict with created budget information
        """
        try:
            async with get_async_session() as db:
                # Check if budget already exists
                existing = await db.execute(
                    select(SessionBudget).where(SessionBudget.session_id == session_id)
                )
                existing_budget = existing.scalar_one_or_none()
                
                if existing_budget:
                    # Update existing budget
                    existing_budget.budget_limit = str(budget_limit)
                    existing_budget.alert_threshold = alert_threshold
                    existing_budget.reset_period = reset_period
                    existing_budget.is_active = True
                    await db.commit()
                    await db.refresh(existing_budget)
                    
                    logger.info(f"Updated session budget: {session_id} = ${budget_limit}")
                    return existing_budget.to_dict()
                else:
                    # Create new budget
                    budget = SessionBudget(
                        session_id=session_id,
                        budget_limit=str(budget_limit),
                        alert_threshold=alert_threshold,
                        reset_period=reset_period
                    )
                    
                    db.add(budget)
                    await db.commit()
                    await db.refresh(budget)
                    
                    logger.info(f"Created session budget: {session_id} = ${budget_limit}")
                    return budget.to_dict()
                    
        except Exception as e:
            logger.error(f"Error creating session budget: {e}")
            raise
    
    async def create_user_budget(
        self,
        user_id: str,
        budget_limit: Decimal,
        reset_period: str = "monthly",
        alert_threshold: float = 0.8
    ) -> Dict[str, Any]:
        """
        Create a new user budget
        
        Args:
            user_id: User identifier
            budget_limit: Budget limit amount
            reset_period: Reset period ('daily', 'weekly', 'monthly')
            alert_threshold: Alert threshold (0.0 to 1.0)
            
        Returns:
            Dict with created budget information
        """
        try:
            async with get_async_session() as db:
                # Calculate period start and end
                now = datetime.now(timezone.utc)
                period_start, period_end = self._calculate_budget_period(now, reset_period)
                
                # Check if active budget already exists for this period
                existing = await db.execute(
                    select(UserBudget).where(
                        and_(
                            UserBudget.user_id == user_id,
                            UserBudget.reset_period == reset_period,
                            UserBudget.is_active == True
                        )
                    )
                )
                existing_budget = existing.scalar_one_or_none()
                
                if existing_budget:
                    # Update existing budget
                    existing_budget.budget_limit = str(budget_limit)
                    existing_budget.alert_threshold = alert_threshold
                    existing_budget.period_start = period_start
                    existing_budget.period_end = period_end
                    await db.commit()
                    await db.refresh(existing_budget)
                    
                    logger.info(f"Updated user budget: {user_id} = ${budget_limit} ({reset_period})")
                    return existing_budget.to_dict()
                else:
                    # Create new budget
                    budget = UserBudget(
                        user_id=user_id,
                        budget_limit=str(budget_limit),
                        period_start=period_start,
                        period_end=period_end,
                        reset_period=reset_period,
                        alert_threshold=alert_threshold
                    )
                    
                    db.add(budget)
                    await db.commit()
                    await db.refresh(budget)
                    
                    logger.info(f"Created user budget: {user_id} = ${budget_limit} ({reset_period})")
                    return budget.to_dict()
                    
        except Exception as e:
            logger.error(f"Error creating user budget: {e}")
            raise
    
    async def get_session_budget(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get active session budget"""
        try:
            async with get_async_session() as db:
                result = await db.execute(
                    select(SessionBudget).where(
                        and_(
                            SessionBudget.session_id == session_id,
                            SessionBudget.is_active == True
                        )
                    )
                )
                budget = result.scalar_one_or_none()
                return budget.to_dict() if budget else None
                
        except Exception as e:
            logger.error(f"Error getting session budget: {e}")
            return None
    
    async def get_user_budget(self, user_id: str, reset_period: str = "monthly") -> Optional[Dict[str, Any]]:
        """Get active user budget for current period"""
        try:
            async with get_async_session() as db:
                now = datetime.now(timezone.utc)
                
                result = await db.execute(
                    select(UserBudget).where(
                        and_(
                            UserBudget.user_id == user_id,
                            UserBudget.reset_period == reset_period,
                            UserBudget.is_active == True,
                            UserBudget.period_start <= now,
                            UserBudget.period_end >= now
                        )
                    )
                )
                budget = result.scalar_one_or_none()
                return budget.to_dict() if budget else None
                
        except Exception as e:
            logger.error(f"Error getting user budget: {e}")
            return None
    
    async def update_budget_spending(
        self,
        session_id: Optional[str],
        user_id: Optional[str],
        cost: Decimal
    ) -> Dict[str, Any]:
        """
        Update budget spending amounts
        
        Args:
            session_id: Session identifier (optional)
            user_id: User identifier (optional)
            cost: Cost to add to spending
            
        Returns:
            Dict with update results and alerts
        """
        alerts = []
        
        try:
            async with get_async_session() as db:
                # Update session budget
                if session_id:
                    session_result = await db.execute(
                        select(SessionBudget).where(
                            and_(
                                SessionBudget.session_id == session_id,
                                SessionBudget.is_active == True
                            )
                        )
                    )
                    session_budget = session_result.scalar_one_or_none()
                    
                    if session_budget:
                        old_spent = Decimal(session_budget.spent_amount)
                        new_spent = old_spent + cost
                        session_budget.spent_amount = str(new_spent)
                        
                        # Check for alerts
                        limit = Decimal(session_budget.budget_limit)
                        usage_percent = new_spent / limit
                        
                        if usage_percent >= session_budget.alert_threshold and old_spent / limit < session_budget.alert_threshold:
                            alert = await self._create_alert(
                                db, session_id=session_id, budget_type="session",
                                alert_type="threshold_exceeded", 
                                threshold_percent=session_budget.alert_threshold,
                                current_usage=str(new_spent), budget_limit=str(limit)
                            )
                            alerts.append(alert)
                        
                        if new_spent > limit and old_spent <= limit:
                            alert = await self._create_alert(
                                db, session_id=session_id, budget_type="session",
                                alert_type="budget_exceeded",
                                current_usage=str(new_spent), budget_limit=str(limit)
                            )
                            alerts.append(alert)
                
                # Update user budget
                if user_id:
                    now = datetime.now(timezone.utc)
                    user_result = await db.execute(
                        select(UserBudget).where(
                            and_(
                                UserBudget.user_id == user_id,
                                UserBudget.is_active == True,
                                UserBudget.period_start <= now,
                                UserBudget.period_end >= now
                            )
                        )
                    )
                    user_budget = user_result.scalar_one_or_none()
                    
                    if user_budget:
                        old_spent = Decimal(user_budget.spent_amount)
                        new_spent = old_spent + cost
                        user_budget.spent_amount = str(new_spent)
                        
                        # Check for alerts
                        limit = Decimal(user_budget.budget_limit)
                        usage_percent = new_spent / limit
                        
                        if usage_percent >= user_budget.alert_threshold and old_spent / limit < user_budget.alert_threshold:
                            alert = await self._create_alert(
                                db, user_id=user_id, budget_type="user",
                                alert_type="threshold_exceeded",
                                threshold_percent=user_budget.alert_threshold,
                                current_usage=str(new_spent), budget_limit=str(limit)
                            )
                            alerts.append(alert)
                        
                        if new_spent > limit and old_spent <= limit:
                            alert = await self._create_alert(
                                db, user_id=user_id, budget_type="user",
                                alert_type="budget_exceeded",
                                current_usage=str(new_spent), budget_limit=str(limit)
                            )
                            alerts.append(alert)
                
                await db.commit()
                
                return {
                    "success": True,
                    "cost_added": str(cost),
                    "alerts": alerts
                }
                
        except Exception as e:
            logger.error(f"Error updating budget spending: {e}")
            return {
                "success": False,
                "error": str(e),
                "alerts": []
            }
    
    async def check_budget_limits(
        self,
        session_id: Optional[str],
        user_id: Optional[str],
        estimated_cost: Decimal
    ) -> Dict[str, Any]:
        """
        Check if estimated cost would exceed budget limits
        
        Args:
            session_id: Session identifier (optional)
            user_id: User identifier (optional)
            estimated_cost: Estimated cost to check
            
        Returns:
            Dict with budget check results
        """
        checks = {
            "allowed": True,
            "warnings": [],
            "limits_exceeded": [],
            "remaining_budgets": {}
        }
        
        try:
            async with get_async_session() as db:
                # Check session budget
                if session_id:
                    session_result = await db.execute(
                        select(SessionBudget).where(
                            and_(
                                SessionBudget.session_id == session_id,
                                SessionBudget.is_active == True
                            )
                        )
                    )
                    session_budget = session_result.scalar_one_or_none()
                    
                    if session_budget:
                        spent = Decimal(session_budget.spent_amount)
                        limit = Decimal(session_budget.budget_limit)
                        new_spent = spent + estimated_cost
                        
                        if new_spent > limit:
                            checks["allowed"] = False
                            checks["limits_exceeded"].append({
                                "type": "session",
                                "limit": str(limit),
                                "would_spend": str(new_spent),
                                "session_id": session_id
                            })
                        else:
                            remaining = limit - new_spent
                            checks["remaining_budgets"]["session"] = str(remaining)
                            
                            # Warning at threshold
                            if new_spent > (limit * Decimal(str(session_budget.alert_threshold))):
                                checks["warnings"].append(
                                    f"Session budget {session_budget.alert_threshold:.0%} used: ${new_spent}/${limit}"
                                )
                
                # Check user budget
                if user_id:
                    now = datetime.now(timezone.utc)
                    user_result = await db.execute(
                        select(UserBudget).where(
                            and_(
                                UserBudget.user_id == user_id,
                                UserBudget.is_active == True,
                                UserBudget.period_start <= now,
                                UserBudget.period_end >= now
                            )
                        )
                    )
                    user_budget = user_result.scalar_one_or_none()
                    
                    if user_budget:
                        spent = Decimal(user_budget.spent_amount)
                        limit = Decimal(user_budget.budget_limit)
                        new_spent = spent + estimated_cost
                        
                        if new_spent > limit:
                            checks["allowed"] = False
                            checks["limits_exceeded"].append({
                                "type": "user",
                                "limit": str(limit),
                                "would_spend": str(new_spent),
                                "user_id": user_id
                            })
                        else:
                            remaining = limit - new_spent
                            checks["remaining_budgets"]["user"] = str(remaining)
                            
                            # Warning at threshold
                            if new_spent > (limit * Decimal(str(user_budget.alert_threshold))):
                                checks["warnings"].append(
                                    f"User budget {user_budget.alert_threshold:.0%} used: ${new_spent}/${limit}"
                                )
                
                return checks
                
        except Exception as e:
            logger.error(f"Error checking budget limits: {e}")
            return checks
    
    async def get_budget_status(
        self,
        session_id: Optional[str],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get current budget status"""
        status = {
            "session_id": session_id,
            "user_id": user_id,
            "budgets": {}
        }
        
        try:
            # Get session budget status
            if session_id:
                session_budget = await self.get_session_budget(session_id)
                if session_budget:
                    status["budgets"]["session"] = session_budget
            
            # Get user budget status
            if user_id:
                user_budget = await self.get_user_budget(user_id)
                if user_budget:
                    status["budgets"]["user"] = user_budget
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting budget status: {e}")
            return status
    
    async def reset_session_budget(self, session_id: str) -> bool:
        """Reset session budget spending"""
        try:
            async with get_async_session() as db:
                result = await db.execute(
                    update(SessionBudget)
                    .where(SessionBudget.session_id == session_id)
                    .values(spent_amount="0.00")
                )
                await db.commit()
                
                if result.rowcount > 0:
                    logger.info(f"Reset session budget: {session_id}")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Error resetting session budget: {e}")
            return False
    
    async def _create_alert(
        self,
        db,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        budget_type: str = "",
        alert_type: str = "",
        threshold_percent: Optional[float] = None,
        current_usage: str = "",
        budget_limit: str = ""
    ) -> Dict[str, Any]:
        """Create a budget alert"""
        try:
            alert = BudgetAlert(
                session_id=session_id,
                user_id=user_id,
                budget_type=budget_type,
                alert_type=alert_type,
                threshold_percent=threshold_percent,
                current_usage=current_usage,
                budget_limit=budget_limit,
                message=f"Budget {alert_type}: ${current_usage}/${budget_limit}"
            )
            
            db.add(alert)
            # Don't commit here - let the caller commit
            
            logger.warning(f"Budget alert created: {alert_type} for {budget_type} budget")
            return alert.to_dict()
            
        except Exception as e:
            logger.error(f"Error creating budget alert: {e}")
            return {}
    
    def _calculate_budget_period(self, current_time: datetime, reset_period: str) -> tuple[datetime, datetime]:
        """Calculate budget period start and end times"""
        if reset_period == "daily":
            start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif reset_period == "weekly":
            days_since_monday = current_time.weekday()
            start = current_time.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_monday)
            end = start + timedelta(weeks=1)
        elif reset_period == "monthly":
            start = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1)
            else:
                end = start.replace(month=start.month + 1)
        else:  # session or custom
            start = current_time
            end = current_time + timedelta(days=30)  # Default 30 day period
        
        return start, end


# Global budget repository instance
budget_repository = BudgetRepository()