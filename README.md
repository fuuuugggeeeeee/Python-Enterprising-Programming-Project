# Python Enterprise Programming Project

[![CI](https://github.com/DevWithX/Python-Enterprising-Programming-Project/actions/workflows/ci.yml/badge.svg)](https://github.com/DevWithX/Python-Enterprising-Programming-Project/actions/workflows/ci.yml)

A standard-library-only Python project that demonstrates three practical backend
concepts: concurrent work processing, stateful domain design, and a persistent JSON
HTTP API. Every component is runnable, importable, and covered by automated tests.

This is deliberately a compact learning project—not a claim that a single-process
demo replaces a production message broker, database, or web framework. The goal is
to make the engineering decisions visible and verifiable.

## What is implemented

| Component | Demonstrates | Verifiable behavior |
| --- | --- | --- |
| Sensor engine | Worker threads, queues, locks, lifecycle management | Concurrent aggregation with exact count/min/max/average statistics |
| Task workflow | Factory, observer, and singleton patterns | Validated state transitions and notification events |
| Student service | Layered design, CRUD, persistence, HTTP | JSON REST-style API with atomic file writes and structured errors |

The project uses only the Python standard library and supports Python 3.9 or newer.

## Quick start

```bash
git clone https://github.com/DevWithX/Python-Enterprising-Programming-Project.git
cd Python-Enterprising-Programming-Project
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install --editable .
```

Run the two finite demos:

```bash
enterprise-project sensor-demo --sensors 3 --readings 100 --workers 4
enterprise-project task-demo
```

Start the student API (data is persisted to `students.json`):

```bash
enterprise-project student-api --host 127.0.0.1 --port 8000 --data students.json
```

You can also run the package without installing a console command:

```bash
python -m enterprise_programming sensor-demo
```

## Sensor processing engine

`SensorAggregator` owns a fixed worker pool and a thread-safe queue. It validates
incoming readings, prevents submissions outside its active lifecycle, waits for all
accepted work during shutdown, and exposes immutable statistics snapshots.

```python
from enterprise_programming.sensor import SensorAggregator, SensorReading

with SensorAggregator(worker_count=2) as engine:
    engine.submit(SensorReading("temperature", 21.5, observed_at=1.0))
    engine.submit(SensorReading("temperature", 22.5, observed_at=2.0))

print(engine.snapshot()["temperature"].average)  # 22.0
```

## Task workflow

The task module makes three classic patterns concrete:

- `TaskFactory` centralizes validation and identifier generation.
- `TaskObserver` receives immutable events when task status changes.
- `TaskManager` provides a synchronized process-wide task registry.

Allowed transitions are enforced. For example, a pending task cannot skip directly
to done, and completed or cancelled tasks are terminal. The singleton is included
as an explicit pattern exercise; dependency injection is usually preferable in a
larger production application.

## Student HTTP API

The HTTP adapter is separated from the service and repository layers. The default
CLI configuration uses `JsonStudentRepository`, which replaces its data file
atomically so an interrupted write does not leave a partially written document.

| Method | Route | Behavior |
| --- | --- | --- |
| `GET` | `/health` | Service health check |
| `GET` | `/students` | List students |
| `GET` | `/students/{id}` | Retrieve one student |
| `POST` | `/students` | Create a student |
| `PUT` | `/students/{id}` | Replace a student's name and course |
| `DELETE` | `/students/{id}` | Delete a student |

Create and retrieve a record:

```bash
curl -i http://127.0.0.1:8000/health

curl -i -X POST http://127.0.0.1:8000/students \
  -H 'Content-Type: application/json' \
  -d '{"student_id":"S001","name":"Amina Patel","course":"Computer Science"}'

curl -i http://127.0.0.1:8000/students/S001
```

Expected client errors use a stable JSON shape and appropriate HTTP status codes:

```json
{
  "error": {
    "code": "student_not_found",
    "message": "Student not found"
  }
}
```

## Tests and continuous integration

Run the complete suite with:

```bash
python -m unittest discover -s tests -v
```

The tests cover concurrency totals, lifecycle rules, task notifications and state
transitions, CRUD behavior, JSON persistence across restarts, and real HTTP requests
against an ephemeral local server. GitHub Actions runs the suite and both CLI demos
on Python 3.9, 3.11, and 3.13 for every push and pull request.

## Project structure

```text
.
├── .github/workflows/ci.yml
├── pyproject.toml
├── src/enterprise_programming/
│   ├── cli.py
│   ├── sensor.py
│   ├── students.py
│   └── tasks.py
└── tests/
    ├── test_cli.py
    ├── test_sensor.py
    ├── test_students.py
    └── test_tasks.py
```

## Deliberate limits

- Sensor processing is in-process; it is not a distributed stream platform.
- Student data uses a locked JSON repository suitable for a demo, not a
  multi-process production database.
- The API has validation and size limits but does not include authentication, TLS,
  rate limiting, schema migration, or production observability.
- Task state exists for the lifetime of one Python process.

These boundaries keep the repository easy to run while making the next production
steps clear: replace adapters with a broker/database/web framework, add telemetry,
and deploy behind authenticated infrastructure.

## Author

Xichavelo Refuge Rikhotso
