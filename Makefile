# Quantum Magnetic Navigation Makefile

.PHONY: help install test lint format docker-build docker-run docker-test docker-stop

# Default target
help:
	@echo "Quantum Magnetic Navigation"
	@echo ""
	@echo "Usage:"
	@echo "  make install        Install the package and dependencies"
	@echo "  make test           Run tests"
	@echo "  make lint           Run linters"
	@echo "  make format         Format code"
	@echo "  make docker-build   Build Docker image"
	@echo "  make docker-run     Run API in Docker container"
	@echo "  make docker-test    Run tests in Docker container"
	@echo "  make docker-stop    Stop Docker containers"
	@echo "  make docker-clean   Remove Docker containers and images"

# Development targets
install:
	pip install -e ".[dev]"

test:
	pytest

lint:
	pre-commit run --all-files

format:
	black src tests

# Docker targets
docker-build:
	docker compose build

docker-run:
	docker compose up -d api
	@echo "API is running at http://localhost:8000"
	@echo "Health check: http://localhost:8000/healthz"

docker-test:
	docker compose run --rm api pytest

docker-stop:
	docker compose down

docker-clean: docker-stop
	docker compose rm -f
	docker rmi qmag-nav:latest || true

# Load testing
docker-loadtest:
	docker compose --profile loadtest up -d
	@echo "Locust UI is available at http://localhost:8089"

# Shorthand for common operations
all: install lint test

# Create data directory if it doesn't exist
mag_data:
	mkdir -p mag_data