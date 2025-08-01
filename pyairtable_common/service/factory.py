"""
Service factory patterns for creating PyAirtable services.
"""

import os
from typing import Optional, Dict, Any, List, Callable
from functools import partial

from .base import PyAirtableService
from .config import ServiceConfig


class ServiceFactory:
    """Factory for creating standardized PyAirtable services."""
    
    @staticmethod
    def create_api_gateway(
        title: str = "PyAirtable API Gateway",
        description: str = "Central entry point for PyAirtable microservices",
        version: str = "1.0.0",
        port: int = 8000,
        **kwargs
    ) -> PyAirtableService:
        """Create an API Gateway service."""
        config = ServiceConfig(
            title=title,
            description=description,
            version=version,
            service_name="api-gateway",
            port=port,
            rate_limit_calls=1000,  # Higher rate limit for gateway
            rate_limit_period=60,
            **kwargs
        )
        return PyAirtableService(config)
    
    @staticmethod
    def create_airtable_gateway(
        title: str = "Airtable Gateway",
        description: str = "REST API wrapper for Airtable operations",
        version: str = "1.0.0",
        port: int = 8002,
        **kwargs
    ) -> PyAirtableService:
        """Create an Airtable Gateway service."""
        config = ServiceConfig(
            title=title,
            description=description,
            version=version,
            service_name="airtable-gateway",
            port=port,
            rate_limit_calls=300,  # Moderate rate limit for Airtable operations
            rate_limit_period=60,
            **kwargs
        )
        return PyAirtableService(config)
    
    @staticmethod
    def create_mcp_server(
        title: str = "MCP Server HTTP API",
        description: str = "HTTP API for MCP tools",
        version: str = "1.0.0",
        port: int = 8001,
        **kwargs
    ) -> PyAirtableService:
        """Create an MCP Server service."""
        config = ServiceConfig(
            title=title,
            description=description,
            version=version,
            service_name="mcp-server",
            port=port,
            cors_methods=["GET", "POST", "OPTIONS"],  # Limited methods for MCP
            **kwargs
        )
        return PyAirtableService(config)
    
    @staticmethod
    def create_llm_orchestrator(
        title: str = "LLM Orchestrator",
        description: str = "Gemini integration with MCP tools",
        version: str = "2.0.0",
        port: int = 8003,
        **kwargs
    ) -> PyAirtableService:
        """Create an LLM Orchestrator service."""
        config = ServiceConfig(
            title=title,
            description=description,
            version=version,
            service_name="llm-orchestrator",
            port=port,
            rate_limit_calls=60,  # Lower rate limit for LLM operations
            rate_limit_period=60,
            **kwargs
        )
        return PyAirtableService(config)
    
    @staticmethod
    def create_custom_service(
        title: str,
        description: str,
        service_name: str,
        version: str = "1.0.0",
        port: int = 8000,
        **kwargs
    ) -> PyAirtableService:
        """Create a custom service with specified configuration."""
        config = ServiceConfig(
            title=title,
            description=description,
            version=version,
            service_name=service_name,
            port=port,
            **kwargs
        )
        return PyAirtableService(config)


def create_service(
    service_type: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    version: Optional[str] = None,
    port: Optional[int] = None,
    api_key: Optional[str] = None,
    startup_tasks: Optional[List[Callable]] = None,
    shutdown_tasks: Optional[List[Callable]] = None,
    **kwargs
) -> PyAirtableService:
    """
    Factory function to create services by type.
    
    Args:
        service_type: Type of service ('api-gateway', 'airtable-gateway', 'mcp-server', 'llm-orchestrator', 'custom')
        title: Service title (optional, uses defaults if not provided)
        description: Service description (optional, uses defaults if not provided)
        version: Service version (optional, uses defaults if not provided)
        port: Service port (optional, uses defaults if not provided)
        api_key: API key for security (optional, reads from environment)
        startup_tasks: List of startup tasks (optional)
        shutdown_tasks: List of shutdown tasks (optional)
        **kwargs: Additional configuration options
    
    Returns:
        PyAirtableService: Configured service instance
    
    Raises:
        ValueError: If service_type is not supported
    """
    
    # Get API key from environment if not provided
    if api_key is None:
        api_key = os.getenv("API_KEY")
    
    # Add common configuration
    common_config = {
        "api_key": api_key,
        "startup_tasks": startup_tasks or [],
        "shutdown_tasks": shutdown_tasks or [],
        **kwargs
    }
    
    # Create service based on type
    if service_type == "api-gateway":
        factory_method = ServiceFactory.create_api_gateway
    elif service_type == "airtable-gateway":
        factory_method = ServiceFactory.create_airtable_gateway
    elif service_type == "mcp-server":
        factory_method = ServiceFactory.create_mcp_server
    elif service_type == "llm-orchestrator":
        factory_method = ServiceFactory.create_llm_orchestrator
    elif service_type == "custom":
        if not title or not description:
            raise ValueError("Custom services require both title and description")
        factory_method = partial(
            ServiceFactory.create_custom_service,
            service_name=kwargs.get("service_name", "custom-service")
        )
    else:
        raise ValueError(f"Unsupported service type: {service_type}")
    
    # Build arguments
    factory_args = {}
    if title is not None:
        factory_args["title"] = title
    if description is not None:
        factory_args["description"] = description
    if version is not None:
        factory_args["version"] = version
    if port is not None:
        factory_args["port"] = port
    
    factory_args.update(common_config)
    
    return factory_method(**factory_args)