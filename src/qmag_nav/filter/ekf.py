"""Extended Kalman Filter for magnetic navigation with optional IMU integration.

This module implements a navigation-grade Extended Kalman Filter (EKF) that fuses
magnetic anomaly measurements with optional IMU data to estimate position and velocity.

The state vector is [lat, lon, dlat, dlon] where:
- lat, lon: Position in decimal degrees
- dlat, dlon: Velocity components in degrees/second

The filter supports:
1. Prediction using a constant velocity model
2. Updates from magnetic field measurements
3. Optional IMU integration for improved dynamics
"""

from __future__ import annotations

import math
from typing import Callable, List, Optional, Tuple, Union

import numpy as np

from qmag_nav.filter.utils import (
    latlon_to_meters,
    matrix_add,
    matrix_inverse_4x4,
    matrix_multiply,
    matrix_subtract,
    matrix_transpose,
    measurement_jacobian,
    meters_to_latlon,
    process_noise_matrix,
    state_transition_matrix,
)
from qmag_nav.models.geo import LatLon, MagneticVector
from qmag_nav.models.map import TileMetadata


class NavEKF:
    """Extended Kalman Filter for magnetic navigation with velocity estimation.
    
    This EKF maintains a state vector [lat, lon, dlat, dlon] and associated
    covariance matrix to provide robust position and velocity estimates by
    fusing magnetic field measurements with optional IMU data.
    """

    def __init__(
        self,
        initial: LatLon,
        initial_velocity: Optional[Tuple[float, float]] = None,
        covariance: Optional[List[List[float]]] = None,
        process_noise: float = 0.01,
    ) -> None:
        """Initialize the EKF with initial state and parameters.
        
        Args:
            initial: Initial position (lat, lon)
            initial_velocity: Initial velocity in (dlat, dlon) degrees/second, defaults to (0,0)
            covariance: Initial 4x4 covariance matrix, defaults to diagonal with position
                        uncertainty of 1.0 and velocity uncertainty of 0.01
            process_noise: Process noise parameter for the constant velocity model
        """
        # Initialize state vector [lat, lon, dlat, dlon]
        self.state = [
            initial.lat,
            initial.lon,
            initial_velocity[0] if initial_velocity else 0.0,
            initial_velocity[1] if initial_velocity else 0.0,
        ]
        
        # Initialize covariance matrix
        if covariance is None:
            # Default: position uncertainty = 1.0, velocity uncertainty = 0.01
            self.P = [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 0.01, 0.0],
                [0.0, 0.0, 0.0, 0.01],
            ]
        else:
            self.P = covariance
        
        # Process noise parameter
        self.process_noise = process_noise
        
        # Last update timestamp (for dt calculation)
        self.last_time = None
        
        # IMU bias estimates (optional)
        self.accel_bias = [0.0, 0.0]
        self.gyro_bias = 0.0

    # ------------------------------------------------------------------
    # Prediction step
    # ------------------------------------------------------------------

    def predict(self, dt: float) -> None:
        """Predict state forward in time using constant velocity model.
        
        Args:
            dt: Time step in seconds
        """
        # State transition matrix for constant velocity model
        F = state_transition_matrix(dt, state_size=4)
        
        # Process noise covariance
        Q = process_noise_matrix(dt, self.process_noise, state_size=4)
        
        # State prediction: x = F * x
        new_state = [0.0, 0.0, 0.0, 0.0]
        for i in range(4):
            for j in range(4):
                new_state[i] += F[i][j] * self.state[j]
        self.state = new_state
        
        # Covariance prediction: P = F*P*F^T + Q
        F_transpose = matrix_transpose(F)
        FP = matrix_multiply(F, self.P)
        FPFT = matrix_multiply(FP, F_transpose)
        self.P = matrix_add(FPFT, Q)

    def predict_with_imu(
        self,
        dt: float,
        accel: Tuple[float, float],
        gyro: float,
        accel_noise: float = 0.1,
        gyro_noise: float = 0.01,
    ) -> None:
        """Predict state using IMU measurements (accelerometer and gyroscope).
        
        Args:
            dt: Time step in seconds
            accel: Accelerometer measurements in m/s² (north, east)
            gyro: Gyroscope measurement in rad/s (yaw rate)
            accel_noise: Accelerometer noise standard deviation
            gyro_noise: Gyroscope noise standard deviation
        """
        # Current position and velocity
        lat, lon, dlat, dlon = self.state
        
        # Apply accelerometer bias correction
        accel_north = accel[0] - self.accel_bias[0]
        accel_east = accel[1] - self.accel_bias[1]
        
        # Convert acceleration to lat/lon acceleration
        lat_accel, lon_accel = meters_to_latlon(lat, lon, accel_north * dt * dt, accel_east * dt * dt)
        lat_accel = (lat_accel - lat) / (dt * dt)
        lon_accel = (lon_accel - lon) / (dt * dt)
        
        # Update velocity components
        new_dlat = dlat + lat_accel * dt
        new_dlon = dlon + lon_accel * dt
        
        # Update position components
        new_lat = lat + dlat * dt + 0.5 * lat_accel * dt * dt
        new_lon = lon + dlon * dt + 0.5 * lon_accel * dt * dt
        
        # Update state
        self.state = [new_lat, new_lon, new_dlat, new_dlon]
        
        # Process noise with IMU
        Q = process_noise_matrix(dt, self.process_noise, state_size=4)
        
        # Add additional noise from IMU measurements
        Q[2][2] += accel_noise * dt * dt  # dlat noise
        Q[3][3] += accel_noise * dt * dt  # dlon noise
        
        # State transition matrix for IMU model
        F = [
            [1.0, 0.0, dt, 0.0],
            [0.0, 1.0, 0.0, dt],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
        
        # Covariance prediction: P = F*P*F^T + Q
        F_transpose = matrix_transpose(F)
        FP = matrix_multiply(F, self.P)
        FPFT = matrix_multiply(FP, F_transpose)
        self.P = matrix_add(FPFT, Q)

    # ------------------------------------------------------------------
    # Update step
    # ------------------------------------------------------------------

    def update(
        self,
        mag_obs: float,
        mag_map_func: Callable[[float, float], float],
        measurement_noise: float = 0.05,
    ) -> None:
        """Update state using magnetic field measurement.
        
        Args:
            mag_obs: Observed magnetic field value
            mag_map_func: Function that returns expected magnetic field at a given lat/lon
            measurement_noise: Measurement noise standard deviation
        """
        # Current state
        lat, lon = self.state[0], self.state[1]
        
        # Expected measurement from map
        mag_expected = mag_map_func(lat, lon)
        
        # Innovation (measurement residual)
        innovation = mag_obs - mag_expected
        
        # Measurement Jacobian
        H = measurement_jacobian(self.state, mag_map_func)
        
        # Innovation covariance: S = H*P*H^T + R
        H_transpose = matrix_transpose(H)
        HP = matrix_multiply(H, self.P)
        HPH = matrix_multiply(HP, H_transpose)
        S = [[HPH[0][0] + measurement_noise]]
        
        # Kalman gain: K = P*H^T*S^-1
        S_inv = [[1.0 / S[0][0]]]
        PH = matrix_multiply(self.P, H_transpose)
        K = matrix_multiply(PH, S_inv)
        
        # State update: x = x + K*innovation
        for i in range(4):
            self.state[i] += K[i][0] * innovation
        
        # Covariance update: P = (I - K*H)*P
        KH = matrix_multiply(K, H)
        I_KH = [
            [1.0 - KH[0][0], -KH[0][1], -KH[0][2], -KH[0][3]],
            [-KH[1][0], 1.0 - KH[1][1], -KH[1][2], -KH[1][3]],
            [-KH[2][0], -KH[2][1], 1.0 - KH[2][2], -KH[2][3]],
            [-KH[3][0], -KH[3][1], -KH[3][2], 1.0 - KH[3][3]],
        ]
        self.P = matrix_multiply(I_KH, self.P)

    def update_vector(
        self,
        mag_obs: MagneticVector,
        mag_map_func: Callable[[float, float], MagneticVector],
        measurement_noise: float = 0.05,
    ) -> None:
        """Update state using 3D magnetic field vector measurement.
        
        Args:
            mag_obs: Observed magnetic field vector
            mag_map_func: Function that returns expected magnetic field vector at a given lat/lon
            measurement_noise: Measurement noise standard deviation
        """
        # Current state
        lat, lon = self.state[0], self.state[1]
        
        # Expected measurement from map
        mag_expected = mag_map_func(lat, lon)
        
        # Innovation (measurement residual)
        innovation = [
            mag_obs.bx - mag_expected.bx,
            mag_obs.by - mag_expected.by,
            mag_obs.bz - mag_expected.bz,
        ]
        
        # For simplicity, we'll use the magnitude for the Jacobian calculation
        def mag_magnitude(lat: float, lon: float) -> float:
            vector = mag_map_func(lat, lon)
            return vector.magnitude()
        
        # Measurement Jacobian (simplified to use magnitude)
        H = measurement_jacobian(self.state, mag_magnitude)
        
        # Expand H to 3x4 for vector measurements
        H_expanded = [
            H[0],  # Use the same Jacobian for all components
            H[0],
            H[0],
        ]
        
        # Innovation covariance: S = H*P*H^T + R
        H_transpose = matrix_transpose(H_expanded)
        HP = matrix_multiply(H_expanded, self.P)
        HPH = matrix_multiply(HP, H_transpose)
        
        # Measurement noise matrix (diagonal)
        R = [
            [measurement_noise, 0.0, 0.0],
            [0.0, measurement_noise, 0.0],
            [0.0, 0.0, measurement_noise],
        ]
        
        S = matrix_add(HPH, R)
        
        # Simplify by treating components as independent
        # Process each component separately
        for i in range(3):
            # Extract the i-th row of H
            H_i = [H_expanded[i]]
            
            # Innovation for this component
            innov_i = innovation[i]
            
            # Innovation covariance for this component
            S_i = [[S[i][i]]]
            
            # Kalman gain for this component
            S_inv_i = [[1.0 / S_i[0][0]]]
            H_i_transpose = matrix_transpose(H_i)
            PH_i = matrix_multiply(self.P, H_i_transpose)
            K_i = matrix_multiply(PH_i, S_inv_i)
            
            # State update for this component
            for j in range(4):
                self.state[j] += K_i[j][0] * innov_i
            
            # Covariance update for this component
            KH_i = matrix_multiply(K_i, H_i)
            I_KH_i = [
                [1.0 - KH_i[0][0], -KH_i[0][1], -KH_i[0][2], -KH_i[0][3]],
                [-KH_i[1][0], 1.0 - KH_i[1][1], -KH_i[1][2], -KH_i[1][3]],
                [-KH_i[2][0], -KH_i[2][1], 1.0 - KH_i[2][2], -KH_i[2][3]],
                [-KH_i[3][0], -KH_i[3][1], -KH_i[3][2], 1.0 - KH_i[3][3]],
            ]
            self.P = matrix_multiply(I_KH_i, self.P)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def estimate(self) -> LatLon:
        """Get the current position estimate.
        
        Returns:
            Current position estimate as LatLon
        """
        return LatLon(lat=self.state[0], lon=self.state[1])
    
    def velocity(self) -> Tuple[float, float]:
        """Get the current velocity estimate.
        
        Returns:
            Current velocity as (dlat, dlon) in degrees/second
        """
        return (self.state[2], self.state[3])
    
    def velocity_ms(self) -> Tuple[float, float]:
        """Get the current velocity estimate in meters/second.
        
        Returns:
            Current velocity as (north_mps, east_mps) in m/s
        """
        lat, lon = self.state[0], self.state[1]
        dlat, dlon = self.state[2], self.state[3]
        
        # Calculate position after 1 second
        lat_next = lat + dlat
        lon_next = lon + dlon
        
        # Convert to meters
        north_m, east_m = latlon_to_meters(lat, lon, lat_next, lon_next)
        
        return north_m, east_m
    
    def position_uncertainty(self) -> Tuple[float, float]:
        """Get the current position uncertainty.
        
        Returns:
            Standard deviations for (lat, lon)
        """
        return (math.sqrt(self.P[0][0]), math.sqrt(self.P[1][1]))
    
    def velocity_uncertainty(self) -> Tuple[float, float]:
        """Get the current velocity uncertainty.
        
        Returns:
            Standard deviations for (dlat, dlon)
        """
        return (math.sqrt(self.P[2][2]), math.sqrt(self.P[3][3]))
    
    def reset_covariance(self, position_var: float = 1.0, velocity_var: float = 0.01) -> None:
        """Reset the covariance matrix to default values.
        
        Args:
            position_var: Variance for position components
            velocity_var: Variance for velocity components
        """
        self.P = [
            [position_var, 0.0, 0.0, 0.0],
            [0.0, position_var, 0.0, 0.0],
            [0.0, 0.0, velocity_var, 0.0],
            [0.0, 0.0, 0.0, velocity_var],
        ]
