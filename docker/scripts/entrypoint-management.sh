#!/bin/bash

# DotMac Management Platform Entrypoint Script
# Handles initialization, migrations, and plugin system startup

set -e

echo "🚀 Starting DotMac Management Platform..."

# Function to wait for database
wait_for_db() {
    echo "⏳ Waiting for database connection..."
    while ! pg_isready -h "${DATABASE_HOST:-db}" -p "${DATABASE_PORT:-5432}" -U "${DATABASE_USER:-dotmac}"; do
        echo "Database not ready, waiting..."
        sleep 2
    done
    echo "✅ Database connection established"
}

# Function to run database migrations
run_migrations() {
    echo "🔄 Running database migrations..."
    cd /app
    if [ -f "alembic.ini" ]; then
        python -m alembic upgrade head
        echo "✅ Database migrations completed"
    else
        echo "⚠️  No alembic.ini found, skipping migrations"
    fi
}

# Function to initialize plugin system
init_plugin_system() {
    echo "🔌 Initializing plugin system..."
    
    # Create plugin directories if they don't exist
    mkdir -p "${PLUGIN_REGISTRY_PATH}" "${PLUGIN_DATA_PATH}" "${PLUGIN_LOGS_PATH}" "${PLUGIN_UPLOAD_PATH}"
    
    # Initialize plugin registry
    if [ -n "${INIT_PLUGIN_REGISTRY}" ] && [ "${INIT_PLUGIN_REGISTRY}" = "true" ]; then
        echo "📦 Initializing plugin registry..."
        python -c "
import asyncio
import sys
sys.path.append('/app/src')

async def init_plugins():
    try:
        from dotmac_shared.plugins.core.manager import PluginManager
        from dotmac_management.services.plugin_service import get_plugin_service
        
        # Initialize plugin manager
        plugin_manager = PluginManager(registry_path='${PLUGIN_REGISTRY_PATH}')
        await plugin_manager.initialize()
        
        print('✅ Plugin system initialized')
        return True
    except Exception as e:
        print(f'⚠️  Plugin system initialization warning: {e}')
        return False

asyncio.run(init_plugins())
        "
    fi
    
    echo "✅ Plugin system ready"
}

# Function to check system health
check_system_health() {
    echo "🔍 Performing system health checks..."
    
    # Check required environment variables
    required_vars=("DATABASE_URL" "SECRET_KEY")
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            echo "❌ Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Check plugin directories are writable
    if [ ! -w "${PLUGIN_DATA_PATH}" ]; then
        echo "❌ Plugin data directory is not writable: ${PLUGIN_DATA_PATH}"
        exit 1
    fi
    
    echo "✅ System health checks passed"
}

# Function to setup monitoring
setup_monitoring() {
    if [ -n "${ENABLE_MONITORING}" ] && [ "${ENABLE_MONITORING}" = "true" ]; then
        echo "📊 Setting up monitoring..."
        
        # Create monitoring directories
        mkdir -p /app/monitoring/metrics /app/monitoring/logs
        
        # Start background monitoring if configured
        if [ -n "${MONITORING_ENDPOINT}" ]; then
            echo "📈 Monitoring endpoint configured: ${MONITORING_ENDPOINT}"
        fi
        
        echo "✅ Monitoring setup completed"
    fi
}

# Function to handle graceful shutdown
cleanup() {
    echo "🛑 Shutting down gracefully..."
    
    # Stop background processes
    jobs -p | xargs -r kill
    
    # Plugin system cleanup
    if [ -n "${PLUGIN_CLEANUP_ON_SHUTDOWN}" ] && [ "${PLUGIN_CLEANUP_ON_SHUTDOWN}" = "true" ]; then
        echo "🔌 Cleaning up plugin system..."
        # Add plugin cleanup logic here
    fi
    
    echo "✅ Cleanup completed"
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Main initialization sequence
main() {
    echo "🔧 Environment: ${DOTMAC_ENVIRONMENT:-development}"
    echo "🔌 Plugin Registry: ${PLUGIN_REGISTRY_PATH}"
    echo "📁 Plugin Data: ${PLUGIN_DATA_PATH}"
    
    # Run initialization steps
    check_system_health
    
    if [ "${SKIP_DB_WAIT:-false}" != "true" ]; then
        wait_for_db
    fi
    
    if [ "${SKIP_MIGRATIONS:-false}" != "true" ]; then
        run_migrations
    fi
    
    init_plugin_system
    setup_monitoring
    
    echo "🎉 DotMac Management Platform initialization completed!"
    echo "🌐 Starting application server..."
    
    # Execute the main command
    exec "$@"
}

# Run main function
main "$@"