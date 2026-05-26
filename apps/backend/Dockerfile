# ── PitWall AI — FastAPI Backend ──────────────────────────────────────────────
# Multi-stage build for smaller final image

FROM python:3.10-slim AS base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# ── Dependencies stage ─────────────────────────────────────────────────────────
FROM base AS dependencies

# Copy requirements first (Docker caches this layer)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Final stage ────────────────────────────────────────────────────────────────
FROM dependencies AS final

# Copy entire project
COPY . .

# Create cache directory for FastF1
RUN mkdir -p /app/data/cache /app/data/ml/models

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start command
CMD ["uvicorn", "apps.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
