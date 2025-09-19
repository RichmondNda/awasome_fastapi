"""
API v1 router configuration.
"""

from fastapi import APIRouter

from .users import router as users_router
from .health import router as health_router
from .endpoints.cache import router as cache_router
from .endpoints.performance import router as performance_router

# Create v1 API router
api_v1_router = APIRouter()

# Include sub-routers
api_v1_router.include_router(
    users_router,
    prefix="/users",
    tags=["users"],
)

api_v1_router.include_router(
    health_router,
    prefix="/system",
    tags=["system", "monitoring"],
)

api_v1_router.include_router(
    cache_router,
    prefix="/system",
    tags=["system", "cache", "monitoring"],
)

api_v1_router.include_router(
    performance_router,
    prefix="/system",
    tags=["system", "performance", "monitoring"],
)