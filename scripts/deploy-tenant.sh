#!/bin/bash
# Simple tenant deployment script using existing Docker Compose
# Creates isolated container environment for each tenant

set -euo pipefail

# Configuration
TEMPLATE_DIR="/home/dotmac_framework/templates"
TENANT_DIR="/home/dotmac_framework/tenants"
SHARED_NETWORK="dotmac-shared-network"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

show_usage() {
    cat << EOF
Usage: $0 <command> [options]

Commands:
  deploy <tenant-id>     Deploy a new tenant
  remove <tenant-id>     Remove a tenant
  list                   List all tenants
  status <tenant-id>     Show tenant status
  restart <tenant-id>    Restart tenant services
  logs <tenant-id>       Show tenant logs

Options:
  --tier <tier>          Tenant tier (starter|standard|premium|enterprise)
  --domain <domain>      Tenant custom domain
  --max-customers <num>  Maximum customers allowed
  --config <file>        Tenant-specific config file

Examples:
  $0 deploy tenant-acme --tier=premium --domain=acme-isp.com
  $0 status tenant-acme
  $0 logs tenant-acme
  $0 remove tenant-acme
EOF
}

generate_tenant_env() {
    local tenant_id="$1"
    local tier="${2:-standard}"
    local domain="${3:-}"
    local max_customers="${4:-1000}"

    local env_file="$TENANT_DIR/$tenant_id/.env"

    # Generate secure passwords
    local postgres_password=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    local redis_password=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    local secret_key=$(openssl rand -base64 64 | tr -d "=+/")

    # Determine resource limits based on tier
    local postgres_memory redis_memory isp_memory
    local postgres_cpus redis_cpus isp_cpus
    local http_port https_port isp_port

    case "$tier" in
        starter)
            postgres_memory="512M"
            redis_memory="256M"
            isp_memory="1G"
            postgres_cpus="0.5"
            redis_cpus="0.25"
            isp_cpus="1.0"
            max_customers=${max_customers:-500}
            ;;
        standard)
            postgres_memory="1G"
            redis_memory="512M"
            isp_memory="2G"
            postgres_cpus="1.0"
            redis_cpus="0.5"
            isp_cpus="2.0"
            max_customers=${max_customers:-2000}
            ;;
        premium)
            postgres_memory="2G"
            redis_memory="1G"
            isp_memory="4G"
            postgres_cpus="2.0"
            redis_cpus="1.0"
            isp_cpus="4.0"
            max_customers=${max_customers:-5000}
            ;;
        enterprise)
            postgres_memory="4G"
            redis_memory="2G"
            isp_memory="8G"
            postgres_cpus="4.0"
            redis_cpus="2.0"
            isp_cpus="8.0"
            max_customers=${max_customers:-10000}
            ;;
        *)
            error "Invalid tier: $tier"
            exit 1
            ;;
    esac

    # Find available ports
    local base_port=8000
    while netstat -ln | grep -q ":$((base_port))"; do
        ((base_port += 10))
    done

    isp_port=$base_port
    http_port=$((base_port + 1))
    https_port=$((base_port + 2))

    # Generate subnet (172.20.x.0/24 where x is based on tenant hash)
    local subnet_octet=$(echo "$tenant_id" | md5sum | head -c 2)
    local subnet_octet_dec=$((16#$subnet_octet % 240 + 10))  # 10-250 range
    local tenant_subnet="172.20.$subnet_octet_dec.0/24"

    cat > "$env_file" << EOF
# DotMac Tenant Configuration: $tenant_id
# Generated on $(date)

# Tenant identification
TENANT_ID=$tenant_id
TENANT_NAME=${tenant_id}
TENANT_TIER=$tier
TENANT_DOMAIN=${domain}

# Security
TENANT_SECRET_KEY=$secret_key
TENANT_POSTGRES_PASSWORD=$postgres_password
TENANT_REDIS_PASSWORD=$redis_password

# Resource limits
TENANT_POSTGRES_MEMORY=$postgres_memory
TENANT_POSTGRES_CPUS=$postgres_cpus
TENANT_REDIS_MEMORY=$redis_memory
TENANT_REDIS_MAXMEMORY=$redis_memory
TENANT_REDIS_CPUS=$redis_cpus
TENANT_ISP_MEMORY=$isp_memory
TENANT_ISP_CPUS=$isp_cpus

# Network configuration
TENANT_SUBNET=$tenant_subnet
TENANT_HTTP_PORT=$http_port
TENANT_HTTPS_PORT=$https_port
TENANT_ISP_PORT=$isp_port

# Business limits
TENANT_MAX_CUSTOMERS=$max_customers
TENANT_MAX_SERVICES=1000

# Feature flags based on tier
TENANT_ENABLE_BILLING=true
TENANT_ENABLE_ANALYTICS=$([ "$tier" != "starter" ] && echo "true" || echo "false")
TENANT_ENABLE_PLUGINS=$([ "$tier" = "premium" -o "$tier" = "enterprise" ] && echo "true" || echo "false")

# Access control
TENANT_ALLOWED_HOSTS=${domain:-localhost,127.0.0.1}
TENANT_CORS_ORIGINS=http://localhost:3000,https://${domain:-localhost}

# Application versions
ISP_FRAMEWORK_VERSION=latest
ENVIRONMENT=production
EOF

    chmod 600 "$env_file"
    log "Generated tenant environment file: $env_file"
}

create_shared_network() {
    # Create shared network if it doesn't exist
    if ! docker network ls | grep -q "$SHARED_NETWORK"; then
        log "Creating shared network: $SHARED_NETWORK"
        docker network create \
            --driver bridge \
            --subnet 172.19.0.0/24 \
            "$SHARED_NETWORK"
    fi
}

create_tenant_dns() {
    local tenant_id="$1"
    local custom_domain="$2"

    log "Creating DNS records for tenant: $tenant_id"

    # Check if Python environment has required dependencies
    if ! python3 -c "import sys; sys.path.append('/home/dotmac_framework/src'); from dotmac_isp.core.dns_manager import create_tenant_dns" 2>/dev/null; then
        warn "DNS automation dependencies not installed. Skipping DNS setup."
        warn "To enable DNS automation:"
        warn "1. Set CLOUDFLARE_TOKEN environment variable"
        warn "2. Set CLOUDFLARE_ZONE_ID environment variable"
        warn "3. Install dependencies: pip install cloudflare dnspython"
        return
    fi

    # Create DNS records via Python DNS manager
    python3 << EOF
import sys
import os
import asyncio
sys.path.append('/home/dotmac_framework/src')

# Set environment variables for DNS manager
os.environ.setdefault('BASE_DOMAIN', 'dotmac.io')
os.environ.setdefault('LOAD_BALANCER_IP', '127.0.0.1')

try:
    from dotmac_isp.core.dns_manager import create_tenant_dns

    async def main():
        result = await create_tenant_dns('$tenant_id', '$custom_domain' if '$custom_domain' else None)

        print(f"DNS setup results for $tenant_id:")

        # Print subdomain creation results
        subdomains = result.get('subdomains_created', {})
        for domain, success in subdomains.items():
            status = "✅" if success else "❌"
            print(f"  {status} {domain}")

        # Print custom domain setup info
        if '$custom_domain':
            print(f"\\nCustom domain setup: $custom_domain")
            verification_records = result.get('verification_required', [])
            if verification_records:
                print("Required DNS records for custom domain:")
                for record in verification_records:
                    print(f"  {record['type']} {record['name']} {record['content']}")

    asyncio.run(main())

except ImportError as e:
    print(f"❌ DNS automation not available: {e}")
    print("Manual DNS setup required")
except Exception as e:
    print(f"❌ DNS setup failed: {e}")
    print("Continuing with deployment...")

EOF
}

deploy_tenant() {
    local tenant_id="$1"
    local tier="${2:-standard}"
    local domain="${3:-}"
    local max_customers="${4:-}"

    log "Deploying tenant: $tenant_id (tier: $tier)"

    # Validate tenant ID
    if [[ ! "$tenant_id" =~ ^[a-z0-9][a-z0-9-]*[a-z0-9]$ ]]; then
        error "Invalid tenant ID. Must be lowercase, alphanumeric, and hyphens only."
        exit 1
    fi

    # Create tenant directory
    local tenant_path="$TENANT_DIR/$tenant_id"
    mkdir -p "$tenant_path"

    # Generate tenant configuration
    generate_tenant_env "$tenant_id" "$tier" "$domain" "$max_customers"

    # Copy Docker Compose template
    local compose_file="$tenant_path/docker-compose.yml"
    envsubst < "$TEMPLATE_DIR/tenant-docker-compose.yml" > "$compose_file"

    # Create shared network
    create_shared_network

    # Create DNS records for tenant
    create_tenant_dns "$tenant_id" "$domain"

    # Deploy using Docker Compose
    log "Starting tenant containers..."
    cd "$tenant_path"

    # Source the environment file and deploy
    set -a
    source .env
    set +a

    if docker-compose up -d; then
        log "✅ Tenant $tenant_id deployed successfully!"
        log "   - ISP Framework: http://localhost:$TENANT_ISP_PORT"
        if [[ -n "$domain" ]]; then
            log "   - Custom domain: https://$domain"
        fi
        log "   - Tier: $tier"
        log "   - Max customers: $TENANT_MAX_CUSTOMERS"

        # Wait for services to be healthy
        log "Waiting for services to be healthy..."
        sleep 10

        if docker-compose ps | grep -q "Up.*healthy"; then
            log "✅ Services are healthy"
        else
            warn "Some services may not be healthy yet. Check logs with: $0 logs $tenant_id"
        fi
    else
        error "Failed to deploy tenant $tenant_id"
        exit 1
    fi
}

remove_tenant() {
    local tenant_id="$1"
    local tenant_path="$TENANT_DIR/$tenant_id"

    if [[ ! -d "$tenant_path" ]]; then
        error "Tenant $tenant_id does not exist"
        exit 1
    fi

    warn "This will permanently delete tenant $tenant_id and all its data!"
    read -p "Are you sure? Type 'yes' to confirm: " confirm

    if [[ "$confirm" == "yes" ]]; then
        log "Removing tenant: $tenant_id"

        cd "$tenant_path"

        # Stop and remove containers
        docker-compose down -v --remove-orphans

        # Remove tenant directory
        cd /
        rm -rf "$tenant_path"

        log "✅ Tenant $tenant_id removed successfully"
    else
        log "Removal cancelled"
    fi
}

list_tenants() {
    log "Deployed tenants:"
    echo

    if [[ ! -d "$TENANT_DIR" ]]; then
        echo "No tenants deployed"
        return
    fi

    for tenant_path in "$TENANT_DIR"/*; do
        if [[ -d "$tenant_path" ]]; then
            local tenant_id=$(basename "$tenant_path")
            local env_file="$tenant_path/.env"

            if [[ -f "$env_file" ]]; then
                local tier=$(grep "TENANT_TIER=" "$env_file" | cut -d= -f2)
                local domain=$(grep "TENANT_DOMAIN=" "$env_file" | cut -d= -f2)
                local port=$(grep "TENANT_ISP_PORT=" "$env_file" | cut -d= -f2)

                # Check if containers are running
                cd "$tenant_path"
                if docker-compose ps -q | xargs docker inspect | grep -q '"Status": "running"'; then
                    local status="🟢 Running"
                else
                    local status="🔴 Stopped"
                fi

                echo "  $tenant_id ($tier) - $status"
                echo "    Port: $port"
                if [[ -n "$domain" ]]; then
                    echo "    Domain: $domain"
                fi
                echo
            fi
        fi
    done
}

show_tenant_status() {
    local tenant_id="$1"
    local tenant_path="$TENANT_DIR/$tenant_id"

    if [[ ! -d "$tenant_path" ]]; then
        error "Tenant $tenant_id does not exist"
        exit 1
    fi

    log "Status for tenant: $tenant_id"

    cd "$tenant_path"
    docker-compose ps
    echo
    docker-compose top
}

show_tenant_logs() {
    local tenant_id="$1"
    local tenant_path="$TENANT_DIR/$tenant_id"

    if [[ ! -d "$tenant_path" ]]; then
        error "Tenant $tenant_id does not exist"
        exit 1
    fi

    cd "$tenant_path"
    docker-compose logs -f --tail=100
}

restart_tenant() {
    local tenant_id="$1"
    local tenant_path="$TENANT_DIR/$tenant_id"

    if [[ ! -d "$tenant_path" ]]; then
        error "Tenant $tenant_id does not exist"
        exit 1
    fi

    log "Restarting tenant: $tenant_id"

    cd "$tenant_path"
    docker-compose restart

    log "✅ Tenant $tenant_id restarted"
}

# Parse command line arguments
command="${1:-}"
tenant_id="${2:-}"

# Parse options
tier="standard"
domain=""
max_customers=""
config_file=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --tier=*)
            tier="${1#*=}"
            shift
            ;;
        --domain=*)
            domain="${1#*=}"
            shift
            ;;
        --max-customers=*)
            max_customers="${1#*=}"
            shift
            ;;
        --config=*)
            config_file="${1#*=}"
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Execute commands
case "$command" in
    deploy)
        if [[ -z "$tenant_id" ]]; then
            error "Tenant ID is required for deploy command"
            show_usage
            exit 1
        fi
        deploy_tenant "$tenant_id" "$tier" "$domain" "$max_customers"
        ;;
    remove)
        if [[ -z "$tenant_id" ]]; then
            error "Tenant ID is required for remove command"
            exit 1
        fi
        remove_tenant "$tenant_id"
        ;;
    list)
        list_tenants
        ;;
    status)
        if [[ -z "$tenant_id" ]]; then
            error "Tenant ID is required for status command"
            exit 1
        fi
        show_tenant_status "$tenant_id"
        ;;
    logs)
        if [[ -z "$tenant_id" ]]; then
            error "Tenant ID is required for logs command"
            exit 1
        fi
        show_tenant_logs "$tenant_id"
        ;;
    restart)
        if [[ -z "$tenant_id" ]]; then
            error "Tenant ID is required for restart command"
            exit 1
        fi
        restart_tenant "$tenant_id"
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
