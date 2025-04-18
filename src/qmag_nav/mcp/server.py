"""MCP server implementation for quantum-magnetic-navigation.

This module provides a Model Context Protocol (MCP) server that exposes
quantum-magnetic-navigation functionality as tools that can be used by
AI assistants and other MCP clients.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any

from mcp.server.lowlevel import Server
from mcp.types import (
    Tool,
    CallToolResult as ToolResult,
    TextContent,
    InitializeRequestParams
)

from qmag_nav.mcp.tools.magnetic_field import MagneticFieldTool
from qmag_nav.mcp.tools.position_estimation import PositionEstimationTool
from qmag_nav.mcp.tools.sensor_calibration import SensorCalibrationTool
from qmag_nav.mcp.tools.trajectory_simulation import TrajectorySimulationTool
from qmag_nav.mcp.transport.stdio import create_stdio_transport


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("qmag_nav.mcp")


class QMagNavServer:
    """MCP server for quantum-magnetic-navigation.
    
    This server exposes the following tools:
    - query_magnetic_field: Get magnetic field values at coordinates
    - estimate_position: Use EKF to estimate position
    - calibrate_sensor: Calibration utilities
    - simulate_trajectory: Generate simulated navigation data
    """
    
    def __init__(
        self,
        server_name: str = "QMagNavServer",
        map_path: Optional[str] = None
    ):
        """Initialize the MCP server.
        
        Args:
            server_name: Name of the MCP server
            map_path: Optional path to the magnetic map file
        """
        self.server_name = server_name
        self.map_path = map_path
        
        # Initialize the MCP server
        self.server = Server(server_name)
        
        # Initialize tools
        self.tools = {
            "query_magnetic_field": MagneticFieldTool(map_path),
            "estimate_position": PositionEstimationTool(map_path),
            "calibrate_sensor": SensorCalibrationTool(),
            "simulate_trajectory": TrajectorySimulationTool(map_path)
        }
        
        # Register handlers
        self.server.list_tools()(self._handle_list_tools)
        self.server.call_tool()(self._handle_call_tool)
    
    async def _handle_list_tools(self) -> List[Tool]:
        """Return available tools during discovery phase."""
        logger.info("Listing available tools")
        
        # Collect tool definitions from all tool implementations
        return [
            tool.get_tool_definition()
            for tool in self.tools.values()
        ]
    
    async def _handle_call_tool(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Execute requested tool with provided arguments."""
        logger.info(f"Executing tool: {name} with arguments: {arguments}")
        
        if name not in self.tools:
            error_message = f"Unknown tool: {name}"
            logger.error(error_message)
            return ToolResult(
                content=[TextContent(type="text", text=error_message)]
            )
        
        try:
            # Execute the tool
            tool = self.tools[name]
            result = await tool.execute(arguments)
            return result
        except Exception as e:
            error_message = f"Error executing tool {name}: {e}"
            logger.error(error_message)
            return ToolResult(
                content=[TextContent(type="text", text=error_message)]
            )
    
    async def run(self):
        """Run the MCP server."""
        logger.info(f"Starting {self.server_name}")
        
        # Create stdio transport
        input_stream, output_stream = await create_stdio_transport()
        
        # Run the server
        await self.server.run(
            input_stream,
            output_stream,
            {
                "serverName": self.server_name,
                "serverVersion": "0.1.0",
                "capabilities": self.server.get_capabilities()
            }
        )


async def main():
    """Main entry point for the MCP server."""
    # Get map path from environment variable if available
    map_path = os.environ.get("QMAG_NAV_MAP_PATH")
    
    # Create and run the server
    server = QMagNavServer(map_path=map_path)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())