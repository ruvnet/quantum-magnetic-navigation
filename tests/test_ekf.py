"""Tests for the Extended Kalman Filter implementation."""

from __future__ import annotations

import math
from typing import Callable, Tuple

import pytest

from qmag_nav.filter.ekf import NavEKF
from qmag_nav.filter.utils import (
    create_identity_matrix,
    latlon_to_meters,
    matrix_add,
    matrix_inverse_4x4,
    matrix_multiply,
    matrix_subtract,
    matrix_transpose,
    meters_to_latlon,
    numerical_jacobian,
    process_noise_matrix,
    state_transition_matrix,
)
from qmag_nav.models.geo import LatLon, MagneticVector


def test_ekf_converges_single_observation():
    """Test that EKF state moves toward measurement after a single update."""
    initial = LatLon(lat=10, lon=20)
    ekf = NavEKF(initial=initial)

    ekf.predict(dt=1.0)

    # Simple magnetic field function that returns lat + lon
    def mag_func(lat, lon):
        return lat + lon

    meas = 32.0  # lat(11) + lon(21) = 32
    ekf.update(meas, mag_func)

    est = ekf.estimate()
    # Because measurement model is identity and K<1, estimate moves towards meas
    assert abs(est.lat + est.lon - meas) < abs(initial.lat + initial.lon - meas)


def test_ekf_multiple_updates_reach_measurement():
    """Test that EKF converges to true position after multiple updates."""
    ekf = NavEKF(initial=LatLon(lat=0, lon=0))

    target = LatLon(lat=1, lon=-1)
    
    # Simple magnetic field function that returns lat + lon
    def mag_func(lat, lon):
        return lat + lon
    
    target_mag = target.lat + target.lon  # 1 + (-1) = 0
    
    for _ in range(20):
        ekf.predict(dt=0.1)
        ekf.update(target_mag, mag_func)

    est = ekf.estimate()
    # Should be extremely close after many identical measurements
    # Note: We can't expect exact convergence to target since our measurement
    # function has a null space (any lat, lon where lat+lon=0 is valid)
    assert abs(est.lat + est.lon - target_mag) < 1e-3


def test_ekf_with_velocity():
    """Test EKF with velocity components in state vector."""
    # Initialize with non-zero velocity
    initial_pos = LatLon(lat=10, lon=20)
    initial_vel = (0.1, 0.2)  # degrees/second
    ekf = NavEKF(initial=initial_pos, initial_velocity=initial_vel)
    
    # Predict forward 1 second
    ekf.predict(dt=1.0)
    
    # Position should have changed according to velocity
    est = ekf.estimate()
    assert abs(est.lat - (initial_pos.lat + initial_vel[0])) < 1e-6
    assert abs(est.lon - (initial_pos.lon + initial_vel[1])) < 1e-6
    
    # Velocity should remain the same
    vel = ekf.velocity()
    assert abs(vel[0] - initial_vel[0]) < 1e-6
    assert abs(vel[1] - initial_vel[1]) < 1e-6


def test_ekf_with_imu():
    """Test EKF with IMU integration."""
    initial_pos = LatLon(lat=10, lon=20)
    ekf = NavEKF(initial=initial_pos)
    
    # Simulate constant acceleration
    accel = (1.0, 2.0)  # m/s²
    gyro = 0.0  # rad/s
    
    # Predict with IMU for 1 second
    ekf.predict_with_imu(dt=1.0, accel=accel, gyro=gyro)
    
    # Velocity should have changed according to acceleration
    vel_ms = ekf.velocity_ms()
    assert abs(vel_ms[0] - accel[0]) < 0.1
    assert abs(vel_ms[1] - accel[1]) < 0.1
    
    # Position should have changed according to velocity and acceleration
    est = ekf.estimate()
    assert est.lat > initial_pos.lat
    assert est.lon > initial_pos.lon


def test_ekf_vector_update():
    """Test EKF update with vector magnetic measurements."""
    ekf = NavEKF(initial=LatLon(lat=10, lon=20))
    
    # Simple magnetic vector function
    def mag_vector_func(lat, lon):
        return MagneticVector(bx=lat, by=lon, bz=lat+lon)
    
    # Create observation at target position
    target = LatLon(lat=11, lon=21)
    mag_obs = mag_vector_func(target.lat, target.lon)
    
    # Update with vector measurement
    ekf.update_vector(mag_obs, mag_vector_func)
    
    # Estimate should move toward target
    est = ekf.estimate()
    assert abs(est.lat - target.lat) < abs(10 - target.lat)
    assert abs(est.lon - target.lon) < abs(20 - target.lon)


def test_ekf_uncertainty_propagation():
    """Test that uncertainty increases during prediction and decreases during update."""
    ekf = NavEKF(initial=LatLon(lat=10, lon=20))
    
    # Get initial uncertainty
    init_pos_unc = ekf.position_uncertainty()
    
    # Predict forward (should increase uncertainty)
    ekf.predict(dt=1.0)
    
    # Uncertainty should increase
    pred_pos_unc = ekf.position_uncertainty()
    assert pred_pos_unc[0] > init_pos_unc[0]
    assert pred_pos_unc[1] > init_pos_unc[1]
    
    # Update with measurement (should decrease uncertainty)
    def mag_func(lat, lon):
        return lat + lon
    
    ekf.update(31.0, mag_func)  # 10+21=31
    
    # Uncertainty should decrease
    update_pos_unc = ekf.position_uncertainty()
    assert update_pos_unc[0] < pred_pos_unc[0]
    assert update_pos_unc[1] < pred_pos_unc[1]


