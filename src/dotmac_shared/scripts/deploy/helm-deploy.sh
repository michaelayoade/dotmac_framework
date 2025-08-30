#!/usr/bin/env bash
set -euo pipefail

# DotMac Helm Deployment Script
# Deploys DotMac services to Kubernetes using Helm

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Default configuration
DEFAULT_NAMESPACE="dotmac"
DEFAULT_RELEASE_NAME="dotmac-framework"
DEFAULT_CHART_PATH="${PROJECT_ROOT}/deployments/helm/dotmac-framework"
DEFAULT_ENVIRONMENT="development"

# Configuration from environment
NAMESPACE="${NAMESPACE:-$DEFAULT_NAMESPACE}"
RELEASE_NAME="${RELEASE_NAME:-$DEFAULT_RELEASE_NAME}"
CHART_PATH="${CHART_PATH:-$DEFAULT_CHART_PATH}"
ENVIRONMENT="${ENVIRONMENT:-$DEFAULT_ENVIRONMENT}"

usage() {
    cat << EOF
Usage: $0 [OPTIONS] COMMAND

Deploy DotMac services to Kubernetes using Helm.

COMMANDS:
    install                Install the Helm chart
    upgrade                Upgrade existing release
    uninstall              Uninstall the release
    status                 Show release status
    values                 Show computed values
    template               Show rendered templates

OPTIONS:
    -h, --help              Show this help message
    -n, --namespace NS      Kubernetes namespace (default: dotmac)
    -r, --release NAME      Helm release name (default: dotmac-framework)
    -c, --chart PATH        Path to Helm chart (default: deployments/helm/dotmac-framework)
    -e, --env ENVIRONMENT   Target environment (dev|staging|prod) (default: development)
    -f, --values FILE       Additional values file
    --set KEY=VALUE         Set individual values
    --dry-run              Show what would be deployed
    --wait                 Wait for deployment to complete
    --timeout TIMEOUT      Timeout for operations (default: 10m)

EXAMPLES:
    $0 install                                  # Install with default settings
    $0 upgrade -e production                   # Upgrade to production
    $0 install --dry-run                       # Preview installation
    $0 upgrade --set image.tag=v1.2.3         # Upgrade with custom image tag

ENVIRONMENT VARIABLES:
    NAMESPACE             Kubernetes namespace
    RELEASE_NAME          Helm release name
    CHART_PATH            Path to Helm chart
    ENVIRONMENT           Target environment
    KUBECONFIG            Kubernetes config file
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
    command -v helm >/dev/null 2>&1 || error "Helm is not installed"
    command -v kubectl >/dev/null 2>&1 || error "kubectl is not installed"

    # Check if we can connect to Kubernetes
    kubectl cluster-info >/dev/null 2>&1 || error "Cannot connect to Kubernetes cluster"

    # Check if chart exists
    [ -f "${CHART_PATH}/Chart.yaml" ] || error "Helm chart not found: $CHART_PATH"
}

create_namespace() {
    log "Ensuring namespace '$NAMESPACE' exists..."
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
}

get_values_file() {
    local env="$1"
    local values_file="${CHART_PATH}/values-${env}.yaml"

    # Check if environment-specific values file exists
    if [ -f "$values_file" ]; then
        echo "$values_file"
    else
        echo "${CHART_PATH}/values.yaml"
    fi
}

helm_install() {
    local dry_run="$1"
    local wait="$2"
    local timeout="$3"
    local extra_args=("${@:4}")

    log "Installing Helm release '$RELEASE_NAME' in namespace '$NAMESPACE'..."

    create_namespace

    local values_file
    values_file=$(get_values_file "$ENVIRONMENT")

    local cmd=(
        helm install "$RELEASE_NAME" "$CHART_PATH"
        --namespace "$NAMESPACE"
        --values "$values_file"
        --set environment="$ENVIRONMENT"
    )

    if [ "$dry_run" = true ]; then
        cmd+=(--dry-run)
    fi

    if [ "$wait" = true ]; then
        cmd+=(--wait --timeout "$timeout")
    fi

    # Add extra arguments
    cmd+=("${extra_args[@]}")

    log "Running: ${cmd[*]}"
    "${cmd[@]}"

    if [ "$dry_run" = false ]; then
        log "Installation completed successfully"
        log "Check status with: helm status $RELEASE_NAME -n $NAMESPACE"
    fi
}

