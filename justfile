set dotenv-load
set export

export ALEMBIC_CONFIG := "app/migrations/alembic.ini"

_default:
    just --list

# Check formatting, linting, typing and security without changing files
[group("qa")]
check:
    ./scripts/check.sh

# Fix formatting and linting, then run the type checker
[group("qa")]
fix:
    uv run -m ruff format .
    uv run -m ruff check --fix .
    uv run -m mypy .

# Run all pre-commit hooks
[group("qa")]
precommit:
    uv run -m pre_commit run --all-files

# Install pre-commit git hooks
[group("qa")]
precommit_install:
    uv run -m pre_commit install

# Update pre-commit hooks
[group("qa")]
precommit_update:
    uv run -m pre_commit autoupdate

# Run checks, tests with coverage and the coverage report
[group("testing")]
test *args:
    ./scripts/test.sh {{args}}

# Run tests with coverage
[group("testing")]
coverage *args:
    ./scripts/coverage.sh {{args}}

# Run pytest for debugging (no capture, slowest tests)
[group("testing")]
pytest *args:
    uv run -m pytest --capture=no --durations 10 {{args}}

# Combine coverage data and build the reports
[group("testing")]
report:
    ./scripts/report.sh

# Run the local development server
[group("fastapi")]
runserver:
    uv run uvicorn app.main:app --reload

# Create a new Alembic migration from the models
[group("fastapi")]
forge MESSAGE:
    uv run alembic revision --autogenerate -m "{{MESSAGE}}"

# Apply all pending migrations
[group("fastapi")]
migrate-forward:
    uv run alembic upgrade head

# Roll back migrations to a revision
[group("fastapi")]
migrate-backward REVISION:
    uv run alembic downgrade {{REVISION}}

# Show the migration history
[group("fastapi")]
showmigrations:
    uv run alembic history --indicate-current

# Remove bytecode and test/build debris
[group("lifecycle")]
clean:
    uv run pyclean . -d all -v

# Show outdated packages
[group("lifecycle")]
show-outdated:
    uv tree --all-groups --outdated

# Upgrade all dependencies within the pinned ranges
[group("lifecycle")]
upgrade:
    uv lock --upgrade
    uv sync --group local --group test

# Run a management command, e.g. `just manage users createsuperuser`
[group("managing")]
manage *args:
    uv run -m app.cli.main {{args}}
