"""Security headers, access logging and request-size limits. No database needed."""

import logging
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_issue_service
from app.core.config import Settings
from app.core.constants import MAX_REQUEST_BODY_BYTES, SECURITY_HEADERS
from app.main import create_app
from app.services.issue_service import IssueService
from app.services.status_policy import StatusTransitionPolicy
from tests.fakes import FakeUnitOfWork, FixedClock, InMemoryIssueRepository, InMemoryUserLookup

ORIGIN = "http://frontend.test"
ISSUES_URL = "/api/v1/issues"


@pytest.fixture
def app() -> FastAPI:
    app = create_app(Settings(environment="test", cors_origins=[ORIGIN], rate_limit_enabled=False))
    service = IssueService(
        issues=InMemoryIssueRepository(),
        users=InMemoryUserLookup(set()),
        uow=FakeUnitOfWork(),
        clock=FixedClock(),
        status_policy=StatusTransitionPolicy(),
    )
    app.dependency_overrides[get_issue_service] = lambda: service

    def boom() -> None:
        raise RuntimeError("boom")

    app.add_api_route("/boom", boom)
    return app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


class TestSecurityHeaders:
    @pytest.mark.parametrize("path", ["/health", "/api/v1/nope", "/boom"])
    def test_present_on_success_and_error_responses(self, client: TestClient, path: str) -> None:
        response = client.get(path)

        for name, value in SECURITY_HEADERS.items():
            assert response.headers[name] == value


class TestAccessLog:
    def test_logs_one_line_per_request_with_status_and_timing(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="app.access"):
            response = client.get("/api/v1/nope", headers={"X-Request-ID": "log-1"})

        [record] = [r for r in caplog.records if r.name == "app.access"]
        assert record.__dict__["method"] == "GET"
        assert record.__dict__["path"] == "/api/v1/nope"
        assert record.__dict__["status"] == 404
        assert record.__dict__["duration_ms"] >= 0
        assert response.headers["X-Process-Time"].endswith("ms")

    def test_unhandled_errors_are_logged_as_500(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="app.access"):
            client.get("/boom")

        [record] = [r for r in caplog.records if r.name == "app.access"]
        assert record.__dict__["status"] == 500


class TestBodySizeLimit:
    def test_small_body_is_accepted(self, client: TestClient) -> None:
        response = client.post(ISSUES_URL, json={"title": "fits"})

        assert response.status_code == 201

    def test_declared_content_length_over_limit_is_rejected(self, client: TestClient) -> None:
        body = b'{"title": "' + b"x" * MAX_REQUEST_BODY_BYTES + b'"}'

        response = client.post(
            ISSUES_URL,
            content=body,
            headers={"Content-Type": "application/json", "Origin": ORIGIN},
        )

        assert response.status_code == 413
        assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
        assert response.headers["access-control-allow-origin"] == ORIGIN

    def test_chunked_body_over_limit_is_rejected(self, client: TestClient) -> None:
        """No Content-Length: the size must be enforced while streaming."""

        def chunks() -> Iterator[bytes]:
            yield b'{"title": "'
            for _ in range(MAX_REQUEST_BODY_BYTES // 1024 + 1):
                yield b"x" * 1024
            yield b'"}'

        response = client.post(
            ISSUES_URL, content=chunks(), headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 413
        assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"

    def test_chunked_body_under_limit_is_accepted(self, client: TestClient) -> None:
        def chunks() -> Iterator[bytes]:
            yield b'{"title": '
            yield b'"streamed"}'

        response = client.post(
            ISSUES_URL, content=chunks(), headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 201
