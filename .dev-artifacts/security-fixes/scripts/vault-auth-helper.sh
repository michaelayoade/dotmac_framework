#!/bin/bash
# Vault Authentication Helper for DotMac Services
# Provides common functions for Vault authentication and secret retrieval

set -e

# Configuration
VAULT_ADDR=${VAULT_ADDR:-http://openbao:8200}
VAULT_ROLE_ID_FILE=${VAULT_ROLE_ID_FILE:-/var/run/secrets/openbao/${SERVICE_NAME}-role-id}
VAULT_SECRET_ID_FILE=${VAULT_SECRET_ID_FILE:-/var/run/secrets/openbao/${SERVICE_NAME}-secret-id}
VAULT_TOKEN_FILE=/tmp/vault-token
MAX_RETRIES=5
RETRY_DELAY=2

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [VAULT-AUTH] $*" >&2
}

# Wait for Vault to be ready
wait_for_vault() {
    local retries=0
    log "Waiting for Vault to be ready at ${VAULT_ADDR}..."
    
    while [ $retries -lt $MAX_RETRIES ]; do
        if curl -s --max-time 5 "${VAULT_ADDR}/v1/sys/health" >/dev/null 2>&1; then
            log "✅ Vault is ready"
            return 0
        fi
        
        retries=$((retries + 1))
        log "⏳ Vault not ready, attempt ${retries}/${MAX_RETRIES}"
        sleep $RETRY_DELAY
    done
    
    log "❌ Vault failed to become ready after ${MAX_RETRIES} attempts"
    return 1
}

# Authenticate with Vault using AppRole
vault_authenticate() {
    wait_for_vault || return 1
    
    if [ ! -f "$VAULT_ROLE_ID_FILE" ]; then
        log "❌ Role ID file not found: $VAULT_ROLE_ID_FILE"
        return 1
    fi
    
    if [ ! -f "$VAULT_SECRET_ID_FILE" ]; then
        log "❌ Secret ID file not found: $VAULT_SECRET_ID_FILE"
        return 1
    fi
    
    local role_id=$(cat "$VAULT_ROLE_ID_FILE")
    local secret_id=$(cat "$VAULT_SECRET_ID_FILE")
    
    if [ -z "$role_id" ] || [ -z "$secret_id" ]; then
        log "❌ Role ID or Secret ID is empty"
        return 1
    fi
    
    log "🔐 Authenticating with Vault using AppRole..."
    
    local response=$(curl -s --max-time 10 \
        -X POST \
        -d "{\"role_id\":\"${role_id}\",\"secret_id\":\"${secret_id}\"}" \
        "${VAULT_ADDR}/v1/auth/approle/login")
    
    if [ $? -ne 0 ]; then
        log "❌ Failed to connect to Vault for authentication"
        return 1
    fi
    
    local token=$(echo "$response" | jq -r '.auth.client_token // empty')
    
    if [ -z "$token" ] || [ "$token" = "null" ]; then
        log "❌ Failed to get Vault token"
        log "Response: $response"
        return 1
    fi
    
    echo "$token" > "$VAULT_TOKEN_FILE"
    log "✅ Successfully authenticated with Vault"
    echo "$token"
}

# Get secret from Vault KV store
get_kv_secret() {
    local path="$1"
    local key="$2"
    
    if [ -z "$path" ]; then
        log "❌ Secret path is required"
        return 1
    fi
    
    local token
    if [ -f "$VAULT_TOKEN_FILE" ]; then
        token=$(cat "$VAULT_TOKEN_FILE")
    else
        token=$(vault_authenticate) || return 1
    fi
    
    log "📥 Retrieving secret from path: $path"
    
    local response=$(curl -s --max-time 10 \
        -H "X-Vault-Token: $token" \
        "${VAULT_ADDR}/v1/${path}")
    
    if [ $? -ne 0 ]; then
        log "❌ Failed to retrieve secret from Vault"
        return 1
    fi
    
    if [ -n "$key" ]; then
        echo "$response" | jq -r ".data.data.${key} // empty"
    else
        echo "$response" | jq -r '.data.data'
    fi
}

# Get database credentials from Vault
get_database_credentials() {
    local role="$1"
    
    if [ -z "$role" ]; then
        log "❌ Database role is required"
        return 1
    fi
    
    local token
    if [ -f "$VAULT_TOKEN_FILE" ]; then
        token=$(cat "$VAULT_TOKEN_FILE")
    else
        token=$(vault_authenticate) || return 1
    fi
    
    log "🔑 Getting database credentials for role: $role"
    
    local response=$(curl -s --max-time 10 \
        -H "X-Vault-Token: $token" \
        "${VAULT_ADDR}/v1/database/creds/${role}")
    
    if [ $? -ne 0 ]; then
        log "❌ Failed to retrieve database credentials"
        return 1
    fi
    
    local username=$(echo "$response" | jq -r '.data.username // empty')
    local password=$(echo "$response" | jq -r '.data.password // empty')
    
    if [ -z "$username" ] || [ -z "$password" ]; then
        log "❌ Failed to parse database credentials"
        log "Response: $response"
        return 1
    fi
    
    log "✅ Successfully retrieved database credentials for user: $username"
    
    # Export as environment variables
    export VAULT_DB_USERNAME="$username"
    export VAULT_DB_PASSWORD="$password"
    
    # Also output as JSON for scripts that prefer it
    jq -n \
        --arg username "$username" \
        --arg password "$password" \
        '{username: $username, password: $password}'
}

# Renew Vault token
renew_vault_token() {
    local token
    if [ -f "$VAULT_TOKEN_FILE" ]; then
        token=$(cat "$VAULT_TOKEN_FILE")
    else
        log "❌ No token file found for renewal"
        return 1
    fi
    
    log "🔄 Renewing Vault token..."
    
    local response=$(curl -s --max-time 10 \
        -X POST \
        -H "X-Vault-Token: $token" \
        "${VAULT_ADDR}/v1/auth/token/renew-self")
    
    if [ $? -ne 0 ]; then
        log "❌ Failed to renew Vault token"
        return 1
    fi
    
    log "✅ Vault token renewed successfully"
}

# Setup token renewal in background
setup_token_renewal() {
    local interval=${1:-3600}  # Default 1 hour
    
    log "⏰ Setting up token renewal every ${interval} seconds"
    
    (
        while true; do
            sleep "$interval"
            if ! renew_vault_token; then
                log "⚠️ Token renewal failed, re-authenticating..."
                vault_authenticate >/dev/null
            fi
        done
    ) &
    
    echo $! > /tmp/vault-renewal.pid
    log "✅ Token renewal background process started (PID: $(cat /tmp/vault-renewal.pid))"
}

# Generate connection string with Vault credentials
generate_clickhouse_connection() {
    local role="$1"
    local host="${2:-clickhouse}"
    local port="${3:-9000}"
    local database="${4:-signoz_traces}"
    
    log "🔗 Generating ClickHouse connection string for role: $role"
    
    local creds_json=$(get_database_credentials "$role")
    if [ $? -ne 0 ]; then
        log "❌ Failed to get database credentials"
        return 1
    fi
    
    local username=$(echo "$creds_json" | jq -r '.username')
    local password=$(echo "$creds_json" | jq -r '.password')
    
    echo "tcp://${username}:${password}@${host}:${port}/?database=${database}"
}

# Export functions for use in other scripts
export -f wait_for_vault
export -f vault_authenticate
export -f get_kv_secret
export -f get_database_credentials
export -f renew_vault_token
export -f setup_token_renewal
export -f generate_clickhouse_connection