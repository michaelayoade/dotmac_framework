#!/bin/bash
# Backup System Setup Script for DotMac Framework
# Sets up automated backup scheduling and monitoring

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_BASE_DIR="${BACKUP_DIR:-/opt/dotmac/backups}"

# Functions for colored output
print_status() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_header() { echo -e "${BLUE}$1${NC}"; }
print_step() { echo -e "${PURPLE}[STEP]${NC} $1"; }

# Usage function
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --schedule SCHEDULE    Backup schedule: daily|weekly|custom (default: daily)"
    echo "  --retention DAYS       Backup retention in days (default: 30)"
    echo "  --remote-storage TYPE  Remote storage: s3|gcs|rsync|none (default: none)"
    echo "  --encrypt              Enable backup encryption"
    echo "  --monitor              Enable backup monitoring"
    echo "  --help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                           # Basic daily backup setup"
    echo "  $0 --schedule weekly         # Weekly backups"
    echo "  $0 --remote-storage s3       # Enable S3 upload"
    echo "  $0 --encrypt --monitor       # Full featured setup"
}

# Check requirements
check_requirements() {
    print_step "Checking requirements..."
    
    # Check if running with sudo
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run with sudo privileges"
        exit 1
    fi
    
    # Check backup script exists
    if [ ! -f "$SCRIPT_DIR/backup.sh" ]; then
        print_error "Backup script not found: $SCRIPT_DIR/backup.sh"
        exit 1
    fi
    
    # Check disk space (minimum 10GB)
    local available_space=$(df / | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 10485760 ]; then
        print_warning "Less than 10GB disk space available"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
    fi
    
    print_status "Requirements check completed"
}

