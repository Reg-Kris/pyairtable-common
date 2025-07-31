"""
Retry utilities with exponential backoff and circuit breaker patterns.
"""
import asyncio
import random
import time
from typing import Any, Callable, Dict, List, Optional, Type, Union
from functools import wraps
from datetime import datetime, timedelta
import logging

from ..logging import get_logger
from ..exceptions import (
    PyAirtableError,
    RateLimitError,
    TimeoutError as PyAirtableTimeoutError,
    CircuitBreakerError,
    ExternalServiceError
)

logger = get_logger(__name__)


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        backoff_strategy: str = "exponential"
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.backoff_strategy = backoff_strategy
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        if self.backoff_strategy == "exponential":
            delay = self.base_delay * (self.exponential_base ** attempt)
        elif self.backoff_strategy == "linear":
            delay = self.base_delay * (attempt + 1)
        elif self.backoff_strategy == "fixed":
            delay = self.base_delay
        else:
            delay = self.base_delay
        
        # Apply max delay
        delay = min(delay, self.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay


class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open
    
    def __call__(self, func):
        """Decorator to apply circuit breaker to function."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self._call_with_circuit_breaker(func, *args, **kwargs)
        return wrapper
    
    async def _call_with_circuit_breaker(self, func, *args, **kwargs):
        """Execute function with circuit breaker logic."""
        
        # Check if circuit is open
        if self.state == "open":
            if self.last_failure_time and time.time() - self.last_failure_time >= self.timeout:
                self.state = "half-open"
                logger.info("Circuit breaker transitioning to half-open state")
            else:
                raise CircuitBreakerError(f"Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            
            # Success - reset circuit breaker
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
                logger.info("Circuit breaker reset to closed state")
            
            return result
            
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.warning(
                    f"Circuit breaker opened after {self.failure_count} failures",
                    timeout=self.timeout
                )
            
            raise e
    
    def reset(self):
        """Manually reset circuit breaker."""
        self.state = "closed"
        self.failure_count = 0
        self.last_failure_time = None
        logger.info("Circuit breaker manually reset")


class RetryableError(Exception):
    """Exception indicating that an operation should be retried."""
    pass


def should_retry(exception: Exception, retryable_exceptions: List[Type[Exception]]) -> bool:
    """Check if exception is retryable."""
    for exc_type in retryable_exceptions:
        if isinstance(exception, exc_type):
            return True
    return False


async def retry_async(
    func: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    retryable_exceptions: Optional[List[Type[Exception]]] = None,
    on_retry: Optional[Callable] = None,
    **kwargs
) -> Any:
    """
    Retry an async function with exponential backoff.
    
    Args:
        func: Async function to retry
        config: Retry configuration
        retryable_exceptions: List of exceptions that should trigger retries
        on_retry: Callback function called on each retry attempt
        *args, **kwargs: Arguments to pass to func
    
    Returns:
        Result of successful function call
        
    Raises:
        Last exception if all retries exhausted
    """
    
    if config is None:
        config = RetryConfig()
    
    if retryable_exceptions is None:
        retryable_exceptions = [
            RateLimitError,
            ExternalServiceError,
            RetryableError,
            ConnectionError,
            TimeoutError,
        ]
    
    last_exception = None
    
    for attempt in range(config.max_attempts):
        try:
            result = await func(*args, **kwargs)
            
            if attempt > 0:
                logger.info(
                    f"Function succeeded after {attempt + 1} attempts",
                    function=func.__name__,
                    total_attempts=attempt + 1
                )
            
            return result
            
        except Exception as e:
            last_exception = e
            
            # Check if we should retry
            if not should_retry(e, retryable_exceptions):
                logger.debug(
                    f"Exception not retryable: {type(e).__name__}",
                    function=func.__name__,
                    exception=str(e)
                )
                raise e
            
            # Check if we have more attempts
            if attempt >= config.max_attempts - 1:
                logger.error(
                    f"All retry attempts exhausted",
                    function=func.__name__,
                    attempts=config.max_attempts,
                    final_exception=str(e)
                )
                break
            
            # Calculate delay
            delay = config.calculate_delay(attempt)
            
            logger.warning(
                f"Retry attempt {attempt + 1}/{config.max_attempts}",
                function=func.__name__,
                delay=delay,
                exception=str(e)
            )
            
            # Call retry callback if provided
            if on_retry:
                await on_retry(attempt + 1, e, delay)
            
            # Wait before retry
            await asyncio.sleep(delay)
    
    # All retries exhausted
    raise last_exception


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    backoff_strategy: str = "exponential",
    retryable_exceptions: Optional[List[Type[Exception]]] = None,
    on_retry: Optional[Callable] = None
):
    """
    Decorator for retrying async functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter to delays
        backoff_strategy: Strategy for calculating delays ('exponential', 'linear', 'fixed')
        retryable_exceptions: List of exceptions that should trigger retries
        on_retry: Callback function called on each retry attempt
    
    Usage:
        @retry(max_attempts=5, base_delay=2.0)
        async def unreliable_function():
            # Function that might fail
            pass
    """
    
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        backoff_strategy=backoff_strategy
    )
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_async(
                func,
                *args,
                config=config,
                retryable_exceptions=retryable_exceptions,
                on_retry=on_retry,
                **kwargs
            )
        return wrapper
    
    return decorator


class AirtableRetryConfig(RetryConfig):
    """Airtable-specific retry configuration."""
    
    def __init__(self):
        super().__init__(
            max_attempts=3,
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=True,
            backoff_strategy="exponential"
        )


def airtable_retry(
    max_attempts: int = 3,
    on_retry: Optional[Callable] = None
):
    """
    Decorator specifically for Airtable API calls.
    
    Handles common Airtable errors like rate limiting and network issues.
    """
    
    retryable_exceptions = [
        RateLimitError,
        ExternalServiceError,
        RetryableError,
        ConnectionError,
        TimeoutError,
    ]
    
    return retry(
        max_attempts=max_attempts,
        base_delay=1.0,
        max_delay=30.0,
        exponential_base=2.0,
        jitter=True,
        retryable_exceptions=retryable_exceptions,
        on_retry=on_retry
    )


async def retry_with_circuit_breaker(
    func: Callable,
    *args,
    retry_config: Optional[RetryConfig] = None,
    circuit_breaker: Optional[CircuitBreaker] = None,
    **kwargs
) -> Any:
    """
    Combine retry logic with circuit breaker pattern.
    
    Args:
        func: Function to execute
        retry_config: Retry configuration
        circuit_breaker: Circuit breaker instance
        *args, **kwargs: Arguments to pass to func
    
    Returns:
        Result of successful function call
    """
    
    if circuit_breaker is None:
        circuit_breaker = CircuitBreaker()
    
    if retry_config is None:
        retry_config = RetryConfig()
    
    # Wrap function with circuit breaker
    protected_func = circuit_breaker(func)
    
    # Apply retry logic
    return await retry_async(
        protected_func,
        *args,
        config=retry_config,
        **kwargs
    )