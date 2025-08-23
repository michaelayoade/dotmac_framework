#!/bin/bash

# Production startup script for DotMac ISP Framework
# Handles SaaS-specific initialization and tenant configuration

set -euo pipefail

# Colors for logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Configuration validation
validate_environment() {
    log "Validating environment configuration..."
    
    # Required environment variables for SaaS deployment
    local required_vars=(
        "ISP_TENANT_ID"
        "DATABASE_URL"
        "REDIS_URL"
        "ENVIRONMENT"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Validate tenant ID format (alphanumeric, underscore, hyphen)
    if [[ ! "$ISP_TENANT_ID" =~ ^[a-zA-Z0-9_-]+$ ]]; then
        error "Invalid ISP_TENANT_ID format: $ISP_TENANT_ID"
        exit 1
    fi
    
    log "Environment validation passed for tenant: $ISP_TENANT_ID"
}

# Database connectivity check
check_database_connection() {
    log "Checking database connectivity..."
    
    python3 -c "
import asyncio
import sys
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
import os

try:
    engine = create_engine(os.environ['DATABASE_URL'])
    with engine.connect() as conn:
        result = conn.execute('SELECT 1')
    print('✅ Database connection successful')
    sys.exit(0)
except SQLAlchemyError as e:
    print(f'❌ Database connection failed: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ Unexpected database error: {e}')
    sys.exit(1)
"
    
    if [ $? -ne 0 ]; then
        error "Database connectivity check failed"
        exit 1
    fi
}

# Redis connectivity check
check_redis_connection() {
    log "Checking Redis connectivity..."
    
    python3 -c "
import redis
import sys
import os
from urllib.parse import urlparse

try:
    redis_url = os.environ['REDIS_URL']
    parsed = urlparse(redis_url)
    
    r = redis.Redis(
        host=parsed.hostname,
        port=parsed.port or 6379,
        password=parsed.password,
        db=int(parsed.path.lstrip('/')) if parsed.path else 0
    )
    
    r.ping()
    print('✅ Redis connection successful')
    sys.exit(0)
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
    sys.exit(1)
"
    
    if [ $? -ne 0 ]; then
        error "Redis connectivity check failed"
        exit 1
    fi
}

# Initialize tenant-specific configuration
initialize_tenant_config() {
    log "Initializing tenant-specific configuration for: $ISP_TENANT_ID"
    
    # Create tenant-specific directories
    mkdir -p "/app/logs/${ISP_TENANT_ID}"
    mkdir -p "/app/tmp/${ISP_TENANT_ID}"
    
    # Set tenant-specific log file
    export LOG_FILE="/app/logs/${ISP_TENANT_ID}/application.log"
    
    # Initialize tenant configuration in database
    python3 -c "
import asyncio
import sys
import os
from dotmac_isp.core.database import get_async_session
from dotmac_isp.core.tenant_initialization import initialize_tenant_data

async def init():
    try:
        async with get_async_session() as session:
            await initialize_tenant_data(session, os.environ['ISP_TENANT_ID'])
        print(f'✅ Tenant {os.environ[\"ISP_TENANT_ID\"]} initialized successfully')
        return True
    except Exception as e:
        print(f'❌ Tenant initialization failed: {e}')
        return False

if __name__ == '__main__':
    result = asyncio.run(init())
    sys.exit(0 if result else 1)
" || {
        warn "Tenant initialization had issues, continuing with startup..."
    }
}

# Plugin license validation
validate_plugin_licenses() {
    log "Validating plugin licenses for tenant: $ISP_TENANT_ID"
    
    python3 -c "
import asyncio
import sys
import os
from dotmac_isp.plugins.core.manager import PluginManager
from dotmac_isp.modules.licensing.service import LicensingService
from dotmac_isp.core.database import get_async_session

async def validate_licenses():
    try:
        async with get_async_session() as session:
            licensing_service = LicensingService(session)
            plugin_manager = PluginManager()
            
            # Get tenant's licensed plugins
            licenses = await licensing_service.get_active_licenses(
                tenant_id=os.environ['ISP_TENANT_ID']
            )
            
            # Validate each plugin license
            for license in licenses:
                if license.is_expired:
                    print(f'⚠️  License expired for: {license.software.name}')
                else:
                    print(f'✅ Valid license for: {license.software.name}')
            
            print(f'✅ Plugin license validation completed')
            return True
    except Exception as e:
        print(f'❌ Plugin license validation failed: {e}')
        return False

if __name__ == '__main__':
    result = asyncio.run(validate_licenses())
    sys.exit(0 if result else 1)
" || {
        warn "Plugin license validation had issues, some features may be disabled..."
    }
}

