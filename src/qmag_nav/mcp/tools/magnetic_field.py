"""MCP tool for querying magnetic field values at specific coordinates."""

from __future__ import annotations

from typing import Dict, Any, Optional, List, Tuple

from mcp.types import Tool, CallToolResult as ToolResult, TextContent
import json

from qmag_nav.mapping.backend import load_map, cached_interpolate
from qmag_nav.models.geo import LatLon, MagneticVector


class MagneticFieldTool:
    """MCP tool for querying magnetic field values at specific coordinates."""

    def __init__(self, map_path: Optional[str] = None):
        """Initialize the magnetic field tool.
        
        Args:
            map_path: Optional path to the magnetic map file. If not provided,
                     the tool will attempt to load a default map when first used.
        """
        self._map_path = map_path
        self._map = None
    
    def get_tool_definition(self) -> Tool:
        """Return the tool definition for MCP discovery."""
        return Tool(
            name="query_magnetic_field",
            description="Get magnetic field values at specific coordinates",
            inputSchema={
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "description": "Latitude in decimal degrees"
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude in decimal degrees"
                    },
                    "interpolation_method": {
                        "type": "string",
                        "description": "Interpolation method (bilinear or bicubic)",
                        "enum": ["bilinear", "bicubic"]
                    }
                },
                "required": ["latitude", "longitude"]
            }
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute the magnetic field query.
        
        Args:
            arguments: Dictionary containing the tool arguments
                - latitude: Latitude in decimal degrees
                - longitude: Longitude in decimal degrees
                - interpolation_method: Optional interpolation method
                
        Returns:
            ToolResult containing the magnetic field value
            
        Raises:
            ValueError: If the coordinates are outside the map bounds
        """
        # Extract and validate arguments
        try:
            latitude = float(arguments.get("latitude"))
            longitude = float(arguments.get("longitude"))
            method = arguments.get("interpolation_method", "bilinear")
            
            if method not in ["bilinear", "bicubic"]:
                method = "bilinear"
                
        except (ValueError, TypeError) as e:
            return ToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Invalid coordinates: {e}"
                    )
                ]
            )
        
        # Load map if not already loaded
        if self._map is None:
            try:
                if self._map_path:
                    self._map = load_map(self._map_path)
                else:
                    # Try to find a default map in the package
                    import os
                    import pkg_resources
                    
                    # Look for maps in standard locations
                    possible_paths = [
                        "mag_data/default.tif",
                        "mag_data/default.nc",
                    ]
                    
                    for path in possible_paths:
                        try:
                            full_path = pkg_resources.resource_filename("qmag_nav", path)
                            if os.path.exists(full_path):
                                self._map = load_map(full_path)
                                break
                        except (ImportError, FileNotFoundError):
                            continue
                    
                    if self._map is None:
                        return ToolResult(
                            content=[
                                TextContent(
                                    type="text",
                                    text="No magnetic map loaded and no default map found."
                                )
                            ]
                        )
            except Exception as e:
                return ToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Failed to load magnetic map: {e}"
                        )
                    ]
                )
        
        # Query the magnetic field
        try:
            # Get the interpolated magnetic field value
            mag_value = cached_interpolate(self._map, latitude, longitude, method)
            
            # Create a response with text content
            data = {
                "latitude": latitude,
                "longitude": longitude,
                "magnetic_field": mag_value,
                "units": "nT",
                "interpolation_method": method
            }
            
            return ToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Magnetic field at ({latitude}, {longitude}): {mag_value:.2f} nT\n\n"
                             f"Data: {json.dumps(data, indent=2)}"
                    )
                ]
            )
        except ValueError as e:
            return ToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Error querying magnetic field: {e}"
                    )
                ]
            )