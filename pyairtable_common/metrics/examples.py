"""
Usage examples and integration patterns for PyAirtable metrics system.

This module provides complete examples of how to integrate metrics collection
into each microservice in the PyAirtable ecosystem.
"""
import asyncio
import time
from typing import Optional
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from ..logging import setup_logging, get_logger
from ..middleware import setup_middleware
from .core import initialize_metrics, MetricsCollector, timed
from .service_configs import create_service_metrics
from .integrations import (
    create_metrics_enabled_redis,
    create_metrics_enabled_airtable_limiter,
    create_metrics_enabled_circuit_breaker
)

logger = get_logger(__name__)


# Example 1: Basic FastAPI Service with Metrics
def create_basic_service_with_metrics(service_name: str, version: str = "1.0.0") -> FastAPI:
    """
    Create a basic FastAPI service with full metrics integration.
    
    This example shows the minimal setup required for any PyAirtable service.
    """
    
    # Initialize logging
    setup_logging(service_name=service_name)
    
    # Initialize metrics
    metrics = initialize_metrics(service_name, version)
    
    # Create FastAPI app
    app = FastAPI(title=service_name, version=version)
    
    # Setup middleware (including metrics)
    setup_middleware(
        app,
        enable_correlation_id=True,
        enable_request_logging=True,
        enable_error_handling=True,
        enable_metrics=True,
        metrics_collector=metrics
    )
    
    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": service_name, "version": version}
    
    return app


# Example 2: Airtable Gateway Service Integration
class AirtableGatewayService:
    """Example Airtable Gateway service with full metrics integration."""
    
    def __init__(self, service_name: str = "airtable-gateway-py", redis_url: str = "redis://localhost:6379"):
        self.service_name = service_name
        self.redis_url = redis_url
        
        # Initialize metrics
        self.metrics = initialize_metrics(service_name)
        self.service_metrics = create_service_metrics(service_name, self.metrics)
        
        # Initialize Redis with metrics
        self.redis = None
        self.rate_limiter = None
    
    async def initialize(self):
        """Initialize async components."""
        # Create metrics-enabled Redis client
        self.redis = create_metrics_enabled_redis(self.redis_url, self.metrics)
        
        # Create metrics-enabled rate limiter
        self.rate_limiter = create_metrics_enabled_airtable_limiter(
            self.redis.redis, self.metrics
        )
        
        logger.info(f"{self.service_name} initialized with metrics")
    
    @timed("airtable_api_call")
    async def make_airtable_request(self, base_id: str, table_name: str, operation: str) -> dict:
        """Example Airtable API request with metrics."""
        start_time = time.time()
        
        try:
            # Check rate limits
            rate_limit_result = await self.rate_limiter.check_base_limit(base_id)
            if not rate_limit_result['allowed']:
                # Rate limit metrics are automatically recorded
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            
            # Check cache first
            cache_key = f"airtable:{base_id}:{table_name}:{operation}"
            cached_result = await self.redis.get(cache_key)
            
            if cached_result:
                # Record cache hit
                self.service_metrics.record_cache_operation(
                    operation="get",
                    base_id=base_id,
                    table_name=table_name,
                    result="hit"
                )
                return {"data": cached_result, "from_cache": True}
            
            # Record cache miss
            self.service_metrics.record_cache_operation(
                operation="get",
                base_id=base_id,
                table_name=table_name,
                result="miss"
            )
            
            # Simulate API call
            await asyncio.sleep(0.1)  # Simulate network delay
            result = {"records": [{"id": "rec123", "fields": {"Name": "Test"}}]}
            
            # Cache the result
            await self.redis.set(cache_key, str(result), ex=300)
            self.service_metrics.record_cache_operation(
                operation="set",
                base_id=base_id,
                table_name=table_name,
                result="success"
            )
            
            # Record successful API call
            duration = time.time() - start_time
            self.metrics.record_airtable_request(
                base_id=base_id,
                table_name=table_name,
                operation=operation,
                status_code=200,
                duration=duration
            )
            
            return {"data": result, "from_cache": False}
            
        except Exception as e:
            # Record error
            self.metrics.record_error(
                error_type=type(e).__name__,
                endpoint=f"/airtable/{base_id}/{table_name}"
            )
            raise
    
    def create_app(self) -> FastAPI:
        """Create FastAPI application."""
        app = FastAPI(title=self.service_name)
        
        # Setup middleware with metrics
        setup_middleware(
            app,
            enable_metrics=True,
            metrics_collector=self.metrics
        )
        
        @app.on_event("startup")
        async def startup():
            await self.initialize()
        
        @app.get("/airtable/{base_id}/{table_name}/records")
        async def get_records(base_id: str, table_name: str):
            """Get records from Airtable."""
            return await self.make_airtable_request(base_id, table_name, "list")
        
        return app


