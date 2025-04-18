"""Utility functions for Extended Kalman Filter implementation.

This module provides helper functions for Jacobian calculations, numerical
differentiation, and other mathematical operations needed by the EKF.
"""

from __future__ import annotations

import math
from typing import Callable, List, Tuple, TypeVar, Union

import numpy as np

from qmag_nav.models.geo import LatLon
from qmag_nav.models.map import TileMetadata

# Type variable for generic functions
T = TypeVar('T')


def create_identity_matrix(size: int) -> List[List[float]]:
    """Create an identity matrix of the specified size.
    
    Args:
        size: The size of the square identity matrix
        
    Returns:
        A list of lists representing the identity matrix
    """
    return [[1.0 if i == j else 0.0 for j in range(size)] for i in range(size)]


def numerical_jacobian(
    func: Callable[[List[float]], List[float]],
    x: List[float],
    epsilon: float = 1e-6
) -> List[List[float]]:
    """Calculate the Jacobian matrix using numerical differentiation.
    
    Args:
        func: The function to differentiate
        x: The point at which to calculate the Jacobian
        epsilon: The step size for finite differences
        
    Returns:
        The Jacobian matrix as a list of lists
    """
    n = len(x)
    f0 = func(x)
    m = len(f0)
    
    jacobian = [[0.0 for _ in range(n)] for _ in range(m)]
    
    for i in range(n):
        x_perturbed = x.copy()
        x_perturbed[i] += epsilon
        f1 = func(x_perturbed)
        
        for j in range(m):
            jacobian[j][i] = (f1[j] - f0[j]) / epsilon
    
    return jacobian


def state_transition_matrix(dt: float, state_size: int = 4) -> List[List[float]]:
    """Create the state transition matrix for a constant velocity model.
    
    For a state vector [lat, lon, dlat, dlon], the transition matrix is:
    [1 0 dt 0]
    [0 1 0  dt]
    [0 0 1  0 ]
    [0 0 0  1 ]
    
    Args:
        dt: Time step in seconds
        state_size: Size of the state vector (default: 4 for [lat, lon, dlat, dlon])
        
    Returns:
        The state transition matrix as a list of lists
    """
    if state_size != 4:
        raise ValueError("Only state size 4 is currently supported")
    
    F = create_identity_matrix(state_size)
    F[0][2] = dt  # lat += dlat * dt
    F[1][3] = dt  # lon += dlon * dt
    
    return F


def process_noise_matrix(dt: float, q: float, state_size: int = 4) -> List[List[float]]:
    """Create the process noise covariance matrix for a constant velocity model.
    
    Args:
        dt: Time step in seconds
        q: Process noise parameter
        state_size: Size of the state vector (default: 4)
        
    Returns:
        The process noise matrix as a list of lists
    """
    if state_size != 4:
        raise ValueError("Only state size 4 is currently supported")
    
    # For a constant velocity model with acceleration noise
    dt2 = dt * dt
    dt3 = dt2 * dt
    dt4 = dt3 * dt
    
    # Process noise matrix
    Q = [[0.0 for _ in range(state_size)] for _ in range(state_size)]
    
    # Position-position terms
    Q[0][0] = q * dt4 / 4.0  # lat-lat
    Q[1][1] = q * dt4 / 4.0  # lon-lon
    
    # Position-velocity terms
    Q[0][2] = q * dt3 / 2.0  # lat-dlat
    Q[2][0] = q * dt3 / 2.0  # dlat-lat
    Q[1][3] = q * dt3 / 2.0  # lon-dlon
    Q[3][1] = q * dt3 / 2.0  # dlon-lon
    
    # Velocity-velocity terms
    Q[2][2] = q * dt2  # dlat-dlat
    Q[3][3] = q * dt2  # dlon-dlon
    
    return Q


def measurement_jacobian(
    state: List[float],
    mag_map_func: Callable[[float, float], float],
    epsilon: float = 1e-6
) -> List[List[float]]:
    """Calculate the measurement Jacobian matrix for magnetic field observations.
    
    Args:
        state: The current state vector [lat, lon, dlat, dlon]
        mag_map_func: Function that returns magnetic field value at a given lat/lon
        epsilon: The step size for finite differences
        
    Returns:
        The measurement Jacobian matrix (1x4)
    """
    lat, lon = state[0], state[1]
    
    # Base magnetic field value
    base_value = mag_map_func(lat, lon)
    
    # Perturb latitude
    lat_perturbed = lat + epsilon
    lat_gradient = (mag_map_func(lat_perturbed, lon) - base_value) / epsilon
    
    # Perturb longitude
    lon_perturbed = lon + epsilon
    lon_gradient = (mag_map_func(lon, lon_perturbed) - base_value) / epsilon
    
    # The Jacobian is [∂B/∂lat, ∂B/∂lon, 0, 0]
    # Velocity components don't directly affect the magnetic field measurement
    return [[lat_gradient, lon_gradient, 0.0, 0.0]]


