"""
Base service class for PyAirtable microservices.
"""

import logging
import os
from typing import Optional, List, Dict, Any, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import middleware and utilities
from ..middleware.setup import setup_middleware
from ..middleware.security import (
    SecurityHeadersMiddleware, 
    RateLimitMiddleware, 
    verify_api_key_secure
)
from ..logging.setup import setup_logging
from ..config.settings import get_service_settings
from .config import ServiceConfig


class PyAirtableService:
    """
    Base class for PyAirtable microservices.
    
    Provides standardized FastAPI setup, middleware configuration,
    security, health checks, and common functionality.
    """
    
    def __init__(self, config: ServiceConfig):
        """
        Initialize the service with configuration.
        
        Args:
            config: ServiceConfig instance with service configuration
        """
        self.config = config
        self.logger = logging.getLogger(config.service_name)
        self._app: Optional[FastAPI] = None
        self._startup_complete = False
        self._shutdown_complete = False
        
        # Setup logging
        setup_logging(
            level=config.log_level,
            format_type=config.log_format,
            service_name=config.service_name
        )
        
        self.logger.info(f"Initializing {config.service_name} v{config.version}")
    
    @property
    def app(self) -> FastAPI:
        """Get the FastAPI application instance."""
        if self._app is None:
            self._app = self._create_app()
        return self._app
    
    def _create_app(self) -> FastAPI:
        """Create and configure the FastAPI application."""
        # Create lifespan context manager
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            self.logger.info(f"Starting {self.config.service_name}...")
            await self._startup()
            yield
            # Shutdown
            self.logger.info(f"Shutting down {self.config.service_name}...")
            await self._shutdown()
        
        # Create FastAPI app with lifespan
        fastapi_kwargs = self.config.get_fastapi_kwargs()
        fastapi_kwargs["lifespan"] = lifespan
        
        app = FastAPI(**fastapi_kwargs)
        
        # Setup middleware
        self._setup_middleware(app)
        
        # Setup routes
        self._setup_routes(app)
        
        return app
    
    def _setup_middleware(self, app: FastAPI) -> None:
        """Setup middleware for the application."""
        
        # CORS middleware (added first, executed last)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.cors_origins,
            allow_credentials=True,
            allow_methods=self.config.cors_methods,
            allow_headers=self.config.cors_headers,
        )
        
        # Security middleware
        if self.config.enable_security_headers:
            app.add_middleware(SecurityHeadersMiddleware)
        
        if self.config.enable_rate_limiting:
            app.add_middleware(
                RateLimitMiddleware,
                calls=self.config.rate_limit_calls,
                period=self.config.rate_limit_period
            )
        
        # Common middleware (correlation ID, logging, error handling)
        setup_middleware(
            app,
            enable_correlation_id=self.config.enable_correlation_id,
            enable_request_logging=self.config.enable_request_logging,
            enable_error_handling=self.config.enable_error_handling,
            enable_metrics=self.config.enable_metrics,
            correlation_header=self.config.correlation_header,
            exclude_log_paths=self.config.exclude_log_paths,
        )
        
        # Custom middleware
        for middleware_class, kwargs in self.config.custom_middleware:
            app.add_middleware(middleware_class, **kwargs)
    
    def _setup_routes(self, app: FastAPI) -> None:
        """Setup routes for the application."""
        
        # Health check endpoint
        if self.config.enable_health_check:
            @app.get(self.config.health_endpoint)
            async def health_check():
                """Health check endpoint with dependency checks."""
                return await self._perform_health_check()
        
        # API key verification dependency
        if self.config.api_key:
            def verify_api_key(
                api_key: Optional[str] = Header(None, alias=self.config.api_key_header)
            ) -> bool:
                """Verify API key from header."""
                if not verify_api_key_secure(api_key or "", self.config.api_key or ""):
                    raise HTTPException(status_code=401, detail="Invalid API key")
                return True
            
            # Store the dependency for use by subclasses
            self.verify_api_key = verify_api_key
        
        # Custom routes
        for router, prefix, tags in self.config.custom_routes:
            app.include_router(router, prefix=prefix, tags=tags)
    
    async def _startup(self) -> None:
        """Execute startup tasks."""
        try:
            # Execute custom startup tasks
            for task in self.config.startup_tasks:
                if callable(task):
                    if hasattr(task, '__call__') and hasattr(task, '__code__'):
                        # Check if it's an async function
                        if task.__code__.co_flags & 0x80:  # CO_ITERABLE_COROUTINE
                            await task()
                        else:
                            task()
                    else:
                        # Assume sync function
                        task()
            
            # Call custom startup hook
            await self.on_startup()
            
            self._startup_complete = True
            self.logger.info(f"{self.config.service_name} startup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Startup failed: {e}")
            raise
    
    async def _shutdown(self) -> None:
        """Execute shutdown tasks."""
        try:
            # Call custom shutdown hook
            await self.on_shutdown()
            
            # Execute custom shutdown tasks
            for task in self.config.shutdown_tasks:
                if callable(task):
                    if hasattr(task, '__call__') and hasattr(task, '__code__'):
                        # Check if it's an async function
                        if task.__code__.co_flags & 0x80:  # CO_ITERABLE_COROUTINE
                            await task()
                        else:
                            task()
                    else:
                        # Assume sync function
                        task()
            
            self._shutdown_complete = True
            self.logger.info(f"{self.config.service_name} shutdown completed successfully")
            
        except Exception as e:
            self.logger.error(f"Shutdown failed: {e}")
            # Don't re-raise during shutdown
    
    async def _perform_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        health_status = {
            "status": "healthy",
            "service": self.config.service_name,
            "version": self.config.version,
            "startup_complete": self._startup_complete,
        }
        
        # Check dependencies
        dependency_checks = []
        for dependency_check in self.config.health_check_dependencies:
            try:
                if callable(dependency_check):
                    if hasattr(dependency_check, '__call__') and hasattr(dependency_check, '__code__'):
                        # Check if it's an async function
                        if dependency_check.__code__.co_flags & 0x80:  # CO_ITERABLE_COROUTINE
                            result = await dependency_check()
                        else:
                            result = dependency_check()
                    else:
                        result = dependency_check()
                    
                    dependency_checks.append(result)
            except Exception as e:
                dependency_checks.append({
                    "name": getattr(dependency_check, '__name__', 'unknown'),
                    "status": "unhealthy",
                    "error": str(e)
                })
        
        if dependency_checks:
            health_status["dependencies"] = dependency_checks
            # Overall health depends on all dependencies being healthy
            if any(dep.get("status") == "unhealthy" for dep in dependency_checks):
                health_status["status"] = "degraded"
        
        # Custom health check
        custom_health = await self.health_check()
        if custom_health:
            health_status.update(custom_health)
        
        return health_status
    
    # Extension points for subclasses
    async def on_startup(self) -> None:
        """Override this method to add custom startup logic."""
        pass
    
    async def on_shutdown(self) -> None:
        """Override this method to add custom shutdown logic."""
        pass
    
    async def health_check(self) -> Optional[Dict[str, Any]]:
        """Override this method to add custom health check logic."""
        return None
    
    def add_router(self, router, prefix: str = "", tags: Optional[List[str]] = None) -> None:
        """Add a router to the application."""
        if tags is None:
            tags = []
        self.app.include_router(router, prefix=prefix, tags=tags)
    
    def add_middleware(self, middleware_class, **kwargs) -> None:
        """Add middleware to the application."""
        self.app.add_middleware(middleware_class, **kwargs)
    
    def run(self, host: str = "0.0.0.0", port: Optional[int] = None) -> None:
        """
        Run the service using uvicorn.
        
        Args:
            host: Host to bind to
            port: Port to bind to (defaults to config.port)
        """
        try:
            import uvicorn
        except ImportError:
            raise ImportError("uvicorn is required to run the service. Install with: pip install uvicorn")
        
        if port is None:
            port = self.config.port
        
        self.logger.info(f"Starting {self.config.service_name} on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port)
    
    def __repr__(self) -> str:
        return f"PyAirtableService(name={self.config.service_name}, version={self.config.version})"