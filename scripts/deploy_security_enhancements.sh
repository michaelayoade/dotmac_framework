#!/bin/bash

# DotMac Security & Reliability Enhancements Deployment Script
# This script helps deploy all security and reliability features

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     DotMac Security & Reliability Enhancements Deployment     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        return 1
    fi
}

# 1. Check Prerequisites
echo "1. Checking Prerequisites..."
echo "─────────────────────────────"

command_exists psql
print_status $? "PostgreSQL client installed"

command_exists nginx
print_status $? "Nginx installed"

command_exists redis-cli
print_status $? "Redis installed"

command_exists openssl
print_status $? "OpenSSL installed"

echo

# 2. PostgreSQL SSL Setup
echo "2. PostgreSQL SSL Configuration"
echo "────────────────────────────────"

if [ -f "$PROJECT_ROOT/scripts/generate_postgres_ssl.sh" ]; then
    echo -e "${GREEN}✓${NC} SSL generation script found"
    read -p "Generate PostgreSQL SSL certificates? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Generating certificates..."
        chmod +x "$PROJECT_ROOT/scripts/generate_postgres_ssl.sh"
        bash "$PROJECT_ROOT/scripts/generate_postgres_ssl.sh"
    fi
else
    echo -e "${RED}✗${NC} SSL generation script not found"
fi

# Check if certificates exist
if [ -f "$PROJECT_ROOT/certs/dev/server.crt" ]; then
    echo -e "${GREEN}✓${NC} Server certificate exists"
else
    echo -e "${YELLOW}⚠${NC} Server certificate not found - run SSL generation script"
fi

echo

# 3. Nginx Configuration
echo "3. Nginx Rate Limiting & DDoS Protection"
echo "─────────────────────────────────────────"

if [ -f "$PROJECT_ROOT/nginx/nginx.conf" ]; then
    echo -e "${GREEN}✓${NC} Enhanced Nginx configuration found"
    
    # Test nginx configuration
    if command_exists nginx; then
        read -p "Test Nginx configuration? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo nginx -t
            if [ $? -eq 0 ]; then
                read -p "Reload Nginx with new configuration? (y/n): " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    sudo nginx -s reload
                    echo -e "${GREEN}✓${NC} Nginx reloaded"
                fi
            fi
        fi
    fi
else
    echo -e "${RED}✗${NC} Nginx configuration not found"
fi

echo

# 4. Redis Rate Limiter
echo "4. Redis-Based Distributed Rate Limiting"
echo "─────────────────────────────────────────"

if [ -f "$PROJECT_ROOT/isp-framework/src/dotmac_isp/core/rate_limiter.py" ]; then
    echo -e "${GREEN}✓${NC} Rate limiter module found"
    
    # Check Redis connection
    if command_exists redis-cli; then
        redis-cli ping > /dev/null 2>&1
        print_status $? "Redis server responding"
    fi
else
    echo -e "${RED}✗${NC} Rate limiter module not found"
fi

echo

# 5. PostgreSQL High Availability
echo "5. PostgreSQL Auto-Failover Setup"
echo "──────────────────────────────────"

echo -e "${YELLOW}ℹ${NC} PostgreSQL auto-failover handled by Kubernetes orchestration"

echo

# 6. Database Monitoring
echo "6. Database Slow Query Monitoring"
echo "──────────────────────────────────"

if [ -f "$PROJECT_ROOT/isp-framework/src/dotmac_isp/core/db_monitoring.py" ]; then
    echo -e "${GREEN}✓${NC} Database monitoring module found"
    
    # Check pg_stat_statements extension
    if command_exists psql; then
        read -p "Check pg_stat_statements extension? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Enter PostgreSQL connection details:"
            read -p "Database name: " dbname
            read -p "Username: " username
            
            psql -U "$username" -d "$dbname" -c "SELECT * FROM pg_extension WHERE extname = 'pg_stat_statements';" 2>/dev/null
            
            if [ $? -ne 0 ]; then
                echo -e "${YELLOW}⚠${NC} pg_stat_statements not enabled"
                read -p "Enable pg_stat_statements? (y/n): " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    psql -U "$username" -d "$dbname" -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"
                fi
            else
                echo -e "${GREEN}✓${NC} pg_stat_statements is enabled"
            fi
        fi
    fi
else
    echo -e "${RED}✗${NC} Database monitoring module not found"
fi

echo
echo "════════════════════════════════════════════════════════════════"
echo "                    Deployment Summary                          "
echo "════════════════════════════════════════════════════════════════"
echo

# Final checks
components=(
    "PostgreSQL SSL certificates"
    "Nginx rate limiting configuration"
    "Redis rate limiter module"
    "PostgreSQL auto-failover script"
    "Database monitoring module"
)

files=(
    "$PROJECT_ROOT/certs/dev/server.crt"
    "$PROJECT_ROOT/nginx/nginx.conf"
    "$PROJECT_ROOT/isp-framework/src/dotmac_isp/core/rate_limiter.py"
    ""
    "$PROJECT_ROOT/isp-framework/src/dotmac_isp/core/db_monitoring.py"
)

ready=0
total=${#components[@]}

for i in "${!components[@]}"; do
    if [ -f "${files[$i]}" ]; then
        echo -e "${GREEN}✓${NC} ${components[$i]}"
        ((ready++))
    else
        echo -e "${RED}✗${NC} ${components[$i]}"
    fi
done

echo
echo "Status: $ready/$total components ready"

if [ $ready -eq $total ]; then
    echo -e "${GREEN}All security enhancements are ready for deployment!${NC}"
else
    echo -e "${YELLOW}Some components need attention before deployment.${NC}"
fi

echo
echo "Next Steps:"
echo "1. Review and customize configuration files"
echo "2. Test in development environment"
echo "3. Create backups before production deployment"
echo "4. Deploy during maintenance window"
echo "5. Monitor logs after deployment"
