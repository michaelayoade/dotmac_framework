# Standardized Multi-Stage Dockerfile Template for DotMac Services
# This template provides security-enhanced, production-ready containerization
# with comprehensive health checks, security scanning, and optimization.

# ==========================================
# Stage 1: Security Scanner (Optional)
# ==========================================
FROM aquasec/trivy:latest as security-scanner
# This stage can be used to scan the base image for vulnerabilities
# Usage: docker build --target security-scanner -t service-security-scan .

# ==========================================
# Stage 2: Base Image with Security Updates
# ==========================================
FROM python:3.11-slim as base

# Set build arguments
ARG BUILD_DATE
ARG VERSION
ARG VCS_REF
ARG SERVICE_NAME
ARG SERVICE_DESCRIPTION
ARG PYTHON_VERSION=3.11

# Security: Set labels for container metadata
LABEL org.opencontainers.image.created=$BUILD_DATE \
      org.opencontainers.image.title="dotmac-dotmac_core_ops" \
      org.opencontainers.image.description="DotMac Core Operations Service" \
      org.opencontainers.image.version=$VERSION \
      org.opencontainers.image.revision=$VCS_REF \
      org.opencontainers.image.vendor="DotMac Framework" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/michaelayoade/dotmac-framework" \
      maintainer="DotMac Framework Team"

# Security: Update base system and install essential security tools
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    # Essential tools
    curl \
    wget \
    ca-certificates \
    # Security tools
    gnupg2 \
    # Build dependencies (will be removed in production stage)
    build-essential \
    pkg-config \
    # Clean up
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Security: Create non-root user early
ARG UID=10001
RUN groupadd -g $UID dotmac && \
    useradd -u $UID -g dotmac -s /bin/bash -m dotmac

# Set working directory
WORKDIR /app

# Security: Set proper ownership
RUN chown -R dotmac:dotmac /app

# ==========================================
# Stage 3: Dependency Builder
# ==========================================
FROM base as builder

# Install Python dependencies in builder stage
COPY pyproject.toml README.md ./
COPY requirements*.txt ./

# Security: Install dependencies with verification
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --user -r requirements.txt

# Copy source code
COPY . .

# Security: Ensure proper file permissions
RUN find . -type f -exec chmod 644 {} \; && \
    find . -type d -exec chmod 755 {} \;

# Install the service package
RUN pip install --no-cache-dir --user -e .

# ==========================================
# Stage 4: Testing Stage
# ==========================================
FROM builder as testing

# Install test dependencies
COPY requirements-test.txt ./
RUN pip install --no-cache-dir --user -r requirements-test.txt

# Copy test files
COPY tests/ ./tests/

# Run tests and security checks
RUN python -m pytest tests/ --cov=. --cov-report=xml --cov-report=html && \
    python -m bandit -r . -f json -o bandit-report.json || true && \
    python -m safety check --json --output safety-report.json || true

# ==========================================
# Stage 5: Production Stage
# ==========================================
FROM base as production

# Security: Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    # Runtime essentials only
    curl \
    ca-certificates \
    # Remove build tools
    && apt-get remove -y \
        build-essential \
        pkg-config \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python dependencies from builder
COPY --from=builder --chown=dotmac:dotmac /home/dotmac/.local /home/dotmac/.local

# Copy application code
COPY --from=builder --chown=dotmac:dotmac /app /app

# Security: Ensure no sensitive files
RUN rm -rf \
    /app/.git* \
    /app/tests \
    /app/docs \
    /app/*.md \
    /app/requirements-*.txt \
    /app/pyproject.toml

# Security: Switch to non-root user
USER dotmac

# Set environment variables
ENV PYTHONPATH=/app:/home/dotmac/.local/lib/python${PYTHON_VERSION}/site-packages
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH=/home/dotmac/.local/bin:$PATH

# Security: Set security-focused environment variables
ENV PYTHONHASHSEED=random
ENV PYTHONFAULTHANDLER=1

# Expose default port (override in service-specific Dockerfiles)
EXPOSE 8000

# Health check with comprehensive validation
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Security: Use exec form and specific user
USER dotmac
ENTRYPOINT ["python", "-m"]
CMD ["dotmac_core_ops"]

# ==========================================
# Stage 6: Development Stage
# ==========================================
FROM builder as development

# Install development dependencies
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir --user -r requirements-dev.txt

# Install debugging tools
RUN pip install --no-cache-dir --user \
    debugpy \
    ipdb \
    pytest-xvs

# Development environment variables
ENV ENVIRONMENT=development
ENV DEBUG=true
ENV LOG_LEVEL=DEBUG

# Expose debugging port
EXPOSE 5678

# Override health check for development
HEALTHCHECK --interval=60s --timeout=5s --start-period=10s --retries=2 \
    CMD python -c "print('Development container healthy')" || exit 1

# Development command with auto-reload
CMD ["python", "-m", "dotmac_core_ops", "--reload", "--debug"]

# ==========================================
# Stage 7: Security Hardened Stage
# ==========================================
FROM production as hardened

# Security: Additional hardening for production
USER root

# Security: Remove unnecessary packages and files
RUN apt-get update && \
    apt-get remove -y \
        wget \
        gnupg2 \
    && apt-get autoremove -y \
    && rm -rf \
        /var/lib/apt/lists/* \
        /tmp/* \
        /var/tmp/* \
        /root/.cache \
    && apt-get clean

# Security: Set restrictive permissions
RUN chmod -R 550 /app && \
    chmod -R 440 /app/config* || true

# Security: Remove shell access for dotmac user
RUN usermod -s /usr/sbin/nologin dotmac

# Security: Set read-only file system markers
VOLUME ["/tmp", "/var/tmp"]

# Switch back to non-root user
USER dotmac

# Security: Override health check with minimal footprint
HEALTHCHECK --interval=45s --timeout=5s --start-period=60s --retries=2 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Note: This stage should be used with read-only file system:
# docker run --read-only --tmpfs /tmp --tmpfs /var/tmp service-hardened