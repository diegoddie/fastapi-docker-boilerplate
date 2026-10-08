#!/usr/bin/env bash

set -euo pipefail

# Why: parallel workers cost more than they save on a small suite; pass `-n auto`
# (e.g. `just test -n auto`) once the suite grows.
uv run pytest --cov "$@"
