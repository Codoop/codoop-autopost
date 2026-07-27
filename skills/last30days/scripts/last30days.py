#!/usr/bin/env python3
"""Standalone last30days launcher for the codoop skill pack."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(os.environ.get("CODOOP_LAST30DAYS_DIR", Path.home() / ".local" / "share" / "last30days" / "runtime"))
REPOSITORY = "https://github.com/mvanhorn/last30days-skill.git"
VERSION = "v3.3.0"


def ensure() -> Path:
    script = ROOT / "scripts" / "last30days.py"
    if script.is_file():
        return script
    ROOT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--depth", "1", "--branch", VERSION, REPOSITORY, str(ROOT)], check=True)
    return script


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover recent discussion candidates.")
    parser.add_argument("topic", nargs="?")
    parser.add_argument("--init", action="store_true")
    args = parser.parse_args()
    script = ensure()
    if args.init:
        print(f"last30days ready at {script.parent.parent}")
        return 0
    if not args.topic:
        parser.error("topic is required unless --init is used")
    return subprocess.run([sys.executable, str(script), args.topic, "--emit=json"], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
