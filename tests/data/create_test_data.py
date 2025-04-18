"""Script to create test data files for mapping tests."""

import numpy as np
import rasterio
import xarray as xr
from pathlib import Path
from rasterio.transform import Affine

# Define the output directory
DATA_DIR = Path(__file__).parent

# Create a simple 5x5 grid with value = row*10 + col
grid_data = np.array([[r * 10 + c for c in range(5)] for r in range(5)])
lats = np.linspace(0, 4, 5)
lons = np.linspace(0, 4, 5)

# Create GeoTIFF file
geotiff_path = DATA_DIR / "5x5_grid.tif"
transform = Affine.translation(0, 4) * Affine.scale(1, -1)
with rasterio.open(
    geotiff_path,
    'w',
    driver='GTiff',
    height=5,
    width=5,
    count=1,
    dtype=grid_data.dtype,
    crs='+proj=latlong',
    transform=transform,
) as dst:
    dst.write(grid_data, 1)
    dst.update_tags(title="Test Map", source="Test", resolution_m="100.0")
print(f"Created GeoTIFF file: {geotiff_path}")

# Create NetCDF file
netcdf_path = DATA_DIR / "5x5_grid.nc"
ds = xr.Dataset(
    data_vars={
        "magnetic_anomaly": (["latitude", "longitude"], grid_data),
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
ds.to_netcdf(netcdf_path)
print(f"Created NetCDF file: {netcdf_path}")

# Create a JSON file with expected interpolation values
import json

# Generate some test points and their expected interpolated values
test_points = [
    {"lat": 0.0, "lon": 0.0, "expected": 0.0},  # Exact corner
    {"lat": 4.0, "lon": 4.0, "expected": 44.0},  # Exact corner
    {"lat": 2.0, "lon": 3.0, "expected": 23.0},  # Exact grid point
    {"lat": 0.5, "lon": 0.5, "expected": 5.5},   # Between points
    {"lat": 2.5, "lon": 3.5, "expected": 28.5},  # Between points
]

with open(DATA_DIR / "interpolation_values.json", "w") as f:
    json.dump(test_points, f, indent=2)
print(f"Created JSON file with expected interpolation values")