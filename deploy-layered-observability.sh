#!/bin/bash
# Master Deployment Script: Layered CI/CD with Fixed Observability Integration
# Purpose: Orchestrate dependency-based startup with observability fixes

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
GATE_E0A_FILE="docker-compose.e-0a.yml"
GATE_E0B_FILE="docker-compose.e-0b.yml"  
GATE_E0C_FILE="docker-compose.e-0c.yml"
GATE_E0A_VALIDATOR="validate-gate-e-0a.sh"
GATE_E0B_VALIDATOR="validate-gate-e-0b.sh"
GATE_E0C_VALIDATOR="validate-gate-e-0c.sh"

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        "INFO")
            echo -e "${BLUE}[INFO]${NC} ${timestamp} - $message"
            ;;
        "SUCCESS") 
            echo -e "${GREEN}[SUCCESS]${NC} ${timestamp} - $message"
            ;;
        "WARNING")
            echo -e "${YELLOW}[WARNING]${NC} ${timestamp} - $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} ${timestamp} - $message"
            ;;
    esac
}

# Function to check prerequisites
check_prerequisites() {
    log "INFO" "Checking deployment prerequisites..."
    
    # Check for required files
    local required_files=("$GATE_E0A_FILE" "$GATE_E0B_FILE" "$GATE_E0C_FILE" "$GATE_E0A_VALIDATOR" "$GATE_E0B_VALIDATOR" "$GATE_E0C_VALIDATOR")
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log "ERROR" "Required file missing: $file"
            return 1
        fi
    done
    
    # Check for OpenBao integration first
    local openbao_available=false
    if command -v curl >/dev/null 2>&1 && timeout 3 curl -sf "http://localhost:8200/v1/sys/health" >/dev/null 2>&1; then
        openbao_available=true
        log "SUCCESS" "OpenBao is available - will use secrets management"
        
        # Setup OpenBao secrets if needed
        if [ ! -f "/tmp/openbao_secrets.env" ]; then
            log "INFO" "Setting up OpenBao secrets for layered deployment..."
            if ./setup-openbao-secrets.sh export; then
                log "SUCCESS" "OpenBao secrets exported"
            else
                log "WARNING" "OpenBao secrets setup failed, falling back to environment variables"
                openbao_available=false
            fi
        else
            log "INFO" "Using existing OpenBao secrets from /tmp/openbao_secrets.env"
        fi
    else
        log "WARNING" "OpenBao not available, using environment variables"
    fi
    
    # Load secrets from OpenBao if available
    if [ "$openbao_available" = true ] && [ -f "/tmp/openbao_secrets.env" ]; then
        set -a
        source /tmp/openbao_secrets.env
        set +a
        log "SUCCESS" "OpenBao secrets loaded"
    fi
    
    # Check for required variables (now potentially loaded from OpenBao)
    if [ -z "${POSTGRES_PASSWORD:-}" ]; then
        log "ERROR" "POSTGRES_PASSWORD not available (check OpenBao setup or set environment variable)"
        return 1
    fi
    
    if [ -z "${REDIS_PASSWORD:-}" ]; then
        log "ERROR" "REDIS_PASSWORD not available (check OpenBao setup or set environment variable)"
        return 1
    fi
    
    if [ -z "${CLICKHOUSE_PASSWORD:-}" ]; then
        log "ERROR" "CLICKHOUSE_PASSWORD not available (check OpenBao setup or set environment variable)"
        return 1
    fi
    
    if [ -z "${VAULT_TOKEN:-}" ]; then
        log "ERROR" "VAULT_TOKEN not available (check OpenBao setup or set environment variable)"
        return 1
    fi
    
    # Check Docker and docker-compose availability
    if ! command -v docker >/dev/null 2>&1; then
        log "ERROR" "Docker is not installed or not in PATH"
        return 1
    fi
    
    if ! command -v docker compose >/dev/null 2>&1 && ! command -v docker-compose >/dev/null 2>&1; then
        log "ERROR" "Docker Compose is not installed or not in PATH"
        return 1
    fi
    
    log "SUCCESS" "All prerequisites satisfied"
    return 0
}

# Function to clean up existing deployment
cleanup_existing() {
    log "INFO" "Cleaning up existing deployment..."
    
    # Stop and remove containers from all layers (in reverse order)
    docker compose -f "$GATE_E0C_FILE" down --remove-orphans 2>/dev/null || true
    docker compose -f "$GATE_E0B_FILE" down --remove-orphans 2>/dev/null || true  
    docker compose -f "$GATE_E0A_FILE" down --remove-orphans 2>/dev/null || true
    
    # Wait for cleanup
    sleep 5
    
    log "SUCCESS" "Existing deployment cleaned up"
}

# Function to deploy and validate a gate
deploy_gate() {
    local gate_name="$1"
    local compose_file="$2"
    local validator_script="$3"
    
    log "INFO" "Deploying $gate_name..."
    
    # Deploy the gate
    if ! docker compose -f "$compose_file" up -d; then
        log "ERROR" "Failed to deploy $gate_name"
        return 1
    fi
    
    log "SUCCESS" "$gate_name services started"
    
    # Validate the gate
    log "INFO" "Validating $gate_name..."
    if ! bash "$validator_script"; then
        log "ERROR" "$gate_name validation failed"
        log "ERROR" "Deployment halted - check logs and configuration"
        return 1
    fi
    
    log "SUCCESS" "$gate_name validated successfully"
    return 0
}

