# Python Enterprise Programming Project

[![CI](https://github.com/DevWithX/Python-Enterprising-Programming-Project/actions/workflows/ci.yml/badge.svg)](https://github.com/DevWithX/Python-Enterprising-Programming-Project/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

A tested backend portfolio project combining concurrent processing, explicit design
patterns, and a deployable student-management API. The API uses FastAPI, SQLAlchemy,
PostgreSQL, Alembic, JWT authentication, role-based access, audit trails, structured
logging, Prometheus metrics, and Docker Compose.

The repository is intentionally honest about its boundaries. It demonstrates
production-style engineering practices without claiming that one containerized service
is a distributed enterprise platform.

## What this project proves

| Area | Implementation | Evidence |
| --- | --- | --- |
| API design | Versioned REST-style CRUD, pagination, search, stable errors, OpenAPI | API and integration tests |
| Security | Argon2 password hashing, signed JWTs, admin/reader RBAC, validation, rate limits | Authentication and authorization tests |
| Data | SQLAlchemy 2, PostgreSQL, SQLite test adapter, optimistic concurrency | PostgreSQL CI service and conflict tests |
| Delivery | Locked dependencies, rootless image, Compose, Alembic migrations | Container-build and migration CI jobs |
| Operations | JSON logs, request IDs, liveness/readiness probes, Prometheus metrics | Endpoint tests and `/metrics` output |
| Quality | Ruff, strict mypy, branch coverage, multi-version tests | Required GitHub Actions quality gates |
| Fundamentals | Threaded sensor aggregation and task design patterns | Deterministic unit and stress tests |

The suite contains 40 tests and currently exercises 93% of the Python codebase with
branch coverage. CI runs
the regular suite on Python 3.11, 3.12, and 3.13, verifies PostgreSQL separately, checks
migration drift, and builds the container image.

## Architecture

```mermaid
flowchart LR
    Client[API client] --> Middleware[Request ID · rate limit · metrics]
    Middleware --> API[FastAPI routers]
    API --> Auth[JWT + RBAC]
    API --> Service[Business services]
    Service --> ORM[SQLAlchemy repositories]
    ORM --> DB[(PostgreSQL)]
    Service --> Audit[(Audit events)]
    Middleware --> Prometheus[/Prometheus metrics/]
    Alembic[Alembic migrations] --> DB
```

The HTTP, business, and persistence layers are separate. SQLite provides a fast local
test adapter; PostgreSQL is the deployment database and is exercised in CI. See
[`docs/architecture.md`](docs/architecture.md) for design decisions and trade-offs.

## Run with Docker Compose

Requirements: Docker Engine with the Compose plugin.

```bash
cp .env.example .env
```

Replace every placeholder in `.env`. Generate a JWT secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Then start the API and PostgreSQL:

```bash
docker compose up --build
```

Compose waits for PostgreSQL's health check, runs `alembic upgrade head`, starts the API
as a non-root user, and publishes port 8000.

- Interactive API: <http://127.0.0.1:8000/docs>
- OpenAPI schema: <http://127.0.0.1:8000/openapi.json>
- Readiness: <http://127.0.0.1:8000/health/ready>
- Metrics: <http://127.0.0.1:8000/metrics>

## Run locally with SQLite

```bash
python3 -m venv .venv
source .venv/bin/activate             # Windows: .venv\Scripts\activate
python -m pip install --editable ".[dev]"

export EPP_ENVIRONMENT=development
export EPP_DATABASE_URL=sqlite+pysqlite:///./enterprise.db
export EPP_JWT_SECRET=local-development-secret-change-me
export EPP_BOOTSTRAP_ADMIN_PASSWORD=correct-horse-battery-staple

alembic upgrade head
enterprise-api --reload
```

The committed `uv.lock` captures the complete development resolution, while
`requirements.lock` pins the smaller production dependency set used by Docker.

The admin account is created only when it does not already exist. Passwords are stored
as Argon2 hashes, never as plaintext.

## Authenticate and use the API

Request a 30-minute bearer token:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"correct-horse-battery-staple"}'
```

Use the returned token to create a student:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/students \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"student_id":"S001","name":"Amina Patel","course":"Computer Science"}'
```

Updates and deletes require the current `version`. This optimistic-concurrency check
prevents one client from silently overwriting another client's changes.

### Main endpoints

| Method | Route | Access | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/v1/auth/token` | Public | Exchange credentials for a JWT |
| `GET` | `/api/v1/auth/me` | Authenticated | Inspect the current user |
| `GET` | `/api/v1/students` | Authenticated | Search and paginate students |
| `GET` | `/api/v1/students/{id}` | Authenticated | Retrieve a student |
| `POST` | `/api/v1/students` | Admin | Create a student |
| `PUT` | `/api/v1/students/{id}` | Admin | Version-checked update |
| `DELETE` | `/api/v1/students/{id}` | Admin | Version-checked deletion |
| `GET` | `/api/v1/users` | Admin | List API users |
| `POST` | `/api/v1/users` | Admin | Create an admin or reader |
| `PATCH` | `/api/v1/users/{username}` | Admin | Change role, activity, or password |
| `GET` | `/api/v1/audit-events` | Admin | Review mutation audit events |

Expected failures have a consistent shape and include the request ID:

```json
{
  "error": {
    "code": "conflict",
    "message": "Student was modified; refresh it and retry with the current version",
    "request_id": "08c0198b-52e1-4ce4-b4f5-f86ea7a442de"
  }
}
```

## Configuration

All runtime settings use the `EPP_` prefix.

| Variable | Purpose | Default |
| --- | --- | --- |
| `EPP_ENVIRONMENT` | `development`, `test`, or `production` | `development` |
| `EPP_DATABASE_URL` | SQLAlchemy database URL | Local SQLite file |
| `EPP_JWT_SECRET` | JWT signing secret | Development-only value |
| `EPP_BOOTSTRAP_ADMIN_USERNAME` | Initial administrator | `admin` |
| `EPP_BOOTSTRAP_ADMIN_PASSWORD` | Initial administrator password | Unset |
| `EPP_ALLOWED_ORIGINS` | JSON list of allowed CORS origins | `[]` |
| `EPP_RATE_LIMIT_PER_MINUTE` | Per-client fixed-window limit | `120` |
| `EPP_ACCESS_TOKEN_MINUTES` | JWT lifetime | `30` |
| `EPP_JSON_LOGS` | Emit machine-readable logs | `true` |

Production mode refuses the development JWT secret, secrets shorter than 32 characters,
and deployments without an initial administrator password.

## Quality and verification

```bash
make quality     # Ruff lint/format plus strict mypy
make test        # Pytest with branch coverage and a 90% floor
```

Run migrations and verify that model changes have a migration:

```bash
alembic upgrade head
alembic check
```

The PostgreSQL integration test is opt-in locally:

```bash
export EPP_TEST_POSTGRES_URL='postgresql+psycopg://user:pass@localhost/test_database'
pytest -m integration -v
```

## Original programming demonstrations

The repository still contains the two finite, dependency-independent demonstrations:

```bash
enterprise-project sensor-demo --sensors 3 --readings 100 --workers 4
enterprise-project task-demo
```

- `SensorAggregator` uses a queue, fixed workers, locking, graceful shutdown, and
  immutable statistics snapshots.
- The task workflow demonstrates factory, observer, and singleton patterns while
  enforcing valid lifecycle transitions.

## Project structure

```text
.
├── .github/workflows/ci.yml
├── docker/entrypoint.sh
├── docs/architecture.md
├── migrations/versions/0001_initial_schema.py
├── src/enterprise_programming/
│   ├── api/
│   │   ├── routers/
│   │   ├── app.py
│   │   ├── models.py
│   │   ├── security.py
│   │   └── services.py
│   ├── sensor.py
│   └── tasks.py
├── tests/api/
├── tests/test_postgres_integration.py
├── compose.yaml
├── Dockerfile
└── pyproject.toml
```

## Honest production boundaries

- The rate limiter is per process; a horizontally scaled deployment should use an API
  gateway or Redis-backed limiter.
- JWTs are short-lived but there is no refresh-token or revocation service.
- Docker Compose is a reproducible single-host deployment, not Kubernetes or cloud
  infrastructure.
- Metrics are exposed for Prometheus scraping, but dashboards and alert rules are not
  bundled.

## CV-ready summary

> Built and containerized an authenticated Python backend using FastAPI, PostgreSQL,
> SQLAlchemy, Alembic, and Docker Compose. Implemented Argon2/JWT security, RBAC,
> optimistic concurrency, audit trails, structured logging, Prometheus metrics, and
> health checks; enforced quality through 40 tests, 93% coverage, strict type checking,
> migration checks, PostgreSQL integration tests, and multi-version CI.

## Author

Xichavelo Refuge Rikhotso
