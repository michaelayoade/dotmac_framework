#!/bin/bash
# Simple production deployment script for DotMac Platform

set -euo pipefail

DOTMAC_HOME="/home/dotmac_framework"
COMPOSE_FILE="$DOTMAC_HOME/docker-compose.unified.yml"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
}

check_prerequisites() {
    log "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker not found"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose not found" 
        exit 1
    fi
    
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        error "Compose file not found: $COMPOSE_FILE"
        exit 1
    fi
    
    log "✅ Prerequisites OK"
}

deploy() {
    log "Deploying to production..."
    
    # Create backup if script exists
    if [[ -x "$DOTMAC_HOME/scripts/simple-backup.sh" ]]; then
        log "Creating backup..."
        "$DOTMAC_HOME/scripts/simple-backup.sh" backup || true
    fi
    
    # Deploy services
    docker-compose -f "$COMPOSE_FILE" up -d
    
    # Wait for services
    sleep 30
    
    # Simple health check
    if curl -s -f http://localhost:8000/health >/dev/null; then
        log "✅ Deployment successful"
    else
        error "Health check failed"
        exit 1
    fi
}

status() {
    docker-compose -f "$COMPOSE_FILE" ps
}

case "${1:-}" in
    deploy)
        check_prerequisites
        deploy
        ;;
    status)
        status
        ;;
    logs)
        docker-compose -f "$COMPOSE_FILE" logs -f
        ;;
    *)
        echo "Usage: $0 {deploy|status|logs}"
        ;;
esac