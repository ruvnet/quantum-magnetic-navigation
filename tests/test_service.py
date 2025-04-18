from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from qmag_nav.service import api
from qmag_nav.service.api import EstimateRequest


# Create a test client
client = TestClient(api.app)


def test_health_endpoint():
    """Test the direct function call."""
    assert api.healthz() == {"status": "ok"}


def test_estimate_updates_state():
    """Test the direct function call."""
    # First observation at (1,1) — estimate should move away from 0,0.
    resp1 = api.estimate(EstimateRequest(lat=1.0, lon=1.0))
    assert resp1["lat"] > 0 and resp1["lon"] > 0
    assert "quality" in resp1

    # Second observation at (2,2) — estimate should increase further.
    resp2 = api.estimate(EstimateRequest(lat=2.0, lon=2.0))
    assert resp2["lat"] > resp1["lat"]
    assert resp2["lon"] > resp1["lon"]
    assert "quality" in resp2


def test_health_endpoint_http():
    """Test the HTTP endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_estimate_endpoint_http():
    """Test the HTTP endpoint."""
    # Reset the EKF state for this test
    api._ekf = None
    
    # First request
    response1 = client.post(
        "/estimate",
        json={"lat": 1.0, "lon": 1.0}
    )
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["lat"] > 0 and data1["lon"] > 0
    assert "quality" in data1
    
    # Second request - should show movement
    response2 = client.post(
        "/estimate",
        json={"lat": 2.0, "lon": 2.0}
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["lat"] > data1["lat"]
    assert data2["lon"] > data1["lon"]
    assert "quality" in data2


def test_process_time_header():
    """Test that the process time header is added."""
    response = client.get("/healthz")
    assert "x-process-time" in response.headers
    assert float(response.headers["x-process-time"]) >= 0


def test_cors_headers():
    """Test that CORS headers are present."""
    response = client.options(
        "/estimate",
        headers={"Origin": "http://example.com", "Access-Control-Request-Method": "POST"}
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "*"


def test_invalid_request():
    """Test handling of invalid requests."""
    # Missing required fields
    response = client.post("/estimate", json={})
    assert response.status_code == 422  # Unprocessable Entity
    
    # Invalid data types
    response = client.post("/estimate", json={"lat": "invalid", "lon": 1.0})
    assert response.status_code == 422


def test_openapi_docs():
    """Test that OpenAPI docs are available."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Quantum Magnetic Navigation API"
    assert "/estimate" in schema["paths"]
    assert "/healthz" in schema["paths"]
