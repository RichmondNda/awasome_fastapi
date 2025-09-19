"""
Performance monitoring and testing endpoints for cache vs database.
Provides detailed metrics and comparison tools.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Query, Body
from app.cache import cache, UserCache
from app.services.user import get_user_service
from app.core.logging import get_logger
from app.schemas.user import PaginationParams, UserStatus
import time
import asyncio
import statistics
from datetime import datetime

logger = get_logger(__name__)

router = APIRouter()


@router.get("/performance/cache-vs-db", response_model=Dict[str, Any])
async def compare_cache_vs_db():
    """
    Compare performance between cache and database access.
    
    Returns:
        Detailed performance metrics comparing cache vs database operations
    """
    try:
        results = {
            "test_timestamp": datetime.utcnow().isoformat(),
            "cache_tests": {},
            "database_tests": {},
            "comparison": {}
        }
        
        # Test 1: Single user retrieval (if users exist)
        user_service = get_user_service()
        try:
            # Get first user for testing
            users_list = user_service.list_users(PaginationParams(skip=0, limit=1))
            if users_list.items:
                test_user_id = users_list.items[0].id
                
                # Database access test
                db_times = []
                for _ in range(10):
                    start_time = time.time()
                    user_service.get_user(test_user_id)
                    db_times.append(time.time() - start_time)
                
                # Cache the user first
                user = user_service.get_user(test_user_id)
                user_dict = user.model_dump()
                await UserCache.set_user(test_user_id, user_dict)
                
                # Cache access test
                cache_times = []
                for _ in range(10):
                    start_time = time.time()
                    await UserCache.get_user(test_user_id)
                    cache_times.append(time.time() - start_time)
                
                results["cache_tests"]["single_user_retrieval"] = {
                    "iterations": 10,
                    "avg_time": statistics.mean(cache_times),
                    "min_time": min(cache_times),
                    "max_time": max(cache_times),
                    "median_time": statistics.median(cache_times)
                }
                
                results["database_tests"]["single_user_retrieval"] = {
                    "iterations": 10,
                    "avg_time": statistics.mean(db_times),
                    "min_time": min(db_times),
                    "max_time": max(db_times),
                    "median_time": statistics.median(db_times)
                }
                
                results["comparison"]["single_user_retrieval"] = {
                    "speedup": statistics.mean(db_times) / statistics.mean(cache_times),
                    "time_saved": statistics.mean(db_times) - statistics.mean(cache_times),
                    "cache_efficiency": f"{((statistics.mean(db_times) - statistics.mean(cache_times)) / statistics.mean(db_times)) * 100:.2f}%"
                }
                
        except Exception as e:
            logger.warning(f"User retrieval test failed: {e}")
            results["cache_tests"]["single_user_retrieval"] = {"error": str(e)}
            results["database_tests"]["single_user_retrieval"] = {"error": str(e)}
        
        # Test 2: Users list retrieval
        try:
            # Database access test
            db_times = []
            for _ in range(5):  # Fewer iterations for list operations
                start_time = time.time()
                user_service.list_users(PaginationParams(skip=0, limit=10))
                db_times.append(time.time() - start_time)
            
            # Cache the list first
            users_list = user_service.list_users(PaginationParams(skip=0, limit=10))
            list_dict = users_list.model_dump()
            await UserCache.set_users_list(list_dict, page=1, limit=10)
            
            # Cache access test
            cache_times = []
            for _ in range(5):
                start_time = time.time()
                await UserCache.get_users_list(page=1, limit=10)
                cache_times.append(time.time() - start_time)
            
            results["cache_tests"]["users_list_retrieval"] = {
                "iterations": 5,
                "avg_time": statistics.mean(cache_times),
                "min_time": min(cache_times),
                "max_time": max(cache_times),
                "median_time": statistics.median(cache_times)
            }
            
            results["database_tests"]["users_list_retrieval"] = {
                "iterations": 5,
                "avg_time": statistics.mean(db_times),
                "min_time": min(db_times),
                "max_time": max(db_times),
                "median_time": statistics.median(db_times)
            }
            
            results["comparison"]["users_list_retrieval"] = {
                "speedup": statistics.mean(db_times) / statistics.mean(cache_times),
                "time_saved": statistics.mean(db_times) - statistics.mean(cache_times),
                "cache_efficiency": f"{((statistics.mean(db_times) - statistics.mean(cache_times)) / statistics.mean(db_times)) * 100:.2f}%"
            }
            
        except Exception as e:
            logger.warning(f"Users list test failed: {e}")
            results["cache_tests"]["users_list_retrieval"] = {"error": str(e)}
            results["database_tests"]["users_list_retrieval"] = {"error": str(e)}
        
        # Test 3: Cache operations performance
        try:
            cache_ops_times = {
                "set": [],
                "get": [],
                "delete": []
            }
            
            # SET performance
            for i in range(20):
                start_time = time.time()
                await cache.set(f"perf_test_{i}", {"test": f"data_{i}"}, 60)
                cache_ops_times["set"].append(time.time() - start_time)
            
            # GET performance
            for i in range(20):
                start_time = time.time()
                await cache.get(f"perf_test_{i}")
                cache_ops_times["get"].append(time.time() - start_time)
            
            # DELETE performance
            for i in range(20):
                start_time = time.time()
                await cache.delete(f"perf_test_{i}")
                cache_ops_times["delete"].append(time.time() - start_time)
            
            results["cache_tests"]["operations"] = {
                "set": {
                    "iterations": 20,
                    "avg_time": statistics.mean(cache_ops_times["set"]),
                    "ops_per_second": 20 / sum(cache_ops_times["set"])
                },
                "get": {
                    "iterations": 20,
                    "avg_time": statistics.mean(cache_ops_times["get"]),
                    "ops_per_second": 20 / sum(cache_ops_times["get"])
                },
                "delete": {
                    "iterations": 20,
                    "avg_time": statistics.mean(cache_ops_times["delete"]),
                    "ops_per_second": 20 / sum(cache_ops_times["delete"])
                }
            }
            
        except Exception as e:
            logger.warning(f"Cache operations test failed: {e}")
            results["cache_tests"]["operations"] = {"error": str(e)}
        
        # Overall cache info
        cache_info = await cache.get_info()
        results["cache_info"] = cache_info
        
        return {
            "status": "success",
            "data": results,
            "message": "Performance comparison completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Performance test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Performance test error: {str(e)}")


@router.get("/performance/load-test", response_model=Dict[str, Any])
async def cache_load_test(
    operations: int = Query(default=100, ge=10, le=1000, description="Number of operations to perform"),
    concurrent_users: int = Query(default=10, ge=1, le=50, description="Number of concurrent operations")
):
    """
    Perform a load test on the cache system.
    
    Args:
        operations: Total number of operations to perform
        concurrent_users: Number of concurrent operations
        
    Returns:
        Load test results with performance metrics
    """
    try:
        start_time = time.time()
        
        async def perform_operations(user_id: int, ops_count: int):
            """Perform a set of cache operations for a simulated user."""
            user_times = []
            for i in range(ops_count):
                op_start = time.time()
                
                # Mix of operations
                key = f"load_test_user_{user_id}_item_{i}"
                
                # SET operation
                await cache.set(key, {"user": user_id, "item": i, "timestamp": time.time()}, 300)
                
                # GET operation
                await cache.get(key)
                
                # Randomly delete some items
                if i % 3 == 0:
                    await cache.delete(key)
                
                user_times.append(time.time() - op_start)
            
            return user_times
        
        # Calculate operations per user
        ops_per_user = operations // concurrent_users
        
        # Run concurrent operations
        tasks = []
        for user_id in range(concurrent_users):
            task = perform_operations(user_id, ops_per_user)
            tasks.append(task)
        
        # Execute all tasks concurrently
        results_per_user = await asyncio.gather(*tasks)
        
        # Calculate overall statistics
        all_times = []
        for user_times in results_per_user:
            all_times.extend(user_times)
        
        total_time = time.time() - start_time
        
        # Cleanup test data
        await cache.flush_pattern("load_test_user_*")
        
        return {
            "status": "success",
            "data": {
                "test_parameters": {
                    "total_operations": len(all_times),
                    "concurrent_users": concurrent_users,
                    "operations_per_user": ops_per_user
                },
                "performance_metrics": {
                    "total_time": total_time,
                    "operations_per_second": len(all_times) / total_time,
                    "avg_operation_time": statistics.mean(all_times),
                    "min_operation_time": min(all_times),
                    "max_operation_time": max(all_times),
                    "median_operation_time": statistics.median(all_times),
                    "95th_percentile": sorted(all_times)[int(0.95 * len(all_times))]
                },
                "concurrent_performance": {
                    "users_completed": len(results_per_user),
                    "avg_time_per_user": [statistics.mean(times) for times in results_per_user]
                }
            },
            "message": f"Load test completed: {len(all_times)} operations in {total_time:.2f}s"
        }
        
    except Exception as e:
        logger.error(f"Load test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Load test error: {str(e)}")


@router.get("/performance/cache-hit-ratio", response_model=Dict[str, Any])
async def get_cache_hit_ratio():
    """
    Get cache hit ratio and statistics.
    
    Returns:
        Cache hit ratio and performance statistics
    """
    try:
        cache_info = await cache.get_info()
        
        if cache_info.get("status") != "connected":
            raise HTTPException(status_code=503, detail="Cache not available")
        
        hits = cache_info.get("keyspace_hits", 0)
        misses = cache_info.get("keyspace_misses", 0)
        total = hits + misses
        
        hit_ratio = (hits / total * 100) if total > 0 else 0
        miss_ratio = (misses / total * 100) if total > 0 else 0
        
        return {
            "status": "success",
            "data": {
                "cache_statistics": {
                    "hits": hits,
                    "misses": misses,
                    "total_operations": total,
                    "hit_ratio_percent": round(hit_ratio, 2),
                    "miss_ratio_percent": round(miss_ratio, 2)
                },
                "cache_efficiency": {
                    "rating": (
                        "Excellent" if hit_ratio >= 90 else
                        "Good" if hit_ratio >= 80 else
                        "Fair" if hit_ratio >= 70 else
                        "Poor"
                    ),
                    "recommendation": (
                        "Cache is performing optimally" if hit_ratio >= 90 else
                        "Consider increasing TTL values" if hit_ratio >= 70 else
                        "Review caching strategy"
                    )
                },
                "redis_info": {
                    "version": cache_info.get("redis_version"),
                    "memory_used": cache_info.get("used_memory"),
                    "connected_clients": cache_info.get("connected_clients"),
                    "total_commands": cache_info.get("total_commands_processed"),
                    "cache_keys": cache_info.get("cache_keys_count")
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Cache hit ratio calculation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cache statistics error: {str(e)}")


@router.post("/performance/warmup-cache", response_model=Dict[str, Any])
async def warmup_cache():
    """
    Warm up the cache by pre-loading frequently accessed data.
    
    Returns:
        Cache warming results and statistics
    """
    try:
        start_time = time.time()
        warmed_items = 0
        
        user_service = get_user_service()
        
        # Warm up user lists (first few pages)
        try:
            for page in range(1, 4):  # First 3 pages
                users_list = user_service.list_users(PaginationParams(skip=(page-1)*10, limit=10))
                list_dict = users_list.model_dump()
                await UserCache.set_users_list(list_dict, page=page, limit=10, ttl=1800)
                warmed_items += 1
                logger.info(f"Warmed up users list page {page}")
        except Exception as e:
            logger.warning(f"Failed to warm up users lists: {e}")
        
        # Warm up individual users (most recent ones)
        try:
            recent_users = user_service.list_users(PaginationParams(skip=0, limit=20))
            for user in recent_users.items:
                user_dict = user.model_dump()
                await UserCache.set_user(user.id, user_dict, ttl=1800)
                warmed_items += 1
            logger.info(f"Warmed up {len(recent_users.items)} individual users")
        except Exception as e:
            logger.warning(f"Failed to warm up individual users: {e}")
        
        # Add system info to cache
        try:
            system_info = {
                "service": "awasome-fastapi",
                "version": "1.0.0",
                "cache_warmed_at": datetime.utcnow().isoformat(),
                "warmed_items": warmed_items
            }
            await cache.set("system:cache_warmup", system_info, 3600)
            warmed_items += 1
        except Exception as e:
            logger.warning(f"Failed to cache system info: {e}")
        
        total_time = time.time() - start_time
        
        return {
            "status": "success",
            "data": {
                "warmup_statistics": {
                    "items_warmed": warmed_items,
                    "time_taken": round(total_time, 3),
                    "items_per_second": round(warmed_items / total_time, 2)
                },
                "cache_status": await cache.get_info()
            },
            "message": f"Cache warmed up successfully: {warmed_items} items in {total_time:.2f}s"
        }
        
    except Exception as e:
        logger.error(f"Cache warmup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cache warmup error: {str(e)}")


@router.delete("/performance/clear-test-data", response_model=Dict[str, Any])
async def clear_test_data():
    """
    Clear all test data from cache.
    
    Returns:
        Cleanup results
    """
    try:
        patterns_to_clear = [
            "perf_test_*",
            "load_test_*",
            "test:*"
        ]
        
        total_cleared = 0
        for pattern in patterns_to_clear:
            cleared = await cache.flush_pattern(pattern)
            total_cleared += cleared
            logger.info(f"Cleared {cleared} keys matching '{pattern}'")
        
        return {
            "status": "success",
            "data": {
                "cleared_keys": total_cleared,
                "patterns_cleared": patterns_to_clear
            },
            "message": f"Cleared {total_cleared} test keys from cache"
        }
        
    except Exception as e:
        logger.error(f"Test data cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup error: {str(e)}")