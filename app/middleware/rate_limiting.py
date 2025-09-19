"""
Rate limiting middleware to prevent abuse.
"""

import time
from typing import Dict, Tuple
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, max_requests: int, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window  # seconds
        self.requests: Dict[str, list] = {}
    
    def is_allowed(self, client_ip: str) -> Tuple[bool, int, int]:
        """
        Check if request is allowed for the client IP.
        
        Returns:
            Tuple of (is_allowed, remaining_requests, reset_time)
        """
        now = time.time()
        
        # Clean old entries
        if client_ip in self.requests:
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip]
                if now - req_time < self.time_window
            ]
        else:
            self.requests[client_ip] = []
        
        # Check if limit exceeded
        current_requests = len(self.requests[client_ip])
        
        if current_requests >= self.max_requests:
            # Calculate reset time
            oldest_request = min(self.requests[client_ip])
            reset_time = int(oldest_request + self.time_window)
            return False, 0, reset_time
        
        # Add current request
        self.requests[client_ip].append(now)
        remaining = self.max_requests - (current_requests + 1)
        reset_time = int(now + self.time_window)
        
        return True, remaining, reset_time


# Global rate limiter instance
rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_PER_MINUTE,
    time_window=60
)


async def rate_limit_middleware(request: Request, call_next) -> Response:
    """Apply rate limiting based on client IP."""
    
    # Skip rate limiting in development mode
    if settings.is_development:
        return await call_next(request)
    
    # Get client IP
    client_ip = "unknown"
    if request.client:
        client_ip = request.client.host
    
    # Handle forwarded headers (for reverse proxy setups)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        client_ip = real_ip
    
    # Check rate limit
    is_allowed, remaining, reset_time = rate_limiter.is_allowed(client_ip)
    
    if not is_allowed:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Too many requests",
                "message": f"Rate limit of {settings.RATE_LIMIT_PER_MINUTE} requests per minute exceeded",
                "retry_after": reset_time - int(time.time())
            },
            headers={
                "X-RateLimit-Limit": str(settings.RATE_LIMIT_PER_MINUTE),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_time),
                "Retry-After": str(reset_time - int(time.time()))
            }
        )
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers to response
    response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_PER_MINUTE)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_time)
    
    return response