#!/bin/sh
# Menu to restart, rebuild or stop varuna's containers (Linux / macOS).
# First time on a fresh checkout: chmod +x manage.sh
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then
  exec python3 scripts/manage.py "$@"
fi
exec python scripts/manage.py "$@"
