#!/bin/bash
# Comprehensive Backup Script for DotMac Framework
# Handles database backups, configuration backups, and application data

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
PRODUCTION_DIR="$PROJECT_ROOT/deployment/production"
BACKUP_BASE_DIR="${BACKUP_DIR:-/opt/dotmac/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# Functions for colored output
print_status() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_header() { echo -e "${BLUE}$1${NC}"; }
print_step() { echo -e "${PURPLE}[STEP]${NC} $1"; }

# Logging setup
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_BASE_DIR/$TIMESTAMP"
LOG_FILE="$BACKUP_BASE_DIR/backup_$TIMESTAMP.log"

exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Error handling
trap 'handle_error $? $LINENO' ERR

handle_error() {
    print_error "Backup failed at line $2 with exit code $1"
    print_error "Check the log file: $LOG_FILE"
    cleanup_failed_backup
    exit $1
}

cleanup_failed_backup() {
    if [ -d "$BACKUP_DIR" ]; then
        print_warning "Cleaning up failed backup directory: $BACKUP_DIR"
        rm -rf "$BACKUP_DIR"
    fi
}

# Usage function
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -t, --type TYPE         Backup type: full|incremental|config|emergency (default: full)"
    echo "  -r, --retention DAYS    Retention period in days (default: 30)"
    echo "  -c, --compress         Enable compression (default: enabled)"
    echo "  -e, --encrypt          Encrypt backup (requires GPG key)"
    echo "  -s, --remote           Upload to remote storage"
    echo "  -v, --verify           Verify backup integrity after creation"
    echo "  -h, --help             Show this help message"
    echo "  --cleanup              Clean old backups only (no new backup)"
    echo ""
    echo "Examples:"
    echo "  $0                      # Full backup with default settings"
    echo "  $0 -t incremental      # Incremental backup"
    echo "  $0 -t config -v        # Configuration backup with verification"
    echo "  $0 -t emergency -e     # Emergency backup with encryption"
    echo "  $0 --cleanup           # Clean old backups only"
}

# Check requirements
check_requirements() {
    print_step "Checking backup requirements..."
    
    # Check if running in production environment
    if [ ! -f "$PRODUCTION_DIR/.env.production" ]; then
        print_warning "Production environment file not found"
        print_warning "This script is designed for production environments"
    fi
    
    # Check required commands
    local required_commands=("docker" "docker-compose" "tar" "gzip")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            print_error "Required command '$cmd' is not installed"
            exit 1
        fi
    done
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check available disk space (minimum 5GB for backup)
    local available_space=$(df "$BACKUP_BASE_DIR" | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 5242880 ]; then  # 5GB in KB
        print_error "Less than 5GB disk space available for backups"
        exit 1
    fi
    
    print_status "All requirements satisfied"
}

# Create backup directories
setup_backup_directories() {
    print_step "Setting up backup directories..."
    
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$BACKUP_DIR/databases"
    mkdir -p "$BACKUP_DIR/configs"
    mkdir -p "$BACKUP_DIR/data"
    mkdir -p "$BACKUP_DIR/logs"
    
    # Create backup metadata
    cat > "$BACKUP_DIR/backup_info.json" << EOF
{
    "timestamp": "$TIMESTAMP",
    "type": "$BACKUP_TYPE",
    "version": "$(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "hostname": "$(hostname)",
    "user": "$(whoami)",
    "retention_days": $RETENTION_DAYS
}
EOF
    
    print_status "Backup directories created: $BACKUP_DIR"
}

