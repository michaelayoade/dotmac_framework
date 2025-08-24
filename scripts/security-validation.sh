#!/bin/bash
# DotMac Platform - Security Validation Script
# Scans for hardcoded secrets and security issues

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

echo -e "${BLUE}🔍 DotMac Platform - Security Validation${NC}"
echo "=============================================="
echo ""

# Check if repository contains sensitive files
echo -e "${BLUE}📁 Checking for sensitive files...${NC}"

SENSITIVE_FOUND=0

# Check for common secret file patterns
SECRET_PATTERNS=(
    "*.pem"
    "*.key" 
    "*.p12"
    "*.pfx"
    "*.jks"
    ".env"
    "secrets.txt"
    "password.txt"
    "jwt_secret.txt"
    "private_key*"
    "id_rsa*"
)

for pattern in "${SECRET_PATTERNS[@]}"; do
    found_files=$(find "$PROJECT_ROOT" -name "$pattern" -type f 2>/dev/null | grep -v "/.git/" | grep -v "/node_modules/" | grep -v "/venv/" | grep -v ".template" || true)
    if [[ -n "$found_files" ]]; then
        echo -e "${YELLOW}⚠️  Found sensitive files matching $pattern:${NC}"
        echo "$found_files"
        SENSITIVE_FOUND=1
        echo ""
    fi
done

if [[ $SENSITIVE_FOUND -eq 0 ]]; then
    echo -e "${GREEN}✅ No sensitive files found in repository${NC}"
fi
echo ""

# Check for hardcoded secrets in code
echo -e "${BLUE}🔎 Scanning for hardcoded secrets in code...${NC}"

SECRETS_FOUND=0

# Common secret patterns
SECRET_REGEXES=(
    "password.*=.*[\"'][^\"']{8,}[\"']"
    "secret.*=.*[\"'][^\"']{16,}[\"']"
    "token.*=.*[\"'][^\"']{16,}[\"']"
    "key.*=.*[\"'][^\"']{16,}[\"']"
    "api_key.*=.*[\"'][^\"']{16,}[\"']"
    "access_key.*=.*[\"'][^\"']{16,}[\"']"
    "private_key.*=.*[\"'][^\"']{16,}[\"']"
    "jwt.*=.*[\"'][^\"']{32,}[\"']"
    "bearer.*[\"'][^\"']{16,}[\"']"
    "Basic [A-Za-z0-9+/]{16,}"
    "sk_live_[A-Za-z0-9]{24,}"
    "pk_live_[A-Za-z0-9]{24,}"
    "AKIA[0-9A-Z]{16}"
)

# Files to exclude from scanning
EXCLUDE_PATTERNS=(
    "*.git/*"
    "*/node_modules/*"
    "*/venv/*"
    "*/test_env/*"
    "*.template"
    "*.md"
    "*.json"
    "*.log"
    "*/coverage/*"
    "*/htmlcov/*"
    "*/test-results/*"
    "*/playwright-report/*"
    "generate-secure-env.sh"
    "security-validation.sh"
)

# Build find exclude arguments
FIND_EXCLUDES=""
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    FIND_EXCLUDES="$FIND_EXCLUDES -path \"*$pattern\" -prune -o"
done

# Scan for hardcoded secrets
for regex in "${SECRET_REGEXES[@]}"; do
    echo -e "${YELLOW}Scanning for: $regex${NC}"
    
    # Use find to get files, then grep for patterns
    eval "find '$PROJECT_ROOT' $FIND_EXCLUDES -type f -name '*.py' -o -name '*.js' -o -name '*.ts' -o -name '*.yml' -o -name '*.yaml' -o -name '*.sh' | grep -v '^$PROJECT_ROOT/.git'" | while read -r file; do
        if [[ -f "$file" ]]; then
            matches=$(grep -nE "$regex" "$file" 2>/dev/null | grep -v "REPLACE_WITH" | grep -v "CHANGE_ME" | grep -v "placeholder" | grep -v "example" | grep -v "test_" | grep -v "fake_" | grep -v "mock_" || true)
            if [[ -n "$matches" ]]; then
                echo -e "${RED}🚨 Potential hardcoded secret found in: ${file}${NC}"
                echo "$matches"
                echo ""
                SECRETS_FOUND=1
            fi
        fi
    done
done

if [[ $SECRETS_FOUND -eq 0 ]]; then
    echo -e "${GREEN}✅ No hardcoded secrets found in code${NC}"
