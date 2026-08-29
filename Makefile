.PHONY: install quality test run migrate

install:
	python -m pip install --editable ".[dev]"

quality:
	ruff check .
	ruff format --check .
	mypy src
	uv lock --check
	pip-audit --skip-editable

test:
	pytest --cov --cov-report=term-missing

run:
	enterprise-api

migrate:
	alembic upgrade head
