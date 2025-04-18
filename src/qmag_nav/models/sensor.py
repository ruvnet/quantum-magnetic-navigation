"""Sensor specification & calibration parameters using Pydantic."""

from __future__ import annotations

from typing import Tuple

from qmag_nav._compat import BaseModel


class SensorSpec(BaseModel):
    """Basic specification of a magnetometer sensor."""

    model: str
    sample_rate_hz: int  # nominal sample rate
    noise_std_nt: float  # 1‑sigma noise in nano‑tesla

    # validation
    @classmethod
    def __get_validators__(cls):  # noqa: D401
        yield cls._validate

    @classmethod
    def _validate(cls, values):  # noqa: D401, ANN001
        if values["sample_rate_hz"] <= 0:
            raise ValueError("sample_rate_hz must be > 0")
        if values["noise_std_nt"] < 0:
            raise ValueError("noise_std_nt must be ≥ 0")
        return values


class CalibrationParams(BaseModel):
    """Simple hard/soft‑iron calibration parameters."""

    offset: Tuple[float, float, float]
    scale: Tuple[float, float, float]

    def apply(self, raw: Tuple[float, float, float]) -> Tuple[float, float, float]:  # noqa: D401
        return tuple((v - o) * s for v, o, s in zip(raw, self.offset, self.scale))  # type: ignore[misc]
