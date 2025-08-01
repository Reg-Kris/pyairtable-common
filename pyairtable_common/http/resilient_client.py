"""
Resilient HTTP client with circuit breaker protection
"""

import httpx
import asyncio
import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta

from ..resilience import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerException, circuit_breaker_registry

logger = logging.getLogger(__name__)


class ResilientHttpClient:
    """
    HTTP client with circuit breaker protection for inter-service communication
    
    Features:
    - Circuit breaker per service endpoint
    - Automatic retry with exponential backoff
    - Connection pooling
    - Request/response logging
    - Timeout management
    """
    
    def __init__(
        self,
        base_url: str,
        service_name: str,
        timeout: int = 30,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None
    ):
        self.base_url = base_url.rstrip('/')
        self.service_name = service_name
        self.circuit_breaker_config = circuit_breaker_config or CircuitBreakerConfig(
            failure_threshold=5,
            success_threshold=3,
            timeout=60,
            response_timeout=timeout
        )
        
        # Create HTTP client with connection pooling
        limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections
        )
        
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            limits=limits,
            headers={
                "User-Agent": f"PyAirtable-{service_name}/1.0",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        )
        
        logger.info(f"Created resilient HTTP client for {service_name} -> {base_url}")
    
    async def request(
        self,
        method: str,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        circuit_breaker_name: Optional[str] = None
    ) -> httpx.Response:
        """
        Make HTTP request with circuit breaker protection
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to base_url)
            json: JSON payload for request body
            params: Query parameters
            headers: Additional headers
            circuit_breaker_name: Custom circuit breaker name (defaults to endpoint)
            
        Returns:
            HTTP response
            
        Raises:
            CircuitBreakerException: If circuit breaker is open
            httpx.HTTPError: For HTTP-related errors
        """
        # Create circuit breaker name
        breaker_name = circuit_breaker_name or f"{self.service_name}-{endpoint.replace('/', '-')}"
        
        # Get or create circuit breaker for this endpoint
        breaker = await circuit_breaker_registry.get_breaker(breaker_name, self.circuit_breaker_config)
        
        # Prepare request
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        request_headers = self.client.headers.copy()
        if headers:
            request_headers.update(headers)
        
        # Add correlation ID if available
        correlation_id = getattr(asyncio.current_task(), 'correlation_id', None)
        if correlation_id:
            request_headers["X-Correlation-ID"] = correlation_id
        
        logger.debug(f"Making {method} request to {url}")
        
        async def make_request():
            """Actual HTTP request function"""
            response = await self.client.request(
                method=method,
                url=url,
                json=json,
                params=params,
                headers=request_headers
            )
            
            # Log response
            logger.debug(f"{method} {url} -> {response.status_code} ({len(response.content)} bytes)")
            
            # Raise for HTTP error status codes
            response.raise_for_status()
            
            return response
        
        # Execute request through circuit breaker
        try:
            return await breaker.call(make_request)
        
        except CircuitBreakerException as e:
            logger.error(f"Circuit breaker open for {self.service_name}: {e}")
            raise
        
        except httpx.TimeoutException as e:
            logger.warning(f"Request timeout for {method} {url}: {e}")
            raise
        
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error for {method} {url}: {e.response.status_code}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error for {method} {url}: {e}")
            raise
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> httpx.Response:
        """Convenience method for GET requests"""
        return await self.request("GET", endpoint, params=params, **kwargs)
    
    async def post(self, endpoint: str, json: Optional[Dict[str, Any]] = None, **kwargs) -> httpx.Response:
        """Convenience method for POST requests"""
        return await self.request("POST", endpoint, json=json, **kwargs)
    
    async def put(self, endpoint: str, json: Optional[Dict[str, Any]] = None, **kwargs) -> httpx.Response:
        """Convenience method for PUT requests"""
        return await self.request("PUT", endpoint, json=json, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> httpx.Response:
        """Convenience method for DELETE requests"""
        return await self.request("DELETE", endpoint, **kwargs)
    
    async def patch(self, endpoint: str, json: Optional[Dict[str, Any]] = None, **kwargs) -> httpx.Response:
        """Convenience method for PATCH requests"""
        return await self.request("PATCH", endpoint, json=json, **kwargs)
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check service health and circuit breaker status
        
        Returns:
            Dict with health status and circuit breaker stats
        """
        try:
            # Try a simple health check request
            response = await self.get("/health", circuit_breaker_name=f"{self.service_name}-health")
            
            # Get circuit breaker statistics
            stats = await circuit_breaker_registry.get_all_stats()
            service_breakers = {
                name: breaker_stats 
                for name, breaker_stats in stats["circuit_breakers"].items()
                if name.startswith(self.service_name)
            }
            
            return {
                "service": self.service_name,
                "base_url": self.base_url,
                "status": "healthy" if response.status_code == 200 else "degraded",
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "circuit_breakers": service_breakers,
                "checked_at": datetime.now().isoformat()
            }
            
        except CircuitBreakerException:
            return {
                "service": self.service_name,
                "base_url": self.base_url,
                "status": "circuit_open",
                "error": "Circuit breaker is open",
                "checked_at": datetime.now().isoformat()
            }
        
        except Exception as e:
            return {
                "service": self.service_name,
                "base_url": self.base_url,
                "status": "unhealthy",
                "error": str(e),
                "checked_at": datetime.now().isoformat()
            }
    
    async def close(self):
        """Close the HTTP client and clean up resources"""
        await self.client.aclose()
        logger.info(f"Closed HTTP client for {self.service_name}")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class ServiceRegistry:
    """
    Registry for managing resilient HTTP clients to different services
    """
    
    def __init__(self):
        self.clients: Dict[str, ResilientHttpClient] = {}
        self._lock = asyncio.Lock()
    
    async def get_client(
        self,
        service_name: str,
        base_url: str,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        **client_kwargs
    ) -> ResilientHttpClient:
        """
        Get or create a resilient HTTP client for a service
        
        Args:
            service_name: Name of the service
            base_url: Base URL for the service
            circuit_breaker_config: Circuit breaker configuration
            **client_kwargs: Additional arguments for ResilientHttpClient
            
        Returns:
            ResilientHttpClient instance
        """
        async with self._lock:
            if service_name not in self.clients:
                self.clients[service_name] = ResilientHttpClient(
                    base_url=base_url,
                    service_name=service_name,
                    circuit_breaker_config=circuit_breaker_config,
                    **client_kwargs
                )
                logger.info(f"Registered HTTP client for service: {service_name}")
            
            return self.clients[service_name]
    
    async def health_check_all(self) -> Dict[str, Any]:
        """
        Check health of all registered services
        
        Returns:
            Dict with health status for all services
        """
        health_checks = {}
        
        for service_name, client in self.clients.items():
            health_checks[service_name] = await client.health_check()
        
        # Overall status
        all_healthy = all(
            check.get("status") == "healthy" 
            for check in health_checks.values()
        )
        
        return {
            "overall_status": "healthy" if all_healthy else "degraded",
            "services": health_checks,
            "total_services": len(self.clients),
            "checked_at": datetime.now().isoformat()
        }
    
    async def close_all(self):
        """Close all HTTP clients"""
        for service_name, client in self.clients.items():
            await client.close()
        
        self.clients.clear()
        logger.info("Closed all HTTP clients")


# Global service registry
service_registry = ServiceRegistry()


# Convenience functions for common service clients
async def get_mcp_client(base_url: str = "http://mcp-server:8001") -> ResilientHttpClient:
    """Get resilient HTTP client for MCP server"""
    config = CircuitBreakerConfig(
        failure_threshold=3,  # Lower threshold for critical service
        success_threshold=2,
        timeout=30,
        response_timeout=10  # MCP calls should be fast
    )
    return await service_registry.get_client("mcp-server", base_url, config)


async def get_airtable_gateway_client(base_url: str = "http://airtable-gateway:8002") -> ResilientHttpClient:
    """Get resilient HTTP client for Airtable Gateway"""
    config = CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=3,
        timeout=60,
        response_timeout=30  # Airtable API can be slower
    )
    return await service_registry.get_client("airtable-gateway", base_url, config)


async def get_llm_orchestrator_client(base_url: str = "http://llm-orchestrator:8000") -> ResilientHttpClient:
    """Get resilient HTTP client for LLM Orchestrator"""
    config = CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout=120,  # LLM calls can take longer
        response_timeout=60
    )
    return await service_registry.get_client("llm-orchestrator", base_url, config)