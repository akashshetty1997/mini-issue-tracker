"""Plain value objects describing what to read, independent of HTTP and SQL."""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PageRequest:
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class PageResult[T]:
    items: Sequence[T]
    total: int
