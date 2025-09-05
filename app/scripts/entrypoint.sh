#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/outputs /app/data
exec "$@"
