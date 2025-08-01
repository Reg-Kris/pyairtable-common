"""
PyAirtableService Usage Examples
Demonstrates how to use the unified service base class and factory patterns.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter
from pyairtable_common.service import PyAirtableService, ServiceConfig, create_service


# Example 1: Simple Custom Service
def example_1_simple_custom_service():
    """Example of creating a simple custom service."""
    
    # Create service using factory function
    service = create_service(
        service_type="custom",
        title="My Custom Service",
        description="A custom PyAirtable microservice",
        service_name="my-custom-service",
        port=8005
    )
    
    # Add custom routes
    @service.app.get("/custom")
    async def custom_endpoint():
        return {"message": "Hello from custom service!"}
    
    # Run the service
    # service.run()
    return service


# Example 2: Service with Custom Configuration
def example_2_custom_configuration():
    """Example of creating a service with custom configuration."""
    
    config = ServiceConfig(
        title="Advanced Custom Service",
        description="Custom service with advanced configuration",
        service_name="advanced-service",
        version="2.0.0",
        port=8006,
        
        # Custom security settings
        rate_limit_calls=200,
        rate_limit_period=60,
        
        # Custom CORS settings
        cors_origins=["https://myapp.com", "https://api.myapp.com"],
        cors_methods=["GET", "POST"],
        
        # Custom middleware exclusions
        exclude_log_paths=["/health", "/metrics", "/custom-health"],
        
        # Custom health endpoint
        health_endpoint="/custom-health"
    )
    
    service = PyAirtableService(config)
    
    # Add custom routes
    @service.app.get("/advanced")
    async def advanced_endpoint():
        return {"message": "Advanced service endpoint"}
    
    return service


# Example 3: Service with Startup/Shutdown Tasks
class DatabaseService:
    """Mock database service for example."""
    
    def __init__(self):
        self.connected = False
    
    async def connect(self):
        """Connect to database."""
        print("🔗 Connecting to database...")
        await asyncio.sleep(0.1)  # Simulate connection time
        self.connected = True
        print("✅ Database connected")
    
    async def disconnect(self):
        """Disconnect from database."""
        print("🔌 Disconnecting from database...")
        await asyncio.sleep(0.1)  # Simulate disconnection time
        self.connected = False
        print("✅ Database disconnected")
    
    async def health_check(self):
        """Check database health."""
        return {
            "name": "database",
            "status": "healthy" if self.connected else "unhealthy",
            "connected": self.connected
        }


def example_3_startup_shutdown_tasks():
    """Example of service with startup and shutdown tasks."""
    
    # Create mock database service
    db = DatabaseService()
    
    config = ServiceConfig(
        title="Database-Backed Service",
        description="Service with database connection management",
        service_name="db-service",
        port=8007,
        
        # Add startup and shutdown tasks
        startup_tasks=[db.connect],
        shutdown_tasks=[db.disconnect],
        
        # Add health check dependency
        health_check_dependencies=[db.health_check]
    )
    
    service = PyAirtableService(config)
    
    # Add routes that use the database
    @service.app.get("/data")
    async def get_data():
        if not db.connected:
            return {"error": "Database not connected"}
        return {"data": "Sample data from database"}
    
    return service


# Example 4: Service with Custom Health Checks
class CustomHealthService(PyAirtableService):
    """Example service with custom health check logic."""
    
    def __init__(self):
        config = ServiceConfig(
            title="Custom Health Service",
            description="Service with custom health check implementation",
            service_name="custom-health-service",
            port=8008
        )
        super().__init__(config)
        
        # Add custom routes
        self._setup_custom_routes()
    
    def _setup_custom_routes(self):
        """Setup custom routes."""
        
        @self.app.get("/status")
        async def status():
            return {"status": "running", "service": "custom-health-service"}
    
    async def health_check(self) -> Optional[Dict[str, Any]]:
        """Custom health check implementation."""
        # Perform custom health checks
        try:
            # Simulate some health checks
            await asyncio.sleep(0.01)
            
            return {
                "custom_check": "passed",
                "memory_usage": "normal",
                "disk_space": "sufficient",
                "external_apis": "reachable"
            }
        except Exception as e:
            return {
                "custom_check": "failed",
                "error": str(e)
            }


# Example 5: Service with Custom Router
def example_5_custom_router():
    """Example of service with custom router."""
    
    # Create a custom router
    api_router = APIRouter()
    
    @api_router.get("/users")
    async def list_users():
        return {"users": ["alice", "bob", "charlie"]}
    
    @api_router.post("/users")
    async def create_user(user_data: dict):
        return {"message": f"User {user_data.get('name')} created"}
    
    @api_router.get("/users/{user_id}")
    async def get_user(user_id: str):
        return {"user_id": user_id, "name": f"User {user_id}"}
    
    # Create service
    service = create_service(
        service_type="custom",
        title="User Management Service",
        description="Service for managing users",
        service_name="user-service",
        port=8009
    )
    
    # Add the router
    service.add_router(api_router, prefix="/api/v1", tags=["users"])
    
    return service


# Example 6: Pre-configured Service Types
def example_6_preconfigured_services():
    """Examples of using pre-configured service types."""
    
    # API Gateway
    gateway = create_service(
        service_type="api-gateway",
        port=8000
    )
    
    # Airtable Gateway
    airtable_gateway = create_service(
        service_type="airtable-gateway",
        port=8002
    )
    
    # MCP Server
    mcp_server = create_service(
        service_type="mcp-server",
        port=8001
    )
    
    # LLM Orchestrator
    llm_orchestrator = create_service(
        service_type="llm-orchestrator",
        port=8003
    )
    
    return {
        "gateway": gateway,
        "airtable_gateway": airtable_gateway,
        "mcp_server": mcp_server,
        "llm_orchestrator": llm_orchestrator
    }


# Example 7: Service with Middleware Customization
def example_7_custom_middleware():
    """Example of service with custom middleware."""
    
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response
    import time
    
    class TimingMiddleware(BaseHTTPMiddleware):
        """Custom middleware to add timing headers."""
        
        async def dispatch(self, request: Request, call_next):
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            return response
    
    config = ServiceConfig(
        title="Timing Service",
        description="Service with custom timing middleware",
        service_name="timing-service",
        port=8010,
        
        # Add custom middleware
        custom_middleware=[(TimingMiddleware, {})]
    )
    
    service = PyAirtableService(config)
    
    @service.app.get("/timed")
    async def timed_endpoint():
        # Simulate some processing time
        await asyncio.sleep(0.1)
        return {"message": "This endpoint is timed"}
    
    return service


# Example Usage Functions
async def run_example_service():
    """Run an example service for testing."""
    
    # Create a simple service
    service = example_1_simple_custom_service()
    
    # You would normally call service.run() here, but for example purposes
    # we'll just show the configuration
    print(f"Service: {service.config.title}")
    print(f"Port: {service.config.port}")
    print(f"Health endpoint: {service.config.health_endpoint}")
    
    # Test health check
    health = await service._perform_health_check()
    print(f"Health check: {health}")


if __name__ == "__main__":
    # Run the example
    asyncio.run(run_example_service())