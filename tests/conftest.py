"""Pytest configuration for the qmag_nav test‑suite."""

from __future__ import annotations

import pathlib
import sys


# Ensure the *src* directory is importable regardless of how the repository is
# laid out in the test environment.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# The source tree lives in ``quantum-magnetic-navigation/src`` relative to the
# project root.
SRC = ROOT / "src"
if SRC.exists():
    sys.path.insert(0, str(SRC))
