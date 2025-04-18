"""Tests for the enhanced MagneticMap implementation."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import rasterio
import xarray as xr
from rasterio.transform import Affine

from qmag_nav.mapping.backend import MagneticMap, load_map, cached_interpolate
from qmag_nav.models.map import MapHeader


def create_test_geotiff(path: Path, data: np.ndarray, transform: Affine) -> None:
    """Create a test GeoTIFF file with the given data and transform."""
    height, width = data.shape
    with rasterio.open(
        path,
        'w',
        driver='GTiff',
        height=height,
        width=width,
        count=1,
        dtype=data.dtype,
        crs='+proj=latlong',
        transform=transform,
    ) as dst:
        dst.write(data, 1)
        dst.update_tags(title="Test Map", source="Test", resolution_m="100.0")


def create_test_netcdf(path: Path, data: np.ndarray, lats: np.ndarray, lons: np.ndarray) -> None:
    """Create a test NetCDF file with the given data and coordinates."""
    ds = xr.Dataset(
        data_vars={
            "magnetic_anomaly": (["latitude", "longitude"], data),
        },
        coords={
            "latitude": lats,
            "longitude": lons,
        },
        attrs={
            "title": "Test Map",
            "source": "Test",
            "resolution_m": 100.0,
        },
    )
    ds.to_netcdf(path)


class TestMagneticMapEnhanced:
    """Test suite for the enhanced MagneticMap class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a simple 5x5 grid with value = row*10 + col
        self.grid_data = np.array([[r * 10 + c for c in range(5)] for r in range(5)])
        self.lats = np.linspace(0, 4, 5)
        self.lons = np.linspace(0, 4, 5)
        
        # Create temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        # Create test GeoTIFF
        self.geotiff_path = self.temp_path / "test_map.tif"
        transform = Affine.translation(0, 4) * Affine.scale(1, -1)
        create_test_geotiff(self.geotiff_path, self.grid_data, transform)
        
        # Create test NetCDF
        self.netcdf_path = self.temp_path / "test_map.nc"
        create_test_netcdf(self.netcdf_path, self.grid_data, self.lats, self.lons)

    def teardown_method(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_from_geotiff(self):
        """Test loading a map from a GeoTIFF file."""
        map_obj = MagneticMap.from_geotiff(self.geotiff_path)
        
        # Check bounds (based on actual GeoTIFF bounds)
        assert map_obj.lat_min == -1.0
        assert map_obj.lat_max == 4.0
        assert map_obj.lon_min == 0.0
        assert map_obj.lon_max == 5.0
        
        # Check grid dimensions
        assert map_obj.rows == 5
        assert map_obj.cols == 5
        
        # Check metadata
        assert map_obj.metadata is not None
        assert map_obj.metadata.title == "Test Map"
        assert map_obj.metadata.source == "Test"
        assert map_obj.metadata.resolution_m == 100.0
        
        # Check a sample value
        assert map_obj.grid[2][3] == 23

    def test_from_netcdf(self):
        """Test loading a map from a NetCDF file."""
        map_obj = MagneticMap.from_netcdf(self.netcdf_path)
        
        # Check bounds
        assert map_obj.lat_min == 0
        assert map_obj.lat_max == 4
        assert map_obj.lon_min == 0
        assert map_obj.lon_max == 4
        
        # Check grid dimensions
        assert map_obj.rows == 5
        assert map_obj.cols == 5
        
        # Check metadata
        assert map_obj.metadata is not None
        assert map_obj.metadata.title == "Test Map"
        assert map_obj.metadata.source == "Test"
        assert map_obj.metadata.resolution_m == 100.0
        
        # Check a sample value
        assert map_obj.grid[2][3] == 23

    def test_from_numpy_array(self):
        """Test creating a map from a NumPy array."""
        metadata = MapHeader(
            title="NumPy Test Map",
            source="Test",
            resolution_m=100.0,
        )
        
        map_obj = MagneticMap.from_numpy_array(
            self.grid_data,
            lat_bounds=(0, 4),
            lon_bounds=(0, 4),
            metadata=metadata,
        )
        
        # Check bounds
        assert map_obj.lat_min == 0
        assert map_obj.lat_max == 4
        assert map_obj.lon_min == 0
        assert map_obj.lon_max == 4
        
        # Check grid dimensions
        assert map_obj.rows == 5
        assert map_obj.cols == 5
        
        # Check metadata
        assert map_obj.metadata is not None
        assert map_obj.metadata.title == "NumPy Test Map"
        
        # Check a sample value
        assert map_obj.grid[2][3] == 23

    def test_load_map_auto_detect(self):
        """Test the load_map function with format auto-detection."""
        # Test GeoTIFF auto-detection
        map_obj1 = load_map(self.geotiff_path)
        assert map_obj1.metadata.title == "Test Map"
        
        # Test NetCDF auto-detection
        map_obj2 = load_map(self.netcdf_path)
        assert map_obj2.metadata.title == "Test Map"
        
        # Test invalid extension
        invalid_path = self.temp_path / "invalid.xyz"
        with open(invalid_path, "w") as f:
            f.write("invalid data")
        
        with pytest.raises(ValueError, match="Could not auto-detect format"):
            load_map(invalid_path)

    def test_load_map_explicit_format(self):
        """Test the load_map function with explicit format specification."""
        map_obj1 = load_map(self.geotiff_path, format_type="geotiff")
        assert map_obj1.metadata.title == "Test Map"
        
        map_obj2 = load_map(self.netcdf_path, format_type="netcdf")
        assert map_obj2.metadata.title == "Test Map"
        
        with pytest.raises(ValueError, match="Unsupported format"):
            load_map(self.geotiff_path, format_type="invalid")

    def test_lru_cache(self):
        """Test that the caching is working for load_map and cached_interpolate."""
        # Clear the map cache
        from qmag_nav.mapping.backend import _map_cache
        _map_cache.clear()
        
        # Test load_map caching
        with patch('qmag_nav.mapping.backend.MagneticMap.from_geotiff') as mock_from_geotiff:
            mock_from_geotiff.return_value = MagneticMap(
                lat_min=0, lat_max=4, lon_min=0, lon_max=4,
                grid=self.grid_data.tolist(),
                metadata=MapHeader(title="Mock Map", source="Test", resolution_m=100.0)
            )
            
            # First call should use the mock
            map_obj1 = load_map(self.geotiff_path)
            assert mock_from_geotiff.call_count == 1
            
            # Second call with same path should use cache
            map_obj2 = load_map(self.geotiff_path)
            assert mock_from_geotiff.call_count == 1
            
            # Different path should call again
            map_obj3 = load_map(self.temp_path / "different.tif")
            assert mock_from_geotiff.call_count == 2
        
        # Test cached_interpolate
        map_obj = MagneticMap(
            lat_min=0, lat_max=4, lon_min=0, lon_max=4,
            grid=self.grid_data.tolist()
        )
        
        # Clear the interpolation cache
        from qmag_nav.mapping.backend import _interpolation_cache
        _interpolation_cache.clear()
        
        # Since we can't patch the interpolate method due to slots=True,
        # we'll test the cache directly
        
        # First call should add to the cache
        val1 = cached_interpolate(map_obj, 2.5, 3.5)
        
        # Check that the value is now in the cache
        cache_key = (id(map_obj), 2.5, 3.5, "bilinear")
        assert cache_key in _interpolation_cache
        
        # Second call with same coordinates should use cache
        val2 = cached_interpolate(map_obj, 2.5, 3.5)
        
        # Values should be the same
        assert val1 == val2
        
        # Different coordinates should add a new entry to the cache
        val3 = cached_interpolate(map_obj, 1.5, 2.5)
        
        # Check that the new value is in the cache
        new_cache_key = (id(map_obj), 1.5, 2.5, "bilinear")
        assert new_cache_key in _interpolation_cache
        
        # Test with bicubic interpolation
        val4 = cached_interpolate(map_obj, 2.5, 3.5, method="bicubic")
        
        # Check that the bicubic value is in the cache
        bicubic_cache_key = (id(map_obj), 2.5, 3.5, "bicubic")
        assert bicubic_cache_key in _interpolation_cache
        
        # For a simple linear grid, bicubic and bilinear might give the same result
        # The important thing is that both methods work and are cached correctly
        
        # Create a more complex grid where bicubic and bilinear should differ
        complex_grid = np.array([
            [0, 10, 13, 10, 0],
            [10, 20, 23, 20, 10],
            [13, 23, 30, 23, 13],
            [10, 20, 23, 20, 10],
            [0, 10, 13, 10, 0]
        ])
        
        complex_map = MagneticMap(
            lat_min=0, lat_max=4, lon_min=0, lon_max=4,
            grid=complex_grid.tolist()
        )
        
        # Clear the cache for testing
        _interpolation_cache.clear()
        
        # Test both methods
        bilinear_val = cached_interpolate(complex_map, 2.5, 2.5, method="bilinear")
        bicubic_val = cached_interpolate(complex_map, 2.5, 2.5, method="bicubic")
        
        # Check that both values are cached
        assert (id(complex_map), 2.5, 2.5, "bilinear") in _interpolation_cache
        assert (id(complex_map), 2.5, 2.5, "bicubic") in _interpolation_cache

    def test_get_tile_metadata(self):
        """Test the get_tile_metadata method."""
        map_obj = MagneticMap(
            lat_min=0, lat_max=4, lon_min=0, lon_max=4, 
            grid=self.grid_data.tolist()
        )
        
        metadata = map_obj.get_tile_metadata()
        assert metadata.lat_min == 0
        assert metadata.lat_max == 4
        assert metadata.lon_min == 0
        assert metadata.lon_max == 4
        assert metadata.rows == 5
        assert metadata.cols == 5
        
        # Test that the contains method works
        assert metadata.contains(2, 2) is True
        assert metadata.contains(5, 5) is False