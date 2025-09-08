#!/bin/bash
# DotMac Framework Production Deployment Script
# Phase 4: Production Readiness

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CONFIG_DIR="${SCRIPT_DIR}/production-config"

echo "🚀 Starting DotMac Framework Production Deployment"
echo "Project Root: ${PROJECT_ROOT}"
echo "Config Directory: ${CONFIG_DIR}"

# Check prerequisites
check_prerequisites() {
    echo "🔍 Checking prerequisites..."
    
    # Check if running as root for system services
    if [[ $EUID -ne 0 ]]; then
        echo "❌ This script must be run as root for system service installation"
        exit 1
    fi
    
    # Check required commands
    local required_commands=("docker" "docker-compose" "systemctl" "nginx")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            echo "❌ Required command '$cmd' not found"
            exit 1
        fi
    done
    
    echo "✅ Prerequisites check passed"
}

# Create application user and directories
setup_system() {
    echo "🔧 Setting up system configuration..."
    
    # Create dotmac user if doesn't exist
    if ! id "dotmac" &>/dev/null; then
        useradd -r -m -s /bin/bash dotmac
        usermod -aG docker dotmac
    fi
    
    # Create application directories
    mkdir -p /opt/dotmac/{logs,config,data}
    chown -R dotmac:dotmac /opt/dotmac
    
    # Copy application code (assuming it's in /tmp/dotmac-deploy)
    if [[ -d "/tmp/dotmac-deploy" ]]; then
        cp -r /tmp/dotmac-deploy/* /opt/dotmac/
        chown -R dotmac:dotmac /opt/dotmac
    fi
    
    echo "✅ System setup completed"
}

# Install and configure services
install_services() {
    echo "🏗️ Installing systemd services..."
    
    # Copy service files
    cp "${CONFIG_DIR}/systemd/"*.service /etc/systemd/system/
    
    # Reload systemd and enable services
    systemctl daemon-reload
    systemctl enable dotmac-management.service
    systemctl enable dotmac-isp.service
    systemctl enable dotmac-workflow-monitor.service
    
    echo "✅ Services installed"
}

# Configure Nginx
configure_nginx() {
    echo "🌐 Configuring Nginx..."
    
    # Backup existing configuration
    if [[ -f "/etc/nginx/sites-available/default" ]]; then
        cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup
    fi
    
    # Install DotMac configuration
    cp "${CONFIG_DIR}/nginx.conf" /etc/nginx/sites-available/dotmac
    ln -sf /etc/nginx/sites-available/dotmac /etc/nginx/sites-enabled/
    
    # Test configuration
    nginx -t
    
    # Reload Nginx
    systemctl reload nginx
    
    echo "✅ Nginx configured"
}

# Deploy with Docker Compose
deploy_docker() {
    echo "🐳 Deploying with Docker Compose..."
    
    cd "${PROJECT_ROOT}"
    
    # Copy production compose file
    cp "${CONFIG_DIR}/docker-compose.production.yml" ./
    
    # Copy environment file
    cp "${CONFIG_DIR}/.env.production" ./
    
    echo "⚠️  IMPORTANT: Please update the .env.production file with your actual passwords!"
    echo "Required changes:"
    echo "  - POSTGRES_PASSWORD"
    echo "  - GRAFANA_ADMIN_PASSWORD"
    echo "  - SECRET_KEY"
    echo "  - JWT_SECRET_KEY"
    echo ""
    read -p "Have you updated the .env.production file? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Please update the .env.production file before continuing"
        exit 1
    fi
    
    # Build and start services
    docker-compose -f docker-compose.production.yml build
    docker-compose -f docker-compose.production.yml up -d
    
    echo "✅ Docker services deployed"
}

# Run database migrations
run_migrations() {
    echo "🗄️ Running database migrations..."
    
    # Wait for database to be ready
    echo "Waiting for database to be ready..."
    sleep 30
    
    # Run migrations
    cd "${PROJECT_ROOT}"
    docker-compose -f docker-compose.production.yml exec dotmac-management /opt/dotmac/.venv/bin/alembic upgrade head
    
    echo "✅ Database migrations completed"
}

# Verify deployment
verify_deployment() {
    echo "✅ Verifying deployment..."
    
    # Check systemd services
    echo "Checking systemd services..."
    systemctl is-active --quiet dotmac-management && echo "✅ dotmac-management service is running" || echo "❌ dotmac-management service failed"
    systemctl is-active --quiet dotmac-isp && echo "✅ dotmac-isp service is running" || echo "❌ dotmac-isp service failed"
    
    # Check Docker services
    echo "Checking Docker services..."
    cd "${PROJECT_ROOT}"
    docker-compose -f docker-compose.production.yml ps
    
    # Check health endpoints
    echo "Checking health endpoints..."
    sleep 10
    curl -f http://localhost:8000/api/workflows/health && echo "✅ Management health check passed" || echo "❌ Management health check failed"
    curl -f http://localhost:8001/health && echo "✅ ISP health check passed" || echo "❌ ISP health check failed"
    
    echo "✅ Deployment verification completed"
}

# Main deployment flow
main() {
    check_prerequisites
    setup_system
    install_services
    configure_nginx
    deploy_docker
    run_migrations
    verify_deployment
    
    echo ""
    echo "🎉 DotMac Framework Production Deployment Complete!"
    echo ""
    echo "Access points:"
    echo "  • Management API: https://api.yourdomain.com/api/management"
    echo "  • ISP API: https://api.yourdomain.com/api/isp"
    echo "  • Grafana: http://monitoring.internal:8080/grafana"
    echo "  • Prometheus: http://monitoring.internal:8080/prometheus"
    echo ""
    echo "Next steps:"
    echo "  1. Configure SSL certificates"
    echo "  2. Update DNS records"
    echo "  3. Configure monitoring alerts"
    echo "  4. Set up backup schedules"
    echo ""
}

# Run main function
main "$@"
