"""RateLimiter behaviour, including degrading to memory when the shared store fails and
switching back once it recovers."""

from typing import Any

import pytest
from limits import parse
from limits.storage import MemoryStorage

from app.core.rate_limit import RateLimiter

LIMIT = parse("3/minute")


class FlakyStorage(MemoryStorage):
    """In-memory storage that can be switched off to simulate a Redis outage."""

    def __init__(self) -> None:
        super().__init__()
        self.down = False
        self.hits = 0

    @property
    def base_exceptions(self) -> type[Exception] | tuple[type[Exception], ...]:
        return ConnectionError

    def _fail_if_down(self) -> None:
        if self.down:
            raise ConnectionError("storage unreachable")

    def acquire_sliding_window_entry(self, *args: Any, **kwargs: Any) -> bool:
        self._fail_if_down()
        self.hits += 1
        return super().acquire_sliding_window_entry(*args, **kwargs)

    def get_sliding_window(self, *args: Any, **kwargs: Any) -> tuple[int, float, int, float]:
        self._fail_if_down()
        return super().get_sliding_window(*args, **kwargs)

    def check(self) -> bool:
        return not self.down


class FakeMonotonic:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def storage() -> FlakyStorage:
    return FlakyStorage()


@pytest.fixture
def clock() -> FakeMonotonic:
    return FakeMonotonic()


@pytest.fixture
def limiter(storage: FlakyStorage, clock: FakeMonotonic) -> RateLimiter:
    return RateLimiter(storage, recovery_interval_seconds=30, monotonic=clock)


def test_allows_up_to_the_limit_then_blocks(limiter: RateLimiter) -> None:
    results = [limiter.hit(LIMIT, "read", "1.1.1.1") for _ in range(4)]

    assert [r.allowed for r in results] == [True, True, True, False]
    assert [r.remaining for r in results[:3]] == [2, 1, 0]
    assert "Retry-After" not in results[0].headers()
    assert int(results[3].headers()["Retry-After"]) >= 1
    assert results[3].headers()["X-RateLimit-Limit"] == "3"


def test_buckets_and_clients_are_counted_separately(limiter: RateLimiter) -> None:
    for _ in range(3):
        limiter.hit(LIMIT, "read", "1.1.1.1")

    assert not limiter.hit(LIMIT, "read", "1.1.1.1").allowed
    assert limiter.hit(LIMIT, "write", "1.1.1.1").allowed
    assert limiter.hit(LIMIT, "read", "2.2.2.2").allowed


def test_storage_outage_falls_back_to_memory_and_keeps_limiting(
    limiter: RateLimiter, storage: FlakyStorage
) -> None:
    storage.down = True

    results = [limiter.hit(LIMIT, "read", "1.1.1.1") for _ in range(4)]

    assert limiter.degraded
    assert [r.allowed for r in results] == [True, True, True, False]


def test_recovers_to_shared_storage_after_the_recovery_interval(
    limiter: RateLimiter, storage: FlakyStorage, clock: FakeMonotonic
) -> None:
    storage.down = True
    limiter.hit(LIMIT, "read", "1.1.1.1")
    assert limiter.degraded

    storage.down = False
    limiter.hit(LIMIT, "read", "1.1.1.1")
    assert limiter.degraded, "should not probe storage before the interval has passed"
    assert storage.hits == 0

    clock.now += 31
    limiter.hit(LIMIT, "read", "1.1.1.1")

    assert not limiter.degraded
    assert storage.hits == 1


def test_stays_degraded_if_storage_is_still_down_at_the_recovery_check(
    limiter: RateLimiter, storage: FlakyStorage, clock: FakeMonotonic
) -> None:
    storage.down = True
    limiter.hit(LIMIT, "read", "1.1.1.1")

    clock.now += 31
    result = limiter.hit(LIMIT, "read", "1.1.1.1")

    assert result.allowed
    assert limiter.degraded
