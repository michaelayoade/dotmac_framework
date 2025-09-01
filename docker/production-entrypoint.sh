#!/bin/bash

# Production entrypoint script for DotMac Framework
# Starts the appropriate service based on SERVICE_TYPE environment variable

set -e

SERVICE_TYPE=${SERVICE_TYPE:-"isp"}
export PYTHONPATH="/app/src:$PYTHONPATH"

echo "🚀 Starting DotMac Framework - Service Type: $SERVICE_TYPE"

# Service-specific configuration
case "$SERVICE_TYPE" in
    "isp")
        echo "📡 Initializing ISP Service"
        export PORT=8000
        export SERVICE_NAME="dotmac-isp"
        export UVICORN_APP="dotmac_isp.main:app"
        ;;
    "management")
        echo "🏢 Initializing Management Service"
        export PORT=8001
        export SERVICE_NAME="dotmac-management"
        export UVICORN_APP="dotmac_management.main:app"
        ;;
    "migration")
        echo "🔄 Initializing Database Migration Job"
        export SERVICE_NAME="dotmac-migration"
        # Migration job uses different entrypoint
        exec /migrate.sh
        ;;
    *)
        echo "❌ Error: Unknown SERVICE_TYPE '$SERVICE_TYPE'"
        echo "Valid options: isp, management, migration"
        exit 1
        ;;
esac

# Wait for database (if DATABASE_URL is provided)
if [ ! -z "$DATABASE_URL" ]; then
    echo "⏳ Waiting for database connection..."
    python3 -c "
import sys
import time
import psycopg2
from urllib.parse import urlparse

url = '$DATABASE_URL'
result = urlparse(url)
max_retries = 30
retry_count = 0

while retry_count < max_retries:
    try:
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        conn.close()
        print('✅ Database connection successful')
        break
    except Exception as e:
        retry_count += 1
        print(f'⏳ Database not ready (attempt {retry_count}/{max_retries}): {e}')
        if retry_count >= max_retries:
            print('❌ Database connection failed after maximum retries')
            sys.exit(1)
        time.sleep(2)
"
fi

# Wait for Redis (if REDIS_URL is provided)
if [ ! -z "$REDIS_URL" ]; then
    echo "⏳ Waiting for Redis connection..."
    python3 -c "
import sys
import time
import redis
from urllib.parse import urlparse

url = '$REDIS_URL'
result = urlparse(url)
max_retries = 30
retry_count = 0

while retry_count < max_retries:
    try:
        r = redis.Redis(
            host=result.hostname,
            port=result.port or 6379,
            password=result.password,
            socket_timeout=5
        )
        r.ping()
        print('✅ Redis connection successful')
        break
    except Exception as e:
        retry_count += 1
        print(f'⏳ Redis not ready (attempt {retry_count}/{max_retries}): {e}')
        if retry_count >= max_retries:
            print('❌ Redis connection failed after maximum retries')
            sys.exit(1)
        time.sleep(2)
"
fi

# NOTE: Database migrations are now handled by dedicated db-migrate service
# This prevents multi-replica race conditions and improves security
echo "ℹ️ Database migrations handled by dedicated migration job"

# Create logs directory
mkdir -p /app/logs

echo "✅ $SERVICE_NAME initialization complete"
echo "🌐 Starting server on port $PORT"

# Start the service with Uvicorn
exec uvicorn $UVICORN_APP \
    --host 0.0.0.0 \
    --port $PORT \
    --workers 1 \
    --log-level info \
    --access-log \
    --loop uvloop \
    --http httptools