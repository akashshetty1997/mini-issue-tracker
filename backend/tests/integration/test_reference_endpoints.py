from fastapi.testclient import TestClient

from app.core.constants import STATUS_TRANSITIONS, TITLE_MAX_LENGTH
from app.models import User


def test_users_are_listed_by_name(client: TestClient, users: list[User]) -> None:
    response = client.get("/api/v1/users")

    assert response.status_code == 200
    assert [u["name"] for u in response.json()] == ["Ada Lovelace", "Alan Turing"]
    assert set(response.json()[0]) == {"id", "name", "email"}


def test_meta_exposes_server_rules(client: TestClient) -> None:
    body = client.get("/api/v1/meta").json()

    assert body["statuses"] == ["open", "in_progress", "resolved", "closed"]
    assert body["priorities"] == ["low", "medium", "high", "critical"]
    assert body["limits"]["title_max_length"] == TITLE_MAX_LENGTH
    assert {k: set(v) for k, v in body["status_transitions"].items()} == {
        status.value: {s.value for s in targets} for status, targets in STATUS_TRANSITIONS.items()
    }


def test_ready_checks_the_database(client: TestClient) -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok", "rate_limit_storage": "ok"},
    }


def test_only_versioned_routes_are_part_of_the_api(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert set(paths) - {"/health", "/ready"} == {p for p in paths if p.startswith("/api/v1/")}
