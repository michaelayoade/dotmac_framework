#!/bin/bash
# VPS Customer Setup Script
# Automated deployment script for customer-managed VPS installations

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="/var/log/dotmac-vps-setup.log"

# Functions for colored output
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" | tee -a "$LOG_FILE"
}

header() {
    echo -e "${BLUE}$1${NC}"
}

# Error handling
trap 'handle_error $? $LINENO' ERR

handle_error() {
    error "Setup failed at line $2 with exit code $1"
    error "Check the log file: $LOG_FILE"
    exit $1
}

show_usage() {
    cat << EOF
Usage: $0 <command> [options]

Commands:
  setup <customer-id>        Set up VPS for customer
  validate <ip> <port>       Validate VPS connectivity
  requirements <plan>        Show VPS requirements for plan
  health-check <customer-id> Run health checks
  status <customer-id>       Show customer status

Options:
  --plan <plan>             Plan tier (starter|professional|enterprise)
  --ip <ip>                 VPS IP address
  --ssh-port <port>         SSH port (default: 22)
  --ssh-user <user>         SSH username (default: root)
  --ssh-key <path>          SSH private key file
  --domain <domain>         Custom domain
  --customers <count>       Expected customer count
  --traffic <level>         Traffic level (low|medium|high)

Examples:
  $0 setup acme-isp --plan=professional --ip=1.2.3.4 --ssh-key=/path/to/key
  $0 validate 1.2.3.4 22
  $0 requirements professional
  $0 health-check acme-isp
EOF
}

# VPS connectivity validation
validate_vps_connectivity() {
    local ip="$1"
    local port="${2:-22}"
    local ssh_user="${3:-root}"
    local ssh_key="${4:-}"
    
    header "🔍 Validating VPS Connectivity"
    log "Testing connection to $ip:$port as $ssh_user"
    
    # SSH connectivity test
    local ssh_opts="-o ConnectTimeout=10 -o StrictHostKeyChecking=no -o BatchMode=yes"
    
    if [[ -n "$ssh_key" ]]; then
        ssh_opts="$ssh_opts -i $ssh_key"
    fi
    
    if ssh $ssh_opts -p "$port" "$ssh_user@$ip" "echo 'SSH connectivity test successful'" 2>/dev/null; then
        log "✅ SSH connectivity: PASSED"
    else
        error "❌ SSH connectivity: FAILED"
        return 1
    fi
    
    # System information gathering
    log "Gathering system information..."
    
    local system_info
    system_info=$(ssh $ssh_opts -p "$port" "$ssh_user@$ip" '
        echo "OS: $(lsb_release -d 2>/dev/null | cut -f2 || cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d \")"
        echo "CPU Cores: $(nproc)"
        echo "Memory: $(free -h | awk "NR==2{print \$2}")"
        echo "Disk Space: $(df -h / | awk "NR==2{print \$2}")"
        echo "Architecture: $(uname -m)"
        echo "Kernel: $(uname -r)"
    ' 2>/dev/null)
    
    if [[ $? -eq 0 ]]; then
        log "✅ System information gathered:"
        echo "$system_info" | while read -r line; do
            log "   $line"
        done
    else
        warn "⚠️ Could not gather complete system information"
    fi
    
    log "✅ VPS connectivity validation completed"
    return 0
}

# Show VPS requirements for a plan
show_requirements() {
    local plan="${1:-starter}"
    
    header "📋 VPS Requirements for $plan Plan"
    
    case "$plan" in
        starter)
            cat << EOF
Minimum Requirements:
  • CPU: 2 cores
  • RAM: 4 GB
  • Storage: 50 GB SSD
  • Network: 100 Mbps
  • OS: Ubuntu 20.04+ or similar

Recommended:
  • CPU: 4 cores  
  • RAM: 8 GB
  • Storage: 100 GB SSD
  • Network: 500 Mbps

Estimated Monthly Cost: \$20-40
Setup Fee: \$500
Monthly Support: \$200
EOF
            ;;
        professional)
            cat << EOF
Minimum Requirements:
  • CPU: 4 cores
  • RAM: 8 GB  
  • Storage: 100 GB SSD
  • Network: 500 Mbps
  • OS: Ubuntu 20.04+ or similar

Recommended:
  • CPU: 8 cores
  • RAM: 16 GB
  • Storage: 250 GB SSD
  • Network: 1 Gbps

Estimated Monthly Cost: \$50-100
Setup Fee: \$1,000
Monthly Support: \$500
EOF
            ;;
        enterprise)
            cat << EOF
Minimum Requirements:
  • CPU: 8 cores
  • RAM: 16 GB
  • Storage: 200 GB SSD
  • Network: 1 Gbps
  • OS: Ubuntu 20.04+ or similar

Recommended:
  • CPU: 16 cores
  • RAM: 32 GB
  • Storage: 500 GB SSD
  • Network: 1 Gbps+

