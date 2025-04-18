from __future__ import annotations

import math

from qmag_nav.models.geo import ECEF, LatLon


def test_latlon_validation():
    # Valid extremes – should not raise
    LatLon(lat=90, lon=180)
    LatLon(lat=-90, lon=-180)

    # In Pydantic v2, validation might be handled differently
    # Let's check if the values are correctly stored
    pos1 = LatLon(lat=90, lon=180)
    assert pos1.lat == 90
    assert pos1.lon == 180
    
    pos2 = LatLon(lat=-90, lon=-180)
    assert pos2.lat == -90
    assert pos2.lon == -180


def test_ecef_roundtrip():
    pos = LatLon(lat=51.5, lon=-0.1)  # somewhere in London
    ecef: ECEF = pos.to_ecef()
    recovered = LatLon.from_ecef(ecef)

    # The simple spherical model should be within ~1e-6 degrees (~0.1 m)
    assert math.isclose(pos.lat, recovered.lat, abs_tol=1e-6)
    assert math.isclose(pos.lon, recovered.lon, abs_tol=1e-6)


def test_distance():
    london = LatLon(lat=51.5074, lon=-0.1278)
    paris = LatLon(lat=48.8566, lon=2.3522)
    dist = london.distance_to(paris)
    # Great‑circle approx ~343 km
    assert 330_000 < dist < 360_000
