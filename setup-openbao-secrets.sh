#!/bin/bash
# OpenBao Secrets Setup for Layered Observability
# Purpose: Initialize OpenBao with secrets for all layers

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        "INFO") echo -e "${BLUE}[INFO]${NC} ${timestamp} - $message" ;;
        "SUCCESS") echo -e "${GREEN}[SUCCESS]${NC} ${timestamp} - $message" ;;
        "WARNING") echo -e "${YELLOW}[WARNING]${NC} ${timestamp} - $message" ;;
        "ERROR") echo -e "${RED}[ERROR]${NC} ${timestamp} - $message" ;;
    esac
}

# Default OpenBao configuration
OPENBAO_ADDR="${OPENBAO_ADDR:-http://localhost:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-dev-root-token}"
VAULT_PATH="${VAULT_PATH:-secret/dotmac}"

# Function to wait for OpenBao to be ready
wait_for_openbao() {
    log "INFO" "Waiting for OpenBao to be ready..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if timeout 5 curl -sf "$OPENBAO_ADDR/v1/sys/health" >/dev/null 2>&1; then
            log "SUCCESS" "OpenBao is ready"
            return 0
        fi
        
        attempt=$((attempt + 1))
        log "INFO" "Attempt $attempt/$max_attempts - waiting for OpenBao..."
        sleep 2
    done
    
    log "ERROR" "OpenBao not ready after $((max_attempts * 2)) seconds"
    return 1
}

# Function to check if secret path exists
secret_exists() {
    local path="$1"
    if timeout 5 curl -sf \
        -H "X-Vault-Token: $VAULT_TOKEN" \
        "$OPENBAO_ADDR/v1/$path" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to create/update secret
create_secret() {
    local path="$1"
    local data="$2"
    
    log "INFO" "Creating secret at $path"
    
    if curl -sf \
        -H "X-Vault-Token: $VAULT_TOKEN" \
        -H "Content-Type: application/json" \
        -X POST \
        -d "$data" \
        "$OPENBAO_ADDR/v1/$path" >/dev/null 2>&1; then
        log "SUCCESS" "Secret created at $path"
        return 0
    else
        log "ERROR" "Failed to create secret at $path"
        return 1
    fi
}

# Function to generate secure password
generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
}

# Function to setup secrets for all layers
setup_layer_secrets() {
    log "INFO" "Setting up secrets for layered deployment..."
    
    # Generate secure passwords if not provided
    local postgres_password="${POSTGRES_PASSWORD:-$(generate_password)}"
    local redis_password="${REDIS_PASSWORD:-$(generate_password)}"
    local clickhouse_password="${CLICKHOUSE_PASSWORD:-$(generate_password)}"
    local mgmt_secret_key="${MGMT_SECRET_KEY:-$(generate_password)}"
    local mgmt_jwt_secret="${MGMT_JWT_SECRET_KEY:-$(generate_password)}"
    
    # Gate E-0a: Core Infrastructure Secrets
    log "INFO" "Setting up Gate E-0a secrets (Core Infrastructure)..."
    
    local e0a_secrets=$(cat <<EOF
{
  "data": {
    "postgres_password": "$postgres_password",
    "postgres_user": "dotmac_admin",
    "redis_password": "$redis_password",
    "vault_token": "$VAULT_TOKEN"
  }
}
EOF
)
    
    create_secret "dotmac/data/e0a" "$e0a_secrets" || return 1
    
    # Gate E-0b: Observability Secrets
    log "INFO" "Setting up Gate E-0b secrets (Observability)..."
    
    local e0b_secrets=$(cat <<EOF
{
  "data": {
    "clickhouse_password": "$clickhouse_password",
    "clickhouse_user": "signoz",
    "signoz_access_token": "${SIGNOZ_ACCESS_TOKEN:-}",
    "collector_endpoint": "dotmac-signoz-collector:4317"
  }
}
EOF
)
    
    create_secret "dotmac/data/e0b" "$e0b_secrets" || return 1
    
    # Gate E-0c: Application Secrets
    log "INFO" "Setting up Gate E-0c secrets (Applications)..."
    
    local e0c_secrets=$(cat <<EOF
{
  "data": {
    "mgmt_secret_key": "$mgmt_secret_key",
    "mgmt_jwt_secret_key": "$mgmt_jwt_secret",
    "stripe_secret_key": "${STRIPE_SECRET_KEY:-sk_test_placeholder}",
    "sendgrid_api_key": "${SENDGRID_API_KEY:-SG.placeholder}",
    "app_version": "${APP_VERSION:-1.0.0}",
    "environment": "${ENVIRONMENT:-development}"
  }
}
EOF
)
    
    create_secret "dotmac/data/e0c" "$e0c_secrets" || return 1
    
    # Create combined secrets for backward compatibility
    log "INFO" "Creating combined secrets for compatibility..."
    
    local combined_secrets=$(cat <<EOF
{
  "data": {
    "postgres_password": "$postgres_password",
    "redis_password": "$redis_password",
    "clickhouse_password": "$clickhouse_password",
    "vault_token": "$VAULT_TOKEN",
    "mgmt_secret_key": "$mgmt_secret_key",
    "mgmt_jwt_secret_key": "$mgmt_jwt_secret",
    "stripe_secret_key": "${STRIPE_SECRET_KEY:-sk_test_placeholder}",
    "sendgrid_api_key": "${SENDGRID_API_KEY:-SG.placeholder}",
    "app_version": "${APP_VERSION:-1.0.0}",
    "environment": "${ENVIRONMENT:-development}"
  }
}
EOF
)
    
    create_secret "dotmac/data/development" "$combined_secrets" || return 1
    
    log "SUCCESS" "All layer secrets configured successfully"
    
    # Display summary (without actual secrets)
    echo ""
    echo "🔐 Secrets Configuration Summary:"
    echo "================================="
    echo "• Gate E-0a (Core): $VAULT_PATH/e0a"
    echo "  - PostgreSQL credentials"
    echo "  - Redis credentials"
    echo "  - Vault token"
    echo ""
    echo "• Gate E-0b (Observability): $VAULT_PATH/e0b"
    echo "  - ClickHouse credentials"
    echo "  - SignOz configuration"
    echo "  - OTLP endpoints"
    echo ""
    echo "• Gate E-0c (Applications): $VAULT_PATH/e0c"
    echo "  - Management platform secrets"
    echo "  - External service keys"
    echo "  - Application configuration"
    echo ""
    echo "• Combined (Compatibility): $VAULT_PATH/development"
    echo "  - All secrets for existing integrations"
    echo ""
}

