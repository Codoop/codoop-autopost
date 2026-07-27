#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$ROOT/skills"
AGENT="auto"
DRY_RUN=0
SKILL="all"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent) AGENT="$2"; shift ;;
    --agent=*) AGENT="${1#*=}" ;;
    --skill) SKILL="$2"; shift ;;
    --skill=*) SKILL="${1#*=}" ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) echo "Usage: install-skill.sh [--agent codex|claude|all] [--skill name|all] [--dry-run]"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
  shift
done

install_to() {
  local target="$1" skill="$2"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] copy $SOURCE/$skill -> $target/$skill"
    return
  fi
  mkdir -p "$target"
  cp -R "$SOURCE/$skill" "$target/"
  echo "Installed $skill to $target/$skill"
}

SKILLS=("$SKILL")
if [[ "$SKILL" == "all" ]]; then
  SKILLS=(codoop-autopost codoop-last30days codoop-firecrawl codoop-social-content codoop-copy-editing codoop-x-twitter)
fi

if [[ "$AGENT" == "auto" || "$AGENT" == "codex" || "$AGENT" == "all" ]]; then
  for skill in "${SKILLS[@]}"; do install_to "${CODEX_HOME:-$HOME/.codex}/skills" "$skill"; done
fi
if [[ "$AGENT" == "auto" || "$AGENT" == "claude" || "$AGENT" == "all" ]]; then
  for skill in "${SKILLS[@]}"; do install_to "${CLAUDE_HOME:-$HOME/.claude}/skills" "$skill"; done
fi
