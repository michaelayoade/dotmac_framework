#!/bin/bash
# Initialize OpenBao with all DotMac platform secrets
# Replaces hardcoded secrets with dynamic secret management

set -e

echo "🔐 Initializing OpenBao for DotMac Platform..."

# Wait for OpenBao to be ready
until bao status > /dev/null 2>&1; do
    echo "Waiting for OpenBao to be ready..."
    sleep 2
done

echo "✓ OpenBao is ready"

# Enable required secret engines
echo "Enabling secret engines..."

# KV v2 for static secrets
bao secrets enable -path=dotmac kv-v2 || echo "KV engine already enabled"

# Database secrets engine for dynamic credentials
bao secrets enable -path=database database || echo "Database engine already enabled"

# PKI for certificate management
bao secrets enable -path=pki pki || echo "PKI engine already enabled"

# Transit for encryption as a service
bao secrets enable -path=transit transit || echo "Transit engine already enabled"

# TOTP for MFA
bao secrets enable totp || echo "TOTP engine already enabled"

echo "✓ Secret engines enabled"

# Configure database connections for dynamic secrets
echo "Configuring database dynamic secrets..."

bao write database/config/postgresql \
    plugin_name=postgresql-database-plugin \
    allowed_roles="*" \
    connection_url="postgresql://{{username}}:{{password}}@postgres:5432/dotmac_db?sslmode=disable" \
    username="${POSTGRES_ADMIN_USER:-postgres}" \
    password="${POSTGRES_ADMIN_PASSWORD:-postgres123}"

# Create database roles for each service
for service in identity billing services networking analytics core_ops core_events platform devtools api_gateway; do
    bao write database/roles/${service} \
        db_name=postgresql \
        creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}' IN ROLE dotmac_${service}_role;" \
        default_ttl="1h" \
        max_ttl="24h"
done

echo "✓ Database dynamic secrets configured"

# Store static application secrets
echo "Storing application secrets..."

# JWT signing keys
bao kv put dotmac/jwt \
    secret_key="$(openssl rand -base64 64)" \
    algorithm="HS256" \
    issuer="dotmac-platform" \
    audience="dotmac-services"

# Service-specific secrets
for service in identity billing services networking analytics core_ops core_events platform devtools api_gateway; do
    bao kv put dotmac/${service} \
        service_key="$(openssl rand -base64 32)" \
        api_key="$(uuidgen)" \
        encryption_key="$(openssl rand -base64 32)"
done

# Redis credentials
bao kv put dotmac/redis \
    password="$(openssl rand -base64 32)" \
    max_connections="100" \
    timeout="30"

# SignOz/OTEL configuration
bao kv put dotmac/observability \
    signoz_endpoint="${SIGNOZ_ENDPOINT:-localhost:4317}" \
    signoz_access_token="$(uuidgen)" \
    trace_sampling_rate="0.1" \
    metrics_export_interval="30"

# External API keys (placeholders - update with real values)
bao kv put dotmac/external \
    stripe_secret_key="${STRIPE_SECRET_KEY:-sk_test_placeholder}" \
    sendgrid_api_key="${SENDGRID_API_KEY:-SG.placeholder}" \
    twilio_auth_token="${TWILIO_AUTH_TOKEN:-placeholder}" \
    aws_access_key_id="${AWS_ACCESS_KEY_ID:-placeholder}" \
    aws_secret_access_key="${AWS_SECRET_ACCESS_KEY:-placeholder}"

# Encryption keys for data at rest
bao kv put dotmac/encryption \
    master_key="$(openssl rand -base64 32)" \
    data_key="$(openssl rand -base64 32)" \
    backup_key="$(openssl rand -base64 32)"

echo "✓ Application secrets stored"

# Create policies for services
echo "Creating access policies..."

# Admin policy
cat > /tmp/admin-policy.hcl <<EOF
# Admin policy - full access
path "*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}
EOF
bao policy write admin /tmp/admin-policy.hcl

# Service policy template
for service in identity billing services networking analytics core_ops core_events platform devtools api_gateway; do
    cat > /tmp/${service}-policy.hcl <<EOF
# Policy for ${service} service
path "dotmac/data/${service}/*" {
  capabilities = ["read", "list"]
}

path "dotmac/data/jwt" {
  capabilities = ["read"]
}

path "dotmac/data/redis" {
  capabilities = ["read"]
}

path "dotmac/data/observability" {
  capabilities = ["read"]
}

path "database/creds/${service}" {
  capabilities = ["read"]
}

path "transit/encrypt/dotmac" {
  capabilities = ["update"]
}

path "transit/decrypt/dotmac" {
  capabilities = ["update"]
}

