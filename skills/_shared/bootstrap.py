#!/usr/bin/env python3
"""Fetch the MIT-licensed last30days runtime into this Skill's private vendor directory."""

import argparse
import os
import subprocess
from pathlib import Path


REPOSITORY = "https://github.com/mvanhorn/last30days-skill.git"
VERSION = "v3.3.0"


def vendor_dir(data_home: Path | None = None) -> Path:
    home = data_home or Path(os.environ.get("CODOOP_AUTOPOST_HOME", Path.home() / ".local" / "share" / "codoop-autopost"))
    return home / "last30days"


def vendor_script(data_home: Path | None = None) -> Path:
    return vendor_dir(data_home) / "skills" / "last30days" / "scripts" / "last30days.py"


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize the bundled last30days runtime.")
    parser.parse_args()
    vendor = vendor_dir()
    if vendor_script().is_file():
        print(f"last30days already available at {vendor}")
        return 0
    vendor.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--depth", "1", "--branch", VERSION, REPOSITORY, str(vendor)], check=True)
    print(f"Installed last30days {VERSION} at {vendor}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
