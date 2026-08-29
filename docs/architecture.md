# Architecture and engineering decisions

## System context

The FastAPI application is a single stateless HTTP service. PostgreSQL owns durable
state. API users obtain signed bearer tokens and interact with versioned `/api/v1`
routes. Prometheus can scrape metrics, while container tooling uses separate liveness
and readiness probes.

```text
client
  │ HTTPS / bearer token
  ▼
request ID → rate limit → FastAPI router → authorization
                                      │
                                      ▼
                              business service
                                │           │
                                ▼           ▼
                         repository      audit event
                                └─────┬─────┘
                                      ▼
                                  PostgreSQL
```

TLS is expected to terminate at a reverse proxy or managed load balancer. The application
does not pretend to implement TLS itself.

## Boundaries

- `routers/` translates HTTP requests and responses.
- `dependencies.py` creates request-scoped sessions and resolves authorization.
- `services.py` owns business rules and transaction boundaries.
- `repositories.py` contains SQLAlchemy queries.
- `models.py` describes relational persistence.
- `schemas.py` validates untrusted input and controls serialized output.
- `security.py` owns password hashing and JWT validation.

This separation lets API tests exercise the full stack while keeping persistence and
security logic independently understandable.

## Data model

### Users

Users have a unique normalized username, an Argon2 password hash, an active flag, and
an `admin` or `reader` role. Administrators manage users and mutate students. Readers
can retrieve students but cannot modify state.

### Students

The public student ID is the primary key. Each row stores a version number. Updates and
deletes include the version observed by the client and use a conditional SQL statement.
If the row changed in the meantime, the API returns HTTP 409 instead of losing an update.

### Audit events

Every API mutation adds an append-only event in the same database transaction. The event
captures the actor, action, resource, timestamp, and structured details. Authentication
attempts are deliberately not stored because a dedicated security-event pipeline would
have different retention and access requirements.

## Security model

- Passwords use the recommended Argon2 configuration from `pwdlib`.
- JWTs require issuer, audience, expiry, issued-at, subject, and token ID claims.
- Authorization checks the current database record, so disabling a user takes effect
  even while an old token has not expired.
- Production startup rejects default or undersized secrets.
- Input models forbid undeclared fields and constrain identifiers and lengths.
- Responses add request IDs and basic browser hardening headers.
- Rate limiting slows accidental or low-volume abuse in one process.

The service does not include refresh tokens, token revocation, MFA, or distributed rate
limiting. Those belong in a dedicated identity provider or shared edge layer for a larger
system.

## Reliability and operations

- Alembic is the only production schema-management path.
- SQLAlchemy checks pooled connections before use.
- Readiness executes a database query; liveness does not depend on downstream services.
- PostgreSQL writes and the corresponding audit event share one transaction.
- Compose waits for PostgreSQL to become healthy before starting the API.
- The container runs without root privileges and handles migrations before Uvicorn.
- Structured logs include method, path, status, duration, client, and request ID.
- Prometheus counters and histograms avoid raw URL labels to prevent unbounded metric
  cardinality.

## Testing strategy

- Domain tests cover concurrency and task transitions.
- API tests cover real middleware, validation, authentication, authorization, CRUD,
  optimistic conflicts, audits, metrics, and rate limits.
- A dedicated CI job applies Alembic migrations to PostgreSQL and runs a real round trip.
- Another CI job checks that SQLAlchemy metadata does not drift from the migration head.
- The container job validates that the deployment artifact builds from a clean checkout.

SQLite is used for most API tests because it is fast and deterministic. It is not treated
as proof of PostgreSQL compatibility; the separate PostgreSQL job provides that evidence.
