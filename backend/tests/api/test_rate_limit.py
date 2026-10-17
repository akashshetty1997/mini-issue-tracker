"""Rate limiting through the HTTP stack. Uses in-memory fakes instead of a database."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_issue_service, get_session
from app.core.config import Settings
from app.main import create_app
from app.services.issue_service import IssueService
from app.services.status_policy import StatusTransitionPolicy
from tests.fakes import FakeUnitOfWork, FixedClock, InMemoryIssueRepository, InMemoryUserLookup

ORIGIN = "http://frontend.test"
READ_URL = "/api/v1/meta"
ISSUES_URL = "/api/v1/issues"


class FakeSession:
    def execute(self, *_: Any) -> None:
        return None


def build_app(**settings: Any) -> FastAPI:
    app = create_app(
        Settings(
            environment="test",
            cors_origins=[ORIGIN],
            read_rate_limit="3/minute",
            write_rate_limit="2/minute",
            **settings,
        )
    )
    service = IssueService(
        issues=InMemoryIssueRepository(),
        users=InMemoryUserLookup(set()),
        uow=FakeUnitOfWork(),
        clock=FixedClock(),
        status_policy=StatusTransitionPolicy(),
    )
    app.dependency_overrides[get_issue_service] = lambda: service
    app.dependency_overrides[get_session] = lambda: FakeSession()
    return app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(build_app()) as client:
        yield client


def test_successful_responses_report_remaining_quota(client: TestClient) -> None:
    remaining = [client.get(READ_URL).headers["X-RateLimit-Remaining"] for _ in range(3)]

    assert remaining == ["2", "1", "0"]


def test_exceeding_the_limit_returns_429_envelope_with_retry_after(client: TestClient) -> None:
    for _ in range(3):
        client.get(READ_URL)

    response = client.get(READ_URL, headers={"Origin": ORIGIN, "X-Request-ID": "rl-1"})

    assert response.status_code == 429
    error = response.json()["error"]
    assert error["code"] == "RATE_LIMITED"
    assert error["request_id"] == "rl-1"
    retry_after = int(response.headers["Retry-After"])
    assert 1 <= retry_after <= 60
    assert error["details"] == {"retry_after_seconds": retry_after}
    # The browser can read the 429 and its Retry-After header.
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert "Retry-After" in response.headers["access-control-expose-headers"]


def test_reads_and_writes_have_separate_budgets(client: TestClient) -> None:
    statuses = [client.post(ISSUES_URL, json={"title": f"t{n}"}).status_code for n in range(3)]

    assert statuses == [201, 201, 429]
    assert client.get(READ_URL).status_code == 200


def test_clients_are_limited_independently() -> None:
    app = build_app()
    with (
        TestClient(app, client=("10.0.0.1", 5000)) as first,
        TestClient(app, client=("10.0.0.2", 5000)) as second,
    ):
        for _ in range(3):
            first.get(READ_URL)

        assert first.get(READ_URL).status_code == 429
        assert second.get(READ_URL).status_code == 200


def test_health_probes_are_never_limited(client: TestClient) -> None:
    statuses = {client.get(path).status_code for path in ["/health", "/ready"] * 10}

    assert statuses == {200}


def test_can_be_disabled() -> None:
    with TestClient(build_app(rate_limit_enabled=False)) as client:
        responses = [client.get(READ_URL) for _ in range(5)]

    assert {r.status_code for r in responses} == {200}
    assert "X-RateLimit-Limit" not in responses[0].headers


def test_unreachable_redis_degrades_to_in_memory_limits() -> None:
    """Nothing listens on port 1: requests still succeed and limits still apply."""
    with TestClient(build_app(redis_url="redis://127.0.0.1:1/0")) as client:
        statuses = [client.get(READ_URL).status_code for _ in range(4)]
        ready = client.get("/ready")

    assert statuses == [200, 200, 200, 429]
    assert ready.status_code == 200
    assert ready.json() == {
        "status": "degraded",
        "checks": {"database": "ok", "rate_limit_storage": "degraded"},
    }
