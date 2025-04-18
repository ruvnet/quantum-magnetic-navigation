"""Basic sanity tests to verify the project structure is working."""

from __future__ import annotations

import importlib
import sys
from typing import Any


def test_import_qmag_nav() -> None:
    """Verify that the qmag_nav package can be imported."""
    import qmag_nav

    assert qmag_nav is not None
    assert hasattr(qmag_nav, "__version__")


def test_python_version() -> None:
    """Verify that we're running on Python 3.11+."""
    assert sys.version_info.major == 3
    assert sys.version_info.minor >= 11, "Python 3.11+ is required"


def test_package_structure() -> None:
    """Verify that the expected subpackages are importable."""
    subpackages = [
        "filter",
        "mapping",
        "models",
        "sensor",
        "service",
    ]
    
    for subpackage in subpackages:
        module_name = f"qmag_nav.{subpackage}"
        module = importlib.import_module(module_name)
        assert module is not None, f"Failed to import {module_name}"