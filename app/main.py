"""
FastAPI application factory and configuration.
Production-ready microservice with comprehensive middleware stack.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn

from .core.config import settings
from .core.logging import setup_logging, get_logger
from .core.database import init_database, close_database
from .core.exceptions import BaseAPIException
from .api.v1 import api_v1_router
from .middleware.logging import logging_middleware
from .middleware.rate_limiting import rate_limit_middleware
from .middleware.security import security_headers_middleware
from .cache import init_cache, close_cache, warm_cache

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    try:
        # Initialize database connection
        init_database()
        logger.info("Database connection initialized")
        
        # Initialize Redis cache
        cache_connected = await init_cache(settings.REDIS_URL)
        if cache_connected:
            logger.info("Redis cache connected")
            # Warm up cache with frequently accessed data
            await warm_cache()
        else:
            logger.warning("Redis cache connection failed - continuing without cache")
        
        # Log configuration
        logger.info(f"API available at: {settings.API_V1_STR}")
        logger.info(f"CORS origins: {settings.BACKEND_CORS_ORIGINS}")
        logger.info(f"Rate limiting: {settings.RATE_LIMIT_PER_MINUTE} req/min")
        
        logger.info("Application startup complete")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down application")
        try:
            close_database()
            logger.info("Database connection closed")
            
            await close_cache()
            logger.info("Redis cache connection closed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        logger.info("Application shutdown complete")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    
    # Create FastAPI app with comprehensive configuration
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        description="Awasome FastAPI Microservice with comprehensive features",
        openapi_url="/api/v1/openapi.json",
        docs_url="/docs" if settings.ENVIRONMENT == "development" else None,  # Disable docs in production
        redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
        lifespan=lifespan,
        openapi_tags=[
            {
                "name": "users",
                "description": "User management operations. Create, read, update, and delete users.",
            },
            {
                "name": "system",
                "description": "System monitoring and health check endpoints.",
            },
        ],
        # Contact and license info for OpenAPI
        contact={
            "name": "API Support",
            "email": "support@example.com",
        },
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time", "X-RateLimit-Remaining"]
    )
    
    # Add custom middleware (order matters - first added is executed last)
    app.middleware("http")(security_headers_middleware)
    app.middleware("http")(rate_limit_middleware)
    app.middleware("http")(logging_middleware)
    
    # Include API routers
    app.include_router(
        api_v1_router,
        prefix=settings.API_V1_STR,
    )
    
    # Global exception handlers
    @app.exception_handler(BaseAPIException)
    async def api_exception_handler(request: Request, exc: BaseAPIException):
        """Handle custom API exceptions."""
        logger.warning(f"API Exception: {exc.detail} (Status: {exc.status_code})")
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "request_id": getattr(request.state, "request_id", None)
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic validation errors."""
        logger.warning(f"Validation error: {exc.errors()}")
        
        # Format validation errors nicely
        errors = []
        for error in exc.errors():
            errors.append({
                "field": " -> ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })
        
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation failed",
                "details": errors,
                "request_id": getattr(request.state, "request_id", None)
            }
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions."""
        logger.warning(f"HTTP Exception: {exc.detail} (Status: {exc.status_code})")
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "request_id": getattr(request.state, "request_id", None)
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(f"Unexpected error: {exc}", exc_info=True)
        
        # Don't expose internal errors in production
        if settings.is_production:
            detail = "Internal server error"
        else:
            detail = str(exc)
        
        return JSONResponse(
            status_code=500,
            content={
                "error": detail,
                "status_code": 500,
                "request_id": getattr(request.state, "request_id", None)
            }
        )
    
    # Root endpoint
    @app.get("/", include_in_schema=False)
    async def root():
        """Root endpoint with service information."""
        return {
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "status": "running",
            "environment": settings.ENVIRONMENT,
            "docs_url": "/docs" if settings.is_development else None,
            "api_url": settings.API_V1_STR
        }
    
    logger.info("FastAPI application created successfully")
    return app


# Create the application instance
app = create_application()


if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
    )