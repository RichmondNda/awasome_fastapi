"""
Security middleware for headers and protection.
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
import secrets

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


async def security_headers_middleware(request: Request, call_next) -> Response:
    """Add security headers to all responses."""
    
    try:
        response = await call_next(request)
        
        # Security headers
        security_headers = {
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Enable XSS protection
            "X-XSS-Protection": "1; mode=block",
            
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Content Security Policy (adapté selon l'environnement)
            "Content-Security-Policy": (
                # CSP relaxée en développement pour Swagger UI/ReDoc
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css; "
                "img-src 'self' data: https: ; "
                "font-src 'self' data:; "
                "connect-src 'self' https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css.map;"
                if settings.is_development else
                # CSP stricte en production
                "default-src 'self'  'unsafe-inline'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self'; "
                "img-src 'self' data: https: ; "
                "font-src 'self' data:; "
                "connect-src 'self';"
            ),
            
            # Strict Transport Security (HTTPS only)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains" if not settings.is_development else "",
            
            # Permissions Policy (formerly Feature Policy)
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "accelerometer=(), "
                "gyroscope=()"
            ),
            
            # Server identification (hide server info)
            "Server": settings.PROJECT_NAME,
            
            # API Version
            "X-API-Version": settings.VERSION
        }
        
        # Add headers to response
        for header_name, header_value in security_headers.items():
            if header_value:  # Only add non-empty headers
                response.headers[header_name] = header_value
        
        return response
        
    except Exception as e:
        logger.error(f"Error in security headers middleware: {e}")
        return await call_next(request)


async def cors_middleware(request: Request, call_next) -> Response:
    """Handle CORS manually (alternative to FastAPI's CORS middleware)."""
    
    origin = request.headers.get("origin")
    
    # Handle preflight requests
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*" if settings.is_development else origin if origin in settings.BACKEND_CORS_ORIGINS else "",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, X-Request-ID",
            "Access-Control-Max-Age": "86400",  # 24 hours
        }
        
        return JSONResponse(
            status_code=200,
            content={},
            headers=headers
        )
    
    # Process regular request
    response = await call_next(request)
    
    # Add CORS headers to response
    if origin:
        if settings.is_development or origin in settings.BACKEND_CORS_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, X-Request-ID"
        response.headers["Access-Control-Expose-Headers"] = "X-Request-ID, X-Process-Time, X-RateLimit-Remaining"
    
    return response