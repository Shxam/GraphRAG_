"""
Redis Query Cache for TigerGraph GSQL queries
Falls back to in-memory cache if Redis is unavailable
"""

import json
import time
import os
from typing import Any, Callable, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# Try to import redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("Warning: redis package not installed. Using in-memory cache.")


class QueryCache:
    """Cache for GSQL query results with Redis and in-memory fallback"""
    
    def __init__(self, redis_url: str = None):
        """
        Initialize cache
        
        Args:
            redis_url: Redis connection URL (default from REDIS_URL env var)
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = None
        self.memory_cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)
        self.hits = 0
        self.misses = 0
        
        # Try to connect to Redis
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2
                )
                # Test connection
                self.redis_client.ping()
                print("✓ Connected to Redis cache")
            except Exception as e:
                print(f"Redis unavailable, using in-memory cache: {e}")
                self.redis_client = None
    
    def cached_gsql(
        self,
        query_key: str,
        fetch_fn: Callable[[], Any],
        ttl: int = 300
    ) -> Any:
        """
        Execute GSQL query with caching
        
        Args:
            query_key: Unique key for this query
            fetch_fn: Function to call if cache miss
            ttl: Time-to-live in seconds (default 300)
            
        Returns:
            Query result (from cache or fresh)
        """
        # Try to get from cache
        cached_value = self._get(query_key)
        
        if cached_value is not None:
            self.hits += 1
            return cached_value
        
        # Cache miss - fetch fresh data
        self.misses += 1
        result = fetch_fn()
        
        # Store in cache
        self._set(query_key, result, ttl)
        
        return result
    
    def _get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        # Try Redis first
        if self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                print(f"Redis get error: {e}")
        
        # Fall back to memory cache
        if key in self.memory_cache:
            value, expiry = self.memory_cache[key]
            if time.time() < expiry:
                return value
            else:
                # Expired
                del self.memory_cache[key]
        
        return None
    
    def _set(self, key: str, value: Any, ttl: int):
        """Set value in cache"""
        serialized = json.dumps(value)
        
        # Try Redis first
        if self.redis_client:
            try:
                self.redis_client.setex(key, ttl, serialized)
                return
            except Exception as e:
                print(f"Redis set error: {e}")
        
        # Fall back to memory cache
        expiry_time = time.time() + ttl
        self.memory_cache[key] = (value, expiry_time)
        
        # Clean up expired entries periodically
        self._cleanup_memory_cache()
    
    def _cleanup_memory_cache(self):
        """Remove expired entries from memory cache"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, expiry) in self.memory_cache.items()
            if current_time >= expiry
        ]
        for key in expired_keys:
            del self.memory_cache[key]
    
    def cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with hits, misses, hit_rate_pct
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0.0
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_pct": round(hit_rate, 2),
            "backend": "redis" if self.redis_client else "memory"
        }
    
    def clear(self):
        """Clear all cache entries"""
        if self.redis_client:
            try:
                self.redis_client.flushdb()
            except Exception as e:
                print(f"Redis clear error: {e}")
        
        self.memory_cache.clear()


# Global cache instance
_cache_instance = None


def get_cache() -> QueryCache:
    """Get or create global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = QueryCache()
    return _cache_instance


def cached_gsql(query_key: str, fetch_fn: Callable[[], Any], ttl: int = 300) -> Any:
    """
    Convenience function for caching GSQL queries
    
    Args:
        query_key: Unique key for this query
        fetch_fn: Function to call if cache miss
        ttl: Time-to-live in seconds
        
    Returns:
        Query result
    """
    cache = get_cache()
    return cache.cached_gsql(query_key, fetch_fn, ttl)


def cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    cache = get_cache()
    return cache.cache_stats()


if __name__ == "__main__":
    # Test the cache
    cache = QueryCache()
    
    def expensive_query():
        print("Executing expensive query...")
        time.sleep(1)
        return {"result": "data", "timestamp": time.time()}
    
    # First call - cache miss
    print("First call:")
    result1 = cache.cached_gsql("test_query", expensive_query, ttl=10)
    print(f"Result: {result1}")
    print(f"Stats: {cache.cache_stats()}")
    
    # Second call - cache hit
    print("\nSecond call:")
    result2 = cache.cached_gsql("test_query", expensive_query, ttl=10)
    print(f"Result: {result2}")
    print(f"Stats: {cache.cache_stats()}")
    
    # Different key - cache miss
    print("\nDifferent key:")
    result3 = cache.cached_gsql("other_query", expensive_query, ttl=10)
    print(f"Result: {result3}")
    print(f"Stats: {cache.cache_stats()}")
