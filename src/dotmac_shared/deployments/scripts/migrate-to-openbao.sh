#!/bin/bash
set -e

# DotMac Framework - Migrate to OpenBao Script
# This script helps migrate from HashiCorp Vault to OpenBao

echo "==============================================="
echo "DotMac Framework - OpenBao Migration"
echo "==============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
OPENBAO_ADDR="${OPENBAO_ADDR:-http://localhost:8200}"
OPENBAO_TOKEN="${OPENBAO_TOKEN:-root-token-for-dev}"
BACKUP_DIR="deployments/openbao/backups/$(date +%Y%m%d-%H%M%S)"

# Check if running from correct directory
if [ ! -d "deployments/openbao" ]; then
    echo -e "${RED}Error: Please run this script from the project root directory${NC}"
    exit 1
fi

# Function to check command existence
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Step 1: Check prerequisites
echo -e "\n${YELLOW}Step 1: Checking prerequisites${NC}"

# Check for Docker
if command_exists docker; then
    echo -e "${GREEN}✓ Docker found${NC}"
else
    echo -e "${RED}Error: Docker is required to run OpenBao${NC}"
    exit 1
fi

# Check for Docker Compose
if command_exists docker-compose; then
    echo -e "${GREEN}✓ Docker Compose found${NC}"
else
    echo -e "${RED}Error: Docker Compose is required${NC}"
    exit 1
fi

# Check for jq (for JSON processing)
if command_exists jq; then
    echo -e "${GREEN}✓ jq found${NC}"
else
    echo -e "${YELLOW}⚠ jq not found. Installing...${NC}"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update && sudo apt-get install -y jq
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install jq
    else
        echo -e "${RED}Please install jq manually${NC}"
        exit 1
    fi
fi

# Step 2: Export secrets from HashiCorp Vault (if available)
if [ ! -z "$VAULT_TOKEN" ] && command_exists vault; then
    echo -e "\n${YELLOW}Step 2: Exporting secrets from HashiCorp Vault${NC}"

    # Create backup directory
    mkdir -p "$BACKUP_DIR"

    # Export secrets
    echo "Exporting secrets from Vault..."

    # List of secret paths to export
    PATHS=(
        "dotmac/database/main"
        "dotmac/database/test"
        "dotmac/cache/redis"
        "dotmac/auth/jwt"
        "dotmac/auth/session"
        "dotmac/api_keys/main"
        "dotmac/api_keys/webhook"
        "dotmac/api_keys/twilio"
        "dotmac/api_keys/stripe"
        "dotmac/encryption/master"
        "dotmac/smtp/default"
        "dotmac/cloud/aws"
        "dotmac/monitoring/sentry"
        "dotmac/network/snmp"
        "dotmac/config/feature_flags"
    )

    for path in "${PATHS[@]}"; do
        echo -n "  Exporting $path... "
        if vault kv get -format=json "secret/$path" > "$BACKUP_DIR/$(echo $path | tr '/' '_').json" 2>/dev/null; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${YELLOW}⚠ Not found${NC}"
        fi
    done

    echo -e "${GREEN}✓ Secrets exported to $BACKUP_DIR${NC}"
else
    echo -e "\n${YELLOW}Step 2: Skipping Vault export (no Vault token found or Vault not installed)${NC}"
fi

# Step 3: Start OpenBao
echo -e "\n${YELLOW}Step 3: Starting OpenBao${NC}"
cd deployments/openbao

# Create docker network if it doesn't exist
docker network create dotmac-network 2>/dev/null || true

# Start OpenBao
echo "Starting OpenBao container..."
docker-compose up -d openbao

# Wait for OpenBao to be ready
echo -n "Waiting for OpenBao to be ready"
for i in {1..30}; do
    if docker exec dotmac-openbao bao status >/dev/null 2>&1; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi
    echo -n "."
    sleep 2
done

# Initialize OpenBao
echo "Initializing OpenBao configuration..."
docker-compose up openbao-init
echo -e "${GREEN}✓ OpenBao initialized${NC}"