# Function to show deployment status
show_deployment_status() {
    log "INFO" "Current deployment status:"
    echo ""
    
    echo "🔍 Service Status:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(dotmac-|signoz)" || true
    echo ""
    
    echo "📊 Network Status:"
    docker network ls | grep dotmac || true
    echo ""
    
    echo "💾 Volume Status:"
    docker volume ls | grep dotmac || true
    echo ""
}

# Function to show access information
show_access_info() {
    log "SUCCESS" "Deployment completed successfully! 🎉"
    echo ""
    echo "🌐 Access Points:"
    echo "=================="
    echo "• ISP Framework API:          http://localhost:8001"
    echo "• Management Platform API:    http://localhost:8000"
    echo "• SignOz Dashboard:           http://localhost:3301"
    echo "• API Documentation:"
    echo "  - ISP Framework:            http://localhost:8001/docs"
    echo "  - Management Platform:      http://localhost:8000/docs"
    echo ""
    echo "📊 Observability Endpoints:"
    echo "============================"
    echo "• OTLP gRPC (applications):   localhost:4317"
    echo "• OTLP HTTP (applications):   localhost:4318"
    echo "• ClickHouse HTTP:            localhost:8123"
    echo "• ClickHouse Native:          localhost:9000"
    echo "• SignOz Query API:           localhost:8080"
    echo ""
    echo "🛠️  Infrastructure Endpoints:"
    echo "=============================="
    echo "• PostgreSQL:                 localhost:5434"
    echo "• Redis:                      localhost:6378"
    echo "• OpenBao:                    localhost:8200"
    echo ""
    echo "✅ Key Features Working:"
    echo "========================"
    echo "• Fixed observability configuration (no more create_default_config errors)"
    echo "• ExporterConfig and ExporterType classes available"
    echo "• Metrics registry using list_metrics() method"
    echo "• Application startup with working observability integration"
    echo "• Dependency-based layered startup (E-0a → E-0b → E-0c)"
    echo "• ClickHouse-only export (no Prometheus per your requirements)"
}

# Main deployment function
main() {
    echo "🚀 DotMac Framework - Layered Observability Deployment"
    echo "======================================================"
    echo "Implementing dependency-based Docker CI/CD with fixed observability integration"
    echo ""
    
    # Check prerequisites
    if ! check_prerequisites; then
        log "ERROR" "Prerequisites check failed"
        exit 1
    fi
    
    # Parse command line arguments
    case "${1:-deploy}" in
        "deploy")
            log "INFO" "Starting full layered deployment..."
            
            # Clean up existing deployment
            cleanup_existing
            
            # Deploy in dependency order: E-0a → E-0b → E-0c
            deploy_gate "Gate E-0a (Core Infrastructure)" "$GATE_E0A_FILE" "$GATE_E0A_VALIDATOR" || exit 1
            deploy_gate "Gate E-0b (Observability Infrastructure)" "$GATE_E0B_FILE" "$GATE_E0B_VALIDATOR" || exit 1
            deploy_gate "Gate E-0c (Applications with Observability)" "$GATE_E0C_FILE" "$GATE_E0C_VALIDATOR" || exit 1
            
            show_deployment_status
            show_access_info
            ;;
            
        "status")
            log "INFO" "Checking deployment status..."
            show_deployment_status
            ;;
            
        "cleanup"|"clean")
            log "INFO" "Cleaning up deployment..."
            cleanup_existing
            log "SUCCESS" "Cleanup completed"
            ;;
            
        "validate")
            log "INFO" "Running validation only..."
            bash "$GATE_E0A_VALIDATOR" || exit 1
            bash "$GATE_E0B_VALIDATOR" || exit 1  
            bash "$GATE_E0C_VALIDATOR" || exit 1
            log "SUCCESS" "All validations passed"
            ;;
            
        "help"|"-h"|"--help")
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  deploy     Deploy full layered stack (default)"
            echo "  status     Show current deployment status"
            echo "  cleanup    Clean up existing deployment"
            echo "  validate   Run validation scripts only"
            echo "  help       Show this help message"
            echo ""
            echo "Prerequisites:"
            echo "  OpenBao running at localhost:8200 (preferred - for secrets management)"
            echo "  OR environment variables set (fallback)"
            echo ""
            echo "Required Secrets (from OpenBao or environment):"
            echo "  POSTGRES_PASSWORD     - PostgreSQL password"
            echo "  REDIS_PASSWORD        - Redis password"
            echo "  CLICKHOUSE_PASSWORD   - ClickHouse password"
            echo "  VAULT_TOKEN           - OpenBao/Vault token"
            echo ""
            echo "Optional Configuration:"
            echo "  MGMT_SECRET_KEY       - Management platform secret"
            echo "  MGMT_JWT_SECRET_KEY   - Management platform JWT secret"
            echo "  APP_VERSION           - Application version (default: 1.0.0)"
            echo ""
            echo "OpenBao Integration:"
            echo "  ./setup-openbao-secrets.sh setup    - Initialize secrets"
            echo "  ./setup-openbao-secrets.sh export   - Export for deployment"
            ;;
            
        *)
            log "ERROR" "Unknown command: $1"
            log "INFO" "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Handle script interruption
trap 'log "WARNING" "Deployment interrupted by user"; exit 1' INT TERM

# Execute main function
main "$@"