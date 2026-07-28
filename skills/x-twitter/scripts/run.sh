#!/bin/sh
set -eu
SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)

for candidate in "${CODOOP_AUTOPOST_PYTHON:-}" python3.13 python3.12 python3; do
  [ -n "$candidate" ] || continue
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' >/dev/null 2>&1; then
    exec "$candidate" "$SCRIPT_DIR/publish.py" "$@"
  fi
done

echo "x-twitter requires Python 3.12+. On macOS: brew install python@3.12; or set CODOOP_AUTOPOST_PYTHON to its executable." >&2
exit 1
