#!/bin/bash

# DotMac Platform Startup Script with SignOz Observability
# Replaces Prometheus/Grafana with unified SignOz platform

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        exit 1
    fi
    
    log_success "All prerequisites met"
}

# Load environment variables
load_environment() {
    log_info "Loading SignOz environment configuration..."
    
    if [ -f ".env.signoz" ]; then
        export $(cat .env.signoz | grep -v '^#' | xargs)
        log_success "Environment loaded from .env.signoz"
    else
        log_warning ".env.signoz not found, using defaults"
        cp .env.signoz.example .env.signoz 2>/dev/null || true
    fi
}

# Start SignOz stack
start_signoz() {
    log_info "Starting SignOz observability stack..."
    
    # Create necessary directories
    mkdir -p signoz/dashboards
    mkdir -p signoz/alerts
    mkdir -p secrets
    
    # Generate secrets if they don't exist
    if [ ! -f "secrets/signoz_jwt_secret.txt" ]; then
        openssl rand -base64 32 > secrets/signoz_jwt_secret.txt
        log_info "Generated SignOz JWT secret"
    fi
    
    # Start SignOz services
    docker-compose -f docker-compose.monitoring.yml up -d
    
    # Wait for SignOz to be ready
    log_info "Waiting for SignOz to be ready..."
    sleep 10
    
    # Check health
    if curl -s http://localhost:13133/health > /dev/null 2>&1; then
        log_success "SignOz collector is healthy"
    else
        log_warning "SignOz collector health check failed"
    fi
    
    if curl -s http://localhost:3301 > /dev/null 2>&1; then
        log_success "SignOz UI is accessible at http://localhost:3301"
    else
        log_warning "SignOz UI not yet ready"
    fi
}

# Start backend services
start_backend_services() {
    log_info "Starting DotMac backend services with SignOz instrumentation..."
    
    # Install Python dependencies
    if [ ! -d "backend/venv" ]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv backend/venv
    fi
    
    # Activate virtual environment
    source backend/venv/bin/activate
    
    # Install requirements
    log_info "Installing Python dependencies..."
    pip install -q --upgrade pip
    pip install -q -r backend/requirements-secure.txt
    
    # Install OpenTelemetry instrumentation packages
    pip install -q \
        opentelemetry-api \
        opentelemetry-sdk \
        opentelemetry-instrumentation-fastapi \
        opentelemetry-instrumentation-sqlalchemy \
        opentelemetry-instrumentation-redis \
        opentelemetry-instrumentation-httpx \
        opentelemetry-instrumentation-logging \
        opentelemetry-exporter-otlp \
        opentelemetry-exporter-prometheus
    
    # Start unified service manager
    log_info "Starting all microservices..."
    python backend/main_unified.py &
    BACKEND_PID=$!
    
    # Store PID for cleanup
    echo $BACKEND_PID > .backend.pid
    
    log_success "Backend services started (PID: $BACKEND_PID)"
}

# Start frontend (if needed)
start_frontend() {
    log_info "Starting frontend applications..."
    
    cd frontend
    
    # Install dependencies
    if [ ! -d "node_modules" ]; then
        log_info "Installing frontend dependencies..."
        pnpm install
    fi
    
    # Start all frontend apps
    pnpm dev &
    FRONTEND_PID=$!
    
    # Store PID
    echo $FRONTEND_PID > ../.frontend.pid
    
    cd ..
    
    log_success "Frontend started (PID: $FRONTEND_PID)"
}

# Setup SignOz dashboards
setup_dashboards() {
    log_info "Setting up SignOz dashboards..."
    
    # Wait for SignOz to be fully ready
    sleep 20
    
    # Import default dashboards
    python3 scripts/setup_signoz_dashboards.py
    
    log_success "SignOz dashboards configured"
}

