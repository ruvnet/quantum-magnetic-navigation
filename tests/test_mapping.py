from __future__ import annotations

import pytest

from qmag_nav.mapping.backend import MagneticMap


def small_map() -> MagneticMap:
    # 5×5 grid with value = row*10 + col
    grid = [[r * 10 + c for c in range(5)] for r in range(5)]
    return MagneticMap(lat_min=0, lat_max=4, lon_min=0, lon_max=4, grid=grid)


def test_interpolation_exact_points():
    m = small_map()
    # points exactly on grid nodes – should match value formula
    assert m.interpolate(2, 3) == 2 * 10 + 3
    assert m.interpolate(0, 0) == 0


def test_interpolation_middle():
    m = small_map()
    # centre of four nodes (0,0), (0,1), (1,0), (1,1)
    val = m.interpolate(0.5, 0.5)
    # Expect average of 0,1,10,11 = 5.5
    assert pytest.approx(val, abs=1e-6) == 5.5


def test_out_of_bounds():
    m = small_map()
    with pytest.raises(ValueError):
        m.interpolate(-1, 0)
