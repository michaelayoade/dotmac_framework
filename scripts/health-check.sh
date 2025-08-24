#!/bin/bash
# DotMac Platform - Production Health Check Script
# Comprehensive health monitoring for all services

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/var/log/dotmac/health-check.log"

# Create log directory
mkdir -p "$(dirname "$LOG_FILE")"

# Function to log messages
log_message() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Function to check HTTP endpoint
check_http_endpoint() {
    local name="$1"
    local url="$2"
    local timeout="${3:-10}"
    local expected_status="${4:-200}"
    
    log_message "${BLUE}🌐 Checking $name: $url${NC}"
    
    if response=$(curl -s -w "%{http_code}" --connect-timeout "$timeout" --max-time "$timeout" "$url" 2>/dev/null); then
        status_code="${response: -3}"
        if [[ "$status_code" == "$expected_status" ]]; then
            log_message "${GREEN}✅ $name: HTTP $status_code (OK)${NC}"
            return 0
        else
            log_message "${RED}❌ $name: HTTP $status_code (Expected $expected_status)${NC}"
            return 1
        fi
    else
        log_message "${RED}❌ $name: Connection failed${NC}"
        return 1
    fi
}

# Function to check container status
check_container() {
    local container_name="$1"
    local service_name="${2:-$container_name}"
    
    log_message "${BLUE}🐳 Checking container: $container_name${NC}"
    
    if docker ps --format "table {{.Names}}\t{{.Status}}\t{{.State}}" | grep -q "$container_name.*Up.*running"; then
        log_message "${GREEN}✅ $service_name: Container running${NC}"
        return 0
    elif docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.State}}" | grep -q "$container_name"; then
        status=$(docker ps -a --format "table {{.Names}}\t{{.Status}}" | grep "$container_name" | awk '{print $2}')
        log_message "${RED}❌ $service_name: Container exists but not running ($status)${NC}"
        return 1
    else
        log_message "${RED}❌ $service_name: Container not found${NC}"
        return 1
    fi
}

# Function to check database connectivity
check_database() {
    log_message "${BLUE}🗄️  Checking database connectivity...${NC}"
    
    # Load environment
    if [[ -f "$PROJECT_ROOT/.env.production" ]]; then
        source "$PROJECT_ROOT/.env.production"
    fi
    
    # Check PostgreSQL
    if docker exec dotmac-postgres-shared pg_isready -U "${POSTGRES_USER:-dotmac_admin}" >/dev/null 2>&1; then
        log_message "${GREEN}✅ PostgreSQL: Connection successful${NC}"
        
        # Check database count
        db_count=$(docker exec dotmac-postgres-shared psql -U "${POSTGRES_USER:-dotmac_admin}" -t -c "SELECT count(*) FROM pg_database WHERE datname IN ('dotmac_isp', 'mgmt_platform', 'dotmac_tenants', 'dotmac_analytics');" 2>/dev/null | tr -d ' \n' || echo "0")
        if [[ "$db_count" == "4" ]]; then
            log_message "${GREEN}✅ PostgreSQL: All databases present${NC}"
        else
            log_message "${YELLOW}⚠️  PostgreSQL: Expected 4 databases, found $db_count${NC}"
        fi
    else
        log_message "${RED}❌ PostgreSQL: Connection failed${NC}"
        return 1
    fi
    
    # Check Redis
    if docker exec dotmac-redis-shared redis-cli -a "${REDIS_PASSWORD:-}" ping >/dev/null 2>&1; then
        log_message "${GREEN}✅ Redis: Connection successful${NC}"
        
        # Check Redis info
        memory_usage=$(docker exec dotmac-redis-shared redis-cli -a "${REDIS_PASSWORD:-}" info memory | grep "used_memory_human" | cut -d: -f2 | tr -d '\r' 2>/dev/null || echo "unknown")
        log_message "${BLUE}ℹ️  Redis: Memory usage: $memory_usage${NC}"
    else
        log_message "${RED}❌ Redis: Connection failed${NC}"
        return 1
    fi
}

