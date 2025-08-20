#!/bin/bash
# Initialize OpenWISP RADIUS Integration
# This script sets up the initial configuration for OpenWISP RADIUS integration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
POSTGRES_HOST=${POSTGRES_HOST:-postgres}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_USER=${POSTGRES_USER:-dotmac}
POSTGRES_PASS=${POSTGRES_PASS:-dotmac_secure_password}
OPENWISP_DB=${OPENWISP_DB:-openwisp_radius}

# Wait for PostgreSQL to be ready
wait_for_postgres() {
    log_info "Waiting for PostgreSQL to be ready..."
    
    for i in {1..30}; do
        if pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" >/dev/null 2>&1; then
            log_success "PostgreSQL is ready"
            return 0
        fi
        
        log_info "Waiting for PostgreSQL... (attempt $i/30)"
        sleep 2
    done
    
    log_error "PostgreSQL did not become ready in time"
    return 1
}

# Create OpenWISP database if it doesn't exist
create_openwisp_database() {
    log_info "Creating OpenWISP database if it doesn't exist..."
    
    PGPASSWORD="$POSTGRES_PASS" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -c \
        "SELECT 1 FROM pg_database WHERE datname = '$OPENWISP_DB'" | grep -q 1 || \
    PGPASSWORD="$POSTGRES_PASS" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -c \
        "CREATE DATABASE $OPENWISP_DB;"
    
    log_success "OpenWISP database ready"
}

# Create FreeRADIUS configuration directory
create_freeradius_config() {
    log_info "Creating FreeRADIUS configuration structure..."
    
    mkdir -p /home/dotmac_framework/openwisp/freeradius/{clients,nas,users,policies}
    
    # Create basic clients.conf
    cat > /home/dotmac_framework/openwisp/freeradius/clients/clients.conf << 'EOF'
# RADIUS Clients Configuration
# This file is managed by OpenWISP RADIUS
# Manual changes will be overwritten

# Default client for testing
client localhost {
    ipaddr = 127.0.0.1
    secret = testing123
    require_message_authenticator = yes
    nas_type = other
    shortname = localhost
}

# Include additional client configurations
$INCLUDE /etc/freeradius/3.0/mods-config/sql/main/postgresql/clients.conf
EOF

    # Create basic NAS configuration
    cat > /home/dotmac_framework/openwisp/freeradius/nas/nas.conf << 'EOF'
# Network Access Server (NAS) Configuration
# Managed by DotMac Networking module

# This file contains NAS-specific settings
# Client definitions are in clients.conf
EOF

    # Set permissions
    chmod -R 644 /home/dotmac_framework/openwisp/freeradius/
    
    log_success "FreeRADIUS configuration structure created"
}

# Create OpenWISP environment file
create_openwisp_env() {
    log_info "Creating OpenWISP environment configuration..."
    
    cat > /home/dotmac_framework/.env.openwisp << EOF
# OpenWISP RADIUS Configuration
OPENWISP_RADIUS_API_URL=http://openwisp-radius:8000/api/v1/
OPENWISP_RADIUS_TOKEN=change-this-api-token-in-production
OPENWISP_ADMIN_USERNAME=admin
OPENWISP_ADMIN_EMAIL=admin@dotmac.local
OPENWISP_ADMIN_PASSWORD=change-this-admin-password

# FreeRADIUS Configuration  
FREERADIUS_HOST=openwisp-freeradius
FREERADIUS_AUTH_PORT=1812
FREERADIUS_ACCT_PORT=1813
FREERADIUS_COA_PORT=3799
FREERADIUS_SECRET=dotmac-radius-secret

# Database Configuration
DATABASE_URL=postgresql://$POSTGRES_USER:$POSTGRES_PASS@$POSTGRES_HOST:$POSTGRES_PORT/$OPENWISP_DB
RADIUS_DATABASE_URL=postgresql://$POSTGRES_USER:$POSTGRES_PASS@$POSTGRES_HOST:$POSTGRES_PORT/$OPENWISP_DB

# Redis Configuration (for sessions and caching)
REDIS_URL=redis://redis:6379/9
CELERY_BROKER_URL=redis://redis:6379/10

# Security
SECRET_KEY=$(openssl rand -hex 32)
DJANGO_SECRET_KEY=$(openssl rand -hex 32)

# Email Configuration (for user notifications)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=localhost
EMAIL_PORT=25

# Debug (set to false in production)
DEBUG=false
DJANGO_DEBUG=false

# Allowed hosts
ALLOWED_HOSTS=localhost,127.0.0.1,openwisp-radius,dotmac-openwisp-radius

# Language and timezone
LANGUAGE_CODE=en-us
TIME_ZONE=UTC
EOF

    log_success "OpenWISP environment file created"
}

