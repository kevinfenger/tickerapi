from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import json
import os
import redis
from redis.exceptions import ConnectionError, RedisError

def get_redis_client():
    """Get Redis client connection"""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    return redis.from_url(redis_url, decode_responses=True)

class Cache:
    def __init__(self, expiration_minutes: int = 5):
        self.expiration_time = timedelta(minutes=expiration_minutes)
        try:
            self.redis_client = get_redis_client()
            self.redis_client.ping()  # Test connection
            self.use_redis = True
        except (ConnectionError, RedisError):
            # Fall back to in-memory cache if Redis unavailable
            self.use_redis = False
            self.cache: Dict[str, Any] = {}
            self.last_updated: Dict[str, datetime] = {}

    def set(self, key: str, value: Any, expiration_minutes: int = None) -> None:
        if self.use_redis:
            try:
                # Use custom expiration or default
                expiration = expiration_minutes if expiration_minutes else self.expiration_time.total_seconds() / 60
                expiration_seconds = int(expiration * 60)
                
                # Store as JSON string
                serialized_value = json.dumps(value) if not isinstance(value, str) else value
                self.redis_client.setex(key, expiration_seconds, serialized_value)
                return
            except (ConnectionError, RedisError):
                self.use_redis = False
        
        # Fall back to in-memory cache
        self.cache[key] = value
        # Use custom expiration or default
        expiration = timedelta(minutes=expiration_minutes) if expiration_minutes else self.expiration_time
        self.last_updated[key] = datetime.now()
        # Store custom expiration time for this key
        if not hasattr(self, 'custom_expirations'):
            self.custom_expirations = {}
        self.custom_expirations[key] = expiration

    def get(self, key: str) -> Optional[Any]:
        if self.use_redis:
            try:
                value = self.redis_client.get(key)
                if value is not None:
                    # Try to parse as JSON, fall back to string
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value
                return None
            except (ConnectionError, RedisError):
                self.use_redis = False
        
        # Fall back to in-memory cache
        if key in self.cache:
            # Check if we have custom expiration for this key
            expiration_time = getattr(self, 'custom_expirations', {}).get(key, self.expiration_time)
            
            if datetime.now() - self.last_updated[key] < expiration_time:
                return self.cache[key]
            else:
                self.invalidate(key)
        return None

    def invalidate(self, key: str) -> None:
        if self.use_redis:
            try:
                self.redis_client.delete(key)
                return
            except (ConnectionError, RedisError):
                self.use_redis = False
        
        # Fall back to in-memory cache
        if key in self.cache:
            del self.cache[key]
            del self.last_updated[key]

    def clear(self) -> None:
        if self.use_redis:
            try:
                self.redis_client.flushdb()
                return
            except (ConnectionError, RedisError):
                self.use_redis = False
        
        # Fall back to in-memory cache
        self.cache.clear()
        self.last_updated.clear()