helm_upgrade() {
    local dry_run="$1"
    local wait="$2"
    local timeout="$3"
    local extra_args=("${@:4}")

    log "Upgrading Helm release '$RELEASE_NAME' in namespace '$NAMESPACE'..."

    local values_file
    values_file=$(get_values_file "$ENVIRONMENT")

    local cmd=(
        helm upgrade "$RELEASE_NAME" "$CHART_PATH"
        --namespace "$NAMESPACE"
        --values "$values_file"
        --set environment="$ENVIRONMENT"
    )

    if [ "$dry_run" = true ]; then
        cmd+=(--dry-run)
    fi

    if [ "$wait" = true ]; then
        cmd+=(--wait --timeout "$timeout")
    fi

    # Add extra arguments
    cmd+=("${extra_args[@]}")

    log "Running: ${cmd[*]}"
    "${cmd[@]}"

    if [ "$dry_run" = false ]; then
        log "Upgrade completed successfully"
    fi
}

helm_uninstall() {
    local wait="$1"
    local timeout="$2"

    log "Uninstalling Helm release '$RELEASE_NAME' from namespace '$NAMESPACE'..."

    local cmd=(
        helm uninstall "$RELEASE_NAME"
        --namespace "$NAMESPACE"
    )

    if [ "$wait" = true ]; then
        cmd+=(--wait --timeout "$timeout")
    fi

    "${cmd[@]}"

    log "Uninstallation completed successfully"
}

helm_status() {
    log "Getting status of Helm release '$RELEASE_NAME'..."
    helm status "$RELEASE_NAME" --namespace "$NAMESPACE"
}

helm_values() {
    log "Getting computed values for Helm release '$RELEASE_NAME'..."
    helm get values "$RELEASE_NAME" --namespace "$NAMESPACE" --all
}

helm_template() {
    local extra_args=("${@}")

    log "Rendering templates for Helm chart..."

    local values_file
    values_file=$(get_values_file "$ENVIRONMENT")

    helm template "$RELEASE_NAME" "$CHART_PATH" \
        --namespace "$NAMESPACE" \
        --values "$values_file" \
        --set environment="$ENVIRONMENT" \
        "${extra_args[@]}"
}

main() {
    local command=""
    local dry_run=false
    local wait=false
    local timeout="10m"
    local extra_args=()

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -r|--release)
                RELEASE_NAME="$2"
                shift 2
                ;;
            -c|--chart)
                CHART_PATH="$2"
                shift 2
                ;;
            -e|--env)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -f|--values)
                extra_args+=(--values "$2")
                shift 2
                ;;
            --set)
                extra_args+=(--set "$2")
                shift 2
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --wait)
                wait=true
                shift
                ;;
            --timeout)
                timeout="$2"
                shift 2
                ;;
            install|upgrade|uninstall|status|values|template)
                command="$1"
                shift
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done

    # Validate command
    if [ -z "$command" ]; then
        error "Command is required. Use -h for help."
    fi

    # Validate environment
    case "$ENVIRONMENT" in
        development|dev|staging|production|prod)
            log "Environment: $ENVIRONMENT"
            ;;
        *)
            error "Invalid environment: $ENVIRONMENT. Must be one of: development, staging, production"
            ;;
    esac

    # Check dependencies
    check_dependencies

    log "Helm deployment for DotMac Framework"
    log "Command: $command"
    log "Release: $RELEASE_NAME"
    log "Namespace: $NAMESPACE"
    log "Environment: $ENVIRONMENT"
    log "Chart: $CHART_PATH"

    # Execute command
    case "$command" in
        install)
            helm_install "$dry_run" "$wait" "$timeout" "${extra_args[@]}"
            ;;
        upgrade)
            helm_upgrade "$dry_run" "$wait" "$timeout" "${extra_args[@]}"
            ;;
        uninstall)
            helm_uninstall "$wait" "$timeout"
            ;;
        status)
            helm_status
            ;;
        values)
            helm_values
            ;;
        template)
            helm_template "${extra_args[@]}"
            ;;
    esac
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
