#!/usr/bin/env bash

set -euo pipefail

# Check every locked dependency (all groups) against the known vulnerabilities.
requirements="$(mktemp)"
trap 'rm -f "$requirements"' EXIT
uv export --frozen --all-groups --no-emit-project --quiet --output-file "$requirements"
uv run --group test pip-audit --requirement "$requirements" --disable-pip --progress-spinner off
