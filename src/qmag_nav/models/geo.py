"""Geographic data‑structures built on **Pydantic v2** validation.

All numerical inputs are validated to ensure they are within physically
plausible ranges:

* latitude ∈ [-90, 90]°
* longitude ∈ [-180, 180]°

Methods implement *approximate* conversions sufficient for tests and most
simulations (spherical Earth model).
"""

from __future__ import annotations

import math
from typing import Tuple

from qmag_nav._compat import BaseModel

EARTH_RADIUS_M: float = 6_371_000.0  # mean Earth radius in metres (IAU 2000)


class LatLon(BaseModel):
    """Latitude / longitude pair in decimal degrees."""

    lat: float  # degrees
    lon: float  # degrees

    # --------------------------- Validators --------------------------- #

    @staticmethod
    def _check_lat(lat: float) -> float:  # noqa: D401, ANN001
        if not -90.0 <= lat <= 90.0:
            raise ValueError("Latitude must be in [-90, 90]°")
        return lat

    @staticmethod
    def _check_lon(lon: float) -> float:  # noqa: D401, ANN001
        if not -180.0 <= lon <= 180.0:
            raise ValueError("Longitude must be in [-180, 180]°")
        return lon

    # Pydantic v2 field validators
    def __post_init__(self):  # noqa: D401
        # Called by dataclass after field assignment (works for both real and
        # stub Pydantic BaseModel dataclass wrapper).
        object.__setattr__(self, "lat", self._check_lat(self.lat))
        object.__setattr__(self, "lon", self._check_lon(self.lon))

    # -------------------------- Convenience --------------------------- #

    def to_radians(self) -> Tuple[float, float]:  # noqa: D401
        return math.radians(self.lat), math.radians(self.lon)

    def to_ecef(self) -> "ECEF":  # noqa: D401
        lat_rad, lon_rad = self.to_radians()
        x = EARTH_RADIUS_M * math.cos(lat_rad) * math.cos(lon_rad)
        y = EARTH_RADIUS_M * math.cos(lat_rad) * math.sin(lon_rad)
        z = EARTH_RADIUS_M * math.sin(lat_rad)
        return ECEF(x=x, y=y, z=z)

    @classmethod
    def from_ecef(cls, ecef: "ECEF") -> "LatLon":  # noqa: D401
        x, y, z = ecef.x, ecef.y, ecef.z
        hyp = math.hypot(x, y)
        lat = math.degrees(math.atan2(z, hyp))
        lon = math.degrees(math.atan2(y, x))
        return cls(lat=lat, lon=lon)

    def distance_to(self, other: "LatLon") -> float:  # noqa: D401
        lat1, lon1 = self.to_radians()
        lat2, lon2 = other.to_radians()
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return EARTH_RADIUS_M * c


class ECEF(BaseModel):
    """Earth‑Centred, Earth‑Fixed coordinates in metres."""

    x: float
    y: float
    z: float


class MagneticVector(BaseModel):
    """Magnetic‑field vector components in nano‑tesla (nT)."""

    bx: float
    by: float
    bz: float

    def magnitude(self) -> float:  # noqa: D401
        return math.sqrt(self.bx**2 + self.by**2 + self.bz**2)