# Function to check disk space
check_disk_space() {
    log_message "${BLUE}💾 Checking disk space...${NC}"
    
    # Check root filesystem
    root_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ "$root_usage" -lt 80 ]]; then
        log_message "${GREEN}✅ Root filesystem: ${root_usage}% used${NC}"
    elif [[ "$root_usage" -lt 90 ]]; then
        log_message "${YELLOW}⚠️  Root filesystem: ${root_usage}% used (Warning)${NC}"
    else
        log_message "${RED}❌ Root filesystem: ${root_usage}% used (Critical)${NC}"
    fi
    
    # Check Docker volumes
    log_message "${BLUE}📊 Docker volume usage:${NC}"
    docker system df --format "table {{.Type}}\t{{.TotalCount}}\t{{.Size}}\t{{.Reclaimable}}" 2>/dev/null || log_message "${YELLOW}⚠️  Could not retrieve Docker volume info${NC}"
}

# Function to check memory usage
check_memory_usage() {
    log_message "${BLUE}🧠 Checking memory usage...${NC}"
    
    # System memory
    memory_info=$(free -h | awk 'NR==2{printf "Memory Usage: %s/%s (%.2f%%)", $3,$2,$3*100/$2 }')
    log_message "${BLUE}ℹ️  $memory_info${NC}"
    
    # Container memory usage
    log_message "${BLUE}🐳 Container memory usage:${NC}"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" 2>/dev/null | head -10 || log_message "${YELLOW}⚠️  Could not retrieve container stats${NC}"
}