# Setup backup directories
setup_directories() {
    print_step "Setting up backup directories..."
    
    # Create main backup directory structure
    local directories=(
        "$BACKUP_BASE_DIR"
        "$BACKUP_BASE_DIR/daily"
        "$BACKUP_BASE_DIR/weekly" 
        "$BACKUP_BASE_DIR/monthly"
        "$BACKUP_BASE_DIR/logs"
        "/opt/dotmac/backup-scripts"
        "/etc/dotmac"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        chown root:root "$dir"
        chmod 755 "$dir"
    done
    
    print_status "Backup directories created"
}

# Create backup configuration
create_backup_config() {
    print_step "Creating backup configuration..."
    
    local config_file="/etc/dotmac/backup.conf"
    
    cat > "$config_file" << EOF
# DotMac Framework Backup Configuration
# Generated on $(date)

# Basic settings
BACKUP_BASE_DIR="$BACKUP_BASE_DIR"
BACKUP_RETENTION_DAYS="$RETENTION_DAYS"
BACKUP_COMPRESSION="true"

# Schedule settings
BACKUP_SCHEDULE="$BACKUP_SCHEDULE"
ENABLE_DAILY_BACKUP="true"
ENABLE_WEEKLY_BACKUP="true"
ENABLE_MONTHLY_BACKUP="false"

# Remote storage settings
ENABLE_REMOTE_STORAGE="$ENABLE_REMOTE_STORAGE"
REMOTE_STORAGE_TYPE="$REMOTE_STORAGE_TYPE"

# S3 Configuration (if using S3)
S3_BUCKET="${S3_BUCKET:-}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Google Cloud Storage Configuration (if using GCS)
GCS_BUCKET="${GCS_BUCKET:-}"

# Rsync Configuration (if using rsync)
RSYNC_DESTINATION="${RSYNC_DESTINATION:-}"

# Encryption settings
ENABLE_ENCRYPTION="$ENABLE_ENCRYPTION"
GPG_RECIPIENT="${GPG_RECIPIENT:-}"

# Monitoring settings
ENABLE_MONITORING="$ENABLE_MONITORING"
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"
EMAIL_RECIPIENTS="${EMAIL_RECIPIENTS:-}"

# Notification settings
NOTIFY_ON_SUCCESS="false"
NOTIFY_ON_FAILURE="true"
NOTIFY_ON_WARNING="true"

# Advanced settings
PARALLEL_BACKUPS="false"
BACKUP_TIMEOUT="7200"  # 2 hours
MAX_BACKUP_SIZE="50G"

# Logging
BACKUP_LOG_LEVEL="INFO"
BACKUP_LOG_RETENTION="90"  # days
EOF
    
    chmod 600 "$config_file"
    print_status "Backup configuration created: $config_file"
}

# Install backup wrapper script
install_backup_wrapper() {
    print_step "Installing backup wrapper script..."
    
    local wrapper_script="/usr/local/bin/dotmac-backup"
    
    cat > "$wrapper_script" << 'EOF'
#!/bin/bash
# DotMac Backup Wrapper Script

# Load configuration
CONFIG_FILE="/etc/dotmac/backup.conf"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

# Set defaults if not configured
BACKUP_BASE_DIR="${BACKUP_BASE_DIR:-/opt/dotmac/backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# Find backup script
BACKUP_SCRIPT=""
POSSIBLE_LOCATIONS=(
    "/opt/dotmac/backup-scripts/backup.sh"
    "/home/dotmac_framework/deployment/scripts/backup.sh"
    "$(dirname $0)/backup.sh"
)

for location in "${POSSIBLE_LOCATIONS[@]}"; do
    if [ -f "$location" ]; then
        BACKUP_SCRIPT="$location"
        break
    fi
done

if [ -z "$BACKUP_SCRIPT" ]; then
    echo "ERROR: Backup script not found"
    exit 1
fi

# Export environment variables for backup script
export BACKUP_DIR="$BACKUP_BASE_DIR"
export BACKUP_RETENTION_DAYS
export REMOTE_STORAGE_TYPE
export S3_BUCKET
export GCS_BUCKET
export RSYNC_DESTINATION
export GPG_RECIPIENT

# Build backup command with options
BACKUP_CMD="bash '$BACKUP_SCRIPT'"

# Add type based on script arguments or defaults
BACKUP_TYPE="full"
if [ "$1" = "--type" ] && [ -n "$2" ]; then
    BACKUP_TYPE="$2"
    shift 2
fi

BACKUP_CMD="$BACKUP_CMD --type $BACKUP_TYPE"

# Add compression if enabled
if [ "$BACKUP_COMPRESSION" = "true" ]; then
    BACKUP_CMD="$BACKUP_CMD --compress"
fi

# Add encryption if enabled
if [ "$ENABLE_ENCRYPTION" = "true" ] && [ -n "$GPG_RECIPIENT" ]; then
    BACKUP_CMD="$BACKUP_CMD --encrypt"
fi

# Add remote storage if enabled
if [ "$ENABLE_REMOTE_STORAGE" = "true" ]; then
    BACKUP_CMD="$BACKUP_CMD --remote"
fi

# Add verification
BACKUP_CMD="$BACKUP_CMD --verify"

# Add retention
BACKUP_CMD="$BACKUP_CMD --retention $BACKUP_RETENTION_DAYS"

# Pass through any additional arguments
BACKUP_CMD="$BACKUP_CMD $@"

# Execute backup with logging
LOG_FILE="$BACKUP_BASE_DIR/logs/backup_$(date +%Y%m%d_%H%M%S).log"
echo "Starting backup at $(date)" > "$LOG_FILE"
echo "Command: $BACKUP_CMD" >> "$LOG_FILE"

eval "$BACKUP_CMD" 2>&1 | tee -a "$LOG_FILE"
BACKUP_EXIT_CODE=${PIPESTATUS[0]}

echo "Backup finished at $(date) with exit code $BACKUP_EXIT_CODE" >> "$LOG_FILE"

# Send notifications if configured
if [ "$ENABLE_MONITORING" = "true" ]; then
    if [ $BACKUP_EXIT_CODE -eq 0 ] && [ "$NOTIFY_ON_SUCCESS" = "true" ]; then
        /usr/local/bin/dotmac-backup-notify "success" "Backup completed successfully"
    elif [ $BACKUP_EXIT_CODE -ne 0 ] && [ "$NOTIFY_ON_FAILURE" = "true" ]; then
        /usr/local/bin/dotmac-backup-notify "failure" "Backup failed with exit code $BACKUP_EXIT_CODE"
    fi
fi

exit $BACKUP_EXIT_CODE
EOF
    
    chmod +x "$wrapper_script"
    print_status "Backup wrapper installed: $wrapper_script"
}

# Install notification script
install_notification_script() {
    if [ "$ENABLE_MONITORING" != "true" ]; then
        print_status "Monitoring disabled, skipping notification script"
        return 0
    fi
    
    print_step "Installing backup notification script..."
    
    local notify_script="/usr/local/bin/dotmac-backup-notify"
    
    cat > "$notify_script" << 'EOF'
#!/bin/bash
# DotMac Backup Notification Script

# Load configuration
CONFIG_FILE="/etc/dotmac/backup.conf"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

STATUS="$1"
MESSAGE="$2"
HOSTNAME="$(hostname)"
TIMESTAMP="$(date)"

# Determine notification color/emoji
case "$STATUS" in
    "success")
        COLOR="good"
        EMOJI="✅"
        ;;
    "failure") 
        COLOR="danger"
        EMOJI="❌"
        ;;
    "warning")
        COLOR="warning"
        EMOJI="⚠️"
        ;;
    *)
        COLOR="warning"
        EMOJI="ℹ️"
        ;;
