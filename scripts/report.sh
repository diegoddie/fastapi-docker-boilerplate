#!/usr/bin/env bash

set -euo pipefail

uv run coverage combine || true
uv run coverage html
uv run coverage report
