FROM python:3.11-alpine

WORKDIR /app

# Install system dependencies
RUN apk add --no-cache curl gcc musl-dev libffi-dev

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN addgroup -g 1001 -S testuser && adduser -S testuser -u 1001
RUN chown -R testuser:testuser /app
USER testuser

# Health check endpoint
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

EXPOSE 8080

CMD ["python", "file_storage_tester.py"]