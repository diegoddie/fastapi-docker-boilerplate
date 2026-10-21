#!/usr/bin/env bash

set -euo pipefail

# Why: one worker per CPU (each with its own test database) halves the suite
# time; arguments come after, so `just test -n 0` runs it in a single process.
uv run pytest --cov -n auto "$@"
