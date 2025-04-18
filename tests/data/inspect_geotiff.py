"""Script to inspect the GeoTIFF file."""

import rasterio
import numpy as np
from pathlib import Path

# Path to the GeoTIFF file
geotiff_path = Path(__file__).parent / "5x5_grid.tif"

# Open the GeoTIFF file
with rasterio.open(geotiff_path) as ds:
    # Print basic information
    print(f"Bounds: {ds.bounds}")
    print(f"Transform: {ds.transform}")
    print(f"CRS: {ds.crs}")
    
    # Read the data
    data = ds.read(1)
    print(f"Data shape: {data.shape}")
    print("Data values:")
    print(data)
    
    # Test some interpolation points
    for lat, lon in [(0.0, 0.0), (4.0, 4.0), (2.0, 3.0)]:
        # Convert lat/lon to pixel coordinates
        row, col = rasterio.transform.rowcol(ds.transform, lon, lat)
        print(f"Lat: {lat}, Lon: {lon} -> Row: {row}, Col: {col}, Value: {data[row, col] if 0 <= row < data.shape[0] and 0 <= col < data.shape[1] else 'out of bounds'}")