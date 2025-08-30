#!/usr/bin/env bash
set -euo pipefail

# DotMac Monitoring Stack Startup Script
# Starts monitoring services (SigNoz, Prometheus, Grafana, etc.)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Default configuration
DEFAULT_STACK="signoz"
DEFAULT_COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.signoz.yml"

# Configuration from environment
MONITORING_STACK="${MONITORING_STACK:-$DEFAULT_STACK}"
COMPOSE_FILE="${COMPOSE_FILE:-$DEFAULT_COMPOSE_FILE}"

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Start the DotMac monitoring stack.

OPTIONS:
    -h, --help              Show this help message
    -s, --stack STACK       Monitoring stack (signoz|prometheus|all) (default: signoz)
    -f, --file FILE         Docker Compose file (default: docker-compose.signoz.yml)
    -d, --detach           Run in detached mode
    -v, --verbose          Verbose output
    --pull                 Pull images before starting
    --setup                Run initial setup/configuration

STACKS:
    signoz                 SigNoz observability platform (recommended)
    prometheus             Prometheus + Grafana stack
    all                    Both SigNoz and Prometheus

EXAMPLES:
    $0                                          # Start SigNoz stack
    $0 -s prometheus                           # Start Prometheus stack
    $0 --setup -d                              # Setup and start in detached mode

ENVIRONMENT VARIABLES:
    MONITORING_STACK      Which stack to start
    COMPOSE_FILE          Path to docker-compose file
    SIGNOZ_VERSION        SigNoz version (default: latest)
EOF
}

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" >&2
}

error() {
    echo "[ERROR] $*" >&2
    exit 1
}

check_dependencies() {
    command -v docker >/dev/null 2>&1 || error "Docker is not installed"
    command -v docker-compose >/dev/null 2>&1 || error "Docker Compose is not installed"

    # Check if Docker daemon is running
    docker info >/dev/null 2>&1 || error "Docker daemon is not running"
}

setup_signoz() {
    log "Setting up SigNoz..."

    # Create SigNoz data directories
    mkdir -p "${PROJECT_ROOT}/signoz-data/clickhouse"
    mkdir -p "${PROJECT_ROOT}/signoz-data/alertmanager"

    # Set proper permissions
    chmod 755 "${PROJECT_ROOT}/signoz-data"

    # Create SigNoz configuration if it doesn't exist
    if [ ! -f "${PROJECT_ROOT}/signoz/otel-collector-config.yaml" ]; then
        log "Creating SigNoz OTEL collector configuration..."
        mkdir -p "${PROJECT_ROOT}/signoz"
        cat > "${PROJECT_ROOT}/signoz/otel-collector-config.yaml" << 'EOF'
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318
        cors:
          allowed_origins:
            - "http://localhost:3000"
            - "http://localhost:3001"
            - "http://localhost:3002"

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024
  resource:
    attributes:
      - key: service.namespace
        value: dotmac
        action: upsert

exporters:
  clickhousetraces:
    endpoint: tcp://clickhouse:9000/?database=signoz_traces
  clickhousemetricswrite:
    endpoint: tcp://clickhouse:9000/?database=signoz_metrics
  clickhouselogsexporter:
    endpoint: tcp://clickhouse:9000/?database=signoz_logs

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch, resource]
      exporters: [clickhousetraces]
    metrics:
      receivers: [otlp]
      processors: [batch, resource]
      exporters: [clickhousemetricswrite]
    logs:
      receivers: [otlp]
      processors: [batch, resource]
      exporters: [clickhouselogsexporter]
EOF
    fi
}

setup_prometheus() {
    log "Setting up Prometheus..."

    # Create Prometheus data directories
    mkdir -p "${PROJECT_ROOT}/monitoring-data/prometheus"
    mkdir -p "${PROJECT_ROOT}/monitoring-data/grafana"

    # Set proper permissions
    chmod 755 "${PROJECT_ROOT}/monitoring-data"
}

