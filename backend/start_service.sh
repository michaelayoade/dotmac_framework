#!/bin/bash
# Consolidated production service startup script with comprehensive features
# Handles all DotMac microservices with proper signal handling, health checks, and observability

set -euo pipefail
IFS=$'\n\t'

# ======================
# Configuration
# ======================

# Service identification
SERVICE_NAME="${SERVICE_NAME:-unknown}"
SERVICE_VERSION="${SERVICE_VERSION:-1.0.0}"
APP_MODULE="${APP_MODULE:-backend.${SERVICE_NAME}.main:app}"
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

# Environment
ENVIRONMENT="${ENVIRONMENT:-development}"
LOG_LEVEL="${LOG_LEVEL:-info}"

# Workers configuration (CPU-aware)
calculate_workers() {
    python3 -c "
import os, math
cpu_count = os.cpu_count() or 2
if '$ENVIRONMENT' == 'production':
    # Production: 2-4 workers per CPU
    workers = max(2, min(cpu_count * 2, 16))
else:
    # Development: fewer workers
    workers = max(2, min(cpu_count, 4))
print(workers)
"
}
WORKERS="${WORKERS:-$(calculate_workers)}"

# Timeouts
GRACEFUL_TIMEOUT="${GRACEFUL_TIMEOUT:-30}"
KEEPALIVE="${KEEPALIVE:-5}"
STARTUP_TIMEOUT="${STARTUP_TIMEOUT:-60}"
SHUTDOWN_TIMEOUT="${SHUTDOWN_TIMEOUT:-30}"

# Observability
SIGNOZ_ENDPOINT="${SIGNOZ_ENDPOINT:-${OTEL_EXPORTER_OTLP_ENDPOINT:-}}"
ACCESS_LOG="${ACCESS_LOG:-false}"
STATSD_HOST="${STATSD_HOST:-}"

# ======================
# Functions
# ======================

log() {
    local level=$1
    shift
    echo "[$(date -Iseconds)] [$level] [${SERVICE_NAME}] $*" >&2
}

log_info() { log "INFO" "$@"; }
log_warn() { log "WARN" "$@"; }
log_error() { log "ERROR" "$@"; }
log_debug() { [ "$LOG_LEVEL" = "debug" ] && log "DEBUG" "$@" || true; }

# Load secrets from OpenBao
load_secrets() {
    if [ "${OPENBAO_ENABLED:-true}" = "true" ]; then
        log_info "Loading secrets from OpenBao..."
        
        python3 -c "
import sys, os
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/backend')

os.environ.setdefault('SERVICE_NAME', '${SERVICE_NAME}')

try:
    from dotmac_sdk_core.openbao_client import get_openbao_client
    
    # Get OpenBao client
    client = get_openbao_client('${SERVICE_NAME}')
    
    # Load service configuration
    config = client.get_service_config()
    
    # Export as environment variables
    for key, value in config.items():
        env_key = key.upper().replace('-', '_')
        print(f'export {env_key}=\"{value}\"')
    
    print('# ✓ Secrets loaded from OpenBao', file=sys.stderr)
    sys.exit(0)
    
except Exception as e:
    print(f'# ⚠ Failed to load from OpenBao: {e}', file=sys.stderr)
    print('# Using environment variables as fallback', file=sys.stderr)
    sys.exit(0)  # Non-fatal, fall back to env vars
" > /tmp/openbao_exports.sh
        
        if [ -f /tmp/openbao_exports.sh ]; then
            source /tmp/openbao_exports.sh
            rm -f /tmp/openbao_exports.sh
            log_info "Secrets loaded from OpenBao"
        else
            log_warn "OpenBao unavailable, using environment variables"
        fi
    else
        log_info "OpenBao disabled, using environment variables"
    fi
}

# Early configuration validation
validate_config() {
    log_info "Validating configuration..."
    
    python3 -c "
import sys, os
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/backend')

# Set minimal env for validation
os.environ.setdefault('SERVICE_NAME', '${SERVICE_NAME}')

try:
    # Try OpenBao-enhanced config first
    try:
        from dotmac_sdk_core.config_openbao import get_service_config
        config = get_service_config('${SERVICE_NAME}')
    except ImportError:
        # Fall back to standard config
        if '${SERVICE_NAME}' != 'unknown':
            module_name = f'backend.dotmac_{SERVICE_NAME}.core.config'
            config_module = __import__(module_name, fromlist=['config'])
            config = config_module.config
        else:
            print('⚠ Service name unknown', file=sys.stderr)
            sys.exit(0)
    
    # Validate required fields
    assert config.database_url, 'DATABASE_URL is required'
    assert config.redis_url, 'REDIS_URL is required'
    assert config.secret_key, 'SECRET_KEY is required'
    
    print(f'✓ Configuration valid for ${SERVICE_NAME}')
    sys.exit(0)
    
except ImportError as e:
    print(f'⚠ Config module not found: {e}', file=sys.stderr)
    sys.exit(0)  # Non-fatal for services without config module
except AssertionError as e:
    print(f'✗ Configuration error: {e}', file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f'✗ Validation failed: {e}', file=sys.stderr)
    sys.exit(1)
" || {
        log_error "Configuration validation failed!"
        exit 1
    }
    
    log_info "Configuration validated successfully"
}

