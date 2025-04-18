#!/bin/bash
# Quantum Magnetic Navigation Installation Script

set -e  # Exit on error

echo "=== Installing Quantum Magnetic Navigation ==="
echo ""

# Create and activate virtual environment (optional)
# python -m venv venv
# source venv/bin/activate

# Install required dependencies
echo "Installing dependencies..."
pip install fastapi uvicorn pydantic numpy scipy rasterio xarray netCDF4 mcp

# Install the package in development mode
echo "Installing quantum-magnetic-navigation in development mode..."
pip install -e .

# Create necessary directories
echo "Creating data directory..."
mkdir -p mag_data

echo ""
echo "=== Installation Complete ==="
echo ""
echo "To run the MCP server:"
echo "python -m scripts.run_mcp_server_fixed --map tests/data/5x5_grid.tif"
echo ""
echo "To run the API service:"
echo "python -m uvicorn src.qmag_nav.service.api:app --host 0.0.0.0 --port 8000"
echo ""
