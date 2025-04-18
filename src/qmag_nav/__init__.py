"""Quantum Magnetic Navigation package.

Minimal but functional implementation following the public roadmap under
`research/implementation.md`.  The emphasis is on providing a clean structure
that can be exercised by the accompanying pytest suite.  Complex scientific
details are intentionally simplified – the goal is correctness relative to the
test‑suite, not high‑fidelity physics.
"""

from __future__ import annotations

# Semantic version of this reference implementation.
__version__: str = "0.1.0"

# Re‑export a handful of frequently‑used symbols for convenience so that test
# code (and future users) can simply ``from qmag_nav import LatLon``.
from qmag_nav.models.geo import LatLon, ECEF, MagneticVector  # noqa: E402, F401
from qmag_nav.filter.ekf import NavEKF  # noqa: E402, F401

__all__ = [
    "__version__",
    # geo
    "LatLon",
    "ECEF",
    "MagneticVector",
    # filter
    "NavEKF",
]