esac

# Send Slack notification if configured
if [ -n "$SLACK_WEBHOOK" ]; then
    SLACK_PAYLOAD=$(cat << EOF
{
    "text": "$EMOJI DotMac Backup Notification",
    "attachments": [
        {
            "color": "$COLOR",
            "fields": [
                {
                    "title": "Status",
                    "value": "$STATUS",
                    "short": true
                },
                {
                    "title": "Host",
                    "value": "$HOSTNAME",
                    "short": true
                },
                {
                    "title": "Message",
                    "value": "$MESSAGE",
                    "short": false
                },
                {
                    "title": "Timestamp",
                    "value": "$TIMESTAMP",
                    "short": false
                }
            ]
        }
    ]
}
EOF
)
    
    curl -X POST -H 'Content-type: application/json' \
         --data "$SLACK_PAYLOAD" \
         "$SLACK_WEBHOOK" > /dev/null 2>&1 || true
fi

# Send email notification if configured
if [ -n "$EMAIL_RECIPIENTS" ]; then
    if command -v mail > /dev/null; then
        echo -e "DotMac Backup Notification\n\nStatus: $STATUS\nHost: $HOSTNAME\nMessage: $MESSAGE\nTimestamp: $TIMESTAMP" | \
        mail -s "[$HOSTNAME] DotMac Backup $STATUS" "$EMAIL_RECIPIENTS"
    fi
fi

# Log notification
LOG_FILE="${BACKUP_BASE_DIR:-/opt/dotmac/backups}/logs/notifications.log"
echo "$(date) - $STATUS - $MESSAGE" >> "$LOG_FILE"
EOF
    
    chmod +x "$notify_script"
    print_status "Notification script installed: $notify_script"
}

# Setup cron jobs
setup_cron_jobs() {
    print_step "Setting up backup cron jobs..."
    
    # Create cron job file
    local cron_file="/etc/cron.d/dotmac-backups"
    
    cat > "$cron_file" << EOF
# DotMac Framework Automated Backups
# Generated on $(date)

SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
MAILTO=""

EOF
    
    # Add scheduled jobs based on configuration
    case "$BACKUP_SCHEDULE" in
        "daily")
            echo "# Daily full backup at 2:30 AM" >> "$cron_file"
            echo "30 2 * * * root /usr/local/bin/dotmac-backup --type full" >> "$cron_file"
            echo "" >> "$cron_file"
            ;;
        "weekly")
            echo "# Weekly full backup on Sunday at 2:30 AM" >> "$cron_file"
            echo "30 2 * * 0 root /usr/local/bin/dotmac-backup --type full" >> "$cron_file"
            echo "" >> "$cron_file"
            echo "# Daily incremental backup at 3:00 AM (Monday-Saturday)" >> "$cron_file"
            echo "0 3 * * 1-6 root /usr/local/bin/dotmac-backup --type incremental" >> "$cron_file"
            echo "" >> "$cron_file"
            ;;
        "custom")
            echo "# Custom backup schedule - edit as needed" >> "$cron_file"
            echo "# 30 2 * * * root /usr/local/bin/dotmac-backup --type full" >> "$cron_file"
            echo "" >> "$cron_file"
            ;;
    esac
    
    # Add configuration backup (weekly)
    echo "# Weekly configuration backup on Saturday at 1:00 AM" >> "$cron_file"
    echo "0 1 * * 6 root /usr/local/bin/dotmac-backup --type config" >> "$cron_file"
    echo "" >> "$cron_file"
    
    # Add backup cleanup (daily)
    echo "# Daily backup cleanup at 4:00 AM" >> "$cron_file"
    echo "0 4 * * * root /usr/local/bin/dotmac-backup --cleanup" >> "$cron_file"
    echo "" >> "$cron_file"
    
    chmod 644 "$cron_file"
    
    # Restart cron service
    systemctl reload cron || systemctl reload crond || true
    
    print_status "Cron jobs configured: $cron_file"
}

