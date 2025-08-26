#!/bin/bash
# Production Rollback Script for DotMac Framework

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
BACKUP_DIR="/opt/dotmac/backups"

# Functions for colored output
print_status() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_header() { echo -e "${BLUE}$1${NC}"; }
print_step() { echo -e "${PURPLE}[STEP]${NC} $1"; }

# Error handling
trap 'handle_error $? $LINENO' ERR

handle_error() {
    print_error "Rollback failed at line $2 with exit code $1"
    exit $1
}

# Usage function
show_usage() {
    echo "Usage: $0 [OPTIONS] [BACKUP_TIMESTAMP]"
    echo ""
    echo "Options:"
    echo "  -l, --list              List available backups"
    echo "  -f, --force             Force rollback without confirmation"
    echo "  -h, --help              Show this help message"
    echo "  -v, --version           Show version information"
    echo ""
    echo "Examples:"
    echo "  $0 -l                   # List available backups"
    echo "  $0 20231201_143000      # Rollback to specific backup"
    echo "  $0 -f 20231201_143000   # Force rollback without confirmation"
}

# List available backups
list_backups() {
    print_header "📋 Available Backups"
    print_header "=" * 50
    
    if [ ! -d "$BACKUP_DIR" ]; then
        print_warning "No backup directory found: $BACKUP_DIR"
        return 1
    fi
    
    local backups=($(ls -1 "$BACKUP_DIR" 2>/dev/null | sort -r))
    
    if [ ${#backups[@]} -eq 0 ]; then
        print_warning "No backups found in $BACKUP_DIR"
        return 1
    fi
    
    print_status "Found ${#backups[@]} backup(s):"
    echo
    
    for backup in "${backups[@]}"; do
        local backup_path="$BACKUP_DIR/$backup"
        local backup_size=$(du -sh "$backup_path" 2>/dev/null | cut -f1)
        local backup_date=$(echo "$backup" | sed 's/_/ /' | sed 's/\(.\{4\}\)\(.\{2\}\)\(.\{2\}\) \(.\{2\}\)\(.\{2\}\)\(.\{2\}\)/\1-\2-\3 \4:\5:\6/')
        
        echo "  📁 $backup"
        echo "     Date: $backup_date"
        echo "     Size: $backup_size"
        
        # Check backup contents
        if [ -f "$backup_path/postgres_backup.sql" ]; then
            echo "     Contains: PostgreSQL data ✓"
        fi
        if [ -f "$backup_path/redis_backup.rdb" ]; then
            echo "     Contains: Redis data ✓"
        fi
        if [ -f "$backup_path/.env.production" ]; then
            echo "     Contains: Configuration ✓"
        fi
        echo
    done
}

# Validate backup
validate_backup() {
    local backup_timestamp="$1"
    local backup_path="$BACKUP_DIR/$backup_timestamp"
    
    print_step "Validating backup: $backup_timestamp"
    
    if [ ! -d "$backup_path" ]; then
        print_error "Backup not found: $backup_path"
        exit 1
    fi
    
    # Check required backup files
    local required_files=()
    local found_files=()
    
    if [ -f "$backup_path/postgres_backup.sql" ]; then
        found_files+=("PostgreSQL database")
    fi
    
    if [ -f "$backup_path/redis_backup.rdb" ]; then
        found_files+=("Redis data")
    fi
    
    if [ -f "$backup_path/.env.production" ]; then
        found_files+=("Configuration")
    fi
    
    if [ ${#found_files[@]} -eq 0 ]; then
        print_error "Backup appears to be empty or corrupted"
        exit 1
    fi
    
    print_status "Backup validation successful"
    print_status "Found: ${found_files[*]}"
}

# Stop services gracefully
stop_services() {
    print_step "Stopping services gracefully..."
    
    cd "$PRODUCTION_DIR"
    
    # Stop application services first
    docker-compose -f docker-compose.prod.yml stop \
        nginx \
        isp-framework \
        management-platform \
        mgmt-celery-worker \
        mgmt-celery-beat
    
    print_status "Application services stopped"
    
    # Give connections time to close
    sleep 10
    
    # Stop infrastructure services
    docker-compose -f docker-compose.prod.yml stop \
        postgres-shared \
        redis-shared \
        openbao-shared
    
    print_status "All services stopped"
}

# Restore database
restore_database() {
    local backup_path="$1"
    
    if [ ! -f "$backup_path/postgres_backup.sql" ]; then
        print_warning "No PostgreSQL backup found, skipping database restore"
        return 0
    fi
    
    print_step "Restoring PostgreSQL database..."
    
    cd "$PRODUCTION_DIR"
    
    # Start only PostgreSQL for restore
    docker-compose -f docker-compose.prod.yml up -d postgres-shared
    
    # Wait for PostgreSQL to be ready
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f docker-compose.prod.yml exec postgres-shared pg_isready -U dotmac_admin; then
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_error "PostgreSQL failed to start"
            exit 1
        fi
        
        print_status "Waiting for PostgreSQL... ($attempt/$max_attempts)"
        sleep 5
        attempt=$((attempt + 1))
    done
    
    # Drop existing databases and restore from backup
    print_status "Restoring database from backup..."
    
    docker-compose -f docker-compose.prod.yml exec -T postgres-shared \
        psql -U dotmac_admin -c "DROP DATABASE IF EXISTS dotmac_isp;"
    
    docker-compose -f docker-compose.prod.yml exec -T postgres-shared \
        psql -U dotmac_admin -c "DROP DATABASE IF EXISTS mgmt_platform;"
    
    # Restore from backup
    docker-compose -f docker-compose.prod.yml exec -T postgres-shared \
        psql -U dotmac_admin < "$backup_path/postgres_backup.sql"
    
    print_status "Database restoration completed"
}

# Restore Redis data
restore_redis() {
    local backup_path="$1"
    
    if [ ! -f "$backup_path/redis_backup.rdb" ]; then
        print_warning "No Redis backup found, skipping Redis restore"
        return 0
    fi
    
    print_step "Restoring Redis data..."
    
    cd "$PRODUCTION_DIR"
    
    # Copy backup file to Redis container
    docker cp "$backup_path/redis_backup.rdb" dotmac-redis-prod:/data/dump.rdb
    
    # Restart Redis to load the backup
    docker-compose -f docker-compose.prod.yml restart redis-shared
    
    print_status "Redis data restoration completed"
}

# Restore configuration
restore_configuration() {
    local backup_path="$1"
    
    if [ ! -f "$backup_path/.env.production" ]; then
        print_warning "No configuration backup found, keeping current configuration"
        return 0
    fi
    
    print_step "Restoring configuration..."
    
    # Backup current configuration
    if [ -f "$PRODUCTION_DIR/.env.production" ]; then
        cp "$PRODUCTION_DIR/.env.production" "$PRODUCTION_DIR/.env.production.pre-rollback"
    fi
    
    # Restore configuration from backup
    cp "$backup_path/.env.production" "$PRODUCTION_DIR/.env.production"
    
    print_status "Configuration restored"
    print_warning "Previous configuration backed up as .env.production.pre-rollback"
}

# Start services
start_services() {
    print_step "Starting services..."
    
    cd "$PRODUCTION_DIR"
    
    # Start infrastructure services first
    docker-compose -f docker-compose.prod.yml up -d \
        postgres-shared \
        redis-shared \
        openbao-shared
    
    # Wait for infrastructure to be ready
    print_status "Waiting for infrastructure services..."
    sleep 30
    
    # Start application services
    docker-compose -f docker-compose.prod.yml up -d \
        isp-framework \
        management-platform \
        mgmt-celery-worker \
        mgmt-celery-beat \
        nginx
    
    print_status "All services started"
}

# Verify rollback
verify_rollback() {
    print_step "Verifying rollback..."
    
    cd "$PRODUCTION_DIR"
    
    local services=("isp-framework" "management-platform" "nginx")
    local max_attempts=30
    
    for service in "${services[@]}"; do
        print_status "Checking $service health..."
        local attempt=1
        
        while [ $attempt -le $max_attempts ]; do
            if docker-compose -f docker-compose.prod.yml ps "$service" | grep -q "healthy\|Up"; then
                print_status "$service is running"
                break
            fi
            
            if [ $attempt -eq $max_attempts ]; then
                print_error "$service failed to start after rollback"
                docker-compose -f docker-compose.prod.yml logs --tail=20 "$service"
                exit 1
            fi
            
            sleep 5
            attempt=$((attempt + 1))
        done
    done
    
    # Test API endpoints
    print_status "Testing API endpoints..."
    
    local endpoints=("http://localhost:8000/health" "http://localhost:8001/health")
    
    for endpoint in "${endpoints[@]}"; do
        if curl -f -s "$endpoint" > /dev/null; then
            print_status "✓ $endpoint is responding"
        else
            print_warning "⚠ $endpoint is not responding (may be expected)"
        fi
    done
    
    print_status "Rollback verification completed"
}

# Main rollback function
perform_rollback() {
    local backup_timestamp="$1"
    local force="${2:-false}"
    local backup_path="$BACKUP_DIR/$backup_timestamp"
    
    print_header "🔄 DotMac Framework Rollback"
    print_header "Backup: $backup_timestamp"
    print_header "=" * 60
    
    # Validate backup
    validate_backup "$backup_timestamp"
    
    # Confirmation
    if [ "$force" != "true" ]; then
        print_warning "This will rollback the production system to backup: $backup_timestamp"
        print_warning "Current data will be lost unless backed up!"
        echo
        read -p "Are you sure you want to proceed? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Rollback cancelled"
            exit 0
        fi
    fi
    
    # Create emergency backup of current state
    print_step "Creating emergency backup of current state..."
    local emergency_backup="$BACKUP_DIR/emergency_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$emergency_backup"
    
    # Quick backup of current databases if running
    if docker ps | grep -q dotmac-postgres-prod; then
        docker exec dotmac-postgres-prod pg_dumpall -U dotmac_admin > "$emergency_backup/postgres_emergency.sql" 2>/dev/null || true
    fi
    
    if [ -f "$PRODUCTION_DIR/.env.production" ]; then
        cp "$PRODUCTION_DIR/.env.production" "$emergency_backup/"
    fi
    
    print_status "Emergency backup created: $emergency_backup"
    
    # Perform rollback
    stop_services
    restore_configuration "$backup_path"
    restore_database "$backup_path"
    restore_redis "$backup_path"
    start_services
    verify_rollback
    
    print_header "\n✅ ROLLBACK COMPLETED SUCCESSFULLY!"
    print_status "System has been rolled back to: $backup_timestamp"
    print_status "Emergency backup of previous state: $emergency_backup"
    print_warning "Please verify all functionality before resuming normal operations"
}

# Parse command line arguments
FORCE=false
BACKUP_TIMESTAMP=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -l|--list)
            list_backups
            exit 0
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        -v|--version)
            echo "DotMac Rollback Script v1.0.0"
            exit 0
            ;;
        -*)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            if [ -z "$BACKUP_TIMESTAMP" ]; then
                BACKUP_TIMESTAMP="$1"
            else
                print_error "Too many arguments"
                show_usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Main execution
if [ -z "$BACKUP_TIMESTAMP" ]; then
    print_error "Backup timestamp is required"
    echo
    show_usage
    exit 1
fi

perform_rollback "$BACKUP_TIMESTAMP" "$FORCE"