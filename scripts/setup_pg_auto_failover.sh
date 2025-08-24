#!/bin/bash
# Setup pg_auto_failover for PostgreSQL High Availability

set -e

# Configuration
MONITOR_HOST="monitor.dotmac.local"
MONITOR_PORT=5432
PRIMARY_HOST="postgres-primary.dotmac.local"
STANDBY_HOST="postgres-standby.dotmac.local"
REPLICATION_USER="replicator"
REPLICATION_PASSWORD="${POSTGRES_REPLICATION_PASSWORD:-changeme}"
POSTGRES_VERSION="14"

echo "=== DotMac PostgreSQL Auto-Failover Setup ==="

# Function to check prerequisites
check_prerequisites() {
    echo "Checking prerequisites..."
    
    # Check if PostgreSQL is installed
    if ! command -v psql &> /dev/null; then
        echo "Error: PostgreSQL is not installed"
        exit 1
    fi
    
    # Check if running as postgres user or sudo
    if [[ $EUID -ne 0 ]] && [[ $(whoami) != "postgres" ]]; then
        echo "This script must be run as root or postgres user"
        exit 1
    fi
}

# Install pg_auto_failover
install_pg_auto_failover() {
    echo "Installing pg_auto_failover..."
    
    if command -v apt-get &> /dev/null; then
        # Debian/Ubuntu
        sudo apt-get update
        sudo apt-get install -y postgresql-${POSTGRES_VERSION}-auto-failover
    elif command -v yum &> /dev/null; then
        # RHEL/CentOS
        sudo yum install -y pg_auto_failover_${POSTGRES_VERSION}
    else
        echo "Unsupported OS. Please install pg_auto_failover manually."
        exit 1
    fi
}

# Setup monitor node
setup_monitor() {
    echo "Setting up monitor node..."
    
    # Create monitor data directory
    MONITOR_DATA="/var/lib/postgresql/${POSTGRES_VERSION}/monitor"
    sudo -u postgres mkdir -p "$MONITOR_DATA"
    
    # Initialize monitor
    sudo -u postgres pg_autoctl create monitor \
        --pgdata "$MONITOR_DATA" \
        --pgport $MONITOR_PORT \
        --hostname "$MONITOR_HOST" \
        --auth trust \
        --ssl-self-signed \
        --skip-pg-hba
    
    # Start monitor
    sudo -u postgres pg_autoctl run \
        --pgdata "$MONITOR_DATA" \
        --daemonize
    
    echo "Monitor node initialized at $MONITOR_HOST:$MONITOR_PORT"
}

# Setup primary node
setup_primary() {
    echo "Setting up primary node..."
    
    PRIMARY_DATA="/var/lib/postgresql/${POSTGRES_VERSION}/primary"
    
    # Create formation
    sudo -u postgres pg_autoctl create postgres \
        --pgdata "$PRIMARY_DATA" \
        --pgport 5432 \
        --hostname "$PRIMARY_HOST" \
        --auth trust \
        --ssl-self-signed \
        --monitor "postgres://autoctl_node@$MONITOR_HOST:$MONITOR_PORT/pg_auto_failover" \
        --formation default \
        --group 0 \
        --name primary
    
    # Configure replication settings
    cat >> "$PRIMARY_DATA/postgresql.conf" <<EOF

# Auto-failover replication settings
max_replication_slots = 10
max_wal_senders = 10
wal_level = replica
hot_standby = on
wal_log_hints = on
shared_preload_libraries = 'pg_stat_statements,pgautofailover'

# Connection settings for failover
listen_addresses = '*'
EOF

    # Start primary
    sudo -u postgres pg_autoctl run \
        --pgdata "$PRIMARY_DATA" \
        --daemonize
    
    echo "Primary node setup complete"
}

# Setup standby node
setup_standby() {
    echo "Setting up standby node..."
    
    STANDBY_DATA="/var/lib/postgresql/${POSTGRES_VERSION}/standby"
    
    # Join formation as secondary
    sudo -u postgres pg_autoctl create postgres \
        --pgdata "$STANDBY_DATA" \
        --pgport 5432 \
        --hostname "$STANDBY_HOST" \
        --auth trust \
        --ssl-self-signed \
        --monitor "postgres://autoctl_node@$MONITOR_HOST:$MONITOR_PORT/pg_auto_failover" \
        --formation default \
        --group 0 \
        --name standby
    
    # Start standby
    sudo -u postgres pg_autoctl run \
        --pgdata "$STANDBY_DATA" \
        --daemonize
    
    echo "Standby node setup complete"
}

# Create systemd services
create_systemd_services() {
    echo "Creating systemd services..."
    
    # Monitor service
    cat > /etc/systemd/system/pg_autoctl_monitor.service <<EOF
[Unit]
Description=pg_auto_failover Monitor
After=network.target

[Service]
Type=notify
User=postgres
Group=postgres
Environment="PGDATA=/var/lib/postgresql/${POSTGRES_VERSION}/monitor"
ExecStart=/usr/bin/pg_autoctl run
Restart=always
RestartSec=10
StartLimitBurst=0

[Install]
WantedBy=multi-user.target
EOF

    # Primary service
    cat > /etc/systemd/system/pg_autoctl_primary.service <<EOF
[Unit]
Description=pg_auto_failover Primary Node
After=network.target pg_autoctl_monitor.service

[Service]
Type=notify
User=postgres
Group=postgres
Environment="PGDATA=/var/lib/postgresql/${POSTGRES_VERSION}/primary"
ExecStart=/usr/bin/pg_autoctl run
Restart=always
RestartSec=10
StartLimitBurst=0

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    systemctl daemon-reload
    
    # Enable services
    systemctl enable pg_autoctl_monitor.service
    systemctl enable pg_autoctl_primary.service
    
    echo "Systemd services created and enabled"
}

# Show cluster status
show_status() {
    echo ""
    echo "=== Cluster Status ==="
    sudo -u postgres pg_autoctl show state \
        --pgdata "/var/lib/postgresql/${POSTGRES_VERSION}/primary"
    
    echo ""
    echo "=== Connection Info ==="
    echo "Monitor: postgres://autoctl_node@$MONITOR_HOST:$MONITOR_PORT/pg_auto_failover"
    echo "Primary: postgres://$PRIMARY_HOST:5432/postgres"
    echo "Standby: postgres://$STANDBY_HOST:5432/postgres"
}

# Main execution
main() {
    check_prerequisites
    
    echo "Select installation mode:"
    echo "1) Full setup (monitor + primary + standby)"
    echo "2) Monitor only"
    echo "3) Primary only"
    echo "4) Standby only"
    echo "5) Show status"
    read -p "Enter choice [1-5]: " choice
    
    case $choice in
        1)
            install_pg_auto_failover
            setup_monitor
            setup_primary
            setup_standby
            create_systemd_services
            show_status
            ;;
        2)
            install_pg_auto_failover
            setup_monitor
            ;;
        3)
            install_pg_auto_failover
            setup_primary
            ;;
        4)
            install_pg_auto_failover
            setup_standby
            ;;
        5)
            show_status
            ;;
        *)
            echo "Invalid choice"
            exit 1
            ;;
    esac
    
    echo ""
    echo "=== Setup Complete ==="
    echo "To perform a manual failover: pg_autoctl perform switchover"
    echo "To check status: pg_autoctl show state"
}

# Run main function
main
