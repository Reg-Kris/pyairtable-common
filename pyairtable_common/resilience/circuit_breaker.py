"""
Circuit breaker implementation to prevent cascading failures
"""

import asyncio
import time
import logging
from enum import Enum
from typing import Dict, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import statistics

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Circuit is open, blocking requests
    HALF_OPEN = "half_open" # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5          # Number of failures to trigger open state
    success_threshold: int = 3          # Number of successes to close circuit
    timeout: int = 60                   # Time in seconds to wait before trying half-open
    max_timeout: int = 300              # Maximum timeout (for exponential backoff)
    backoff_multiplier: float = 2.0     # Multiplier for exponential backoff
    response_timeout: int = 30          # Individual request timeout
    
    # Health check thresholds
    error_rate_threshold: float = 0.5   # 50% error rate threshold
    slow_request_threshold: int = 5000  # 5 seconds - requests slower than this are "slow"
    slow_request_rate_threshold: float = 0.3  # 30% slow request rate threshold


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker monitoring"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    response_times: list = field(default_factory=list)
    state_changes: list = field(default_factory=list)
    
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    def error_rate(self) -> float:
        """Calculate error rate"""
        return 1.0 - self.success_rate()
    
    def avg_response_time(self) -> float:
        """Calculate average response time"""
        if not self.response_times:
            return 0.0
        return statistics.mean(self.response_times[-100:])  # Last 100 requests
    
    def slow_request_rate(self, threshold_ms: int) -> float:
        """Calculate percentage of slow requests"""
        if not self.response_times:
            return 0.0
        slow_requests = sum(1 for rt in self.response_times[-100:] if rt > threshold_ms)
        return slow_requests / min(len(self.response_times), 100)


class CircuitBreakerException(Exception):
    """Exception raised when circuit breaker is open"""
    def __init__(self, message: str, state: CircuitBreakerState, stats: CircuitBreakerStats):
        self.state = state
        self.stats = stats
        super().__init__(message)


