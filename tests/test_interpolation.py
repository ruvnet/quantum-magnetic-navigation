"""Tests for the interpolation module."""

from __future__ import annotations

import numpy as np
import pytest

from qmag_nav.mapping.interpolate import bilinear, bicubic, grid_to_geo_coords


class TestInterpolation:
    """Test suite for the interpolation module."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a simple 5x5 grid with value = row*10 + col
        self.grid_data = np.array([[r * 10 + c for c in range(5)] for r in range(5)])
        
        # Create a list of lists version for testing
        self.grid_list = self.grid_data.tolist()

    def test_bilinear_exact_points(self):
        """Test bilinear interpolation at exact grid points."""
        # Test at exact grid points
        assert bilinear(self.grid_data, 2.0, 3.0, 5, 5) == 23.0
        assert bilinear(self.grid_list, 0.0, 0.0, 5, 5) == 0.0
        assert bilinear(self.grid_data, 4.0, 4.0, 5, 5) == 44.0

    def test_bilinear_between_points(self):
        """Test bilinear interpolation between grid points."""
        # Test halfway between points
        assert bilinear(self.grid_data, 0.5, 0.5, 5, 5) == 5.5
        assert bilinear(self.grid_list, 2.5, 3.5, 5, 5) == 28.5
        
        # Test at arbitrary position
        assert pytest.approx(bilinear(self.grid_data, 1.25, 2.75, 5, 5), abs=1e-6) == 15.25
        
        # Test near edge
        assert bilinear(self.grid_list, 3.9, 4.0, 5, 5) == 43.0

    def test_bilinear_out_of_bounds(self):
        """Test bilinear interpolation with out-of-bounds indices."""
        with pytest.raises(ValueError):
            bilinear(self.grid_data, -0.1, 2.0, 5, 5)
        
        with pytest.raises(ValueError):
            bilinear(self.grid_list, 2.0, 5.1, 5, 5)

    def test_bicubic_exact_points(self):
        """Test bicubic interpolation at exact grid points."""
        # Test at exact grid points (should match the original values)
        assert pytest.approx(bicubic(self.grid_data, 2.0, 2.0, 5, 5), abs=1e-6) == 22.0
        
        # Points at the edge should fall back to bilinear
        assert pytest.approx(bicubic(self.grid_data, 0.0, 0.0, 5, 5), abs=1e-6) == 0.0

    def test_bicubic_between_points(self):
        """Test bicubic interpolation between grid points."""
        # Test at arbitrary position
        # For our simplified implementation, bicubic might equal bilinear in some cases
        # especially for a simple linear grid like our test data
        bicubic_val = bicubic(self.grid_data, 2.5, 2.5, 5, 5)
        bilinear_val = bilinear(self.grid_data, 2.5, 2.5, 5, 5)
        
        # They should be close
        assert pytest.approx(bicubic_val, abs=1.0) == bilinear_val
        
        # Test with a more complex grid where bicubic and bilinear should differ
        complex_grid = np.array([
            [0, 10, 13, 10, 0],
            [10, 20, 23, 20, 10],
            [13, 23, 30, 23, 13],
            [10, 20, 23, 20, 10],
            [0, 10, 13, 10, 0]
        ])
        
        bicubic_val = bicubic(complex_grid, 2.5, 2.5, 5, 5)
        bilinear_val = bilinear(complex_grid, 2.5, 2.5, 5, 5)
        
        # Now they should be different
        assert bicubic_val != bilinear_val

    def test_bicubic_out_of_bounds(self):
        """Test bicubic interpolation with out-of-bounds indices."""
        with pytest.raises(ValueError):
            bicubic(self.grid_data, -0.1, 2.0, 5, 5)
        
        with pytest.raises(ValueError):
            bicubic(self.grid_list, 2.0, 5.1, 5, 5)

    def test_grid_to_geo_coords(self):
        """Test conversion from geographic coordinates to grid indices."""
        # Define geographic bounds
        lat_min, lat_max = 0.0, 4.0
        lon_min, lon_max = 0.0, 4.0
        rows, cols = 5, 5
        
        # Test exact corners
        row_f, col_f = grid_to_geo_coords(0.0, 0.0, lat_min, lat_max, lon_min, lon_max, rows, cols)
        assert row_f == 0.0
        assert col_f == 0.0
        
        row_f, col_f = grid_to_geo_coords(4.0, 4.0, lat_min, lat_max, lon_min, lon_max, rows, cols)
        assert row_f == 4.0
        assert col_f == 4.0
        
        # Test middle point
        row_f, col_f = grid_to_geo_coords(2.0, 2.0, lat_min, lat_max, lon_min, lon_max, rows, cols)
        assert row_f == 2.0
        assert col_f == 2.0
        
        # Test arbitrary point
        row_f, col_f = grid_to_geo_coords(1.5, 3.5, lat_min, lat_max, lon_min, lon_max, rows, cols)
        assert row_f == 1.5
        assert col_f == 3.5
        
        # Test out of bounds
        with pytest.raises(ValueError):
            grid_to_geo_coords(-0.1, 2.0, lat_min, lat_max, lon_min, lon_max, rows, cols)
        
        with pytest.raises(ValueError):
            grid_to_geo_coords(2.0, 4.1, lat_min, lat_max, lon_min, lon_max, rows, cols)