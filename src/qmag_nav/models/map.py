"""Magnetic map dataset metadata using Pydantic models."""

from __future__ import annotations

from qmag_nav._compat import BaseModel


class MapHeader(BaseModel):
    """Dataset‑level metadata."""

    title: str
    source: str
    resolution_m: float


class TileMetadata(BaseModel):
    """Spatial metadata for an individual tile within a dataset."""

    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    rows: int
    cols: int

    def contains(self, lat: float, lon: float) -> bool:  # noqa: D401
        return self.lat_min <= lat <= self.lat_max and self.lon_min <= lon <= self.lon_max