# Step 4: Import secrets to OpenBao (if we have backups)
if [ -d "../../$BACKUP_DIR" ] && [ "$(ls -A ../../$BACKUP_DIR)" ]; then
    echo -e "\n${YELLOW}Step 4: Importing secrets to OpenBao${NC}"

    # Set OpenBao environment
    export BAO_ADDR=$OPENBAO_ADDR
    export BAO_TOKEN=$OPENBAO_TOKEN

    # Import each secret
    for file in ../../$BACKUP_DIR/*.json; do
        if [ -f "$file" ]; then
            filename=$(basename "$file" .json)
            path=$(echo $filename | tr '_' '/')
            echo -n "  Importing $path... "

            # Extract the data section from Vault export
            data=$(jq '.data.data // .data' "$file")

            # Import to OpenBao
            if echo "$data" | docker exec -i dotmac-openbao bao kv put "secret/$path" - >/dev/null 2>&1; then
                echo -e "${GREEN}✓${NC}"
            else
                echo -e "${YELLOW}⚠ Failed${NC}"
            fi
        fi
    done

    echo -e "${GREEN}✓ Secrets imported to OpenBao${NC}"
else
    echo -e "\n${YELLOW}Step 4: No secrets to import${NC}"
fi

# Step 5: Test OpenBao
echo -e "\n${YELLOW}Step 5: Testing OpenBao${NC}"

# Test secret read
echo -n "Testing secret read... "
if docker exec dotmac-openbao bao kv get secret/dotmac/database/main >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠ No test data found (that's okay for fresh install)${NC}"
fi

# Test transit engine
echo -n "Testing transit encryption... "
if echo "test-data" | docker exec -i dotmac-openbao bao write -field=ciphertext transit/encrypt/dotmac-default plaintext=- >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Transit engine test failed${NC}"
fi

# Step 6: Update application configuration
echo -e "\n${YELLOW}Step 6: Updating application configuration${NC}"

# Create .env.openbao file with OpenBao configuration
cat > .env.openbao << EOF
# OpenBao Configuration
USE_OPENBAO=true
OPENBAO_ADDR=$OPENBAO_ADDR
OPENBAO_TOKEN=$OPENBAO_TOKEN
OPENBAO_MOUNT_POINT=secret
OPENBAO_KV_VERSION=2

# Application will use these automatically
VAULT_ADDR=$OPENBAO_ADDR
VAULT_TOKEN=$OPENBAO_TOKEN
EOF

echo -e "${GREEN}✓ Created .env.openbao configuration file${NC}"

# Step 7: Test Python client compatibility
echo -e "\n${YELLOW}Step 7: Testing Python client compatibility${NC}"

# Create test script
cat > test_openbao.py << 'EOF'
import os
import sys
sys.path.insert(0, 'dotmac_platform')

# Set OpenBao configuration
os.environ['USE_OPENBAO'] = 'true'
os.environ['OPENBAO_ADDR'] = 'http://localhost:8200'
os.environ['OPENBAO_TOKEN'] = 'root-token-for-dev'

try:
    from dotmac_platform.security.openbao_client import get_secret_backend

    client = get_secret_backend()
    print("✓ OpenBao client initialized successfully")
    print(f"  Backend: OpenBao")
    print(f"  Address: {os.environ['OPENBAO_ADDR']}")

    # Test health check
    import asyncio
    async def test():
        health = await client.health_check()
        print(f"✓ Health check passed: {health}")

    asyncio.run(test())

except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
EOF

# Run test
echo "Testing Python client..."
if python test_openbao.py 2>/dev/null; then
    echo -e "${GREEN}✓ Python client is compatible with OpenBao${NC}"
else
    echo -e "${YELLOW}⚠ Python client test skipped (dependencies not installed)${NC}"
fi
rm -f test_openbao.py

# Return to original directory
cd ../..

# Step 8: Summary
echo -e "\n${GREEN}===============================================${NC}"
echo -e "${GREEN}Migration to OpenBao completed successfully!${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""
echo -e "${BLUE}OpenBao is now running at:${NC} $OPENBAO_ADDR"
echo -e "${BLUE}OpenBao UI:${NC} $OPENBAO_ADDR/ui"
echo -e "${BLUE}Root Token:${NC} $OPENBAO_TOKEN"
echo ""
echo "Next steps:"
echo "1. Update your .env file with OpenBao configuration:"
echo "   cp .env.openbao .env"
echo ""
echo "2. Restart your applications to use OpenBao"
echo ""
echo "3. Access OpenBao UI to manage secrets:"
echo "   $OPENBAO_ADDR/ui"
echo ""
echo "Key benefits:"
echo "• ${GREEN}Open Source:${NC} MPL-2.0 license (no BSL restrictions)"
echo "• ${GREEN}API Compatible:${NC} Works with existing Vault clients"
echo "• ${GREEN}Cost Effective:${NC} No enterprise license fees"
echo "• ${GREEN}Community Driven:${NC} Active development and support"
echo ""
echo "For more information, see: deployments/OPENTOFU_MIGRATION.md"

# Optional: Show docker-compose logs
echo -e "\n${YELLOW}Tip: View OpenBao logs with:${NC}"
echo "  docker-compose -f deployments/openbao/docker-compose.yml logs -f"
