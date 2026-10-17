"""Error envelope and middleware behaviour. These tests need no database."""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.main import create_app

ORIGIN = "http://frontend.test"


@pytest.fixture
def app() -> FastAPI:
    app = create_app(Settings(environment="test", cors_origins=[ORIGIN]))

    def boom() -> None:
        raise RuntimeError("secret internal detail")

    def db_down() -> None:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    app.add_api_route("/boom", boom)
    app.add_api_route("/db-down", db_down)
    return app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


def assert_envelope(body: dict[str, object], code: str) -> dict[str, object]:
    assert set(body) == {"error"}
    error = body["error"]
    assert isinstance(error, dict)
    assert set(error) == {"code", "message", "details", "request_id"}
    assert error["code"] == code
    return error


class TestRequestId:
    def test_generated_when_absent(self, client: TestClient) -> None:
        response = client.get("/health")

        assert len(response.headers["X-Request-ID"]) == 32

    def test_valid_incoming_id_is_echoed(self, client: TestClient) -> None:
        response = client.get("/health", headers={"X-Request-ID": "trace-abc.123_x"})

        assert response.headers["X-Request-ID"] == "trace-abc.123_x"

    @pytest.mark.parametrize("bad_id", ["has spaces", "a" * 65, '{"inject":1}', ""])
    def test_invalid_incoming_id_is_replaced(self, client: TestClient, bad_id: str) -> None:
        response = client.get("/health", headers={"X-Request-ID": bad_id})

        assert response.headers["X-Request-ID"] != bad_id
        assert len(response.headers["X-Request-ID"]) == 32

    def test_error_body_carries_the_request_id(self, client: TestClient) -> None:
        response = client.get("/nope", headers={"X-Request-ID": "req-1"})

        assert response.json()["error"]["request_id"] == "req-1"


class TestUnhandledErrors:
    def test_returns_generic_500_without_internals(self, client: TestClient) -> None:
        response = client.get("/boom")

        assert response.status_code == 500
        error = assert_envelope(response.json(), "INTERNAL_ERROR")
        assert error["message"] == "An unexpected error occurred."
        assert "secret" not in response.text
        assert "Traceback" not in response.text

    def test_500_still_has_cors_and_request_id_headers(self, client: TestClient) -> None:
        response = client.get("/boom", headers={"Origin": ORIGIN})

        assert response.headers["access-control-allow-origin"] == ORIGIN
        assert "X-Request-ID" in response.headers

    def test_database_outage_maps_to_503(self, client: TestClient) -> None:
        response = client.get("/db-down")

        assert response.status_code == 503
        assert_envelope(response.json(), "SERVICE_UNAVAILABLE")
        assert "connection refused" not in response.text


class TestFrameworkErrors:
    def test_unknown_route_uses_envelope(self, client: TestClient) -> None:
        response = client.get("/api/v1/nope")

        assert response.status_code == 404
        assert_envelope(response.json(), "NOT_FOUND")

    def test_wrong_method_uses_envelope_and_keeps_allow_header(self, client: TestClient) -> None:
        response = client.delete("/health")

        assert response.status_code == 405
        assert_envelope(response.json(), "METHOD_NOT_ALLOWED")
        assert "GET" in response.headers["allow"]


class TestCors:
    def test_exposes_headers_the_frontend_reads(self, client: TestClient) -> None:
        response = client.get("/health", headers={"Origin": ORIGIN})

        exposed = response.headers["access-control-expose-headers"]
        assert "X-Request-ID" in exposed
        assert "Location" in exposed

    def test_preflight_allows_patch_from_frontend(self, client: TestClient) -> None:
        response = client.options(
            "/health",
            headers={
                "Origin": ORIGIN,
                "Access-Control-Request-Method": "PATCH",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == ORIGIN

    def test_unknown_origin_gets_no_cors_headers(self, client: TestClient) -> None:
        response = client.get("/health", headers={"Origin": "http://evil.test"})

        assert "access-control-allow-origin" not in response.headers
