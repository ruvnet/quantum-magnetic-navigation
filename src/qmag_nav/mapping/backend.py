"""Magnetic map implementation with support for various file formats and caching."""

from __future__ import annotations

import math
import os
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union, cast

import numpy as np
import rasterio
import xarray as xr
from rasterio.transform import rowcol

from qmag_nav.mapping.interpolate import bilinear, bicubic, grid_to_geo_coords
from qmag_nav.models.map import MapHeader, TileMetadata


@dataclass(slots=True)
class MagneticMap:
    """
    Magnetic anomaly map with support for various file formats and caching.
    
    Provides bilinear interpolation of magnetic anomaly values (in nano-tesla)
    from a regularly-spaced 2-D grid.
    
    Attributes:
        lat_min: Minimum latitude bound of the map
        lat_max: Maximum latitude bound of the map
        lon_min: Minimum longitude bound of the map
        lon_max: Maximum longitude bound of the map
        grid: 2D grid of magnetic anomaly values (rows × cols, lat major)
        metadata: Optional metadata about the map source
    """

    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    grid: List[List[float]]  # rows × cols, lat major
    metadata: Optional[MapHeader] = None
    _cell_size_cache: Optional[Tuple[float, float]] = None

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------

    @property
    def rows(self) -> int:  # noqa: D401
        """Number of rows in the grid."""
        return len(self.grid)

    @property
    def cols(self) -> int:  # noqa: D401
        """Number of columns in the grid."""
        return len(self.grid[0]) if self.grid else 0

    def _cell_size(self) -> tuple[float, float]:
        """
        Calculate the cell size in latitude and longitude dimensions.
        
        Returns:
            Tuple of (latitude_cell_size, longitude_cell_size)
        """
        if self._cell_size_cache is None:
            self._cell_size_cache = (
                (self.lat_max - self.lat_min) / (self.rows - 1),
                (self.lon_max - self.lon_min) / (self.cols - 1),
            )
        return self._cell_size_cache

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def interpolate(self, lat: float, lon: float, method: str = "bilinear") -> float:  # noqa: D401
        """
        Interpolate the magnetic anomaly value at the given coordinates.
        
        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            method: Interpolation method ("bilinear" or "bicubic")
            
        Returns:
            Interpolated magnetic anomaly value in nano-tesla
            
        Raises:
            ValueError: If the location is outside map bounds or method is invalid
        """
        if method not in ["bilinear", "bicubic"]:
            raise ValueError(f"Unsupported interpolation method: {method}")

        if not (self.lat_min <= lat <= self.lat_max) or not (
            self.lon_min <= lon <= self.lon_max
        ):
            raise ValueError("Location outside of map bounds")

        # Convert geographic coordinates to grid indices
        row_f, col_f = grid_to_geo_coords(
            lat, lon,
            self.lat_min, self.lat_max,
            self.lon_min, self.lon_max,
            self.rows, self.cols
        )
        
        # Perform interpolation using the selected method
        if method == "bilinear":
            return bilinear(self.grid, row_f, col_f, self.rows, self.cols)
        else:  # method == "bicubic"
            return bicubic(self.grid, row_f, col_f, self.rows, self.cols)

    def get_tile_metadata(self) -> TileMetadata:
        """
        Return the spatial metadata for this map tile.
        
        Returns:
            TileMetadata object containing the spatial bounds and dimensions
        """
        return TileMetadata(
            lat_min=self.lat_min,
            lat_max=self.lat_max,
            lon_min=self.lon_min,
            lon_max=self.lon_max,
            rows=self.rows,
            cols=self.cols,
        )

    # ------------------------------------------------------------------
    # Factory methods for loading from files
    # ------------------------------------------------------------------

    @classmethod
    def from_geotiff(cls, path: Union[str, Path], band: int = 1) -> MagneticMap:
        """
        Load a magnetic map from a GeoTIFF file.
        
        Args:
            path: Path to the GeoTIFF file
            band: Band number to read (default: 1)
            
        Returns:
            MagneticMap instance
            
        Raises:
            ValueError: If the file cannot be read or is not a valid GeoTIFF
        """
        try:
            with rasterio.open(path) as dataset:
                # Read the data from the specified band
                grid_data = dataset.read(band)
                
                # Get the geospatial bounds
                bounds = dataset.bounds
                
                # Convert to list of lists for compatibility with existing code
                grid = grid_data.tolist()
                
                # Create metadata from tags if available
                metadata = None
                if dataset.tags():
                    metadata = MapHeader(
                        title=dataset.tags().get("title", os.path.basename(str(path))),
                        source=dataset.tags().get("source", "GeoTIFF"),
                        resolution_m=float(dataset.tags().get("resolution_m", 0.0)),
                    )
                
                return cls(
                    lat_min=bounds.bottom,
                    lat_max=bounds.top,
                    lon_min=bounds.left,
                    lon_max=bounds.right,
                    grid=grid,
                    metadata=metadata,
                )
        except Exception as e:
            raise ValueError(f"Failed to load GeoTIFF file: {e}") from e

    @classmethod
    def from_netcdf(
        cls,
        path: Union[str, Path],
        lat_var: str = "latitude",
        lon_var: str = "longitude",
        data_var: str = "magnetic_anomaly"
    ) -> MagneticMap:
        """
        Load a magnetic map from a NetCDF file.
        
        Args:
            path: Path to the NetCDF file
            lat_var: Name of the latitude variable
            lon_var: Name of the longitude variable
            data_var: Name of the data variable containing magnetic anomaly values
            
        Returns:
            MagneticMap instance
            
        Raises:
            ValueError: If the file cannot be read or variables are not found
        """
        try:
            with xr.open_dataset(path) as ds:
                # Check if required variables exist
                if lat_var not in ds or lon_var not in ds or data_var not in ds:
                    missing = []
                    if lat_var not in ds:
                        missing.append(lat_var)
                    if lon_var not in ds:
                        missing.append(lon_var)
                    if data_var not in ds:
                        missing.append(data_var)
                    raise ValueError(f"Missing required variables in NetCDF: {', '.join(missing)}")
                
                # Extract coordinates and data
                lats = ds[lat_var].values
                lons = ds[lon_var].values
                data = ds[data_var].values
                
                # Create metadata if available
                metadata = None
                if hasattr(ds, 'title') and hasattr(ds, 'source'):
                    resolution = 0.0
                    if hasattr(ds, 'resolution_m'):
                        resolution = float(ds.resolution_m)
                    
                    metadata = MapHeader(
                        title=str(ds.title),
                        source=str(ds.source),
                        resolution_m=resolution,
                    )
                
                # Convert to list of lists
                grid = data.tolist()
                
                return cls(
                    lat_min=float(np.min(lats)),
                    lat_max=float(np.max(lats)),
                    lon_min=float(np.min(lons)),
                    lon_max=float(np.max(lons)),
                    grid=grid,
                    metadata=metadata,
                )
        except Exception as e:
            raise ValueError(f"Failed to load NetCDF file: {e}") from e

    @classmethod
    def from_numpy_array(
        cls,
        array: np.ndarray,
        lat_bounds: Tuple[float, float],
        lon_bounds: Tuple[float, float],
        metadata: Optional[MapHeader] = None,
    ) -> MagneticMap:
        """
        Create a magnetic map from a NumPy array.
        
        Args:
            array: 2D NumPy array containing magnetic anomaly values
            lat_bounds: Tuple of (min_latitude, max_latitude)
            lon_bounds: Tuple of (min_longitude, max_longitude)
            metadata: Optional map metadata
            
        Returns:
            MagneticMap instance
            
        Raises:
            ValueError: If the array is not 2D
        """
        if array.ndim != 2:
            raise ValueError(f"Expected 2D array, got {array.ndim}D")
        
        return cls(
            lat_min=lat_bounds[0],
            lat_max=lat_bounds[1],
            lon_min=lon_bounds[0],
            lon_max=lon_bounds[1],
            grid=array.tolist(),
            metadata=metadata,
        )


