"""
Gemini API cost tracking and calculation utilities with real token counting
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Optional, Union, List
from datetime import datetime, timezone
import logging
import asyncio
import os

# Import Gemini SDK for real token counting
try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    GEMINI_SDK_AVAILABLE = True
except ImportError:
    GEMINI_SDK_AVAILABLE = False

logger = logging.getLogger(__name__)

# Gemini 2.5 Flash pricing (as of 2025-01-01)
# Prices are per 1K tokens
GEMINI_PRICING = {
    "gemini-2.5-flash": {
        "input_tokens": Decimal("0.000075"),   # $0.000075 per 1K input tokens
        "output_tokens": Decimal("0.0003"),    # $0.0003 per 1K output tokens
        "thinking_tokens": Decimal("0.000075"), # Same as input tokens for thinking
    },
    "gemini-2.5-pro": {
        "input_tokens": Decimal("0.00125"),    # $0.00125 per 1K input tokens  
        "output_tokens": Decimal("0.005"),     # $0.005 per 1K output tokens
        "thinking_tokens": Decimal("0.00125"), # Same as input tokens for thinking
    },
    "gemini-1.5-flash": {
        "input_tokens": Decimal("0.000075"),   # $0.000075 per 1K input tokens
        "output_tokens": Decimal("0.0003"),    # $0.0003 per 1K output tokens
        "thinking_tokens": Decimal("0.000075"), # Same as input tokens for thinking
    },
    "gemini-1.5-pro": {
        "input_tokens": Decimal("0.00125"),    # $0.00125 per 1K input tokens
        "output_tokens": Decimal("0.005"),     # $0.005 per 1K output tokens
        "thinking_tokens": Decimal("0.00125"), # Same as input tokens for thinking
    }
}

# Default model for fallback
DEFAULT_MODEL = "gemini-2.5-flash"


class GeminiCostCalculator:
    """
    Calculate costs for Gemini API usage with real token counting and pricing
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the cost calculator with optional API key for real token counting
        
        Args:
            api_key: Gemini API key for real token counting (optional)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._client = None
        
        if GEMINI_SDK_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel("gemini-2.5-flash")
                logger.info("✅ Real token counting enabled with Gemini SDK")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Gemini SDK: {e}")
                self._client = None
        else:
            logger.warning("⚠️ Real token counting unavailable - using estimates")
    
    async def count_tokens_real(
        self, 
        model_name: str,
        input_text: str,
        output_text: str = "",
        thinking_text: str = ""
    ) -> Dict[str, int]:
        """
        Count tokens using official Gemini SDK for accurate counting
        
        Args:
            model_name: Gemini model name
            input_text: Input text content
            output_text: Output text content (optional)
            thinking_text: Thinking process text (optional)
            
        Returns:
            Dict with accurate token counts
        """
        if not self._client or not GEMINI_SDK_AVAILABLE:
            logger.warning("Real token counting unavailable, falling back to estimates")
            return {
                "input_tokens": self.estimate_token_count(input_text),
                "output_tokens": self.estimate_token_count(output_text),
                "thinking_tokens": self.estimate_token_count(thinking_text),
                "method": "estimated"
            }
        
        try:
            # Count input tokens
            input_tokens = 0
            if input_text:
                input_response = await asyncio.to_thread(
                    self._client.count_tokens, input_text
                )
                input_tokens = input_response.total_tokens
            
            # Count output tokens
            output_tokens = 0
            if output_text:
                output_response = await asyncio.to_thread(
                    self._client.count_tokens, output_text
                )
                output_tokens = output_response.total_tokens
            
            # Count thinking tokens
            thinking_tokens = 0
            if thinking_text:
                thinking_response = await asyncio.to_thread(
                    self._client.count_tokens, thinking_text
                )
                thinking_tokens = thinking_response.total_tokens
            
            logger.debug(f"Real token count: input={input_tokens}, output={output_tokens}, thinking={thinking_tokens}")
            
            return {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "thinking_tokens": thinking_tokens,
                "method": "real_api"
            }
            
        except Exception as e:
            logger.error(f"Error counting tokens with Gemini SDK: {e}")
            # Fallback to estimation
            return {
                "input_tokens": self.estimate_token_count(input_text),
                "output_tokens": self.estimate_token_count(output_text),
                "thinking_tokens": self.estimate_token_count(thinking_text),
                "method": "estimated_fallback"
            }
    
    def count_tokens_sync(
        self,
        model_name: str,
        input_text: str,
        output_text: str = "",
        thinking_text: str = ""
    ) -> Dict[str, int]:
        """
        Synchronous version of real token counting
        
        Args:
            model_name: Gemini model name
            input_text: Input text content
            output_text: Output text content (optional)
            thinking_text: Thinking process text (optional)
            
        Returns:
            Dict with accurate token counts
        """
        if not self._client or not GEMINI_SDK_AVAILABLE:
            return {
                "input_tokens": self.estimate_token_count(input_text),
                "output_tokens": self.estimate_token_count(output_text),
                "thinking_tokens": self.estimate_token_count(thinking_text),
                "method": "estimated"
            }
        
        try:
            # Count input tokens
            input_tokens = 0
            if input_text:
                input_response = self._client.count_tokens(input_text)
                input_tokens = input_response.total_tokens
            
            # Count output tokens
            output_tokens = 0
            if output_text:
                output_response = self._client.count_tokens(output_text)
                output_tokens = output_response.total_tokens
            
            # Count thinking tokens
            thinking_tokens = 0
            if thinking_text:
                thinking_response = self._client.count_tokens(thinking_text)
                thinking_tokens = thinking_response.total_tokens
            
            return {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "thinking_tokens": thinking_tokens,
                "method": "real_sync"
            }
            
        except Exception as e:
            logger.error(f"Error counting tokens with Gemini SDK: {e}")
            return {
                "input_tokens": self.estimate_token_count(input_text),
                "output_tokens": self.estimate_token_count(output_text),
                "thinking_tokens": self.estimate_token_count(thinking_text),
                "method": "estimated_fallback"
            }
    
    @staticmethod
    def estimate_token_count(text: str) -> int:
        """
        Estimate token count for text (rough approximation - fallback only)
        
        Args:
            text: Input text
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        
        # Rough estimation: ~0.75 tokens per word for English text
        # This is a conservative estimate; actual tokenization may vary
        words = len(text.split())
        return int(words * 0.75)
    
    @staticmethod
    def calculate_cost(
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        thinking_tokens: int = 0
    ) -> Dict[str, Any]:
        """
        Calculate cost for Gemini API usage
        
        Args:
            model_name: Name of the Gemini model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            thinking_tokens: Number of thinking tokens (for reasoning)
            
        Returns:
            Dict with cost breakdown and total
        """
        # Get pricing for the model (fallback to default if not found)
        pricing = GEMINI_PRICING.get(model_name, GEMINI_PRICING[DEFAULT_MODEL])
        
        if model_name not in GEMINI_PRICING:
            logger.warning(f"Unknown model {model_name}, using {DEFAULT_MODEL} pricing")
        
        # Calculate costs (prices are per 1K tokens)
        input_cost = (Decimal(input_tokens) / 1000) * pricing["input_tokens"]
        output_cost = (Decimal(output_tokens) / 1000) * pricing["output_tokens"]
        thinking_cost = (Decimal(thinking_tokens) / 1000) * pricing["thinking_tokens"]
        
        total_cost = input_cost + output_cost + thinking_cost
        total_tokens = input_tokens + output_tokens + thinking_tokens
        
        # Round to 6 decimal places for precision
        return {
            "model_name": model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "thinking_tokens": thinking_tokens,
            "total_tokens": total_tokens,
            "input_cost": str(input_cost.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)),
            "output_cost": str(output_cost.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)),
            "thinking_cost": str(thinking_cost.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)),
            "total_cost": str(total_cost.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)),
            "calculated_at": datetime.now(timezone.utc).isoformat(),
            "pricing_used": {
                "input_per_1k": str(pricing["input_tokens"]),
                "output_per_1k": str(pricing["output_tokens"]),
                "thinking_per_1k": str(pricing["thinking_tokens"])
            }
        }
    
    async def calculate_cost_from_text_real(
        self,
        model_name: str,
        input_text: str,
        output_text: str,
        thinking_text: str = ""
    ) -> Dict[str, Any]:
        """
        Calculate cost from text content using real token counting
        
        Args:
            model_name: Name of the Gemini model used
            input_text: Input text content
            output_text: Output text content
            thinking_text: Thinking process text (if available)
            
        Returns:
            Dict with accurate cost breakdown
        """
        # Get real token counts
        token_counts = await self.count_tokens_real(
            model_name, input_text, output_text, thinking_text
        )
        
        # Calculate cost using real token counts
        cost_data = self.calculate_cost(
            model_name, 
            token_counts["input_tokens"], 
            token_counts["output_tokens"], 
            token_counts["thinking_tokens"]
        )
        
        # Add token counting method info
        cost_data["token_counting_method"] = token_counts["method"]
        cost_data["estimated"] = token_counts["method"].startswith("estimated")
        
        return cost_data
    
    def calculate_cost_from_text_sync(
        self,
        model_name: str,
        input_text: str,
        output_text: str,
        thinking_text: str = ""
    ) -> Dict[str, Any]:
        """
        Calculate cost from text content using real token counting (synchronous)
        
        Args:
            model_name: Name of the Gemini model used
            input_text: Input text content
            output_text: Output text content
            thinking_text: Thinking process text (if available)
            
        Returns:
            Dict with accurate cost breakdown
        """
        # Get real token counts
        token_counts = self.count_tokens_sync(
            model_name, input_text, output_text, thinking_text
        )
        
        # Calculate cost using real token counts
        cost_data = self.calculate_cost(
            model_name, 
            token_counts["input_tokens"], 
            token_counts["output_tokens"], 
            token_counts["thinking_tokens"]
        )
        
        # Add token counting method info
        cost_data["token_counting_method"] = token_counts["method"]
        cost_data["estimated"] = token_counts["method"].startswith("estimated")
        
        return cost_data
    
    @staticmethod
    def estimate_cost_from_text(
        model_name: str,
        input_text: str,
        output_text: str,
        thinking_text: str = ""
    ) -> Dict[str, Any]:
        """
        Estimate cost from text content (fallback method)
        
        Args:
            model_name: Name of the Gemini model used
            input_text: Input text content
            output_text: Output text content
            thinking_text: Thinking process text (if available)
            
        Returns:
            Dict with estimated cost breakdown
        """
        input_tokens = GeminiCostCalculator.estimate_token_count(input_text)
        output_tokens = GeminiCostCalculator.estimate_token_count(output_text)
        thinking_tokens = GeminiCostCalculator.estimate_token_count(thinking_text) if thinking_text else 0
        
        cost_data = GeminiCostCalculator.calculate_cost(
            model_name, input_tokens, output_tokens, thinking_tokens
        )
        
        # Add estimation flag
        cost_data["estimated"] = True
        cost_data["token_counting_method"] = "word_count_approximation"
        
        return cost_data


class BudgetManager:
    """
    Manage budgets and limits for API usage with database persistence
    """
    
    def __init__(self, use_database: bool = True):
        self.use_database = use_database
        self.repository = None
        
        if use_database:
            try:
                from .budget_repository import budget_repository
                self.repository = budget_repository
                logger.info("✅ Database-backed budget management enabled")
            except ImportError as e:
                logger.warning(f"⚠️ Database budget repository not available: {e}")
                self.use_database = False
        
        # Fallback in-memory storage
        if not self.use_database:
            self.session_budgets: Dict[str, Dict[str, Any]] = {}
            self.user_budgets: Dict[str, Dict[str, Any]] = {}
            logger.info("Using in-memory budget management")
        
        self.global_limits = {
            "daily_limit": Decimal("100.00"),    # $100 daily limit
            "session_limit": Decimal("10.00"),   # $10 per session limit
            "user_limit": Decimal("50.00")       # $50 per user daily limit
        }
    
    async def set_session_budget(self, session_id: str, budget_limit: Decimal):
        """Set budget limit for a specific session"""
        if self.use_database and self.repository:
            return await self.repository.create_session_budget(session_id, budget_limit)
        else:
            # Fallback to in-memory
            self.session_budgets[session_id] = {
                "limit": budget_limit,
                "spent": Decimal("0.00"),
                "created_at": datetime.now(timezone.utc)
            }
            logger.info(f"Set session budget (in-memory): {session_id} = ${budget_limit}")
            return self.session_budgets[session_id]
    
    async def set_user_budget(self, user_id: str, budget_limit: Decimal, reset_period: str = "monthly"):
        """Set budget limit for a specific user"""
        if self.use_database and self.repository:
            return await self.repository.create_user_budget(user_id, budget_limit, reset_period)
        else:
            # Fallback to in-memory
            self.user_budgets[user_id] = {
                "limit": budget_limit,
                "spent": Decimal("0.00"),
                "created_at": datetime.now(timezone.utc),
                "reset_period": reset_period
            }
            logger.info(f"Set user budget (in-memory): {user_id} = ${budget_limit}")
            return self.user_budgets[user_id]
    
    async def check_budget_limits(self, session_id: str, user_id: Optional[str], cost: Decimal) -> Dict[str, Any]:
        """
        Check if the cost would exceed budget limits
        
        Args:
            session_id: Session identifier
            user_id: User identifier (optional)
            cost: Cost to check against budgets
            
        Returns:
            Dict with budget check results
        """
        if self.use_database and self.repository:
            return await self.repository.check_budget_limits(session_id, user_id, cost)
        else:
            # Fallback to in-memory checking
            checks = {
                "allowed": True,
                "warnings": [],
                "limits_exceeded": [],
                "remaining_budgets": {}
            }
            
            # Check session budget
            if session_id in self.session_budgets:
                session_budget = self.session_budgets[session_id]
                new_spent = session_budget["spent"] + cost
                
                if new_spent > session_budget["limit"]:
                    checks["allowed"] = False
                    checks["limits_exceeded"].append({
                        "type": "session",
                        "limit": str(session_budget["limit"]),
                        "would_spend": str(new_spent),
                        "session_id": session_id
                    })
                else:
                    remaining = session_budget["limit"] - new_spent
                    checks["remaining_budgets"]["session"] = str(remaining)
                    
                    # Warning at 80% of budget
                    if new_spent > (session_budget["limit"] * Decimal("0.8")):
                        checks["warnings"].append(f"Session budget 80% used: ${new_spent}/${session_budget['limit']}")
            
            # Check user budget
            if user_id and user_id in self.user_budgets:
                user_budget = self.user_budgets[user_id]
                new_spent = user_budget["spent"] + cost
                
                if new_spent > user_budget["limit"]:
                    checks["allowed"] = False
                    checks["limits_exceeded"].append({
                        "type": "user",
                        "limit": str(user_budget["limit"]),
                        "would_spend": str(new_spent),
                        "user_id": user_id
                    })
                else:
                    remaining = user_budget["limit"] - new_spent
                    checks["remaining_budgets"]["user"] = str(remaining)
                    
                    # Warning at 80% of budget
                    if new_spent > (user_budget["limit"] * Decimal("0.8")):
                        checks["warnings"].append(f"User budget 80% used: ${new_spent}/${user_budget['limit']}")
            
            return checks
    
    async def record_usage(self, session_id: str, user_id: Optional[str], cost: Decimal):
        """
        Record API usage against budgets
        
        Args:
            session_id: Session identifier
            user_id: User identifier (optional)
            cost: Cost to record
        """
        if self.use_database and self.repository:
            return await self.repository.update_budget_spending(session_id, user_id, cost)
        else:
            # Fallback to in-memory recording
            # Record session usage
            if session_id in self.session_budgets:
                self.session_budgets[session_id]["spent"] += cost
                logger.debug(f"Recorded session usage (in-memory): {session_id} += ${cost}")
            
            # Record user usage
            if user_id and user_id in self.user_budgets:
                self.user_budgets[user_id]["spent"] += cost
                logger.debug(f"Recorded user usage (in-memory): {user_id} += ${cost}")
            
            return {"success": True, "cost_added": str(cost), "alerts": []}
    
    async def get_budget_status(self, session_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current budget status
        
        Args:
            session_id: Session identifier
            user_id: User identifier (optional)
            
        Returns:
            Dict with budget status information
        """
        if self.use_database and self.repository:
            return await self.repository.get_budget_status(session_id, user_id)
        else:
            # Fallback to in-memory status
            status = {
                "session_id": session_id,
                "user_id": user_id,
                "budgets": {}
            }
            
            # Session budget status
            if session_id in self.session_budgets:
                session_budget = self.session_budgets[session_id]
                remaining = session_budget["limit"] - session_budget["spent"]
                usage_percent = (session_budget["spent"] / session_budget["limit"]) * 100
                
                status["budgets"]["session"] = {
                    "limit": str(session_budget["limit"]),
                    "spent": str(session_budget["spent"]),
                    "remaining": str(remaining),
                    "usage_percent": float(usage_percent.quantize(Decimal('0.01'))),
                    "created_at": session_budget["created_at"].isoformat()
                }
            
            # User budget status
            if user_id and user_id in self.user_budgets:
                user_budget = self.user_budgets[user_id]
                remaining = user_budget["limit"] - user_budget["spent"]
                usage_percent = (user_budget["spent"] / user_budget["limit"]) * 100
                
                status["budgets"]["user"] = {
                    "limit": str(user_budget["limit"]),
                    "spent": str(user_budget["spent"]),
                    "remaining": str(remaining),
                    "usage_percent": float(usage_percent.quantize(Decimal('0.01'))),
                    "created_at": user_budget["created_at"].isoformat()
                }
            
            return status
    
    async def reset_session_budget(self, session_id: str):
        """Reset session budget (clear spending)"""
        if self.use_database and self.repository:
            return await self.repository.reset_session_budget(session_id)
        else:
            # Fallback to in-memory reset
            if session_id in self.session_budgets:
                self.session_budgets[session_id]["spent"] = Decimal("0.00")
                logger.info(f"Reset session budget (in-memory): {session_id}")
                return True
            return False
    
    async def reset_user_budget(self, user_id: str):
        """Reset user budget (clear spending)"""
        if self.use_database and self.repository:
            # For database, we don't reset user budgets - they have time periods
            logger.warning("User budget reset not supported with database backend - budgets have time periods")
            return False
        else:
            # Fallback to in-memory reset
            if user_id in self.user_budgets:
                self.user_budgets[user_id]["spent"] = Decimal("0.00")
                logger.info(f"Reset user budget (in-memory): {user_id}")
                return True
            return False


# Global budget manager instance
budget_manager = BudgetManager()