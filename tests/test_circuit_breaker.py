#!/usr/bin/env python3
"""
Test script for circuit breaker functionality
"""

import asyncio
import logging
import random
from typing import Dict, Any
from pyairtable_common.resilience import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def unreliable_service(failure_rate: float = 0.3) -> str:
    """
    Simulate an unreliable service that fails randomly
    
    Args:
        failure_rate: Probability of failure (0.0 to 1.0)
        
    Returns:
        Success message
        
    Raises:
        Exception: When service fails
    """
    # Simulate network delay
    await asyncio.sleep(random.uniform(0.1, 0.5))
    
    if random.random() < failure_rate:
        raise Exception("Service temporarily unavailable")
    
    return "Service call successful"


async def slow_service(slow_rate: float = 0.2) -> str:
    """
    Simulate a service that is sometimes slow
    
    Args:
        slow_rate: Probability of being slow (0.0 to 1.0)
        
    Returns:
        Success message
    """
    if random.random() < slow_rate:
        # Slow response (6 seconds)
        await asyncio.sleep(6.0)
    else:
        # Normal response
        await asyncio.sleep(0.1)
    
    return "Slow service call completed"


async def test_circuit_breaker_basic():
    """Test basic circuit breaker functionality"""
    logger.info("🧪 Testing basic circuit breaker functionality")
    
    config = CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout=5,
        response_timeout=30
    )
    
    breaker = CircuitBreaker("test-service", config)
    
    # Test successful calls
    logger.info("Testing successful calls...")
    for i in range(5):
        try:
            result = await breaker.call(unreliable_service, failure_rate=0.0)
            logger.info(f"✅ Call {i+1}: {result}")
        except Exception as e:
            logger.error(f"❌ Call {i+1} failed: {e}")
    
    # Test failing calls to trigger circuit opening
    logger.info("\nTesting failing calls...")
    for i in range(5):
        try:
            result = await breaker.call(unreliable_service, failure_rate=1.0)
            logger.info(f"✅ Call {i+1}: {result}")
        except CircuitBreakerException as e:
            logger.warning(f"🔴 Circuit breaker open on call {i+1}: {e}")
            break
        except Exception as e:
            logger.error(f"❌ Call {i+1} failed: {e}")
    
    # Show circuit breaker stats
    stats = breaker.get_stats()
    logger.info(f"\n📊 Circuit breaker stats:")
    logger.info(f"State: {stats['state']}")
    logger.info(f"Total requests: {stats['stats']['total_requests']}")
    logger.info(f"Success rate: {stats['stats']['success_rate']:.2%}")
    logger.info(f"Error rate: {stats['stats']['error_rate']:.2%}")
    logger.info(f"Consecutive failures: {stats['stats']['consecutive_failures']}")


async def test_circuit_breaker_recovery():
    """Test circuit breaker recovery after failures"""
    logger.info("\n🧪 Testing circuit breaker recovery")
    
    config = CircuitBreakerConfig(
        failure_threshold=2,
        success_threshold=2,
        timeout=2,  # Short timeout for testing
        response_timeout=30
    )
    
    breaker = CircuitBreaker("recovery-test", config)
    
    # Cause failures to open the circuit
    logger.info("Causing failures to open circuit...")
    for i in range(3):
        try:
            await breaker.call(unreliable_service, failure_rate=1.0)
        except Exception as e:
            logger.info(f"Expected failure {i+1}: {type(e).__name__}")
    
    # Wait for circuit to go to half-open
    logger.info("Waiting for circuit to go to half-open...")
    await asyncio.sleep(3)
    
    # Test recovery with successful calls
    logger.info("Testing recovery with successful calls...")
    for i in range(3):
        try:
            result = await breaker.call(unreliable_service, failure_rate=0.0)
            logger.info(f"✅ Recovery call {i+1}: Success")
        except CircuitBreakerException as e:
            logger.warning(f"🔴 Circuit still open on call {i+1}")
        except Exception as e:
            logger.error(f"❌ Recovery call {i+1} failed: {e}")
        
        # Small delay between recovery attempts
        await asyncio.sleep(0.5)
    
    # Final stats
    stats = breaker.get_stats()
    logger.info(f"\n📊 Final stats:")
    logger.info(f"State: {stats['state']}")
    logger.info(f"Success rate: {stats['stats']['success_rate']:.2%}")


async def test_slow_request_detection():
    """Test circuit breaker detection of slow requests"""
    logger.info("\n🧪 Testing slow request detection")
    
    config = CircuitBreakerConfig(
        failure_threshold=10,  # High threshold for failures
        success_threshold=3,
        timeout=10,
        response_timeout=30,
        slow_request_threshold=3000,  # 3 seconds
        slow_request_rate_threshold=0.5  # 50% slow requests
    )
    
    breaker = CircuitBreaker("slow-test", config)
    
    # Make calls with mix of slow and fast responses
    logger.info("Making calls with mixed response times...")
    for i in range(15):
        try:
            result = await breaker.call(slow_service, slow_rate=0.6)  # 60% slow
            logger.info(f"✅ Call {i+1}: Success")
        except CircuitBreakerException as e:
            logger.warning(f"🔴 Circuit opened due to slow requests on call {i+1}")
            break
        except Exception as e:
            logger.error(f"❌ Call {i+1} failed: {e}")
        
        await asyncio.sleep(0.1)  # Small delay between calls
    
    # Show stats
    stats = breaker.get_stats()
    logger.info(f"\n📊 Slow request stats:")
    logger.info(f"State: {stats['state']}")
    logger.info(f"Average response time: {stats['stats']['avg_response_time_ms']:.0f}ms")
    logger.info(f"Slow request rate: {stats['stats']['slow_request_rate']:.2%}")


async def test_concurrent_calls():
    """Test circuit breaker with concurrent calls"""
    logger.info("\n🧪 Testing concurrent calls")
    
    config = CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=3,
        timeout=5,
        response_timeout=30
    )
    
    breaker = CircuitBreaker("concurrent-test", config)
    
    async def make_call(call_id: int, failure_rate: float):
        try:
            result = await breaker.call(unreliable_service, failure_rate=failure_rate)
            logger.info(f"✅ Concurrent call {call_id}: Success")
            return True
        except CircuitBreakerException as e:
            logger.warning(f"🔴 Concurrent call {call_id}: Circuit open")
            return False
        except Exception as e:
            logger.error(f"❌ Concurrent call {call_id}: Failed")
            return False
    
    # Make concurrent calls with high failure rate
    logger.info("Making 10 concurrent calls with 70% failure rate...")
    tasks = [make_call(i, 0.7) for i in range(10)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = sum(1 for r in results if r is True)
    logger.info(f"Successful calls: {success_count}/10")
    
    # Show final stats
    stats = breaker.get_stats()
    logger.info(f"\n📊 Concurrent test stats:")
    logger.info(f"State: {stats['state']}")
    logger.info(f"Total requests: {stats['stats']['total_requests']}")
    logger.info(f"Success rate: {stats['stats']['success_rate']:.2%}")


async def main():
    """Run all circuit breaker tests"""
    logger.info("🚀 Starting circuit breaker tests\n")
    
    try:
        await test_circuit_breaker_basic()
        await test_circuit_breaker_recovery()
        await test_slow_request_detection()
        await test_concurrent_calls()
        
        logger.info("\n✅ All circuit breaker tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())