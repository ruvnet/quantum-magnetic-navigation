"""Command-line interface for quantum magnetic navigation.

This module provides a CLI for simulating trajectories and estimating positions
using the quantum magnetic navigation system.
"""

from __future__ import annotations

import argparse
import json
import sys
from random import uniform
from typing import List, Dict, Any, Optional

from qmag_nav.models.geo import LatLon
from qmag_nav.filter.ekf import NavEKF


def _simulate_positions(steps: int) -> list[dict[str, float]]:
    """Generate *steps* random positions around a reference point."""

    ref = LatLon(lat=0.0, lon=0.0)
    results: list[dict[str, float]] = []
    for _ in range(steps):
        # create tiny random offsets within ±0.001° (~100 m)
        pos = LatLon(lat=ref.lat + uniform(-0.001, 0.001), lon=ref.lon + uniform(-0.001, 0.001))
        results.append({"lat": pos.lat, "lon": pos.lon})
    return results


def main(argv: list[str] | None = None) -> None:  # noqa: D401
    """Execute the CLI command with the given arguments."""
    parser = argparse.ArgumentParser(
        prog="qmag-nav", description="Quantum Magnetic Navigation demo CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Simulate command
    sim_parser = subparsers.add_parser(
        "simulate", help="generate dummy trajectory as JSON"
    )
    sim_parser.add_argument("--steps", type=int, default=10, 
                           help="number of points to emit (default: 10)")
    sim_parser.add_argument("--output", type=str, default="-",
                           help="output file path (default: stdout)")

    # Estimate command
    est_parser = subparsers.add_parser(
        "estimate", help="fuse a single measurement and print updated EKF state"
    )
    est_parser.add_argument("--lat", type=float, required=True,
                           help="latitude of the measurement")
    est_parser.add_argument("--lon", type=float, required=True,
                           help="longitude of the measurement")
    est_parser.add_argument("--reset", action="store_true",
                           help="reset the EKF state to initial values")

    args = parser.parse_args(argv)

    if args.command == "simulate":
        data = _simulate_positions(args.steps)
        
        if args.output == "-":
            json.dump(data, fp=sys.stdout)  # type: ignore[arg-type] – monkeypatch for tests
        else:
            with open(args.output, "w") as f:
                json.dump(data, fp=f, indent=2)

    if args.command == "estimate":
        # Singleton EKF stored on the function attribute (persist across calls
        # in long‑running shell sessions / tests)
        if not hasattr(main, "_ekf") or args.reset:
            setattr(main, "_ekf", NavEKF(initial=LatLon(lat=0.0, lon=0.0)))
        ekf: NavEKF = getattr(main, "_ekf")  # type: ignore[assignment]

        # Create a simple magnetic field function that returns lat + lon
        # This is just a placeholder for demonstration purposes
        def mag_func(lat, lon):
            return lat + lon
            
        ekf.predict(dt=1.0)  # Use a default time step of 1 second
        
        # Use the measurement lat/lon to calculate a magnetic field value
        mag_value = args.lat + args.lon
        ekf.update(mag_value, mag_func)
        est = ekf.estimate()
        
        result = {
            "lat": est.lat, 
            "lon": est.lon,
            "measurement": {"lat": args.lat, "lon": args.lon}
        }
        
        json.dump(result, fp=sys.stdout, indent=2)  # type: ignore[arg-type]


if __name__ == "__main__":  # pragma: no cover – manual testing
    main(sys.argv[1:])