# Wait for OpenWISP RADIUS to be ready and create superuser
setup_openwisp_admin() {
    log_info "Waiting for OpenWISP RADIUS to be ready..."
    
    # Wait for OpenWISP service
    for i in {1..60}; do
        if curl -sf http://localhost:8010/admin/login/ >/dev/null 2>&1; then
            log_success "OpenWISP RADIUS is ready"
            break
        fi
        
        if [ $i -eq 60 ]; then
            log_error "OpenWISP RADIUS did not become ready in time"
            return 1
        fi
        
        log_info "Waiting for OpenWISP RADIUS... (attempt $i/60)"
        sleep 5
    done
    
    # Create superuser via API (if possible) or provide instructions
    log_info "OpenWISP RADIUS is ready. Please create admin user manually:"
    log_info "1. Visit: http://localhost:8010/admin/"
    log_info "2. Or run: docker exec dotmac-openwisp-radius python manage.py createsuperuser"
}

# Create sample RADIUS clients for testing
create_sample_clients() {
    log_info "Creating sample RADIUS clients configuration..."
    
    cat > /home/dotmac_framework/sample-radius-clients.json << 'EOF'
{
  "sample_clients": [
    {
      "name": "Test BNG",
      "ip_address": "192.168.1.10",
      "secret": "bng-secret-123",
      "nas_type": "bng",
      "description": "Test Broadband Network Gateway"
    },
    {
      "name": "Test OLT",
      "ip_address": "192.168.1.20", 
      "secret": "olt-secret-456",
      "nas_type": "olt",
      "description": "Test Optical Line Terminal"
    },
    {
      "name": "Test WiFi Controller",
      "ip_address": "192.168.1.30",
      "secret": "wifi-secret-789", 
      "nas_type": "wifi",
      "description": "Test WiFi Access Controller"
    }
  ]
}
EOF

    log_success "Sample RADIUS clients configuration created"
    log_info "Use sample-radius-clients.json to add test clients to OpenWISP"
}

# Print integration status
print_integration_status() {
    log_success "OpenWISP RADIUS Integration Setup Complete!"
    echo
    log_info "Services:"
    log_info "  - OpenWISP RADIUS UI: http://localhost:8010/admin/"
    log_info "  - FreeRADIUS Server: localhost:1812 (auth), localhost:1813 (acct)"
    log_info "  - DotMac Networking: http://localhost:8006/"
    echo
    log_info "Next Steps:"
    log_info "  1. Create OpenWISP admin user"
    log_info "  2. Add RADIUS clients via OpenWISP admin or API"
    log_info "  3. Create test users for authentication"
    log_info "  4. Test RADIUS authentication via DotMac networking API"
    echo
    log_info "Configuration Files:"
    log_info "  - Environment: .env.openwisp" 
    log_info "  - FreeRADIUS: openwisp/freeradius/"
    log_info "  - Sample clients: sample-radius-clients.json"
    echo
    log_warn "IMPORTANT: Change default passwords and secrets in production!"
}

# Main execution
main() {
    log_info "Starting OpenWISP RADIUS Integration Setup..."
    
    wait_for_postgres
    create_openwisp_database
    create_freeradius_config
    create_openwisp_env
    create_sample_clients
    
    # Note: OpenWISP admin setup requires the service to be running
    # This will be done after containers start
    
    print_integration_status
}

# Run main function
main "$@"