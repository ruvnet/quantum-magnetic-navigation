from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from io import StringIO
from pathlib import Path

import pytest

from qmag_nav import cli


def test_simulate_default_steps(monkeypatch):
    # Capture stdout
    buffer = StringIO()
    monkeypatch.setattr(sys, "stdout", buffer)

    cli.main(["simulate"])

    data = json.loads(buffer.getvalue())
    # Default steps=10
    assert isinstance(data, list) and len(data) == 10
    for item in data:
        assert {"lat", "lon"}.issubset(item.keys())


def test_estimate_updates(monkeypatch):
    # First call with lat=1, lon=1 – estimate should move towards 1,1 from 0,0
    from qmag_nav import cli  # local import to reset singleton between test runs

    buffer = StringIO()
    monkeypatch.setattr(sys, "stdout", buffer)
    cli.main(["estimate", "--lat", "1", "--lon", "1"])
    first_est = json.loads(buffer.getvalue())
    assert first_est["lat"] > 0 and first_est["lon"] > 0
    assert "measurement" in first_est
    assert first_est["measurement"]["lat"] == 1
    assert first_est["measurement"]["lon"] == 1

    # Second call with lat=2,lon=2 – estimate should increase further
    buffer = StringIO()
    monkeypatch.setattr(sys, "stdout", buffer)
    cli.main(["estimate", "--lat", "2", "--lon", "2"])
    second_est = json.loads(buffer.getvalue())
    assert second_est["lat"] > first_est["lat"]
    assert second_est["lon"] > first_est["lon"]
    assert second_est["measurement"]["lat"] == 2
    assert second_est["measurement"]["lon"] == 2


@pytest.mark.parametrize("steps", [1, 5, 13])
def test_simulate_steps_option(monkeypatch, steps):
    buffer = StringIO()
    monkeypatch.setattr(sys, "stdout", buffer)
    cli.main(["simulate", "--steps", str(steps)])
    data = json.loads(buffer.getvalue())
    assert len(data) == steps


def test_simulate_output_to_file():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        try:
            # Run the command with output to file
            cli.main(["simulate", "--steps", "5", "--output", tmp.name])
            
            # Check the file was created and contains valid data
            with open(tmp.name, "r") as f:
                data = json.load(f)
                assert isinstance(data, list) and len(data) == 5
                for item in data:
                    assert {"lat", "lon"}.issubset(item.keys())
        finally:
            # Clean up
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)


def test_estimate_reset_option(monkeypatch):
    # First call to establish a baseline
    buffer = StringIO()
    monkeypatch.setattr(sys, "stdout", buffer)
    cli.main(["estimate", "--lat", "1", "--lon", "1"])
    first_est = json.loads(buffer.getvalue())
    
    # Second call with reset flag should start fresh
    buffer = StringIO()
    monkeypatch.setattr(sys, "stdout", buffer)
    cli.main(["estimate", "--lat", "1", "--lon", "1", "--reset"])
    reset_est = json.loads(buffer.getvalue())
    
    # The reset estimate should be closer to 0,0 than the first estimate
    # because it's starting from scratch
    assert reset_est["lat"] < first_est["lat"]
    assert reset_est["lon"] < first_est["lon"]


@pytest.mark.integration
def test_cli_subprocess():
    """Test the CLI using subprocess to ensure it works as an actual command."""
    # This test requires the package to be installed
    # Skip if running in a test environment without installation
    if not Path(sys.executable).parent.joinpath("qmag-nav").exists():
        pytest.skip("CLI command not available in PATH")
    
    # Run the simulate command
    result = subprocess.run(
        [sys.executable, "-m", "qmag_nav.cli", "simulate", "--steps", "3"],
        capture_output=True,
        text=True,
        check=True,
    )
    
    # Check the output
    data = json.loads(result.stdout)
    assert isinstance(data, list) and len(data) == 3
    for item in data:
        assert {"lat", "lon"}.issubset(item.keys())
