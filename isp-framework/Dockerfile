# DotMac ISP Framework Dockerfile

# Base stage with common dependencies
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VENV_IN_PROJECT=1
ENV POETRY_CACHE_DIR=/opt/poetry-cache

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Set work directory
WORKDIR /app

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Development stage
FROM base AS development

# Configure poetry and install all dependencies including dev
RUN poetry config virtualenvs.create false
RUN poetry install --no-root && rm -rf $POETRY_CACHE_DIR

# Copy application code
COPY src/ ./src/
COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY README.md ./

# Install the application
RUN poetry install --only-root

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application with auto-reload for development
CMD ["uvicorn", "dotmac_isp.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base AS production

# Configure poetry and install only main dependencies
RUN poetry config virtualenvs.create false
RUN poetry install --only=main --no-root && rm -rf $POETRY_CACHE_DIR

# Copy application code
COPY src/ ./src/
COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY README.md ./

# Install the application
RUN poetry install --only-root

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "dotmac_isp.main:app", "--host", "0.0.0.0", "--port", "8000"]