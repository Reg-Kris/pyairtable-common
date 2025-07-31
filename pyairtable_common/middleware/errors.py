"""
Error handling middleware.
"""
import traceback
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..logging import get_logger
from ..exceptions import PyAirtableError, ValidationError, AuthenticationError

logger = get_logger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for centralized error handling."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle errors consistently across the application."""
        
        try:
            response = await call_next(request)
            return response
            
        except PyAirtableError as exc:
            # Handle known application errors
            logger.warning(
                "Application error occurred",
                error_type=type(exc).__name__,
                error_message=str(exc),
                path=request.url.path,
                method=request.method,
            )
            
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": {
                        "type": type(exc).__name__,
                        "message": str(exc),
                        "code": getattr(exc, 'error_code', None),
                    }
                }
            )
            
        except ValidationError as exc:
            # Handle validation errors
            logger.warning(
                "Validation error occurred",
                error_message=str(exc),
                path=request.url.path,
                method=request.method,
            )
            
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "type": "ValidationError",
                        "message": str(exc),
                        "details": getattr(exc, 'errors', []),
                    }
                }
            )
            
        except AuthenticationError as exc:
            # Handle authentication errors
            logger.warning(
                "Authentication error occurred",
                error_message=str(exc),
                path=request.url.path,
                method=request.method,
            )
            
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "type": "AuthenticationError",
                        "message": str(exc),
                    }
                }
            )
            
        except Exception as exc:
            # Handle unexpected errors
            logger.error(
                "Unexpected error occurred",
                error_type=type(exc).__name__,
                error_message=str(exc),
                path=request.url.path,
                method=request.method,
                traceback=traceback.format_exc(),
                exc_info=True
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "type": "InternalServerError",
                        "message": "An unexpected error occurred",
                    }
                }
            )


async def error_handling_middleware(request: Request, call_next: Callable) -> Response:
    """Function-based error handling middleware."""
    
    try:
        response = await call_next(request)
        return response
        
    except Exception as exc:
        logger.error(
            "Unhandled error in request",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            exc_info=True
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": type(exc).__name__,
                    "message": "Internal server error",
                }
            }
        )