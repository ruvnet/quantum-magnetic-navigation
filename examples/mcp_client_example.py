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
import subprocess
from typing import Dict, Any, List, Optional

from mcp.client import Client
from mcp.client.stdio import stdio_client


async def run_query_magnetic_field(client: Client, lat: float, lon: float) -> None:
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
    client: Client,
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


async def run_sensor_calibration(client: Client) -> None:
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


async def run_trajectory_simulation(client: Client) -> None:
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
            
            print(f"\nFirst point: {json.dumps(data['trajectory'][0], indent=2)}")
            print(f"\nLast point: {json.dumps(data['trajectory'][-1], indent=2)}")
            print(f"\nTotal points: {len(data['trajectory'])}")


async def run_demo(server_process) -> None:
    """Run a complete demo of all MCP tools."""
    # Connect to the server
    async with stdio_client(server_process.stdout, server_process.stdin) as client:
        # Wait for server initialization
        await asyncio.sleep(1)
        
        # List available tools
        print("=== Available Tools ===")
        tools = await client.list_tools()
        for tool in tools:
            print(f"- {tool.name}: {tool.description}")
            print(f"  Parameters: {json.dumps({k: v.dict() for k, v in tool.parameters.items()}, indent=2)}")
            print()
        
        # Run each tool demo
        await run_query_magnetic_field(client, 40.5, -73.5)
        await run_position_estimation(client, 50000.0, 40.5, -73.5)
        await run_sensor_calibration(client)
        await run_trajectory_simulation(client)
        
        print("\n=== Demo completed ===")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="MCP client example for quantum-magnetic-navigation")
    
    parser.add_argument(
        "--map", "-m",
        dest="map_path",
        help="Path to the magnetic map file for the server"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Find the server script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(script_dir, "..", "scripts", "run_mcp_server.py")
    
    # Prepare server command
    cmd = [sys.executable, server_script]
    if args.map_path:
        cmd.extend(["--map", args.map_path])
    
    # Start the server as a subprocess
    print(f"Starting MCP server: {' '.join(cmd)}")
    server_process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,  # Use binary mode for stdio
        bufsize=0    # Unbuffered
    )
    
    try:
        # Run the demo
        asyncio.run(run_demo(server_process))
    finally:
        # Clean up
        print("Shutting down server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()


if __name__ == "__main__":
    main()