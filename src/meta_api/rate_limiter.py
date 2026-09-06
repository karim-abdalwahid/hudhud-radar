"""
Rate Limiter & Quota Protector for Meta Graph API.
Strictly prevents account bans by enforcing platform rate limits and sliding-window throttling.
"""
import json
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
        # Platform cooldown (seconds since epoch) triggered by high Meta usage headers
        self._cooldown_until: Dict[str, float] = {}

    def check_and_acquire(self, platform: str = "default") -> bool:
        """
        Validates whether a new API call is permitted right now.
        Raises RateLimitExceededError if rate limit is reached or a Meta-usage
        cooldown is active.
        """
        now = time.time()

        # Respect active cooldowns derived from real Meta usage headers
        cooldown_end = self._cooldown_until.get(platform, 0)
        if cooldown_end and now < cooldown_end:
            retry_after = int(cooldown_end - now) + 1
            logger.warning(f"Meta usage cooldown active for '{platform}' ({retry_after}s remaining)")
            raise RateLimitExceededError(platform=platform, retry_after=retry_after)

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

    def _parse_usage(self, raw: str) -> Dict[str, float]:
        """Safely parses Meta usage header JSON (e.g. X-App-Usage)."""
        try:
            data = json.loads(raw)
            return {k: float(v) for k, v in data.items() if isinstance(v, (int, float))}
        except Exception:
            return {}

    def _extract_max_usage(self, usage: Dict[str, float]) -> float:
        """Finds the dominant usage percentage from a usage dict."""
        if not usage:
            return 0.0
        candidates = [
            usage.get("call_count", 0.0),
            usage.get("total_cputime", 0.0),
            usage.get("total_time", 0.0),
        ]
        return max(candidates)

    def update_from_headers(self, platform: str, headers: Dict[str, str]):
        """
        Parses Meta response headers (X-App-Usage, X-Page-Usage, X-Business-Use-Case-Usage)
        and applies protective throttling:
        - >= 80% usage: warning logged.
        - >= 95% usage: 60s platform cooldown enforced by check_and_acquire().
        """
        lower_headers = {k.lower(): v for k, v in (headers or {}).items()}
        max_usage = 0.0

        for header_name in ("x-app-usage", "x-page-usage", "x-business-use-case-usage"):
            raw = lower_headers.get(header_name)
            if not raw:
                continue
            if header_name == "x-business-use-case-usage":
                # Structure: {"<object_id>": {"call_count": n, ...}, ...}
                try:
                    bundled = json.loads(raw)
                    for object_usage in bundled.values() if isinstance(bundled, dict) else []:
                        if isinstance(object_usage, dict):
                            pct = self._extract_max_usage(
                                {k: v for k, v in object_usage.items() if isinstance(v, (int, float))}
                            )
                            max_usage = max(max_usage, pct)
                except Exception:
                    pass
            else:
                max_usage = max(max_usage, self._extract_max_usage(self._parse_usage(raw)))

        if max_usage >= 95.0:
            self._cooldown_until[platform] = time.time() + 60.0
            logger.error(
                f"[{platform}] Meta usage CRITICAL: {max_usage:.0f}% — enforcing 60s protective cooldown."
            )
        elif max_usage >= 80.0:
            logger.warning(f"[{platform}] Meta usage high: {max_usage:.0f}% — consider slowing outbound traffic.")


rate_limiter = PlatformRateLimiter()
