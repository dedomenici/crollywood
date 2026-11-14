#!/usr/bin/env python3
"""Compatibility wrapper. Duration presets now live in build_duration_presets.py."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name("build_duration_presets.py")), run_name="__main__")
