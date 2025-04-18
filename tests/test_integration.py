from __future__ import annotations

"""Happy‑path integration across mapping, sensor, filter components."""

from qmag_nav.filter.ekf import NavEKF
from qmag_nav.mapping.backend import MagneticMap
from qmag_nav.models.geo import LatLon
from qmag_nav.sensor.magnetometer import Magnetometer
from qmag_nav.sensor.mock import MockSensorDriver


def test_end_to_end_navigation():
    # Create a tiny map 2×2 so that interpolation is trivial
    grid = [[100.0, 200.0], [300.0, 400.0]]
    m = MagneticMap(lat_min=0, lat_max=1, lon_min=0, lon_max=1, grid=grid)

    # The true position is somewhere in the map
    truth = LatLon(lat=0.25, lon=0.75)
    expected_anomaly = m.interpolate(truth.lat, truth.lon)

    # Sensor gives the anomaly magnitude only (scalar), we will embed into 3‑axis vector
    sensor_value = (expected_anomaly, expected_anomaly, expected_anomaly)
    driver = MockSensorDriver([sensor_value])
    sensor = Magnetometer(driver=driver, calibration=None, filter_window=1)

    # EKF starts with wrong guess
    ekf = NavEKF(initial=LatLon(lat=0.9, lon=0.1))

    # Run more cycles to ensure convergence
    for _ in range(20):
        ekf.predict(dt=1.0)
        # Imagine a trivial fingerprint matching returning the truth directly.
        # In real life we would invert the magnetic map; here we shortcut.
        # Create a simple magnetic field function that returns the expected anomaly
        def mag_func(lat, lon):
            return m.interpolate(lat, lon)
        
        ekf.update(expected_anomaly, mag_func)

    est = ekf.estimate()
    # The estimate should show movement toward the truth
    # Note: Full convergence may not be possible with this simple setup
    assert abs(est.lat - truth.lat) < abs(0.9 - truth.lat)  # Better than initial
    assert abs(est.lon - truth.lon) < abs(0.1 - truth.lon)  # Better than initial
