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
COPY sso_integration_tester.py .
COPY package.json .

# Create non-root user
RUN addgroup --gid 1001 --system ssotester && \
    adduser --no-create-home --shell /bin/false --disabled-password --uid 1001 --system --group ssotester

# Create results directory
RUN mkdir -p /app/results && chown -R ssotester:ssotester /app

USER ssotester

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

# Default command
CMD ["python", "sso_integration_tester.py"]