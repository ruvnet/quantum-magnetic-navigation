"""MCP stdio transport implementation for quantum-magnetic-navigation."""

from __future__ import annotations

import asyncio
import sys
from typing import Tuple, AsyncIterator

from mcp.server.stdio import stdio_server


async def create_stdio_transport() -> Tuple[AsyncIterator[str], asyncio.StreamWriter]:
    """Create a stdio transport for MCP.
    
    Returns:
        Tuple of (input_stream, output_stream) for MCP server
    """
    async with stdio_server() as (input_stream, output_stream):
        return input_stream, output_stream