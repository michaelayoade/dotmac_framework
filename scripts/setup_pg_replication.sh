#!/bin/bash

# PostgreSQL Streaming Replication Setup (Alternative to pg_auto_failover)
# Uses native PostgreSQL replication with manual failover capability

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "═══════════════════════════════════════════════════════════"
echo "     PostgreSQL Streaming Replication Setup"
echo "═══════════════════════════════════════════════════════════"
echo

# Configuration
REPLICATION_USER="${REPLICATION_USER:-replicator}"
REPLICATION_PASSWORD="${REPLICATION_PASSWORD:-}"
PRIMARY_HOST="${PRIMARY_HOST:-}"
PRIMARY_PORT="${PRIMARY_PORT:-5432}"
STANDBY_PORT="${STANDBY_PORT:-5433}"
DATA_DIR="${DATA_DIR:-/var/lib/postgresql/14/main}"
BACKUP_DIR="${BACKUP_DIR:-/var/lib/postgresql/backups}"

show_menu() {
    echo "Select setup mode:"
    echo "1) Configure Primary Server"
    echo "2) Configure Standby Server"
    echo "3) Check Replication Status"
    echo "4) Perform Manual Failover"
    echo "5) Exit"
    echo
    read -p "Enter choice [1-5]: " choice
}

setup_primary() {
    echo "Setting up PRIMARY server..."
    
    # Get replication password
    if [ -z "$REPLICATION_PASSWORD" ]; then
        read -sp "Enter replication password: " REPLICATION_PASSWORD
        echo
    fi
    
    # Create replication user
    sudo -u postgres psql -c "CREATE USER $REPLICATION_USER REPLICATION LOGIN ENCRYPTED PASSWORD '$REPLICATION_PASSWORD';" 2>/dev/null || \
    sudo -u postgres psql -c "ALTER USER $REPLICATION_USER REPLICATION LOGIN ENCRYPTED PASSWORD '$REPLICATION_PASSWORD';"
    
    # Update postgresql.conf
    PG_CONF="/etc/postgresql/14/main/postgresql.conf"
    
    echo "Updating PostgreSQL configuration..."
    sudo tee -a "$PG_CONF" > /dev/null <<EOF

# Replication Settings (Added by setup script)
wal_level = replica
max_wal_senders = 10
wal_keep_segments = 64
max_replication_slots = 10
hot_standby = on
archive_mode = on
archive_command = 'test ! -f $BACKUP_DIR/%f && cp %p $BACKUP_DIR/%f'
EOF
    
    # Create backup directory
    sudo mkdir -p "$BACKUP_DIR"
    sudo chown postgres:postgres "$BACKUP_DIR"
    
    # Update pg_hba.conf for replication
    PG_HBA="/etc/postgresql/14/main/pg_hba.conf"
    echo "host    replication     $REPLICATION_USER     0.0.0.0/0     scram-sha-256" | sudo tee -a "$PG_HBA"
    
    # Create replication slot
    sudo -u postgres psql -c "SELECT * FROM pg_create_physical_replication_slot('standby_slot');"
    
    # Restart PostgreSQL
    sudo systemctl restart postgresql
    
    echo -e "${GREEN}✓${NC} Primary server configured successfully"
    echo
    echo "Primary server details:"
    echo "  Replication user: $REPLICATION_USER"
    echo "  Replication slot: standby_slot"
    echo "  Archive directory: $BACKUP_DIR"
}

