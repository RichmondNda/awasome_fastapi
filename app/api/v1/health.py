"""
Health check and system monitoring endpoints.
"""

import time
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from ...core.config import settings
from ...core.database import db_manager
from ...schemas.user import HealthCheck
from ...core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Track application startup time
APP_START_TIME = time.time()


@router.get(
    "/health",
    response_model=HealthCheck,
    summary="Health check",
    description="Check the health status of the API and its dependencies.",
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Service is unhealthy"}
    }
)
async def health_check():
    """
    Comprehensive health check endpoint.
    
    Returns:
    - Service status
    - Current timestamp
    - Service version
    - Uptime
    - Database connection status
    """
    try:
        current_time = time.time()
        uptime = current_time - APP_START_TIME
        
        # Check database health
        db_health = db_manager.health_check()
        
        # Determine overall status
        is_healthy = db_health.get("status") == "connected"
        
        health_data = HealthCheck(
            status="healthy" if is_healthy else "unhealthy",
            timestamp=datetime.utcnow().isoformat(),
            version=settings.VERSION,
            uptime=uptime,
            database=db_health
        )
        
        status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        
        logger.debug(f"Health check: {health_data.status}")
        
        return JSONResponse(
            status_code=status_code,
            content=health_data.dict()
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        
        error_response = {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.VERSION,
            "uptime": time.time() - APP_START_TIME,
            "error": str(e),
            "database": {"status": "error", "error": str(e)}
        }
        
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=error_response
        )


@router.get(
    "/health/live",
    summary="Liveness probe",
    description="Simple liveness check for container orchestration.",
    responses={
        200: {"description": "Service is alive"}
    }
)
async def liveness_check():
    """
    Simple liveness check for Kubernetes/Docker.
    
    Returns 200 if the application is running.
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@router.get(
    "/health/ready",
    summary="Readiness probe", 
    description="Readiness check for container orchestration.",
    responses={
        200: {"description": "Service is ready"},
        503: {"description": "Service is not ready"}
    }
)
async def readiness_check():
    """
    Readiness check for Kubernetes/Docker.
    
    Returns 200 if the application is ready to serve traffic.
    """
    try:
        # Check critical dependencies
        db_health = db_manager.health_check()
        is_ready = db_health.get("status") == "connected"
        
        if is_ready:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "ready",
                    "timestamp": datetime.utcnow().isoformat(),
                    "database": db_health
                }
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "not ready",
                    "timestamp": datetime.utcnow().isoformat(),
                    "reason": "Database not connected",
                    "database": db_health
                }
            )
            
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not ready",
                "timestamp": datetime.utcnow().isoformat(),
                "reason": str(e)
            }
        )


@router.get(
    "/info",
    summary="Service information",
    description="Get detailed information about the service.",
    responses={
        200: {"description": "Service information"}
    }
)
async def service_info():
    """
    Get detailed service information.
    
    Returns configuration and runtime information.
    """
    try:
        uptime = time.time() - APP_START_TIME
        
        info = {
            "service": {
                "name": settings.PROJECT_NAME,
                "version": settings.VERSION,
                "description": settings.DESCRIPTION,
                "environment": settings.ENVIRONMENT,
                "debug": settings.DEBUG
            },
            "runtime": {
                "uptime_seconds": uptime,
                "start_time": datetime.fromtimestamp(APP_START_TIME).isoformat(),
                "current_time": datetime.utcnow().isoformat()
            },
            "api": {
                "version": settings.API_V1_STR,
                "docs_url": "/docs",
                "redoc_url": "/redoc"
            },
            "database": {
                "type": "CouchDB",
                "name": settings.COUCHDB_DB_NAME
            },
            "features": {
                "rate_limiting": settings.RATE_LIMIT_PER_MINUTE > 0,
                "cors_enabled": len(settings.BACKEND_CORS_ORIGINS) > 0,
                "security_headers": True,
                "request_logging": True
            }
        }
        
        logger.debug("Retrieved service info")
        return info
        
    except Exception as e:
        logger.error(f"Error getting service info: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Failed to retrieve service information"}
        )