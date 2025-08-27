#!/bin/bash

# Tenant Container Startup Script
# Handles tenant-specific initialization, migrations, and health checks

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] TENANT-$TENANT_ID:${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] TENANT-$TENANT_ID WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] TENANT-$TENANT_ID ERROR:${NC} $1"
}

# Check required environment variables
check_environment() {
    log "Checking environment variables..."
    
    required_vars=(
        "TENANT_ID"
        "DATABASE_URL" 
        "REDIS_URL"
        "DATABASE_SCHEMA"
        "PYTHONPATH"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            error "Missing required environment variable: $var"
            exit 1
        fi
    done
    
    log "Environment check passed ✓"
}

# Wait for dependencies to be ready
wait_for_dependencies() {
    log "Waiting for dependencies..."
    
    # Wait for PostgreSQL
    log "Checking PostgreSQL connection..."
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if python3 -c "
import asyncio
import asyncpg
import os

async def check_db():
    try:
        conn = await asyncpg.connect(os.environ['DATABASE_URL'])
        await conn.close()
        return True
    except:
        return False

result = asyncio.run(check_db())
exit(0 if result else 1)
" 2>/dev/null; then
            log "PostgreSQL is ready ✓"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            error "PostgreSQL not ready after $max_attempts attempts"
            exit 1
        fi
        
        warn "PostgreSQL not ready, attempt $attempt/$max_attempts..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    # Wait for Redis
    log "Checking Redis connection..."
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if python3 -c "
import asyncio
import redis.asyncio as redis
import os

async def check_redis():
    try:
        r = redis.from_url(os.environ['REDIS_URL'])
        await r.ping()
        await r.close()
        return True
    except:
        return False

result = asyncio.run(check_redis())
exit(0 if result else 1)
" 2>/dev/null; then
            log "Redis is ready ✓"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            error "Redis not ready after $max_attempts attempts"
            exit 1
        fi
        
        warn "Redis not ready, attempt $attempt/$max_attempts..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log "All dependencies ready ✓"
}

# Run database migrations for tenant schema
run_migrations() {
    log "Running Alembic migrations for tenant schema..."
    
    # Set search path to tenant schema for migrations
    export ALEMBIC_CONFIG="alembic.ini"
    
    # Run migrations
    if alembic upgrade head; then
        log "Migrations completed successfully ✓"
    else
        error "Migrations failed"
        exit 1
    fi
}

# Initialize tenant-specific configuration
initialize_tenant_config() {
    log "Initializing tenant configuration..."
    
    # Create tenant-specific directories
    mkdir -p /app/logs/tenant-$TENANT_ID
    mkdir -p /app/uploads/tenant-$TENANT_ID
    
    # Set proper permissions
    chown -R appuser:appuser /app/logs/tenant-$TENANT_ID
    chown -R appuser:appuser /app/uploads/tenant-$TENANT_ID
    
    log "Tenant configuration initialized ✓"
}

# Validate tenant setup
validate_setup() {
    log "Validating tenant setup..."
    
    # Test application imports
    if python3 -c "
import sys
sys.path.insert(0, '/app/shared')
from startup.error_handling import create_startup_manager
from dotmac_isp.app import create_app
print('Import validation passed')
"; then
        log "Import validation passed ✓"
    else
        error "Import validation failed"
        exit 1
    fi
    
    log "Tenant setup validation completed ✓"
}

# Main startup sequence
main() {
    log "Starting tenant container initialization..."
    
    # Run startup checks
    check_environment
    wait_for_dependencies
    initialize_tenant_config
    run_migrations
    validate_setup
    
    log "Tenant initialization completed successfully! Starting application..."
    
    # Start the application with tenant-specific configuration
    exec uvicorn dotmac_isp.app:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers 1 \
        --access-log \
        --log-level info
}

# Handle signals for graceful shutdown
cleanup() {
    log "Received shutdown signal, cleaning up..."
    # TODO: Add any cleanup logic here
    exit 0
}

trap cleanup SIGTERM SIGINT

# Run main function
main "$@"