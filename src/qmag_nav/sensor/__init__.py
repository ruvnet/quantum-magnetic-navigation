"""Sensor abstraction package."""

from qmag_nav.sensor.magnetometer import Magnetometer, MovingAverageFilter
from qmag_nav.sensor.mock import MockSensorDriver

__all__ = [
    "Magnetometer",
    "MovingAverageFilter",
    "MockSensorDriver",
]
