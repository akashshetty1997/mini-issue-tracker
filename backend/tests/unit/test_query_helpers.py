import pytest

from app.repositories.issue_repository import escape_like
from app.repositories.queries import SortOrder


@pytest.mark.parametrize(
    ("raw", "escaped"),
    [
        ("plain", "plain"),
        ("100%", "100\\%"),
        ("user_id", "user\\_id"),
        ("C:\\temp", "C:\\\\temp"),
        ("\\%", "\\\\\\%"),
    ],
)
def test_escape_like(raw: str, escaped: str) -> None:
    assert escape_like(raw) == escaped


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("created_at", SortOrder("created_at", descending=False)),
        ("-priority", SortOrder("priority", descending=True)),
    ],
)
def test_sort_order_parse(value: str, expected: SortOrder) -> None:
    assert SortOrder.parse(value) == expected
