"""
Integration modules for metrics with existing PyAirtable infrastructure.

This module provides integrations with Redis, rate limiting, circuit breakers,
and other existing components to collect relevant metrics.
"""
import asyncio
import time
from typing import Optional, Dict, Any, Callable
from functools import wraps

import redis.asyncio as redis
from redis.asyncio import Redis

from ..logging import get_logger
from ..utils.rate_limiter import RateLimiter, AirtableRateLimiter
from ..utils.retry import CircuitBreaker, RetryConfig
from .core import MetricsCollector, metrics_registry

logger = get_logger(__name__)


class RedisMetricsCollector:
    """Collect metrics from Redis operations."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self._setup_redis_metrics()
    
    def _setup_redis_metrics(self):
        """Setup Redis-specific metrics."""
        # Redis connection metrics are already defined in InfrastructureMetrics
        pass
    
    def record_redis_operation(self, operation: str, result: str, duration: float = None):
        """Record Redis operation metrics."""
        labels = metrics_registry.get_common_labels(
            operation=operation,
            result=result
        )
        self.metrics_collector.infra_metrics.redis_operations_total.labels(**labels).inc()
        
        if duration is not None:
            # We could add a Redis operation duration histogram if needed
            pass
    
    def update_connection_pool_size(self, pool_type: str, size: int):
        """Update Redis connection pool size."""
        labels = metrics_registry.get_common_labels(pool_type=pool_type)
        self.metrics_collector.infra_metrics.redis_connection_pool_size.labels(**labels).set(size)


class MetricsEnabledRedis:
    """Redis client wrapper that collects metrics."""
    
    def __init__(self, redis_client: Redis, metrics_collector: MetricsCollector):
        self.redis = redis_client
        self.metrics = RedisMetricsCollector(metrics_collector)
        self._wrap_redis_methods()
    
    def _wrap_redis_methods(self):
        """Wrap Redis methods to collect metrics."""
        # Common Redis methods to monitor
        methods_to_wrap = [
            'get', 'set', 'delete', 'exists', 'expire', 'ttl',
            'hget', 'hset', 'hgetall', 'hdel', 'hlen',
            'lpush', 'rpush', 'lpop', 'rpop', 'llen',
            'sadd', 'srem', 'smembers', 'scard',
            'zadd', 'zrem', 'zcard', 'zrange', 'zrangebyscore',
            'incr', 'decr', 'ping'
        ]
        
        for method_name in methods_to_wrap:
            if hasattr(self.redis, method_name):
                original_method = getattr(self.redis, method_name)
                wrapped_method = self._create_wrapped_method(method_name, original_method)
                setattr(self, method_name, wrapped_method)
    
    def _create_wrapped_method(self, method_name: str, original_method: Callable):
        """Create a wrapped method that collects metrics."""
        
        @wraps(original_method)
        async def wrapped(*args, **kwargs):
            start_time = time.time()
            try:
                result = await original_method(*args, **kwargs)
                duration = time.time() - start_time
                
                self.metrics.record_redis_operation(
                    operation=method_name,
                    result='success',
                    duration=duration
                )
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                self.metrics.record_redis_operation(
                    operation=method_name,
                    result='error',
                    duration=duration
                )
                raise
        
        return wrapped
    
    def __getattr__(self, name):
        """Delegate other attributes to the original Redis client."""
        return getattr(self.redis, name)


class MetricsEnabledRateLimiter:
    """Rate limiter wrapper that collects metrics."""
    
    def __init__(self, rate_limiter: RateLimiter, metrics_collector: MetricsCollector):
        self.rate_limiter = rate_limiter
        self.metrics_collector = metrics_collector
    
    async def is_allowed(self, identifier: str, limit: int, window_seconds: int, algorithm: str = "sliding_window") -> Dict[str, Any]:
        """Check rate limit and collect metrics."""
        start_time = time.time()
        
        try:
            result = await self.rate_limiter.is_allowed(identifier, limit, window_seconds, algorithm)
            
            # Record cache operation (rate limiting uses Redis)
            self.metrics_collector.record_cache_operation(
                operation='rate_limit_check',
                result='hit' if not result['allowed'] else 'miss'
            )
            
            # Record rate limit metrics if blocked
            if not result['allowed']:
                self.metrics_collector.record_rate_limit_hit(
                    base_id=identifier,  # This might need adjustment based on identifier format
                    limit_type=algorithm
                )
            
            return result
            
        except Exception as e:
            self.metrics_collector.record_cache_operation(
                operation='rate_limit_check',
                result='error'
            )
            raise
    
    async def reset(self, identifier: str):
        """Reset rate limit and record metric."""
        try:
            result = await self.rate_limiter.reset(identifier)
            self.metrics_collector.record_cache_operation(
                operation='rate_limit_reset',
                result='success'
            )
            return result
        except Exception as e:
            self.metrics_collector.record_cache_operation(
                operation='rate_limit_reset',
                result='error'
            )
            raise


class MetricsEnabledAirtableRateLimiter:
    """Airtable rate limiter wrapper that collects metrics."""
    
    def __init__(self, airtable_limiter: AirtableRateLimiter, metrics_collector: MetricsCollector):
        self.airtable_limiter = airtable_limiter
        self.metrics_collector = metrics_collector
    
    async def check_base_limit(self, base_id: str) -> Dict[str, Any]:
        """Check base rate limit and collect metrics."""
        result = await self.airtable_limiter.check_base_limit(base_id)
        
        if not result['allowed']:
            self.metrics_collector.record_rate_limit_hit(base_id, 'base')
        
        self.metrics_collector.update_rate_limit_remaining(
            base_id, 'base', result['remaining']
        )
        
        return result
    
    async def check_global_limit(self, api_key_hash: str) -> Dict[str, Any]:
        """Check global rate limit and collect metrics."""
        result = await self.airtable_limiter.check_global_limit(api_key_hash)
        
        if not result['allowed']:
            self.metrics_collector.record_rate_limit_hit('global', 'api')
        
        self.metrics_collector.update_rate_limit_remaining(
            'global', 'api', result['remaining']
        )
        
        return result
    
    async def check_service_limit(self, service_name: str) -> Dict[str, Any]:
        """Check service rate limit and collect metrics."""
        result = await self.airtable_limiter.check_service_limit(service_name)
        
        if not result['allowed']:
            self.metrics_collector.record_rate_limit_hit(service_name, 'service')
        
        self.metrics_collector.update_rate_limit_remaining(
            service_name, 'service', result['remaining']
        )
        
        return result


class MetricsEnabledCircuitBreaker:
    """Circuit breaker wrapper that collects metrics."""
    
    def __init__(self, circuit_breaker: CircuitBreaker, circuit_name: str, metrics_collector: MetricsCollector):
        self.circuit_breaker = circuit_breaker
        self.circuit_name = circuit_name
        self.metrics_collector = metrics_collector
        self._update_state_metric()
    
    def _update_state_metric(self):
        """Update circuit breaker state metric."""
        labels = metrics_registry.get_common_labels(circuit_name=self.circuit_name)
        self.metrics_collector.infra_metrics.circuit_breaker_state.labels(**labels).state(
            self.circuit_breaker.state
        )
    
    async def _call_with_circuit_breaker(self, func, *args, **kwargs):
        """Execute function with circuit breaker and metrics."""
        try:
            result = await self.circuit_breaker._call_with_circuit_breaker(func, *args, **kwargs)
            self._update_state_metric()
            return result
            
        except Exception as e:
            # Record failure
            labels = metrics_registry.get_common_labels(circuit_name=self.circuit_name)
            self.metrics_collector.infra_metrics.circuit_breaker_failures_total.labels(**labels).inc()
            
            self._update_state_metric()
            raise
    
    def __call__(self, func):
        """Decorator to apply circuit breaker with metrics."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self._call_with_circuit_breaker(func, *args, **kwargs)
        return wrapper
    
    def reset(self):
        """Reset circuit breaker and update metrics."""
        self.circuit_breaker.reset()
        self._update_state_metric()


