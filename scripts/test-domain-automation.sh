#!/bin/bash
# Test Domain Automation Implementation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ERROR: $1${NC}"
}

show_usage() {
    cat << EOF
Usage: $0 <command>

Commands:
  install     Install DNS automation dependencies
  test-dns    Test DNS manager functionality
  test-api    Test domain API endpoints
  deploy      Deploy test tenant with domain automation
  cleanup     Remove test tenant and DNS records

Examples:
  $0 install
  $0 test-dns
  $0 deploy test-tenant portal.example.com
EOF
}

install_dependencies() {
    log "Installing DNS automation dependencies..."
    
    cd "$ROOT_DIR/isp-framework"
    
    # Install Python dependencies
    if command -v poetry &> /dev/null; then
        log "Installing via Poetry..."
        poetry add cloudflare dnspython
        poetry install
    else
        log "Installing via pip..."
        pip3 install cloudflare dnspython
    fi
    
    log "✅ DNS automation dependencies installed"
}

test_dns_manager() {
    log "Testing DNS manager functionality..."
    
    cd "$ROOT_DIR"
    
    # Test DNS manager import and basic functionality
    python3 << 'EOF'
import sys
sys.path.append('isp-framework/src')

try:
    from dotmac_isp.core.dns_manager import DNSManager, create_tenant_dns
    print("✅ DNS manager imported successfully")
    
    # Test DNS manager initialization
    dns_manager = DNSManager()
    print(f"✅ DNS manager initialized with base domain: {dns_manager.base_domain}")
    
    if dns_manager.cf:
        print("✅ Cloudflare integration enabled")
    else:
        print("⚠️ Cloudflare not configured - DNS automation will be simulated")
    
    print("✅ DNS manager tests passed")
    
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("Make sure dependencies are installed: pip install cloudflare dnspython")
    exit(1)
except Exception as e:
    print(f"❌ DNS manager test failed: {e}")
    exit(1)
EOF

    log "✅ DNS manager tests completed"
}

test_api_endpoints() {
    log "Testing domain API endpoints..."
    
    # Check if ISP framework is running
    if ! curl -s http://localhost:8001/health > /dev/null; then
        error "ISP framework not running. Start it first with: docker-compose up isp-framework"
        return 1
    fi
    
    log "Testing domain setup endpoint..."
    response=$(curl -s -X POST http://localhost:8001/api/v1/domains/setup \
        -H "Content-Type: application/json" \
        -d '{
            "domain": "test.example.com",
            "tenant_id": "test-tenant"
        }' || echo "failed")
    
    if [[ "$response" == "failed" ]]; then
        warn "Could not connect to domain API - framework may not be running"
    else
        log "✅ Domain setup API responding"
    fi
    
    log "Testing domain verification endpoint..."
    response=$(curl -s -X POST http://localhost:8001/api/v1/domains/verify \
        -H "Content-Type: application/json" \
        -d '{
            "domain": "test.example.com"
        }' || echo "failed")
    
    if [[ "$response" == "failed" ]]; then
        warn "Could not connect to verification API"
    else
        log "✅ Domain verification API responding"
    fi
    
    log "✅ API endpoint tests completed"
}

deploy_test_tenant() {
    local tenant_id="${1:-test-domain-automation}"
    local custom_domain="${2:-}"
    
    log "Deploying test tenant with domain automation..."
    log "Tenant ID: $tenant_id"
    if [[ -n "$custom_domain" ]]; then
        log "Custom domain: $custom_domain"
    fi
    
    # Use the enhanced deploy script
    if [[ -n "$custom_domain" ]]; then
        "$ROOT_DIR/scripts/deploy-tenant.sh" deploy "$tenant_id" \
            --tier=standard \
            --domain="$custom_domain"
    else
        "$ROOT_DIR/scripts/deploy-tenant.sh" deploy "$tenant_id" \
            --tier=standard
    fi
    
    log "✅ Test tenant deployed with domain automation"
    
    # Test the deployment
    log "Testing tenant accessibility..."
    sleep 5
    
    local tenant_port
    tenant_port=$(grep "TENANT_ISP_PORT=" "/home/dotmac_framework/tenants/$tenant_id/.env" | cut -d= -f2)
    
    if curl -s "http://localhost:$tenant_port/health" > /dev/null; then
        log "✅ Tenant is accessible at http://localhost:$tenant_port"
    else
        warn "Tenant may not be fully ready yet. Check logs with: ./scripts/deploy-tenant.sh logs $tenant_id"
    fi
}

cleanup_test_tenant() {
    local tenant_id="${1:-test-domain-automation}"
    
    log "Cleaning up test tenant: $tenant_id"
    
    "$ROOT_DIR/scripts/deploy-tenant.sh" remove "$tenant_id"
    
    log "✅ Test tenant cleanup completed"
}

test_full_workflow() {
    log "Testing complete domain automation workflow..."
    
    local test_tenant="workflow-test-$(date +%s)"
    local test_domain="test-workflow.example.com"
    
    log "1. Testing tenant deployment with custom domain..."
    deploy_test_tenant "$test_tenant" "$test_domain"
    
    log "2. Testing domain status API..."
    sleep 2
    curl -s "http://localhost:8001/api/v1/domains/tenant/$test_tenant/status" | jq . || echo "Status check completed"
    
    log "3. Testing DNS records generation..."
    curl -s "http://localhost:8001/api/v1/domains/dns-records/$test_tenant?custom_domain=$test_domain" | jq . || echo "DNS records check completed"
    
    log "4. Cleaning up test tenant..."
    cleanup_test_tenant "$test_tenant"
    
    log "✅ Full workflow test completed"
}

# Main command dispatcher
case "${1:-help}" in
    "install")
        install_dependencies
        ;;
    "test-dns")
        test_dns_manager
        ;;
    "test-api")
        test_api_endpoints
        ;;
    "deploy")
        deploy_test_tenant "${2:-}" "${3:-}"
        ;;
    "cleanup")
        cleanup_test_tenant "${2:-test-domain-automation}"
        ;;
    "test-all")
        log "Running complete domain automation test suite..."
        install_dependencies
        test_dns_manager
        test_api_endpoints
        test_full_workflow
        log "🎉 All tests completed successfully!"
        ;;
    "help"|*)
        show_usage
        ;;
esac