fi
echo ""

# Check environment template files
echo -e "${BLUE}📋 Validating environment templates...${NC}"

TEMPLATE_ISSUES=0

if [[ -f "$PROJECT_ROOT/.env.production.template" ]]; then
    echo -e "${YELLOW}Checking production template...${NC}"
    
    # Check for placeholders that should be replaced
    REQUIRED_PLACEHOLDERS=(
        "REPLACE_WITH_SECURE_64_CHAR_RANDOM_STRING"
        "REPLACE_WITH_SECURE_DB_PASSWORD"
        "REPLACE_WITH_VAULT_TOKEN"
    )
    
    for placeholder in "${REQUIRED_PLACEHOLDERS[@]}"; do
        if ! grep -q "$placeholder" "$PROJECT_ROOT/.env.production.template" 2>/dev/null; then
            echo -e "${RED}❌ Missing placeholder: $placeholder${NC}"
            TEMPLATE_ISSUES=1
        fi
    done
    
    # Check for development values that shouldn't be in production
    DEV_VALUES=(
        "localhost"
        "127.0.0.1"
        "dev_"
        "test_"
        "development"
        "DEBUG=true"
    )
    
    for dev_val in "${DEV_VALUES[@]}"; do
        if grep -q "$dev_val" "$PROJECT_ROOT/.env.production.template" 2>/dev/null; then
            echo -e "${YELLOW}⚠️  Development value in production template: $dev_val${NC}"
        fi
    done
    
    if [[ $TEMPLATE_ISSUES -eq 0 ]]; then
        echo -e "${GREEN}✅ Production template looks good${NC}"
    fi
else
    echo -e "${RED}❌ Missing production environment template${NC}"
    TEMPLATE_ISSUES=1
fi
echo ""

# Check Docker Compose files
echo -e "${BLUE}🐳 Checking Docker Compose files...${NC}"

DOCKER_ISSUES=0

DOCKER_FILES=(
    "$PROJECT_ROOT/docker-compose.yml"
    "$PROJECT_ROOT/isp-framework/docker-compose.yml"
    "$PROJECT_ROOT/management-platform/docker-compose.yml"
)

for docker_file in "${DOCKER_FILES[@]}"; do
    if [[ -f "$docker_file" ]]; then
        echo -e "${YELLOW}Checking $(basename "$docker_file")...${NC}"
        
        # Check for hardcoded passwords
        HARDCODED_PATTERNS=(
            "password: [^$]"
            "POSTGRES_PASSWORD: [^$]"
            "REDIS_PASSWORD: [^$]"
            "_TOKEN: [^$]"
            "_KEY: [^$]"
            "_SECRET: [^$]"
        )
        
        for pattern in "${HARDCODED_PATTERNS[@]}"; do
            matches=$(grep -n "$pattern" "$docker_file" 2>/dev/null | grep -v '\${' || true)
            if [[ -n "$matches" ]]; then
                echo -e "${RED}🚨 Hardcoded value in $docker_file:${NC}"
                echo "$matches"
                DOCKER_ISSUES=1
            fi
        done
    fi
done

if [[ $DOCKER_ISSUES -eq 0 ]]; then
    echo -e "${GREEN}✅ Docker Compose files look secure${NC}"
fi
echo ""

# Final security score
echo -e "${BLUE}📊 Security Validation Summary${NC}"
echo "================================"

TOTAL_ISSUES=$((SENSITIVE_FOUND + SECRETS_FOUND + TEMPLATE_ISSUES + DOCKER_ISSUES))

if [[ $TOTAL_ISSUES -eq 0 ]]; then
    echo -e "${GREEN}🎉 All security checks passed!${NC}"
    echo -e "${GREEN}✅ Repository appears to be clean of hardcoded secrets${NC}"
    exit 0
else
    echo -e "${RED}❌ Found $TOTAL_ISSUES security issues${NC}"
    echo -e "${YELLOW}🔧 Please review and fix the issues above${NC}"
    echo ""
    echo -e "${BLUE}💡 Recommendations:${NC}"
    echo "1. Use environment variables for all secrets"
    echo "2. Run ./scripts/generate-secure-env.sh to create secure .env files"
    echo "3. Add sensitive files to .gitignore"
    echo "4. Use OpenBao/Vault for production secret management"
    exit 1
fi