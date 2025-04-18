# Quantum Magnetic Navigation

A navigation system that uses quantum magnetometers to provide precise positioning in GPS-denied environments.

# Introduction 
Imagine a navigation system that never needs satellites, radios, or signals of any kind. Instead, it carries a tiny quantum sensor that quietly “listens” to Earth’s own magnetic field. Every location on the planet has a unique magnetic fingerprint—subtle variations in strength and direction that arise from the rocks and minerals below our feet. By comparing what the sensor reads to a pre‑loaded map of those fingerprints, a robot or vehicle can pinpoint its position with GPS‑level accuracy.

Because it emits nothing, this approach is immune to jamming or spoofing. It works everywhere — indoors, underground, underwater, in dense cities or deep forests — where GPS and other systems fail. Drones can continue mapping pipelines under bridges, warehouse robots can navigate tunnels without beacons, and self‑driving cars can stay on course in concrete canyons. For military or search‑and‑rescue missions, the technology offers stealth and reliability when every second counts.

In short, quantum magnetic navigation transforms the Earth itself into a silent guide, giving any machine the confidence to find its way, no matter the terrain or the threats it faces.



## Practicality & Feasibility
Recent advances in quantum‐sensor miniaturization have produced compact, low‐power magnetometers—some weighing under 100 g and consuming just 1–2 W—that can be integrated into drones, vehicles, or wearable devices. 

These sensors, based on optically‐pumped atomic cells or microfabricated vapor chambers, now achieve femtotesla‐level sensitivity and maintain stability across temperature extremes. At the same time, high‐resolution global magnetic anomaly maps are freely available from geological surveys and can be refined with crowd‑sourced flight or vehicle data. 

Onboard processors (ARM Cortex‐class or FPGA accelerators) can run the necessary Kalman filters and interpolation routines at hundreds of hertz, meeting real‑time constraints.


## Applications
1. **GPS‑Free Positioning**  
   Robots and vehicles carry a tiny quantum sensor that listens to Earth’s magnetic field. By matching readings to a stored magnetic map, the robot always knows where it is—even when GPS is unavailable or jammed.  
2. **Indoor and Underground Robots**  
   In warehouses, mines or tunnels, the magnetic field penetrates walls and rock. Forklift‑style robots, inspection drones or autonomous mining vehicles navigate complex layouts without external trackers.  
3. **Aerial and Marine Drones**  
   Drones and unmanned boats gain a passive, jamming‑proof way to track their path when acoustic or radio signals fail.  
4. **Backup for Critical Transport**  
   Airliners and self‑driving cars get a silent, always‑on backup. If satellites are out of reach, the vehicle still knows its course over ocean or in urban canyons.  
5. **Stealth and Security Applications**  
   Military robots and reconnaissance drones navigate covertly. Because the system emits nothing, adversaries cannot detect or jam it.  
6. **Search‑and‑Rescue Response**  
   In disaster zones where infrastructure is down, magnetic navigation helps rescue robots find survivors and deliver supplies when GPS or radio beacons are unreliable.  
7. **Infrastructure Inspection**  
   Crawlers inside pipelines, bridges or power‑plant conduits use magnetic fingerprints to track location, enabling precise defect detection without manual control.

## Novel Uses
1. **Augmented‑Reality Alignment**  
   AR headsets match magnetic fingerprints to auto‑align digital overlays indoors.  
2. **Digital Twin Sync**  
   Construction sites sync physical progress to a digital model by tracking machinery magnetically instead of QR codes.  
3. **Wildlife Tracking Tags**  
   Animal collars record local magnetic data. Recovered maps reconstruct movement paths without satellites.  
4. **Subterranean Internet Gateways**  
   Mesh networks in tunnels use fixed magnetometers as reference points for seamless connectivity.  
5. **Pipeline Integrity Drones**  
   Robots inside pipelines use welded‑seam anomalies to self‑localize and spot corrosion without beacons.  
6. **Geothermal Prospecting**  
   Vehicles map subsurface heat‑flow regions by combining magnetic nav with temperature sensors.  
7. **Emergency Firefighter Locators**  
   Wearable magnetic beacons in smoke‑filled buildings let command track teams in real time without radio.  
8. **Swarm Robotics Coordination**  
   Drone swarms navigate using shared magnetic maps to maintain formation in GPS‑denied urban canyons.  
9. **Planetary Rover Deployment**  
   On Mars or the Moon, rovers use crustal magnetic anomalies for navigation when no satellite system exists.  
10. **Secure Asset Authentication**  
   Cargo containers embed magnetic signatures. Readers confirm location and authenticity, thwarting 
Field demonstrations by startups and research labs have already shown error bounds of tens of meters over hours of operation—comparable to unaugmented GPS under ideal conditions. With off‑the‑shelf quantum magnetometers, open magnetic datasets, and embedded compute modules, a working prototype can be assembled today. As manufacturing scales and algorithms improve, cost and size will continue to fall, making quantum magnetic navigation a practical option for a wide range of robotics and transport applications.



