#!/bin/bash
# GitHub Secrets Setup Script
# Helps you configure repository secrets for CI/CD pipeline

set -e

echo "🔐 DotMac Framework - GitHub Secrets Setup"
echo "=========================================="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ GitHub CLI (gh) is not installed${NC}"
    echo "Please install it from: https://cli.github.com/"
    echo
    echo -e "${BLUE}Alternative: Set secrets manually via GitHub web interface${NC}"
    echo "See: .dev-artifacts/scripts/setup_github_secrets.md"
    exit 1
fi

# Check if user is authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${RED}❌ Not authenticated with GitHub${NC}"
    echo "Please run: gh auth login"
    exit 1
fi

echo -e "${GREEN}✅ GitHub CLI is installed and authenticated${NC}"
echo

# Get repository info
REPO_INFO=$(gh repo view --json nameWithOwner,defaultBranchRef -q '{owner: .nameWithOwner, branch: .defaultBranchRef.name}')
REPO_NAME=$(echo "$REPO_INFO" | jq -r '.owner')
BRANCH_NAME=$(echo "$REPO_INFO" | jq -r '.branch')

echo "📋 Repository: $REPO_NAME"
echo "🌿 Default branch: $BRANCH_NAME"
echo

# Function to set secret with validation
set_secret() {
    local secret_name=$1
    local description=$2
    local validation_pattern=$3
    local example=$4
    
    echo -e "${BLUE}Setting: $secret_name${NC}"
    echo "Description: $description"
    echo "Example: $example"
    echo
    
    while true; do
        if [[ "$secret_name" == "AUTH_INITIAL_ADMIN_PASSWORD" ]]; then
            # Use secure input for password
            echo -n "Enter value (hidden): "
            read -s secret_value
            echo
        else
            echo -n "Enter value: "
            read secret_value
        fi
        
        # Basic validation
        if [[ -n "$validation_pattern" ]]; then
            if [[ ! "$secret_value" =~ $validation_pattern ]]; then
                echo -e "${RED}❌ Invalid format. Please try again.${NC}"
                continue
            fi
        fi
        
        if [[ -n "$secret_value" ]]; then
            break
        else
            echo -e "${RED}❌ Value cannot be empty. Please try again.${NC}"
        fi
    done
    
    # Set the secret
    if echo "$secret_value" | gh secret set "$secret_name"; then
        echo -e "${GREEN}✅ Successfully set $secret_name${NC}"
    else
        echo -e "${RED}❌ Failed to set $secret_name${NC}"
        return 1
    fi
    
    echo
}

# Set required secrets
echo -e "${YELLOW}📝 Setting up required secrets...${NC}"
echo

# AUTH_ADMIN_EMAIL
set_secret "AUTH_ADMIN_EMAIL" \
    "Email address for initial admin user" \
    "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$" \
    "admin@yourdomain.com"

# AUTH_INITIAL_ADMIN_PASSWORD
set_secret "AUTH_INITIAL_ADMIN_PASSWORD" \
    "Secure password for initial admin user (min 12 chars)" \
    "^.{12,}$" \
    "SecureAdm1n!Pass2024"

echo -e "${BLUE}ℹ️ Coverage Reporting${NC}"
echo "Coverage reports are now handled natively by GitHub Actions:"
echo "  ✅ PR comments with coverage summaries"  
echo "  ✅ Workflow artifacts with HTML reports"
echo "  ✅ No external services required"
echo
echo -e "${YELLOW}Note: Codecov is no longer required for this setup${NC}"

echo
echo -e "${GREEN}🎉 Secret setup complete!${NC}"
echo

# Verify secrets
echo -e "${BLUE}📋 Verifying secrets...${NC}"
echo "The following secrets are now configured:"

if gh secret list | grep -q "AUTH_ADMIN_EMAIL"; then
    echo -e "  ${GREEN}✅ AUTH_ADMIN_EMAIL${NC}"
else
    echo -e "  ${RED}❌ AUTH_ADMIN_EMAIL${NC}"
fi

if gh secret list | grep -q "AUTH_INITIAL_ADMIN_PASSWORD"; then
    echo -e "  ${GREEN}✅ AUTH_INITIAL_ADMIN_PASSWORD${NC}"
else
    echo -e "  ${RED}❌ AUTH_INITIAL_ADMIN_PASSWORD${NC}"
fi

echo -e "  ${GREEN}✅ Coverage via GitHub Actions (no external service needed)${NC}"

echo
echo -e "${BLUE}🚀 Next steps:${NC}"
echo "1. Push a commit to trigger the CI pipeline"
echo "2. Check that 'Security Bootstrap Validation' runs instead of being skipped"
echo "3. View coverage reports in PR comments and workflow artifacts"
echo
echo -e "${GREEN}✅ All done! Your CI/CD pipeline is now fully configured.${NC}"