# Wait for dependencies
wait_for_dependencies() {
    log_info "Checking dependencies..."
    
    # Wait for database
    if [ -n "${DATABASE_URL:-}" ]; then
        log_info "Waiting for database..."
        python3 -c "
import time, psycopg2, os
from urllib.parse import urlparse

url = urlparse(os.environ.get('DATABASE_URL', ''))
if url.hostname:
    for i in range(30):
        try:
            conn = psycopg2.connect(
                host=url.hostname,
                port=url.port or 5432,
                user=url.username,
                password=url.password,
                database=url.path[1:] if url.path else 'postgres',
                connect_timeout=5
            )
            conn.close()
            print('✓ Database is ready')
            break
        except:
            time.sleep(2)
    else:
        print('✗ Database connection timeout')
        exit(1)
"
    fi
    
    # Wait for Redis
    if [ -n "${REDIS_URL:-}" ]; then
        log_info "Waiting for Redis..."
        python3 -c "
import time, redis, os

r = redis.from_url(os.environ.get('REDIS_URL', ''))
for i in range(30):
    try:
        r.ping()
        print('✓ Redis is ready')
        break
    except:
        time.sleep(2)
else:
    print('✗ Redis connection timeout')
    exit(1)
"
    fi
    
    log_info "All dependencies ready"
}

# Setup OpenTelemetry instrumentation
setup_observability() {
    if [ -n "$SIGNOZ_ENDPOINT" ]; then
        log_info "Setting up SignOz/OpenTelemetry instrumentation..."
        
        # Export OTEL environment variables
        export OTEL_SERVICE_NAME="dotmac-${SERVICE_NAME}"
        export OTEL_SERVICE_VERSION="${SERVICE_VERSION}"
        export OTEL_EXPORTER_OTLP_ENDPOINT="${SIGNOZ_ENDPOINT}"
        export OTEL_EXPORTER_OTLP_PROTOCOL="${OTEL_EXPORTER_OTLP_PROTOCOL:-grpc}"
        export OTEL_TRACES_EXPORTER="${OTEL_TRACES_EXPORTER:-otlp}"
        export OTEL_METRICS_EXPORTER="${OTEL_METRICS_EXPORTER:-otlp}"
        export OTEL_LOGS_EXPORTER="${OTEL_LOGS_EXPORTER:-otlp}"
        export OTEL_RESOURCE_ATTRIBUTES="service.name=${OTEL_SERVICE_NAME},service.version=${SERVICE_VERSION},deployment.environment=${ENVIRONMENT},service.namespace=dotmac"
        export OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true
        
        # Auto-instrument the application
        INSTRUMENT_CMD="opentelemetry-instrument"
        
        log_info "OpenTelemetry configured for ${SIGNOZ_ENDPOINT}"
    else
        INSTRUMENT_CMD=""
        log_info "OpenTelemetry disabled (SIGNOZ_ENDPOINT not set)"
    fi
}

# Run database migrations
run_migrations() {
    if [ "${RUN_MIGRATIONS:-false}" = "true" ] && [ -n "${DATABASE_URL:-}" ]; then
        log_info "Running database migrations..."
        
        cd /app/backend/dotmac_${SERVICE_NAME} 2>/dev/null || cd /app
        
        if [ -f "alembic.ini" ]; then
            alembic upgrade head || {
                log_error "Migration failed!"
                exit 1
            }
            log_info "Migrations completed successfully"
        else
            log_debug "No alembic.ini found, skipping migrations"
        fi
    fi
}

# Warm-up the service
warmup_service() {
    log_info "Warming up service..."
    
    # Wait for service to start
    sleep 2
    
    # Call health endpoint to warm up
    for i in {1..10}; do
        if curl -sf "http://localhost:${PORT}/health" > /dev/null 2>&1; then
            log_info "Service warm-up successful"
            return 0
        fi
        sleep 1
    done
    
    log_warn "Service warm-up timeout (non-fatal)"
    return 0
}

