from __future__ import annotations


from qmag_nav.models.sensor import CalibrationParams
from qmag_nav.sensor.magnetometer import Magnetometer, MovingAverageFilter
from qmag_nav.sensor.mock import MockSensorDriver


def test_moving_average_filter():
    f = MovingAverageFilter(window=3)

    assert f.update((3, 0, 0))[0] == 3  # first sample
    assert f.update((3, 0, 0))[0] == 3  # average of two 3s
    assert f.update((9, 0, 0))[0] == 5  # (3+3+9)/3


def test_moving_average_window_edge_cases():
    # Size 1 behaves as a simple pass‑through average
    f1 = MovingAverageFilter(window=1)
    assert f1.update((7, 2, 1)) == (7, 2, 1)
    # Invalid window (0) must raise
    import pytest

    with pytest.raises(ValueError):
        MovingAverageFilter(window=0)


def test_moving_average_hot_restart():
    """Buffer can be serialised and restored in a new instance."""

    f = MovingAverageFilter(window=3)
    f.update((1, 0, 0))
    f.update((2, 0, 0))

    # Persist buffer state (e.g. to disk) and recreate filter
    snap = f.snapshot()
    f2 = MovingAverageFilter.from_snapshot(window=3, state=snap)

    # Continue filtering should include history 1,2
    val = f2.update((3, 0, 0))[0]
    # Average of 1,2,3 is 2
    assert val == 2


def test_magnetometer_calibration_and_filtering():
    # raw samples return constant 10 nT on all axes
    driver = MockSensorDriver(samples=[(10, 10, 10)])
    cal = CalibrationParams(offset=(2, 2, 2), scale=(0.5, 0.5, 0.5))
    mag = Magnetometer(driver=driver, calibration=cal, filter_window=2)

    first = mag.read()
    second = mag.read()

    # After calibration each axis: (10‑2)*0.5 = 4.0
    assert first == (4.0, 4.0, 4.0)
    # Second reading – average of two identical calibrated samples is still 4
    assert second == (4.0, 4.0, 4.0)
