"""
Redis Cache Management for Awasome FastAPI
Provides comprehensive caching functionality with Redis backend.
"""

import json
import pickle
import asyncio
from typing import Any, Optional, Union, Dict, List
from datetime import datetime, timedelta
from functools import wraps
import redis.asyncio as aioredis
from redis.asyncio import Redis
from app.models import User, UserOut
import logging

logger = logging.getLogger(__name__)

class RedisCache:
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        default_ttl: int = 3600,  # 1 hour default
        key_prefix: str = "awasome:"
    ):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self._redis: Optional[Redis] = None
        self._connection_pool = None

    async def connect(self) -> bool:
        """Initialize Redis connection."""
        try:
            self._connection_pool = aioredis.ConnectionPool.from_url(
                self.redis_url,
                decode_responses=False,
                encoding='utf-8',
                max_connections=20
            )
            self._redis = aioredis.Redis(connection_pool=self._connection_pool)
            
            # Test connection
            await self._redis.ping()
            logger.info(f"✅ Redis connected successfully to {self.redis_url}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            return False

    async def disconnect(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            logger.info("🔌 Redis connection closed")

    def _make_key(self, key: str) -> str:
        """Create a prefixed cache key."""
        return f"{self.key_prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with failsafe fallback."""
        if not self._redis:
            logger.debug("⚠️ Redis not connected - skipping cache get")
            return None
            
        try:
            cache_key = self._make_key(key)
            data = await self._redis.get(cache_key)
            
            if data is None:
                return None
                
            # Try to deserialize
            try:
                return pickle.loads(data)
            except (pickle.UnpicklingError, TypeError):
                # Fallback to string
                return data.decode('utf-8')
                
        except Exception as e:
            logger.warning(f"⚠️ Cache GET error for key '{key}' (continuing without cache): {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        serialize: bool = True
    ) -> bool:
        """Set value in cache with failsafe fallback."""
        if not self._redis:
            logger.debug("⚠️ Redis not connected - skipping cache set")
            return False
            
        try:
            cache_key = self._make_key(key)
            ttl = ttl or self.default_ttl
            
            # Serialize data
            if serialize:
                try:
                    data = pickle.dumps(value)
                except Exception as e:
                    logger.warning(f"⚠️ Serialization error for key '{key}' (skipping cache): {e}")
                    return False
            else:
                data = str(value).encode('utf-8')
            
            await self._redis.setex(cache_key, ttl, data)
            logger.debug(f"✅ Cache SET: '{key}' (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Cache SET error for key '{key}' (continuing without cache): {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache with failsafe fallback."""
        if not self._redis:
            logger.debug("⚠️ Redis not connected - skipping cache delete")
            return False
            
        try:
            cache_key = self._make_key(key)
            result = await self._redis.delete(cache_key)
            logger.debug(f"🗑️ Cache DELETE: '{key}' (found: {bool(result)})")
            return bool(result)
            
        except Exception as e:
            logger.warning(f"⚠️ Cache DELETE error for key '{key}' (continuing without cache): {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self._redis:
            return False
            
        try:
            cache_key = self._make_key(key)
            result = await self._redis.exists(cache_key)
            return bool(result)
            
        except Exception as e:
            logger.error(f"❌ Cache EXISTS error for key '{key}': {e}")
            return False

    async def ttl(self, key: str) -> int:
        """Get TTL for a key."""
        if not self._redis:
            return -1
            
        try:
            cache_key = self._make_key(key)
            return await self._redis.ttl(cache_key)
            
        except Exception as e:
            logger.error(f"❌ Cache TTL error for key '{key}': {e}")
            return -1

    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        if not self._redis:
            return []
            
        try:
            cache_pattern = self._make_key(pattern)
            keys = await self._redis.keys(cache_pattern)
            # Remove prefix from keys
            return [key.decode('utf-8').replace(self.key_prefix, '') for key in keys]
            
        except Exception as e:
            logger.error(f"❌ Cache KEYS error for pattern '{pattern}': {e}")
            return []

    async def flush_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern with failsafe fallback."""
        if not self._redis:
            logger.debug("⚠️ Redis not connected - skipping cache flush")
            return 0
            
        try:
            cache_pattern = self._make_key(pattern)
            keys = await self._redis.keys(cache_pattern)
            
            if keys:
                deleted = await self._redis.delete(*keys)
                logger.info(f"🗑️ Flushed {deleted} keys matching '{pattern}'")
                return deleted
            return 0
            
        except Exception as e:
            logger.warning(f"⚠️ Cache FLUSH error for pattern '{pattern}' (continuing): {e}")
            return 0

    async def flush_all(self) -> bool:
        """Delete all cache keys with our prefix."""
        if not self._redis:
            return False
            
        try:
            keys = await self._redis.keys(f"{self.key_prefix}*")
            if keys:
                deleted = await self._redis.delete(*keys)
                logger.info(f"🗑️ Flushed all cache ({deleted} keys)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Cache FLUSH_ALL error: {e}")
            return False

    async def get_info(self) -> Dict[str, Any]:
        """Get cache information."""
        if not self._redis:
            return {"status": "disconnected"}
            
        try:
            info = await self._redis.info()
            keys_count = len(await self._redis.keys(f"{self.key_prefix}*"))
            
            return {
                "status": "connected",
                "redis_version": info.get('redis_version'),
                "used_memory": info.get('used_memory_human'),
                "connected_clients": info.get('connected_clients'),
                "total_commands_processed": info.get('total_commands_processed'),
                "keyspace_hits": info.get('keyspace_hits', 0),
                "keyspace_misses": info.get('keyspace_misses', 0),
                "cache_keys_count": keys_count,
                "key_prefix": self.key_prefix,
                "default_ttl": self.default_ttl
            }
            
        except Exception as e:
            logger.error(f"❌ Cache INFO error: {e}")
            return {"status": "error", "error": str(e)}


# Global cache instance
cache = RedisCache()


def cache_result(key_template: str, ttl: Optional[int] = None):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from template
            try:
                cache_key = key_template.format(*args, **kwargs)
            except (KeyError, IndexError):
                cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"🎯 Cache HIT: {cache_key}")
                return cached_result
            
            # Execute function
            logger.debug(f"🔄 Cache MISS: {cache_key}")
            result = await func(*args, **kwargs)
            
            # Cache result
            await cache.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


class UserCache:
    """Specialized cache for User operations."""
    
    @staticmethod
    async def get_user(user_id: str) -> Optional[Dict[str, Any]]:
        """Get user from cache."""
        return await cache.get(f"user:{user_id}")
    
    @staticmethod
    async def set_user(user_id: str, user_data: Dict[str, Any], ttl: int = 1800) -> bool:
        """Cache user data (30 min default)."""
        return await cache.set(f"user:{user_id}", user_data, ttl)
    
    @staticmethod
    async def delete_user(user_id: str) -> bool:
        """Remove user from cache."""
        return await cache.delete(f"user:{user_id}")
    
    @staticmethod
    async def get_users_list(
        page: int = 1, 
        limit: int = 10, 
        filters: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached users list with filters."""
        filters = filters or {}
        # Create cache key from filters
        filter_key = "_".join([
            f"{k}:{v}" for k, v in sorted(filters.items()) 
            if v is not None
        ]) or "none"
        cache_key = f"users:list:{page}:{limit}:{filter_key}"
        return await cache.get(cache_key)
    
    @staticmethod
    async def set_users_list(
        users: Dict[str, Any], 
        page: int = 1, 
        limit: int = 10,
        ttl: int = 600,  # 10 min default
        filters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Cache users list with filters."""
        filters = filters or {}
        # Create cache key from filters
        filter_key = "_".join([
            f"{k}:{v}" for k, v in sorted(filters.items()) 
            if v is not None
        ]) or "none"
        cache_key = f"users:list:{page}:{limit}:{filter_key}"
        return await cache.set(cache_key, users, ttl)
    
    @staticmethod
    async def invalidate_users_lists() -> int:
        """Invalidate all cached user lists."""
        return await cache.flush_pattern("users:list:*")


class SessionCache:
    """Session management with Redis."""
    
    @staticmethod
    async def create_session(session_id: str, user_id: str, ttl: int = 86400) -> bool:
        """Create user session (24h default)."""
        session_data = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat()
        }
        return await cache.set(f"session:{session_id}", session_data, ttl)
    
    @staticmethod
    async def get_session(session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        session = await cache.get(f"session:{session_id}")
        if session:
            # Update last accessed
            session["last_accessed"] = datetime.utcnow().isoformat()
            await cache.set(f"session:{session_id}", session)
        return session
    
    @staticmethod
    async def delete_session(session_id: str) -> bool:
        """Delete session."""
        return await cache.delete(f"session:{session_id}")
    
    @staticmethod
    async def get_user_sessions(user_id: str) -> List[str]:
        """Get all sessions for a user."""
        session_keys = await cache.keys("session:*")
        user_sessions = []
        
        for session_key in session_keys:
            session_data = await cache.get(session_key)
            if session_data and session_data.get("user_id") == user_id:
                user_sessions.append(session_key.replace("session:", ""))
        
        return user_sessions


async def init_cache(redis_url: str = "redis://localhost:6379") -> bool:
    """Initialize cache connection."""
    cache.redis_url = redis_url
    return await cache.connect()


async def close_cache():
    """Close cache connection."""
    await cache.disconnect()


# Cache warming functions
async def warm_cache():
    """Warm up cache with frequently accessed data."""
    logger.info("🔥 Warming up cache...")
    
    try:
        # Example: Pre-cache system info
        system_info = {
            "service": "awasome-fastapi",
            "version": "1.0.0",
            "startup_time": datetime.utcnow().isoformat()
        }
        await cache.set("system:info", system_info, 86400)  # 24h
        
        logger.info("✅ Cache warming completed")
        
    except Exception as e:
        logger.error(f"❌ Cache warming failed: {e}")


# Testing utilities
async def test_cache_performance():
    """Test cache performance."""
    if not cache._redis:
        return {"error": "Redis not connected"}
    
    import time
    
    # Test write performance
    start_time = time.time()
    for i in range(100):
        await cache.set(f"test:perf:{i}", f"value_{i}", 60)
    write_time = time.time() - start_time
    
    # Test read performance  
    start_time = time.time()
    for i in range(100):
        await cache.get(f"test:perf:{i}")
    read_time = time.time() - start_time
    
    # Cleanup
    await cache.flush_pattern("test:perf:*")
    
    return {
        "write_100_keys": f"{write_time:.3f}s",
        "read_100_keys": f"{read_time:.3f}s",
        "writes_per_second": f"{100/write_time:.1f}",
        "reads_per_second": f"{100/read_time:.1f}"
    }