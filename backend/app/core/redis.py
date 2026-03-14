"""
LeadForge AI - Redis Configuration
Used for caching, rate limiting, and Celery queues
"""
import redis
from typing import Optional
import json

from .config import settings


class RedisClient:
    """Redis client wrapper"""

    def __init__(self):
        self._client: Optional[redis.Redis] = None

    @property
    def client(self) -> redis.Redis:
        """Get or create Redis client"""
        if self._client is None:
            self._client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
        return self._client

    def ping(self) -> bool:
        """Check Redis connection"""
        try:
            return self.client.ping()
        except redis.ConnectionError:
            return False

    def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        try:
            return self.client.get(key)
        except redis.RedisError:
            return None

    def set(
        self,
        key: str,
        value: str,
        expire: Optional[int] = None
    ) -> bool:
        """Set value in Redis"""
        try:
            return self.client.set(key, value, ex=expire)
        except redis.RedisError:
            return False

    def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        try:
            return bool(self.client.delete(key))
        except redis.RedisError:
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return bool(self.client.exists(key))
        except redis.RedisError:
            return False

    def get_json(self, key: str) -> Optional[dict]:
        """Get JSON value from Redis"""
        value = self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    def set_json(
        self,
        key: str,
        value: dict,
        expire: Optional[int] = None
    ) -> bool:
        """Set JSON value in Redis"""
        try:
            return self.set(key, json.dumps(value), expire)
        except (json.JSONEncodeError, TypeError):
            return False

    def incr(self, key: str) -> int:
        """Increment counter"""
        try:
            return self.client.incr(key)
        except redis.RedisError:
            return 0

    def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key"""
        try:
            return self.client.expire(key, seconds)
        except redis.RedisError:
            return False

    def ttl(self, key: str) -> int:
        """Get time to live for key"""
        try:
            return self.client.ttl(key)
        except redis.RedisError:
            return -1


# Global Redis client instance
redis_client = RedisClient()
