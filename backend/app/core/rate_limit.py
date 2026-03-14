"""
LeadForge AI - Rate Limiting
Redis-based rate limiting for API endpoints
"""
from fastapi import Request, HTTPException, status
from typing import Optional
import time

from .redis import redis_client


class RateLimiter:
    """Redis-based rate limiter using sliding window"""

    def __init__(
        self,
        requests: int = 100,
        window: int = 60,
        key_prefix: str = "rate_limit"
    ):
        """
        Initialize rate limiter

        Args:
            requests: Number of requests allowed in the window
            window: Time window in seconds
            key_prefix: Prefix for Redis keys
        """
        self.requests = requests
        self.window = window
        self.key_prefix = key_prefix

    def _get_key(self, identifier: str) -> str:
        """Generate Redis key for rate limiting"""
        return f"{self.key_prefix}:{identifier}"

    def is_allowed(self, identifier: str) -> tuple[bool, dict]:
        """
        Check if request is allowed

        Returns:
            Tuple of (allowed, info_dict)
        """
        key = self._get_key(identifier)
        current_time = int(time.time())

        try:
            # Get current request count and window start
            data = redis_client.get_json(key)

            if data is None:
                # First request in window
                data = {
                    "count": 1,
                    "window_start": current_time
                }
                redis_client.set_json(key, data, self.window)
                return True, {
                    "remaining": self.requests - 1,
                    "reset": current_time + self.window,
                    "limit": self.requests
                }

            # Check if window has expired
            window_start = data["window_start"]
            if current_time - window_start >= self.window:
                # Reset window
                data = {
                    "count": 1,
                    "window_start": current_time
                }
                redis_client.set_json(key, data, self.window)
                return True, {
                    "remaining": self.requests - 1,
                    "reset": current_time + self.window,
                    "limit": self.requests
                }

            # Check if limit exceeded
            count = data["count"]
            if count >= self.requests:
                ttl = redis_client.ttl(key)
                return False, {
                    "remaining": 0,
                    "reset": current_time + ttl,
                    "limit": self.requests,
                    "retry_after": ttl
                }

            # Increment counter
            data["count"] = count + 1
            redis_client.set_json(key, data, redis_client.ttl(key))

            return True, {
                "remaining": self.requests - data["count"],
                "reset": window_start + self.window,
                "limit": self.requests
            }

        except Exception:
            # Fail open - allow request if Redis is down
            return True, {
                "remaining": self.requests,
                "reset": int(time.time()) + self.window,
                "limit": self.requests
            }

    def check_rate_limit(
        self,
        request: Request,
        identifier: Optional[str] = None
    ) -> None:
        """
        Check rate limit and raise exception if exceeded

        Args:
            request: FastAPI request object
            identifier: Unique identifier (defaults to client IP)
        """
        if identifier is None:
            identifier = request.client.host if request.client else "unknown"

        allowed, info = self.is_allowed(identifier)

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "retry_after": info.get("retry_after", 60),
                    "reset": info.get("reset")
                },
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info["reset"]),
                    "Retry-After": str(info.get("retry_after", 60))
                }
            )


# Predefined rate limiters
rate_limit_auth = RateLimiter(requests=5, window=60, key_prefix="auth")
rate_limit_api = RateLimiter(requests=100, window=60, key_prefix="api")
rate_limit_scrape = RateLimiter(requests=10, window=60, key_prefix="scrape")
rate_limit_email = RateLimiter(requests=20, window=60, key_prefix="email")
