# Engineering notes

## 1. Why did you choose your technology stack?

**FastAPI + Pydantic.**
- Request and response models are declared once as typed Pydantic classes. The same classes drive validation, serialisation and the OpenAPI schema.
- Most of the brief's validation requirements are covered by type annotations:
  - empty titles
  - invalid status or priority values
  - missing fields
  - malformed ids
- The free `/docs` UI makes the API easy for a reviewer to try.

**PostgreSQL + SQLAlchemy 2 + Alembic.**
- The data is relational: issues reference users. I wanted the database to enforce integrity too, using foreign keys, CHECK constraints for the enums, and NOT NULL.
- SQLAlchemy 2's typed ORM keeps queries readable and lets mypy check them.
- Alembic gives a reviewable, versioned schema history instead of `create_all()`.
- Postgres also gives a credible path to good search, via the `pg_trgm` indexes added in migration 0002.

**Redis**, only for rate-limit counters. Every API worker and replica has to see the same counts, and losing those counts is harmless. That's exactly what Redis is good at.

**Next.js + TypeScript + TanStack Query.**
- TypeScript lets me generate the API types from the backend's OpenAPI schema. Frontend and backend can't drift silently: CI regenerates the types and fails on any diff.
  - This worked in practice. When I made `version` required on PATCH, the compiler pointed at exactly the three call sites that needed it.
- TanStack Query handles caching, cancellation, refetching after mutations and keeping the previous page visible while the next one loads. Otherwise that would be hand-written `useEffect` code.

**Docker Compose.** A reviewer can run the database, Redis, API and web app with one command, without installing Python or Postgres locally.

## 2. How did you structure your application and why?

The backend is layered, and each layer has one job:

```
HTTP request
 → middleware            request id → access log → security headers → CORS → catch-all errors → body size
 → api/v1/*.py           translate HTTP ⇄ schemas; rate-limit dependencies
 → services/             business rules: assignee must exist, status transitions, versions, timestamps
 → repositories/         all SQL; never commit
 → unit of work          owns the transaction; translates DB constraint errors into domain errors
```

These are the decisions I'd point to:

- **The service depends on Protocols, not on SQLAlchemy.**
  - `IssueService` receives an `IssueRepository`, a `UserLookup`, a `UnitOfWork`, a `Clock` and a `StatusTransitionPolicy`.
  - The concrete classes are wired in one place, `api/deps.py`.
  - So the business rules are unit-tested against in-memory fakes, with no database and no HTTP.
  - The service only needs to ask "does this user exist?", so it depends on a one-method `UserLookup`, not on a whole user repository.
- **Rules as data.**
  - Status transitions are a table in `core/constants.py`. Changing the workflow is a data change.
  - List filters are a tuple of small "clause builder" functions. Adding a filter means adding one function, not editing the query.
  - Every domain error is an `AppError` subclass that carries its HTTP status and code, so one handler renders them all.
- **One home for constants.**
  - `core/constants.py` holds every fixed value: enums, limits, error codes, header names, default rate limits.
  - `core/config.py` holds only values that change per environment.
  - The frontend doesn't duplicate domain constants. Types come from the generated schema, and runtime limits come from `GET /api/v1/meta`.
  - The UI's label maps are typed `Record<IssueStatus, string>`. If the backend adds a status, the frontend stops compiling until someone gives it a label.
- **One error contract.**
  - Every failure renders as `{"error": {code, message, details, request_id}}`.
  - That includes Starlette's own 404/405, validation errors, 413, 429, database outages (503) and unexpected exceptions (generic 500, traceback logged only).
- **Versioning by URL prefix (`/api/v1`).** Each version has its own router package, so a future `v2` could change request/response shapes and still share the services underneath. `/health` and `/ready` stay unversioned because they describe the process, not the API.
- **Middleware is pure ASGI**, not `BaseHTTPMiddleware`. That avoids an extra task per request and known problems with context variables and streaming bodies. The stack order is deliberate and documented in `middleware/__init__.py`.

The frontend is split into:

- `app/`: routes only
- `views/`: page-level client components
- `components/`: presentational components
- `hooks/`: data and URL state
- `lib/`: API client, generated types, pure logic

All data is fetched in the browser, for two reasons. There is one API URL to configure. And the API sees real client IPs, which per-IP rate limiting needs.

### SOLID, mapped to the code

