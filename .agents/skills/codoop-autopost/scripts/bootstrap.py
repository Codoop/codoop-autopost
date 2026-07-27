#!/usr/bin/env python3
"""Fetch the MIT-licensed last30days runtime into this Skill's private vendor directory."""

import argparse
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]
VENDOR = ROOT / "vendor" / "last30days"
REPOSITORY = "https://github.com/mvanhorn/last30days-skill.git"
VERSION = "v3.3.0"


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize the bundled last30days runtime.")
    parser.parse_args()
    if (VENDOR / "scripts" / "last30days.py").is_file():
        print(f"last30days already available at {VENDOR}")
        return 0
    VENDOR.parent.mkdir(exist_ok=True)
    subprocess.run(["git", "clone", "--depth", "1", "--branch", VERSION, REPOSITORY, str(VENDOR)], check=True)
    print(f"Installed last30days {VERSION} at {VENDOR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
