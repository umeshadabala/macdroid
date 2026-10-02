#!/usr/bin/env python3
"""Launcher script for MacDroid — Android on your Mac."""

import sys
from pathlib import Path

# Ensure root directory is on PYTHONPATH
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.main import main

if __name__ == "__main__":
    sys.exit(main())
