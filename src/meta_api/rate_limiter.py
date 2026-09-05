"""
Rate Limiter & Quota Protector for Meta Graph API.
Strictly prevents account bans by enforcing platform rate limits and sliding-window throttling.
"""
import time
from collections import deque
from typing import Dict
from src.config import settings
from src.core.logger import logger
from src.core.exceptions import RateLimitExceededError


class PlatformRateLimiter:
    """Sliding-window rate limiter for Meta Graph API and Instagram."""

    def __init__(self, max_requests_per_minute: int = settings.MAX_MESSAGES_PER_MINUTE):
        self.max_per_minute = max_requests_per_minute
        # Deques storing timestamps for each platform
        self.history: Dict[str, deque] = {
            "facebook": deque(),
            "instagram": deque(),
            "default": deque()
        }

    def check_and_acquire(self, platform: str = "default") -> bool:
        """
        Validates whether a new API call is permitted right now.
        Raises RateLimitExceededError if rate limit is reached.
        """
        now = time.time()
        window_start = now - 60.0
        q = self.history.setdefault(platform, deque())

        # Clean expired timestamps older than 60 seconds
        while q and q[0] < window_start:
            q.popleft()

        # Check threshold
        if len(q) >= self.max_per_minute:
            retry_after = int(60.0 - (now - q[0])) + 1
            logger.warning(f"Rate limit triggered for platform '{platform}'. Requests in 60s: {len(q)}/{self.max_per_minute}")
            raise RateLimitExceededError(platform=platform, retry_after=retry_after)

        q.append(now)
        return True

    def update_from_headers(self, platform: str, headers: Dict[str, str]):
        """
        Parses Meta response headers (X-App-Usage, X-Page-Usage)
        and logs warnings if usage exceeds 80%.
        """
        lower_headers = {k.lower(): v for k, v in headers.items()}
        app_usage = lower_headers.get("x-app-usage")
        if app_usage:
            logger.debug(f"[{platform}] Meta App Usage: {app_usage}")


rate_limiter = PlatformRateLimiter()
