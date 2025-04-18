#!/usr/bin/env python3
"""
Run the quantum-magnetic-navigation MCP server.

This script starts the MCP server with optional configuration parameters.
"""

import argparse
import asyncio
import logging
import os
import sys

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Modify import to use relative path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Import the server class directly
from qmag_nav.mcp.server import QMagNavServer


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run the quantum-magnetic-navigation MCP server")
    
    parser.add_argument(
        "--map", "-m",
        dest="map_path",
        help="Path to the magnetic map file (GeoTIFF or NetCDF)"
    )
    
    parser.add_argument(
        "--name", "-n",
        dest="server_name",
        default="QMagNavServer",
        help="Name of the MCP server"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create and run the server
    server = QMagNavServer(
        server_name=args.server_name,
        map_path=args.map_path
    )
    
    try:
        await server.run()
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
    except Exception as e:
        logging.error(f"Server error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))