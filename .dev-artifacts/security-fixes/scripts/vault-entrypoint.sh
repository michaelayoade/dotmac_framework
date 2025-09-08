#!/bin/bash
# Vault-Integrated Entrypoint for DotMac Services
# This script authenticates with Vault and configures services with dynamic credentials

set -e

# Source the Vault authentication helper
SCRIPT_DIR="$(dirname "$0")"
source "${SCRIPT_DIR}/vault-auth-helper.sh"

SERVICE_NAME=${SERVICE_NAME:-unknown}
ORIGINAL_CMD="$@"

log "🚀 Starting Vault-integrated service: $SERVICE_NAME"
log "Original command: $ORIGINAL_CMD"

# Authenticate with Vault
log "🔐 Authenticating with Vault..."
VAULT_TOKEN=$(vault_authenticate)

if [ $? -ne 0 ] || [ -z "$VAULT_TOKEN" ]; then
    log "❌ Vault authentication failed"
    exit 1
fi

# Setup background token renewal (renew every hour)
setup_token_renewal 3600

# Service-specific configuration
configure_service() {
    case "$SERVICE_NAME" in
        "signoz-query")
            configure_signoz_query
            ;;
        "otel-collector"|"signoz-collector")
            configure_otel_collector
            ;;
        "dotmac-management")
            configure_management_service
            ;;
        "dotmac-isp")
            configure_isp_service
            ;;
        *)
            log "⚠️ No specific configuration for service: $SERVICE_NAME"
            ;;
    esac
}

# Configure SigNoz Query Service
configure_signoz_query() {
    log "⚙️ Configuring SigNoz Query Service with Vault credentials..."
    
    # Get ClickHouse credentials
    local clickhouse_creds=$(get_database_credentials "signoz-query")
    if [ $? -ne 0 ]; then
        log "❌ Failed to get ClickHouse credentials"
        exit 1
    fi
    
    local username=$(echo "$clickhouse_creds" | jq -r '.username')
    local password=$(echo "$clickhouse_creds" | jq -r '.password')
    
    # Get observability configuration
    local obs_config=$(get_kv_secret "dotmac/data/observability")
    local clickhouse_config=$(get_kv_secret "dotmac/data/clickhouse")
    
    # Set environment variables for the service
    export CLICKHOUSE_USER="$username"
    export CLICKHOUSE_PASSWORD="$password"
    export CLICKHOUSE_DSN="tcp://${username}:${password}@${CLICKHOUSE_HOST:-clickhouse}:${CLICKHOUSE_PORT:-9000}?database=signoz_traces"
    
    # Additional configuration from Vault
    if [ -n "$obs_config" ]; then
        export SIGNOZ_ENDPOINT=$(echo "$obs_config" | jq -r '.signoz_endpoint // "http://localhost:8080"')
        export TRACE_SAMPLING_RATE=$(echo "$obs_config" | jq -r '.trace_sampling_rate // "0.1"')
        export LOG_LEVEL=$(echo "$obs_config" | jq -r '.log_level // "INFO"')
    fi
    
    log "✅ SigNoz Query Service configured with Vault credentials"
}

# Configure OTEL Collector
configure_otel_collector() {
    log "⚙️ Configuring OTEL Collector with Vault credentials..."
    
    # Get ClickHouse credentials for collector
    local clickhouse_creds=$(get_database_credentials "signoz-collector")
    if [ $? -ne 0 ]; then
        log "❌ Failed to get ClickHouse credentials for collector"
        exit 1
    fi
    
    local username=$(echo "$clickhouse_creds" | jq -r '.username')
    local password=$(echo "$clickhouse_creds" | jq -r '.password')
    
    # Get configuration from Vault
    local obs_config=$(get_kv_secret "dotmac/data/observability")
    local clickhouse_config=$(get_kv_secret "dotmac/data/clickhouse")
    
    # Generate dynamic OTEL collector config
    local config_template="/etc/otel-collector-config.yaml"
    local config_file="/tmp/otel-collector-config-runtime.yaml"
    
    if [ -f "$config_template" ]; then
        # Replace placeholders in config template
        sed \
            -e "s/{{CLICKHOUSE_USERNAME}}/$username/g" \
            -e "s/{{CLICKHOUSE_PASSWORD}}/$password/g" \
            -e "s/{{CLICKHOUSE_HOST}}/${CLICKHOUSE_HOST:-clickhouse}/g" \
            -e "s/{{CLICKHOUSE_PORT}}/${CLICKHOUSE_PORT:-9000}/g" \
            "$config_template" > "$config_file"
        
        log "✅ OTEL Collector config generated with Vault credentials"
        
        # Update the command to use the runtime config
        ORIGINAL_CMD=$(echo "$ORIGINAL_CMD" | sed "s|/etc/otel-collector-config.yaml|$config_file|g")
    else
        log "⚠️ OTEL config template not found, using environment variables"
        export CLICKHOUSE_USER="$username"
        export CLICKHOUSE_PASSWORD="$password"
    fi
    
    log "✅ OTEL Collector configured with Vault credentials"
}

