#!/bin/bash
# DotMac Platform Backup System Installation Script

set -euo pipefail

# Configuration
DOTMAC_HOME="/home/dotmac_framework"
BACKUP_ROOT="/var/backups/dotmac"
LOG_DIR="/var/log"
CONFIG_DIR="/etc/dotmac"
SCRIPTS_DIR="$DOTMAC_HOME/scripts"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if running as root
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root. Run as the dotmac user."
        exit 1
    fi
    
    # Check required commands
    local required_commands=("python3" "docker" "systemctl" "pg_dump" "pg_restore")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            error "Required command '$cmd' not found"
            exit 1
        fi
    done
    
    # Check Python packages
    python3 -c "import cryptography, docker, boto3, redis, psycopg2, aiohttp, yaml, prometheus_client" 2>/dev/null || {
        error "Required Python packages not installed. Install with:"
        echo "pip3 install cryptography docker boto3 redis psycopg2-binary aiohttp pyyaml prometheus_client"
        exit 1
    }
    
    log "Prerequisites check passed"
}

create_directories() {
    log "Creating backup system directories..."
    
    # Create directories with appropriate permissions
    sudo mkdir -p "$BACKUP_ROOT" "$CONFIG_DIR"
    sudo chown -R "$USER:docker" "$BACKUP_ROOT"
    sudo chmod 750 "$BACKUP_ROOT"
    
    # Create subdirectories
    mkdir -p "$BACKUP_ROOT/archives" "$BACKUP_ROOT/temp"
    
    log "Directories created successfully"
}

install_system_services() {
    log "Installing systemd services..."
    
    # Copy service files
    sudo cp "$SCRIPTS_DIR/dotmac-backup.service" /etc/systemd/system/
    sudo cp "$SCRIPTS_DIR/dotmac-backup.timer" /etc/systemd/system/
    sudo cp "$SCRIPTS_DIR/dotmac-backup-monitor.service" /etc/systemd/system/
    
    # Set permissions
    sudo chmod 644 /etc/systemd/system/dotmac-backup.*
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    # Enable services
    sudo systemctl enable dotmac-backup.timer
    sudo systemctl enable dotmac-backup-monitor.service
    
    log "System services installed and enabled"
}

setup_encryption() {
    log "Setting up backup encryption..."
    
    local key_file="$CONFIG_DIR/backup.key"
    
    if [[ ! -f "$key_file" ]]; then
        # Generate encryption key
        python3 -c "
from cryptography.fernet import Fernet
import os
key = Fernet.generate_key()
os.makedirs('$CONFIG_DIR', exist_ok=True)
with open('$key_file', 'wb') as f:
    f.write(key)
print('Encryption key generated')
"
        sudo chown "$USER:docker" "$key_file"
        sudo chmod 600 "$key_file"
        log "Backup encryption key generated: $key_file"
    else
        log "Encryption key already exists: $key_file"
    fi
}

setup_configuration() {
    log "Setting up backup configuration..."
    
    local config_file="$CONFIG_DIR/backup-config.yml"
    
    if [[ ! -f "$config_file" ]]; then
        # Copy default configuration
        sudo cp "$DOTMAC_HOME/config/backup-config.yml" "$config_file"
        sudo chown "$USER:docker" "$config_file"
        sudo chmod 640 "$config_file"
        log "Default backup configuration installed: $config_file"
    else
        log "Backup configuration already exists: $config_file"
    fi
    
    # Create environment-specific overrides
    local env_config="$CONFIG_DIR/backup-config.local.yml"
    if [[ ! -f "$env_config" ]]; then
        cat > /tmp/backup-config.local.yml << 'EOF'
# Environment-specific backup configuration overrides
# This file is not tracked in version control

# Database configuration
database:
  host: "${POSTGRES_HOST:-localhost}"
  password: "${POSTGRES_PASSWORD}"

# AWS configuration (if using S3)
aws:
  bucket_name: "${BACKUP_S3_BUCKET}"
  
# Monitoring configuration
monitoring:
  notifications:
    email:
      enabled: false  # Set to true to enable email alerts
      recipients:
        - ops@your-domain.com
    slack:
      enabled: false  # Set to true to enable Slack alerts
      webhook_url: "${SLACK_BACKUP_WEBHOOK}"

# Security settings
security:
  backup_access_logs: true
EOF
        sudo mv /tmp/backup-config.local.yml "$env_config"
        sudo chown "$USER:docker" "$env_config"
        sudo chmod 640 "$env_config"
        log "Local configuration template created: $env_config"
    fi
}

setup_logrotate() {
    log "Setting up log rotation..."
    
    sudo tee /etc/logrotate.d/dotmac-backup > /dev/null << 'EOF'
/var/log/dotmac-backup.log
/var/log/dotmac-backup-monitor.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 dotmac docker
    postrotate
        systemctl reload dotmac-backup-monitor.service >/dev/null 2>&1 || true
    endscript
}
EOF
    
    log "Log rotation configured"
}