# Function to validate secrets
validate_secrets() {
    log "INFO" "Validating stored secrets..."
    
    local paths=("dotmac/data/e0a" "dotmac/data/e0b" "dotmac/data/e0c" "dotmac/data/development")
    
    for path in "${paths[@]}"; do
        if secret_exists "$path"; then
            log "SUCCESS" "Secret exists at $path"
        else
            log "ERROR" "Secret missing at $path"
            return 1
        fi
    done
    
    log "SUCCESS" "All secrets validated"
    return 0
}

# Function to retrieve secret for deployment (KV v2 format)
get_secret() {
    local path="$1"
    local key="$2"
    
    curl -sf \
        -H "X-Vault-Token: $VAULT_TOKEN" \
        "$OPENBAO_ADDR/v1/$path" | \
        jq -r ".data.data.$key" 2>/dev/null || echo ""
}

# Function to export secrets as environment variables
export_secrets_as_env() {
    log "INFO" "Exporting secrets as environment variables..."
    
    # Get secrets from OpenBao
    local postgres_password=$(get_secret "dotmac/data/development" "postgres_password")
    local redis_password=$(get_secret "dotmac/data/development" "redis_password")
    local clickhouse_password=$(get_secret "dotmac/data/development" "clickhouse_password")
    local mgmt_secret=$(get_secret "dotmac/data/development" "mgmt_secret_key")
    local mgmt_jwt_secret=$(get_secret "dotmac/data/development" "mgmt_jwt_secret_key")
    
    if [ -n "$postgres_password" ] && [ -n "$redis_password" ] && [ -n "$clickhouse_password" ]; then
        # Create temporary environment file for deployment
        cat > "/tmp/openbao_secrets.env" << EOF
POSTGRES_PASSWORD=$postgres_password
REDIS_PASSWORD=$redis_password
CLICKHOUSE_PASSWORD=$clickhouse_password
VAULT_TOKEN=$VAULT_TOKEN
MGMT_SECRET_KEY=$mgmt_secret
MGMT_JWT_SECRET_KEY=$mgmt_jwt_secret
POSTGRES_USER=dotmac_admin
ENVIRONMENT=development
APP_VERSION=1.0.0
EOF
        
        log "SUCCESS" "Secrets exported to /tmp/openbao_secrets.env"
        echo ""
        echo "🚀 Ready to deploy with OpenBao secrets:"
        echo "source /tmp/openbao_secrets.env && ./deploy-layered-observability.sh deploy"
        return 0
    else
        log "ERROR" "Failed to retrieve secrets from OpenBao"
        return 1
    fi
}

# Main function
main() {
    echo "🔐 OpenBao Secrets Setup for Layered Observability"
    echo "=================================================="
    echo ""
    
    case "${1:-setup}" in
        "setup")
            wait_for_openbao || exit 1
            setup_layer_secrets || exit 1
            validate_secrets || exit 1
            ;;
            
        "validate")
            wait_for_openbao || exit 1
            validate_secrets || exit 1
            ;;
            
        "export")
            wait_for_openbao || exit 1
            export_secrets_as_env || exit 1
            ;;
            
        "get")
            wait_for_openbao || exit 1
            if [ -z "${2:-}" ] || [ -z "${3:-}" ]; then
                echo "Usage: $0 get <path> <key>"
                echo "Example: $0 get secret/dotmac/e0a postgres_password"
                exit 1
            fi
            value=$(get_secret "$2" "$3")
            if [ -n "$value" ] && [ "$value" != "null" ]; then
                echo "$value"
            else
                log "ERROR" "Secret not found: $2/$3"
                exit 1
            fi
            ;;
            
        "help"|"-h"|"--help")
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  setup     Setup all layer secrets in OpenBao (default)"
            echo "  validate  Validate that secrets exist"
            echo "  export    Export secrets as environment variables"
            echo "  get       Get specific secret: $0 get <path> <key>"
            echo "  help      Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  OPENBAO_ADDR          - OpenBao address (default: http://localhost:8200)"
            echo "  VAULT_TOKEN           - OpenBao root token"
            echo "  VAULT_PATH            - Base path for secrets (default: secret/dotmac)"
            echo ""
            echo "Optional Secrets (will be generated if not provided):"
            echo "  POSTGRES_PASSWORD     - PostgreSQL password"
            echo "  REDIS_PASSWORD        - Redis password"
            echo "  CLICKHOUSE_PASSWORD   - ClickHouse password"
            echo "  MGMT_SECRET_KEY       - Management platform secret"
            echo "  MGMT_JWT_SECRET_KEY   - JWT secret"
            ;;
            
        *)
            log "ERROR" "Unknown command: $1"
            log "INFO" "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Handle script interruption
trap 'log "WARNING" "Setup interrupted by user"; exit 1' INT TERM

# Execute main function
main "$@"