"""HTTP service exposing the quantum magnetic navigation capabilities.

The implementation uses the *FastAPI* fallback defined in :pymod:`qmag_nav._compat`
if the real dependency is not installed. This service provides endpoints for
health checks and position estimation.
"""

from __future__ import annotations

import time
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from qmag_nav._compat import BaseModel
from qmag_nav.filter.ekf import NavEKF
from qmag_nav.models.geo import LatLon


class EstimateRequest(BaseModel):
    """Request model for position estimation."""
    lat: float
    lon: float


class EstimateResponse(BaseModel):
    """Response model for position estimation."""
    lat: float
    lon: float
    quality: float = 1.0  # Default quality indicator


app = FastAPI(
    title="Quantum Magnetic Navigation API",
    description="API for quantum magnetic navigation position estimation",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)


# Singleton EKF instance (reset on interpreter restart)
_ekf: NavEKF | None = None


def _get_filter() -> NavEKF:  # noqa: D401
    """Get or initialize the navigation filter."""
    global _ekf  # noqa: PLW0603
    if _ekf is None:
        _ekf = NavEKF(initial=LatLon(0.0, 0.0))
    return _ekf


@app.middleware("http")
async def add_process_time_header(request: Request, call_next) -> Response:
    """Add processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.get("/healthz", tags=["System"])
def healthz() -> Dict[str, str]:  # noqa: D401
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/estimate", response_model=EstimateResponse, tags=["Navigation"])
def estimate(payload: EstimateRequest) -> Dict[str, float]:  # noqa: D401
    """Update EKF with a new magnetic-based observation and return state.
    
    Args:
        payload: The request payload containing latitude and longitude
        
    Returns:
        A dictionary with the estimated position and quality indicator
    """
    lat = float(payload.lat)
    lon = float(payload.lon)
    
    ekf = _get_filter()
    ekf.predict()
    ekf.update(LatLon(lat, lon))
    est = ekf.estimate()
    
    # Calculate a simple quality metric (could be enhanced with actual uncertainty)
    quality = 1.0
    
    return {"lat": est.lat, "lon": est.lon, "quality": quality}


# Customize OpenAPI schema
def custom_openapi():
    """Generate custom OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Quantum Magnetic Navigation API",
        version="1.0.0",
        description="API for quantum magnetic navigation position estimation",
        routes=app.routes,
    )
    
    # Add additional metadata
    openapi_schema["info"]["x-logo"] = {
        "url": "https://example.com/logo.png"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
