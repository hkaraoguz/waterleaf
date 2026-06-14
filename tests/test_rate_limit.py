from waterleaf.rate_limit import SlidingWindowRateLimiter


def test_rate_limiter_blocks_after_limit_inside_window():
    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=60)

    assert limiter.allow("203.0.113.10", now=100.0) is True
    assert limiter.allow("203.0.113.10", now=110.0) is True
    assert limiter.allow("203.0.113.10", now=120.0) is False


def test_rate_limiter_expires_old_attempts():
    limiter = SlidingWindowRateLimiter(limit=1, window_seconds=60)

    assert limiter.allow("203.0.113.10", now=100.0) is True
    assert limiter.allow("203.0.113.10", now=161.0) is True

