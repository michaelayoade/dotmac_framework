#!/bin/bash
# Comprehensive Failure Artifact Collection Script
# Collects logs, database snapshots, container diagnostics, and test artifacts

set -e

STAGE=${1:-unknown}
SCENARIO=${2:-unknown}
COMPREHENSIVE=${3:-""}

export CI_JOB_ID="${GITHUB_RUN_ID:-local}_${GITHUB_RUN_ATTEMPT:-1}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARTIFACT_DIR="artifacts/${STAGE}-${SCENARIO}-${TIMESTAMP}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

# Load environment variables
load_environment() {
    if [[ -f ".env.e2e-ports-${CI_JOB_ID}" ]]; then
        source ".env.e2e-ports-${CI_JOB_ID}"
        log "Loaded port configuration for job ${CI_JOB_ID}"
    else
        warn "Port configuration file not found, using defaults"
        export BACKEND_PORT=8000
        export ADMIN_PORT=3001
        export CUSTOMER_PORT=3002
    fi
}

# Initialize artifact collection
initialize_collection() {
    log "Initializing artifact collection for $STAGE/$SCENARIO..."
    
    mkdir -p "$ARTIFACT_DIR"/{logs,screenshots,videos,database,containers,network,performance,config}
    
    # Create collection metadata
    cat > "$ARTIFACT_DIR/collection-metadata.json" << EOF
{
    "stage": "$STAGE",
    "scenario": "$SCENARIO",
    "job_id": "$CI_JOB_ID",
    "timestamp": "$TIMESTAMP",
    "comprehensive": "$COMPREHENSIVE",
    "git_sha": "${GITHUB_SHA:-unknown}",
    "branch": "${GITHUB_REF_NAME:-unknown}",
    "runner": "${RUNNER_NAME:-local}",
    "collection_start": "$(date -u -Iseconds)"
}
EOF

    log "Artifact directory created: $ARTIFACT_DIR"
}

# Collect container logs
collect_container_logs() {
    log "📋 Collecting container logs..."
    
    # Docker compose logs
    if docker-compose -f docker/docker-compose.e2e-tenant.yml ps -q &>/dev/null; then
        docker-compose -f docker/docker-compose.e2e-tenant.yml logs --no-color > "$ARTIFACT_DIR/logs/docker-compose.log" 2>&1
        log "  - Docker Compose logs collected"
    else
        warn "Docker Compose stack not found"
    fi
    
    # Individual container logs
    local containers
    containers=$(docker ps --filter "name=*${CI_JOB_ID}*" --format "{{.Names}}")
    
    if [[ -n "$containers" ]]; then
        while IFS= read -r container_name; do
            log "  - Collecting logs from: $container_name"
            docker logs "$container_name" > "$ARTIFACT_DIR/logs/${container_name}.log" 2>&1 || \
                warn "Failed to collect logs from $container_name"
                
            # Get container inspection data
            docker inspect "$container_name" > "$ARTIFACT_DIR/containers/${container_name}-inspect.json" 2>&1 || \
                warn "Failed to inspect $container_name"
        done <<< "$containers"
    else
        warn "No containers found for job ${CI_JOB_ID}"
    fi
    
    # Collect system docker info
    docker system info > "$ARTIFACT_DIR/containers/docker-system-info.txt" 2>&1 || warn "Failed to collect docker system info"
    docker system df > "$ARTIFACT_DIR/containers/docker-disk-usage.txt" 2>&1 || warn "Failed to collect docker disk usage"
}

