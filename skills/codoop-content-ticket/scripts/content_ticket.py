#!/usr/bin/env python3
"""Run the bundled content-ticket CLI."""

from pathlib import Path
import runpy


runpy.run_path(Path(__file__).parents[2] / "codoop-autopost" / "scripts" / "autopost.py", run_name="__main__")