def matrix_multiply(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
    """Multiply two matrices.
    
    Args:
        A: First matrix (m x n)
        B: Second matrix (n x p)
        
    Returns:
        The product matrix (m x p)
    """
    m = len(A)
    n = len(B)
    p = len(B[0])
    
    C = [[0.0 for _ in range(p)] for _ in range(m)]
    
    for i in range(m):
        for j in range(p):
            for k in range(n):
                C[i][j] += A[i][k] * B[k][j]
    
    return C


def matrix_transpose(A: List[List[float]]) -> List[List[float]]:
    """Transpose a matrix.
    
    Args:
        A: Input matrix (m x n)
        
    Returns:
        The transposed matrix (n x m)
    """
    m = len(A)
    n = len(A[0])
    
    AT = [[0.0 for _ in range(m)] for _ in range(n)]
    
    for i in range(m):
        for j in range(n):
            AT[j][i] = A[i][j]
    
    return AT


def matrix_add(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
    """Add two matrices.
    
    Args:
        A: First matrix (m x n)
        B: Second matrix (m x n)
        
    Returns:
        The sum matrix (m x n)
    """
    m = len(A)
    n = len(A[0])
    
    C = [[0.0 for _ in range(n)] for _ in range(m)]
    
    for i in range(m):
        for j in range(n):
            C[i][j] = A[i][j] + B[i][j]
    
    return C


def matrix_subtract(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
    """Subtract matrix B from matrix A.
    
    Args:
        A: First matrix (m x n)
        B: Second matrix (m x n)
        
    Returns:
        The difference matrix (m x n)
    """
    m = len(A)
    n = len(A[0])
    
    C = [[0.0 for _ in range(n)] for _ in range(m)]
    
    for i in range(m):
        for j in range(n):
            C[i][j] = A[i][j] - B[i][j]
    
    return C


def matrix_inverse_2x2(A: List[List[float]]) -> List[List[float]]:
    """Calculate the inverse of a 2x2 matrix.
    
    Args:
        A: Input 2x2 matrix
        
    Returns:
        The inverse matrix
        
    Raises:
        ValueError: If the matrix is singular
    """
    det = A[0][0] * A[1][1] - A[0][1] * A[1][0]
    
    if abs(det) < 1e-10:
        raise ValueError("Matrix is singular, cannot compute inverse")
    
    inv_det = 1.0 / det
    
    return [
        [A[1][1] * inv_det, -A[0][1] * inv_det],
        [-A[1][0] * inv_det, A[0][0] * inv_det]
    ]


def matrix_inverse_4x4(A: List[List[float]]) -> List[List[float]]:
    """Calculate the inverse of a 4x4 matrix using numpy.
    
    Args:
        A: Input 4x4 matrix
        
    Returns:
        The inverse matrix
        
    Raises:
        ValueError: If the matrix is singular
    """
    # Convert to numpy array for inversion
    A_np = np.array(A)
    
    try:
        A_inv_np = np.linalg.inv(A_np)
        # Convert back to list of lists
        return A_inv_np.tolist()
    except np.linalg.LinAlgError:
        raise ValueError("Matrix is singular, cannot compute inverse")


def latlon_to_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> Tuple[float, float]:
    """Convert latitude/longitude differences to approximate meters.
    
    Args:
        lat1: First latitude in degrees
        lon1: First longitude in degrees
        lat2: Second latitude in degrees
        lon2: Second longitude in degrees
        
    Returns:
        Tuple of (north_meters, east_meters)
    """
    # Earth radius in meters
    earth_radius = 6371000.0
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # North-south distance
    north_meters = earth_radius * (lat2_rad - lat1_rad)
    
    # East-west distance (accounting for latitude)
    east_meters = earth_radius * math.cos(lat1_rad) * (lon2_rad - lon1_rad)
    
    return north_meters, east_meters


def meters_to_latlon(lat: float, lon: float, north_meters: float, east_meters: float) -> Tuple[float, float]:
    """Convert north/east meters to latitude/longitude differences.
    
    Args:
        lat: Reference latitude in degrees
        lon: Reference longitude in degrees
        north_meters: North distance in meters
        east_meters: East distance in meters
        
    Returns:
        Tuple of (new_latitude, new_longitude) in degrees
    """
    # Earth radius in meters
    earth_radius = 6371000.0
    
    # Convert to radians
    lat_rad = math.radians(lat)
    
    # Latitude change
    dlat = north_meters / earth_radius
    
    # Longitude change (accounting for latitude)
    dlon = east_meters / (earth_radius * math.cos(lat_rad))
    
    # Convert back to degrees
    new_lat = lat + math.degrees(dlat)
    new_lon = lon + math.degrees(dlon)
    
    return new_lat, new_lon