wait_for_monitoring() {
    local stack="$1"
    log "Waiting for monitoring services to become healthy..."

    local max_attempts=60
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        case "$stack" in
            signoz)
                if curl -s http://localhost:3301/api/v1/health >/dev/null 2>&1; then
                    log "SigNoz is ready at http://localhost:3301"
                    return 0
                fi
                ;;
            prometheus)
                if curl -s http://localhost:9090/-/ready >/dev/null 2>&1; then
                    log "Prometheus is ready at http://localhost:9090"
                    return 0
                fi
                ;;
        esac

        log "Attempt $attempt/$max_attempts: Services not ready yet..."
        sleep 5
        ((attempt++))
    done

    error "Monitoring services failed to start within timeout"
}

start_signoz() {
    local detach="$1"

    log "Starting SigNoz monitoring stack..."

    export SIGNOZ_VERSION="${SIGNOZ_VERSION:-latest}"

    cd "$PROJECT_ROOT"

    local cmd="docker-compose -f docker-compose.signoz.yml"

    if [ "$detach" = true ]; then
        $cmd up -d
        wait_for_monitoring "signoz"
        log "SigNoz started successfully"
        log "Access SigNoz UI at: http://localhost:3301"
    else
        $cmd up
    fi
}

start_prometheus() {
    local detach="$1"

    log "Starting Prometheus monitoring stack..."

    cd "$PROJECT_ROOT"

    local cmd="docker-compose -f docker-compose.monitoring.yml"

    if [ "$detach" = true ]; then
        $cmd up -d
        wait_for_monitoring "prometheus"
        log "Prometheus stack started successfully"
        log "Access Prometheus at: http://localhost:9090"
        log "Access Grafana at: http://localhost:3000 (admin/admin)"
    else
        $cmd up
    fi
}

start_all() {
    local detach="$1"

    log "Starting all monitoring stacks..."

    # Start SigNoz first
    start_signoz true

    # Start Prometheus
    start_prometheus true

    if [ "$detach" = false ]; then
        log "All monitoring services started. Press Ctrl+C to stop."
        read -r -p "Press Enter to continue..."
    fi
}

main() {
    local detach=false
    local verbose=false
    local pull=false
    local setup=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -s|--stack)
                MONITORING_STACK="$2"
                shift 2
                ;;
            -f|--file)
                COMPOSE_FILE="$2"
                shift 2
                ;;
            -d|--detach)
                detach=true
                shift
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            --pull)
                pull=true
                shift
                ;;
            --setup)
                setup=true
                shift
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done

    # Validate stack
    case "$MONITORING_STACK" in
        signoz|prometheus|all)
            log "Monitoring stack: $MONITORING_STACK"
            ;;
        *)
            error "Invalid monitoring stack: $MONITORING_STACK. Must be one of: signoz, prometheus, all"
            ;;
    esac

    # Check dependencies
    check_dependencies

    # Change to project root
    cd "$PROJECT_ROOT"

    # Setup if requested
    if [ "$setup" = true ]; then
        case "$MONITORING_STACK" in
            signoz|all)
                setup_signoz
                ;;
        esac

        case "$MONITORING_STACK" in
            prometheus|all)
                setup_prometheus
                ;;
        esac
    fi

    # Pull images if requested
    if [ "$pull" = true ]; then
        log "Pulling monitoring images..."
        case "$MONITORING_STACK" in
            signoz)
                docker-compose -f docker-compose.signoz.yml pull
                ;;
            prometheus)
                docker-compose -f docker-compose.monitoring.yml pull
                ;;
            all)
                docker-compose -f docker-compose.signoz.yml pull
                docker-compose -f docker-compose.monitoring.yml pull
                ;;
        esac
    fi

    log "Starting DotMac monitoring..."
    log "Stack: $MONITORING_STACK"

    # Start based on stack
    case "$MONITORING_STACK" in
        signoz)
            start_signoz "$detach"
            ;;
        prometheus)
            start_prometheus "$detach"
            ;;
        all)
            start_all "$detach"
            ;;
    esac
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
