"""Integration fixtures: a real Postgres database, isolated per test.

Isolation works like this: each test opens a connection and begins an outer transaction.
The session joins it in "create_savepoint" mode, so when application code calls
``commit()`` only a SAVEPOINT is released. At teardown the outer transaction is rolled
back, which discards everything the test wrote. Tests stay independent and fast without
truncating tables.
"""

import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from alembic import command
from app.api.deps import get_session
from app.core.config import Settings
from app.main import create_app
from app.models import User

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://issues:issues@localhost:5433/issue_tracker_test",
)
ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"
ISSUES_URL = "/api/v1/issues"


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """Build the schema from the real migrations, which also tests that they apply cleanly."""
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    config.attributes["configure_logger"] = False
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = Session(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture
def app(db_session: Session) -> FastAPI:
    app = create_app(Settings(environment="test", database_url=TEST_DATABASE_URL))
    app.dependency_overrides[get_session] = lambda: db_session
    return app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


@pytest.fixture
def users(db_session: Session) -> list[User]:
    users = [
        User(name="Ada Lovelace", email="ada@test.dev"),
        User(name="Alan Turing", email="alan@test.dev"),
    ]
    db_session.add_all(users)
    # Release the savepoint so a later rollback inside a request can't discard these rows.
    db_session.commit()
    return users


CreateIssue = Callable[..., dict[str, Any]]


@pytest.fixture
def create_issue(client: TestClient) -> CreateIssue:
    """Factory: create an issue through the API and return its JSON body."""

    def _create(**fields: Any) -> dict[str, Any]:
        response = client.post(ISSUES_URL, json={"title": "Login fails", **fields})
        assert response.status_code == 201, response.text
        body: dict[str, Any] = response.json()
        return body

    return _create
