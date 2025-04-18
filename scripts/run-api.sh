#!/bin/bash
# Helper script to run the Quantum Magnetic Navigation API

set -e

# Default values
PORT=8000
DATA_DIR="./mag_data"
LOG_LEVEL="info"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --port=*)
      PORT="${1#*=}"
      shift
      ;;
    --data-dir=*)
      DATA_DIR="${1#*=}"
      shift
      ;;
    --log-level=*)
      LOG_LEVEL="${1#*=}"
      shift
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --port=PORT        Port to run the API on (default: 8000)"
      echo "  --data-dir=PATH    Path to magnetic data directory (default: ./mag_data)"
      echo "  --log-level=LEVEL  Log level (default: info)"
      echo "  --help             Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Ensure data directory exists
mkdir -p "$DATA_DIR"

# Run the API using Docker Compose
echo "Starting Quantum Magnetic Navigation API on port $PORT..."
echo "Using data directory: $DATA_DIR"
echo "Log level: $LOG_LEVEL"

docker compose up -d \
  --build \
  -e PORT="$PORT" \
  -e LOG_LEVEL="$LOG_LEVEL" \
  -v "$DATA_DIR:/app/mag_data" \
  api

echo "API is running at http://localhost:$PORT"
echo "Health check: http://localhost:$PORT/healthz"
echo "To stop the API: docker compose down"