# Configure Management Service
configure_management_service() {
    log "⚙️ Configuring Management Service with Vault credentials..."
    
    # Get PostgreSQL credentials
    local db_creds=$(get_database_credentials "management")
    if [ $? -ne 0 ]; then
        log "❌ Failed to get PostgreSQL credentials"
        exit 1
    fi
    
    local db_username=$(echo "$db_creds" | jq -r '.username')
    local db_password=$(echo "$db_creds" | jq -r '.password')
    
    # Get application secrets
    local mgmt_secrets=$(get_kv_secret "dotmac/data/management")
    local app_secrets=$(get_kv_secret "dotmac/data/application")
    local redis_config=$(get_kv_secret "dotmac/data/redis")
    
    # Set database connection
    export DATABASE_URL="postgresql+asyncpg://${db_username}:${db_password}@postgres:5432/dotmac_db"
    
    # Set application secrets
    if [ -n "$mgmt_secrets" ]; then
        export SECRET_KEY=$(echo "$mgmt_secrets" | jq -r '.secret_key')
        export JWT_SECRET=$(echo "$mgmt_secrets" | jq -r '.jwt_secret')
        export ENCRYPTION_KEY=$(echo "$mgmt_secrets" | jq -r '.encryption_key')
    fi
    
    # Set Redis connection
    if [ -n "$redis_config" ]; then
        local redis_password=$(echo "$redis_config" | jq -r '.password')
        export REDIS_URL="redis://:${redis_password}@redis:6379/0"
    fi
    
    log "✅ Management Service configured with Vault credentials"
}

# Configure ISP Service
configure_isp_service() {
    log "⚙️ Configuring ISP Service with Vault credentials..."
    
    # Get PostgreSQL credentials
    local db_creds=$(get_database_credentials "isp")
    if [ $? -ne 0 ]; then
        log "❌ Failed to get PostgreSQL credentials"
        exit 1
    fi
    
    local db_username=$(echo "$db_creds" | jq -r '.username')
    local db_password=$(echo "$db_creds" | jq -r '.password')
    
    # Get application secrets
    local isp_secrets=$(get_kv_secret "dotmac/data/isp")
    local app_secrets=$(get_kv_secret "dotmac/data/application")
    local redis_config=$(get_kv_secret "dotmac/data/redis")
    
    # Set database connection
    export DATABASE_URL="postgresql+asyncpg://${db_username}:${db_password}@postgres:5432/dotmac_db"
    
    # Set application secrets
    if [ -n "$isp_secrets" ]; then
        export SECRET_KEY=$(echo "$isp_secrets" | jq -r '.secret_key')
        export JWT_SECRET=$(echo "$isp_secrets" | jq -r '.jwt_secret')
        export BILLING_ENCRYPTION_KEY=$(echo "$isp_secrets" | jq -r '.billing_encryption_key')
    fi
    
    # Set Redis connection (use different DB for ISP)
    if [ -n "$redis_config" ]; then
        local redis_password=$(echo "$redis_config" | jq -r '.password')
        export REDIS_URL="redis://:${redis_password}@redis:6379/1"
    fi
    
    log "✅ ISP Service configured with Vault credentials"
}

# Trap function for cleanup
cleanup() {
    log "🧹 Cleaning up Vault integration..."
    
    # Kill token renewal process if it exists
    if [ -f "/tmp/vault-renewal.pid" ]; then
        local renewal_pid=$(cat /tmp/vault-renewal.pid)
        if kill -0 "$renewal_pid" 2>/dev/null; then
            log "🔄 Stopping token renewal process (PID: $renewal_pid)"
            kill "$renewal_pid"
        fi
        rm -f /tmp/vault-renewal.pid
    fi
    
    # Clean up temporary files
    rm -f "$VAULT_TOKEN_FILE"
    rm -f /tmp/otel-collector-config-runtime.yaml
    
    log "✅ Cleanup completed"
}

# Set up signal handlers for graceful shutdown
trap cleanup EXIT TERM INT

# Configure the service with Vault secrets
configure_service

log "🎯 Starting service with Vault-managed configuration..."
log "Command: $ORIGINAL_CMD"

# Execute the original command
exec $ORIGINAL_CMD