- **S (single responsibility):** one job per layer. Routes in `api/v1/issues.py` only translate HTTP, `services/issue_service.py` holds the rules, `repositories/issue_repository.py` holds the SQL, `db/unit_of_work.py` owns the transaction.
- **O (open/closed):** new behaviour is added, not edited in. A filter is one more function in `FILTER_BUILDERS` (`repositories/issue_repository.py`). A domain error is one more `AppError` subclass (`core/exceptions.py`). The workflow is the `STATUS_TRANSITIONS` table (`core/constants.py`).
- **L (Liskov substitution):** the in-memory fakes in `tests/fakes.py` stand in for the SQLAlchemy classes behind the same Protocols. `IssueService` runs unchanged on either: the unit tests use the fakes, the integration tests use the real classes.
- **I (interface segregation):** the service needs only `UserLookup.exists()`, while the users endpoint uses the wider `UserDirectory` (`repositories/interfaces.py`).
- **D (dependency inversion):** `IssueService` depends on Protocols (`IssueRepository`, `UserLookup`, `UnitOfWork`, `Clock`). The concrete classes are wired only in `api/deps.py`.

### Design decisions worth calling out

- **Optimistic locking: a version in the body plus `409`, rather than `ETag`/`If-Match` plus `412`.**
  - The textbook HTTP answer is to return an `ETag` and require `If-Match` on writes, failing with `412 Precondition Failed`.
  - I chose a `version` field in the JSON body and `409 Conflict`. It is explicit in the OpenAPI schema, so the generated client types *require* it. It is trivial for a JSON SPA to send, and it keeps all errors in the same envelope.
  - Moving to ETags later would be additive.
- **The version check is an atomic `UPDATE … WHERE id = :id AND version = :v`, not SQLAlchemy's `version_id_col`.**
  - With `version_id_col`, a mismatch raises `StaleDataError`, which is a `SQLAlchemyError`. It would fall into the generic database-error path, which maps to 500/503, unless special-cased.
  - Checking the rowcount myself is explicit and easy to explain.
  - A rowcount of 0 is then resolved to 404 (deleted) or 409 (changed).
- **My own small rate limiter on top of the `limits` library, instead of slowapi.**
  - slowapi's decorators bind to a module-global `Limiter`. That makes per-app settings and test isolation awkward.
  - Its header injection needs an extra `response` parameter on every route.
  - Its storage fallback doesn't protect header injection. If Redis fails after the hit but while slowapi reads the window stats for the headers, it switches to memory and then re-raises the error anyway, so the request fails with a 500 (slowapi 0.1.10, unless `swallow_errors` is set). I reproduced this with a storage stub that fails only on `get_window_stats`.
  - About 100 lines of my own code give injectable, testable behaviour: Redis sliding-window counters, fallback to memory on connection errors, and a recovery check every 30 s with short socket timeouts.
- **Readiness ignores Redis.** If Redis failed readiness, a Redis outage would pull every healthy API instance out of rotation, even though the limiter can work without it. `/ready` reports it as `degraded` and still returns 200.
- **The client IP is resolved in one place.** Uvicorn's `--proxy-headers --forwarded-allow-ips=$TRUSTED_PROXIES` rewrites the client address only for trusted proxies. The limiter reads `request.client.host` and never parses `X-Forwarded-For` itself, which could be spoofed.

## 3. What was the most difficult part of the task?

Making the error contract hold everywhere, not just in the happy-path handlers. Several things weren't obvious:

1. **Unhandled 500s lose their CORS headers.**
   - Starlette runs a bare `Exception` handler in `ServerErrorMiddleware`, which sits *outside* all user middleware, including CORS.
   - The browser would see a CORS failure instead of the JSON error.
   - I catch unexpected exceptions in my own middleware placed *inside* CORS. The same reasoning places the body-size limit inside CORS, so 413s are readable too.
   - Tests assert that a forced 500 and an oversized body both still carry `Access-Control-Allow-Origin`.
2. **Check-then-write races.**
   - The service checks that an assignee exists, but the user can be deleted before the INSERT.
   - The unit of work translates Postgres SQLSTATE codes into domain errors:
     - an FK violation on the assignee constraint becomes `422 INVALID_ASSIGNEE`
     - unique violations become `409`
   - Only real connectivity failures map to `503`.
   - The same thinking drove the atomic version check above. Checking the version on read gives a fast, clear error. The conditional `UPDATE` closes the window between that read and the write.
3. **Oversized chunked uploads.**
   - Checking `Content-Length` isn't enough, because chunked requests don't send one. The middleware also counts bytes as the body streams in.
   - FastAPI turns any exception raised while it reads the body into a generic `400`. So the "too large" signal had to be an `HTTPException(413)`, which FastAPI re-raises unchanged.
