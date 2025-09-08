#!/bin/bash
# Monitoring Setup Script for DotMac Framework

set -e

# SigNoz-only monitoring setup

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}$1${NC}"
}

# Check if Docker and Docker Compose are installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_status "Docker and Docker Compose are available"
}

# Check if main DotMac network exists
check_dotmac_network() {
    if ! docker network ls | grep -q dotmac-network; then
        print_warning "DotMac network does not exist. Creating it..."
        docker network create dotmac-network
        print_status "Created dotmac-network"
    else
        print_status "DotMac network exists"
    fi
}

# Create monitoring configuration directories
setup_directories() {
    print_status "Setting up monitoring directories..."
    
    local dirs=("monitoring/loki" "monitoring/promtail" "monitoring/alertmanager/templates" "monitoring/blackbox" "monitoring/snmp")
    
    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
        print_status "Created directory: $dir"
    done
}

# Create Grafana provisioning files
setup_grafana_provisioning() { :; }

# Create Loki configuration
setup_loki_config() {
    print_status "Setting up Loki configuration..."
    
    cat > monitoring/loki/loki.yml << 'EOF'
auth_enabled: false

server:
  http_listen_port: 3100

common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

query_range:
  results_cache:
    cache:
      embedded_cache:
        enabled: true
        max_size_mb: 100

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

ruler:
  alertmanager_url: http://alertmanager:9093
EOF

    print_status "Loki configuration created"
}

# Create Promtail configuration
setup_promtail_config() {
    print_status "Setting up Promtail configuration..."
    
    cat > monitoring/promtail/promtail.yml << 'EOF'
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: containers
    static_configs:
      - targets:
          - localhost
        labels:
          job: containerlogs
          __path__: /var/lib/docker/containers/*/*log
    pipeline_stages:
      - json:
          expressions:
            output: log
            stream: stream
            attrs:
      - json:
          expressions:
            tag:
          source: attrs
      - regex:
          expression: (?P<container_name>(?:[^|]*/)*(?P<image_name>[^|:]+)(?::[^|]+)?)
          source: tag
      - timestamp:
          format: RFC3339Nano
          source: time
      - labels:
          stream:
          container_name:
          image_name:
      - output:
          source: output

  - job_name: syslog
    static_configs:
      - targets:
          - localhost
        labels:
          job: syslog
          __path__: /var/log/syslog
EOF

    print_status "Promtail configuration created"
}

# Create Blackbox exporter configuration
setup_blackbox_config() {
    print_status "Setting up Blackbox exporter configuration..."
    
    cat > monitoring/blackbox/blackbox.yml << 'EOF'
modules:
  http_2xx:
    prober: http
    timeout: 5s
    http:
      valid_http_versions: ["HTTP/1.1", "HTTP/2.0"]
      valid_status_codes: []
      method: GET
      headers:
        Host: localhost
      no_follow_redirects: false
      fail_if_ssl: false
      fail_if_not_ssl: false
      
  http_post_2xx:
    prober: http
    timeout: 5s
    http:
      valid_http_versions: ["HTTP/1.1", "HTTP/2.0"]
      method: POST
      headers:
        Content-Type: application/json
      body: '{}'
      
  tcp_connect:
    prober: tcp
    timeout: 5s
    
  icmp:
    prober: icmp
    timeout: 5s
    icmp:
      preferred_ip_protocol: "ip4"
EOF

    print_status "Blackbox exporter configuration created"
}

# Create SNMP exporter configuration (for ISP network monitoring)
setup_snmp_config() {
    print_status "Setting up SNMP exporter configuration..."
    
    cat > monitoring/snmp/snmp.yml << 'EOF'
auths:
  public_v2:
    community: public
    security_level: noAuthNoPriv
    auth_protocol: MD5
    priv_protocol: DES
    version: 2

modules:
  if_mib:
    walk:
      - 1.3.6.1.2.1.2.2.1.2   # ifDescr
      - 1.3.6.1.2.1.2.2.1.3   # ifType
      - 1.3.6.1.2.1.2.2.1.5   # ifSpeed
      - 1.3.6.1.2.1.2.2.1.8   # ifOperStatus
      - 1.3.6.1.2.1.2.2.1.10  # ifInOctets
      - 1.3.6.1.2.1.2.2.1.16  # ifOutOctets
    lookups:
      - source_indexes: [ifIndex]
        lookup: 1.3.6.1.2.1.2.2.1.2
        drop_source_indexes: true
    auth:
      community: public
EOF

    print_status "SNMP exporter configuration created"
}