# Backup PostgreSQL databases
backup_postgresql() {
    print_step "Backing up PostgreSQL databases..."
    
    cd "$PRODUCTION_DIR"
    
    # Check if PostgreSQL container is running
    if ! docker-compose -f docker-compose.prod.yml ps postgres-shared | grep -q "Up"; then
        print_warning "PostgreSQL container is not running, skipping database backup"
        return 0
    fi
    
    # Get database list
    local databases=$(docker-compose -f docker-compose.prod.yml exec -T postgres-shared \
        psql -U dotmac_admin -t -c "SELECT datname FROM pg_database WHERE datistemplate = false;")
    
    # Backup each database
    for db in $databases; do
        db=$(echo "$db" | xargs)  # Trim whitespace
        if [ -n "$db" ] && [ "$db" != "postgres" ]; then
            print_status "Backing up database: $db"
            
            docker-compose -f docker-compose.prod.yml exec -T postgres-shared \
                pg_dump -U dotmac_admin -d "$db" --clean --create > "$BACKUP_DIR/databases/${db}_backup.sql"
            
            if [ $? -eq 0 ]; then
                print_status "Database $db backup completed"
            else
                print_error "Database $db backup failed"
                return 1
            fi
        fi
    done
    
    # Full cluster backup
    print_status "Creating full cluster backup..."
    docker-compose -f docker-compose.prod.yml exec -T postgres-shared \
        pg_dumpall -U dotmac_admin > "$BACKUP_DIR/databases/postgres_full_backup.sql"
    
    print_status "PostgreSQL backup completed"
}

# Backup Redis data
backup_redis() {
    print_step "Backing up Redis data..."
    
    cd "$PRODUCTION_DIR"
    
    # Check if Redis container is running
    if ! docker-compose -f docker-compose.prod.yml ps redis-shared | grep -q "Up"; then
        print_warning "Redis container is not running, skipping Redis backup"
        return 0
    fi
    
    # Create Redis backup
    docker-compose -f docker-compose.prod.yml exec -T redis-shared \
        redis-cli --rdb /tmp/dump_backup.rdb
    
    # Copy backup from container
    local container_name=$(docker-compose -f docker-compose.prod.yml ps -q redis-shared)
    docker cp "$container_name:/tmp/dump_backup.rdb" "$BACKUP_DIR/databases/redis_backup.rdb"
    
    # Also get Redis info for restoration reference
    docker-compose -f docker-compose.prod.yml exec -T redis-shared \
        redis-cli INFO > "$BACKUP_DIR/databases/redis_info.txt"
    
    print_status "Redis backup completed"
}

# Backup OpenBao/Vault data
backup_openbao() {
    print_step "Backing up OpenBao data..."
    
    cd "$PRODUCTION_DIR"
    
    # Check if OpenBao container is running
    if ! docker-compose -f docker-compose.prod.yml ps openbao-shared | grep -q "Up"; then
        print_warning "OpenBao container is not running, skipping OpenBao backup"
        return 0
    fi
    
    # Backup OpenBao data directory
    local container_name=$(docker-compose -f docker-compose.prod.yml ps -q openbao-shared)
    docker cp "$container_name:/openbao/data" "$BACKUP_DIR/databases/openbao_data"
    
    # Get OpenBao status for reference
    docker-compose -f docker-compose.prod.yml exec -T openbao-shared \
        openbao status > "$BACKUP_DIR/databases/openbao_status.txt" || true
    
    print_status "OpenBao backup completed"
}

# Backup configuration files
backup_configurations() {
    print_step "Backing up configuration files..."
    
    # Production environment configuration
    if [ -f "$PRODUCTION_DIR/.env.production" ]; then
        cp "$PRODUCTION_DIR/.env.production" "$BACKUP_DIR/configs/"
        print_status "Environment configuration backed up"
    fi
    
    # Docker Compose configurations
    cp "$PRODUCTION_DIR/docker-compose.prod.yml" "$BACKUP_DIR/configs/"
    
    # Nginx configuration
    if [ -d "$PRODUCTION_DIR/nginx" ]; then
        cp -r "$PRODUCTION_DIR/nginx" "$BACKUP_DIR/configs/"
        print_status "Nginx configuration backed up"
    fi
    
    # SSL certificates
    if [ -d "/opt/dotmac/ssl" ]; then
        cp -r "/opt/dotmac/ssl" "$BACKUP_DIR/configs/"
        print_status "SSL certificates backed up"
    fi
    
    # System configurations (if accessible)
    local system_configs=(
        "/etc/nginx/sites-available"
        "/etc/ssl/certs/dotmac*"
        "/etc/docker/daemon.json"
        "/etc/fail2ban/jail.local"
        "/etc/audit/rules.d/dotmac.rules"
        "/etc/sysctl.d/99-security.conf"
    )
    
    for config in "${system_configs[@]}"; do
        if [ -e $config ]; then
            cp -r $config "$BACKUP_DIR/configs/" 2>/dev/null || true
        fi
    done
    
    print_status "Configuration backup completed"
}