# Collect database snapshots and diagnostics
collect_database_artifacts() {
    log "🗄️ Collecting database artifacts..."
    
    local postgres_container
    postgres_container=$(docker ps --filter "name=postgres-e2e-${CI_JOB_ID}" --format "{{.Names}}" | head -1)
    
    if [[ -n "$postgres_container" ]]; then
        log "  - Creating database dump from: $postgres_container"
        
        # Full database dump
        docker exec "$postgres_container" pg_dump -U test_user --verbose \
            "dotmac_test_${CI_JOB_ID}" > "$ARTIFACT_DIR/database/full-dump.sql" 2>&1 || \
            warn "Failed to create full database dump"
        
        # Schema-only dump
        docker exec "$postgres_container" pg_dump -U test_user --schema-only \
            "dotmac_test_${CI_JOB_ID}" > "$ARTIFACT_DIR/database/schema-dump.sql" 2>&1 || \
            warn "Failed to create schema dump"
        
        # Database statistics
        docker exec "$postgres_container" psql -U test_user -d "dotmac_test_${CI_JOB_ID}" -c "
            SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del, n_live_tup, n_dead_tup
            FROM pg_stat_user_tables
            ORDER BY n_live_tup DESC;
        " > "$ARTIFACT_DIR/database/table-statistics.txt" 2>&1 || warn "Failed to collect table statistics"
        
        # Active connections
        docker exec "$postgres_container" psql -U test_user -d "dotmac_test_${CI_JOB_ID}" -c "
            SELECT pid, usename, application_name, client_addr, state, query_start, query 
            FROM pg_stat_activity 
            WHERE state != 'idle'
            ORDER BY query_start;
        " > "$ARTIFACT_DIR/database/active-connections.txt" 2>&1 || warn "Failed to collect active connections"
        
        # Database size information
        docker exec "$postgres_container" psql -U test_user -d "dotmac_test_${CI_JOB_ID}" -c "
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
            FROM pg_tables 
            WHERE schemaname NOT IN ('information_schema','pg_catalog')
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
        " > "$ARTIFACT_DIR/database/table-sizes.txt" 2>&1 || warn "Failed to collect table sizes"
        
        # Recent log entries from PostgreSQL
        docker exec "$postgres_container" bash -c "
            find /var/lib/postgresql/data/log -name '*.log' -type f -newermt '1 hour ago' | \
            head -5 | xargs cat
        " > "$ARTIFACT_DIR/database/postgres-recent-logs.txt" 2>&1 || warn "Failed to collect recent PostgreSQL logs"
        
    else
        warn "PostgreSQL container not found"
    fi
    
    # Redis diagnostics
    local redis_container
    redis_container=$(docker ps --filter "name=redis-e2e-${CI_JOB_ID}" --format "{{.Names}}" | head -1)
    
    if [[ -n "$redis_container" ]]; then
        log "  - Collecting Redis diagnostics from: $redis_container"
        
        # Redis info
        docker exec "$redis_container" redis-cli INFO > "$ARTIFACT_DIR/database/redis-info.txt" 2>&1 || \
            warn "Failed to collect Redis info"
        
        # Redis memory usage
        docker exec "$redis_container" redis-cli MEMORY USAGE > "$ARTIFACT_DIR/database/redis-memory.txt" 2>&1 || \
            warn "Failed to collect Redis memory usage"
        
        # Redis key scan (limited to prevent performance issues)
        docker exec "$redis_container" redis-cli --scan --pattern "*" | head -100 > "$ARTIFACT_DIR/database/redis-keys-sample.txt" 2>&1 || \
            warn "Failed to collect Redis keys sample"
        
        # Redis slow log
        docker exec "$redis_container" redis-cli SLOWLOG GET 10 > "$ARTIFACT_DIR/database/redis-slowlog.txt" 2>&1 || \
            warn "Failed to collect Redis slow log"
    fi
}

# Collect application health and metrics
collect_application_metrics() {
    log "📊 Collecting application metrics..."
    
    # Backend health check
    if curl -f -s "http://localhost:$BACKEND_PORT/health" > "$ARTIFACT_DIR/logs/backend-health.json" 2>&1; then
        log "  - Backend health check collected"
    else
        warn "Failed to collect backend health check"
    fi
    
    # Backend metrics (if available)
    if curl -f -s "http://localhost:$BACKEND_PORT/metrics" > "$ARTIFACT_DIR/performance/backend-metrics.txt" 2>&1; then
        log "  - Backend Prometheus metrics collected"
    else
        log "  - Backend metrics endpoint not available"
    fi
    
    # Application configuration dump (if available)
    if curl -f -s "http://localhost:$BACKEND_PORT/debug/config" > "$ARTIFACT_DIR/config/backend-config.json" 2>&1; then
        log "  - Backend configuration collected"
    else
        log "  - Backend debug config not available"
    fi
    
    # Frontend health checks
    for frontend in "admin:$ADMIN_PORT" "customer:$CUSTOMER_PORT"; do
        IFS=':' read -r name port <<< "$frontend"
        if curl -f -s "http://localhost:$port/health" > "$ARTIFACT_DIR/logs/${name}-frontend-health.json" 2>&1; then
            log "  - $name frontend health collected"
        else
            log "  - $name frontend health not available"
        fi
    done
}