# Function to check SSL certificates
check_ssl_certificates() {
    log_message "${BLUE}🔐 Checking SSL certificates...${NC}"
    
    SSL_DIR="$PROJECT_ROOT/ssl/certs"
    
    if [[ -d "$SSL_DIR" ]]; then
        # Check certificate expiration
        for cert in "$SSL_DIR"/*.crt; do
            if [[ -f "$cert" ]]; then
                cert_name=$(basename "$cert")
                expiry_date=$(openssl x509 -enddate -noout -in "$cert" 2>/dev/null | cut -d= -f2 || echo "unknown")
                if [[ "$expiry_date" != "unknown" ]]; then
                    expiry_epoch=$(date -d "$expiry_date" +%s 2>/dev/null || echo "0")
                    current_epoch=$(date +%s)
                    days_until_expiry=$(( (expiry_epoch - current_epoch) / 86400 ))
                    
                    if [[ "$days_until_expiry" -gt 30 ]]; then
                        log_message "${GREEN}✅ $cert_name: Expires in $days_until_expiry days${NC}"
                    elif [[ "$days_until_expiry" -gt 7 ]]; then
                        log_message "${YELLOW}⚠️  $cert_name: Expires in $days_until_expiry days${NC}"
                    else
                        log_message "${RED}❌ $cert_name: Expires in $days_until_expiry days (CRITICAL)${NC}"
                    fi
                else
                    log_message "${YELLOW}⚠️  $cert_name: Could not determine expiry${NC}"
                fi
            fi
        done
    else
        log_message "${YELLOW}⚠️  SSL certificates directory not found${NC}"
    fi
}

# Function to run performance tests
check_performance() {
    log_message "${BLUE}⚡ Running performance checks...${NC}"
    
    # Test API response times
    endpoints=(
        "http://localhost:8000/health"
        "http://localhost:8001/health"
    )
    
    for endpoint in "${endpoints[@]}"; do
        if command -v curl >/dev/null 2>&1; then
            response_time=$(curl -o /dev/null -s -w "%{time_total}" --connect-timeout 10 --max-time 10 "$endpoint" 2>/dev/null || echo "timeout")
            if [[ "$response_time" != "timeout" ]]; then
                response_ms=$(awk "BEGIN {printf \"%.0f\", $response_time * 1000}")
                if [[ "$response_ms" -lt 200 ]]; then
                    log_message "${GREEN}✅ $endpoint: ${response_ms}ms${NC}"
                elif [[ "$response_ms" -lt 1000 ]]; then
                    log_message "${YELLOW}⚠️  $endpoint: ${response_ms}ms${NC}"
                else
                    log_message "${RED}❌ $endpoint: ${response_ms}ms (SLOW)${NC}"
                fi
            else
                log_message "${RED}❌ $endpoint: Timeout${NC}"
            fi
        fi
    done
}

# Function to generate health report
generate_health_report() {
    local overall_status="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    log_message ""
    log_message "${BLUE}📋 Health Check Summary${NC}"
    log_message "================================"
    log_message "Timestamp: $timestamp"
    log_message "Overall Status: $overall_status"
    log_message "Log File: $LOG_FILE"
    log_message ""
    
    if [[ "$overall_status" == "HEALTHY" ]]; then
        log_message "${GREEN}🎉 All systems operational!${NC}"
    elif [[ "$overall_status" == "WARNING" ]]; then
        log_message "${YELLOW}⚠️  Some issues detected - monitoring recommended${NC}"
    else
        log_message "${RED}❌ Critical issues detected - immediate attention required${NC}"
    fi
    
    log_message ""
}

# Main health check function
main() {
    local exit_code=0
    local overall_status="HEALTHY"
    
    log_message "${BLUE}🔍 DotMac Platform Health Check - $(date)${NC}"
    log_message "=================================================="
    log_message ""
    
    # Infrastructure checks
    log_message "${BLUE}🏗️  Infrastructure Health Checks${NC}"
    log_message "--------------------------------"
    
    # Check containers
    containers=(
        "dotmac-nginx-proxy:Nginx Reverse Proxy"
        "dotmac-postgres-shared:PostgreSQL Database"
        "dotmac-redis-shared:Redis Cache"
        "dotmac-openbao-shared:OpenBao Secrets"
        "dotmac-clickhouse:ClickHouse Analytics"
        "dotmac-signoz-collector:SignOz Collector"
        "dotmac-signoz-query:SignOz Query Service"
        "dotmac-signoz-frontend:SignOz Frontend"
        "dotmac-isp-framework:ISP Framework"
        "dotmac-isp-worker:ISP Worker"
        "dotmac-management-platform:Management Platform"
        "dotmac-mgmt-celery-worker:Management Worker"
        "dotmac-mgmt-celery-beat:Management Scheduler"
    )
    
    for container_info in "${containers[@]}"; do
        IFS=':' read -r container_name service_name <<< "$container_info"
        if ! check_container "$container_name" "$service_name"; then
            exit_code=1
            overall_status="CRITICAL"
        fi
    done
    
    # Database connectivity
    log_message ""
    if ! check_database; then
        exit_code=1
        overall_status="CRITICAL"
    fi
    
    # HTTP endpoints
    log_message ""
    log_message "${BLUE}🌐 Application Health Checks${NC}"
    log_message "------------------------------"
    
    endpoints=(
        "Management Platform Health:http://localhost:8000/health"
        "ISP Framework Health:http://localhost:8001/health"
        "SignOz Frontend:http://localhost:3301"
    )
    
    for endpoint_info in "${endpoints[@]}"; do
        IFS=':' read -r name url <<< "$endpoint_info"
        if ! check_http_endpoint "$name" "$url"; then
            if [[ "$overall_status" != "CRITICAL" ]]; then
                overall_status="WARNING"
            fi
            exit_code=1
        fi
    done
    
    # System resources
    log_message ""
    log_message "${BLUE}💻 System Resource Checks${NC}"
    log_message "---------------------------"
    check_disk_space
    check_memory_usage
    
    # SSL certificates
    log_message ""
    check_ssl_certificates
    
    # Performance tests
    log_message ""
    check_performance
    
    # Generate final report
    generate_health_report "$overall_status"
    
    exit $exit_code
}

# Parse command line arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo "Options:"
        echo "  --help, -h      Show this help message"
        echo "  --quiet, -q     Minimal output"
        echo "  --verbose, -v   Detailed output"
        exit 0
        ;;
    --quiet|-q)
        # Redirect stdout but keep stderr for errors
        exec 1>/dev/null
        ;;
    --verbose|-v)
        set -x
        ;;
esac

# Run main function
main "$@"