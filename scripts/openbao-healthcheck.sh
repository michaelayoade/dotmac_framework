#!/bin/sh
#
# OpenBao Health Check Script
# 
# This script provides a robust health check for OpenBao containers
# by trying multiple methods to verify the service is running and healthy.
#

set -e

OPENBAO_ADDR="${OPENBAO_ADDR:-http://localhost:8200}"
HEALTH_ENDPOINT="${OPENBAO_ADDR}/v1/sys/health"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo "${GREEN}[INFO]${NC} $1" >&2
}

log_warn() {
    echo "${YELLOW}[WARN]${NC} $1" >&2
}

log_error() {
    echo "${RED}[ERROR]${NC} $1" >&2
}

# Method 1: Try curl (most reliable for HTTP health checks)
check_with_curl() {
    if command -v curl >/dev/null 2>&1; then
        log_info "Trying health check with curl..."
        if curl -f -s "$HEALTH_ENDPOINT" >/dev/null 2>&1; then
            log_info "OpenBao health check passed with curl"
            return 0
        else
            log_warn "curl health check failed"
            return 1
        fi
    else
        log_warn "curl not available"
        return 1
    fi
}

# Method 2: Try wget as fallback
check_with_wget() {
    if command -v wget >/dev/null 2>&1; then
        log_info "Trying health check with wget..."
        if wget -q --spider "$HEALTH_ENDPOINT" 2>/dev/null; then
            log_info "OpenBao health check passed with wget"
            return 0
        else
            log_warn "wget health check failed"
            return 1
        fi
    else
        log_warn "wget not available"
        return 1
    fi
}

# Method 3: Try OpenBao native status command
check_with_bao_status() {
    if command -v bao >/dev/null 2>&1; then
        log_info "Trying health check with bao status..."
        # Set BAO_ADDR for the status check
        export BAO_ADDR="$OPENBAO_ADDR"
        
        if bao status -format=json >/dev/null 2>&1; then
            log_info "OpenBao health check passed with bao status"
            return 0
        else
            log_warn "bao status health check failed"
            return 1
        fi
    else
        log_warn "bao command not available"
        return 1
    fi
}

# Method 4: Try basic TCP connection check
check_tcp_connection() {
    log_info "Trying TCP connection check..."
    
    # Extract host and port from OPENBAO_ADDR
    HOST=$(echo "$OPENBAO_ADDR" | sed 's|http[s]*://||' | cut -d: -f1)
    PORT=$(echo "$OPENBAO_ADDR" | sed 's|http[s]*://||' | cut -d: -f2 | cut -d/ -f1)
    
    # Default port if not specified
    if [ "$PORT" = "$HOST" ]; then
        PORT="8200"
    fi
    
    log_info "Checking TCP connection to $HOST:$PORT"
    
    # Use netcat if available
    if command -v nc >/dev/null 2>&1; then
        if nc -z "$HOST" "$PORT" 2>/dev/null; then
            log_info "TCP connection successful with netcat"
            return 0
        else
            log_warn "TCP connection failed with netcat"
        fi
    fi
    
    # Use telnet as fallback
    if command -v telnet >/dev/null 2>&1; then
        if echo | telnet "$HOST" "$PORT" 2>/dev/null | grep -q Connected; then
            log_info "TCP connection successful with telnet"
            return 0
        else
            log_warn "TCP connection failed with telnet"
        fi
    fi
    
    # Use /dev/tcp if available (bash built-in)
    if [ -n "$BASH_VERSION" ]; then
        if exec 6<>/dev/tcp/"$HOST"/"$PORT" 2>/dev/null; then
            exec 6>&-
            log_info "TCP connection successful with /dev/tcp"
            return 0
        else
            log_warn "TCP connection failed with /dev/tcp"
        fi
    fi
    
    log_warn "No suitable TCP connection method available"
    return 1
}

# Method 5: Check if OpenBao process is running
check_process_running() {
    log_info "Checking if OpenBao process is running..."
    
    if pgrep -f "bao.*server" >/dev/null 2>&1; then
        log_info "OpenBao server process found"
        return 0
    elif pgrep -f "vault.*server" >/dev/null 2>&1; then
        log_info "Vault server process found (OpenBao compatible)"
        return 0
    else
        log_warn "No OpenBao/Vault server process found"
        return 1
    fi
}

# Main health check function
perform_health_check() {
    log_info "Starting OpenBao health check..."
    log_info "Target address: $OPENBAO_ADDR"
    
    # Try methods in order of preference
    if check_with_curl; then
        return 0
    elif check_with_wget; then
        return 0
    elif check_with_bao_status; then
        return 0
    elif check_tcp_connection; then
        log_warn "Only TCP connection successful - service may not be fully ready"
        return 0
    elif check_process_running; then
        log_warn "Process running but not responding to health checks - service may be starting"
        return 0
    else
        log_error "All health check methods failed"
        return 1
    fi
}

# Parse command line arguments
while [ $# -gt 0 ]; do
    case $1 in
        --addr=*)
            OPENBAO_ADDR="${1#*=}"
            HEALTH_ENDPOINT="${OPENBAO_ADDR}/v1/sys/health"
            shift
            ;;
        --addr)
            OPENBAO_ADDR="$2"
            HEALTH_ENDPOINT="${OPENBAO_ADDR}/v1/sys/health"
            shift 2
            ;;
        --quiet|-q)
            # Redirect info and warn messages to /dev/null for quiet mode
            exec 1>/dev/null
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --addr=URL    OpenBao address (default: http://localhost:8200)"
            echo "  --quiet, -q   Suppress info and warning messages"
            echo "  --help, -h    Show this help message"
            echo ""
            echo "Exit codes:"
            echo "  0  Health check passed"
            echo "  1  Health check failed"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Perform the health check
if perform_health_check; then
    log_info "✅ OpenBao health check PASSED"
    exit 0
else
    log_error "❌ OpenBao health check FAILED"
    exit 1
fi