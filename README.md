# Mini Issue Tracker

A small issue tracker for creating, triaging and tracking software issues. It consists of:

- a versioned REST API: **FastAPI + PostgreSQL**
- a web UI: **Next.js + TypeScript**
- one-command setup with **Docker Compose**

| Issue list (filtered, sorted by priority) | Issue detail |
|---|---|
| ![Issue list](docs/screenshots/issue-list.png) | ![Issue detail](docs/screenshots/issue-detail.png) |

## Features

- Create, view, edit and delete issues. Each issue has a title, description, status, priority, assignee, and created/updated dates.
- Change status inline. The UI only offers moves the server allows (see [Status workflow](#status-workflow)).
- Assign and unassign issues to users.
- List issues with filters, search, sorting and pagination:
  - filter by status and priority (multiple values each), and by assignee
  - case-insensitive search across title and description
  - sort by created, updated, priority (by severity) or title
  - paginated results
- The list's filters live in the URL, so a filtered view can be shared or bookmarked and survives a reload.
- Input is validated on both client and server. Every API error uses one consistent error format, and internal details are never exposed.

## Tech stack

| Layer | Choice |
|---|---|
| API | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic |
| Database | PostgreSQL 16 (with `pg_trgm` for search) |
| Web | Next.js 16 (App Router), React 19, TypeScript, TanStack Query, Tailwind CSS |
| API contract | OpenAPI schema → TypeScript types via `openapi-typescript` |
| Tests / quality | pytest (unit + integration against real Postgres), ruff, mypy (strict), ESLint, `tsc` |
| Delivery | Docker Compose, multi-stage images, GitHub Actions CI |

## Quick start (Docker)

Prerequisites: Docker with Compose v2 and `make`. Without `make`, run the equivalent `docker compose` commands in the [Makefile](Makefile).

```bash
git clone <repo-url> && cd MPcircle
make up            # = docker compose up --build -d
```

| What | URL |
|---|---|
| Web app | http://localhost:3000 |
| API docs (Swagger UI) | http://localhost:8000/docs |
| Health / readiness | http://localhost:8000/health, http://localhost:8000/ready |

On first start the API container applies the database migrations and seeds four demo users and a few issues. Data lives in the `pgdata` Docker volume, so it survives `make down` / `make up`. To start from an empty database, run `docker compose down -v`.

**Port already in use?** Copy `.env.example` to `.env` and change `API_HOST_PORT`, `WEB_HOST_PORT` or `DB_HOST_PORT`. Then run `make up` again. The web app's API URL and the API's CORS origin follow those ports automatically.

Other useful targets (`make help` lists them all):

```bash
make logs       # follow logs
make down       # stop (keeps data)
make test       # backend tests in the dev image
make lint       # ruff + mypy
make gen-api    # regenerate openapi.json and the frontend's TypeScript types
make test-web   # frontend lint, type-check and build (needs Node 24 locally)
```

## Running without Docker (local development)

You still need a Postgres. The simplest option is the compose one, which is published on host port **5433**:

```bash
docker compose up -d db
```

**API** (Python 3.12):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
python -m app.scripts.seed
uvicorn app.main:create_app --factory --reload --port 8000
```

**Web** (Node 24):

```bash
cd frontend
npm ci
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev    # http://localhost:3000
```

## Environment variables

All variables are optional. The defaults in `docker-compose.yml` and `app/core/config.py` work out of the box. See [.env.example](.env.example).

| Variable | Used by | Default | Purpose |
|---|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | db, api | `issues` / `issues` / `issue_tracker` | Database credentials |
| `DB_HOST_PORT` | compose | `5433` | Host port for Postgres. 5433 avoids clashing with a local Postgres |
| `DATABASE_URL` | api | `postgresql+psycopg://issues:issues@localhost:5433/issue_tracker` | SQLAlchemy URL. Compose sets it to the `db` service |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` / `DB_POOL_RECYCLE_SECONDS` | api | `5` / `10` / `1800` | Connection pool per worker process |
| `CORS_ORIGINS` | api | `http://localhost:3000` | Comma-separated origins allowed to call the API from a browser |
| `LOG_LEVEL` | api | `INFO` | Log level (logs are JSON on stdout) |
| `WEB_CONCURRENCY` | api | `2` | Number of uvicorn worker processes |
| `API_HOST_PORT` | compose | `8000` | Host port for the API |
| `TEST_DATABASE_URL` | tests | `…@localhost:5433/issue_tracker_test` | Separate database used by the test suite |
| `WEB_HOST_PORT` | compose | `3000` | Host port for the web app |
| `NEXT_PUBLIC_API_URL` | web (build time) | `http://localhost:${API_HOST_PORT}` | API base URL **as seen by the browser**. It is baked in at build time |

## Tests

```bash
make test                         # all backend tests, inside Docker (needs the db service)
```

Or locally, from `backend/` with the venv active and `docker compose up -d db` running:

```bash
pytest                            # TEST_DATABASE_URL defaults to localhost:5433/issue_tracker_test
```

The backend has three groups of tests:

| Suite | What it covers | Needs a DB |
|---|---|---|
| `tests/unit` | `IssueService` business rules, the status-transition table, a rollback when a write fails part-way, LIKE escaping | No (in-memory fakes) |
| `tests/api` | Error envelope, request ids, 500/503 handling, CORS on error responses, 404/405 | No |
| `tests/integration` | Full HTTP contract against Postgres: CRUD, validation, filters, search escaping, sorting/pagination stability, the FK race → 422 | Yes |

Integration tests build the schema by running the real Alembic migrations. Each test then runs inside a transaction that is rolled back afterwards. The application's `commit()` calls become savepoint releases, so tests are isolated without truncating tables.

Frontend checks: `make test-web` runs lint, type-check and production build. CI (`.github/workflows/ci.yml`) runs all of the above. It also fails if `openapi/openapi.json` or the generated TypeScript types are out of date with the code.

## API

Base path: `/api/v1`. Interactive docs are at `/docs`, and the committed schema is in [openapi/openapi.json](openapi/openapi.json).

| Method | Path | Description |
|---|---|---|
| `GET` | `/issues` | List issues. Query: `status` (repeatable), `priority` (repeatable), `assignee_id`, `q`, `sort`, `limit` (1–100), `offset` |
| `POST` | `/issues` | Create an issue. Returns `201` and a `Location` header |
| `GET` | `/issues/{id}` | Get one issue |
| `PATCH` | `/issues/{id}` | Partial update. Only the fields you send are changed |
| `DELETE` | `/issues/{id}` | Delete an issue. Returns `204` |
| `GET` | `/users` | Users who can be assigned |
| `GET` | `/meta` | Statuses, priorities, transitions and field limits, so clients don't hard-code them |
| `GET` | `/health`, `/ready` | Liveness and readiness probes (unversioned). `/ready` checks the database |

Example:

```bash
curl -s localhost:8000/api/v1/issues -H 'Content-Type: application/json' \
  -d '{"title":"Checkout is slow","priority":"high","assignee_id":1}'

curl -s 'localhost:8000/api/v1/issues?status=open&status=in_progress&q=checkout&sort=-priority'
```

Each issue in a response embeds its assignee (`{id, name}`) and an `allowed_transitions` list.

`sort` takes one of `created_at`, `updated_at`, `priority` or `title`. Prefix it with `-` for descending order. The default is `-created_at`. The issue id is always used as a tiebreaker, so pages never repeat or skip rows.

**PATCH null rules:**
- `title`, `status` or `priority` set to `null` → `422`
- `description: null` → stored as an empty string
- `assignee_id: null` → unassigns the issue
- an empty body → `422`

### Errors

Every error, including unknown routes and unexpected failures, has the same shape:

```json
{
  "error": {
    "code": "INVALID_STATUS_TRANSITION",
    "message": "Cannot change status from 'closed' to 'in_progress'.",
    "details": { "from": "closed", "to": "in_progress", "allowed": ["open"] },
    "request_id": "8072325cf0c54a6fa8ff32cca01009b6"
  }
}
```

| Status | Codes |
|---|---|
| 404 | `ISSUE_NOT_FOUND`, `NOT_FOUND` |
| 405 | `METHOD_NOT_ALLOWED` |
| 409 | `INVALID_STATUS_TRANSITION`, `CONFLICT` |
| 422 | `VALIDATION_ERROR` (`details` lists each field and message), `INVALID_ASSIGNEE` |
| 500 | `INTERNAL_ERROR`, with a generic message. The stack trace is only logged |
| 503 | `SERVICE_UNAVAILABLE` (database unreachable) |

`request_id` is also returned in the `X-Request-ID` header and included in every log line, so a user-reported error can be found in the logs.

### Status workflow

| From | Allowed next statuses |
|---|---|
| `open` | `in_progress`, `resolved`, `closed` |
| `in_progress` | `open`, `resolved`, `closed` |
| `resolved` | `open`, `in_progress`, `closed` |
| `closed` | `open` (reopen) |

Setting an issue to its current status is a no-op. Any other move returns `409 INVALID_STATUS_TRANSITION`. The rule this enforces is that a closed issue must be reopened before work resumes on it. The table is plain data in [`backend/app/core/constants.py`](backend/app/core/constants.py).

## Project structure

```
backend/
  app/
    api/            HTTP layer: v1 routers, dependency wiring (deps.py), error handlers, health
    core/           constants.py (all fixed values), config.py (env), exceptions, logging, clock
    middleware/     request id, unhandled-error catch-all (pure ASGI)
    services/       IssueService (business rules), StatusTransitionPolicy
    repositories/   persistence Protocols + SQLAlchemy implementations, query objects
    db/             engine/session, unit of work, DB-error → domain-error translation
    models/         SQLAlchemy models
    schemas/        Pydantic request/response models
  alembic/          migrations
  tests/            unit/, api/, integration/
frontend/
  src/app/          routes (list, new, detail, edit), error + not-found boundaries
  src/views/        page-level client components
  src/components/   UI components (issues/, ui/)
  src/hooks/        TanStack Query hooks, URL-backed filter state
  src/lib/          API client, generated schema types, constants, filter (de)serialisation
openapi/            committed OpenAPI schema (source for frontend types)
```

## Assumptions

- **There is no authentication.** Users are seeded and stand in for real accounts. Anyone with access to the app can create, edit or delete any issue.
- **Single tenant.** All issues belong to one shared workspace.
- **Deletes are permanent.** There is no soft delete or audit history.
- **The status workflow above** is my interpretation. The brief only listed the statuses. The workflow is enforced server-side and surfaced in the UI.
- An issue may be created directly in any status, for example when importing a resolved bug.
- **Data is fetched in the browser**, not by Next.js on the server. The API therefore sees each user's own IP address, which matters for rate limiting.
- Timestamps are stored in UTC and shown in the viewer's local time zone.

## Known limitations

- No authentication, authorisation, comments or activity history.
- Offset pagination. It is simple, but it slows down on very deep pages and can shift if rows are inserted while paging. See ENGINEERING.md for the alternative.
- Search uses `ILIKE` with trigram indexes. Search terms shorter than 3 characters can't use the index. There is no relevance ranking or stemming.
- `GET /users` is not paginated. That's fine for a seeded team, not for a large organisation.
- Database migrations run when the API container starts. With several replicas this should become a separate job.
- `NEXT_PUBLIC_API_URL` is baked into the web image at build time, so each environment needs its own build.
- Concurrent edits are last-write-wins.
- Frontend behaviour is covered by lint, type-check and build in CI, plus manual end-to-end checks. There are no automated UI tests yet.
