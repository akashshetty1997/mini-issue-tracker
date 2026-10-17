"""HTTP contract for issue CRUD against a real database."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_issue_service
from app.core.clock import SystemClock
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.models import User
from app.repositories.issue_repository import SqlAlchemyIssueRepository
from app.services.issue_service import IssueService
from app.services.status_policy import StatusTransitionPolicy
from tests.integration.conftest import ISSUES_URL, CreateIssue


class TestCreate:
    def test_returns_201_with_location_and_defaults(self, client: TestClient) -> None:
        response = client.post(ISSUES_URL, json={"title": "  Login fails  "})

        assert response.status_code == 201
        body = response.json()
        assert response.headers["Location"] == f"{ISSUES_URL}/{body['id']}"
        assert body["title"] == "Login fails"
        assert body["description"] == ""
        assert body["status"] == "open"
        assert body["priority"] == "medium"
        assert body["assignee"] is None
        assert body["created_at"] == body["updated_at"]
        assert body["allowed_transitions"] == ["in_progress", "resolved", "closed"]

    def test_with_all_fields_and_embedded_assignee(
        self, client: TestClient, users: list[User]
    ) -> None:
        response = client.post(
            ISSUES_URL,
            json={
                "title": "Checkout is slow",
                "description": "p95 above 3s",
                "status": "in_progress",
                "priority": "critical",
                "assignee_id": users[0].id,
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["priority"] == "critical"
        assert body["status"] == "in_progress"
        assert body["assignee"] == {"id": users[0].id, "name": "Ada Lovelace"}

    def test_unknown_assignee_is_rejected(self, client: TestClient) -> None:
        response = client.post(ISSUES_URL, json={"title": "x", "assignee_id": 999_999})

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_ASSIGNEE"

    def test_assignee_deleted_after_existence_check_still_returns_422(
        self, app: FastAPI, client: TestClient, db_session: Session
    ) -> None:
        """Race: the user exists when checked but is gone by the INSERT. The foreign-key
        violation must surface as INVALID_ASSIGNEE, not as a 5xx."""

        class StaleUserLookup:
            def exists(self, user_id: int) -> bool:
                return True

        def service_with_stale_lookup() -> IssueService:
            return IssueService(
                issues=SqlAlchemyIssueRepository(db_session),
                users=StaleUserLookup(),
                uow=SqlAlchemyUnitOfWork(db_session),
                clock=SystemClock(),
                status_policy=StatusTransitionPolicy(),
            )

        app.dependency_overrides[get_issue_service] = service_with_stale_lookup

        response = client.post(ISSUES_URL, json={"title": "x", "assignee_id": 999_999})

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_ASSIGNEE"


class TestRetrieve:
    def test_get_by_id(self, client: TestClient, create_issue: CreateIssue) -> None:
        created = create_issue(description="Steps to reproduce")

        response = client.get(f"{ISSUES_URL}/{created['id']}")

        assert response.status_code == 200
        assert response.json() == created

    def test_unknown_id_returns_404(self, client: TestClient) -> None:
        response = client.get(f"{ISSUES_URL}/999999")

        assert response.status_code == 404
        error = response.json()["error"]
        assert error["code"] == "ISSUE_NOT_FOUND"
        assert error["message"] == "Issue 999999 was not found."

    def test_list_is_newest_first_and_paginated(
        self, client: TestClient, create_issue: CreateIssue
    ) -> None:
        ids = [create_issue(title=f"Issue {n}")["id"] for n in range(3)]

        first_page = client.get(ISSUES_URL, params={"limit": 2}).json()
        second_page = client.get(ISSUES_URL, params={"limit": 2, "offset": 2}).json()

        assert [i["id"] for i in first_page["items"]] == [ids[2], ids[1]]
        assert [i["id"] for i in second_page["items"]] == [ids[0]]
        assert first_page["total"] == second_page["total"] == 3
        assert (first_page["limit"], first_page["offset"]) == (2, 0)


class TestUpdate:
    def test_partial_update_changes_only_given_fields(
        self, client: TestClient, create_issue: CreateIssue
    ) -> None:
        created = create_issue(description="keep me", priority="low")

        response = client.patch(f"{ISSUES_URL}/{created['id']}", json={"title": "Renamed"})

        assert response.status_code == 200
        body = response.json()
        assert body["title"] == "Renamed"
        assert body["description"] == "keep me"
        assert body["priority"] == "low"
        assert body["created_at"] == created["created_at"]
        assert body["updated_at"] > created["updated_at"]

    def test_change_status(self, client: TestClient, create_issue: CreateIssue) -> None:
        created = create_issue()

        response = client.patch(f"{ISSUES_URL}/{created['id']}", json={"status": "resolved"})

        assert response.status_code == 200
        assert response.json()["status"] == "resolved"
        assert response.json()["allowed_transitions"] == ["open", "in_progress", "closed"]

    def test_disallowed_status_change_returns_409_with_allowed_options(
        self, client: TestClient, create_issue: CreateIssue
    ) -> None:
        created = create_issue(status="closed")

        response = client.patch(f"{ISSUES_URL}/{created['id']}", json={"status": "in_progress"})

        assert response.status_code == 409
        error = response.json()["error"]
        assert error["code"] == "INVALID_STATUS_TRANSITION"
        assert error["details"] == {"from": "closed", "to": "in_progress", "allowed": ["open"]}
        assert client.get(f"{ISSUES_URL}/{created['id']}").json()["status"] == "closed"

    def test_assign_and_unassign(
        self, client: TestClient, create_issue: CreateIssue, users: list[User]
    ) -> None:
        created = create_issue()
        url = f"{ISSUES_URL}/{created['id']}"

        assigned = client.patch(url, json={"assignee_id": users[1].id}).json()
        unassigned = client.patch(url, json={"assignee_id": None}).json()

        assert assigned["assignee"] == {"id": users[1].id, "name": "Alan Turing"}
        assert unassigned["assignee"] is None
        assert unassigned["assignee_id"] is None

    def test_null_description_becomes_empty(
        self, client: TestClient, create_issue: CreateIssue
    ) -> None:
        created = create_issue(description="something")

        response = client.patch(f"{ISSUES_URL}/{created['id']}", json={"description": None})

        assert response.status_code == 200
        assert response.json()["description"] == ""

    def test_unknown_assignee_is_rejected(
        self, client: TestClient, create_issue: CreateIssue
    ) -> None:
        created = create_issue()

        response = client.patch(f"{ISSUES_URL}/{created['id']}", json={"assignee_id": 424242})

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_ASSIGNEE"

    def test_unknown_issue_returns_404(self, client: TestClient) -> None:
        response = client.patch(f"{ISSUES_URL}/999999", json={"title": "x"})

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "ISSUE_NOT_FOUND"


class TestDelete:
    def test_delete_then_get_returns_404(
        self, client: TestClient, create_issue: CreateIssue
    ) -> None:
        created = create_issue()
        url = f"{ISSUES_URL}/{created['id']}"

        response = client.delete(url)

        assert response.status_code == 204
        assert response.content == b""
        assert client.get(url).status_code == 404

    def test_unknown_issue_returns_404(self, client: TestClient) -> None:
        response = client.delete(f"{ISSUES_URL}/999999")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "ISSUE_NOT_FOUND"
