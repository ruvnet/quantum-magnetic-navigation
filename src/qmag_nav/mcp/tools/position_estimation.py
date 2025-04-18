"""MCP tool for position estimation using Extended Kalman Filter."""

from __future__ import annotations

from typing import Dict, Any, Optional, List, Tuple, Callable

from mcp.types import Tool, CallToolResult as ToolResult, TextContent
import json

from qmag_nav.filter.ekf import NavEKF
from qmag_nav.mapping.backend import load_map, cached_interpolate
from qmag_nav.models.geo import LatLon, MagneticVector


class PositionEstimationTool:
    """MCP tool for estimating position using Extended Kalman Filter."""

    def __init__(self, map_path: Optional[str] = None):
        """Initialize the position estimation tool.
        
        Args:
            map_path: Optional path to the magnetic map file. If not provided,
                     the tool will attempt to load a default map when first used.
        """
        self._map_path = map_path
        self._map = None
        self._ekf = None
    
    def get_tool_definition(self) -> Tool:
        """Return the tool definition for MCP discovery."""
        return Tool(
            name="estimate_position",
            description="Estimate position using Extended Kalman Filter with magnetic measurements",
            inputSchema={
                "type": "object",
                "properties": {
                    "magnetic_field": {
                        "type": "number",
                        "description": "Measured magnetic field value in nT"
                    },
                    "initial_latitude": {
                        "type": "number",
                        "description": "Initial latitude estimate in decimal degrees"
                    },
                    "initial_longitude": {
                        "type": "number",
                        "description": "Initial longitude estimate in decimal degrees"
                    },
                    "dt": {
                        "type": "number",
                        "description": "Time step in seconds since last measurement"
                    },
                    "reset": {
                        "type": "boolean",
                        "description": "Reset the filter with new initial position"
                    }
                },
                "required": ["magnetic_field"]
            }
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute the position estimation.
        
        Args:
            arguments: Dictionary containing the tool arguments
                - magnetic_field: Measured magnetic field value in nT
                - initial_latitude: Optional initial latitude estimate
                - initial_longitude: Optional initial longitude estimate
                - dt: Optional time step in seconds since last measurement
                - reset: Optional flag to reset the filter
                
        Returns:
            ToolResult containing the estimated position
            
        Raises:
            ValueError: If the arguments are invalid
        """
        # Extract and validate arguments
        try:
            magnetic_field = float(arguments.get("magnetic_field"))
            
            # Optional arguments
            initial_lat = arguments.get("initial_latitude")
            initial_lon = arguments.get("initial_longitude")
            dt = arguments.get("dt", 1.0)
            reset = arguments.get("reset", False)
            
            if initial_lat is not None:
                initial_lat = float(initial_lat)
            if initial_lon is not None:
                initial_lon = float(initial_lon)
            if dt is not None:
                dt = float(dt)
                
        except (ValueError, TypeError) as e:
            return ToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Invalid arguments: {e}"
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
        
        # Initialize or reset EKF if needed
        if self._ekf is None or reset:
            if initial_lat is None or initial_lon is None:
                # If no initial position is provided, use the center of the map
                initial_lat = (self._map.lat_min + self._map.lat_max) / 2
                initial_lon = (self._map.lon_min + self._map.lon_max) / 2
            
            # Create a new EKF instance
            self._ekf = NavEKF(
                initial=LatLon(lat=initial_lat, lon=initial_lon),
                initial_velocity=None,  # Default to zero velocity
                process_noise=0.01  # Default process noise
            )
        
        # Define the magnetic field lookup function for the EKF
        def mag_map_func(lat: float, lon: float) -> float:
            try:
                return cached_interpolate(self._map, lat, lon, "bilinear")
            except ValueError:
                # If outside map bounds, return a default value
                # This is not ideal but prevents the filter from failing
                return 0.0
        
        try:
            # Predict step (move the state forward in time)
            self._ekf.predict(dt)
            
            # Update step (incorporate the magnetic measurement)
            self._ekf.update(magnetic_field, mag_map_func)
            
            # Get the current position estimate
            position = self._ekf.estimate()
            
            # Get the current velocity estimate
            velocity_deg = self._ekf.velocity()
            velocity_ms = self._ekf.velocity_ms()
            
            # Get uncertainty estimates
            pos_uncertainty = self._ekf.position_uncertainty()
            vel_uncertainty = self._ekf.velocity_uncertainty()
            
            # Create a response with text content
            data = {
                "position": {
                    "latitude": position.lat,
                    "longitude": position.lon
                },
                "velocity": {
                    "north_mps": velocity_ms[0],
                    "east_mps": velocity_ms[1],
                    "dlat_dps": velocity_deg[0],
                    "dlon_dps": velocity_deg[1]
                },
                "uncertainty": {
                    "position": {
                        "latitude": pos_uncertainty[0],
                        "longitude": pos_uncertainty[1]
                    },
                    "velocity": {
                        "dlat": vel_uncertainty[0],
                        "dlon": vel_uncertainty[1]
                    }
                }
            }
            
            return ToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Estimated position: ({position.lat:.6f}, {position.lon:.6f})\n"
                             f"Velocity: {velocity_ms[0]:.2f} m/s N, {velocity_ms[1]:.2f} m/s E\n"
                             f"Position uncertainty: {pos_uncertainty[0]:.6f}° lat, {pos_uncertainty[1]:.6f}° lon\n\n"
                             f"Data: {json.dumps(data, indent=2)}"
                    )
                ]
            )
        except Exception as e:
            return ToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Error in position estimation: {e}"
                    )
                ]
            )