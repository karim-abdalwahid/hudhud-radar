"""
Unit Tests for Rate Limiter and Platform Quota Protections.
"""
import pytest
import time
from src.meta_api.rate_limiter import PlatformRateLimiter
from src.core.exceptions import RateLimitExceededError


def test_rate_limiter_allows_under_threshold():
    """Verify that requests under the threshold pass immediately."""
    limiter = PlatformRateLimiter(max_requests_per_minute=5)
    for _ in range(5):
        assert limiter.check_and_acquire("facebook") is True


def test_rate_limiter_blocks_above_threshold():
    """Verify that exceeding the threshold raises RateLimitExceededError with retry_after."""
    limiter = PlatformRateLimiter(max_requests_per_minute=3)
    for _ in range(3):
        limiter.check_and_acquire("instagram")

    with pytest.raises(RateLimitExceededError) as exc_info:
        limiter.check_and_acquire("instagram")

    assert exc_info.value.platform == "instagram"
    assert exc_info.value.retry_after > 0


def test_rate_limiter_independent_platforms():
    """Verify that hitting limit on Facebook does not block Instagram."""
    limiter = PlatformRateLimiter(max_requests_per_minute=2)
    limiter.check_and_acquire("facebook")
    limiter.check_and_acquire("facebook")

    # Facebook is now at capacity
    with pytest.raises(RateLimitExceededError):
        limiter.check_and_acquire("facebook")

    # Instagram must still be available
    assert limiter.check_and_acquire("instagram") is True