class CircuitBreaker:
    """
    Circuit breaker implementation for resilient service calls
    
    The circuit breaker has three states:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit is open, requests fail fast
    - HALF_OPEN: Testing if service has recovered
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitBreakerState.CLOSED
        self.stats = CircuitBreakerStats()
        self.last_state_change = datetime.now()
        self.current_timeout = self.config.timeout
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function call through the circuit breaker
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function call
            
        Raises:
            CircuitBreakerException: If circuit is open
        """
        async with self._lock:
            await self._check_state()
            
            if self.state == CircuitBreakerState.OPEN:
                raise CircuitBreakerException(
                    f"Circuit breaker '{self.name}' is OPEN. Service is unavailable.",
                    self.state,
                    self.stats
                )
        
        # Execute the function with timeout
        start_time = time.time()
        try:
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.response_timeout
                )
            else:
                result = func(*args, **kwargs)
            
            response_time_ms = int((time.time() - start_time) * 1000)
            await self._record_success(response_time_ms)
            return result
            
        except asyncio.TimeoutError:
            response_time_ms = int((time.time() - start_time) * 1000)
            await self._record_failure(f"Timeout after {response_time_ms}ms")
            raise
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            await self._record_failure(str(e))
            raise
    
    async def _check_state(self):
        """Check and update circuit breaker state"""
        now = datetime.now()
        time_since_last_change = (now - self.last_state_change).total_seconds()
        
        if self.state == CircuitBreakerState.OPEN:
            # Check if we should try half-open
            if time_since_last_change >= self.current_timeout:
                await self._change_state(CircuitBreakerState.HALF_OPEN)
                logger.info(f\"Circuit breaker '{self.name}' changed to HALF_OPEN\")\n        \n        elif self.state == CircuitBreakerState.HALF_OPEN:\n            # In half-open state, we're testing the service\n            pass\n        \n        elif self.state == CircuitBreakerState.CLOSED:\n            # Check if we should open due to health metrics\n            await self._check_health_metrics()\n    \n    async def _check_health_metrics(self):\n        \"\"\"Check if health metrics indicate we should open the circuit\"\"\"\n        if self.stats.total_requests < 10:  # Not enough data\n            return\n        \n        # Check consecutive failures\n        if self.stats.consecutive_failures >= self.config.failure_threshold:\n            await self._change_state(CircuitBreakerState.OPEN)\n            logger.warning(f\"Circuit breaker '{self.name}' OPENED due to consecutive failures: {self.stats.consecutive_failures}\")\n            return\n        \n        # Check error rate\n        if (self.stats.total_requests >= 20 and \n            self.stats.error_rate() >= self.config.error_rate_threshold):\n            await self._change_state(CircuitBreakerState.OPEN)\n            logger.warning(f\"Circuit breaker '{self.name}' OPENED due to high error rate: {self.stats.error_rate():.2%}\")\n            return\n        \n        # Check slow request rate\n        if (len(self.stats.response_times) >= 10 and\n            self.stats.slow_request_rate(self.config.slow_request_threshold) >= self.config.slow_request_rate_threshold):\n            await self._change_state(CircuitBreakerState.OPEN)\n            logger.warning(f\"Circuit breaker '{self.name}' OPENED due to slow requests: {self.stats.slow_request_rate(self.config.slow_request_threshold):.2%}\")\n    \n    async def _record_success(self, response_time_ms: int):\n        \"\"\"Record a successful request\"\"\"\n        async with self._lock:\n            self.stats.total_requests += 1\n            self.stats.successful_requests += 1\n            self.stats.consecutive_successes += 1\n            self.stats.consecutive_failures = 0\n            self.stats.last_success_time = datetime.now()\n            self.stats.response_times.append(response_time_ms)\n            \n            # Keep only last 1000 response times\n            if len(self.stats.response_times) > 1000:\n                self.stats.response_times = self.stats.response_times[-1000:]\n            \n            # Check if we should close the circuit (from half-open)\n            if (self.state == CircuitBreakerState.HALF_OPEN and \n                self.stats.consecutive_successes >= self.config.success_threshold):\n                await self._change_state(CircuitBreakerState.CLOSED)\n                logger.info(f\"Circuit breaker '{self.name}' CLOSED after successful recovery\")\n    \n    async def _record_failure(self, error: str):\n        \"\"\"Record a failed request\"\"\"\n        async with self._lock:\n            self.stats.total_requests += 1\n            self.stats.failed_requests += 1\n            self.stats.consecutive_failures += 1\n            self.stats.consecutive_successes = 0\n            self.stats.last_failure_time = datetime.now()\n            \n            logger.debug(f\"Circuit breaker '{self.name}' recorded failure: {error}\")\n            \n            # If we're in half-open and get a failure, go back to open\n            if self.state == CircuitBreakerState.HALF_OPEN:\n                await self._change_state(CircuitBreakerState.OPEN)\n                logger.warning(f\"Circuit breaker '{self.name}' returned to OPEN after failure in HALF_OPEN\")\n    \n    async def _change_state(self, new_state: CircuitBreakerState):\n        \"\"\"Change circuit breaker state\"\"\"\n        old_state = self.state\n        self.state = new_state\n        self.last_state_change = datetime.now()\n        \n        # Record state change\n        self.stats.state_changes.append({\n            \"from\": old_state.value,\n            \"to\": new_state.value,\n            \"timestamp\": self.last_state_change.isoformat(),\n            \"consecutive_failures\": self.stats.consecutive_failures,\n            \"error_rate\": self.stats.error_rate()\n        })\n        \n        # Keep only last 100 state changes\n        if len(self.stats.state_changes) > 100:\n            self.stats.state_changes = self.stats.state_changes[-100:]\n        \n        # Update timeout for exponential backoff\n        if new_state == CircuitBreakerState.OPEN:\n            self.current_timeout = min(\n                self.current_timeout * self.config.backoff_multiplier,\n                self.config.max_timeout\n            )\n        elif new_state == CircuitBreakerState.CLOSED:\n            self.current_timeout = self.config.timeout  # Reset timeout\n    \n    def get_stats(self) -> Dict[str, Any]:\n        \"\"\"Get circuit breaker statistics\"\"\"\n        return {\n            \"name\": self.name,\n            \"state\": self.state.value,\n            \"last_state_change\": self.last_state_change.isoformat(),\n            \"current_timeout\": self.current_timeout,\n            \"stats\": {\n                \"total_requests\": self.stats.total_requests,\n                \"successful_requests\": self.stats.successful_requests,\n                \"failed_requests\": self.stats.failed_requests,\n                \"success_rate\": self.stats.success_rate(),\n                \"error_rate\": self.stats.error_rate(),\n                \"consecutive_failures\": self.stats.consecutive_failures,\n                \"consecutive_successes\": self.stats.consecutive_successes,\n                \"avg_response_time_ms\": self.stats.avg_response_time(),\n                \"slow_request_rate\": self.stats.slow_request_rate(self.config.slow_request_threshold),\n                \"last_failure_time\": self.stats.last_failure_time.isoformat() if self.stats.last_failure_time else None,\n                \"last_success_time\": self.stats.last_success_time.isoformat() if self.stats.last_success_time else None\n            },\n            \"config\": {\n                \"failure_threshold\": self.config.failure_threshold,\n                \"success_threshold\": self.config.success_threshold,\n                \"timeout\": self.config.timeout,\n                \"max_timeout\": self.config.max_timeout,\n                \"error_rate_threshold\": self.config.error_rate_threshold,\n                \"slow_request_threshold\": self.config.slow_request_threshold\n            },\n            \"recent_state_changes\": self.stats.state_changes[-10:]  # Last 10 state changes\n        }\n    \n    async def reset(self):\n        \"\"\"Reset circuit breaker to closed state with clean stats\"\"\"\n        async with self._lock:\n            old_stats = self.get_stats()\n            self.state = CircuitBreakerState.CLOSED\n            self.stats = CircuitBreakerStats()\n            self.last_state_change = datetime.now()\n            self.current_timeout = self.config.timeout\n            \n            logger.info(f\"Circuit breaker '{self.name}' manually reset\")\n            return old_stats\n\n\nclass CircuitBreakerRegistry:\n    \"\"\"Registry for managing multiple circuit breakers\"\"\"\n    \n    def __init__(self):\n        self._breakers: Dict[str, CircuitBreaker] = {}\n        self._lock = asyncio.Lock()\n    \n    async def get_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:\n        \"\"\"Get or create a circuit breaker\"\"\"\n        async with self._lock:\n            if name not in self._breakers:\n                self._breakers[name] = CircuitBreaker(name, config)\n                logger.info(f\"Created circuit breaker: {name}\")\n            return self._breakers[name]\n    \n    async def get_all_stats(self) -> Dict[str, Any]:\n        \"\"\"Get statistics for all circuit breakers\"\"\"\n        stats = {}\n        for name, breaker in self._breakers.items():\n            stats[name] = breaker.get_stats()\n        return {\n            \"circuit_breakers\": stats,\n            \"total_breakers\": len(self._breakers),\n            \"generated_at\": datetime.now().isoformat()\n        }\n    \n    async def reset_all(self) -> Dict[str, Any]:\n        \"\"\"Reset all circuit breakers\"\"\"\n        results = {}\n        for name, breaker in self._breakers.items():\n            results[name] = await breaker.reset()\n        return results\n\n\n# Global circuit breaker registry\ncircuit_breaker_registry = CircuitBreakerRegistry()\n\n\ndef circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):\n    \"\"\"Decorator to add circuit breaker protection to a function\"\"\"\n    def decorator(func: Callable) -> Callable:\n        async def wrapper(*args, **kwargs):\n            breaker = await circuit_breaker_registry.get_breaker(name, config)\n            return await breaker.call(func, *args, **kwargs)\n        return wrapper\n    return decorator"