# Example 3: MCP Server with Subprocess Metrics
class MCPServerService:
    """Example MCP Server service with subprocess and protocol metrics."""
    
    def __init__(self, service_name: str = "mcp-server-py"):
        self.service_name = service_name
        self.metrics = initialize_metrics(service_name)
        self.service_metrics = create_service_metrics(service_name, self.metrics)
        self.active_processes = {}
    
    async def create_subprocess(self, process_type: str) -> str:
        """Create a subprocess and track metrics."""
        process_id = f"{process_type}_{int(time.time())}"
        start_time = time.time()
        
        try:
            # Simulate subprocess creation
            await asyncio.sleep(0.05)  # Simulate startup time
            
            self.active_processes[process_id] = {
                "type": process_type,
                "start_time": start_time
            }
            
            # Record successful creation
            self.service_metrics.record_subprocess_creation(process_type, "success")
            self.service_metrics.update_subprocess_count(
                process_type, 
                len([p for p in self.active_processes.values() if p["type"] == process_type])
            )
            
            logger.info(f"Created subprocess {process_id}")
            return process_id
            
        except Exception as e:
            # Record failed creation
            self.service_metrics.record_subprocess_creation(process_type, "failure")
            raise
    
    async def terminate_subprocess(self, process_id: str):
        """Terminate subprocess and record duration."""
        if process_id not in self.active_processes:
            return
        
        process_info = self.active_processes[process_id]
        duration = time.time() - process_info["start_time"]
        
        # Record subprocess duration
        self.service_metrics.record_subprocess_duration(process_info["type"], duration)
        
        # Update count
        del self.active_processes[process_id]
        self.service_metrics.update_subprocess_count(
            process_info["type"],
            len([p for p in self.active_processes.values() if p["type"] == process_info["type"]])
        )
        
        logger.info(f"Terminated subprocess {process_id} after {duration:.2f}s")
    
    async def execute_tool(self, tool_name: str, parameters: dict) -> dict:
        """Execute a tool and record metrics."""
        start_time = time.time()
        
        try:
            # Simulate tool execution
            execution_time = 0.1 + (hash(tool_name) % 5) * 0.1  # Variable execution time
            await asyncio.sleep(execution_time)
            
            duration = time.time() - start_time
            result = {"success": True, "output": f"Tool {tool_name} executed"}
            
            # Record successful execution
            self.service_metrics.record_tool_execution(tool_name, "success", duration)
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            # Record failed execution
            self.service_metrics.record_tool_execution(tool_name, "failure", duration)
            raise
    
    def handle_protocol_message(self, message_type: str, direction: str, message_data: dict):
        """Handle protocol message and record metrics."""
        import json
        
        message_size = len(json.dumps(message_data).encode('utf-8'))
        
        try:
            # Process message (simulation)
            if message_type == "tool_call":
                # This would trigger tool execution
                pass
            
            # Record successful message handling
            self.service_metrics.record_protocol_message(
                message_type, direction, "success", message_size
            )
            
        except Exception as e:
            # Record failed message handling
            self.service_metrics.record_protocol_message(
                message_type, direction, "failure", message_size
            )
            raise