setup_standby() {
    echo "Setting up STANDBY server..."
    
    # Get primary server details
    if [ -z "$PRIMARY_HOST" ]; then
        read -p "Enter primary server IP/hostname: " PRIMARY_HOST
    fi
    
    if [ -z "$REPLICATION_PASSWORD" ]; then
        read -sp "Enter replication password: " REPLICATION_PASSWORD
        echo
    fi
    
    # Stop PostgreSQL
    sudo systemctl stop postgresql
    
    # Backup existing data directory
    if [ -d "$DATA_DIR" ]; then
        sudo mv "$DATA_DIR" "${DATA_DIR}.backup.$(date +%Y%m%d%H%M%S)"
    fi
    
    # Base backup from primary
    echo "Creating base backup from primary..."
    sudo -u postgres pg_basebackup \
        -h "$PRIMARY_HOST" \
        -p "$PRIMARY_PORT" \
        -U "$REPLICATION_USER" \
        -D "$DATA_DIR" \
        -Fp -Xs -R -P \
        -S standby_slot
    
    # Create standby.signal
    sudo -u postgres touch "$DATA_DIR/standby.signal"
    
    # Update postgresql.auto.conf
    sudo -u postgres tee "$DATA_DIR/postgresql.auto.conf" > /dev/null <<EOF
# Standby configuration
primary_conninfo = 'host=$PRIMARY_HOST port=$PRIMARY_PORT user=$REPLICATION_USER password=$REPLICATION_PASSWORD'
primary_slot_name = 'standby_slot'
recovery_target_timeline = 'latest'
EOF
    
    # Update port if different
    if [ "$STANDBY_PORT" != "5432" ]; then
        echo "port = $STANDBY_PORT" | sudo tee -a "/etc/postgresql/14/main/postgresql.conf"
    fi
    
    # Start PostgreSQL
    sudo systemctl start postgresql
    
    echo -e "${GREEN}✓${NC} Standby server configured successfully"
}

check_status() {
    echo "Checking replication status..."
    echo
    
    # Check if this is primary or standby
    IS_PRIMARY=$(sudo -u postgres psql -t -c "SELECT pg_is_in_recovery();" | tr -d ' ')
    
    if [ "$IS_PRIMARY" = "f" ]; then
        echo -e "${GREEN}This is a PRIMARY server${NC}"
        echo
        echo "Replication slots:"
        sudo -u postgres psql -c "SELECT slot_name, active, restart_lsn FROM pg_replication_slots;"
        echo
        echo "Connected standbys:"
        sudo -u postgres psql -c "SELECT client_addr, state, sync_state FROM pg_stat_replication;"
        echo
        echo "WAL sender processes:"
        sudo -u postgres psql -c "SELECT pid, usename, client_addr, state FROM pg_stat_activity WHERE backend_type = 'walsender';"
    else
        echo -e "${YELLOW}This is a STANDBY server${NC}"
        echo
        echo "Recovery status:"
        sudo -u postgres psql -c "SELECT pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn(), pg_last_xact_replay_timestamp();"
        echo
        echo "Replication lag:"
        sudo -u postgres psql -c "SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) AS lag_seconds;"
    fi
}

perform_failover() {
    echo -e "${YELLOW}WARNING: Manual failover process${NC}"
    echo "This will promote the standby to primary"
    echo
    read -p "Are you sure you want to proceed? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        echo "Failover cancelled"
        return
    fi
    
    # Check if this is a standby
    IS_STANDBY=$(sudo -u postgres psql -t -c "SELECT pg_is_in_recovery();" | tr -d ' ')
    
    if [ "$IS_STANDBY" = "f" ]; then
        echo -e "${RED}This server is already a primary!${NC}"
        return
    fi
    
    echo "Promoting standby to primary..."
    sudo -u postgres pg_ctl promote -D "$DATA_DIR"
    
    # Remove standby configuration
    sudo rm -f "$DATA_DIR/standby.signal"
    
    echo -e "${GREEN}✓${NC} Standby promoted to primary"
    echo
    echo "Next steps:"
    echo "1. Update application connection strings"
    echo "2. Reconfigure old primary as new standby (if needed)"
    echo "3. Update monitoring and alerting"
}

# Main menu loop
while true; do
    show_menu
    
    case $choice in
        1) setup_primary ;;
        2) setup_standby ;;
        3) check_status ;;
        4) perform_failover ;;
        5) echo "Exiting..."; exit 0 ;;
        *) echo -e "${RED}Invalid option${NC}" ;;
    esac
    
    echo
    read -p "Press Enter to continue..."
    echo
done
