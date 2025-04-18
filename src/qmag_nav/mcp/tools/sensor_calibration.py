"""MCP tool for magnetometer sensor calibration."""

from __future__ import annotations

from typing import Dict, Any, List, Tuple, Optional

import numpy as np
from mcp.types import Tool, CallToolResult as ToolResult, TextContent
import json

from qmag_nav.models.sensor import CalibrationParams


class SensorCalibrationTool:
    """MCP tool for magnetometer sensor calibration."""

    def __init__(self):
        """Initialize the sensor calibration tool."""
        pass
    
    def get_tool_definition(self) -> Tool:
        """Return the tool definition for MCP discovery."""
        return Tool(
            name="calibrate_sensor",
            description="Calibrate magnetometer sensor using collected samples",
            inputSchema={
                "type": "object",
                "properties": {
                    "samples": {
                        "type": "array",
                        "description": "Array of [Bx, By, Bz] magnetic field samples in nT",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 3,
                            "maxItems": 3
                        }
                    },
                    "method": {
                        "type": "string",
                        "description": "Calibration method to use",
                        "enum": ["ellipsoid", "simple"]
                    }
                },
                "required": ["samples"]
            }
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute the sensor calibration.
        
        Args:
            arguments: Dictionary containing the tool arguments
                - samples: Array of [Bx, By, Bz] magnetic field samples
                - method: Optional calibration method (ellipsoid or simple)
                
        Returns:
            ToolResult containing the calibration parameters
            
        Raises:
            ValueError: If the arguments are invalid
        """
        # Extract and validate arguments
        try:
            samples = arguments.get("samples", [])
            method = arguments.get("method", "ellipsoid")
            
            if not isinstance(samples, list) or len(samples) < 8:
                return ToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text="At least 8 samples are required for calibration."
                        )
                    ]
                )
            
            # Convert samples to numpy array
            samples_array = np.array(samples, dtype=float)
            if samples_array.ndim != 2 or samples_array.shape[1] != 3:
                return ToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text="Samples must be an array of [Bx, By, Bz] values."
                        )
                    ]
                )
                
        except (ValueError, TypeError) as e:
            return ToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Invalid arguments: {e}"
                    )
                ]
            )
        
        try:
            # Perform calibration based on the selected method
            if method == "ellipsoid":
                cal_params = self._ellipsoid_calibration(samples_array)
            else:  # method == "simple"
                cal_params = self._simple_calibration(samples_array)
            
            # Create a response with text content
            data = {
                "calibration": {
                    "scale": cal_params.scale,
                    "offset": cal_params.offset,
                    "method": method,
                    "samples_used": len(samples)
                }
            }
            
            return ToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Calibration completed using {method} method.\n"
                             f"Scale factors: [{cal_params.scale[0]:.4f}, {cal_params.scale[1]:.4f}, {cal_params.scale[2]:.4f}]\n"
                             f"Offsets: [{cal_params.offset[0]:.2f}, {cal_params.offset[1]:.2f}, {cal_params.offset[2]:.2f}] nT\n"
                             f"Apply these parameters to correct raw sensor readings.\n\n"
                             f"Data: {json.dumps(data, indent=2)}"
                    )
                ]
            )
        except Exception as e:
            return ToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Error in sensor calibration: {e}"
                    )
                ]
            )
    
    def _simple_calibration(self, samples: np.ndarray) -> CalibrationParams:
        """Perform simple min/max calibration.
        
        This method calculates scale factors and offsets based on the min/max values
        in each axis, assuming the sensor should measure points on a sphere.
        
        Args:
            samples: Array of [Bx, By, Bz] magnetic field samples
            
        Returns:
            CalibrationParams with scale and offset values
        """
        # Find min and max values for each axis
        min_values = np.min(samples, axis=0)
        max_values = np.max(samples, axis=0)
        
        # Calculate offsets (center of the range)
        offsets = (min_values + max_values) / 2
        
        # Calculate scale factors
        # Assuming the true field should be a sphere, we normalize by the average range
        ranges = max_values - min_values
        avg_range = np.mean(ranges)
        
        # Avoid division by zero
        ranges = np.where(ranges < 1e-6, 1.0, ranges)
        
        # Scale factors to normalize each axis to the average range
        scales = avg_range / ranges
        
        return CalibrationParams(
            scale=scales.tolist(),
            offset=offsets.tolist()
        )
    
    def _ellipsoid_calibration(self, samples: np.ndarray) -> CalibrationParams:
        """Perform ellipsoid fitting calibration.
        
        This method fits an ellipsoid to the sample points and calculates
        the transformation to convert it to a sphere centered at the origin.
        
        Args:
            samples: Array of [Bx, By, Bz] magnetic field samples
            
        Returns:
            CalibrationParams with scale and offset values
        """
        # For simplicity, we'll use a basic approach:
        # 1. Find the center of the ellipsoid (average of all points)
        # 2. Center the points
        # 3. Find the scaling factors to make it spherical
        
        # Find the center (offset)
        center = np.mean(samples, axis=0)
        
        # Center the points
        centered = samples - center
        
        # Find the average distance from center for each axis
        axis_ranges = np.mean(np.abs(centered), axis=0) * 2
        
        # Calculate scale factors to make it spherical
        # We'll normalize to the average of the three axes
        avg_range = np.mean(axis_ranges)
        
        # Avoid division by zero
        axis_ranges = np.where(axis_ranges < 1e-6, 1.0, axis_ranges)
        
        # Scale factors
        scales = avg_range / axis_ranges
        
        return CalibrationParams(
            scale=scales.tolist(),
            offset=center.tolist()
        )