4. **Test isolation with real commits.**
   - The service commits, so wrapping each test in a transaction isn't enough on its own.
   - The test session joins an outer transaction with `join_transaction_mode="create_savepoint"`. Application `commit()` calls then only release savepoints, and the outer transaction is rolled back after each test.

On the frontend, the subtle parts were these:

- **The debounced search box.** It has to stay in sync when filters are cleared or the user presses Back, without an effect that re-submits a stale term. I debounce the *callback*, not the value.
- **The edit form under conflicts.** The form keeps a snapshot of the issue it was opened with. It diffs against that snapshot and saves with its version, even if fresher data arrives in the background. On a conflict it offers "discard my edits and load the latest version" instead of silently overwriting.

## 4. What would you improve if you had another two days?

- **Authentication and ownership.** Real users, a reporter field, and permissions on edit and delete. Rate limits would then be keyed per user instead of per IP.
- **Activity history and comments.** Each update would write an event row in the same transaction, giving an audit trail and a timeline on the issue page.
- **End-to-end tests in CI.** A Playwright smoke test (create → filter → edit with a conflict → delete) against the compose stack. I ran these flows by hand in a browser, but they aren't automated. Component tests for the form and filters would also help.
- **Keyset pagination** for the list, plus "my issues" and "unassigned" quick filters.
- **Observability.** OpenTelemetry traces across web → API → database, plus metrics for request latency, rate-limit rejections and degraded mode.

## 5. If this application grew to 100,000 users, what parts of your implementation would you reconsider?

Some of this is already designed in:
- The API is stateless, so it scales horizontally behind a load balancer.
- Rate-limit state is shared through Redis, and the limiter degrades rather than failing.
- Connection pool sizes are configurable.
- The list query has composite indexes that match the default sort, and trigram indexes for search.
- `total` is counted without the join and sort.
- Request bodies are size-limited.
- Logs are structured JSON with request ids, so they can be correlated across replicas.

What I'd reconsider:

- **Database connections.** Each API worker has its own pool, so many replicas × workers can exhaust Postgres connections. I'd put **PgBouncer** (transaction pooling) in front of Postgres. I'd also consider an async driver (`asyncpg` / SQLAlchemy async) if request latency becomes I/O-bound.
- **Migrations at startup.** Several replicas starting together would race to migrate. Migrations should be a separate one-off job in the deploy pipeline, with changes written to be backwards-compatible (expand → migrate → contract). Migration 0003 is already written so the column is added without a table rewrite.
- **Pagination.** Offset pagination gets slower as the offset grows. Rows also shift between pages under concurrent writes. I'd switch to keyset pagination on `(created_at, id)`, which the existing index already supports.
- **`COUNT(*)` on every list request.** This gets expensive on large filtered sets. I'd drop exact totals for "has next page" or an estimate, or cache counts per filter.
- **Search.** Trigram `ILIKE` is fine for substring search over a moderate table. Beyond that I'd move to Postgres full-text search (`tsvector` + GIN, with ranking), or a dedicated search engine fed by change events.
- **Reads.** Route list and detail reads to read replicas. Cache reference data such as `/meta` and `/users` with HTTP caching headers (`ETag`) or Redis.
- **Multi-tenancy and auth.** At this scale there would be many teams. That needs a `workspace_id` on every row (and in every index), row-level authorisation, and per-tenant and per-user rate limits instead of per-IP ones.
- **Rate limiting.** Redis would need high availability (replica + Sentinel or a managed cluster) so that fallback mode stays rare. Coarse limits (WAF/CDN) belong at the edge, with the app keeping the fine-grained, per-user ones.
- **Frontend delivery.** Serve the static assets from a CDN. Make the API URL a runtime setting instead of a build-time constant, so one image can be promoted across environments.

## Time spent and use of AI

- **Time.** Measured from the git history:
  - About **1 h 40 min** for the core requirements, from the first commit to working CRUD, filters, search, validation, error handling, tests, CI and docs.
  - About **30 min** more for the extras: rate limiting, extra middleware, optimistic locking, frontend unit tests and the doc updates.
  - Planning beforehand isn't included in these numbers.
- **AI usage.** I used an AI coding assistant (Claude Code) as a pair programmer for planning, implementation and review.
  - The plan went through two review rounds before any code was written. Several issues in this document came out of those reviews, including the CORS/500 ordering, the FK race, savepoint isolation, readiness vs. Redis, and chunked bodies.
  - I reviewed every change, ran the full test suites, and exercised the UI end to end in a browser against the Docker stack before committing.
