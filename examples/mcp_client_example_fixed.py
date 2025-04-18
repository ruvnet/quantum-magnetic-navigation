#!/usr/bin/env python3
"""
Example client for the quantum-magnetic-navigation MCP server.

This script demonstrates how to interact with the MCP server
using the Python MCP client library.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import traceback
from datetime import timedelta
from typing import Dict, Any, List, Optional

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession


async def run_query_magnetic_field(client, lat: float, lon: float) -> None:
    """Query the magnetic field at a specific location."""
    print(f"\n=== Querying magnetic field at ({lat}, {lon}) ===")
    
    result = await client.call_tool(
        "query_magnetic_field",
        {
            "latitude": lat,
            "longitude": lon,
            "interpolation_method": "bilinear"
        }
    )
    
    # Print the text response
    for content in result.content:
        if content.type == "text":
            print(content.text)
        elif content.type == "json":
            print("\nDetailed data:")
            print(json.dumps(content.json, indent=2))


async def run_position_estimation(
    client,
    magnetic_field: float,
    initial_lat: Optional[float] = None,
    initial_lon: Optional[float] = None
) -> None:
    """Estimate position using the EKF."""
    print(f"\n=== Estimating position with magnetic field {magnetic_field} nT ===")
    
    # Prepare arguments
    args = {
        "magnetic_field": magnetic_field,
        "dt": 1.0,
        "reset": True
    }
    
    if initial_lat is not None and initial_lon is not None:
        args["initial_latitude"] = initial_lat
        args["initial_longitude"] = initial_lon
        print(f"Using initial position: ({initial_lat}, {initial_lon})")
    
    result = await client.call_tool("estimate_position", args)
    
    # Print the text response
    for content in result.content:
        if content.type == "text":
            print(content.text)
        elif content.type == "json":
            print("\nDetailed data:")
            print(json.dumps(content.json, indent=2))


async def run_sensor_calibration(client) -> None:
    """Run sensor calibration with sample data."""
    print("\n=== Calibrating sensor with sample data ===")
    
    # Create some sample data (points on a sphere with some noise)
    samples = [
        [30000, 0, 0],
        [-30000, 0, 0],
        [0, 30000, 0],
        [0, -30000, 0],
        [0, 0, 30000],
        [0, 0, -30000],
        [20000, 20000, 20000],
        [-20000, -20000, -20000],
        # Add some noise
        [29800, 200, -150],
        [-29900, -100, 300],
        [150, 30100, -200],
        [-250, -29800, 150]
    ]
    
    result = await client.call_tool(
        "calibrate_sensor",
        {
            "samples": samples,
            "method": "ellipsoid"
        }
    )
    
    # Print the text response
    for content in result.content:
        if content.type == "text":
            print(content.text)
        elif content.type == "json":
            print("\nDetailed data:")
            print(json.dumps(content.json, indent=2))


async def run_trajectory_simulation(client) -> None:
    """Simulate a navigation trajectory."""
    print("\n=== Simulating a navigation trajectory ===")
    
    # Define a trajectory
    start_lat = 40.2
    start_lon = -73.8
    end_lat = 40.8
    end_lon = -73.2
    
    result = await client.call_tool(
        "simulate_trajectory",
        {
            "start_latitude": start_lat,
            "start_longitude": start_lon,
            "end_latitude": end_lat,
            "end_longitude": end_lon,
            "speed": 10.0,
            "sample_rate": 1.0,
            "noise_level": 5.0,
            "path_type": "curved"
        }
    )
    
    # Print the text response
    for content in result.content:
        if content.type == "text":
            print(content.text)
        elif content.type == "json":
            # Just print metadata and first/last points to avoid too much output
            data = content.json
            print("\nTrajectory metadata:")
            print(json.dumps(data["metadata"], indent=2))
            
            if "trajectory" in data:
                print(f"\nFirst point: {json.dumps(data['trajectory'][0], indent=2)}")
                print(f"\nLast point: {json.dumps(data['trajectory'][-1], indent=2)}")
                print(f"\nTotal points: {len(data['trajectory'])}")
            elif "first_point" in data and "last_point" in data:
                print(f"\nFirst point: {json.dumps(data['first_point'], indent=2)}")
                print(f"\nLast point: {json.dumps(data['last_point'], indent=2)}")


async def run_demo() -> None:
    """Run a complete demo of all MCP tools."""
    # Define the server parameters
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["/workspaces/codex/quantum-magnetic-navigation/scripts/run_mcp_server_fixed.py", "--verbose"]
    )
    
    # Connect to the server
    print("Connecting to MCP server...")
    
    # Set a timeout for the entire demo
    try:
        async with asyncio.timeout(30):  # 30 second timeout
            # Use the default stderr for error logging
            async with stdio_client(server_params) as (read_stream, write_stream):
                # Create a client from the streams with a timeout
                client = ClientSession(
                    read_stream, 
                    write_stream,
                    read_timeout_seconds=timedelta(seconds=5)  # 5 second timeout for operations
                )
                
                # Wait for server initialization
                await asyncio.sleep(2)
                
                try:
                    # List available tools
                    print("=== Available Tools ===")
                    tools = await client.list_tools()
                    for tool in tools:
                        print(f"- {tool.name}: {tool.description}")
                        # Handle different API versions
                        if hasattr(tool, 'parameters'):
                            if hasattr(tool.parameters, 'items'):
                                print(f"  Parameters: {json.dumps({k: v.dict() for k, v in tool.parameters.items()}, indent=2)}")
                            else:
                                print(f"  Parameters: {tool.parameters}")
                        print()
                    
                    # Run each tool demo
                    await run_query_magnetic_field(client, 40.5, -73.5)
                    await run_position_estimation(client, 50000.0, 40.5, -73.5)
                    await run_sensor_calibration(client)
                    await run_trajectory_simulation(client)
                    
                    print("\n=== Demo completed ===")
                except Exception as e:
                    print(f"Error during demo: {e}")
                    print(traceback.format_exc())
    except asyncio.TimeoutError:
        print("Demo timed out after 30 seconds")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="MCP client example for quantum-magnetic-navigation")
    
    parser.add_argument(
        "--map", "-m",
        dest="map_path",
        help="Path to the magnetic map file for the server"
    )
    
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug logging"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    try:
        # Run the demo
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("Demo stopped by user")
    except Exception as e:
        print(f"Error: {e}")
        print(traceback.format_exc())


if __name__ == "__main__":
    main()