## Technical Details
- **Sensor:** Quantum magnetometer measures total magnetic field with ~80 fT/√Hz sensitivity.  
- **Map Engine:** Onboard interpolation of preloaded magnetic anomaly grids (global or regional).  
- **Filter:** Extended Kalman Filter fuses magnetic observations for real‑time 2D position updates.  
- **SWaP:** Module mass < 200 g, power consumption < 5 W, update rate up to 250 Hz.  
- **Accuracy:** Position error typically 10–50 m, bounded over time without drift.  

## Installation
 
### Local Development

```bash
# Install the package with development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linters
pre-commit run --all-files
```

### Docker Installation

The project is containerized for easy deployment and testing.

```bash
# Build the Docker image
make docker-build

# Run the API service
make docker-run

# Run tests in Docker
make docker-test

# Stop Docker containers
make docker-stop
```

## Docker & Containerization

### Docker Image

The project uses a multi-stage Docker build:
- **Builder stage**: Installs development dependencies, runs tests, and builds a wheel
- **Runtime stage**: Contains only the necessary runtime dependencies for a slim image

### Running with Docker Compose

```bash
# Start the API service
docker compose up -d api

# Run with load testing (Locust)
docker compose --profile loadtest up -d
```

### Configuration

The Docker container can be configured with the following environment variables:
- `LOG_LEVEL`: Logging level (default: info)
- `PORT`: Port to expose the API (default: 8000)
- `QMAG_NAV_MAP_PATH`: Path to the magnetic map file (GeoTIFF or NetCDF)

### Helper Script

A helper script is provided to simplify running the API:

```bash
./scripts/run-api.sh --port=8000 --data-dir=./mag_data --log-level=info
```

### Continuous Integration

The project uses GitHub Actions for CI/CD:
- Builds and pushes Docker images to GitHub Container Registry
- Tags images with commit SHA and "latest" on the main branch
- Scans images for vulnerabilities using Trivy

## MCP Server

The Model Context Protocol (MCP) server exposes the core functionality of the navigation system as tools that can be used by AI assistants and other MCP clients.

### Running the MCP Server

```bash
# Run using the provided script
python -m scripts.run_mcp_server --map path/to/magnetic_map.tif

# Or run directly
python -m qmag_nav.mcp.server
```

### Available MCP Tools

1. **query_magnetic_field**: Get magnetic field values at specific coordinates
   ```json
   {
     "latitude": 37.7749,
     "longitude": -122.4194,
     "interpolation_method": "bilinear"
   }
   ```

2. **estimate_position**: Use Extended Kalman Filter to estimate position
   ```json
   {
     "magnetic_field": 48250.5,
     "initial_latitude": 37.7749,
     "initial_longitude": -122.4194,
     "dt": 1.0,
     "reset": false
   }
   ```

3. **calibrate_sensor**: Calibration utilities for magnetometer sensors
   ```json
   {
     "samples": [[48250.5, 0.0, 0.0], [48251.2, 0.0, 0.0]],
     "method": "ellipsoid"
   }
   ```

4. **simulate_trajectory**: Generate simulated navigation data along a trajectory
   ```json
   {
     "start_latitude": 37.7749,
     "start_longitude": -122.4194,
     "end_latitude": 37.7750,
     "end_longitude": -122.4195,
     "speed": 1.0,
     "sample_rate": 10,
     "noise_level": 0.1,
     "path_type": "straight"
   }
   ```

### Example Client

An example client is provided in `examples/mcp_client_example.py`:

```bash
python examples/mcp_client_example.py --map path/to/magnetic_map.tif
```

## API Documentation

The system provides a RESTful API for integration with other applications.

### Base URL
By default, the API is available at `http://localhost:8000`

### Endpoints

#### Health Check
```
GET /healthz
```
Returns the health status of the API.

**Response**:
```json
{
  "status": "ok"
}
```

#### Position Estimation
```
POST /estimate
```
Updates the EKF with a new magnetic-based observation and returns the estimated position.

**Request Body**:
```json
{
  "lat": 37.7749,
  "lon": -122.4194
}
```

**Response**:
```json
{
  "lat": 37.77491,
  "lon": -122.41942,
  "quality": 1.0
}
```

### API Configuration

The API can be configured with the following environment variables:
- `LOG_LEVEL`: Logging level (default: info)
- `PORT`: Port to expose the API (default: 8000)
- `QMAG_NAV_MAP_PATH`: Path to the magnetic map file

## CLI Commands

The package provides a command-line interface for simulating trajectories and estimating positions.

### Basic Usage

```bash
# Run the CLI
python -m qmag_nav.cli [command] [options]
```

### Available Commands

#### Simulate Trajectory
Generates a simulated trajectory as JSON.

```bash
python -m qmag_nav.cli simulate --steps 10 --output trajectory.json
```

**Options**:
- `--steps`: Number of points to generate (default: 10)
- `--output`: Output file path (default: stdout)

#### Estimate Position
Fuses a single measurement and prints the updated EKF state.

```bash
python -m qmag_nav.cli estimate --lat 37.7749 --lon -122.4194 --reset
```

**Options**:
- `--lat`: Latitude of the measurement (required)
- `--lon`: Longitude of the measurement (required)
- `--reset`: Reset the EKF state to initial values

## License

Proprietary - All rights reserved.
