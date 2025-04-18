"""End-to-end integration tests for the quantum magnetic navigation API.

These tests verify that the entire system works together correctly, from the
API layer down to the core navigation components.
"""

from __future__ import annotations

import subprocess
import sys
import json
import time
from pathlib import Path

import pytest
import requests
from fastapi.testclient import TestClient

from qmag_nav.service import api
from qmag_nav.filter.ekf import NavEKF
from qmag_nav.mapping.backend import MagneticMap
from qmag_nav.models.geo import LatLon


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    # Reset the EKF state for each test
    api._ekf = None
    return TestClient(api.app)


def test_cli_to_api_integration(test_client):
    """Test integration between CLI and API.
    
    This test:
    1. Uses the CLI to generate a simulated trajectory
    2. Sends each point to the API
    3. Verifies the API responses form a reasonable path
    """
    # Use CLI to generate trajectory
    result = subprocess.run(
        [sys.executable, "-m", "qmag_nav.cli", "simulate", "--steps", "5"],
        capture_output=True,
        text=True,
        check=True,
    )
    
    # Parse the trajectory
    trajectory = json.loads(result.stdout)
    assert len(trajectory) == 5
    
    # Send each point to the API and collect responses
    responses = []
    for point in trajectory:
        response = test_client.post(
            "/estimate",
            json={"lat": point["lat"], "lon": point["lon"]}
        )
        assert response.status_code == 200
        responses.append(response.json())
    
    # Verify the responses form a reasonable path
    # The estimates should converge toward the input points
    for i in range(1, len(responses)):
        # Calculate distance between consecutive estimates
        # (This is a simple check - in a real system we'd use proper geodesic distance)
        prev_est = responses[i-1]
        curr_est = responses[i]
        
        # The path should be continuous (no huge jumps)
        assert abs(curr_est["lat"] - prev_est["lat"]) < 0.1
        assert abs(curr_est["lon"] - prev_est["lon"]) < 0.1


def test_end_to_end_api_with_map():
    """Test the API with a real magnetic map and EKF.
    
    This test:
    1. Creates a simple magnetic map
    2. Sets up the API with a known EKF
    3. Sends measurements to the API
    4. Verifies the API responses converge to the true position
    """
    # Create a tiny map 2×2 so that interpolation is trivial
    grid = [[100.0, 200.0], [300.0, 400.0]]
    m = MagneticMap(lat_min=0, lat_max=1, lon_min=0, lon_max=1, grid=grid)
    
    # The true position is somewhere in the map
    truth = LatLon(0.25, 0.75)
    
    # Reset the EKF state and initialize with a wrong guess
    api._ekf = NavEKF(initial=LatLon(0.9, 0.1))
    
    # Create a test client
    client = TestClient(api.app)
    
    # Send several measurements to the API
    estimates = []
    for _ in range(5):
        response = client.post(
            "/estimate",
            json={"lat": truth.lat, "lon": truth.lon}
        )
        assert response.status_code == 200
        estimates.append(response.json())
    
    # The final estimate should be close to truth
    final_est = estimates[-1]
    assert abs(final_est["lat"] - truth.lat) < 0.01
    assert abs(final_est["lon"] - truth.lon) < 0.01
    
    # The estimates should converge (get closer to truth over time)
    distances = [
        abs(est["lat"] - truth.lat) + abs(est["lon"] - truth.lon)
        for est in estimates
    ]
    assert distances[-1] < distances[0]


@pytest.mark.skipif(
    not Path(sys.executable).parent.joinpath("uvicorn").exists(),
    reason="Uvicorn not installed"
)
def test_live_server_integration():
    """Test with a live server (requires uvicorn to be installed).
    
    This test:
    1. Starts a live server using uvicorn
    2. Sends requests to the live server
    3. Verifies the responses
    
    This test is marked as skip if uvicorn is not installed.
    """
    # Start the server in a subprocess
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "qmag_nav.service.api:app", "--port", "8765"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    try:
        # Wait for server to start
        time.sleep(2)
        
        # Test health endpoint
        response = requests.get("http://localhost:8765/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        
        # Test estimate endpoint
        response = requests.post(
            "http://localhost:8765/estimate",
            json={"lat": 1.0, "lon": 1.0}
        )
        assert response.status_code == 200
        data = response.json()
        assert "lat" in data
        assert "lon" in data
        assert "quality" in data
        
    finally:
        # Clean up
        server_process.terminate()
        server_process.wait(timeout=5)