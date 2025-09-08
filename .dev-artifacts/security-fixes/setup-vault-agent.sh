#!/bin/sh

# Setup Vault Agent for SigNoz services
set -e

echo "Setting up Vault Agent credentials for SigNoz..."

export BAO_ADDR="http://localhost:8200"
export BAO_TOKEN="gate-e0a-root-token"

# Create AppRole for SigNoz services
echo "Creating AppRole for signoz-services..."
bao auth enable -path=signoz-approle approle 2>/dev/null || echo "AppRole already enabled"

# Create policy for SigNoz services
cat > /tmp/signoz-policy.hcl << 'EOF'
# Allow reading ClickHouse credentials
path "dotmac/clickhouse" {
  capabilities = ["read"]
}

# Allow reading ISP database/redis credentials  
path "dotmac/isp" {
  capabilities = ["read"]
}
EOF

bao policy write signoz-services /tmp/signoz-policy.hcl

# Create AppRole
bao write auth/signoz-approle/role/signoz-services \
    token_policies="signoz-services" \
    token_ttl=1h \
    token_max_ttl=4h \
    bind_secret_id=true

# Get role ID
ROLE_ID=$(bao read -field=role_id auth/signoz-approle/role/signoz-services/role-id)
echo "Role ID: $ROLE_ID"

# Generate secret ID
SECRET_ID=$(bao write -field=secret_id auth/signoz-approle/role/signoz-services/secret-id)
echo "Secret ID generated"

# Create vault-auth volume directory if it doesn't exist
mkdir -p vault-auth

# Write credentials to files
echo "$ROLE_ID" > vault-auth/role_id
echo "$SECRET_ID" > vault-auth/secret_id
chmod 600 vault-auth/role_id vault-auth/secret_id

echo "Vault Agent setup complete!"
echo "Role ID saved to: vault-auth/role_id"
echo "Secret ID saved to: vault-auth/secret_id"

# Test authentication
echo "Testing Vault Agent authentication..."
AGENT_TOKEN=$(bao write -field=token auth/signoz-approle/login \
    role_id="$ROLE_ID" \
    secret_id="$SECRET_ID")

if [ -n "$AGENT_TOKEN" ]; then
    echo "✅ Vault Agent authentication test successful"
else
    echo "❌ Vault Agent authentication test failed"
    exit 1
fi

# Test secret access
echo "Testing secret access..."
BAO_TOKEN="$AGENT_TOKEN" bao kv get dotmac/clickhouse >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ ClickHouse secrets accessible"
else
    echo "❌ ClickHouse secrets not accessible"
    exit 1
fi

echo "All tests passed! Ready to start Vault Agent services."