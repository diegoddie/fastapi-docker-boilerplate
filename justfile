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

# Check the locked dependencies against the known vulnerabilities
[group("qa")]
audit:
    ./scripts/audit.sh

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

# Create a new Alembic migration from the models, in the main branch
[group("fastapi")]
forge MESSAGE:
    uv run alembic revision --autogenerate --head main@head -m "{{MESSAGE}}"

# Create a new Alembic migration in the branch of an optional module
[group("fastapi")]
forge-module MODULE MESSAGE:
    uv run alembic revision --autogenerate --head {{MODULE}}@head -m "{{MESSAGE}}"

# Apply all pending migrations, of every branch
[group("fastapi")]
migrate-forward:
    uv run alembic upgrade heads

# Merge branches that diverged (e.g. after a template update) into one head
[group("fastapi")]
migrate-merge:
    uv run alembic merge heads -m "merge heads"

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
# copier:celery:start

# Run a Celery worker (restart it after changing the code)
[group("jobs")]
worker:
    uv run celery --app app.jobs.worker worker

# Run Celery beat, which sends the scheduled tasks
[group("jobs")]
beat:
    uv run celery --app app.jobs.worker beat
# copier:celery:end
# copier:template:start

# Render the working tree into a project with an answers file (template only)
[group("template")]
template-render ANSWERS DESTINATION:
    rm -rf {{DESTINATION}}
    uv run --group template copier copy --trust --defaults --vcs-ref HEAD --data-file {{ANSWERS}} . {{DESTINATION}}
    uv run python .copier/check_render.py {{DESTINATION}}
# copier:template:end