# Collect network diagnostics
collect_network_diagnostics() {
    log "🌐 Collecting network diagnostics..."
    
    # Docker networks
    docker network ls > "$ARTIFACT_DIR/network/docker-networks.txt" 2>&1
    
    # Inspect the e2e network
    local network_name="e2e-network-${CI_JOB_ID}"
    if docker network inspect "$network_name" > "$ARTIFACT_DIR/network/e2e-network-inspect.json" 2>&1; then
        log "  - E2E network configuration collected"
    else
        warn "E2E network not found: $network_name"
    fi
    
    # Port connectivity tests
    log "  - Testing service connectivity..."
    cat > "$ARTIFACT_DIR/network/connectivity-test.txt" << EOF
# Service Connectivity Test Results
# Generated: $(date -u)

EOF
    
    # Test backend connectivity from different perspectives
    for service in dotmac-isp-e2e frontend-admin-e2e frontend-customer-e2e; do
        container_name="${service}-${CI_JOB_ID}"
        if docker ps --filter "name=$container_name" --format "{{.Names}}" | grep -q "$container_name"; then
            echo "Testing connectivity from $service:" >> "$ARTIFACT_DIR/network/connectivity-test.txt"
            
            # Test backend API from container
            docker exec "$container_name" curl -f -s "http://dotmac-isp-e2e-${CI_JOB_ID}:8000/health" \
                >> "$ARTIFACT_DIR/network/connectivity-test.txt" 2>&1 || \
                echo "  FAILED: $service -> backend API" >> "$ARTIFACT_DIR/network/connectivity-test.txt"
            
            echo "" >> "$ARTIFACT_DIR/network/connectivity-test.txt"
        fi
    done
    
    # Host-level connectivity tests
    echo "Host-level connectivity:" >> "$ARTIFACT_DIR/network/connectivity-test.txt"
    for service in "backend:$BACKEND_PORT" "admin:$ADMIN_PORT" "customer:$CUSTOMER_PORT"; do
        IFS=':' read -r name port <<< "$service"
        if curl -f -s -m 5 "http://localhost:$port" >/dev/null; then
            echo "  ✓ $name (port $port) - accessible" >> "$ARTIFACT_DIR/network/connectivity-test.txt"
        else
            echo "  ✗ $name (port $port) - failed" >> "$ARTIFACT_DIR/network/connectivity-test.txt"
        fi
    done
    
    # Network statistics
    netstat -tuln > "$ARTIFACT_DIR/network/port-usage.txt" 2>&1 || \
        ss -tuln > "$ARTIFACT_DIR/network/port-usage.txt" 2>&1 || \
        warn "Failed to collect port usage statistics"
}

# Collect Playwright test artifacts
collect_playwright_artifacts() {
    log "🎭 Collecting Playwright test artifacts..."
    
    # Copy Playwright test results
    for results_dir in test-results playwright-report; do
        if [[ -d "$results_dir" ]]; then
            cp -r "$results_dir" "$ARTIFACT_DIR/" 2>/dev/null || warn "Failed to copy $results_dir"
            log "  - Copied $results_dir"
        fi
    done
    
    # Look for screenshots in various possible locations
    find . -name "*.png" -path "*/test-results/*" -newermt "1 hour ago" | \
        head -20 | \
        xargs -I {} cp {} "$ARTIFACT_DIR/screenshots/" 2>/dev/null || true
    
    # Look for videos
    find . -name "*.webm" -path "*/test-results/*" -newermt "1 hour ago" | \
        head -10 | \
        xargs -I {} cp {} "$ARTIFACT_DIR/videos/" 2>/dev/null || true
    
    # Count collected artifacts
    local screenshot_count video_count
    screenshot_count=$(find "$ARTIFACT_DIR/screenshots" -name "*.png" 2>/dev/null | wc -l)
    video_count=$(find "$ARTIFACT_DIR/videos" -name "*.webm" 2>/dev/null | wc -l)
    
    log "  - Screenshots collected: $screenshot_count"
    log "  - Videos collected: $video_count"
}

# Collect system resource information
collect_system_resources() {
    log "💻 Collecting system resource information..."
    
    # Docker stats
    timeout 10s docker stats --no-stream > "$ARTIFACT_DIR/containers/docker-stats.txt" 2>&1 || \
        warn "Failed to collect Docker stats"
    
    # System resources
    {
        echo "=== System Information ==="
        uname -a
        echo
        echo "=== CPU Information ==="
        cat /proc/cpuinfo | grep "model name\|processor\|cpu cores" | head -10
        echo
        echo "=== Memory Information ==="  
        free -h
        echo
        echo "=== Disk Usage ==="
        df -h
        echo
        echo "=== Load Average ==="
        cat /proc/loadavg
        echo
        echo "=== Process Tree ==="
        pstree -p $$ 2>/dev/null || ps -ef | head -20
    } > "$ARTIFACT_DIR/containers/system-resources.txt" 2>&1
    
    # Docker system resources
    {
        echo "=== Docker System Events (last 10 minutes) ==="
        docker system events --since "10m" --until "now" 2>/dev/null || echo "No recent events"
        echo
        echo "=== Docker Container Processes ==="
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    } >> "$ARTIFACT_DIR/containers/docker-system-info.txt" 2>&1
}