def test_ekf_reset_covariance():
    """Test resetting the covariance matrix."""
    ekf = NavEKF(initial=LatLon(lat=10, lon=20))
    
    # Predict to change covariance
    ekf.predict(dt=1.0)
    
    # Reset covariance
    pos_var = 2.0
    vel_var = 0.5
    ekf.reset_covariance(position_var=pos_var, velocity_var=vel_var)
    
    # Check position uncertainty
    pos_unc = ekf.position_uncertainty()
    assert abs(pos_unc[0] - math.sqrt(pos_var)) < 1e-6
    assert abs(pos_unc[1] - math.sqrt(pos_var)) < 1e-6
    
    # Check velocity uncertainty
    vel_unc = ekf.velocity_uncertainty()
    assert abs(vel_unc[0] - math.sqrt(vel_var)) < 1e-6
    assert abs(vel_unc[1] - math.sqrt(vel_var)) < 1e-6


# Tests for utility functions

def test_create_identity_matrix():
    """Test creating identity matrices of different sizes."""
    # 2x2 identity
    I2 = create_identity_matrix(2)
    assert I2 == [[1.0, 0.0], [0.0, 1.0]]
    
    # 3x3 identity
    I3 = create_identity_matrix(3)
    assert I3 == [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def test_matrix_operations():
    """Test basic matrix operations."""
    A = [[1.0, 2.0], [3.0, 4.0]]
    B = [[5.0, 6.0], [7.0, 8.0]]
    
    # Matrix addition
    C = matrix_add(A, B)
    assert C == [[6.0, 8.0], [10.0, 12.0]]
    
    # Matrix subtraction
    D = matrix_subtract(A, B)
    assert D == [[-4.0, -4.0], [-4.0, -4.0]]
    
    # Matrix transpose
    AT = matrix_transpose(A)
    assert AT == [[1.0, 3.0], [2.0, 4.0]]
    
    # Matrix multiplication
    AB = matrix_multiply(A, B)
    assert AB == [[19.0, 22.0], [43.0, 50.0]]


def test_matrix_inverse_4x4():
    """Test 4x4 matrix inversion."""
    # Identity matrix
    I = create_identity_matrix(4)
    I_inv = matrix_inverse_4x4(I)
    assert all(abs(I_inv[i][j] - I[i][j]) < 1e-6 for i in range(4) for j in range(4))
    
    # Diagonal matrix
    D = [[2.0, 0.0, 0.0, 0.0],
         [0.0, 3.0, 0.0, 0.0],
         [0.0, 0.0, 4.0, 0.0],
         [0.0, 0.0, 0.0, 5.0]]
    
    D_inv = matrix_inverse_4x4(D)
    D_expected = [[0.5, 0.0, 0.0, 0.0],
                  [0.0, 1/3, 0.0, 0.0],
                  [0.0, 0.0, 0.25, 0.0],
                  [0.0, 0.0, 0.0, 0.2]]
    
    assert all(abs(D_inv[i][j] - D_expected[i][j]) < 1e-6 for i in range(4) for j in range(4))


def test_state_transition_matrix():
    """Test state transition matrix for constant velocity model."""
    dt = 0.5
    F = state_transition_matrix(dt, state_size=4)
    
    # Expected matrix
    F_expected = [[1.0, 0.0, dt, 0.0],
                  [0.0, 1.0, 0.0, dt],
                  [0.0, 0.0, 1.0, 0.0],
                  [0.0, 0.0, 0.0, 1.0]]
    
    assert F == F_expected


def test_process_noise_matrix():
    """Test process noise matrix for constant velocity model."""
    dt = 0.5
    q = 0.1
    Q = process_noise_matrix(dt, q, state_size=4)
    
    # Check matrix structure
    assert len(Q) == 4
    assert len(Q[0]) == 4
    
    # Check positive definiteness (all diagonal elements > 0)
    assert all(Q[i][i] > 0 for i in range(4))
    
    # Check symmetry
    for i in range(4):
        for j in range(4):
            assert abs(Q[i][j] - Q[j][i]) < 1e-6


def test_latlon_to_meters_and_back():
    """Test conversion between lat/lon and meters."""
    lat1, lon1 = 10.0, 20.0
    north_m, east_m = 1000.0, 2000.0
    
    # Convert meters to lat/lon
    lat2, lon2 = meters_to_latlon(lat1, lon1, north_m, east_m)
    
    # Convert back to meters
    north_m2, east_m2 = latlon_to_meters(lat1, lon1, lat2, lon2)
    
    # Check round-trip conversion
    assert abs(north_m - north_m2) < 1.0
    assert abs(east_m - east_m2) < 1.0


def test_numerical_jacobian():
    """Test numerical Jacobian calculation."""
    # Simple function: f(x,y) = [x^2, y^2]
    def func(x):
        return [x[0]**2, x[1]**2]
    
    # Calculate Jacobian at (2,3)
    x = [2.0, 3.0]
    J = numerical_jacobian(func, x)
    
    # Expected Jacobian: [[2x, 0], [0, 2y]] = [[4, 0], [0, 6]]
    J_expected = [[4.0, 0.0], [0.0, 6.0]]
    
    assert abs(J[0][0] - J_expected[0][0]) < 1e-4
    assert abs(J[0][1] - J_expected[0][1]) < 1e-4
    assert abs(J[1][0] - J_expected[1][0]) < 1e-4
    assert abs(J[1][1] - J_expected[1][1]) < 1e-4
