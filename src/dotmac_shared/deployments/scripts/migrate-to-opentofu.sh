#!/bin/bash
set -e

# DotMac Framework - Migrate to OpenTofu Script
# This script helps migrate from Terraform to OpenTofu

echo "==============================================="
echo "DotMac Framework - OpenTofu Migration"
echo "==============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running from correct directory
if [ ! -f "deployments/terraform/main.tf" ]; then
    echo -e "${RED}Error: Please run this script from the project root directory${NC}"
    exit 1
fi

# Function to check command existence
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Step 1: Check for existing Terraform installation
echo -e "\n${YELLOW}Step 1: Checking existing Terraform setup${NC}"
if command_exists terraform; then
    TERRAFORM_VERSION=$(terraform version -json | jq -r '.terraform_version' 2>/dev/null || terraform version | head -n1 | cut -d' ' -f2)
    echo -e "${GREEN}✓ Terraform ${TERRAFORM_VERSION} found${NC}"

    # Check for existing state
    if [ -f "deployments/terraform/terraform.tfstate" ]; then
        echo -e "${YELLOW}⚠ Found existing Terraform state file${NC}"
        echo "  Creating backup..."
        cp deployments/terraform/terraform.tfstate deployments/terraform/terraform.tfstate.backup.$(date +%Y%m%d-%H%M%S)
        echo -e "${GREEN}✓ Backup created${NC}"
    fi
else
    echo "ℹ Terraform not found (that's okay, we're migrating to OpenTofu)"
fi

# Step 2: Install OpenTofu
echo -e "\n${YELLOW}Step 2: Installing OpenTofu${NC}"
if command_exists tofu; then
    TOFU_VERSION=$(tofu version -json | jq -r '.terraform_version' 2>/dev/null || tofu version | head -n1 | cut -d' ' -f2)
    echo -e "${GREEN}✓ OpenTofu ${TOFU_VERSION} already installed${NC}"
else
    echo "Installing OpenTofu..."

    # Detect OS
    OS="$(uname -s)"
    case "${OS}" in
        Linux*)
            echo "Detected Linux"
            # Download and install OpenTofu
            TOFU_VERSION="1.6.0"
            curl -Lo tofu.tar.gz "https://github.com/opentofu/opentofu/releases/download/v${TOFU_VERSION}/tofu_${TOFU_VERSION}_linux_amd64.tar.gz"
            tar -xzf tofu.tar.gz
            sudo mv tofu /usr/local/bin/
            rm tofu.tar.gz
            ;;
        Darwin*)
            echo "Detected macOS"
            if command_exists brew; then
                brew install opentofu
            else
                echo -e "${RED}Error: Homebrew not found. Please install Homebrew or OpenTofu manually${NC}"
                exit 1
            fi
            ;;
        *)
            echo -e "${RED}Error: Unsupported OS: ${OS}${NC}"
            echo "Please install OpenTofu manually from: https://opentofu.org/docs/intro/install/"
            exit 1
            ;;
    esac

    if command_exists tofu; then
        echo -e "${GREEN}✓ OpenTofu installed successfully${NC}"
    else
        echo -e "${RED}Error: OpenTofu installation failed${NC}"
        exit 1
    fi
fi

# Step 3: Initialize OpenTofu
echo -e "\n${YELLOW}Step 3: Initializing OpenTofu${NC}"
cd deployments/terraform

# Remove Terraform lock file if exists (will be regenerated)
if [ -f ".terraform.lock.hcl" ]; then
    echo "Removing old Terraform lock file..."
    rm .terraform.lock.hcl
fi

# Initialize OpenTofu
echo "Running: tofu init"
if tofu init; then
    echo -e "${GREEN}✓ OpenTofu initialized successfully${NC}"
else
    echo -e "${RED}Error: OpenTofu initialization failed${NC}"
    exit 1
fi

# Step 4: Validate configuration
echo -e "\n${YELLOW}Step 4: Validating configuration${NC}"
if tofu validate; then
    echo -e "${GREEN}✓ Configuration is valid${NC}"
else
    echo -e "${RED}Error: Configuration validation failed${NC}"
    exit 1
fi

# Step 5: Plan infrastructure
echo -e "\n${YELLOW}Step 5: Planning infrastructure${NC}"
echo "Running: tofu plan"
if [ -f "production.tfvars" ]; then
    tofu plan -var-file="production.tfvars" -out=opentofu.plan
else
    tofu plan -out=opentofu.plan
fi

# Step 6: Migration summary
echo -e "\n${GREEN}===============================================${NC}"
echo -e "${GREEN}Migration to OpenTofu completed successfully!${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""
echo "Next steps:"
echo "1. Review the plan output above"
echo "2. Apply changes with: tofu apply opentofu.plan"
echo "3. Update CI/CD pipelines to use 'tofu' instead of 'terraform'"
echo ""
echo "Key changes:"
echo "• Command: terraform → tofu"
echo "• State files: Fully compatible (no changes needed)"
echo "• Providers: All existing providers work with OpenTofu"
echo "• License: BSL → MPL-2.0 (truly open source)"
echo ""
echo "For more information, see: deployments/OPENTOFU_MIGRATION.md"

# Return to original directory
cd ../../

# Optional: Create alias for transition period
echo -e "\n${YELLOW}Tip: You can create an alias for the transition period:${NC}"
echo "  alias terraform='tofu'"
echo "  Add this to your ~/.bashrc or ~/.zshrc file"