Estimated Monthly Cost: \$100-200
Setup Fee: \$2,000
Monthly Support: \$800
EOF
            ;;
        *)
            error "Invalid plan: $plan. Valid options: starter, professional, enterprise"
            return 1
            ;;
    esac
    
    echo
    log "Required Ports: 22 (SSH), 80 (HTTP), 443 (HTTPS), 8000 (ISP), 8001 (Management)"
    log "Supported OS: Ubuntu 20.04+, Debian 11+, CentOS 8+, Rocky Linux 8+"
    log "Recommended Providers: DigitalOcean, Linode, Vultr, Hetzner"
}

# Set up VPS for customer
setup_vps_customer() {
    local customer_id="$1"
    local plan="${2:-starter}"
    local vps_ip="$3"
    local ssh_port="${4:-22}"
    local ssh_user="${5:-root}"
    local ssh_key="$6"
    local custom_domain="${7:-}"
    local expected_customers="${8:-100}"
    local traffic_level="${9:-low}"
    
    header "🚀 Setting up VPS for Customer: $customer_id"
    
    # Validate inputs
    if [[ -z "$customer_id" || -z "$vps_ip" ]]; then
        error "Customer ID and VPS IP are required"
        show_usage
        return 1
    fi
    
    if [[ -n "$ssh_key" && ! -f "$ssh_key" ]]; then
        error "SSH key file not found: $ssh_key"
        return 1
    fi
    
    # Step 1: Validate connectivity
    log "Step 1/7: Validating VPS connectivity..."
    if ! validate_vps_connectivity "$vps_ip" "$ssh_port" "$ssh_user" "$ssh_key"; then
        error "VPS connectivity validation failed"
        return 1
    fi
    
    # Step 2: Check requirements
    log "Step 2/7: Checking server requirements..."
    # This would integrate with the VPS requirements service
    
    # Step 3: Install dependencies
    log "Step 3/7: Installing dependencies..."
    local ssh_opts="-o ConnectTimeout=30 -o StrictHostKeyChecking=no"
    if [[ -n "$ssh_key" ]]; then
        ssh_opts="$ssh_opts -i $ssh_key"
    fi
    
    # Install Docker
    ssh $ssh_opts -p "$ssh_port" "$ssh_user@$vps_ip" '
        # Update system
        apt-get update -y
        
        # Install Docker if not present
        if ! command -v docker &> /dev/null; then
            echo "Installing Docker..."
            apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
            echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
            apt-get update -y
            apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
            systemctl enable docker
            systemctl start docker
            usermod -aG docker $USER
        fi
        
        # Verify Docker installation
        docker --version
        docker compose version
    '
    
    if [[ $? -ne 0 ]]; then
        error "Failed to install dependencies"
        return 1
    fi
    
    log "✅ Dependencies installed successfully"
    
    # Step 4: Deploy ISP Framework
    log "Step 4/7: Deploying ISP Framework..."
    
    # Copy deployment script to VPS
    scp $ssh_opts -P "$ssh_port" "$PROJECT_ROOT/scripts/deploy-tenant.sh" "$ssh_user@$vps_ip:/tmp/"
    
    # Run deployment
    ssh $ssh_opts -p "$ssh_port" "$ssh_user@$vps_ip" "
        chmod +x /tmp/deploy-tenant.sh
        cd /tmp
        ./deploy-tenant.sh deploy $customer_id \\
            --tier=$plan \\
            --domain=${custom_domain:-$customer_id.yourdomain.com} \\
            --max-customers=$expected_customers
    "
    
    if [[ $? -ne 0 ]]; then
        error "Failed to deploy ISP Framework"
        return 1
    fi
    
    log "✅ ISP Framework deployed successfully"
    
    # Step 5: Set up monitoring
    log "Step 5/7: Setting up monitoring..."
    
    scp $ssh_opts -P "$ssh_port" "$PROJECT_ROOT/scripts/setup_monitoring.sh" "$ssh_user@$vps_ip:/tmp/"
    
    ssh $ssh_opts -p "$ssh_port" "$ssh_user@$vps_ip" "
        chmod +x /tmp/setup_monitoring.sh
        cd /tmp
        ./setup_monitoring.sh
    "
    
    # Step 6: Configure SSL (if custom domain provided)
    if [[ -n "$custom_domain" ]]; then
        log "Step 6/7: Configuring SSL for $custom_domain..."
        
        ssh $ssh_opts -p "$ssh_port" "$ssh_user@$vps_ip" "
            # Install certbot
            apt-get install -y certbot python3-certbot-nginx
            
            # Generate SSL certificate
            certbot --nginx -d $custom_domain --non-interactive --agree-tos --email admin@$custom_domain
        "
        
        if [[ $? -eq 0 ]]; then
            log "✅ SSL certificate configured for $custom_domain"
        else
            warn "⚠️ SSL configuration failed, continuing with HTTP"
        fi
    else
        log "Step 6/7: Skipping SSL configuration (no custom domain)"
    fi
    
    # Step 7: Health checks
    log "Step 7/7: Running health checks..."
    
    # Wait for services to start
    sleep 30
    
    # Test HTTP endpoints
    local base_url="http://$vps_ip:8000"
    if curl -f -s "$base_url/health" > /dev/null; then
        log "✅ ISP Framework health check: PASSED"
    else
        warn "⚠️ ISP Framework health check: FAILED"
    fi
    
    local mgmt_url="http://$vps_ip:8001"  
    if curl -f -s "$mgmt_url/health" > /dev/null; then
        log "✅ Management Platform health check: PASSED"
    else
        warn "⚠️ Management Platform health check: FAILED"
    fi
    
    # Final summary
    header "🎉 VPS Setup Completed for $customer_id"
    echo "=========================================="
    log "Customer: $customer_id"
    log "Plan: $plan"
    log "VPS IP: $vps_ip"
    log "ISP Framework: http://$vps_ip:8000"
    log "Management: http://$vps_ip:8001"
    if [[ -n "$custom_domain" ]]; then
        log "Custom Domain: https://$custom_domain"
    fi
    echo
    log "Next Steps:"
    log "1. Test the ISP Framework at the URLs above"
    log "2. Configure DNS records if using custom domain"
    log "3. Set up monitoring alerts and backups"
    log "4. Provide customer with admin credentials"
    log "5. Schedule training session with customer"
    echo "=========================================="
}

