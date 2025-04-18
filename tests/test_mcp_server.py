"""Tests for the MCP server implementation."""

import asyncio
import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp.types import Tool, CallToolResult as ToolResult, TextContent
import json

from qmag_nav.mcp.server import QMagNavServer
from qmag_nav.mcp.tools.magnetic_field import MagneticFieldTool
from qmag_nav.mcp.tools.position_estimation import PositionEstimationTool
from qmag_nav.mcp.tools.sensor_calibration import SensorCalibrationTool
from qmag_nav.mcp.tools.trajectory_simulation import TrajectorySimulationTool


@pytest.fixture
def mock_map():
    """Create a mock map for testing."""
    with patch("qmag_nav.mapping.backend.load_map") as mock_load_map:
        # Create a simple mock map
        mock_map = MagicMock()
        mock_map.lat_min = 40.0
        mock_map.lat_max = 41.0
        mock_map.lon_min = -74.0
        mock_map.lon_max = -73.0
        mock_map.rows = 11
        mock_map.cols = 11
        mock_map.interpolate.return_value = 50000.0  # 50,000 nT
        
        # Configure the mock to return our mock map
        mock_load_map.return_value = mock_map
        
        yield mock_map


@pytest.mark.asyncio
async def test_server_list_tools():
    """Test that the server correctly lists available tools."""
    server = QMagNavServer()
    
    # Call the list_tools handler
    tools = await server._handle_list_tools()
    
    # Verify that all expected tools are present
    tool_names = [tool.name for tool in tools]
    assert "query_magnetic_field" in tool_names
    assert "estimate_position" in tool_names
    assert "calibrate_sensor" in tool_names
    assert "simulate_trajectory" in tool_names
    
    # Verify that each tool has the required fields
    for tool in tools:
        assert tool.name
        assert tool.description
        assert tool.inputSchema


@pytest.mark.asyncio
async def test_magnetic_field_tool(mock_map):
    """Test the magnetic field query tool."""
    # Create the tool
    tool = MagneticFieldTool()
    
    # Mock the map loading
    tool._map = mock_map
    
    # Test execution with valid arguments
    result = await tool.execute({
        "latitude": 40.5,
        "longitude": -73.5,
        "interpolation_method": "bilinear"
    })
    
    # Verify the result
    assert isinstance(result, ToolResult)
    assert len(result.content) == 1
    
    # Check text content
    text_content = result.content[0]
    assert text_content.type == "text"
    
    # We're only using TextContent in this version
    assert "Magnetic field at (40.5, -73.5)" in text_content.text


@pytest.mark.asyncio
async def test_position_estimation_tool(mock_map):
    """Test the position estimation tool."""
    # Create the tool
    tool = PositionEstimationTool()
    
    # Mock the map loading
    tool._map = mock_map
    
    # Test execution with valid arguments
    result = await tool.execute({
        "magnetic_field": 50000.0,
        "initial_latitude": 40.5,
        "initial_longitude": -73.5,
        "dt": 1.0,
        "reset": True
    })
    
    # Verify the result
    assert isinstance(result, ToolResult)
    assert len(result.content) == 1
    
    # Check text content
    text_content = result.content[0]
    assert text_content.type == "text"
    
    # We're only using TextContent in this version
    assert "Estimated position" in text_content.text
    assert "Velocity" in text_content.text
    assert "Position uncertainty" in text_content.text


@pytest.mark.asyncio
async def test_sensor_calibration_tool():
    """Test the sensor calibration tool."""
    # Create the tool
    tool = SensorCalibrationTool()
    
    # Create some sample data (8 points on a sphere with some noise)
    samples = [
        [30000, 0, 0],
        [-30000, 0, 0],
        [0, 30000, 0],
        [0, -30000, 0],
        [0, 0, 30000],
        [0, 0, -30000],
        [20000, 20000, 20000],
        [-20000, -20000, -20000]
    ]
    
    # Test execution with valid arguments
    result = await tool.execute({
        "samples": samples,
        "method": "simple"
    })
    
    # Verify the result
    assert isinstance(result, ToolResult)
    assert len(result.content) == 1
    
    # Check text content
    text_content = result.content[0]
    assert text_content.type == "text"
    
    # We're only using TextContent in this version
    assert "Calibration completed" in text_content.text
    assert "Scale factors" in text_content.text
    assert "Offsets" in text_content.text


@pytest.mark.asyncio
async def test_trajectory_simulation_tool(mock_map):
    """Test the trajectory simulation tool."""
    # Create the tool
    tool = TrajectorySimulationTool()
    
    # Mock the map loading
    tool._map = mock_map
    
    # Test execution with valid arguments
    result = await tool.execute({
        "start_latitude": 40.2,
        "start_longitude": -73.8,
        "end_latitude": 40.8,
        "end_longitude": -73.2,
        "speed": 10.0,
        "sample_rate": 1.0,
        "noise_level": 5.0,
        "path_type": "straight"
    })
    
    # Verify the result
    assert isinstance(result, ToolResult)
    assert len(result.content) == 1
    
    # Check text content
    text_content = result.content[0]
    assert text_content.type == "text"
    
    # We're only using TextContent in this version
    assert "Generated trajectory" in text_content.text
    assert "Total distance" in text_content.text
    assert "Path type" in text_content.text


@pytest.mark.asyncio
async def test_server_call_tool():
    """Test that the server correctly routes tool calls."""
    server = QMagNavServer()
    
    # Mock the tools
    for tool_name in server.tools:
        server.tools[tool_name].execute = AsyncMock(return_value=ToolResult(
            content=[TextContent(type="text", text=f"Mock result for {tool_name}")]
        ))
    
    # Test calling each tool
    for tool_name in server.tools:
        result = await server._handle_call_tool(tool_name, {})
        
        # Verify the result
        assert isinstance(result, ToolResult)
        assert len(result.content) == 1
        assert result.content[0].text == f"Mock result for {tool_name}"
        
        # Verify the tool was called
        server.tools[tool_name].execute.assert_called_once_with({})
    
    # Test calling an unknown tool
    result = await server._handle_call_tool("unknown_tool", {})
    assert "Unknown tool" in result.content[0].text


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])