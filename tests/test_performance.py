"""Performance tests for the mapping module."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pytest

from qmag_nav.mapping.backend import MagneticMap, cached_interpolate


# Path to test data directory
DATA_DIR = Path(__file__).parent / "data"


def test_interpolation_performance():
    """Test the performance of interpolation methods."""
    # Create a larger grid for performance testing (100x100)
    rows, cols = 100, 100
    grid_data = np.zeros((rows, cols))
    for r in range(rows):
        for c in range(cols):
            grid_data[r, c] = r * cols + c
    
    # Create a map
    map_obj = MagneticMap(
        lat_min=0.0,
        lat_max=10.0,
        lon_min=0.0,
        lon_max=10.0,
        grid=grid_data.tolist(),
    )
    
    # Test points
    test_points = [
        (lat, lon) for lat in np.linspace(0.1, 9.9, 10) for lon in np.linspace(0.1, 9.9, 10)
    ]
    
    # Measure bilinear interpolation performance
    start_time = time.perf_counter()
    for lat, lon in test_points:
        map_obj.interpolate(lat, lon, method="bilinear")
    end_time = time.perf_counter()
    
    # Calculate average time per interpolation
    bilinear_time = (end_time - start_time) * 1_000_000 / len(test_points)  # in microseconds
    
    # Measure bicubic interpolation performance
    start_time = time.perf_counter()
    for lat, lon in test_points:
        map_obj.interpolate(lat, lon, method="bicubic")
    end_time = time.perf_counter()
    
    # Calculate average time per interpolation
    bicubic_time = (end_time - start_time) * 1_000_000 / len(test_points)  # in microseconds
    
    # Print performance results
    print(f"\nBilinear interpolation: {bilinear_time:.2f} µs per call")
    print(f"Bicubic interpolation: {bicubic_time:.2f} µs per call")
    
    # Verify that bilinear interpolation meets the performance criteria
    assert bilinear_time <= 100, f"Bilinear interpolation too slow: {bilinear_time:.2f} µs (target: ≤ 100 µs)"
    
    # Bicubic is expected to be slower, but should still be reasonable
    assert bicubic_time <= 1000, f"Bicubic interpolation too slow: {bicubic_time:.2f} µs (target: ≤ 1000 µs)"


def test_cached_interpolation_performance():
    """Test the performance of cached interpolation."""
    # Create a map from the test GeoTIFF
    map_obj = MagneticMap.from_geotiff(DATA_DIR / "5x5_grid.tif")
    
    # Clear the cache
    from qmag_nav.mapping.backend import _interpolation_cache
    _interpolation_cache.clear()
    
    # Test points
    test_points = [
        (lat, lon) for lat in np.linspace(0.1, 3.9, 10) for lon in np.linspace(0.1, 3.9, 10)
    ]
    
    # First run - uncached
    start_time = time.perf_counter()
    for lat, lon in test_points:
        cached_interpolate(map_obj, lat, lon)
    end_time = time.perf_counter()
    
    uncached_time = (end_time - start_time) * 1_000_000 / len(test_points)  # in microseconds
    
    # Second run - should use cache
    start_time = time.perf_counter()
    for lat, lon in test_points:
        cached_interpolate(map_obj, lat, lon)
    end_time = time.perf_counter()
    
    cached_time = (end_time - start_time) * 1_000_000 / len(test_points)  # in microseconds
    
    # Print performance results
    print(f"\nUncached interpolation: {uncached_time:.2f} µs per call")
    print(f"Cached interpolation: {cached_time:.2f} µs per call")
    
    # Cached lookup should be significantly faster
    assert cached_time < uncached_time * 0.5, "Caching not providing significant speedup"
    
    # Cached lookup should be very fast
    assert cached_time <= 10, f"Cached lookup too slow: {cached_time:.2f} µs (target: ≤ 10 µs)"


def test_memory_usage():
    """Test the memory usage of the MagneticMap class."""
    # This is a simple approximation - for a more accurate measurement,
    # we would need to use a memory profiler
    
    # Create a 1000x1000 grid (simulating a 1° global grid)
    rows, cols = 1000, 1000
    grid_data = np.zeros((rows, cols))
    
    # Measure memory before
    import psutil
    process = psutil.Process()
    memory_before = process.memory_info().rss / (1024 * 1024)  # in MB
    
    # Create the map
    map_obj = MagneticMap(
        lat_min=0.0,
        lat_max=1.0,
        lon_min=0.0,
        lon_max=1.0,
        grid=grid_data.tolist(),
    )
    
    # Measure memory after
    memory_after = process.memory_info().rss / (1024 * 1024)  # in MB
    
    # Calculate memory usage
    memory_usage = memory_after - memory_before
    
    # Print memory usage
    print(f"\nMemory usage for 1000x1000 grid: {memory_usage:.2f} MB")
    
    # Check against the requirement (≤ 200 MB for 1° global grid)
    # This test may be skipped if psutil is not available or on CI systems
    if memory_usage > 0:  # Only check if we got a valid measurement
        assert memory_usage <= 200, f"Memory usage too high: {memory_usage:.2f} MB (target: ≤ 200 MB)"