path "auth/token/renew-self" {
  capabilities = ["update"]
}
EOF
    bao policy write ${service} /tmp/${service}-policy.hcl
done

echo "✓ Access policies created"

# Enable AppRole authentication
echo "Configuring AppRole authentication..."

bao auth enable approle || echo "AppRole already enabled"

# Create AppRole for each service
for service in identity billing services networking analytics core_ops core_events platform devtools api_gateway; do
    # Create role
    bao write auth/approle/role/${service} \
        token_ttl=1h \
        token_max_ttl=4h \
        token_policies="${service}" \
        secret_id_ttl=24h \
        secret_id_num_uses=0

    # Get role ID
    role_id=$(bao read -field=role_id auth/approle/role/${service}/role-id)

    # Generate secret ID
    secret_id=$(bao write -field=secret_id -f auth/approle/role/${service}/secret-id)

    # Store in temporary file for service startup
    mkdir -p /var/run/secrets/openbao
    echo "${role_id}" > /var/run/secrets/openbao/${service}-role-id
    echo "${secret_id}" > /var/run/secrets/openbao/${service}-secret-id

    echo "✓ AppRole created for ${service}"
done

echo "✓ AppRole authentication configured"

# Configure transit encryption
echo "Configuring transit encryption..."

bao write -f transit/keys/dotmac type=aes256-gcm96
bao write transit/keys/dotmac/config min_decryption_version=1 min_encryption_version=1

echo "✓ Transit encryption configured"

# Setup audit logging
echo "Enabling audit logging..."

bao audit enable file file_path=/vault/logs/audit.log || echo "Audit already enabled"

echo "✓ Audit logging enabled"

# Create Kubernetes authentication (if in K8s)
if [ -n "${KUBERNETES_SERVICE_HOST}" ]; then
    echo "Configuring Kubernetes authentication..."

    bao auth enable kubernetes || echo "Kubernetes auth already enabled"

    bao write auth/kubernetes/config \
        kubernetes_host="https://${KUBERNETES_SERVICE_HOST}:${KUBERNETES_SERVICE_PORT}" \
        token_reviewer_jwt="$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)" \
        kubernetes_ca_cert="$(cat /var/run/secrets/kubernetes.io/serviceaccount/ca.crt)"

    # Create role for each service
    for service in identity billing services networking analytics core_ops core_events platform devtools api_gateway; do
        bao write auth/kubernetes/role/${service} \
            bound_service_account_names=${service} \
            bound_service_account_namespaces=dotmac \
            policies=${service} \
            ttl=1h
    done

    echo "✓ Kubernetes authentication configured"
fi

# Setup response wrapping for security
echo "Configuring response wrapping..."

bao write sys/wrapping/wrap \
    ttl=5m \
    max_ttl=1h

echo "✓ Response wrapping configured"

# Create backup policy
cat > /tmp/backup-policy.hcl <<EOF
# Backup policy for disaster recovery
path "sys/storage/raft/snapshot" {
  capabilities = ["read"]
}
EOF
bao policy write backup /tmp/backup-policy.hcl

# Generate backup token
backup_token=$(bao token create -policy=backup -ttl=24h -field=token)
echo "${backup_token}" > /var/run/secrets/openbao/backup-token

echo "✓ Backup configuration complete"

# Display summary
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  OpenBao Initialization Complete!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  Secret Engines Enabled:"
echo "    ✓ KV v2 (dotmac/)"
echo "    ✓ Database (dynamic PostgreSQL credentials)"
echo "    ✓ PKI (certificate management)"
echo "    ✓ Transit (encryption as a service)"
echo "    ✓ TOTP (multi-factor authentication)"
echo ""
echo "  Authentication Methods:"
echo "    ✓ Token"
echo "    ✓ AppRole (for services)"
if [ -n "${KUBERNETES_SERVICE_HOST}" ]; then
echo "    ✓ Kubernetes (for pods)"
fi
echo ""
echo "  Policies Created:"
echo "    ✓ Admin (full access)"
echo "    ✓ Service policies (10 services)"
echo "    ✓ Backup policy"
echo ""
echo "  Security Features:"
echo "    ✓ Audit logging enabled"
echo "    ✓ Response wrapping configured"
echo "    ✓ Transit encryption ready"
echo ""
echo "  Access OpenBao UI: http://localhost:8200"
echo "  Root Token: ${BAO_TOKEN}"
echo ""
echo "  ⚠️  IMPORTANT: Store the root token securely!"
echo "  ⚠️  Enable production mode before deployment!"
echo ""
echo "═══════════════════════════════════════════════════════════════"