# Comprehensive mode - additional diagnostics
collect_comprehensive_diagnostics() {
    if [[ "$COMPREHENSIVE" == "--comprehensive" ]]; then
        log "🔍 Comprehensive mode: Collecting additional diagnostics..."
        
        # Container filesystem inspection
        local containers
        containers=$(docker ps --filter "name=*${CI_JOB_ID}*" --format "{{.Names}}")
        
        while IFS= read -r container_name; do
            if [[ -n "$container_name" ]]; then
                log "  - Comprehensive inspection: $container_name"
                
                # Process list within container
                docker exec "$container_name" ps aux > "$ARTIFACT_DIR/containers/${container_name}-processes.txt" 2>&1 || \
                    warn "Failed to get process list from $container_name"
                
                # Environment variables (filtered for security)
                docker exec "$container_name" env | grep -E '^(PATH|PYTHONPATH|NODE_|NEXT_|DATABASE_URL|REDIS_URL)' > \
                    "$ARTIFACT_DIR/containers/${container_name}-env.txt" 2>&1 || \
                    warn "Failed to get environment from $container_name"
                
                # Disk usage within container
                docker exec "$container_name" df -h > "$ARTIFACT_DIR/containers/${container_name}-disk.txt" 2>&1 || \
                    warn "Failed to get disk usage from $container_name"
                
                # Network configuration within container
                docker exec "$container_name" ip addr show > "$ARTIFACT_DIR/containers/${container_name}-network.txt" 2>&1 || \
                    warn "Failed to get network config from $container_name"
            fi
        done <<< "$containers"
        
        # Application log files from containers
        log "  - Collecting application log files..."
        containers=$(docker ps --filter "name=dotmac-isp-e2e-${CI_JOB_ID}" --format "{{.Names}}")
        if [[ -n "$containers" ]]; then
            while IFS= read -r container_name; do
                docker exec "$container_name" find /app -name "*.log" -type f 2>/dev/null | \
                    head -10 | \
                    xargs -I {} docker exec "$container_name" cat {} > \
                    "$ARTIFACT_DIR/logs/${container_name}-app-logs.txt" 2>&1 || true
            done <<< "$containers"
        fi
    fi
}

