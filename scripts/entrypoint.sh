#!/usr/bin/env bash

set -euo pipefail

# Apply pending migrations before starting any command.
alembic upgrade head

COMMAND=("uv" "run")
COMMAND+=("$@")

echo "Running command: ${COMMAND[*]}"

exec "${COMMAND[@]}"
