#!/bin/bash

# DotMac Platform Environment Setup Script
# Helps developers set up their environment configuration quickly

set -e

# Colors for output
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}DotMac Platform Environment Setup${NC}"
echo "=================================="
echo ""

# Function to prompt user with default
prompt_with_default() {
    local var_name=$1
    local description=$2
    local default_value=$3
    local current_value
    
    echo -e "${YELLOW}${description}${NC}"
    read -p "Enter value (default: ${default_value}): " current_value
    
    if [[ -z "$current_value" ]]; then
        current_value=$default_value
    fi
    
    echo "${var_name}=${current_value}" >> .env.local
}

# Function to generate secure random string
generate_secret() {
    openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p -c 32
}

# Check if .env.local already exists
if [[ -f ".env.local" ]]; then
    echo -e "${YELLOW}⚠️  .env.local already exists!${NC}"
    read -p "Do you want to overwrite it? (y/N): " overwrite
    if [[ $overwrite != "y" && $overwrite != "Y" ]]; then
        echo -e "${GREEN}Keeping existing .env.local file${NC}"
        exit 0
    fi
    rm .env.local
fi

echo -e "${GREEN}Creating your local development environment configuration...${NC}"
echo ""

# Ask user about their setup type
echo -e "${BLUE}What type of development setup do you want?${NC}"
echo "1) Quick Start (all defaults, ready to go)"
echo "2) Custom Setup (configure external services)"
echo "3) Production-like (staging environment)"
read -p "Choose (1-3): " setup_type

case $setup_type in
    1)
        echo -e "${GREEN}Setting up Quick Start configuration...${NC}"
        cp .env.development .env.local
        
        # Generate secure secrets even for development
        echo "" >> .env.local
        echo "# Generated secrets for development" >> .env.local
        echo "JWT_SECRET_KEY=$(generate_secret)" >> .env.local
        echo "MGMT_SECRET_KEY=$(generate_secret)" >> .env.local
        echo "MGMT_JWT_SECRET_KEY=$(generate_secret)" >> .env.local
        
        echo -e "${GREEN}✅ Quick start configuration created!${NC}"
        ;;
    2)
        echo -e "${BLUE}Setting up custom configuration...${NC}"
        echo ""
        
        # Start with development defaults
        cp .env.development .env.local
        
        # Ask for external service configurations
        echo -e "${BLUE}External Services Configuration:${NC}"
        echo "Leave blank to use mock services for development"
        echo ""
        
        prompt_with_default "STRIPE_SECRET_KEY" "Stripe Secret Key (for payments)" "sk_test_mock_key"
        prompt_with_default "SENDGRID_API_KEY" "SendGrid API Key (for emails)" "SG.mock_key"
        prompt_with_default "TWILIO_ACCOUNT_SID" "Twilio Account SID (for SMS)" "AC_mock_sid"
        prompt_with_default "TWILIO_AUTH_TOKEN" "Twilio Auth Token" "mock_token"
        
        # Generate secure secrets
        echo "" >> .env.local
        echo "# Generated secrets" >> .env.local
        echo "JWT_SECRET_KEY=$(generate_secret)" >> .env.local
        echo "MGMT_SECRET_KEY=$(generate_secret)" >> .env.local
        echo "MGMT_JWT_SECRET_KEY=$(generate_secret)" >> .env.local
        
        echo -e "${GREEN}✅ Custom configuration created!${NC}"
        ;;
    3)
        echo -e "${BLUE}Setting up production-like staging configuration...${NC}"
        
        # Use production template but with local URLs
        sed 's/ENVIRONMENT=production/ENVIRONMENT=staging/' .env.example > .env.local
        sed -i 's/DEBUG=false/DEBUG=true/' .env.local
        sed -i 's/LOG_LEVEL=INFO/LOG_LEVEL=DEBUG/' .env.local
        
        # Replace vault references with actual values for local development
        sed -i 's/vault:.*#.*/PLEASE_CONFIGURE_THIS_VALUE/' .env.local
        
        echo -e "${YELLOW}⚠️  You'll need to configure actual values for external services${NC}"
        echo -e "${GREEN}✅ Staging-like configuration template created!${NC}"
        ;;
    *)
        echo -e "${RED}Invalid choice. Using Quick Start defaults.${NC}"
        cp .env.development .env.local
        ;;
esac

echo ""
echo -e "${BLUE}Environment Configuration Summary:${NC}"
echo "================================="
echo "• Configuration file: .env.local"
echo "• Environment: $(grep '^ENVIRONMENT=' .env.local | cut -d'=' -f2)"
echo "• Debug mode: $(grep '^DEBUG=' .env.local | cut -d'=' -f2)"
echo ""

echo -e "${YELLOW}Next steps:${NC}"
echo "1. Review and customize .env.local if needed"
echo "2. Run 'make quick-start' to start the platform"
echo "3. Check 'make show-endpoints' for service URLs"
echo ""

echo -e "${BLUE}Useful commands:${NC}"
echo "• make quick-start     - Complete first-time setup"
echo "• make dev-simple      - Lightweight development"
echo "• make health-check    - Verify all services"
echo "• make show-endpoints  - Show service URLs"
echo ""

echo -e "${GREEN}🎉 Environment configuration complete!${NC}"
echo "Your secrets are safely stored in .env.local (git-ignored)"