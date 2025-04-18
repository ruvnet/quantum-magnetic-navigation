# Multi-stage Dockerfile for Quantum Magnetic Navigation

# ===== BUILDER STAGE =====
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY tests/ ./tests/

# Install dependencies, run tests, and build wheel
RUN pip install --no-cache-dir ".[dev]" && \
    pytest && \
    pip wheel --no-deps --wheel-dir /wheels .

# ===== RUNTIME STAGE =====
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN useradd -m appuser && \
    chown -R appuser:appuser /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy wheel from builder stage
COPY --from=builder /wheels/*.whl /tmp/wheels/

# Install the application wheel and uvicorn
RUN pip install --no-cache-dir /tmp/wheels/*.whl uvicorn && \
    rm -rf /tmp/wheels

# Switch to non-root user
USER appuser

# Expose API port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run the API server
CMD ["uvicorn", "qmag_nav.service.api:app", "--host", "0.0.0.0", "--port", "8000"]