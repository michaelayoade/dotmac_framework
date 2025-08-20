#!/bin/bash
# Secure service startup script with proper signal handling and error management

set -euo pipefail  # Exit on error, undefined vars, pipe failures
IFS=$'\n\t'       # Set secure Internal Field Separator

# Trap signals for graceful shutdown
trap 'handle_signal TERM' TERM
trap 'handle_signal INT' INT
trap 'handle_signal HUP' HUP

# PID tracking for graceful shutdown
PID=""

handle_signal() {
    local signal=$1
    echo "[$(date -Iseconds)] Received $signal signal, shutting down gracefully..."
    
    if [ -n "$PID" ]; then
        kill -TERM "$PID" 2>/dev/null || true
        wait "$PID" 2>/dev/null || true
    fi
    
    exit 0
}

# Load secrets from files if they exist
load_secret() {
    local env_var=$1
    local secret_file=$2
    
    if [ -f "$secret_file" ]; then
        export "$env_var"="$(cat "$secret_file")"
        echo "[$(date -Iseconds)] Loaded secret from $secret_file"
    fi
}

# Load all secrets
load_secret "DATABASE_PASSWORD" "/run/secrets/db_password"
load_secret "REDIS_PASSWORD" "/run/secrets/redis_password"
load_secret "SECRET_KEY" "/run/secrets/jwt_secret"
load_secret "OPENBAO_TOKEN" "/run/secrets/openbao_token"

# Build database URL with loaded password
if [ -n "${DATABASE_PASSWORD:-}" ]; then
    export DATABASE_URL="postgresql://${POSTGRES_USER:-dotmac}:${DATABASE_PASSWORD}@${DB_HOST:-postgres}:5432/${POSTGRES_DB:-dotmac_db}"
fi

# Build Redis URL with loaded password
if [ -n "${REDIS_PASSWORD:-}" ]; then
    export REDIS_URL="redis://:${REDIS_PASSWORD}@${REDIS_HOST:-redis}:6379/${REDIS_DB:-0}"
fi

# Validate required environment variables
validate_env() {
    local required_vars=("SERVICE_NAME" "DATABASE_URL" "REDIS_URL" "SECRET_KEY")
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            echo "[$(date -Iseconds)] ERROR: Required environment variable $var is not set"
            exit 1
        fi
    done
}

# Wait for dependencies with exponential backoff
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local max_attempts=30
    local attempt=1
    local wait_time=2
    
    echo "[$(date -Iseconds)] Waiting for $service_name at $host:$port..."
    
    while [ $attempt -le $max_attempts ]; do
        if nc -z "$host" "$port" 2>/dev/null; then
            echo "[$(date -Iseconds)] $service_name is available"
            return 0
        fi
        
        echo "[$(date -Iseconds)] Attempt $attempt/$max_attempts: $service_name not ready, waiting ${wait_time}s..."
        sleep "$wait_time"
        
        # Exponential backoff with cap
        wait_time=$((wait_time * 2))
        if [ $wait_time -gt 30 ]; then
            wait_time=30
        fi
        
        attempt=$((attempt + 1))
    done
    
    echo "[$(date -Iseconds)] ERROR: $service_name failed to become available"
    return 1
}

# Main startup logic
main() {
    echo "[$(date -Iseconds)] Starting DotMac service: ${SERVICE_NAME:-unknown}"
    
    # Validate environment
    validate_env
    
    # Wait for dependencies
    wait_for_service "${DB_HOST:-postgres}" "${DB_PORT:-5432}" "PostgreSQL"
    wait_for_service "${REDIS_HOST:-redis}" "${REDIS_PORT:-6379}" "Redis"
    
    # Run database migrations if needed
    if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
        echo "[$(date -Iseconds)] Running database migrations..."
        alembic upgrade head || {
            echo "[$(date -Iseconds)] ERROR: Migration failed"
            exit 1
        }
    fi
    
    # Determine service module
    SERVICE_MODULE="backend.dotmac_${SERVICE_NAME}.main:app"
    
    # Start the service
    echo "[$(date -Iseconds)] Starting Uvicorn for $SERVICE_MODULE"
    
    # Use exec to replace shell with uvicorn process for proper signal handling
    if [ "${ENVIRONMENT:-development}" = "production" ]; then
        exec uvicorn "$SERVICE_MODULE" \
            --host 0.0.0.0 \
            --port "${PORT:-8000}" \
            --workers "${WORKERS:-1}" \
            --loop uvloop \
            --no-access-log \
            --no-server-header \
            --limit-concurrency 1000 \
            --timeout-keep-alive 5 \
            --ssl-keyfile "${SSL_KEY:-}" \
            --ssl-certfile "${SSL_CERT:-}"
    else
        # Development mode with auto-reload
        exec uvicorn "$SERVICE_MODULE" \
            --host 0.0.0.0 \
            --port "${PORT:-8000}" \
            --reload \
            --reload-dir "backend/dotmac_${SERVICE_NAME}" \
            --log-level debug
    fi
}

# Run main function
main "$@" &
PID=$!

# Wait for the background process
wait "$PID"