# Backup application data
backup_application_data() {
    print_step "Backing up application data..."
    
    # Backup uploaded files and data
    local data_dirs=(
        "/opt/dotmac/data/isp/uploads"
        "/opt/dotmac/data/mgmt/uploads"
        "/opt/dotmac/data/shared"
    )
    
    for data_dir in "${data_dirs[@]}"; do
        if [ -d "$data_dir" ]; then
            local dir_name=$(basename "$data_dir")
            cp -r "$data_dir" "$BACKUP_DIR/data/${dir_name}_data"
            print_status "Data directory backed up: $data_dir"
        fi
    done
    
    print_status "Application data backup completed"
}

# Backup logs
backup_logs() {
    if [ "$BACKUP_TYPE" = "config" ]; then
        print_status "Skipping logs for config backup"
        return 0
    fi
    
    print_step "Backing up recent logs..."
    
    # Application logs
    local log_dirs=(
        "/opt/dotmac/logs"
        "/var/log/nginx"
        "/var/log/audit"
        "/var/log/fail2ban.log"
    )
    
    for log_dir in "${log_dirs[@]}"; do
        if [ -e "$log_dir" ]; then
            local dir_name=$(basename "$log_dir")
            if [ -d "$log_dir" ]; then
                # Copy recent logs (last 7 days)
                mkdir -p "$BACKUP_DIR/logs/$dir_name"
                find "$log_dir" -type f -mtime -7 -exec cp {} "$BACKUP_DIR/logs/$dir_name/" \;
            else
                cp "$log_dir" "$BACKUP_DIR/logs/"
            fi
            print_status "Logs backed up: $log_dir"
        fi
    done
    
    # Docker container logs
    cd "$PRODUCTION_DIR"
    local containers=$(docker-compose -f docker-compose.prod.yml ps --services)
    mkdir -p "$BACKUP_DIR/logs/containers"
    
    for container in $containers; do
        docker-compose -f docker-compose.prod.yml logs --since 7d "$container" > \
            "$BACKUP_DIR/logs/containers/${container}.log" 2>/dev/null || true
    done
    
    print_status "Log backup completed"
}

# Compress backup
compress_backup() {
    if [ "$ENABLE_COMPRESSION" != "true" ]; then
        print_status "Compression disabled, skipping"
        return 0
    fi
    
    print_step "Compressing backup..."
    
    local compressed_file="$BACKUP_BASE_DIR/dotmac_backup_$TIMESTAMP.tar.gz"
    
    cd "$BACKUP_BASE_DIR"
    tar -czf "$compressed_file" "$TIMESTAMP"
    
    if [ $? -eq 0 ]; then
        # Remove uncompressed directory
        rm -rf "$BACKUP_DIR"
        BACKUP_DIR="$compressed_file"
        print_status "Backup compressed: $compressed_file"
        
        # Update backup info
        echo "{\"compressed_file\": \"$compressed_file\", \"size\": \"$(du -sh "$compressed_file" | cut -f1)\"}" > \
            "$BACKUP_BASE_DIR/backup_${TIMESTAMP}_info.json"
    else
        print_error "Compression failed"
        return 1
    fi
}

# Encrypt backup
encrypt_backup() {
    if [ "$ENABLE_ENCRYPTION" != "true" ]; then
        print_status "Encryption disabled, skipping"
        return 0
    fi
    
    print_step "Encrypting backup..."
    
    # Check for GPG key
    if ! gpg --list-keys "$GPG_RECIPIENT" &>/dev/null; then
        print_error "GPG key not found for recipient: $GPG_RECIPIENT"
        return 1
    fi
    
    local source_file="$BACKUP_DIR"
    local encrypted_file="${source_file}.gpg"
    
    gpg --trust-model always --encrypt --recipient "$GPG_RECIPIENT" --output "$encrypted_file" "$source_file"
    
    if [ $? -eq 0 ]; then
        rm -f "$source_file"
        BACKUP_DIR="$encrypted_file"
        print_status "Backup encrypted: $encrypted_file"
    else
        print_error "Encryption failed"
        return 1
    fi
}

