#!/bin/bash
# DotMac Platform - Secure Environment Generator
# This script generates cryptographically secure environment variables

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}🔐 DotMac Platform - Secure Environment Generator${NC}"
echo "=================================================="
echo ""

# Check if OpenSSL is available
if ! command -v openssl &> /dev/null; then
    echo -e "${RED}❌ OpenSSL is required but not installed.${NC}"
    exit 1
fi

# Function to generate secure random string
generate_secure_string() {
    local length=$1
    openssl rand -base64 $length | tr -d "=+/" | cut -c1-${length}
}

# Function to generate JWT secret (64 characters)
generate_jwt_secret() {
    openssl rand -base64 48 | tr -d "\n"
}

# Function to generate database password (32 characters)
generate_db_password() {
    openssl rand -base64 24 | tr -d "\n"
}

# Function to generate Redis password (32 characters)
generate_redis_password() {
    openssl rand -base64 24 | tr -d "\n"
}

# Function to generate Vault token (36 characters)
generate_vault_token() {
    uuidgen | tr '[:upper:]' '[:lower:]'
}

# Function to generate encryption key (32 characters)
generate_encryption_key() {
    openssl rand -base64 24 | tr -d "\n"
}

# Environment type selection
echo -e "${YELLOW}Select environment type:${NC}"
echo "1) Development (less secure, longer tokens)"
echo "2) Production (highly secure, short tokens)"
echo ""
read -p "Enter choice (1 or 2): " env_choice

case $env_choice in
    1)
        ENV_TYPE="development"
        OUTPUT_FILE=".env"
        TEMPLATE_FILE=".env.development.template"
        ;;
    2)
        ENV_TYPE="production"
        OUTPUT_FILE=".env.production"
        TEMPLATE_FILE=".env.production.template"
        ;;
    *)
        echo -e "${RED}❌ Invalid choice. Exiting.${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}🔧 Generating secure environment for: ${ENV_TYPE}${NC}"
echo ""

# Check if output file exists
if [[ -f "$PROJECT_ROOT/$OUTPUT_FILE" ]]; then
    echo -e "${YELLOW}⚠️  File $OUTPUT_FILE already exists.${NC}"
    read -p "Overwrite? (y/N): " overwrite
    if [[ $overwrite != "y" && $overwrite != "Y" ]]; then
        echo -e "${YELLOW}Operation cancelled.${NC}"
        exit 0
    fi
fi

# Generate secure values
echo -e "${BLUE}🎲 Generating cryptographically secure secrets...${NC}"

JWT_SECRET=$(generate_jwt_secret)
POSTGRES_PASSWORD=$(generate_db_password)
REDIS_PASSWORD=$(generate_redis_password)
VAULT_TOKEN=$(generate_vault_token)
ENCRYPTION_KEY=$(generate_encryption_key)
CLICKHOUSE_PASSWORD=$(generate_db_password)
MINIO_ACCESS_KEY=$(generate_secure_string 20)
MINIO_SECRET_KEY=$(generate_encryption_key)
MGMT_SECRET_KEY=$(generate_encryption_key)
MGMT_JWT_SECRET_KEY=$(generate_jwt_secret)

echo -e "${GREEN}✅ Generated JWT secret (64+ chars)${NC}"
echo -e "${GREEN}✅ Generated database password (32+ chars)${NC}"
echo -e "${GREEN}✅ Generated Redis password (32+ chars)${NC}"
echo -e "${GREEN}✅ Generated Vault token (UUID)${NC}"
echo -e "${GREEN}✅ Generated encryption key (32+ chars)${NC}"
echo -e "${GREEN}✅ Generated ClickHouse password (32+ chars)${NC}"
echo -e "${GREEN}✅ Generated MinIO access key (20+ chars)${NC}"
echo -e "${GREEN}✅ Generated MinIO secret key (32+ chars)${NC}"
echo -e "${GREEN}✅ Generated Management Platform secret key (32+ chars)${NC}"
echo -e "${GREEN}✅ Generated Management Platform JWT secret (64+ chars)${NC}"

# Copy template and replace placeholders
echo ""
echo -e "${BLUE}📝 Creating environment file...${NC}"

if [[ ! -f "$PROJECT_ROOT/$TEMPLATE_FILE" ]]; then
    echo -e "${RED}❌ Template file $TEMPLATE_FILE not found.${NC}"
    exit 1
fi

