#!/bin/sh
set -eu
SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
exec "$SCRIPT_DIR/../../_shared/run-python.sh" "$SCRIPT_DIR/content_ticket.py" "$@"
