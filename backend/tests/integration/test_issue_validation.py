"""Invalid input is rejected with 422 and a field-level error envelope."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.constants import DESCRIPTION_MAX_LENGTH, MAX_PAGE_SIZE, TITLE_MAX_LENGTH
from tests.integration.conftest import ISSUES_URL, CreateIssue


def error_fields(response: Any) -> list[str | None]:
    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    return [detail["field"] for detail in error["details"]]


class TestCreateValidation:
    @pytest.mark.parametrize(
        ("payload", "field"),
        [
            ({}, "title"),
            ({"title": ""}, "title"),
            ({"title": "    "}, "title"),
            ({"title": "x" * (TITLE_MAX_LENGTH + 1)}, "title"),
            ({"title": None}, "title"),
            ({"title": "ok", "description": "x" * (DESCRIPTION_MAX_LENGTH + 1)}, "description"),
            ({"title": "ok", "status": "done"}, "status"),
            ({"title": "ok", "status": "OPEN"}, "status"),
            ({"title": "ok", "priority": "urgent"}, "priority"),
            ({"title": "ok", "assignee_id": 0}, "assignee_id"),
            ({"title": "ok", "assignee_id": "abc"}, "assignee_id"),
            ({"title": "ok", "reporter": "me"}, "reporter"),
        ],
    )
    def test_invalid_payload_is_rejected(
        self, client: TestClient, payload: dict[str, Any], field: str
    ) -> None:
        response = client.post(ISSUES_URL, json=payload)

        assert field in error_fields(response)

    def test_malformed_json_is_rejected(self, client: TestClient) -> None:
        response = client.post(
            ISSUES_URL, content=b"{not json", headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_nothing_is_saved_when_validation_fails(self, client: TestClient) -> None:
        client.post(ISSUES_URL, json={"title": "ok", "priority": "urgent"})

        assert client.get(ISSUES_URL).json()["total"] == 0


class TestUpdateValidation:
    @pytest.mark.parametrize(
        ("payload", "field"),
        [
            ({"title": None}, "title"),
            ({"status": None}, "status"),
            ({"priority": None}, "priority"),
            ({"title": "  "}, "title"),
            ({"status": "archived"}, "status"),
            ({"priority": "p0"}, "priority"),
            ({"unknown": 1}, "unknown"),
            ({"title": "ok", "version": 0}, "version"),
            ({"title": "ok", "version": "latest"}, "version"),
        ],
    )
    def test_invalid_payload_is_rejected(
        self,
        client: TestClient,
        create_issue: CreateIssue,
        payload: dict[str, Any],
        field: str,
    ) -> None:
        created = create_issue()

        response = client.patch(f"{ISSUES_URL}/{created['id']}", json={"version": 1, **payload})

        assert field in error_fields(response)

    def test_empty_body_is_rejected(self, client: TestClient, create_issue: CreateIssue) -> None:
        created = create_issue()

        response = client.patch(f"{ISSUES_URL}/{created['id']}", json={"version": 1})

        assert response.status_code == 422
        assert response.json()["error"]["details"][0]["message"] == (
            "At least one field to change must be provided."
        )


class TestIdAndQueryValidation:
    @pytest.mark.parametrize("bad_id", ["abc", "0", "-1", "1.5", str(2**31)])
    def test_invalid_issue_id_is_rejected(self, client: TestClient, bad_id: str) -> None:
        for response in (
            client.get(f"{ISSUES_URL}/{bad_id}"),
            client.patch(f"{ISSUES_URL}/{bad_id}", json={"title": "x", "version": 1}),
            client.delete(f"{ISSUES_URL}/{bad_id}"),
        ):
            assert error_fields(response) == ["issue_id"]

    @pytest.mark.parametrize(
        ("params", "field"),
        [
            ({"limit": 0}, "limit"),
            ({"limit": MAX_PAGE_SIZE + 1}, "limit"),
            ({"offset": -1}, "offset"),
            ({"colour": "red"}, "colour"),
        ],
    )
    def test_invalid_list_parameters_are_rejected(
        self, client: TestClient, params: dict[str, Any], field: str
    ) -> None:
        response = client.get(ISSUES_URL, params=params)

        assert field in error_fields(response)