# Migrate from Prometheus/Grafana
migrate_from_prometheus() {
    log_info "Checking for Prometheus/Grafana migration..."
    
    # Check if Prometheus is running
    if docker ps | grep -q prometheus; then
        log_warning "Prometheus detected. Starting migration..."
        
        # Run migration script
        python3 scripts/migrate_to_signoz.py \
            --grafana-url http://localhost:3000 \
            --grafana-api-key ${GRAFANA_API_KEY:-admin} \
            --prometheus-url http://localhost:9090 \
            --signoz-url http://localhost:3301 \
            --migrate-dashboards \
            --migrate-alerts
        
        log_success "Migration completed"
        
        # Stop old stack
        log_info "Stopping Prometheus/Grafana..."
        docker-compose -f docker-compose.old-monitoring.yml down
    else
        log_info "No Prometheus installation detected, skipping migration"
    fi
}

# Show status
show_status() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║          DotMac Platform with SignOz - Status             ║"
    echo "╠════════════════════════════════════════════════════════════╣"
    echo "║ Component          │ Status    │ URL                       ║"
    echo "╠────────────────────┼───────────┼───────────────────────────╣"
    
    # Check SignOz UI
    if curl -s http://localhost:3301 > /dev/null 2>&1; then
        echo "║ SignOz UI          │ ✅ Running │ http://localhost:3301     ║"
    else
        echo "║ SignOz UI          │ ❌ Down    │ http://localhost:3301     ║"
    fi
    
    # Check OTLP Collector
    if curl -s http://localhost:13133/health > /dev/null 2>&1; then
        echo "║ OTLP Collector     │ ✅ Running │ localhost:4317 (gRPC)     ║"
    else
        echo "║ OTLP Collector     │ ❌ Down    │ localhost:4317 (gRPC)     ║"
    fi
    
    # Check API Gateway
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "║ API Gateway        │ ✅ Running │ http://localhost:8000     ║"
    else
        echo "║ API Gateway        │ ❌ Down    │ http://localhost:8000     ║"
    fi
    
    # Check ClickHouse
    if docker ps | grep -q clickhouse; then
        echo "║ ClickHouse DB      │ ✅ Running │ localhost:9000            ║"
    else
        echo "║ ClickHouse DB      │ ❌ Down    │ localhost:9000            ║"
    fi
    
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📊 SignOz Dashboard: http://localhost:3301"
    echo "🔍 Query your data using SQL in SignOz!"
    echo "📈 All metrics, traces, and logs in one place"
    echo ""
}

# Cleanup function
cleanup() {
    log_info "Shutting down services..."
    
    # Stop backend
    if [ -f ".backend.pid" ]; then
        kill $(cat .backend.pid) 2>/dev/null || true
        rm .backend.pid
    fi
    
    # Stop frontend
    if [ -f ".frontend.pid" ]; then
        kill $(cat .frontend.pid) 2>/dev/null || true
        rm .frontend.pid
    fi
    
    log_success "Services stopped"
}

# Main execution
main() {
    echo ""
    echo "🚀 Starting DotMac Platform with SignOz Observability"
    echo "=================================================="
    echo ""
    
    # Set trap for cleanup
    trap cleanup EXIT
    
    # Run startup sequence
    check_prerequisites
    load_environment
    migrate_from_prometheus
    start_signoz
    start_backend_services
    # start_frontend  # Uncomment if you want to start frontend
    setup_dashboards
    show_status
    
    echo ""
    log_success "DotMac Platform is running with SignOz observability!"
    echo ""
    echo "Press Ctrl+C to stop all services"
    echo ""
    
    # Keep script running
    wait
}

# Parse command line arguments
case "${1:-}" in
    start)
        main
        ;;
    stop)
        cleanup
        docker-compose -f docker-compose.monitoring.yml down
        ;;
    restart)
        cleanup
        docker-compose -f docker-compose.monitoring.yml down
        main
        ;;
    status)
        show_status
        ;;
    migrate)
        migrate_from_prometheus
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|migrate}"
        echo ""
        echo "  start   - Start all services with SignOz"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  status  - Show service status"
        echo "  migrate - Migrate from Prometheus/Grafana to SignOz"
        exit 1
        ;;
esac