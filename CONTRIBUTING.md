# Contributing

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --editable ".[dev]"
```

Before opening a pull request, run:

```bash
make quality
make test
```

If a persistence model changes, create and review an Alembic revision:

```bash
alembic revision --autogenerate -m "describe the schema change"
alembic upgrade head
alembic check
```

## Pull requests

- Keep changes focused and explain the behavior being changed.
- Add tests for success, failure, and authorization paths.
- Do not commit `.env`, databases, access tokens, or generated credentials.
- Preserve stable error codes unless the pull request documents a breaking API change.
- Update the README and architecture notes when public behavior changes.
