FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy test files
COPY i18n_integration_tester.py .
COPY package.json .

# Create non-root user
RUN addgroup --gid 1001 --system i18ntester && \
    adduser --no-create-home --shell /bin/false --disabled-password --uid 1001 --system --group i18ntester

# Create results directory
RUN mkdir -p /app/results && chown -R i18ntester:i18ntester /app

USER i18ntester

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

# Default command
CMD ["python", "i18n_integration_tester.py"]