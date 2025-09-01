# DB Migration Job Dockerfile
# One-off service that runs migrations and exits (prevents multi-replica races)

FROM python:3.11-slim

WORKDIR /app

# Install only migration dependencies
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code (minimal for migrations)
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

# Create non-root user
RUN useradd -r -s /bin/false migrate-user
RUN chown -R migrate-user:migrate-user /app
USER migrate-user

# Set Python path
ENV PYTHONPATH=/app/src

# Migration script
COPY docker/migrate.sh /migrate.sh
USER root
RUN chmod +x /migrate.sh
USER migrate-user

# Health check (for migration completion)
HEALTHCHECK --interval=5s --timeout=3s --retries=1 \
    CMD [ -f /app/migration_complete ] || exit 1

ENTRYPOINT ["/migrate.sh"]