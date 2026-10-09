#!/usr/bin/env bash

set -euo pipefail

./scripts/check.sh
# Fail when a model changed without a matching migration (needs the database
# migrated to head: the container entrypoint does it, locally `just migrate-forward`).
uv run alembic check
./scripts/coverage.sh "$@"
./scripts/report.sh
