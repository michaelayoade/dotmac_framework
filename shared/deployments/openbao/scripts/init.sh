#!/bin/sh
set -e

echo "Initializing OpenBao for DotMac Framework..."

# Wait for OpenBao to be ready
until bao status 2>/dev/null; do
  echo "Waiting for OpenBao to be ready..."
  sleep 2
done

echo "OpenBao is ready. Configuring secrets engines and policies..."

# Enable KV v2 secrets engine
bao secrets enable -path=secret kv-v2 || true

# Enable Transit secrets engine for encryption
bao secrets enable transit || true

# Enable AppRole auth method
bao auth enable approle || true

# Enable Kubernetes auth method (for production)
bao auth enable kubernetes || true

# Create encryption key for transit engine
bao write -f transit/keys/dotmac-default || true

# Create initial secret structure
echo "Creating DotMac secret paths..."

# Database credentials
bao kv put secret/dotmac/database/main \
  host="${DB_HOST:-postgres}" \
  port="${DB_PORT:-5432}" \
  username="${DB_USER:-dotmac}" \
  password="${DB_PASSWORD:-changeme}" \
  database="${DB_NAME:-dotmac_core}" || true

# Redis credentials
bao kv put secret/dotmac/redis/main \
  host="${REDIS_HOST:-redis}" \
  port="${REDIS_PORT:-6379}" \
  password="${REDIS_PASSWORD:-}" || true

# JWT secrets
bao kv put secret/dotmac/auth/jwt \
  secret="${JWT_SECRET:-$(openssl rand -base64 32)}" \
  algorithm="HS256" \
  expiry="3600" || true

# API keys structure
bao kv put secret/dotmac/api_keys/internal \
  key="${INTERNAL_API_KEY:-$(uuidgen)}" || true

# SMTP configuration
bao kv put secret/dotmac/smtp/default \
  host="${SMTP_HOST:-smtp.gmail.com}" \
  port="${SMTP_PORT:-587}" \
  username="${SMTP_USER:-}" \
  password="${SMTP_PASSWORD:-}" \
  use_tls="true" || true

# Feature flags
bao kv put secret/dotmac/config/feature_flags \
  multi_tenant="true" \
  billing_enabled="true" \
  analytics_enabled="true" \
  realtime_updates="true" || true

# Cloud provider credentials (AWS)
bao kv put secret/dotmac/cloud/aws \
  access_key_id="${AWS_ACCESS_KEY_ID:-}" \
  secret_access_key="${AWS_SECRET_ACCESS_KEY:-}" \
  region="${AWS_REGION:-us-east-1}" || true

# Encryption keys
ENCRYPTION_KEY=$(openssl rand -base64 32)
bao kv put secret/dotmac/encryption/master \
  key="${ENCRYPTION_KEY}" || true

echo "Creating OpenBao policies..."

# Create read-only policy for applications
cat <<EOF | bao policy write dotmac-read -
path "secret/data/dotmac/*" {
  capabilities = ["read", "list"]
}

path "transit/encrypt/dotmac-default" {
  capabilities = ["update"]
}

path "transit/decrypt/dotmac-default" {
  capabilities = ["update"]
}
EOF

# Create admin policy
cat <<EOF | bao policy write dotmac-admin -
path "secret/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "transit/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "sys/*" {
  capabilities = ["read", "list"]
}

path "auth/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
EOF

# Create AppRole for applications
bao write auth/approle/role/dotmac-app \
  token_policies="dotmac-read" \
  token_ttl=1h \
  token_max_ttl=24h || true

# Get role ID and secret ID for applications
ROLE_ID=$(bao read -field=role_id auth/approle/role/dotmac-app/role-id)
SECRET_ID=$(bao write -field=secret_id -f auth/approle/role/dotmac-app/secret-id)

echo "============================================"
echo "OpenBao initialization complete!"
echo "============================================"
echo ""
echo "Configuration for your .env file:"
echo "VAULT_ADDR=http://localhost:8200"
echo "VAULT_TOKEN=${BAO_TOKEN}"
echo "VAULT_ROLE_ID=${ROLE_ID}"
echo "VAULT_SECRET_ID=${SECRET_ID}"
echo ""
echo "OpenBao UI available at: http://localhost:8200"
echo "Use token: ${BAO_TOKEN}"
echo "============================================"