# Create temporary replacements file
TEMP_REPLACEMENTS=$(mktemp)
cat > "$TEMP_REPLACEMENTS" << EOF
REPLACE_WITH_SECURE_64_CHAR_RANDOM_STRING=$JWT_SECRET
REPLACE_WITH_SECURE_DB_PASSWORD=$POSTGRES_PASSWORD
REPLACE_WITH_SECURE_REDIS_PASSWORD=$REDIS_PASSWORD
REPLACE_WITH_VAULT_TOKEN=$VAULT_TOKEN
REPLACE_WITH_32_CHAR_ENCRYPTION_KEY=$ENCRYPTION_KEY
REPLACE_WITH_CLICKHOUSE_PASSWORD=$CLICKHOUSE_PASSWORD
REPLACE_WITH_MINIO_ACCESS_KEY=$MINIO_ACCESS_KEY
REPLACE_WITH_MINIO_SECRET_KEY=$MINIO_SECRET_KEY
REPLACE_WITH_MGMT_SECRET_KEY=$MGMT_SECRET_KEY
REPLACE_WITH_MGMT_JWT_SECRET_KEY=$MGMT_JWT_SECRET_KEY
EOF

# Use Python script to replace placeholders (handles special characters properly)
python3 "$SCRIPT_DIR/create-env-from-template.py" "$PROJECT_ROOT/$TEMPLATE_FILE" "$PROJECT_ROOT/$OUTPUT_FILE" "$TEMP_REPLACEMENTS"

# Clean up temporary file
rm -f "$TEMP_REPLACEMENTS"

echo -e "${GREEN}✅ Environment file created: $OUTPUT_FILE${NC}"
echo -e "${GREEN}✅ File permissions set to 600 (owner read/write only)${NC}"

# Security warnings
echo ""
echo -e "${RED}🚨 SECURITY WARNINGS:${NC}"
echo -e "${YELLOW}1. Never commit $OUTPUT_FILE to version control${NC}"
echo -e "${YELLOW}2. Store secrets securely (use a password manager for production)${NC}"
echo -e "${YELLOW}3. Rotate secrets regularly (monthly for production)${NC}"
echo -e "${YELLOW}4. Use environment-specific secrets (don't reuse between dev/prod)${NC}"
echo ""

# Additional production warnings
if [[ $env_choice == "2" ]]; then
    echo -e "${RED}🔒 PRODUCTION ADDITIONAL STEPS:${NC}"
    echo -e "${YELLOW}1. Update CORS_ORIGINS with your actual domain(s)${NC}"
    echo -e "${YELLOW}2. Update ALLOWED_HOSTS with your actual domain(s)${NC}"
    echo -e "${YELLOW}3. Configure SSL/TLS certificates${NC}"
    echo -e "${YELLOW}4. Set up monitoring and alerting${NC}"
    echo -e "${YELLOW}5. Configure external services (Stripe, email, etc.)${NC}"
    echo ""
fi

# Save secrets securely (optional)
echo -e "${BLUE}💾 Save secrets to secure file? (recommended for production)${NC}"
read -p "Create secrets backup file? (y/N): " save_secrets

if [[ $save_secrets == "y" || $save_secrets == "Y" ]]; then
    SECRETS_FILE="$PROJECT_ROOT/secrets-backup-$(date +%Y%m%d-%H%M%S).txt"
    cat > "$SECRETS_FILE" << EOF
# DotMac Platform Secrets Backup
# Generated on: $(date)
# Environment: $ENV_TYPE
# 
# Store this file securely and delete after use
# Never commit this file to version control

JWT_SECRET=$JWT_SECRET
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
REDIS_PASSWORD=$REDIS_PASSWORD
VAULT_TOKEN=$VAULT_TOKEN
ENCRYPTION_KEY=$ENCRYPTION_KEY
CLICKHOUSE_PASSWORD=$CLICKHOUSE_PASSWORD
MINIO_ACCESS_KEY=$MINIO_ACCESS_KEY
MINIO_SECRET_KEY=$MINIO_SECRET_KEY
MGMT_SECRET_KEY=$MGMT_SECRET_KEY
MGMT_JWT_SECRET_KEY=$MGMT_JWT_SECRET_KEY
EOF
    chmod 600 "$SECRETS_FILE"
    echo -e "${GREEN}✅ Secrets backup saved to: $SECRETS_FILE${NC}"
    echo -e "${YELLOW}⚠️  Remember to delete this file after storing secrets securely${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Secure environment generation complete!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "1. Review and customize $OUTPUT_FILE"
echo -e "2. Test the environment: ${YELLOW}make up${NC}"
echo -e "3. Run security validation: ${YELLOW}make security-check${NC}"
echo ""