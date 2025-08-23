#!/bin/bash
# Consolidated service startup script
# Handles all DotMac services with proper configuration

set -e

# Colors for logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
SERVICE_NAME=${SERVICE_NAME:-unknown}
PORT=${PORT:-8000}
WORKERS=${WORKERS:-}
ENVIRONMENT=${ENVIRONMENT:-production}
LOG_LEVEL=${LOG_LEVEL:-info}
RELOAD=${RELOAD:-false}

log_info "Starting DotMac service: $SERVICE_NAME"
log_info "Environment: $ENVIRONMENT"
log_info "Port: $PORT"
log_info "Log Level: $LOG_LEVEL"

# Calculate workers if not set
if [[ -z "$WORKERS" ]]; then
    WORKERS=$(python3 -c "
import os
import multiprocessing

# Get CPU count
cpu_count = multiprocessing.cpu_count()

# Calculate workers based on environment and CPU count
if os.getenv('ENVIRONMENT') == 'development':
    workers = 1
elif cpu_count <= 2:
    workers = 2
else:
    workers = min((cpu_count * 2) + 1, 16)

print(workers)
")
    log_info "Calculated workers: $WORKERS (based on CPU count)"
fi

# Early validation - check required environment variables
log_info "Validating configuration..."

required_vars=("DATABASE_URL" "REDIS_URL")
for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        log_error "Required environment variable $var is not set"
        exit 1
    fi
done

# Wait for dependencies
log_info "Waiting for dependencies..."

# Extract database host and port from DATABASE_URL
if [[ "$DATABASE_URL" =~ postgresql://[^@]*@([^:/]+)(:([0-9]+))?/ ]]; then
    DB_HOST="${BASH_REMATCH[1]}"
    DB_PORT="${BASH_REMATCH[3]:-5432}"
    
    log_info "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
    
    timeout=30
    while ! nc -z "$DB_HOST" "$DB_PORT"; do
        timeout=$((timeout - 1))
        if [[ $timeout -le 0 ]]; then
            log_error "PostgreSQL not available after 30 seconds"
            exit 1
        fi
        sleep 1
    done
    
    log_success "PostgreSQL is ready"
fi

# Extract Redis host and port from REDIS_URL
if [[ "$REDIS_URL" =~ redis://[^@]*@?([^:/]+)(:([0-9]+))?/ ]]; then
    REDIS_HOST="${BASH_REMATCH[1]}"
    REDIS_PORT="${BASH_REMATCH[3]:-6379}"
    
    log_info "Waiting for Redis at $REDIS_HOST:$REDIS_PORT..."
    
    timeout=30
    while ! nc -z "$REDIS_HOST" "$REDIS_PORT"; do
        timeout=$((timeout - 1))
        if [[ $timeout -le 0 ]]; then
            log_error "Redis not available after 30 seconds"
            exit 1
        fi
        sleep 1
    done
    
    log_success "Redis is ready"
fi

# Load secrets from OpenBao if available
if [[ -n "$OPENBAO_ADDR" ]] && [[ -n "$OPENBAO_TOKEN" ]]; then
    log_info "Loading secrets from OpenBao..."
    
    # Load service-specific secrets
    python3 - <<EOF
import os
import sys
sys.path.insert(0, '/app/backend')

try:
    from dotmac_sdk_core.openbao_client import OpenBaoClient
    client = OpenBaoClient()
    
    # Load database credentials
    db_creds = client.get_database_credentials()
    if db_creds:
        for key, value in db_creds.items():
            os.environ[key.upper()] = value
    
    # Load service secrets
    secrets = client.get_secret(f"services/{os.getenv('SERVICE_NAME')}")
    if secrets:
        for key, value in secrets.items():
            os.environ[key.upper()] = str(value)
            
    print("Secrets loaded successfully")
except Exception as e:
    print(f"Warning: Could not load secrets: {e}")
EOF
fi

# Set up telemetry
export OTEL_SERVICE_NAME="dotmac-$SERVICE_NAME"
export OTEL_RESOURCE_ATTRIBUTES="service.name=dotmac-$SERVICE_NAME,service.version=${SERVICE_VERSION:-1.0.0},deployment.environment=$ENVIRONMENT"

if [[ -n "$SIGNOZ_ENDPOINT" ]]; then
    export OTEL_EXPORTER_OTLP_ENDPOINT="$SIGNOZ_ENDPOINT"
    export OTEL_EXPORTER_OTLP_HEADERS="signoz-access-token=${SIGNOZ_TOKEN:-}"
    log_info "OpenTelemetry configured for SignOz"
fi

# Build uvicorn command
UVICORN_CMD="uvicorn"
UVICORN_ARGS=(
    "--host" "0.0.0.0"
    "--port" "$PORT"
    "--workers" "$WORKERS"
    "--log-level" "$LOG_LEVEL"
)

# Add development-specific options
if [[ "$ENVIRONMENT" == "development" ]] && [[ "$RELOAD" == "true" ]]; then
    UVICORN_ARGS+=("--reload")
    log_info "Hot reload enabled for development"
fi

# Add production optimizations
if [[ "$ENVIRONMENT" == "production" ]]; then
    UVICORN_ARGS+=(
        "--access-log"
        "--no-use-colors"
        "--loop" "uvloop"
        "--http" "httptools"
    )
fi

# Determine the app module based on service name
case "$SERVICE_NAME" in
    "identity")
        APP_MODULE="backend.dotmac_identity.main:app"
        ;;
    "billing")
        APP_MODULE="backend.dotmac_billing.main:app"
        ;;
    "services")
        APP_MODULE="backend.dotmac_services.main:app"
        ;;
    "networking")
        APP_MODULE="backend.dotmac_networking.main:app"
        ;;
    "analytics")
        APP_MODULE="backend.dotmac_analytics.main:app"
        ;;
    "api-gateway")
        APP_MODULE="backend.dotmac_api_gateway.main:app"
        ;;
    "core-events")
        APP_MODULE="backend.dotmac_core_events.api.rest:app"
        ;;
    "core-ops")
        APP_MODULE="backend.dotmac_core_ops.main:app"
        ;;
    "platform")
        APP_MODULE="backend.dotmac_platform.app:app"
        ;;
    *)
        log_error "Unknown service: $SERVICE_NAME"
        log_error "Available services: identity, billing, services, networking, analytics, api-gateway, core-events, core-ops, platform"
        exit 1
        ;;
esac

# Final command
UVICORN_ARGS+=("$APP_MODULE")

log_info "Starting $SERVICE_NAME service..."
log_info "Command: $UVICORN_CMD ${UVICORN_ARGS[*]}"

# Start the service with proper signal handling
exec "$UVICORN_CMD" "${UVICORN_ARGS[@]}"