test_backup_system() {
    log "Testing backup system..."
    
    # Test backup script
    log "Testing backup script execution..."
    if python3 "$SCRIPTS_DIR/backup-system.py" --help > /dev/null 2>&1; then
        log "✓ Backup script is executable"
    else
        error "✗ Backup script test failed"
        exit 1
    fi
    
    # Test backup monitor
    log "Testing backup monitor..."
    if python3 "$SCRIPTS_DIR/backup-health-monitor.py" --help > /dev/null 2>&1; then
        log "✓ Backup monitor is executable"
    else
        error "✗ Backup monitor test failed"
        exit 1
    fi
    
    # Test configuration loading
    log "Testing configuration loading..."
    if python3 -c "
import sys
sys.path.append('$SCRIPTS_DIR')
from backup_system import DisasterRecoveryManager
dr = DisasterRecoveryManager('$CONFIG_DIR/backup-config.yml')
print('Configuration loaded successfully')
" > /dev/null 2>&1; then
        log "✓ Configuration loading works"
    else
        error "✗ Configuration loading test failed"
        exit 1
    fi
    
    log "Backup system tests passed"
}

setup_monitoring_dashboards() {
    log "Setting up monitoring dashboards..."
    
    # Create Prometheus configuration snippet
    cat > /tmp/backup-metrics.yml << 'EOF'
# DotMac Backup System Metrics Configuration
# Add this to your prometheus.yml scrape_configs section

scrape_configs:
  - job_name: 'dotmac-backup-monitor'
    static_configs:
      - targets: ['localhost:8080']
    scrape_interval: 30s
    metrics_path: /metrics
    honor_labels: true
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        replacement: 'dotmac-backup-system'
EOF
    
    # Create Grafana dashboard JSON
    cat > /tmp/backup-dashboard.json << 'EOF'
{
  "dashboard": {
    "title": "DotMac Backup System",
    "tags": ["dotmac", "backup", "disaster-recovery"],
    "panels": [
      {
        "title": "Backup Health Score",
        "type": "stat",
        "targets": [
          {
            "expr": "dotmac_backup_health_score",
            "legendFormat": "Health Score"
          }
        ]
      },
      {
        "title": "Backup Success Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(dotmac_backup_success_total[24h])",
            "legendFormat": "Success Rate"
          },
          {
            "expr": "rate(dotmac_backup_failure_total[24h])",
            "legendFormat": "Failure Rate"
          }
        ]
      },
      {
        "title": "Backup Duration",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, dotmac_backup_completion_seconds_bucket)",
            "legendFormat": "95th Percentile"
          }
        ]
      }
    ]
  }
}
EOF
    
    log "Monitoring configuration files created in /tmp/"
    log "- Prometheus config: /tmp/backup-metrics.yml"
    log "- Grafana dashboard: /tmp/backup-dashboard.json"
}

start_services() {
    log "Starting backup services..."
    
    # Start backup monitor
    sudo systemctl start dotmac-backup-monitor.service
    
    # Start backup timer
    sudo systemctl start dotmac-backup.timer
    
    # Check service status
    if sudo systemctl is-active --quiet dotmac-backup-monitor.service; then
        log "✓ Backup monitor service is running"
    else
        error "✗ Backup monitor service failed to start"
        sudo systemctl status dotmac-backup-monitor.service
        exit 1
    fi
    
    if sudo systemctl is-active --quiet dotmac-backup.timer; then
        log "✓ Backup timer is active"
    else
        error "✗ Backup timer failed to start"
        sudo systemctl status dotmac-backup.timer
        exit 1
    fi
    
    log "Backup services started successfully"
}

show_status() {
    log "Backup System Status:"
    echo
    
    # Service status
    echo "Services:"
    sudo systemctl status --no-pager -l dotmac-backup-monitor.service | grep -E "(Active|Main PID)" || true
    sudo systemctl status --no-pager -l dotmac-backup.timer | grep -E "(Active|Next)" || true
    echo
    
    # Configuration
    echo "Configuration:"
    echo "  Config file: $CONFIG_DIR/backup-config.yml"
    echo "  Encryption key: $CONFIG_DIR/backup.key"
    echo "  Backup directory: $BACKUP_ROOT"
    echo
    
    # Next backup
    echo "Next scheduled backup:"
    sudo systemctl list-timers dotmac-backup.timer --no-pager | tail -n +2 | head -n 1 || true
    echo
    
    # Health check URL
    echo "Health check endpoint: http://localhost:8080/metrics"
    echo
    
    # Logs
    echo "Recent log entries:"
    sudo journalctl -u dotmac-backup-monitor.service --no-pager -n 5 || true
}

main() {
    log "Starting DotMac Platform Backup System installation..."
    echo
    
    check_prerequisites
    create_directories
    setup_encryption
    setup_configuration
    setup_logrotate
    install_system_services
    setup_monitoring_dashboards
    test_backup_system
    start_services
    
    echo
    log "✅ DotMac Backup System installation completed successfully!"
    echo
    
    show_status
    
    echo
    log "Next steps:"
    echo "1. Review and customize configuration: $CONFIG_DIR/backup-config.yml"
    echo "2. Set up cloud storage credentials (AWS S3, Azure, or GCP)"
    echo "3. Configure notification settings (email/Slack)"
    echo "4. Add Prometheus metrics to your monitoring system"
    echo "5. Import Grafana dashboard from /tmp/backup-dashboard.json"
    echo "6. Test the backup system: sudo -u dotmac python3 $SCRIPTS_DIR/backup-system.py backup --backup-type=manual"
    echo
}

# Handle command line arguments
case "${1:-install}" in
    install)
        main
        ;;
    status)
        show_status
        ;;
    test)
        test_backup_system
        ;;
    *)
        echo "Usage: $0 {install|status|test}"
        echo
        echo "Commands:"
        echo "  install  - Install and configure the backup system (default)"
        echo "  status   - Show backup system status"
        echo "  test     - Test backup system components"
        exit 1
        ;;
esac