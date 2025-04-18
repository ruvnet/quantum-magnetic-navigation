"""MCP tool for simulating navigation trajectories."""

from __future__ import annotations

from typing import Dict, Any, List, Tuple, Optional
import math
import random

import numpy as np
from mcp.types import Tool, CallToolResult as ToolResult, TextContent
import json

from qmag_nav.models.geo import LatLon
from qmag_nav.filter.utils import latlon_to_meters, meters_to_latlon
from qmag_nav.mapping.backend import load_map, cached_interpolate


class TrajectorySimulationTool:
    """MCP tool for simulating navigation trajectories."""

    def __init__(self, map_path: Optional[str] = None):
        """Initialize the trajectory simulation tool.
        
        Args:
            map_path: Optional path to the magnetic map file. If not provided,
                     the tool will attempt to load a default map when first used.
        """
        self._map_path = map_path
        self._map = None
    
    def get_tool_definition(self) -> Tool:
        """Return the tool definition for MCP discovery."""
        return Tool(
            name="simulate_trajectory",
            description="Generate simulated navigation data along a trajectory",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_latitude": {
                        "type": "number",
                        "description": "Starting latitude in decimal degrees"
                    },
                    "start_longitude": {
                        "type": "number",
                        "description": "Starting longitude in decimal degrees"
                    },
                    "end_latitude": {
                        "type": "number",
                        "description": "Ending latitude in decimal degrees"
                    },
                    "end_longitude": {
                        "type": "number",
                        "description": "Ending longitude in decimal degrees"
                    },
                    "speed": {
                        "type": "number",
                        "description": "Speed in meters per second"
                    },
                    "sample_rate": {
                        "type": "number",
                        "description": "Sampling rate in Hz"
                    },
                    "noise_level": {
                        "type": "number",
                        "description": "Noise level for magnetic measurements in nT"
                    },
                    "path_type": {
                        "type": "string",
                        "description": "Type of path to simulate",
                        "enum": ["straight", "curved", "random"]
                    }
                },
                "required": ["start_latitude", "start_longitude", "end_latitude", "end_longitude"]
            }
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute the trajectory simulation.
        
        Args:
            arguments: Dictionary containing the tool arguments
                - start_latitude: Starting latitude in decimal degrees
                - start_longitude: Starting longitude in decimal degrees
                - end_latitude: Ending latitude in decimal degrees
                - end_longitude: Ending longitude in decimal degrees
                - speed: Optional speed in meters per second (default: 10)
                - sample_rate: Optional sampling rate in Hz (default: 1)
                - noise_level: Optional noise level for magnetic measurements in nT (default: 5)
                - path_type: Optional type of path to simulate (default: "straight")
                
        Returns:
            ToolResult containing the simulated trajectory data
            
        Raises:
            ValueError: If the arguments are invalid
        """
        # Extract and validate arguments
        try:
            start_lat = float(arguments.get("start_latitude"))
            start_lon = float(arguments.get("start_longitude"))
            end_lat = float(arguments.get("end_latitude"))
            end_lon = float(arguments.get("end_longitude"))
            
            # Optional arguments with defaults
            speed = float(arguments.get("speed", 10.0))  # m/s
            sample_rate = float(arguments.get("sample_rate", 1.0))  # Hz
            noise_level = float(arguments.get("noise_level", 5.0))  # nT
            path_type = arguments.get("path_type", "straight")
            
            if path_type not in ["straight", "curved", "random"]:
                path_type = "straight"
                
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
        
        try:
            # Calculate the total distance in meters
            north_m, east_m = latlon_to_meters(
                start_lat, start_lon, end_lat, end_lon
            )
            total_distance = math.sqrt(north_m**2 + east_m**2)
            
            # Calculate the total time needed
            total_time = total_distance / speed  # seconds
            
            # Calculate the number of samples
            num_samples = max(2, int(total_time * sample_rate))
            
            # Generate the trajectory points
            trajectory = self._generate_trajectory(
                start_lat, start_lon,
                end_lat, end_lon,
                num_samples,
                path_type
            )
            
            # Calculate time steps
            time_steps = [i / sample_rate for i in range(num_samples)]
            
            # Generate magnetic field values along the trajectory
            magnetic_values = []
            for lat, lon in trajectory:
                try:
                    # Get the true magnetic field value
                    true_value = cached_interpolate(self._map, lat, lon, "bilinear")
                    
                    # Add noise
                    noisy_value = true_value + random.gauss(0, noise_level)
                    magnetic_values.append(noisy_value)
                except ValueError:
                    # If outside map bounds, use a default value
                    magnetic_values.append(0.0)
            
            # Prepare the result data
            trajectory_data = []
            for i in range(num_samples):
                trajectory_data.append({
                    "time": time_steps[i],
                    "position": {
                        "latitude": trajectory[i][0],
                        "longitude": trajectory[i][1]
                    },
                    "magnetic_field": magnetic_values[i]
                })
            
            # Create a response with text content
            data = {
                "metadata": {
                    "start": {"latitude": start_lat, "longitude": start_lon},
                    "end": {"latitude": end_lat, "longitude": end_lon},
                    "speed": speed,
                    "sample_rate": sample_rate,
                    "noise_level": noise_level,
                    "path_type": path_type,
                    "total_distance": total_distance,
                    "total_time": total_time,
                    "num_points": num_samples
                },
                # Include just the first and last points to keep the response size reasonable
                "first_point": trajectory_data[0] if trajectory_data else None,
                "last_point": trajectory_data[-1] if trajectory_data else None
            }
            
            return ToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Generated trajectory with {num_samples} points from "
                             f"({start_lat:.6f}, {start_lon:.6f}) to "
                             f"({end_lat:.6f}, {end_lon:.6f}).\n"
                             f"Total distance: {total_distance:.2f} m\n"
                             f"Total time: {total_time:.2f} s\n"
                             f"Path type: {path_type}\n\n"
                             f"Data: {json.dumps(data, indent=2)}"
                    )
                ]
            )
        except Exception as e:
            return ToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Error in trajectory simulation: {e}"
                    )
                ]
            )
    
    def _generate_trajectory(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        num_points: int,
        path_type: str
    ) -> List[Tuple[float, float]]:
        """Generate a trajectory between two points.
        
        Args:
            start_lat: Starting latitude
            start_lon: Starting longitude
            end_lat: Ending latitude
            end_lon: Ending longitude
            num_points: Number of points to generate
            path_type: Type of path ("straight", "curved", or "random")
            
        Returns:
            List of (latitude, longitude) points
        """
        if path_type == "straight":
            # Linear interpolation between start and end
            return [
                (
                    start_lat + (end_lat - start_lat) * i / (num_points - 1),
                    start_lon + (end_lon - start_lon) * i / (num_points - 1)
                )
                for i in range(num_points)
            ]
        
        elif path_type == "curved":
            # Generate a curved path using a quadratic Bezier curve
            # We'll create a control point perpendicular to the straight line
            
            # Calculate the midpoint
            mid_lat = (start_lat + end_lat) / 2
            mid_lon = (start_lon + end_lon) / 2
            
            # Calculate a perpendicular vector
            dlat = end_lat - start_lat
            dlon = end_lon - start_lon
            
            # Perpendicular vector (rotate 90 degrees)
            perp_lat = -dlon
            perp_lon = dlat
            
            # Normalize and scale
            length = math.sqrt(perp_lat**2 + perp_lon**2)
            if length > 0:
                # Scale to 20% of the path length
                scale = 0.2 * math.sqrt(dlat**2 + dlon**2) / length
                perp_lat *= scale
                perp_lon *= scale
            
            # Control point
            ctrl_lat = mid_lat + perp_lat
            ctrl_lon = mid_lon + perp_lon
            
            # Generate points using quadratic Bezier curve
            return [
                self._quadratic_bezier(
                    start_lat, start_lon,
                    ctrl_lat, ctrl_lon,
                    end_lat, end_lon,
                    t / (num_points - 1)
                )
                for t in range(num_points)
            ]
        
        else:  # path_type == "random"
            # Start with a straight line
            base_path = [
                (
                    start_lat + (end_lat - start_lat) * i / (num_points - 1),
                    start_lon + (end_lon - start_lon) * i / (num_points - 1)
                )
                for i in range(num_points)
            ]
            
            # Calculate the average distance between points
            total_north, total_east = latlon_to_meters(
                start_lat, start_lon, end_lat, end_lon
            )
            avg_distance = math.sqrt(total_north**2 + total_east**2) / (num_points - 1)
            
            # Add random perturbations to each point (except start and end)
            random_path = [base_path[0]]
            
            for i in range(1, num_points - 1):
                base_lat, base_lon = base_path[i]
                
                # Random perturbation (up to 10% of average distance)
                max_perturbation = 0.1 * avg_distance
                
                # Random distance and angle
                distance = random.uniform(0, max_perturbation)
                angle = random.uniform(0, 2 * math.pi)
                
                # Convert to north/east offsets
                north_offset = distance * math.cos(angle)
                east_offset = distance * math.sin(angle)
                
                # Convert to lat/lon offsets
                perturbed_lat, perturbed_lon = meters_to_latlon(
                    base_lat, base_lon, north_offset, east_offset
                )
                
                random_path.append((perturbed_lat, perturbed_lon))
            
            # Add the end point
            random_path.append(base_path[-1])
            
            return random_path
    
    def _quadratic_bezier(
        self,
        p0_lat: float, p0_lon: float,
        p1_lat: float, p1_lon: float,
        p2_lat: float, p2_lon: float,
        t: float
    ) -> Tuple[float, float]:
        """Calculate a point on a quadratic Bezier curve.
        
        Args:
            p0_lat, p0_lon: Start point
            p1_lat, p1_lon: Control point
            p2_lat, p2_lon: End point
            t: Parameter (0 to 1)
            
        Returns:
            (latitude, longitude) at parameter t
        """
        # Quadratic Bezier formula: B(t) = (1-t)²P₀ + 2(1-t)tP₁ + t²P₂
        t2 = t * t
        mt = 1 - t
        mt2 = mt * mt
        
        lat = mt2 * p0_lat + 2 * mt * t * p1_lat + t2 * p2_lat
        lon = mt2 * p0_lon + 2 * mt * t * p1_lon + t2 * p2_lon
        
        return (lat, lon)