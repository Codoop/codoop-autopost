#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$ROOT/skills/codoop-autopost"
AGENT="auto"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent) AGENT="$2"; shift ;;
    --agent=*) AGENT="${1#*=}" ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) echo "Usage: install-skill.sh [--agent codex|claude|all] [--dry-run]"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
  shift
done

install_to() {
  local target="$1"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] copy $SOURCE -> $target/codoop-autopost"
    return
  fi
  mkdir -p "$target"
  cp -R "$SOURCE" "$target/"
  echo "Installed codoop-autopost to $target/codoop-autopost"
}

if [[ "$AGENT" == "auto" || "$AGENT" == "codex" || "$AGENT" == "all" ]]; then
  install_to "${CODEX_HOME:-$HOME/.codex}/skills"
fi
if [[ "$AGENT" == "auto" || "$AGENT" == "claude" || "$AGENT" == "all" ]]; then
  install_to "${CLAUDE_HOME:-$HOME/.claude}/skills"
fi
