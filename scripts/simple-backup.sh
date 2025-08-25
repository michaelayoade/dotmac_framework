#!/bin/bash
# Simple DotMac Platform Backup Script
# Uses existing Docker, PostgreSQL, and standard Linux tools

set -euo pipefail

# Configuration from environment or defaults
BACKUP_DIR="${BACKUP_DIR:-/var/backups/dotmac}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
S3_BUCKET="${BACKUP_S3_BUCKET:-}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"

# Create timestamped backup directory
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/$TIMESTAMP"
mkdir -p "$BACKUP_PATH"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
}

# Backup PostgreSQL databases
backup_databases() {
    log "Backing up PostgreSQL databases..."
    
    export PGPASSWORD="$POSTGRES_PASSWORD"
    
    local databases=("dotmac_db" "identity_db" "billing_db")
    for db in "${databases[@]}"; do
        local backup_file="$BACKUP_PATH/${db}.sql.gz"
        log "  Backing up $db..."
        
        if pg_dump -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$db" --clean --if-exists | gzip > "$backup_file"; then
            log "  ✓ Database $db backed up ($(du -h "$backup_file" | cut -f1))"
        else
            error "Failed to backup database $db"
            return 1
        fi
    done
    
    unset PGPASSWORD
}

# Backup Redis data
backup_redis() {
    log "Backing up Redis data..."
    
    # Use Docker to backup Redis
    if docker exec dotmac-redis redis-cli --rdb /tmp/dump.rdb > /dev/null 2>&1; then
        docker cp dotmac-redis:/tmp/dump.rdb "$BACKUP_PATH/redis-dump.rdb"
        log "  ✓ Redis data backed up ($(du -h "$BACKUP_PATH/redis-dump.rdb" | cut -f1))"
    else
        error "Failed to backup Redis data"
        return 1
    fi
}

# Backup configuration files
backup_config() {
    log "Backing up configuration files..."
    
    local config_dirs=(
        "/home/dotmac_framework/config"
        "/home/dotmac_framework/.env"
        "/home/dotmac_framework/docker-compose*.yml"
        "/etc/dotmac"
    )
    
    tar -czf "$BACKUP_PATH/config.tar.gz" "${config_dirs[@]}" 2>/dev/null || true
    log "  ✓ Configuration backed up ($(du -h "$BACKUP_PATH/config.tar.gz" | cut -f1))"
}

# Backup Docker volumes
backup_volumes() {
    log "Backing up Docker volumes..."
    
    local volumes=("dotmac_postgres_data" "dotmac_redis_data" "dotmac_signoz_data")
    for volume in "${volumes[@]}"; do
        if docker volume inspect "$volume" >/dev/null 2>&1; then
            docker run --rm -v "$volume":/data -v "$BACKUP_PATH":/backup alpine:latest tar -czf "/backup/${volume}.tar.gz" -C /data .
            log "  ✓ Volume $volume backed up ($(du -h "$BACKUP_PATH/${volume}.tar.gz" | cut -f1))"
        else
            log "  ! Volume $volume not found, skipping"
        fi
    done
}

# Upload to S3 if configured
upload_to_s3() {
    if [[ -z "$S3_BUCKET" ]]; then
        log "No S3 bucket configured, skipping upload"
        return 0
    fi
    
    log "Uploading backup to S3..."
    
    if command -v aws >/dev/null 2>&1; then
        local archive_name="dotmac-backup-${TIMESTAMP}.tar.gz"
        tar -czf "/tmp/$archive_name" -C "$BACKUP_DIR" "$TIMESTAMP"
        
        if aws s3 cp "/tmp/$archive_name" "s3://$S3_BUCKET/backups/$archive_name" --storage-class STANDARD_IA; then
            log "  ✓ Backup uploaded to S3: s3://$S3_BUCKET/backups/$archive_name"
            rm "/tmp/$archive_name"
        else
            error "Failed to upload backup to S3"
            return 1
        fi
    else
        log "AWS CLI not installed, skipping S3 upload"
    fi
}

# Clean up old backups
cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."
    
    find "$BACKUP_DIR" -maxdepth 1 -type d -name "[0-9]*_[0-9]*" -mtime +$RETENTION_DAYS -exec rm -rf {} \; 2>/dev/null || true
    
    # Also clean up S3 if configured
    if [[ -n "$S3_BUCKET" ]] && command -v aws >/dev/null 2>&1; then
        local cutoff_date=$(date -d "$RETENTION_DAYS days ago" +%Y%m%d)
        aws s3 ls "s3://$S3_BUCKET/backups/" | awk '{print $4}' | while read file; do
            if [[ "$file" =~ dotmac-backup-([0-9]{8})_ ]]; then
                local file_date="${BASH_REMATCH[1]}"
                if [[ "$file_date" < "$cutoff_date" ]]; then
                    aws s3 rm "s3://$S3_BUCKET/backups/$file"
                    log "  Deleted old S3 backup: $file"
                fi
            fi
        done
    fi
    
    log "  ✓ Old backups cleaned up"
}

# Create backup summary
create_summary() {
    local total_size=$(du -sh "$BACKUP_PATH" | cut -f1)
    local file_count=$(find "$BACKUP_PATH" -type f | wc -l)
    
    cat > "$BACKUP_PATH/backup-summary.txt" << EOF
DotMac Platform Backup Summary
=============================
Timestamp: $TIMESTAMP
Total Size: $total_size
Files: $file_count
Status: $([ $? -eq 0 ] && echo "SUCCESS" || echo "FAILED")

Contents:
$(ls -lah "$BACKUP_PATH" | tail -n +2)

System Info:
Host: $(hostname)
Uptime: $(uptime)
Docker Status: $(docker system df --format "table {{.Type}}\t{{.TotalCount}}\t{{.Size}}")
EOF
    
    log "  ✓ Backup summary created"
}

