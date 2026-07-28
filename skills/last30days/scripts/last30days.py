#!/usr/bin/env python3
"""Run the vendored last30days runtime for the codoop skill pack."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def ensure() -> Path:
    configured = os.environ.get("CODOOP_LAST30DAYS_DIR")
    if configured:
        script = Path(configured) / "skills" / "last30days" / "scripts" / "last30days.py"
    else:
        script = Path(__file__).parents[1] / "vendor" / "scripts" / "last30days.py"
    if not script.is_file():
        raise RuntimeError("last30days runtime is missing; reinstall codoop-autopost")
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
