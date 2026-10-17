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

**Next.js + TypeScript + TanStack Query.**
- TypeScript lets me generate the API types from the backend's OpenAPI schema. Frontend and backend can't drift silently: CI regenerates the types and fails on any diff.
- TanStack Query handles caching, cancellation, refetching after mutations and keeping the previous page visible while the next one loads. Otherwise that would be hand-written `useEffect` code.

**Docker Compose.** A reviewer can run the database, API and web app with one command, without installing Python or Postgres locally.

## 2. How did you structure your application and why?

The backend is layered, and each layer has one job:

```
HTTP request
 → middleware (request id, CORS, catch-all error handler)
 → api/v1/*.py            translate HTTP ⇄ schemas, nothing else
 → services/issue_service business rules: assignee must exist, status transitions, timestamps
 → repositories/*         all SQL; never commit
 → unit of work            owns the transaction; translates DB constraint errors into domain errors
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
  - `core/constants.py` holds every fixed value: enums, limits, error codes, header names.
  - `core/config.py` holds only values that change per environment.
  - The frontend doesn't duplicate domain constants. Types come from the generated schema, and runtime limits come from `GET /api/v1/meta`.
  - The UI's label maps are typed `Record<IssueStatus, string>`. If the backend adds a status, the frontend stops compiling until someone gives it a label.
- **One error contract.**
  - Every failure renders as `{"error": {code, message, details, request_id}}`.
  - That includes Starlette's own 404/405 responses, validation errors, database outages (503) and unexpected exceptions (generic 500, traceback logged only).
- **Versioning by URL prefix (`/api/v1`).** Each version has its own router package, so a future `v2` could change request/response shapes and still share the services underneath. `/health` and `/ready` stay unversioned because they describe the process, not the API.

The frontend is split into:

- `app/`: routes only
- `views/`: page-level client components
- `components/`: presentational components
- `hooks/`: data and URL state
- `lib/`: API client, generated types, pure helpers

All data is fetched in the browser, for two reasons. There is one API URL to configure. And the API sees real client IPs, which per-IP rate limiting needs.

## 3. What was the most difficult part of the task?

Making the error contract hold everywhere, not just in the happy-path handlers. Three things weren't obvious:

1. **Unhandled 500s lose their CORS headers.**
   - Starlette runs a bare `Exception` handler in `ServerErrorMiddleware`, which sits *outside* all user middleware, including CORS.
   - The browser would see a CORS failure instead of the JSON error.
   - I catch unexpected exceptions in my own small middleware placed *inside* CORS. A test asserts that a forced 500 still carries `Access-Control-Allow-Origin`.
2. **Check-then-write races.**
   - The service checks that an assignee exists, but the user can be deleted before the INSERT.
   - The foreign-key violation would then surface as a database error.
   - The unit of work translates Postgres SQLSTATE codes into domain errors:
     - an FK violation on the assignee constraint becomes `422 INVALID_ASSIGNEE`
     - unique violations become `409`
   - Only real connectivity failures map to `503`. A test simulates the race.
3. **Test isolation with real commits.**
   - The service commits, so wrapping each test in a transaction isn't enough on its own.
   - The test session joins an outer transaction with `join_transaction_mode="create_savepoint"`. Application `commit()` calls then only release savepoints, and the outer transaction is rolled back after each test.

On the frontend, the hardest detail was the debounced search box. It has to stay in sync when filters are cleared or the user presses Back, without an effect that re-submits a stale term. I solved it by debouncing the *callback* rather than the value, and by adjusting local state during render when the URL value changes.

## 4. What would you improve if you had another two days?

- **Authentication and ownership.** Real users, a reporter field, and permissions on edit and delete.
- **Activity history and comments.** Today an issue has no record of who changed what.
- **Frontend tests.** Component tests for the form and filters, and one Playwright smoke test (create → filter → delete) in CI. I ran these flows by hand against the Docker stack, but they aren't automated.
- **Optimistic concurrency.** A `version` column so two people editing the same issue get a conflict instead of a silent last-write-wins.
- **Cursor (keyset) pagination** for the list, plus a "my issues" / "unassigned" quick filter.

## 5. If this application grew to 100,000 users, what parts of your implementation would you reconsider?

Some of this is already designed in:
- The API is stateless, so it scales horizontally behind a load balancer.
- Connection pool sizes are configurable.
- The list query has composite indexes matching the default sort, and trigram indexes for search.
- `total` is counted without the join and sort.
- Logs are structured JSON with request ids, so they can be correlated across replicas.

What I'd reconsider:

- **Database connections.** Each API worker has its own pool, so many replicas × workers can exhaust Postgres connections. I'd put **PgBouncer** (transaction pooling) in front of Postgres. I'd also consider an async driver (`asyncpg` / SQLAlchemy async) if request latency becomes I/O-bound.
- **Migrations at startup.** Several replicas starting together would race to migrate. Migrations should be a separate one-off job in the deploy pipeline, with changes written to be backwards-compatible (expand → migrate → contract).
- **Pagination.** Offset pagination gets slower as the offset grows. Rows also shift between pages under concurrent writes. I'd switch to keyset pagination on `(created_at, id)`, which the existing index already supports.
- **Search.** Trigram `ILIKE` is fine for substring search over a moderate table. Beyond that I'd move to Postgres full-text search (`tsvector` + GIN, with ranking), or a dedicated search engine fed by change events.
- **Reads.** Route list and detail reads to read replicas. Cache hot reference data such as `/meta` and `/users` with HTTP caching headers (`ETag`) or Redis.
- **Multi-tenancy and auth.** At this scale there would be many teams. That needs a `workspace_id` on every row (and in every index), row-level authorisation, and per-tenant rate limits.
- **Protection and observability.** Add rate limiting (shared state in Redis), request size limits, OpenTelemetry traces and metrics, and alerting on error rates and p95 latency.
- **Frontend delivery.** Serve the static assets from a CDN. Make the API URL a runtime setting instead of a build-time constant, so one image can be promoted across environments.

## Time spent and use of AI

- **Time.** The core requirements took about 2 hours of focused work, from the first commit to a working stack with tests and CI. The git history timestamps reflect this.
- **AI usage.** I used an AI coding assistant (Claude Code) as a pair programmer for planning, scaffolding and review. The plan went through two review rounds before implementation, covering the CORS/500 ordering, the FK race and savepoint isolation described above. I reviewed every change, ran the full test suite, and exercised the UI end to end in a browser against the Docker stack before committing.
