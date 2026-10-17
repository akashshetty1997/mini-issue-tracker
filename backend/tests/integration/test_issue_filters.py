"""Filtering, search, sorting and pagination of GET /issues."""

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.constants import IssuePriority
from app.models import Issue, User
from tests.integration.conftest import ISSUES_URL, CreateIssue


def list_titles(client: TestClient, **params: Any) -> list[str]:
    response = client.get(ISSUES_URL, params=params)
    assert response.status_code == 200, response.text
    return [issue["title"] for issue in response.json()["items"]]


@pytest.fixture
def backlog(create_issue: CreateIssue, users: list[User]) -> None:
    ada, alan = users
    create_issue(title="Login fails", status="open", priority="critical", assignee_id=ada.id)
    create_issue(title="Slow dashboard", status="in_progress", priority="high")
    create_issue(
        title="Typo on pricing page",
        description="'Montly' should be 'Monthly'",
        status="resolved",
        priority="low",
        assignee_id=alan.id,
    )
    create_issue(title="Old export bug", status="closed", priority="medium", assignee_id=ada.id)


@pytest.mark.usefixtures("backlog")
class TestFilters:
    def test_by_single_status(self, client: TestClient) -> None:
        assert list_titles(client, status="open") == ["Login fails"]

    def test_by_multiple_statuses(self, client: TestClient) -> None:
        titles = list_titles(client, status=["open", "in_progress"])

        assert sorted(titles) == ["Login fails", "Slow dashboard"]

    def test_by_priority(self, client: TestClient) -> None:
        assert list_titles(client, priority="low") == ["Typo on pricing page"]

    def test_by_assignee(self, client: TestClient, users: list[User]) -> None:
        titles = list_titles(client, assignee_id=users[0].id)

        assert sorted(titles) == ["Login fails", "Old export bug"]

    def test_filters_combine_with_and(self, client: TestClient, users: list[User]) -> None:
        titles = list_titles(client, assignee_id=users[0].id, status="closed")

        assert titles == ["Old export bug"]

    def test_total_counts_filtered_rows_not_the_page(self, client: TestClient) -> None:
        body = client.get(ISSUES_URL, params={"status": ["open", "closed"], "limit": 1}).json()

        assert len(body["items"]) == 1
        assert body["total"] == 2

    def test_no_matches_returns_empty_page(self, client: TestClient) -> None:
        body = client.get(ISSUES_URL, params={"status": "open", "priority": "low"}).json()

        assert body == {"items": [], "total": 0, "limit": 20, "offset": 0}


@pytest.mark.usefixtures("backlog")
class TestSearch:
    def test_matches_title_case_insensitively(self, client: TestClient) -> None:
        assert list_titles(client, q="LOGIN") == ["Login fails"]

    def test_matches_description(self, client: TestClient) -> None:
        assert list_titles(client, q="monthly") == ["Typo on pricing page"]

    def test_combines_with_filters(self, client: TestClient) -> None:
        assert list_titles(client, q="o", status="closed") == ["Old export bug"]

    def test_blank_query_is_ignored(self, client: TestClient) -> None:
        assert len(list_titles(client, q="   ")) == 4


class TestSearchEscaping:
    """User input is matched literally; LIKE wildcards must not leak through."""

    def test_percent_is_literal(self, client: TestClient, create_issue: CreateIssue) -> None:
        create_issue(title="CPU at 100% on worker")
        create_issue(title="CPU at 100 on worker")

        assert list_titles(client, q="100%") == ["CPU at 100% on worker"]
        assert list_titles(client, q="%") == ["CPU at 100% on worker"]

    def test_underscore_is_literal(self, client: TestClient, create_issue: CreateIssue) -> None:
        create_issue(title="Rename user_id column")
        create_issue(title="Rename userXid column")

        assert list_titles(client, q="user_id") == ["Rename user_id column"]

    def test_backslash_is_literal(self, client: TestClient, create_issue: CreateIssue) -> None:
        create_issue(title=r"Path C:\temp breaks")
        create_issue(title="Path C:temp breaks")

        assert list_titles(client, q="\\") == [r"Path C:\temp breaks"]


class TestSorting:
    @pytest.mark.usefixtures("backlog")
    def test_priority_sorts_by_severity_not_alphabetically(self, client: TestClient) -> None:
        titles = list_titles(client, sort="-priority")

        assert titles == ["Login fails", "Slow dashboard", "Old export bug", "Typo on pricing page"]

    def test_title_ascending_is_case_insensitive(
        self, client: TestClient, create_issue: CreateIssue
    ) -> None:
        for title in ("banana", "Apple", "cherry"):
            create_issue(title=title)

        assert list_titles(client, sort="title") == ["Apple", "banana", "cherry"]

    def test_pagination_is_stable_when_sort_values_tie(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Rows with identical sort keys must each appear exactly once across pages."""
        same_time = datetime(2026, 1, 1, tzinfo=UTC)
        db_session.add_all(
            Issue(
                title=f"Tied {n}",
                priority=IssuePriority.HIGH,
                created_at=same_time,
                updated_at=same_time,
            )
            for n in range(7)
        )
        db_session.commit()

        seen: list[int] = []
        for offset in range(0, 7, 2):
            page = client.get(
                ISSUES_URL, params={"sort": "-created_at", "limit": 2, "offset": offset}
            ).json()
            seen.extend(issue["id"] for issue in page["items"])

        assert len(seen) == len(set(seen)) == 7
        assert seen == sorted(seen, reverse=True)

    @pytest.mark.parametrize("bad_sort", ["colour", "-colour", "--created_at", "id", ""])
    def test_unknown_sort_field_is_rejected(self, client: TestClient, bad_sort: str) -> None:
        response = client.get(ISSUES_URL, params={"sort": bad_sort})

        assert response.status_code == 422
        assert response.json()["error"]["details"][0]["field"] == "sort"


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"status": "done"}, "status.0"),
        ({"priority": "urgent"}, "priority.0"),
        ({"assignee_id": "me"}, "assignee_id"),
        ({"q": "x" * 201}, "q"),
    ],
)
def test_invalid_filter_values_are_rejected(
    client: TestClient, params: dict[str, Any], field: str
) -> None:
    response = client.get(ISSUES_URL, params=params)

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == field