# Example 4: LLM Orchestrator with Gemini Metrics
class LLMOrchestratorService:
    """Example LLM Orchestrator service with Gemini and session metrics."""
    
    def __init__(self, service_name: str = "llm-orchestrator-py"):
        self.service_name = service_name
        self.metrics = initialize_metrics(service_name)
        self.service_metrics = create_service_metrics(service_name, self.metrics)
        self.active_sessions = {}
    
    async def create_session(self, session_type: str = "chat") -> str:
        """Create a new LLM session."""
        session_id = f"session_{int(time.time())}"
        self.active_sessions[session_id] = {
            "type": session_type,
            "start_time": time.time(),
            "turn_count": 0
        }
        
        # Update active session count
        self.service_metrics.update_active_sessions(len(self.active_sessions))
        
        logger.info(f"Created session {session_id}")
        return session_id
    
    async def end_session(self, session_id: str):
        """End an LLM session and record metrics."""
        if session_id not in self.active_sessions:
            return
        
        session_info = self.active_sessions[session_id]
        duration = time.time() - session_info["start_time"]
        
        # Record session duration
        self.service_metrics.record_session_duration(duration)
        
        # Clean up
        del self.active_sessions[session_id]
        self.service_metrics.update_active_sessions(len(self.active_sessions))
        
        logger.info(f"Ended session {session_id} after {duration:.2f}s")
    
    @timed("gemini_api_call")
    async def call_gemini_api(self, session_id: str, model: str, prompt: str) -> dict:
        """Make a call to Gemini API with metrics."""
        start_time = time.time()
        
        try:
            # Simulate API call latency
            await asyncio.sleep(0.5 + (hash(prompt) % 10) * 0.1)
            
            # Simulate response
            response_text = f"Response to: {prompt[:50]}..."
            input_tokens = len(prompt.split())
            output_tokens = len(response_text.split())
            
            duration = time.time() - start_time
            
            # Record API request metrics
            self.service_metrics.record_gemini_request(model, "generate", 200, duration)
            
            # Record token usage
            self.service_metrics.record_token_usage(model, "input", input_tokens)
            self.service_metrics.record_token_usage(model, "output", output_tokens)
            
            # Record message lengths
            self.service_metrics.record_message_length("input", len(prompt))
            self.service_metrics.record_message_length("output", len(response_text))
            
            # Update session turn count
            if session_id in self.active_sessions:
                self.active_sessions[session_id]["turn_count"] += 1
                self.service_metrics.record_conversation_turn(
                    self.active_sessions[session_id]["type"]
                )
            
            return {
                "response": response_text,
                "tokens_used": {"input": input_tokens, "output": output_tokens}
            }
            
        except Exception as e:
            duration = time.time() - start_time
            # Record failed API request
            self.service_metrics.record_gemini_request(model, "generate", 500, duration)
            raise


# Example 5: Complete Service Factory
def create_service_with_full_metrics(
    service_name: str,
    version: str = "1.0.0",
    redis_url: Optional[str] = None,
    enable_airtable_metrics: bool = False
) -> FastAPI:
    """
    Factory function to create a fully configured service with metrics.
    
    This is the recommended way to bootstrap any PyAirtable microservice.
    """
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        logger.info(f"Starting {service_name} v{version}")
        
        # Initialize async components if needed
        if redis_url:
            # Initialize Redis connections, rate limiters, etc.
            pass
        
        yield
        
        # Shutdown
        logger.info(f"Shutting down {service_name}")
    
    # Initialize logging
    setup_logging(service_name=service_name)
    
    # Initialize metrics
    metrics = initialize_metrics(service_name, version)
    service_metrics = create_service_metrics(service_name, metrics)
    
    # Create FastAPI app with lifespan
    app = FastAPI(
        title=service_name,
        version=version,
        lifespan=lifespan
    )
    
    # Setup all middleware
    setup_middleware(
        app,
        enable_correlation_id=True,
        enable_request_logging=True,
        enable_error_handling=True,
        enable_metrics=True,
        metrics_collector=metrics
    )
    
    # Store metrics in app state for access in route handlers
    app.state.metrics = metrics
    app.state.service_metrics = service_metrics
    
    # Add standard endpoints
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": service_name, "version": version}
    
    @app.get("/metrics/summary")
    async def metrics_summary():
        """Get metrics summary for this service."""
        from .service_configs import get_service_metrics_summary
        return get_service_metrics_summary(service_name)
    
    return app


# Example usage in a service's main.py:
"""
# main.py for any PyAirtable service

from pyairtable_common.metrics.examples import create_service_with_full_metrics

# Create the app
app = create_service_with_full_metrics(
    service_name="my-service-py",
    version="1.0.0",
    redis_url="redis://localhost:6379",
    enable_airtable_metrics=True
)

# Add your custom routes
@app.get("/custom-endpoint")
async def custom_endpoint():
    # Access metrics from app state
    metrics = app.state.metrics
    service_metrics = app.state.service_metrics
    
    # Your business logic here
    with metrics.time_operation("custom_operation"):
        # Do some work
        pass
    
    return {"message": "Custom endpoint"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""