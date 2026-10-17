"""Rate-limit dependencies for routes. Health probes deliberately have none."""

from collections.abc import Callable

from fastapi import Depends, Request, Response

from app.core.config import Settings
from app.core.constants import RateLimitBucket
from app.core.exceptions import RateLimitExceededError
from app.core.rate_limit import RateLimiter, parse_limit

UNKNOWN_CLIENT = "unknown"


def client_ip(request: Request) -> str:
    # Uvicorn has already resolved X-Forwarded-For for trusted proxies (see
    # --forwarded-allow-ips), so the header is never parsed here as well.
    return request.client.host if request.client else UNKNOWN_CLIENT


def _limit(bucket: RateLimitBucket) -> Callable[[Request, Response], None]:
    def enforce(request: Request, response: Response) -> None:
        limiter: RateLimiter | None = request.app.state.rate_limiter
        if limiter is None:
            return
        settings: Settings = request.app.state.settings
        limit = parse_limit(settings.rate_limit_for(bucket))
        result = limiter.hit(limit, bucket, client_ip(request))
        if not result.allowed:
            raise RateLimitExceededError(result.retry_after_seconds, result.headers())
        response.headers.update(result.headers())

    return enforce


ReadRateLimit = Depends(_limit(RateLimitBucket.READ))
WriteRateLimit = Depends(_limit(RateLimitBucket.WRITE))