# Verify backup integrity
verify_backup() {
    log "Verifying backup integrity..."
    
    local errors=0
    
    # Check database backups
    for db_backup in "$BACKUP_PATH"/*.sql.gz; do
        if [[ -f "$db_backup" ]]; then
            if ! gzip -t "$db_backup"; then
                error "Corrupt database backup: $(basename "$db_backup")"
                ((errors++))
            fi
        fi
    done
    
    # Check tar archives
    for tar_backup in "$BACKUP_PATH"/*.tar.gz; do
        if [[ -f "$tar_backup" ]]; then
            if ! tar -tzf "$tar_backup" >/dev/null 2>&1; then
                error "Corrupt tar archive: $(basename "$tar_backup")"
                ((errors++))
            fi
        fi
    done
    
    if [[ $errors -eq 0 ]]; then
        log "  ✓ Backup integrity verified"
        return 0
    else
        error "Backup integrity check failed with $errors errors"
        return 1
    fi
}

# Main backup function
main() {
    log "Starting DotMac Platform backup..."
    
    # Check prerequisites
    if [[ -z "$POSTGRES_PASSWORD" ]]; then
        error "POSTGRES_PASSWORD environment variable is required"
        exit 1
    fi
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    # Run backup steps
    backup_databases || exit 1
    backup_redis || exit 1
    backup_config || exit 1
    backup_volumes || exit 1
    
    # Verify backup
    verify_backup || exit 1
    
    # Create summary
    create_summary
    
    # Upload to cloud storage
    upload_to_s3 || true  # Don't fail if upload fails
    
    # Clean up old backups
    cleanup_old_backups
    
    local total_size=$(du -sh "$BACKUP_PATH" | cut -f1)
    log "✅ Backup completed successfully!"
    log "   Location: $BACKUP_PATH"
    log "   Total size: $total_size"
    
    # Send success notification if configured
    if [[ -n "${BACKUP_SUCCESS_WEBHOOK:-}" ]]; then
        curl -X POST "$BACKUP_SUCCESS_WEBHOOK" -H "Content-Type: application/json" -d "{\"text\":\"✅ DotMac backup completed successfully. Size: $total_size\"}" >/dev/null 2>&1 || true
    fi
}

# Handle different commands
case "${1:-backup}" in
    backup)
        main
        ;;
    restore)
        if [[ -z "${2:-}" ]]; then
            echo "Usage: $0 restore <backup_timestamp>"
            echo "Available backups:"
            ls -1 "$BACKUP_DIR" | grep -E '^[0-9]{8}_[0-9]{6}$' | sort -r | head -10
            exit 1
        fi
        
        RESTORE_PATH="$BACKUP_DIR/$2"
        if [[ ! -d "$RESTORE_PATH" ]]; then
            error "Backup not found: $RESTORE_PATH"
            exit 1
        fi
        
        log "Restoring from backup: $2"
        log "⚠️  This will overwrite existing data!"
        read -p "Are you sure? (yes/no): " confirm
        
        if [[ "$confirm" == "yes" ]]; then
            # Restore databases
            export PGPASSWORD="$POSTGRES_PASSWORD"
            for db_backup in "$RESTORE_PATH"/*.sql.gz; do
                if [[ -f "$db_backup" ]]; then
                    db_name=$(basename "$db_backup" .sql.gz)
                    log "Restoring database: $db_name"
                    gunzip -c "$db_backup" | psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$db_name"
                fi
            done
            unset PGPASSWORD
            
            # Restore Redis
            if [[ -f "$RESTORE_PATH/redis-dump.rdb" ]]; then
                log "Restoring Redis data..."
                docker cp "$RESTORE_PATH/redis-dump.rdb" dotmac-redis:/data/dump.rdb
                docker restart dotmac-redis
            fi
            
            log "✅ Restore completed!"
        else
            log "Restore cancelled"
        fi
        ;;
    list)
        echo "Available backups:"
        ls -la "$BACKUP_DIR" | grep -E '^d.*[0-9]{8}_[0-9]{6}$' | while read -r line; do
            backup_name=$(echo "$line" | awk '{print $9}')
            size=$(du -sh "$BACKUP_DIR/$backup_name" | cut -f1)
            date_formatted=$(echo "$backup_name" | sed 's/\([0-9]\{4\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)_\([0-9]\{2\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)/\1-\2-\3 \4:\5:\6/')
            echo "  $backup_name ($size) - $date_formatted"
        done
        ;;
    cleanup)
        cleanup_old_backups
        ;;
    verify)
        if [[ -z "${2:-}" ]]; then
            # Verify latest backup
            LATEST=$(ls -1 "$BACKUP_DIR" | grep -E '^[0-9]{8}_[0-9]{6}$' | sort -r | head -1)
            if [[ -n "$LATEST" ]]; then
                BACKUP_PATH="$BACKUP_DIR/$LATEST"
                verify_backup
            else
                error "No backups found"
                exit 1
            fi
        else
            # Verify specific backup
            BACKUP_PATH="$BACKUP_DIR/$2"
            verify_backup
        fi
        ;;
    *)
        echo "Usage: $0 {backup|restore|list|cleanup|verify} [backup_timestamp]"
        echo
        echo "Commands:"
        echo "  backup             - Create a new backup"
        echo "  restore <timestamp> - Restore from specific backup"  
        echo "  list               - List available backups"
        echo "  cleanup            - Remove old backups"
        echo "  verify [timestamp] - Verify backup integrity"
        exit 1
        ;;
esac