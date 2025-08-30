#!/usr/bin/env bash
set -euo pipefail

# DotMac Backend Startup Script
# Starts the backend services using Docker Compose with configurable profiles

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Default configuration
DEFAULT_COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
DEFAULT_PROFILES="backend,database,monitoring"
DEFAULT_ENVIRONMENT="development"

# Configuration from environment
COMPOSE_FILE="${COMPOSE_FILE:-$DEFAULT_COMPOSE_FILE}"
COMPOSE_PROFILES="${COMPOSE_PROFILES:-$DEFAULT_PROFILES}"
ENVIRONMENT="${ENVIRONMENT:-$DEFAULT_ENVIRONMENT}"

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Start the DotMac backend services using Docker Compose.

OPTIONS:
    -h, --help              Show this help message
    -f, --file FILE         Docker Compose file (default: docker-compose.yml)
    -p, --profiles PROFILES Comma-separated list of profiles (default: backend,database,monitoring)
    -e, --env ENVIRONMENT   Environment (development|staging|production) (default: development)
    -d, --detach           Run in detached mode
    -v, --verbose          Verbose output
    --pull                 Pull images before starting
    --build                Build images before starting

EXAMPLES:
    $0                                          # Start with default profiles
    $0 -p "backend,database"                   # Start only backend and database
    $0 -e production -d                        # Start in production mode, detached
    $0 --build --pull                          # Build and pull before starting

ENVIRONMENT VARIABLES:
    COMPOSE_FILE      Path to docker-compose file
    COMPOSE_PROFILES  Comma-separated profiles to enable
    ENVIRONMENT       Target environment
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

validate_environment() {
    case "$ENVIRONMENT" in
        development|staging|production)
            log "Environment: $ENVIRONMENT"
            ;;
        *)
            error "Invalid environment: $ENVIRONMENT. Must be one of: development, staging, production"
            ;;
    esac
}

setup_environment() {
    export COMPOSE_FILE
    export COMPOSE_PROFILES
    export ENVIRONMENT

    # Set environment-specific variables
    case "$ENVIRONMENT" in
        development)
            export LOG_LEVEL="${LOG_LEVEL:-debug}"
            export POSTGRES_DB="${POSTGRES_DB:-dotmac_dev}"
            ;;
        staging)
            export LOG_LEVEL="${LOG_LEVEL:-info}"
            export POSTGRES_DB="${POSTGRES_DB:-dotmac_staging}"
            ;;
        production)
            export LOG_LEVEL="${LOG_LEVEL:-warn}"
            export POSTGRES_DB="${POSTGRES_DB:-dotmac_prod}"
            ;;
    esac
}

wait_for_services() {
    log "Waiting for services to become healthy..."

    local max_attempts=60
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker-compose ps --services --filter "status=running" | grep -q .; then
            log "Services are running"
            return 0
        fi

        log "Attempt $attempt/$max_attempts: Services not ready yet..."
        sleep 5
        ((attempt++))
    done

    error "Services failed to start within timeout"
}

main() {
    local detach=false
    local verbose=false
    local pull=false
    local build=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -f|--file)
                COMPOSE_FILE="$2"
                shift 2
                ;;
            -p|--profiles)
                COMPOSE_PROFILES="$2"
                shift 2
                ;;
            -e|--env)
                ENVIRONMENT="$2"
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
            --build)
                build=true
                shift
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done

    # Change to project root
    cd "$PROJECT_ROOT"

    # Validate dependencies and environment
    check_dependencies
    validate_environment
    setup_environment

    log "Starting DotMac backend services..."
    log "Compose file: $COMPOSE_FILE"
    log "Profiles: $COMPOSE_PROFILES"
    log "Environment: $ENVIRONMENT"

    # Build docker-compose command
    local cmd="docker-compose"

    if [ "$verbose" = true ]; then
        cmd="$cmd --verbose"
    fi

    if [ "$pull" = true ]; then
        log "Pulling latest images..."
        $cmd pull
    fi

    if [ "$build" = true ]; then
        log "Building images..."
        $cmd build
    fi

    # Start services
    log "Starting services..."
    if [ "$detach" = true ]; then
        $cmd up -d
        wait_for_services
        log "Backend services started successfully in detached mode"
        log "View logs with: docker-compose logs -f"
    else
        $cmd up
    fi
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
