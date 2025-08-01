"""
Cost tracking and budgeting utilities for PyAirtable services with real token counting
"""

import os
from .gemini_cost_calculator import (
    GeminiCostCalculator,
    BudgetManager,
    GEMINI_PRICING
)

# Create global instances with real token counting enabled
cost_calculator = GeminiCostCalculator(api_key=os.getenv("GEMINI_API_KEY"))
budget_manager = BudgetManager()

__all__ = [
    "GeminiCostCalculator",
    "BudgetManager", 
    "cost_calculator",
    "budget_manager",
    "GEMINI_PRICING"
]