# Copy backup scripts to system location
copy_backup_scripts() {
    print_step "Copying backup scripts to system location..."
    
    local system_script_dir="/opt/dotmac/backup-scripts"
    
    # Copy main backup script
    cp "$SCRIPT_DIR/backup.sh" "$system_script_dir/"
    cp "$SCRIPT_DIR/rollback.sh" "$system_script_dir/" 2>/dev/null || true
    cp "$SCRIPT_DIR/disaster_recovery.py" "$system_script_dir/" 2>/dev/null || true
    
    # Set proper permissions
    chmod +x "$system_script_dir"/*.sh "$system_script_dir"/*.py
    chown root:root "$system_script_dir"/*
    
    print_status "Backup scripts copied to $system_script_dir"
}

# Setup backup monitoring
setup_monitoring() {
    if [ "$ENABLE_MONITORING" != "true" ]; then
        print_status "Monitoring disabled, skipping monitoring setup"
        return 0
    fi
    
    print_step "Setting up backup monitoring..."
    
    # Create monitoring script
    local monitor_script="/usr/local/bin/dotmac-backup-monitor"
    
    cat > "$monitor_script" << 'EOF'
#!/bin/bash
# DotMac Backup Monitoring Script

# Load configuration
CONFIG_FILE="/etc/dotmac/backup.conf"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

BACKUP_BASE_DIR="${BACKUP_BASE_DIR:-/opt/dotmac/backups}"
LOG_DIR="$BACKUP_BASE_DIR/logs"
ALERT_FILE="$LOG_DIR/backup_alerts.log"

# Check for recent successful backups
check_recent_backups() {
    local recent_backup_threshold=48  # hours
    
    # Find most recent backup
    local latest_backup=""
    local latest_timestamp=0
    
    for backup in "$BACKUP_BASE_DIR"/*; do
        if [[ -d "$backup" && $(basename "$backup") =~ ^[0-9]{8}_[0-9]{6}$ ]]; then
            local backup_name=$(basename "$backup")
            local backup_time=$(date -d "${backup_name:0:8} ${backup_name:9:2}:${backup_name:11:2}:${backup_name:13:2}" +%s 2>/dev/null)
            
            if [ "$backup_time" -gt "$latest_timestamp" ]; then
                latest_timestamp="$backup_time"
                latest_backup="$backup"
            fi
        fi
    done
    
    if [ -n "$latest_backup" ]; then
        local hours_old=$(( ($(date +%s) - latest_timestamp) / 3600 ))
        
        if [ "$hours_old" -gt "$recent_backup_threshold" ]; then
            echo "$(date) - WARNING: Latest backup is $hours_old hours old (threshold: $recent_backup_threshold hours)" >> "$ALERT_FILE"
            /usr/local/bin/dotmac-backup-notify "warning" "Latest backup is $hours_old hours old"
        fi
    else
        echo "$(date) - ERROR: No backups found" >> "$ALERT_FILE"
        /usr/local/bin/dotmac-backup-notify "failure" "No backups found"
    fi
}

# Check disk space for backups
check_disk_space() {
    local threshold=90  # percentage
    local usage=$(df "$BACKUP_BASE_DIR" | awk 'NR==2 {print $5}' | cut -d'%' -f1)
    
    if [ "$usage" -gt "$threshold" ]; then
        echo "$(date) - WARNING: Backup disk usage is ${usage}% (threshold: ${threshold}%)" >> "$ALERT_FILE"
        /usr/local/bin/dotmac-backup-notify "warning" "Backup disk usage is ${usage}%"
    fi
}

# Check for failed backup logs
check_failed_backups() {
    local log_files=($LOG_DIR/backup_*.log)
    
    if [ ${#log_files[@]} -gt 0 ]; then
        for log_file in "${log_files[@]}"; do
            if [ -f "$log_file" ]; then
                # Check if log file is from last 24 hours and contains errors
                local file_age=$(( ($(date +%s) - $(stat -c %Y "$log_file")) / 3600 ))
                
                if [ "$file_age" -lt 24 ] && grep -qi "error\|failed\|exception" "$log_file"; then
                    echo "$(date) - ERROR: Backup failure detected in $log_file" >> "$ALERT_FILE"
                    /usr/local/bin/dotmac-backup-notify "failure" "Backup failure detected in $(basename "$log_file")"
                fi
            fi
        done
    fi
}

# Main monitoring function
main() {
    mkdir -p "$LOG_DIR"
    
    check_recent_backups
    check_disk_space
    check_failed_backups
    
    # Clean old alert logs (keep 30 days)
    find "$LOG_DIR" -name "*.log" -type f -mtime +30 -delete 2>/dev/null || true
}

main "$@"
EOF
    
    chmod +x "$monitor_script"
    
    # Add monitoring to cron (every 6 hours)
    echo "# Backup monitoring every 6 hours" >> "/etc/cron.d/dotmac-backups"
    echo "0 */6 * * * root /usr/local/bin/dotmac-backup-monitor" >> "/etc/cron.d/dotmac-backups"
    
    print_status "Backup monitoring configured"
}

