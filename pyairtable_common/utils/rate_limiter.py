"""
Rate limiting utilities using Redis for distributed rate limiting.
"""
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio

import redis.asyncio as redis
from redis.asyncio import Redis

from ..logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Redis-based distributed rate limiter with multiple algorithms."""
    
    def __init__(self, redis_client: Redis, prefix: str = "rate_limit"):
        self.redis = redis_client
        self.prefix = prefix
    
    def _make_key(self, identifier: str, window: str = "") -> str:
        """Generate rate limit key."""
        if window:
            return f"{self.prefix}:{identifier}:{window}"
        return f"{self.prefix}:{identifier}"
    
    async def is_allowed(
        self,
        identifier: str,
        limit: int,
        window_seconds: int,
        algorithm: str = "sliding_window"
    ) -> Dict[str, Any]:
        """
        Check if request is allowed under rate limit.
        
        Args:
            identifier: Unique identifier for the rate limit (user_id, api_key, etc.)
            limit: Maximum number of requests allowed
            window_seconds: Time window in seconds
            algorithm: Rate limiting algorithm ('sliding_window', 'fixed_window', 'token_bucket')
            
        Returns:
            Dict with allowed status, remaining requests, and reset time
        """
        
        if algorithm == "sliding_window":
            return await self._sliding_window(identifier, limit, window_seconds)
        elif algorithm == "fixed_window":
            return await self._fixed_window(identifier, limit, window_seconds)
        elif algorithm == "token_bucket":
            return await self._token_bucket(identifier, limit, window_seconds)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
    
    async def _sliding_window(self, identifier: str, limit: int, window_seconds: int) -> Dict[str, Any]:
        """Sliding window rate limiter using Redis sorted sets."""
        key = self._make_key(identifier, "sliding")
        now = time.time()
        window_start = now - window_seconds
        
        pipe = self.redis.pipeline()
        
        # Remove expired entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current requests
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(now): now})
        
        # Set expiration
        pipe.expire(key, window_seconds)
        
        results = await pipe.execute()
        current_requests = results[1]
        
        if current_requests >= limit:
            # Remove the request we just added since it's not allowed
            await self.redis.zrem(key, str(now))
            
            # Get the oldest request to calculate reset time
            oldest = await self.redis.zrange(key, 0, 0, withscores=True)
            reset_time = oldest[0][1] + window_seconds if oldest else now + window_seconds
            
            return {
                "allowed": False,
                "remaining": 0,
                "reset_time": reset_time,
                "retry_after": int(reset_time - now),
                "limit": limit,
                "window_seconds": window_seconds
            }
        
        remaining = limit - current_requests - 1
        reset_time = now + window_seconds
        
        return {
            "allowed": True,
            "remaining": remaining,
            "reset_time": reset_time,
            "retry_after": 0,
            "limit": limit,
            "window_seconds": window_seconds
        }
    
    async def _fixed_window(self, identifier: str, limit: int, window_seconds: int) -> Dict[str, Any]:
        """Fixed window rate limiter using Redis counters."""
        now = time.time()
        window_start = int(now // window_seconds) * window_seconds
        key = self._make_key(identifier, f"fixed:{window_start}")
        
        # Increment counter
        current = await self.redis.incr(key)
        
        # Set expiration on first request
        if current == 1:
            await self.redis.expire(key, window_seconds)
        
        if current > limit:
            reset_time = window_start + window_seconds
            return {
                "allowed": False,
                "remaining": 0,
                "reset_time": reset_time,
                "retry_after": int(reset_time - now),
                "limit": limit,
                "window_seconds": window_seconds
            }
        
        remaining = limit - current
        reset_time = window_start + window_seconds
        
        return {
            "allowed": True,
            "remaining": remaining,
            "reset_time": reset_time,
            "retry_after": 0,
            "limit": limit,
            "window_seconds": window_seconds
        }
    
    async def _token_bucket(self, identifier: str, limit: int, refill_period: int) -> Dict[str, Any]:
        """Token bucket rate limiter using Redis hash."""
        key = self._make_key(identifier, "bucket")
        now = time.time()
        
        # Get current state
        bucket_data = await self.redis.hmget(key, "tokens", "last_refill")
        
        if bucket_data[0] is None:
            # Initialize bucket
            tokens = limit - 1  # Take one token for current request
            last_refill = now
        else:
            tokens = float(bucket_data[0])
            last_refill = float(bucket_data[1])
            
            # Calculate tokens to add based on time elapsed
            time_elapsed = now - last_refill
            tokens_to_add = (time_elapsed / refill_period) * limit
            tokens = min(limit, tokens + tokens_to_add)
            
            # Try to consume one token
            if tokens >= 1:
                tokens -= 1
            else:
                # Not enough tokens
                return {
                    "allowed": False,
                    "remaining": 0,
                    "reset_time": now + (1 - tokens) * (refill_period / limit),
                    "retry_after": int((1 - tokens) * (refill_period / limit)),
                    "limit": limit,
                    "window_seconds": refill_period
                }
        
        # Update bucket state
        await self.redis.hset(key, mapping={
            "tokens": tokens,
            "last_refill": now
        })
        await self.redis.expire(key, refill_period * 2)  # Cleanup old buckets
        
        return {
            "allowed": True,
            "remaining": int(tokens),
            "reset_time": now + (limit - tokens) * (refill_period / limit),
            "retry_after": 0,
            "limit": limit,
            "window_seconds": refill_period
        }
    
    async def reset(self, identifier: str):
        """Reset rate limit for identifier."""
        keys = [
            self._make_key(identifier, "sliding"),
            self._make_key(identifier, "bucket")
        ]
        
        # Also clean up fixed window keys (they're harder to predict)
        pattern = self._make_key(identifier, "fixed:*")
        fixed_keys = await self.redis.keys(pattern)
        keys.extend(fixed_keys)
        
        if keys:
            deleted = await self.redis.delete(*keys)
            logger.info(f"Reset rate limit for {identifier}, deleted {deleted} keys")
            return deleted
        return 0


class AirtableRateLimiter:
    """Airtable-specific rate limiter respecting API limits."""
    
    def __init__(self, redis_client: Redis):
        self.limiter = RateLimiter(redis_client, "airtable")
    
    async def check_base_limit(self, base_id: str) -> Dict[str, Any]:
        """Check rate limit for specific Airtable base (5 QPS)."""
        return await self.limiter.is_allowed(
            identifier=f"base:{base_id}",
            limit=5,
            window_seconds=1,
            algorithm="sliding_window"
        )
    
    async def check_global_limit(self, api_key_hash: str) -> Dict[str, Any]:
        """Check global Airtable API limit per API key."""
        return await self.limiter.is_allowed(
            identifier=f"global:{api_key_hash}",
            limit=100,
            window_seconds=60,
            algorithm="sliding_window"
        )
    
    async def check_service_limit(self, service_name: str) -> Dict[str, Any]:
        """Check rate limit for internal service calls."""
        return await self.limiter.is_allowed(
            identifier=f"service:{service_name}",
            limit=50,
            window_seconds=1,
            algorithm="sliding_window"
        )


async def create_rate_limiter(redis_url: str) -> RateLimiter:
    """Create rate limiter with Redis connection."""
    redis_client = redis.from_url(redis_url, decode_responses=True)
    await redis_client.ping()
    return RateLimiter(redis_client)


async def create_airtable_rate_limiter(redis_url: str) -> AirtableRateLimiter:
    """Create Airtable-specific rate limiter."""
    redis_client = redis.from_url(redis_url, decode_responses=True)
    await redis_client.ping()
    return AirtableRateLimiter(redis_client)