# Production-Ready DotMac Framework - Unified Multi-Service Container
FROM python:3.12-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    curl \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

# Create app directory
WORKDIR /app

# Copy configuration and requirements
COPY pyproject.toml ./
COPY config/ ./config/

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -e .

# Development stage
FROM base as development
ENV ENVIRONMENT=development
COPY src/ ./src/
EXPOSE 8001 8002 8080
CMD ["python", "-m", "dotmac_isp.main"]

# Production stage
FROM base as production

# Copy source code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Create non-root user for security
RUN groupadd -r dotmacuser && useradd -r -g dotmacuser dotmacuser \
    && mkdir -p /app/logs /app/uploads /app/data \
    && chown -R dotmacuser:dotmacuser /app

# Switch to non-root user
USER dotmacuser

# Multi-service health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8001/health && curl -f http://localhost:8002/health || exit 1

# Expose all service ports
EXPOSE 8001 8002 8080 3000

# Default to ISP service, but allow override
ENV SERVICE_TYPE=isp
CMD ["sh", "-c", "python -m dotmac_${SERVICE_TYPE}.main"]