# Graceful shutdown handler
cleanup() {
    local exit_code=$?
    log_info "Shutting down service (exit code: $exit_code)..."
    
    # Log shutdown metrics
    if [ -n "$MAIN_PID" ]; then
        log_info "Stopping main process (PID: $MAIN_PID)..."
        
        # Send SIGTERM for graceful shutdown
        kill -TERM "$MAIN_PID" 2>/dev/null || true
        
        # Wait for graceful shutdown
        local count=0
        while kill -0 "$MAIN_PID" 2>/dev/null && [ $count -lt $SHUTDOWN_TIMEOUT ]; do
            sleep 1
            count=$((count + 1))
            log_debug "Waiting for shutdown... ($count/$SHUTDOWN_TIMEOUT)"
        done
        
        # Force kill if still running
        if kill -0 "$MAIN_PID" 2>/dev/null; then
            log_warn "Graceful shutdown timeout, forcing termination"
            kill -KILL "$MAIN_PID" 2>/dev/null || true
        fi
    fi
    
    # Log final metrics
    log_info "Service shutdown complete (runtime: $SECONDS seconds)"
    
    # Record shutdown event if SignOz is configured
    if [ -n "$SIGNOZ_ENDPOINT" ]; then
        python3 -c "
from opentelemetry import trace
tracer = trace.get_tracer('shutdown')
with tracer.start_as_current_span('service.shutdown'):
    pass
" 2>/dev/null || true
    fi
    
    exit $exit_code
}

# Signal handlers
handle_sigterm() {
    log_info "Received SIGTERM, initiating graceful shutdown..."
    cleanup
}

handle_sigint() {
    log_info "Received SIGINT, initiating shutdown..."
    cleanup
}

# ======================
# Main Execution
# ======================

main() {
    # Set up signal handlers
    trap handle_sigterm TERM
    trap handle_sigint INT
    trap cleanup EXIT
    
    # Log startup information
    log_info "Starting DotMac service: ${SERVICE_NAME}"
    log_info "Environment: ${ENVIRONMENT}"
    log_info "Port: ${PORT}"
    log_info "Workers: ${WORKERS}"
    log_info "Module: ${APP_MODULE}"
    
    # Startup sequence
    load_secrets
    validate_config
    wait_for_dependencies
    run_migrations
    setup_observability
    
    # Prepare uvicorn command
    UVICORN_CMD="uvicorn ${APP_MODULE}"
    UVICORN_ARGS=(
        "--host" "$HOST"
        "--port" "$PORT"
        "--workers" "$WORKERS"
        "--loop" "uvloop"
        "--lifespan" "on"
        "--timeout-keep-alive" "$KEEPALIVE"
        "--timeout-graceful-shutdown" "$GRACEFUL_TIMEOUT"
    )
    
    # Add production optimizations
    if [ "$ENVIRONMENT" = "production" ]; then
        UVICORN_ARGS+=(
            "--no-access-log"  # Use structured logging instead
            "--no-server-header"  # Security
            "--limit-concurrency" "1000"
            "--limit-max-requests" "10000"  # Restart workers periodically
        )
    else
        UVICORN_ARGS+=(
            "--reload"
            "--reload-dir" "/app/backend/dotmac_${SERVICE_NAME}"
            "--log-level" "$LOG_LEVEL"
        )
    fi
    
    # Add access logging if enabled
    if [ "$ACCESS_LOG" = "true" ]; then
        UVICORN_ARGS+=("--access-log")
    fi
    
    # Add log config if exists
    if [ -f "/app/logging.json" ]; then
        UVICORN_ARGS+=("--log-config" "/app/logging.json")
    fi
    
    # Add SSL if configured
    if [ -n "${SSL_KEYFILE:-}" ] && [ -n "${SSL_CERTFILE:-}" ]; then
        UVICORN_ARGS+=(
            "--ssl-keyfile" "$SSL_KEYFILE"
            "--ssl-certfile" "$SSL_CERTFILE"
        )
    fi
    
    # Build final command
    if [ -n "${INSTRUMENT_CMD:-}" ]; then
        FINAL_CMD="$INSTRUMENT_CMD -- $UVICORN_CMD ${UVICORN_ARGS[*]}"
    else
        FINAL_CMD="$UVICORN_CMD ${UVICORN_ARGS[*]}"
    fi
    
    log_info "Starting server with command:"
    log_info "$FINAL_CMD"
    
    # Start the service
    if [ "$ENVIRONMENT" = "production" ]; then
        # Production: use exec to replace shell process
        exec $FINAL_CMD &
    else
        # Development: run in background for monitoring
        $FINAL_CMD &
    fi
    
    MAIN_PID=$!
    log_info "Service started (PID: $MAIN_PID)"
    
    # Warm up the service
    warmup_service &
    
    # Wait for the main process
    wait $MAIN_PID
}

# Run main function
main "$@"