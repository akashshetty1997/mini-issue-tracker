"""Rate limiting with a shared store and an in-memory fallback.

Counters live in Redis so every API worker and replica enforces the same limit for a
client. If Redis becomes unreachable, the limiter degrades instead of failing: it keeps
counting in process memory (limits then apply per worker, so the effective limit becomes
roughly workers x limit) and periodically checks whether Redis is back.
"""

import logging
import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache

from limits import RateLimitItem, parse
from limits.storage import MemoryStorage, Storage, storage_from_string
from limits.strategies import SlidingWindowCounterRateLimiter

from app.core.constants import (
    RATE_LIMIT_HEADER_LIMIT,
    RATE_LIMIT_HEADER_REMAINING,
    RATE_LIMIT_HEADER_RESET,
    RATE_LIMIT_RECOVERY_INTERVAL_SECONDS,
    RATE_LIMIT_STORAGE_TIMEOUT_SECONDS,
    RETRY_AFTER_HEADER,
)

logger = logging.getLogger(__name__)


@lru_cache
def parse_limit(limit: str) -> RateLimitItem:
    """Parse "30/minute"-style strings once."""
    return parse(limit)


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_at: float  # epoch seconds when the window frees up

    @property
    def retry_after_seconds(self) -> int:
        return max(1, math.ceil(self.reset_at - time.time()))

    def headers(self) -> dict[str, str]:
        headers = {
            RATE_LIMIT_HEADER_LIMIT: str(self.limit),
            RATE_LIMIT_HEADER_REMAINING: str(self.remaining),
            RATE_LIMIT_HEADER_RESET: str(math.ceil(self.reset_at)),
        }
        if not self.allowed:
            headers[RETRY_AFTER_HEADER] = str(self.retry_after_seconds)
        return headers


class RateLimiter:
    def __init__(
        self,
        primary: Storage,
        fallback: Storage | None = None,
        *,
        recovery_interval_seconds: float = RATE_LIMIT_RECOVERY_INTERVAL_SECONDS,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._primary = SlidingWindowCounterRateLimiter(primary)
        self._fallback = SlidingWindowCounterRateLimiter(fallback or MemoryStorage())
        self._primary_storage = primary
        self._recovery_interval = recovery_interval_seconds
        self._monotonic = monotonic
        self._lock = threading.Lock()
        self._degraded = False
        self._next_recovery_check = 0.0

    @classmethod
    def from_uri(cls, storage_uri: str) -> "RateLimiter":
        options: dict[str, float | str | bool] = {}
        if storage_uri.startswith("redis"):
            # Fail fast: a slow Redis must not add seconds to every request.
            options = {
                "socket_connect_timeout": RATE_LIMIT_STORAGE_TIMEOUT_SECONDS,
                "socket_timeout": RATE_LIMIT_STORAGE_TIMEOUT_SECONDS,
            }
        storage = storage_from_string(storage_uri, **options)
        if not isinstance(storage, Storage):
            raise ValueError(f"Async storage is not supported: {storage_uri}")
        return cls(storage)

    @property
    def degraded(self) -> bool:
        return self._degraded

    def storage_healthy(self) -> bool:
        return self._primary_storage.check()

    def hit(self, item: RateLimitItem, *identifiers: str) -> RateLimitResult:
        """Consume one request from the window identified by ``identifiers``."""
        if self._should_use_primary():
            try:
                return self._hit(self._primary, item, identifiers)
            except self._primary_storage.base_exceptions:
                self._enter_degraded_mode()
        return self._hit(self._fallback, item, identifiers)

    @staticmethod
    def _hit(
        strategy: SlidingWindowCounterRateLimiter, item: RateLimitItem, identifiers: tuple[str, ...]
    ) -> RateLimitResult:
        allowed = strategy.hit(item, *identifiers)
        stats = strategy.get_window_stats(item, *identifiers)
        return RateLimitResult(
            allowed=allowed, limit=item.amount, remaining=stats.remaining, reset_at=stats.reset_time
        )

    def _should_use_primary(self) -> bool:
        if not self._degraded:
            return True
        with self._lock:
            if self._monotonic() < self._next_recovery_check:
                return False
            self._next_recovery_check = self._monotonic() + self._recovery_interval
        if self.storage_healthy():
            self._degraded = False
            logger.warning("Rate limit storage recovered; using shared counters again")
            return True
        return False

    def _enter_degraded_mode(self) -> None:
        with self._lock:
            if self._degraded:
                return
            self._degraded = True
            self._next_recovery_check = self._monotonic() + self._recovery_interval
        logger.error(
            "Rate limit storage unreachable; falling back to per-process in-memory limits",
            exc_info=True,
        )
