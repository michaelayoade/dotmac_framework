#!/usr/bin/env bash
set -euo pipefail

# DotMac Graceful Shutdown Script
# Gracefully stops all DotMac services

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"

# Default configuration
DEFAULT_TIMEOUT=30
DEFAULT_SERVICES="all"

# Configuration from environment
TIMEOUT="${TIMEOUT:-$DEFAULT_TIMEOUT}"
SERVICES="${SERVICES:-$DEFAULT_SERVICES}"

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Gracefully stop DotMac services.

OPTIONS:
    -h, --help              Show this help message
    -s, --services SERVICES Services to stop (all|backend|frontend|monitoring) (default: all)
    -t, --timeout TIMEOUT   Timeout in seconds (default: 30)
    -f, --force            Force stop without graceful shutdown
    -v, --verbose          Verbose output
    --keep-volumes         Don't remove Docker volumes
    --keep-networks        Don't remove Docker networks

EXAMPLES:
    $0                                          # Stop all services gracefully
    $0 -s backend                              # Stop only backend services
    $0 -f                                      # Force stop all services
    $0 -t 60                                   # Use 60-second timeout

ENVIRONMENT VARIABLES:
    TIMEOUT               Graceful shutdown timeout
    SERVICES              Which services to stop
EOF
}

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" >&2
}

error() {
    echo "[ERROR] $*" >&2
    exit 1
}

stop_frontend() {
    local force="$1"

    log "Stopping frontend services..."

    # Check for running frontend processes
    if [ -f "${FRONTEND_DIR}/.frontend-pids" ]; then
        local pids
        pids=$(cat "${FRONTEND_DIR}/.frontend-pids")

        if [ -n "$pids" ]; then
            log "Stopping frontend processes: $pids"

            if [ "$force" = true ]; then
                # Force kill
                kill -KILL $pids 2>/dev/null || true
            else
                # Graceful shutdown
                kill -TERM $pids 2>/dev/null || true

                # Wait for processes to exit
                local timeout_count=0
                while [ $timeout_count -lt "$TIMEOUT" ]; do
                    local running=false
                    for pid in $pids; do
                        if kill -0 "$pid" 2>/dev/null; then
                            running=true
                            break
                        fi
                    done

                    if [ "$running" = false ]; then
                        log "Frontend processes stopped gracefully"
                        break
                    fi

                    sleep 1
                    ((timeout_count++))
                done

                # Force kill if still running
                if [ $timeout_count -eq "$TIMEOUT" ]; then
                    log "Timeout reached, force killing frontend processes"
                    kill -KILL $pids 2>/dev/null || true
                fi
            fi
        fi

        rm -f "${FRONTEND_DIR}/.frontend-pids"
    fi

    # Stop any remaining Node.js processes
    log "Checking for remaining Node.js processes..."
    pkill -f "next|pnpm dev|node.*server.js" 2>/dev/null || true

    log "Frontend services stopped"
}

stop_docker_services() {
    local force="$1"
    local keep_volumes="$2"
    local keep_networks="$3"
    local service_type="$4"

    cd "$PROJECT_ROOT"

    case "$service_type" in
        backend)
            log "Stopping backend services..."
            stop_compose "docker-compose.yml" "$force" "$keep_volumes" "$keep_networks"
            ;;
        monitoring)
            log "Stopping monitoring services..."
            stop_compose "docker-compose.signoz.yml" "$force" "$keep_volumes" "$keep_networks"
            stop_compose "docker-compose.monitoring.yml" "$force" "$keep_volumes" "$keep_networks"
            ;;
        all)
            log "Stopping all Docker services..."
            # Stop in reverse order of dependencies
            stop_compose "docker-compose.signoz.yml" "$force" "$keep_volumes" "$keep_networks"
            stop_compose "docker-compose.monitoring.yml" "$force" "$keep_volumes" "$keep_networks"
            stop_compose "docker-compose.production.yml" "$force" "$keep_volumes" "$keep_networks"
            stop_compose "docker-compose.yml" "$force" "$keep_volumes" "$keep_networks"
            ;;
    esac
}

stop_compose() {
    local compose_file="$1"
    local force="$2"
    local keep_volumes="$3"
    local keep_networks="$4"

    if [ ! -f "$compose_file" ]; then
        return 0
    fi

    log "Stopping services from $compose_file..."

    local cmd="docker-compose -f $compose_file"

    if [ "$force" = true ]; then
        # Force stop
        $cmd kill
        $cmd rm -f
    else
        # Graceful stop
        timeout "$TIMEOUT" $cmd stop || {
            log "Timeout reached for $compose_file, force stopping..."
            $cmd kill
        }
        $cmd rm -f
    fi

    # Remove volumes if requested
    if [ "$keep_volumes" = false ]; then
        log "Removing volumes for $compose_file..."
        $cmd down --volumes 2>/dev/null || true
    fi

    # Remove networks if requested
    if [ "$keep_networks" = false ]; then
        log "Removing networks for $compose_file..."
        $cmd down --remove-orphans 2>/dev/null || true
    fi
}

cleanup_docker() {
    local keep_volumes="$1"
    local keep_networks="$2"

    log "Cleaning up Docker resources..."

    # Remove stopped containers
    log "Removing stopped containers..."
    docker container prune -f 2>/dev/null || true

    # Remove unused images
    log "Removing unused images..."
    docker image prune -f 2>/dev/null || true

    # Remove volumes if requested
    if [ "$keep_volumes" = false ]; then
        log "Removing unused volumes..."
        docker volume prune -f 2>/dev/null || true
    fi

    # Remove networks if requested
    if [ "$keep_networks" = false ]; then
        log "Removing unused networks..."
        docker network prune -f 2>/dev/null || true
    fi
}

main() {
    local force=false
    local verbose=false
    local keep_volumes=false
    local keep_networks=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -s|--services)
                SERVICES="$2"
                shift 2
                ;;
            -t|--timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            -f|--force)
                force=true
                shift
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            --keep-volumes)
                keep_volumes=true
                shift
                ;;
            --keep-networks)
                keep_networks=true
                shift
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done

    # Validate services
    case "$SERVICES" in
        all|backend|frontend|monitoring)
            log "Services to stop: $SERVICES"
            ;;
        *)
            error "Invalid services: $SERVICES. Must be one of: all, backend, frontend, monitoring"
            ;;
    esac

    log "Starting graceful shutdown..."
    log "Timeout: ${TIMEOUT}s"
    log "Force: $force"

    # Stop services based on selection
    case "$SERVICES" in
        frontend)
            stop_frontend "$force"
            ;;
        backend)
            stop_docker_services "$force" "$keep_volumes" "$keep_networks" "backend"
            ;;
        monitoring)
            stop_docker_services "$force" "$keep_volumes" "$keep_networks" "monitoring"
            ;;
        all)
            # Stop in proper order
            stop_frontend "$force"
            stop_docker_services "$force" "$keep_volumes" "$keep_networks" "all"
            cleanup_docker "$keep_volumes" "$keep_networks"
            ;;
    esac

    log "Shutdown complete"
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
