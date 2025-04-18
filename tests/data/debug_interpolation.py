"""Script to debug the interpolation issue."""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from qmag_nav.mapping.backend import MagneticMap, load_map

# Path to the GeoTIFF file
geotiff_path = Path(__file__).parent / "5x5_grid.tif"

# Load the map directly using MagneticMap.from_geotiff
map_obj = MagneticMap.from_geotiff(geotiff_path)

# Print map bounds
print(f"Map bounds: lat_min={map_obj.lat_min}, lat_max={map_obj.lat_max}, lon_min={map_obj.lon_min}, lon_max={map_obj.lon_max}")

# Print grid values
print("Grid values:")
for row in map_obj.grid:
    print(row)

# Test interpolation at specific points
test_points = [
    (0.0, 0.0),
    (4.0, 4.0),
    (2.0, 3.0),
]

for lat, lon in test_points:
    try:
        value = map_obj.interpolate(lat, lon)
        print(f"Value at ({lat}, {lon}): {value}")
    except Exception as e:
        print(f"Error interpolating at ({lat}, {lon}): {e}")