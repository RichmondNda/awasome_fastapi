"""
System endpoints for cache management and monitoring.
Provides comprehensive cache control and performance testing.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Query, Body
from app.cache import cache, test_cache_performance, UserCache, SessionCache
from app.core.logging import get_logger
import uuid
import time

logger = get_logger(__name__)

router = APIRouter()


@router.get("/cache/info", response_model=Dict[str, Any])
async def get_cache_info():
    """
    Get comprehensive cache information and statistics.
    
    Returns:
        Cache status, Redis info, performance metrics
    """
    try:
        cache_info = await cache.get_info()
        return {
            "status": "success",
            "data": cache_info,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Failed to get cache info: {e}")
        raise HTTPException(status_code=500, detail=f"Cache info error: {str(e)}")


@router.get("/cache/test", response_model=Dict[str, Any])
async def test_cache():
    """
    Test cache functionality with basic operations.
    
    Returns:
        Results of cache operations test
    """
    try:
        test_key = f"test:{uuid.uuid4().hex[:8]}"
        test_value = {"message": "Cache test", "timestamp": time.time()}
        
        # Test SET
        set_result = await cache.set(test_key, test_value, 60)
        
        # Test GET
        get_result = await cache.get(test_key)
        
        # Test EXISTS
        exists_result = await cache.exists(test_key)
        
        # Test TTL
        ttl_result = await cache.ttl(test_key)
        
        # Test DELETE
        delete_result = await cache.delete(test_key)
        
        # Verify deletion
        get_after_delete = await cache.get(test_key)
        
        return {
            "status": "success",
            "data": {
                "set_operation": set_result,
                "get_operation": get_result == test_value,
                "exists_operation": exists_result,
                "ttl_operation": ttl_result,
                "delete_operation": delete_result,
                "get_after_delete": get_after_delete is None,
                "test_key": test_key
            },
            "message": "Cache test completed successfully"
        }
    except Exception as e:
        logger.error(f"Cache test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cache test error: {str(e)}")


@router.get("/cache/performance", response_model=Dict[str, Any])
async def test_cache_perf():
    """
    Test cache performance with multiple operations.
    
    Returns:
        Performance metrics for cache operations
    """
    try:
        performance_results = await test_cache_performance()
        
        return {
            "status": "success",
            "data": performance_results,
            "timestamp": time.time(),
            "message": "Performance test completed"
        }
    except Exception as e:
        logger.error(f"Performance test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Performance test error: {str(e)}")


@router.get("/cache/keys", response_model=Dict[str, Any])
async def get_cache_keys(
    pattern: str = Query(default="*", description="Key pattern to match"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of keys to return")
):
    """
    Get cache keys matching a pattern.
    
    Args:
        pattern: Key pattern to match (supports wildcards)
        limit: Maximum number of keys to return
        
    Returns:
        List of matching cache keys with metadata
    """
    try:
        keys = await cache.keys(pattern)
        limited_keys = keys[:limit]
        
        # Get additional info for each key
        key_info = []
        for key in limited_keys:
            try:
                ttl = await cache.ttl(key)
                exists = await cache.exists(key)
                key_info.append({
                    "key": key,
                    "ttl": ttl,
                    "exists": exists
                })
            except Exception as e:
                key_info.append({
                    "key": key,
                    "error": str(e)
                })
        
        return {
            "status": "success",
            "data": {
                "pattern": pattern,
                "total_found": len(keys),
                "returned": len(limited_keys),
                "keys": key_info
            }
        }
    except Exception as e:
        logger.error(f"Failed to get cache keys: {e}")
        raise HTTPException(status_code=500, detail=f"Get keys error: {str(e)}")


@router.delete("/cache/keys")
async def flush_cache_keys(
    pattern: str = Query(description="Key pattern to delete (required for safety)"),
    confirm: bool = Query(default=False, description="Confirmation flag")
):
    """
    Delete cache keys matching a pattern.
    
    Args:
        pattern: Key pattern to delete
        confirm: Must be true to proceed
        
    Returns:
        Number of keys deleted
    """
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="Must set confirm=true to delete keys"
        )
    
    if pattern in ["*", "**", ""]:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete all keys with wildcard pattern. Use specific pattern."
        )
    
    try:
        deleted_count = await cache.flush_pattern(pattern)
        
        return {
            "status": "success",
            "data": {
                "pattern": pattern,
                "deleted_count": deleted_count
            },
            "message": f"Deleted {deleted_count} keys matching '{pattern}'"
        }
    except Exception as e:
        logger.error(f"Failed to flush cache keys: {e}")
        raise HTTPException(status_code=500, detail=f"Flush keys error: {str(e)}")


@router.post("/cache/set")
async def set_cache_value(
    key: str = Query(description="Cache key"),
    value: Any = Body(description="Value to cache"),
    ttl: int = Query(default=3600, ge=1, le=86400, description="TTL in seconds (max 24h)")
):
    """
    Manually set a cache value.
    
    Args:
        key: Cache key
        value: Value to store
        ttl: Time to live in seconds
        
    Returns:
        Success confirmation
    """
    try:
        result = await cache.set(key, value, ttl)
        
        if result:
            return {
                "status": "success",
                "data": {
                    "key": key,
                    "ttl": ttl,
                    "cached": True
                },
                "message": f"Value cached successfully for key '{key}'"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to cache value")
            
    except Exception as e:
        logger.error(f"Failed to set cache value: {e}")
        raise HTTPException(status_code=500, detail=f"Set cache error: {str(e)}")


@router.get("/cache/get/{key}")
async def get_cache_value(key: str):
    """
    Get a specific cache value.
    
    Args:
        key: Cache key to retrieve
        
    Returns:
        Cached value if found
    """
    try:
        value = await cache.get(key)
        
        if value is not None:
            ttl = await cache.ttl(key)
            return {
                "status": "success",
                "data": {
                    "key": key,
                    "value": value,
                    "ttl": ttl,
                    "found": True
                }
            }
        else:
            return {
                "status": "success",
                "data": {
                    "key": key,
                    "found": False
                },
                "message": f"No value found for key '{key}'"
            }
            
    except Exception as e:
        logger.error(f"Failed to get cache value: {e}")
        raise HTTPException(status_code=500, detail=f"Get cache error: {str(e)}")


@router.delete("/cache/get/{key}")
async def delete_cache_value(key: str):
    """
    Delete a specific cache value.
    
    Args:
        key: Cache key to delete
        
    Returns:
        Deletion confirmation
    """
    try:
        result = await cache.delete(key)
        
        return {
            "status": "success",
            "data": {
                "key": key,
                "deleted": result
            },
            "message": f"Key '{key}' {'deleted' if result else 'not found'}"
        }
    except Exception as e:
        logger.error(f"Failed to delete cache value: {e}")
        raise HTTPException(status_code=500, detail=f"Delete cache error: {str(e)}")


# User cache specific endpoints
@router.get("/cache/users/stats")
async def get_user_cache_stats():
    """Get user cache statistics."""
    try:
        user_keys = await cache.keys("user:*")
        user_list_keys = await cache.keys("users:list:*")
        
        return {
            "status": "success",
            "data": {
                "cached_users": len(user_keys),
                "cached_user_lists": len(user_list_keys),
                "total_user_cache_keys": len(user_keys) + len(user_list_keys)
            }
        }
    except Exception as e:
        logger.error(f"Failed to get user cache stats: {e}")
        raise HTTPException(status_code=500, detail=f"User cache stats error: {str(e)}")


@router.delete("/cache/users/invalidate")
async def invalidate_user_cache():
    """Invalidate all user-related cache."""
    try:
        user_deleted = await cache.flush_pattern("user:*")
        lists_deleted = await UserCache.invalidate_users_lists()
        
        return {
            "status": "success",
            "data": {
                "users_deleted": user_deleted,
                "lists_deleted": lists_deleted,
                "total_deleted": user_deleted + lists_deleted
            },
            "message": "User cache invalidated successfully"
        }
    except Exception as e:
        logger.error(f"Failed to invalidate user cache: {e}")
        raise HTTPException(status_code=500, detail=f"User cache invalidation error: {str(e)}")


# Session cache endpoints
@router.post("/cache/session/create")
async def create_test_session(
    user_id: str = Query(description="User ID for session"),
    ttl: int = Query(default=3600, description="Session TTL in seconds")
):
    """Create a test session."""
    try:
        session_id = str(uuid.uuid4())
        result = await SessionCache.create_session(session_id, user_id, ttl)
        
        if result:
            return {
                "status": "success",
                "data": {
                    "session_id": session_id,
                    "user_id": user_id,
                    "ttl": ttl,
                    "created": True
                },
                "message": "Test session created successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create session")
            
    except Exception as e:
        logger.error(f"Failed to create test session: {e}")
        raise HTTPException(status_code=500, detail=f"Session creation error: {str(e)}")


@router.get("/cache/session/{session_id}")
async def get_session_info(session_id: str):
    """Get session information."""
    try:
        session = await SessionCache.get_session(session_id)
        
        if session:
            return {
                "status": "success",
                "data": {
                    "session_id": session_id,
                    "session_data": session,
                    "found": True
                }
            }
        else:
            return {
                "status": "success",
                "data": {
                    "session_id": session_id,
                    "found": False
                },
                "message": "Session not found"
            }
            
    except Exception as e:
        logger.error(f"Failed to get session: {e}")
        raise HTTPException(status_code=500, detail=f"Get session error: {str(e)}")


@router.get("/cache/sessions/user/{user_id}")
async def get_user_sessions(user_id: str):
    """Get all sessions for a user."""
    try:
        sessions = await SessionCache.get_user_sessions(user_id)
        
        return {
            "status": "success",
            "data": {
                "user_id": user_id,
                "sessions": sessions,
                "session_count": len(sessions)
            }
        }
    except Exception as e:
        logger.error(f"Failed to get user sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Get user sessions error: {str(e)}")