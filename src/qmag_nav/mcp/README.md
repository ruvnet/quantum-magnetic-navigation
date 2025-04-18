# Quantum Magnetic Navigation MCP Server

This directory contains a Model Context Protocol (MCP) server implementation for the Quantum Magnetic Navigation system. The MCP server exposes the core functionality of the navigation system as tools that can be used by AI assistants and other MCP clients.

## Overview

The MCP server provides the following tools:

1. **query_magnetic_field** - Get magnetic field values at specific coordinates
2. **estimate_position** - Use Extended Kalman Filter to estimate position
3. **calibrate_sensor** - Calibration utilities for magnetometer sensors
4. **simulate_trajectory** - Generate simulated navigation data along a trajectory

## Directory Structure

```
mcp/
├── __init__.py           # Package initialization
├── server.py             # Main MCP server implementation
├── tools/                # Tool implementations
│   ├── __init__.py
│   ├── magnetic_field.py
│   ├── position_estimation.py
│   ├── sensor_calibration.py
│   └── trajectory_simulation.py
└── transport/            # Transport layer implementations
    ├── __init__.py
    └── stdio.py          # Standard I/O transport
```

## Usage

### Running the Server

The MCP server can be run using the provided script:

```bash
python -m scripts.run_mcp_server --map path/to/magnetic_map.tif
```

Or directly:

```bash
python -m qmag_nav.mcp.server
```

### Environment Variables

- `QMAG_NAV_MAP_PATH`: Path to the magnetic map file (GeoTIFF or NetCDF)

### Example Client

An example client is provided in `examples/mcp_client_example.py` that demonstrates how to interact with the MCP server:

```bash
python examples/mcp_client_example.py --map path/to/magnetic_map.tif
```

## Tool Documentation

### query_magnetic_field

Gets the magnetic field value at specific coordinates.

**Parameters:**
- `latitude` (number, required): Latitude in decimal degrees
- `longitude` (number, required): Longitude in decimal degrees
- `interpolation_method` (string, optional): Interpolation method ("bilinear" or "bicubic")

**Returns:**
- Text description of the magnetic field value
- JSON object with the magnetic field value and metadata

### estimate_position

Estimates position using an Extended Kalman Filter with magnetic measurements.

**Parameters:**
- `magnetic_field` (number, required): Measured magnetic field value in nT
- `initial_latitude` (number, optional): Initial latitude estimate
- `initial_longitude` (number, optional): Initial longitude estimate
- `dt` (number, optional): Time step in seconds since last measurement
- `reset` (boolean, optional): Reset the filter with new initial position

**Returns:**
- Text description of the estimated position
- JSON object with position, velocity, and uncertainty estimates

### calibrate_sensor

Calibrates a magnetometer sensor using collected samples.

**Parameters:**
- `samples` (array, required): Array of [Bx, By, Bz] magnetic field samples in nT
- `method` (string, optional): Calibration method ("ellipsoid" or "simple")

**Returns:**
- Text description of the calibration parameters
- JSON object with scale factors and offsets

### simulate_trajectory

Generates simulated navigation data along a trajectory.

**Parameters:**
- `start_latitude` (number, required): Starting latitude in decimal degrees
- `start_longitude` (number, required): Starting longitude in decimal degrees
- `end_latitude` (number, required): Ending latitude in decimal degrees
- `end_longitude` (number, required): Ending longitude in decimal degrees
- `speed` (number, optional): Speed in meters per second
- `sample_rate` (number, optional): Sampling rate in Hz
- `noise_level` (number, optional): Noise level for magnetic measurements in nT
- `path_type` (string, optional): Type of path ("straight", "curved", or "random")

**Returns:**
- Text description of the generated trajectory
- JSON object with trajectory points and metadata

## Development

### Adding New Tools

To add a new tool:

1. Create a new file in the `tools/` directory
2. Implement a class with `get_tool_definition()` and `execute()` methods
3. Register the tool in `server.py`

### Running Tests

Tests for the MCP server can be run using pytest:

```bash
pytest tests/test_mcp_server.py
```

## Dependencies

- `mcp`: Model Context Protocol Python SDK
- Core quantum-magnetic-navigation packages