# Run health checks for existing customer
health_check_customer() {
    local customer_id="$1"
    
    header "🏥 Health Check for Customer: $customer_id"
    
    # This would integrate with the monitoring system
    # For now, basic checks
    
    local config_file="/opt/dotmac/customers/$customer_id/.env"
    if [[ ! -f "$config_file" ]]; then
        error "Customer configuration not found: $customer_id"
        return 1
    fi
    
    # Load customer configuration
    source "$config_file"
    
    local vps_ip="${TENANT_VPS_IP:-localhost}"
    local isp_port="${TENANT_ISP_PORT:-8000}"
    local mgmt_port="${TENANT_MGMT_PORT:-8001}"
    
    # Test endpoints
    log "Testing ISP Framework endpoint..."
    if curl -f -s "http://$vps_ip:$isp_port/health" > /dev/null; then
        log "✅ ISP Framework: HEALTHY"
    else
        error "❌ ISP Framework: UNHEALTHY"
    fi
    
    log "Testing Management Platform endpoint..."
    if curl -f -s "http://$vps_ip:$mgmt_port/health" > /dev/null; then
        log "✅ Management Platform: HEALTHY"
    else
        error "❌ Management Platform: UNHEALTHY"
    fi
    
    log "Health check completed for $customer_id"
}

# Get customer status
get_customer_status() {
    local customer_id="$1"
    
    header "📊 Status for Customer: $customer_id"
    
    # This would query the management API
    curl -s "http://localhost:8001/api/v1/vps-customers/$customer_id/status" | jq '.' || {
        warn "Could not retrieve status from management API"
        
        # Fallback to local checks
        local config_file="/opt/dotmac/customers/$customer_id/.env"
        if [[ -f "$config_file" ]]; then
            log "Customer configuration found: $customer_id"
            grep -E "^(TENANT_ID|TENANT_TIER|TENANT_DOMAIN|TENANT_VPS_IP)" "$config_file"
        else
            error "Customer not found: $customer_id"
        fi
    }
}

# Main execution
main() {
    # Parse command line arguments
    command="${1:-}"
    
    case "$command" in
        setup)
            customer_id="${2:-}"
            shift 2
            
            # Parse options
            plan="starter"
            vps_ip=""
            ssh_port="22"
            ssh_user="root"
            ssh_key=""
            custom_domain=""
            expected_customers="100"
            traffic_level="low"
            
            while [[ $# -gt 0 ]]; do
                case $1 in
                    --plan=*)
                        plan="${1#*=}"
                        shift
                        ;;
                    --ip=*)
                        vps_ip="${1#*=}"
                        shift
                        ;;
                    --ssh-port=*)
                        ssh_port="${1#*=}"
                        shift
                        ;;
                    --ssh-user=*)
                        ssh_user="${1#*=}"
                        shift
                        ;;
                    --ssh-key=*)
                        ssh_key="${1#*=}"
                        shift
                        ;;
                    --domain=*)
                        custom_domain="${1#*=}"
                        shift
                        ;;
                    --customers=*)
                        expected_customers="${1#*=}"
                        shift
                        ;;
                    --traffic=*)
                        traffic_level="${1#*=}"
                        shift
                        ;;
                    *)
                        shift
                        ;;
                esac
            done
            
            setup_vps_customer "$customer_id" "$plan" "$vps_ip" "$ssh_port" "$ssh_user" "$ssh_key" "$custom_domain" "$expected_customers" "$traffic_level"
            ;;
        validate)
            vps_ip="${2:-}"
            ssh_port="${3:-22}"
            ssh_user="${4:-root}"
            ssh_key="${5:-}"
            validate_vps_connectivity "$vps_ip" "$ssh_port" "$ssh_user" "$ssh_key"
            ;;
        requirements)
            plan="${2:-starter}"
            show_requirements "$plan"
            ;;
        health-check)
            customer_id="${2:-}"
            health_check_customer "$customer_id"
            ;;
        status)
            customer_id="${2:-}"
            get_customer_status "$customer_id"
            ;;
        *)
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"