# Generate setup summary
generate_summary() {
    print_header "\n✅ BACKUP SYSTEM SETUP COMPLETED!"
    print_header "=" * 60
    
    print_status "Configuration:"
    echo "  📁 Backup directory: $BACKUP_BASE_DIR"
    echo "  📅 Schedule: $BACKUP_SCHEDULE"
    echo "  🗄️  Retention: $RETENTION_DAYS days"
    echo "  📤 Remote storage: $REMOTE_STORAGE_TYPE"
    echo "  🔐 Encryption: $([ "$ENABLE_ENCRYPTION" = "true" ] && echo "enabled" || echo "disabled")"
    echo "  📊 Monitoring: $([ "$ENABLE_MONITORING" = "true" ] && echo "enabled" || echo "disabled")"
    
    print_status "\nManagement commands:"
    echo "  🔄 Manual backup: sudo dotmac-backup"
    echo "  📊 List backups: ls -la $BACKUP_BASE_DIR"
    echo "  📋 View logs: tail -f $BACKUP_BASE_DIR/logs/backup_*.log"
    echo "  🗑️  Cleanup: sudo dotmac-backup --cleanup"
    
    print_status "\nFiles created:"
    echo "  📝 Configuration: /etc/dotmac/backup.conf"
    echo "  🔧 Wrapper script: /usr/local/bin/dotmac-backup"
    echo "  📅 Cron jobs: /etc/cron.d/dotmac-backups"
    echo "  📊 Monitor script: /usr/local/bin/dotmac-backup-monitor"
    
    if [ "$ENABLE_MONITORING" = "true" ]; then
        echo "  📢 Notification script: /usr/local/bin/dotmac-backup-notify"
    fi
    
    print_status "\nNext steps:"
    echo "  1. Test backup: sudo dotmac-backup --type config --verify"
    echo "  2. Configure remote storage credentials (if enabled)"
    echo "  3. Set up GPG keys for encryption (if enabled)"
    echo "  4. Configure notification webhooks/emails (if enabled)"
    echo "  5. Test disaster recovery: python3 /opt/dotmac/backup-scripts/disaster_recovery.py --list-backups"
}

# Parse command line arguments
BACKUP_SCHEDULE="daily"
RETENTION_DAYS="30"
ENABLE_REMOTE_STORAGE="false"
REMOTE_STORAGE_TYPE="none"
ENABLE_ENCRYPTION="false"
ENABLE_MONITORING="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        --schedule)
            BACKUP_SCHEDULE="$2"
            shift 2
            ;;
        --retention)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        --remote-storage)
            ENABLE_REMOTE_STORAGE="true"
            REMOTE_STORAGE_TYPE="$2"
            shift 2
            ;;
        --encrypt)
            ENABLE_ENCRYPTION="true"
            shift
            ;;
        --monitor)
            ENABLE_MONITORING="true"
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate parameters
case "$BACKUP_SCHEDULE" in
    daily|weekly|custom)
        ;;
    *)
        print_error "Invalid schedule: $BACKUP_SCHEDULE"
        print_error "Valid schedules: daily, weekly, custom"
        exit 1
        ;;
esac

case "$REMOTE_STORAGE_TYPE" in
    none|s3|gcs|rsync)
        ;;
    *)
        print_error "Invalid remote storage type: $REMOTE_STORAGE_TYPE"
        print_error "Valid types: none, s3, gcs, rsync"
        exit 1
        ;;
esac

# Main execution
print_header "🔧 DotMac Framework Backup System Setup"
print_header "Schedule: $BACKUP_SCHEDULE | Retention: $RETENTION_DAYS days"
print_header "=" * 60

check_requirements
setup_directories
create_backup_config
copy_backup_scripts
install_backup_wrapper
install_notification_script
setup_cron_jobs
setup_monitoring
generate_summary

print_header "\n🎉 Backup system setup completed successfully!"