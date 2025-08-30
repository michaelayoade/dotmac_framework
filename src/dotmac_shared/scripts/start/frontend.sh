#!/usr/bin/env bash
set -euo pipefail

# DotMac Frontend Startup Script
# Starts the frontend applications (admin, customer, reseller portals)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"

# Default configuration
DEFAULT_MODE="development"
DEFAULT_APPS="admin,customer,reseller"

# Configuration from environment
MODE="${MODE:-$DEFAULT_MODE}"
APPS="${APPS:-$DEFAULT_APPS}"

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Start the DotMac frontend applications.

OPTIONS:
    -h, --help              Show this help message
    -m, --mode MODE         Development mode (development|production) (default: development)
    -a, --apps APPS         Comma-separated list of apps (admin,customer,reseller) (default: all)
    -p, --ports PORTS       Custom port mapping (format: admin:3000,customer:3001,reseller:3002)
    -d, --detach           Run in detached mode (production only)
    -v, --verbose          Verbose output
    --build                Build applications before starting
    --install              Install dependencies before starting

EXAMPLES:
    $0                                          # Start all apps in development
    $0 -a "admin,customer"                     # Start only admin and customer portals
    $0 -m production -d                        # Start in production mode, detached
    $0 --install --build                       # Install deps and build before starting

ENVIRONMENT VARIABLES:
    MODE                  Development mode (development|production)
    APPS                  Comma-separated list of apps to start
    NEXT_PUBLIC_API_URL   Backend API URL
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
    command -v node >/dev/null 2>&1 || error "Node.js is not installed"
    command -v pnpm >/dev/null 2>&1 || error "pnpm is not installed"

    # Check if we're in the frontend directory
    [ -f "${FRONTEND_DIR}/package.json" ] || error "Frontend directory not found: $FRONTEND_DIR"
}

install_dependencies() {
    log "Installing dependencies..."
    cd "$FRONTEND_DIR"
    pnpm install --frozen-lockfile
}

build_applications() {
    log "Building applications..."
    cd "$FRONTEND_DIR"

    # Parse apps to build
    IFS=',' read -ra app_list <<< "$APPS"
    for app in "${app_list[@]}"; do
        app=$(echo "$app" | xargs) # trim whitespace
        case "$app" in
            admin|customer|reseller)
                log "Building $app app..."
                pnpm --filter "@dotmac/${app}-app" build
                ;;
            *)
                error "Unknown app: $app. Must be one of: admin, customer, reseller"
                ;;
        esac
    done
}

start_development() {
    log "Starting frontend in development mode..."
    cd "$FRONTEND_DIR"

    # Parse apps to start
    IFS=',' read -ra app_list <<< "$APPS"

    if [ ${#app_list[@]} -eq 3 ] && [[ "$APPS" == *"admin"* ]] && [[ "$APPS" == *"customer"* ]] && [[ "$APPS" == *"reseller"* ]]; then
        # Start all apps with turbo
        log "Starting all applications with Turbo..."
        pnpm dev
    else
        # Start specific apps
        local pids=()

        for app in "${app_list[@]}"; do
            app=$(echo "$app" | xargs)
            case "$app" in
                admin)
                    log "Starting admin portal on port 3000..."
                    cd "${FRONTEND_DIR}/apps/admin"
                    pnpm dev &
                    pids+=($!)
                    cd "$FRONTEND_DIR"
                    ;;
                customer)
                    log "Starting customer portal on port 3001..."
                    cd "${FRONTEND_DIR}/apps/customer"
                    pnpm dev &
                    pids+=($!)
                    cd "$FRONTEND_DIR"
                    ;;
                reseller)
                    log "Starting reseller portal on port 3002..."
                    cd "${FRONTEND_DIR}/apps/reseller"
                    pnpm dev &
                    pids+=($!)
                    cd "$FRONTEND_DIR"
                    ;;
                *)
                    error "Unknown app: $app"
                    ;;
            esac
        done

        # Wait for all processes
        log "Frontend applications started. Press Ctrl+C to stop."
        trap 'log "Stopping frontend applications..."; kill ${pids[@]} 2>/dev/null; wait' INT TERM
        wait
    fi
}

start_production() {
    local detach="$1"

    log "Starting frontend in production mode..."
    cd "$FRONTEND_DIR"

    # Parse apps to start
    IFS=',' read -ra app_list <<< "$APPS"
    local pids=()

    for app in "${app_list[@]}"; do
        app=$(echo "$app" | xargs)
        case "$app" in
            admin)
                log "Starting admin portal in production mode..."
                cd "${FRONTEND_DIR}/apps/admin"
                if [ "$detach" = true ]; then
                    nohup pnpm start:custom > admin.log 2>&1 &
                    pids+=($!)
                else
                    pnpm start:custom &
                    pids+=($!)
                fi
                cd "$FRONTEND_DIR"
                ;;
            customer)
                log "Starting customer portal in production mode..."
                cd "${FRONTEND_DIR}/apps/customer"
                if [ "$detach" = true ]; then
                    nohup pnpm start:custom > customer.log 2>&1 &
                    pids+=($!)
                else
                    pnpm start:custom &
                    pids+=($!)
                fi
                cd "$FRONTEND_DIR"
                ;;
            reseller)
                log "Starting reseller portal in production mode..."
                cd "${FRONTEND_DIR}/apps/reseller"
                if [ "$detach" = true ]; then
                    nohup pnpm start:custom > reseller.log 2>&1 &
                    pids+=($!)
                else
                    pnpm start:custom &
                    pids+=($!)
                fi
                cd "$FRONTEND_DIR"
                ;;
            *)
                error "Unknown app: $app"
                ;;
        esac
    done

    if [ "$detach" = true ]; then
        log "Frontend applications started in detached mode"
        log "Process IDs: ${pids[*]}"
        echo "${pids[*]}" > "${FRONTEND_DIR}/.frontend-pids"
        log "To stop: kill \$(cat ${FRONTEND_DIR}/.frontend-pids)"
    else
        log "Frontend applications started. Press Ctrl+C to stop."
        trap 'log "Stopping frontend applications..."; kill ${pids[@]} 2>/dev/null; wait' INT TERM
        wait
    fi
}

main() {
    local install=false
    local build=false
    local detach=false
    local verbose=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -m|--mode)
                MODE="$2"
                shift 2
                ;;
            -a|--apps)
                APPS="$2"
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
            --install)
                install=true
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

    # Validate mode
    case "$MODE" in
        development|production)
            log "Mode: $MODE"
            ;;
        *)
            error "Invalid mode: $MODE. Must be one of: development, production"
            ;;
    esac

    # Check dependencies
    check_dependencies

    # Install dependencies if requested
    if [ "$install" = true ]; then
        install_dependencies
    fi

    # Build if requested or if production mode
    if [ "$build" = true ] || [ "$MODE" = "production" ]; then
        build_applications
    fi

    # Set up environment
    export NODE_ENV="$MODE"
    export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"
    export NEXT_PUBLIC_WEBSOCKET_URL="${NEXT_PUBLIC_WEBSOCKET_URL:-ws://localhost:3001}"

    log "Starting DotMac frontend..."
    log "Mode: $MODE"
    log "Apps: $APPS"
    log "API URL: $NEXT_PUBLIC_API_URL"

    # Start based on mode
    case "$MODE" in
        development)
            if [ "$detach" = true ]; then
                error "Detached mode is not supported in development"
            fi
            start_development
            ;;
        production)
            start_production "$detach"
            ;;
    esac
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
