"""Magnetometer abstraction with optional moving‑average filter."""

from __future__ import annotations

import collections
from typing import Deque, Iterable, Protocol, Tuple

from qmag_nav.models.sensor import CalibrationParams


class _Driver(Protocol):
    """Simple protocol that real / mock sensor drivers must follow."""

    def read(self) -> Tuple[float, float, float]:  # noqa: D401
        """Return a raw magnetic vector in nano‑tesla (Bx, By, Bz)."""


class MovingAverageFilter:
    """A sliding‑window moving average over the incoming sensor stream."""

    def __init__(
        self,
        window: int = 1,
        *,
        initial: Iterable[Tuple[float, float, float]] | None = None,
    ) -> None:
        """Create a moving‑average filter.

        Parameters
        ----------
        window:
            Sliding‑window length ``N``.  Must be positive.
        initial:
            Optional iterable of *up to* ``N`` samples used to warm‑start the
            internal buffer.  This small convenience enables **hot‑restart**
            scenarios where we would like to persist the filter state across
            application restarts.
        """

        if window <= 0:
            raise ValueError("Window size must be > 0")

        self.window: int = window
        self._buf: Deque[Tuple[float, float, float]] = collections.deque(
            maxlen=window
        )

        if initial is not None:
            # Only the *most recent* ``window`` elements are relevant.
            for sample in list(initial)[-window:]:
                self._buf.append(sample)

    def update(self, sample: Tuple[float, float, float]) -> Tuple[float, float, float]:  # noqa: D401
        self._buf.append(sample)
        bx = sum(v[0] for v in self._buf) / len(self._buf)
        by = sum(v[1] for v in self._buf) / len(self._buf)
        bz = sum(v[2] for v in self._buf) / len(self._buf)
        return (bx, by, bz)

    @property
    def buffer(self) -> Iterable[Tuple[float, float, float]]:  # noqa: D401
        return tuple(self._buf)

    # ------------------------------------------------------------------
    # (De)serialisation helpers – aid hot‑restart persistence
    # ------------------------------------------------------------------

    def snapshot(self) -> list[Tuple[float, float, float]]:  # noqa: D401
        """Return a *copy* of the internal buffer suitable for persistence."""

        return list(self._buf)

    @classmethod
    def from_snapshot(cls, window: int, state: Iterable[Tuple[float, float, float]]):  # noqa: D401
        """Reconstruct a filter instance from a previously captured *state*."""

        return cls(window=window, initial=state)


class Magnetometer:
    """High‑level sensor facade used by the navigation filter."""

    def __init__(
        self,
        driver: _Driver,
        calibration: CalibrationParams | None = None,
        filter_window: int = 1,
    ) -> None:
        self._driver: _Driver = driver
        self._cal: CalibrationParams | None = calibration
        self._filter = MovingAverageFilter(filter_window)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read(self) -> Tuple[float, float, float]:  # noqa: D401
        """Return a calibrated / smoothed magnetic vector (nano‑tesla)."""

        raw = self._driver.read()
        if self._cal is not None:
            raw = self._cal.apply(raw)
        return self._filter.update(raw)
