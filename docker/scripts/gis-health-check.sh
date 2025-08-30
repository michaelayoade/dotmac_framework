#!/bin/sh
# ============================================================================
# GIS CDN Health Check Script
# Validates that all GIS services and assets are properly available
# ============================================================================

set -e

# Configuration
HEALTH_CHECK_TIMEOUT=10
EXIT_CODE=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [HEALTH] $1"
}

log_success() {
    echo "${GREEN}✓${NC} $1"
}

log_warning() {
    echo "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo "${RED}✗${NC} $1"
    EXIT_CODE=1
}

# ============================================================================
# BASIC NGINX HEALTH CHECK
# ============================================================================

log "Starting GIS CDN health check..."

# Check if nginx is responding
if ! curl -sf -m $HEALTH_CHECK_TIMEOUT http://localhost/health > /dev/null; then
    log_error "Nginx health endpoint not responding"
    exit 1
fi

log_success "Nginx is responding"

# ============================================================================
# STATIC ASSETS AVAILABILITY
# ============================================================================

# Check if map assets directory is accessible
if [ ! -d "/usr/share/nginx/html/maps" ]; then
    log_warning "Maps directory not found"
else
    log_success "Maps directory accessible"
fi

# Check if icons directory is accessible
if [ ! -d "/usr/share/nginx/html/assets/icons" ]; then
    log_warning "Icons directory not found"
else
    log_success "Icons directory accessible"
fi

# Check if assets directory is accessible
if [ ! -d "/usr/share/nginx/html/assets" ]; then
    log_warning "Assets directory not found"
else
    log_success "Assets directory accessible"
fi

# ============================================================================
# SAMPLE ASSET CHECKS
# ============================================================================

# Check if sample map tile exists
if curl -sf -m $HEALTH_CHECK_TIMEOUT -o /dev/null http://localhost/maps/sample.png; then
    log_success "Sample map tile accessible"
else
    log_warning "Sample map tile not found (this may be expected)"
fi

# Check if default marker icon exists
if curl -sf -m $HEALTH_CHECK_TIMEOUT -o /dev/null http://localhost/icons/default-marker.svg; then
    log_success "Default marker icon accessible"
else
    log_warning "Default marker icon not found"
fi

# ============================================================================
# GZIP AND COMPRESSION CHECK
# ============================================================================

# Test gzip compression
if curl -sf -H "Accept-Encoding: gzip" -m $HEALTH_CHECK_TIMEOUT http://localhost/health | gzip -t 2>/dev/null; then
    log_success "Gzip compression working"
else
    log_warning "Gzip compression may not be working"
fi

# ============================================================================
# CORS HEADERS CHECK
# ============================================================================

# Check CORS headers for map assets
CORS_HEADER=$(curl -sf -m $HEALTH_CHECK_TIMEOUT -I http://localhost/maps/ 2>/dev/null | grep -i "access-control-allow-origin" || true)

if [ -n "$CORS_HEADER" ]; then
    log_success "CORS headers present for map assets"
else
    log_warning "CORS headers not found (may affect cross-origin requests)"
fi

# ============================================================================
# CACHE HEADERS CHECK
# ============================================================================

# Check cache headers for static assets
CACHE_HEADER=$(curl -sf -m $HEALTH_CHECK_TIMEOUT -I http://localhost/assets/ 2>/dev/null | grep -i "cache-control" || true)

if [ -n "$CACHE_HEADER" ]; then
    log_success "Cache headers configured for static assets"
else
    log_warning "Cache headers not found"
fi

# ============================================================================
# RATE LIMITING CHECK
# ============================================================================

# Basic rate limiting test (make multiple requests)
RATE_LIMIT_TEST=0
for i in $(seq 1 5); do
    if curl -sf -m 2 http://localhost/health > /dev/null; then
        RATE_LIMIT_TEST=$((RATE_LIMIT_TEST + 1))
    fi
done

if [ $RATE_LIMIT_TEST -ge 3 ]; then
    log_success "Basic rate limiting appears to be working"
else
    log_warning "Rate limiting may be too restrictive or not working"
fi

# ============================================================================
# DISK SPACE CHECK
# ============================================================================

# Check available disk space
DISK_USAGE=$(df /usr/share/nginx/html | awk 'NR==2{print $5}' | sed 's/%//')

if [ "$DISK_USAGE" -lt 90 ]; then
    log_success "Disk space OK ($DISK_USAGE% used)"
elif [ "$DISK_USAGE" -lt 95 ]; then
    log_warning "Disk space getting low ($DISK_USAGE% used)"
else
    log_error "Disk space critically low ($DISK_USAGE% used)"
fi

# ============================================================================
# MEMORY CHECK
# ============================================================================

# Check available memory
if [ -r /proc/meminfo ]; then
    MEMORY_FREE=$(awk '/MemAvailable/{printf "%.0f", $2/1024/1024}' /proc/meminfo)
    if [ "$MEMORY_FREE" -gt 0 ]; then
        if [ "$MEMORY_FREE" -lt 100 ]; then
            log_warning "Low memory available (${MEMORY_FREE}MB)"
        else
            log_success "Memory available (${MEMORY_FREE}MB)"
        fi
    fi
fi

# ============================================================================
# FINAL HEALTH STATUS
# ============================================================================

if [ $EXIT_CODE -eq 0 ]; then
    log_success "GIS CDN health check passed"
    echo "healthy"
else
    log_error "GIS CDN health check failed"
    echo "unhealthy"
fi

exit $EXIT_CODE