# Create comprehensive failure summary
create_failure_summary() {
    log "📄 Creating failure summary report..."
    
    local container_status
    container_status=$(docker-compose -f docker/docker-compose.e2e-tenant.yml ps 2>/dev/null || echo "Docker Compose stack not available")
    
    local total_size
    total_size=$(du -sh "$ARTIFACT_DIR" 2>/dev/null | cut -f1 || echo "Unknown")
    
    cat > "$ARTIFACT_DIR/failure-summary.md" << EOF
# Test Failure Artifact Collection Report

## Test Execution Details
- **Stage**: $STAGE
- **Scenario**: $SCENARIO  
- **Job ID**: $CI_JOB_ID
- **Collection Timestamp**: $(date -u)
- **Git SHA**: ${GITHUB_SHA:-unknown}
- **Branch**: ${GITHUB_REF_NAME:-unknown}
- **Runner**: ${RUNNER_NAME:-local}
- **Comprehensive Mode**: ${COMPREHENSIVE:-disabled}

## Environment Configuration
- **Backend Port**: $BACKEND_PORT
- **Admin Frontend Port**: $ADMIN_PORT
- **Customer Frontend Port**: $CUSTOMER_PORT
- **Reseller Frontend Port**: ${RESELLER_PORT:-not configured}

## Container Status at Collection Time
\`\`\`
$container_status
\`\`\`

## Collected Artifacts Summary
- **Total Artifact Size**: $total_size
- **Container Logs**: $(find "$ARTIFACT_DIR/logs" -name "*.log" 2>/dev/null | wc -l) files
- **Database Snapshots**: $(find "$ARTIFACT_DIR/database" -name "*.sql" 2>/dev/null | wc -l) files
- **Screenshots**: $(find "$ARTIFACT_DIR/screenshots" -name "*.png" 2>/dev/null | wc -l) files
- **Videos**: $(find "$ARTIFACT_DIR/videos" -name "*.webm" 2>/dev/null | wc -l) files
- **Container Inspections**: $(find "$ARTIFACT_DIR/containers" -name "*-inspect.json" 2>/dev/null | wc -l) files

## Quick Investigation Guide

### 1. Container Issues
- Check \`logs/docker-compose.log\` for overall container orchestration issues
- Review individual container logs in \`logs/\` directory
- Examine container inspection data in \`containers/\` directory

### 2. Database Issues  
- Review \`database/full-dump.sql\` for data integrity
- Check \`database/active-connections.txt\` for connection issues
- Examine \`database/table-statistics.txt\` for data volumes

### 3. Application Issues
- Review \`logs/backend-health.json\` for API health status
- Check \`performance/backend-metrics.txt\` for performance indicators
- Examine \`config/backend-config.json\` for configuration issues

### 4. Network Issues
- Review \`network/connectivity-test.txt\` for service communication problems
- Check \`network/e2e-network-inspect.json\` for network configuration
- Examine \`network/port-usage.txt\` for port conflicts

### 5. Test-Specific Issues
- Review Playwright HTML reports in \`playwright-report/\`
- Examine screenshots in \`screenshots/\` directory
- Check videos in \`videos/\` directory for visual debugging

## Environment URLs (if still accessible)
- **Backend API**: http://localhost:$BACKEND_PORT
- **Admin Portal**: http://localhost:$ADMIN_PORT  
- **Customer Portal**: http://localhost:$CUSTOMER_PORT

## Next Steps
1. **Immediate**: Review container logs for obvious error messages
2. **Database**: Check database dump for data consistency issues
3. **Application**: Verify API health and configuration
4. **Network**: Test service connectivity and port accessibility
5. **UI/UX**: Review Playwright screenshots and videos for user-facing issues

---
*This report was generated automatically by the failure artifact collection system.*
EOF

    # Add collection completion metadata
    cat >> "$ARTIFACT_DIR/collection-metadata.json" << EOF
,
    "collection_end": "$(date -u -Iseconds)",
    "total_artifacts": $(find "$ARTIFACT_DIR" -type f | wc -l),
    "total_size_bytes": $(du -sb "$ARTIFACT_DIR" | cut -f1),
    "summary_report": "failure-summary.md"
}
EOF
}

# Set GitHub Actions outputs
set_github_outputs() {
    if [[ -n "$GITHUB_OUTPUT" ]]; then
        echo "artifact_path=$ARTIFACT_DIR" >> "$GITHUB_OUTPUT"
        echo "artifact_size=$(du -sh "$ARTIFACT_DIR" | cut -f1)" >> "$GITHUB_OUTPUT"
        echo "collection_timestamp=$TIMESTAMP" >> "$GITHUB_OUTPUT"
    fi
}

# Main execution function
main() {
    log "Starting comprehensive failure artifact collection..."
    log "Configuration: STAGE=$STAGE, SCENARIO=$SCENARIO, JOB_ID=$CI_JOB_ID"
    
    load_environment
    initialize_collection
    
    # Run all collection steps
    collect_container_logs
    collect_database_artifacts  
    collect_application_metrics
    collect_network_diagnostics
    collect_playwright_artifacts
    collect_system_resources
    collect_comprehensive_diagnostics
    
    create_failure_summary
    set_github_outputs
    
    success "Artifact collection completed!"
    log "📁 Total artifacts collected: $(find "$ARTIFACT_DIR" -type f | wc -l) files"
    log "📦 Total size: $(du -sh "$ARTIFACT_DIR" | cut -f1)"
    log "📂 Artifact location: $ARTIFACT_DIR"
    
    echo
    echo "==================== ARTIFACT COLLECTION SUMMARY ===================="
    echo "Location: $ARTIFACT_DIR"
    echo "Size: $(du -sh "$ARTIFACT_DIR" | cut -f1)"
    echo "Files: $(find "$ARTIFACT_DIR" -type f | wc -l)"
    echo "Summary: $ARTIFACT_DIR/failure-summary.md"
    echo "======================================================================="
}

# Handle errors during collection
handle_collection_error() {
    error "Artifact collection failed at step: $1"
    if [[ -d "$ARTIFACT_DIR" ]]; then
        echo "Partial artifacts may be available in: $ARTIFACT_DIR"
    fi
    exit 1
}

# Trap errors
trap 'handle_collection_error "$BASH_COMMAND"' ERR

# Execute main function
main "$@"