# LRU cache for loaded maps with configurable size
class LRUCache(OrderedDict):
    """
    LRU (Least Recently Used) cache implementation.
    
    This cache has a maximum size and will remove the least recently used items
    when the size limit is reached.
    """
    
    def __init__(self, maxsize: int = 128):
        """
        Initialize an LRU cache with a maximum size.
        
        Args:
            maxsize: Maximum number of items to store in the cache
        """
        self.maxsize = maxsize
        super().__init__()
    
    def __getitem__(self, key):
        """
        Get an item from the cache and mark it as recently used.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value
            
        Raises:
            KeyError: If the key is not in the cache
        """
        value = super().__getitem__(key)
        self.move_to_end(key)
        return value
    
    def __setitem__(self, key, value):
        """
        Add an item to the cache and remove oldest items if size limit is reached.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        if len(self) > self.maxsize:
            oldest = next(iter(self))
            del self[oldest]


# Map cache with configurable size
_map_cache = LRUCache(maxsize=32)

def load_map(
    path: Union[str, Path],
    format_type: Optional[Literal["geotiff", "netcdf"]] = None,
    **kwargs: Any
) -> MagneticMap:
    """
    Load a magnetic map from a file, with format auto-detection.
    
    This function is cached to avoid reloading the same file multiple times.
    
    Args:
        path: Path to the map file
        format_type: Optional format specification (if None, will be auto-detected from extension)
        **kwargs: Additional arguments passed to the specific loader
        
    Returns:
        MagneticMap instance
        
    Raises:
        ValueError: If the file format is not supported or cannot be detected
    """
    # Convert path to string for caching
    path_str = str(path)
    format_type_str = str(format_type) if format_type else None
    
    # Create a cache key
    cache_key = (path_str, format_type_str, frozenset(kwargs.items()) if kwargs else None)
    
    # Check if map is already in cache
    if cache_key in _map_cache:
        return _map_cache[cache_key]
    
    # Auto-detect format if not specified
    if format_type is None:
        suffix = Path(path_str).suffix.lower()
        if suffix in ('.tif', '.tiff'):
            format_type = 'geotiff'
        elif suffix in ('.nc', '.netcdf'):
            format_type = 'netcdf'
        else:
            raise ValueError(f"Could not auto-detect format for file: {path}")
    
    # Load based on format
    if format_type == 'geotiff':
        map_obj = MagneticMap.from_geotiff(path, **kwargs)
    elif format_type == 'netcdf':
        map_obj = MagneticMap.from_netcdf(path, **kwargs)
    else:
        raise ValueError(f"Unsupported format: {format_type}")
    
    # Cache the result
    _map_cache[cache_key] = map_obj
    
    return map_obj


# Interpolation cache with configurable size
_interpolation_cache = LRUCache(maxsize=1024)

def cached_interpolate(map_obj: MagneticMap, lat: float, lon: float, method: str = "bilinear") -> float:
    """
    Cached version of the interpolate method.
    
    This function uses a custom LRU cache for efficient caching of
    interpolation results.
    
    Args:
        map_obj: MagneticMap instance
        lat: Latitude coordinate
        lon: Longitude coordinate
        method: Interpolation method ("bilinear" or "bicubic")
        
    Returns:
        Interpolated value
        
    Raises:
        ValueError: If the method is not supported or coordinates are out of bounds
    """
    if method not in ["bilinear", "bicubic"]:
        raise ValueError(f"Unsupported interpolation method: {method}")
    
    # Create a cache key
    cache_key = (id(map_obj), lat, lon, method)
    
    # Check if result is in cache
    if cache_key in _interpolation_cache:
        return _interpolation_cache[cache_key]
    
    # Calculate and cache the result
    result = map_obj.interpolate(lat, lon, method)
    _interpolation_cache[cache_key] = result
    
    return result