# Verify backup
verify_backup() {
    if [ "$ENABLE_VERIFICATION" != "true" ]; then
        print_status "Verification disabled, skipping"
        return 0
    fi
    
    print_step "Verifying backup integrity..."
    
    local verify_result=true
    
    # Check if backup files exist and have content
    if [[ "$BACKUP_DIR" == *.tar.gz ]]; then
        # Verify compressed backup
        if ! tar -tzf "$BACKUP_DIR" >/dev/null 2>&1; then
            print_error "Compressed backup verification failed"
            verify_result=false
        fi
    elif [[ "$BACKUP_DIR" == *.gpg ]]; then
        # Cannot verify encrypted backup without decryption
        print_status "Encrypted backup - skipping content verification"
    else
        # Verify directory backup
        local essential_files=(
            "$BACKUP_DIR/backup_info.json"
            "$BACKUP_DIR/configs/.env.production"
        )
        
        for file in "${essential_files[@]}"; do
            if [ ! -f "$file" ]; then
                print_error "Essential backup file missing: $file"
                verify_result=false
            fi
        done
        
        # Check database backups
        if [ -d "$BACKUP_DIR/databases" ]; then
            local db_files=$(ls "$BACKUP_DIR/databases"/*.sql 2>/dev/null | wc -l)
            if [ "$db_files" -eq 0 ]; then
                print_warning "No database backup files found"
            fi
        fi
    fi
    
    if [ "$verify_result" = true ]; then
        print_status "Backup verification successful"
        return 0
    else
        print_error "Backup verification failed"
        return 1
    fi
}

# Upload to remote storage
upload_remote() {
    if [ "$ENABLE_REMOTE" != "true" ]; then
        print_status "Remote upload disabled, skipping"
        return 0
    fi
    
    print_step "Uploading backup to remote storage..."
    
    # This is a placeholder for remote storage integration
    # Implement based on your storage solution (AWS S3, Google Cloud, etc.)
    
    case "$REMOTE_STORAGE_TYPE" in
        "s3")
            if command -v aws &> /dev/null; then
                aws s3 cp "$BACKUP_DIR" "s3://$S3_BUCKET/dotmac-backups/" --storage-class STANDARD_IA
                print_status "Backup uploaded to S3"
            else
                print_error "AWS CLI not available for S3 upload"
                return 1
            fi
            ;;
        "gcs")
            if command -v gsutil &> /dev/null; then
                gsutil cp "$BACKUP_DIR" "gs://$GCS_BUCKET/dotmac-backups/"
                print_status "Backup uploaded to Google Cloud Storage"
            else
                print_error "gsutil not available for GCS upload"
                return 1
            fi
            ;;
        "rsync")
            if [ -n "$RSYNC_DESTINATION" ]; then
                rsync -avz "$BACKUP_DIR" "$RSYNC_DESTINATION"
                print_status "Backup uploaded via rsync"
            else
                print_error "RSYNC_DESTINATION not configured"
                return 1
            fi
            ;;
        *)
            print_warning "Unknown remote storage type: $REMOTE_STORAGE_TYPE"
            return 1
            ;;
    esac
}

# Clean old backups
cleanup_old_backups() {
    print_step "Cleaning up old backups (retention: $RETENTION_DAYS days)..."
    
    # Find and remove old backup files and directories
    find "$BACKUP_BASE_DIR" -name "dotmac_backup_*" -type f -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_BASE_DIR" -name "202*_*" -type d -mtime +$RETENTION_DAYS -exec rm -rf {} + 2>/dev/null || true
    find "$BACKUP_BASE_DIR" -name "backup_*.log" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_BASE_DIR" -name "*_info.json" -mtime +$RETENTION_DAYS -delete
    
    # Count remaining backups
    local remaining_backups=$(find "$BACKUP_BASE_DIR" -name "dotmac_backup_*" -o -name "202*_*" -type d | wc -l)
    print_status "Old backups cleaned up, $remaining_backups backups remaining"
}

# Generate backup report
generate_report() {
    print_step "Generating backup report..."
    
    local report_file="$BACKUP_BASE_DIR/backup_report_$TIMESTAMP.txt"
    local backup_size=""
    
    if [[ "$BACKUP_DIR" == *.tar.gz ]] || [[ "$BACKUP_DIR" == *.gpg ]]; then
        backup_size=$(du -sh "$BACKUP_DIR" | cut -f1)
    else
        backup_size=$(du -sh "$BACKUP_DIR" | cut -f1)
    fi
    
    cat > "$report_file" << EOF
DotMac Framework Backup Report
=============================

Backup Details:
- Timestamp: $TIMESTAMP
- Type: $BACKUP_TYPE
- Location: $BACKUP_DIR
- Size: $backup_size
- Hostname: $(hostname)
- User: $(whoami)

Components Backed Up:
- PostgreSQL Databases: $([ -d "$BACKUP_DIR/databases" ] && echo "Yes" || echo "No")
- Redis Data: $([ -f "$BACKUP_DIR/databases/redis_backup.rdb" ] && echo "Yes" || echo "No")
- OpenBao Data: $([ -d "$BACKUP_DIR/databases/openbao_data" ] && echo "Yes" || echo "No")
- Configuration Files: $([ -d "$BACKUP_DIR/configs" ] && echo "Yes" || echo "No")
- Application Data: $([ -d "$BACKUP_DIR/data" ] && echo "Yes" || echo "No")
- Logs: $([ -d "$BACKUP_DIR/logs" ] && echo "Yes" || echo "No")

Options Used:
- Compression: $ENABLE_COMPRESSION
- Encryption: $ENABLE_ENCRYPTION
- Remote Upload: $ENABLE_REMOTE
- Verification: $ENABLE_VERIFICATION

Status: SUCCESS
Completed: $(date)
EOF
    
    print_status "Backup report generated: $report_file"
}

# Main backup function
perform_backup() {
    print_header "🔄 DotMac Framework Backup"
    print_header "Type: $BACKUP_TYPE"
    print_header "Timestamp: $TIMESTAMP"
    print_header "=" * 60
    
    log "Starting backup process"
    
    # Setup
    check_requirements
    setup_backup_directories
    
    # Backup components based on type
    case "$BACKUP_TYPE" in
        "full")
            backup_postgresql
            backup_redis
            backup_openbao
            backup_configurations
            backup_application_data
            backup_logs
            ;;
        "incremental")
            # For incremental, focus on data that changes frequently
            backup_postgresql
            backup_redis
            backup_configurations
            backup_logs
            ;;
        "config")
            backup_configurations
            ;;
        "emergency")
            backup_postgresql
            backup_redis
            backup_configurations
            ;;
        *)
            print_error "Unknown backup type: $BACKUP_TYPE"
            exit 1
            ;;
    esac
    
    # Post-backup processing
    compress_backup
    encrypt_backup
    verify_backup
    upload_remote
    generate_report
    
    # Cleanup
    cleanup_old_backups
    
    print_header "\n✅ BACKUP COMPLETED SUCCESSFULLY!"
    print_status "Backup location: $BACKUP_DIR"
    print_status "Backup size: $(du -sh "$BACKUP_DIR" | cut -f1)"
    print_status "Log file: $LOG_FILE"
    
    log "Backup process completed successfully"
}

# Parse command line arguments
BACKUP_TYPE="full"
ENABLE_COMPRESSION="true"
ENABLE_ENCRYPTION="false"
ENABLE_REMOTE="false"
ENABLE_VERIFICATION="false"
CLEANUP_ONLY="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            BACKUP_TYPE="$2"
            shift 2
            ;;
        -r|--retention)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        -c|--compress)
            ENABLE_COMPRESSION="true"
            shift
            ;;
        -e|--encrypt)
            ENABLE_ENCRYPTION="true"
            shift
            ;;
        -s|--remote)
            ENABLE_REMOTE="true"
            shift
            ;;
        -v|--verify)
            ENABLE_VERIFICATION="true"
            shift
            ;;
        --cleanup)
            CLEANUP_ONLY="true"
            shift
            ;;
        -h|--help)
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

# Validate backup type
case "$BACKUP_TYPE" in
    full|incremental|config|emergency)
        ;;
    *)
        print_error "Invalid backup type: $BACKUP_TYPE"
        print_error "Valid types: full, incremental, config, emergency"
        exit 1
        ;;
esac

# Create backup base directory
mkdir -p "$BACKUP_BASE_DIR"

# Handle cleanup-only mode
if [ "$CLEANUP_ONLY" = "true" ]; then
    cleanup_old_backups
    exit 0
fi

# Perform backup
perform_backup