# Create environment file template
create_monitoring_env() {
    print_status "Creating monitoring environment template..."
    
    cat > monitoring/.env.monitoring.template << 'EOF'
# Monitoring Stack Environment Variables for DotMac Framework
# Configure only the services you actually use

# ===== GRAFANA CONFIGURATION =====
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=change-this-secure-password

# ===== DATABASE CONNECTIONS =====
# These should match your main application configuration
POSTGRES_PASSWORD=your-postgres-password
REDIS_PASSWORD=your-redis-password

# ===== EMAIL NOTIFICATIONS (Optional) =====
# Configure if you want email alerts
# SMTP_SMARTHOST=smtp.gmail.com:587
# SMTP_FROM=alerts@yourdomain.com
# SMTP_AUTH_USERNAME=your-email@gmail.com
# SMTP_AUTH_PASSWORD=your-app-password
# DEFAULT_EMAIL_TO=admin@yourdomain.com
# CRITICAL_EMAIL_TO=oncall@yourdomain.com

# ===== WEBHOOK NOTIFICATIONS (Optional) =====
# Generic webhook - works with Discord, Teams, Mattermost, etc.
# DEFAULT_WEBHOOK_URL=https://your-webhook-service.com/webhook
# CRITICAL_WEBHOOK_URL=https://your-emergency-webhook.com/webhook
# WEBHOOK_USERNAME=optional-basic-auth-username
# WEBHOOK_PASSWORD=optional-basic-auth-password

# ===== INCIDENT MANAGEMENT (Optional) =====
# PagerDuty
# CRITICAL_WEBHOOK_URL=https://events.pagerduty.com/v2/enqueue
# PAGERDUTY_INTEGRATION_KEY=your-integration-key

# OpsGenie
# CRITICAL_WEBHOOK_URL=https://api.opsgenie.com/v2/alerts
# OPSGENIE_API_KEY=your-api-key

# ===== TEAM-SPECIFIC NOTIFICATIONS (Optional) =====
# DATABASE_TEAM_EMAIL=database-team@yourdomain.com
# DATABASE_TEAM_WEBHOOK=https://your-db-team-webhook.com
# DEV_TEAM_EMAIL=dev-team@yourdomain.com

# ===== SMS NOTIFICATIONS (Optional) =====
# Via Twilio or similar service
# SMS_WEBHOOK_URL=https://api.twilio.com/2010-04-01/Accounts/YOUR_ACCOUNT/Messages.json
# SMS_USERNAME=your-twilio-account-sid
# SMS_PASSWORD=your-twilio-auth-token

# See monitoring/NOTIFICATION_PROVIDERS.md for detailed setup instructions
EOF

    if [ ! -f "monitoring/.env.monitoring" ]; then
        cp monitoring/.env.monitoring.template monitoring/.env.monitoring
        print_warning "Created monitoring/.env.monitoring from template. Please update with your actual values."
    fi
}

# Start monitoring stack
start_monitoring() {
    print_status "Starting monitoring stack..."
    
    # Load environment variables
    if [ -f "monitoring/.env.monitoring" ]; then
        export $(cat monitoring/.env.monitoring | xargs)
    fi
    
    # Start monitoring services
    docker-compose -f monitoring/docker-compose.monitoring.yml up -d
    
    print_status "Monitoring stack started successfully!"
}

# Show access URLs
show_urls() {
    print_header "\n🎯 MONITORING SERVICES ACCESS"
    echo
    : # Grafana not used
    echo "   Default login: admin / (password from .env.monitoring)"
    echo
    print_status "Prometheus: http://localhost:9090"
    echo "   Metrics collection and querying"
    echo
    print_status "AlertManager: http://localhost:9093"
    echo "   Alert routing and notifications"
    echo
    print_status "Jaeger Tracing: http://localhost:16686"
    echo "   Distributed tracing visualization"
    echo
    print_status "Kibana (if using ELK): http://localhost:5601"
    echo "   Log analysis and visualization"
    echo
}

# Verify monitoring stack health
verify_monitoring() {
    print_status "Verifying monitoring stack health..."
    
    local services=(
        "prometheus:9090"
        "grafana:3000"
        "alertmanager:9093"
    )
    
    sleep 30  # Wait for services to start
    
    for service in "${services[@]}"; do
        local name=$(echo $service | cut -d: -f1)
        local port=$(echo $service | cut -d: -f2)
        
        if curl -f -s "http://localhost:$port" > /dev/null; then
            print_status "✅ $name is healthy"
        else
            print_warning "⚠️ $name might not be ready yet"
        fi
    done
}

# Main execution
main() {
    print_header "📊 DotMac Framework - Monitoring Stack Setup"
    echo "This script will set up a comprehensive monitoring solution"
    echo "including SigNoz (default)."
    echo "========================================================"
    echo
    
    # Run setup steps
    check_docker
    check_dotmac_network
    setup_directories
    setup_grafana_provisioning
    setup_loki_config
    setup_promtail_config
    setup_blackbox_config
    setup_snmp_config
    create_monitoring_env
    
    echo
    print_header "🚀 Ready to start monitoring stack"
    read -p "Do you want to start the monitoring services now? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        start_monitoring
        verify_monitoring
        show_urls
        
        print_header "\n✅ MONITORING SETUP COMPLETE!"
        print_status "All monitoring services are now running."
        print_status "Check the URLs above to access different services."
        echo
        print_warning "Remember to:"
        echo "  1. Update monitoring/.env.monitoring with your actual values"
        echo "  2. Configure your Slack/email notifications in AlertManager"
        : # Grafana not used
        echo "  4. Set up retention policies based on your storage requirements"
    else
        print_status "Monitoring configuration complete. Run the following to start:"
        echo "  docker-compose -f monitoring/docker-compose.monitoring.yml up -d"
    fi
}

# Run main function
main "$@"
