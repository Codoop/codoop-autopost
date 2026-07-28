#!/usr/bin/env python3
"""Create a private codoop-autopost configuration template without overwriting it."""

import argparse
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create config.toml for a content-operations workspace.")
    parser.add_argument("--workspace", default=".", help="content-operations workspace (default: current directory)")
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    for name in ("content-leads", "content-tickets"):
        (workspace / name).mkdir(exist_ok=True)
    destination = workspace / "config.toml"
    if destination.exists():
        print(f"Preserved existing {destination}")
        return 0
    source = Path(__file__).parents[1] / "config.example.toml"
    shutil.copyfile(source, destination)
    destination.chmod(0o600)
    print(f"Created {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
