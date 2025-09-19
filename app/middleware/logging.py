"""
Request logging middleware for monitoring and debugging.
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import logging

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)
access_logger = get_logger("access")


async def logging_middleware(request: Request, call_next: Callable) -> Response:
    """Log all HTTP requests with timing and request details."""
    
    # Generate unique request ID
    request_id = str(uuid.uuid4())[:8]
    
    # Add request ID to request state for use in other parts of the application
    request.state.request_id = request_id
    
    # Start timing
    start_time = time.time()
    
    # Extract request details
    client_host = getattr(request.client, "host", "unknown") if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Log incoming request
    access_logger.info(
        f"[{request_id}] {request.method} {request.url} - "
        f"Client: {client_host} - UserAgent: {user_agent}"
    )
    
    try:
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        access_logger.info(
            f"[{request_id}] {request.method} {request.url} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.3f}s"
        )
        
        # Add custom headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.3f}"
        
        return response
        
    except Exception as e:
        # Calculate processing time for errors too
        process_time = time.time() - start_time
        
        # Log error
        logger.error(
            f"[{request_id}] {request.method} {request.url} - "
            f"Error: {str(e)} - Time: {process_time:.3f}s"
        )
        
        # Return generic error response
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "request_id": request_id
            },
            headers={
                "X-Request-ID": request_id,
                "X-Process-Time": f"{process_time:.3f}"
            }
        )