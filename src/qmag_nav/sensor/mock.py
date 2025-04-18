"""Deterministic mock sensor driver for tests."""

from __future__ import annotations

from typing import List, Tuple


class MockSensorDriver:
    """Return pre‑programmed magnetic vectors in sequence, cycling forever."""

    def __init__(self, samples: List[Tuple[float, float, float]]):
        if not samples:
            raise ValueError("At least one sample required")
        self._samples: List[Tuple[float, float, float]] = samples
        self._idx: int = 0

    def read(self) -> Tuple[float, float, float]:  # noqa: D401
        sample = self._samples[self._idx]
        self._idx = (self._idx + 1) % len(self._samples)
        return sample