class CacheMetrics:
    """Cache-specific metrics collector."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self._hit_count = 0
        self._miss_count = 0
    
    def record_hit(self):
        """Record cache hit."""
        self._hit_count += 1
        self.metrics_collector.record_cache_operation('get', 'hit')
        self._update_hit_ratio()
    
    def record_miss(self):
        """Record cache miss."""
        self._miss_count += 1
        self.metrics_collector.record_cache_operation('get', 'miss')
        self._update_hit_ratio()
    
    def record_set(self):
        """Record cache set operation."""
        self.metrics_collector.record_cache_operation('set', 'success')
    
    def record_delete(self):
        """Record cache delete operation."""
        self.metrics_collector.record_cache_operation('delete', 'success')
    
    def record_error(self, operation: str):
        """Record cache error."""
        self.metrics_collector.record_cache_operation(operation, 'error')
    
    def _update_hit_ratio(self):
        """Update cache hit ratio."""
        total = self._hit_count + self._miss_count
        if total > 0:
            ratio = self._hit_count / total
            self.metrics_collector.update_cache_hit_ratio(ratio)


def create_metrics_enabled_redis(redis_url: str, metrics_collector: MetricsCollector) -> MetricsEnabledRedis:
    """Create a metrics-enabled Redis client."""
    redis_client = redis.from_url(redis_url, decode_responses=True)
    return MetricsEnabledRedis(redis_client, metrics_collector)


def create_metrics_enabled_rate_limiter(redis_client: Redis, metrics_collector: MetricsCollector) -> MetricsEnabledRateLimiter:
    """Create a metrics-enabled rate limiter."""
    rate_limiter = RateLimiter(redis_client)
    return MetricsEnabledRateLimiter(rate_limiter, metrics_collector)


def create_metrics_enabled_airtable_limiter(redis_client: Redis, metrics_collector: MetricsCollector) -> MetricsEnabledAirtableRateLimiter:
    """Create a metrics-enabled Airtable rate limiter."""
    airtable_limiter = AirtableRateLimiter(redis_client)
    return MetricsEnabledAirtableRateLimiter(airtable_limiter, metrics_collector)


def create_metrics_enabled_circuit_breaker(
    circuit_name: str,
    metrics_collector: MetricsCollector,
    failure_threshold: int = 5,
    timeout: float = 60.0,
    expected_exception: type = Exception
) -> MetricsEnabledCircuitBreaker:
    """Create a metrics-enabled circuit breaker."""
    circuit_breaker = CircuitBreaker(failure_threshold, timeout, expected_exception)
    return MetricsEnabledCircuitBreaker(circuit_breaker, circuit_name, metrics_collector)