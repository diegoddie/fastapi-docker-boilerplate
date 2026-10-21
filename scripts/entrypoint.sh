#!/usr/bin/env bash

set -euo pipefail

# Apply pending migrations before starting any command (every branch: the main
# one and those of the optional modules).
alembic upgrade heads

COMMAND=("uv" "run")
COMMAND+=("$@")

echo "Running command: ${COMMAND[*]}"

exec "${COMMAND[@]}"