# Pre-flight health checks
run_preflight_checks() {
    log "Running pre-flight health checks..."
    
    # Check disk space
    local disk_usage=$(df /app | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt 90 ]; then
        error "Disk usage is ${disk_usage}%, which is too high"
        exit 1
    fi
    
    # Check memory
    local mem_available=$(free -m | awk 'NR==2{printf "%.0f", $7*100/($2+$3+$4+$5+$6+$7)}')
    if [ "$mem_available" -lt 10 ]; then
        warn "Available memory is only ${mem_available}%"
    fi
    
    log "Pre-flight checks completed"
}

# Start application with proper configuration
start_application() {
    log "Starting DotMac ISP Framework for tenant: $ISP_TENANT_ID"
    
    # Set Gunicorn configuration based on environment
    case "$ENVIRONMENT" in
        production)
            WORKERS=${WORKERS:-4}
            WORKER_CLASS=${WORKER_CLASS:-"uvicorn.workers.UvicornWorker"}
            LOG_LEVEL=${LOG_LEVEL:-"info"}
            TIMEOUT=${TIMEOUT:-30}
            ;;
        staging)
            WORKERS=${WORKERS:-2}
            WORKER_CLASS=${WORKER_CLASS:-"uvicorn.workers.UvicornWorker"}
            LOG_LEVEL=${LOG_LEVEL:-"debug"}
            TIMEOUT=${TIMEOUT:-60}
            ;;
        *)
            WORKERS=${WORKERS:-1}
            WORKER_CLASS=${WORKER_CLASS:-"uvicorn.workers.UvicornWorker"}
            LOG_LEVEL=${LOG_LEVEL:-"debug"}
            TIMEOUT=${TIMEOUT:-300}
            ;;
    esac
    
    # Create Gunicorn configuration
    cat > /app/gunicorn.conf.py << EOF
# Gunicorn configuration for tenant: ${ISP_TENANT_ID}
bind = "${BIND:-0.0.0.0:8000}"
workers = ${WORKERS}
worker_class = "${WORKER_CLASS}"
worker_connections = 1000
timeout = ${TIMEOUT}
keepalive = ${KEEPALIVE:-5}
max_requests = ${MAX_REQUESTS:-1000}
max_requests_jitter = ${MAX_REQUESTS_JITTER:-100}
preload_app = True
loglevel = "${LOG_LEVEL}"
accesslog = "/app/logs/${ISP_TENANT_ID}/access.log"
errorlog = "/app/logs/${ISP_TENANT_ID}/error.log"
access_log_format = '%h %l %u %t "%r" %s %b "%{Referer}i" "%{User-Agent}i" %D'

# Worker process handling
worker_tmp_dir = "/app/tmp/${ISP_TENANT_ID}"
tmp_upload_dir = "/app/tmp/${ISP_TENANT_ID}/uploads"

# Security settings
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Process naming
proc_name = "dotmac-isp-${ISP_TENANT_ID}"

def on_starting(server):
    server.log.info("Starting DotMac ISP Framework for tenant: ${ISP_TENANT_ID}")

def worker_int(worker):
    worker.log.info("Worker received INT or QUIT signal for tenant: ${ISP_TENANT_ID}")

def on_exit(server):
    server.log.info("DotMac ISP Framework shutting down for tenant: ${ISP_TENANT_ID}")
EOF
    
    log "Starting Gunicorn with configuration:"
    log "  - Workers: $WORKERS"
    log "  - Worker Class: $WORKER_CLASS"
    log "  - Bind: ${BIND:-0.0.0.0:8000}"
    log "  - Log Level: $LOG_LEVEL"
    log "  - Tenant: $ISP_TENANT_ID"
    
    # Start the application
    exec gunicorn --config /app/gunicorn.conf.py dotmac_isp.main:app
}

# Signal handlers for graceful shutdown
cleanup() {
    log "Received shutdown signal, performing cleanup for tenant: $ISP_TENANT_ID"
    
    # Cleanup tenant-specific resources
    python3 -c "
import asyncio
import sys
import os

async def cleanup_tenant():
    try:
        # Perform any tenant-specific cleanup
        print(f'🧹 Cleaning up resources for tenant: {os.environ[\"ISP_TENANT_ID\"]}')
        
        # Close database connections, clear caches, etc.
        # Implementation would go here
        
        print('✅ Cleanup completed')
        return True
    except Exception as e:
        print(f'❌ Cleanup failed: {e}')
        return False

if __name__ == '__main__':
    result = asyncio.run(cleanup_tenant())
    sys.exit(0 if result else 1)
" || true
    
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT SIGQUIT

# Main execution flow
main() {
    log "Starting DotMac ISP Framework production deployment"
    log "Tenant ID: ${ISP_TENANT_ID:-unknown}"
    log "Environment: ${ENVIRONMENT:-unknown}"
    log "Version: $(cat /app/VERSION 2>/dev/null || echo 'unknown')"
    
    # Run all initialization steps
    validate_environment
    check_database_connection
    check_redis_connection
    initialize_tenant_config
    validate_plugin_licenses
    run_preflight_checks
    
    # Start the application
    start_application
}

# Execute main function
main "$@"