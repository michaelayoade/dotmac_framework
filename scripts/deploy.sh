#!/bin/bash

# DotMac Platform Automated Deployment Script
# Supports Docker Compose and Kubernetes deployments with plugin orchestration

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEPLOYMENT_TYPE="${DEPLOYMENT_TYPE:-kubernetes}"
ENVIRONMENT="${ENVIRONMENT:-production}"
SKIP_TESTS="${SKIP_TESTS:-false}"
PLUGIN_REGISTRY_INIT="${PLUGIN_REGISTRY_INIT:-true}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Help function
show_help() {
    cat << EOF
DotMac Platform Deployment Script

Usage: ./scripts/deploy.sh [OPTIONS]

OPTIONS:
    -t, --type          Deployment type (docker|kubernetes) [default: kubernetes]
    -e, --environment   Environment (production|staging|development) [default: production]
    -s, --skip-tests    Skip pre-deployment tests [default: false]
    -p, --plugins       Initialize plugin registry [default: true]
    -h, --help          Show this help message

EXAMPLES:
    # Deploy to Kubernetes (production)
    ./scripts/deploy.sh

    # Deploy to Docker Compose (staging)
    ./scripts/deploy.sh --type docker --environment staging

    # Deploy without tests
    ./scripts/deploy.sh --skip-tests

    # Deploy with plugin registry initialization
    ./scripts/deploy.sh --plugins

ENVIRONMENT VARIABLES:
    DEPLOYMENT_TYPE     Override deployment type
    ENVIRONMENT         Override environment
    SKIP_TESTS         Skip pre-deployment tests
    PLUGIN_REGISTRY_INIT Initialize plugin registry
    KUBECONFIG         Kubernetes config file path
    DOCKER_REGISTRY    Docker registry URL

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--type)
                DEPLOYMENT_TYPE="$2"
                shift 2
                ;;
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -s|--skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            -p|--plugins)
                PLUGIN_REGISTRY_INIT=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Validate prerequisites
validate_prerequisites() {
    log_info "Validating prerequisites..."

    # Check deployment type
    if [[ "$DEPLOYMENT_TYPE" != "docker" && "$DEPLOYMENT_TYPE" != "kubernetes" ]]; then
        log_error "Invalid deployment type: $DEPLOYMENT_TYPE. Must be 'docker' or 'kubernetes'"
        exit 1
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is required but not installed"
        exit 1
    fi

    # Check Docker Compose for docker deployment
    if [[ "$DEPLOYMENT_TYPE" == "docker" ]] && ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is required for docker deployment"
        exit 1
    fi

    # Check kubectl for kubernetes deployment
    if [[ "$DEPLOYMENT_TYPE" == "kubernetes" ]] && ! command -v kubectl &> /dev/null; then
        log_error "kubectl is required for Kubernetes deployment"
        exit 1
    fi

    # Check environment file
    local env_file="${PROJECT_ROOT}/.env.${ENVIRONMENT}"
    if [[ ! -f "$env_file" ]]; then
        log_warning "Environment file not found: $env_file"
        log_info "Creating from template..."
        cp "${PROJECT_ROOT}/.env.${ENVIRONMENT}.template" "$env_file"
        log_warning "Please edit $env_file before deploying"
        exit 1
    fi

    log_success "Prerequisites validated"
}

# Run pre-deployment tests
run_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log_warning "Skipping tests as requested"
        return
    fi

    log_info "Running pre-deployment tests..."
    
    cd "$PROJECT_ROOT"
    
    # Plugin system tests
    if [[ -f "tests/test_plugin_system.py" ]]; then
        log_info "Running plugin system tests..."
        python -m pytest tests/test_plugin_system.py -v
    fi

    # API tests
    if [[ -f "tests/test_api.py" ]]; then
        log_info "Running API tests..."
        python -m pytest tests/test_api.py -v
    fi

    # E2E tests for critical paths
    if [[ -f "tests/e2e/management-tenant-communication.spec.ts" ]]; then
        log_info "Running E2E tests..."
        npm run test:dev4:smoke
    fi

    log_success "All tests passed"
}

# Build Docker images
build_images() {
    log_info "Building Docker images..."
    
    cd "$PROJECT_ROOT"
    
    # Get image tag from environment or use latest
    local image_tag="${DOCKER_IMAGE_TAG:-latest}"
    local registry="${DOCKER_REGISTRY:-dotmac}"
    
    # Build Management Platform image
    log_info "Building management platform image..."
    docker build \
        -f docker/Dockerfile.management \
        -t "${registry}/management:${image_tag}" \
        --target production \
        .
    
    # Build Plugin Runner image
    log_info "Building plugin runner image..."
    docker build \
        -f docker/Dockerfile.plugin-runner \
        -t "${registry}/plugin-runner:${image_tag}" \
        --target production \
        .
    
    # Build Plugin Registry image if exists
    if [[ -f "docker/Dockerfile.plugin-registry" ]]; then
        log_info "Building plugin registry image..."
        docker build \
            -f docker/Dockerfile.plugin-registry \
            -t "${registry}/plugin-registry:${image_tag}" \
            .
    fi
    
    log_success "Docker images built successfully"
}

# Deploy using Docker Compose
deploy_docker() {
    log_info "Deploying using Docker Compose..."
    
    cd "$PROJECT_ROOT"
    
    # Load environment variables
    set -a
    source ".env.${ENVIRONMENT}"
    set +a
    
    # Deploy with Docker Compose
    local compose_file="docker-compose.prod.yml"
    if [[ "$ENVIRONMENT" != "production" ]]; then
        compose_file="docker-compose.${ENVIRONMENT}.yml"
        if [[ ! -f "$compose_file" ]]; then
            compose_file="docker-compose.prod.yml"
        fi
    fi
    
    log_info "Using compose file: $compose_file"
    
    # Deploy services
    docker-compose -f "$compose_file" down --remove-orphans
    docker-compose -f "$compose_file" up -d
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 30
    
    # Health checks
    check_docker_health
    
    log_success "Docker deployment completed"
}

# Deploy to Kubernetes
deploy_kubernetes() {
    log_info "Deploying to Kubernetes..."
    
    cd "$PROJECT_ROOT"
    
    local k8s_namespace="dotmac-system"
    local plugin_namespace="dotmac-plugins"
    
    # Apply namespace first
    kubectl apply -f k8s/base/namespace.yaml
    
    # Create secrets from environment file
    create_k8s_secrets
    
    # Apply ConfigMaps
    kubectl apply -f k8s/base/configmap.yaml
    
    # Apply persistent volumes if needed
    if [[ -f "k8s/base/persistent-volumes.yaml" ]]; then
        kubectl apply -f k8s/base/persistent-volumes.yaml
    fi
    
    # Apply services
    kubectl apply -f k8s/base/services.yaml
    
    # Apply deployments
    kubectl apply -f k8s/base/management-deployment.yaml
    kubectl apply -f k8s/base/plugin-runner-deployment.yaml
    
    # Apply autoscaling
    kubectl apply -f k8s/base/horizontal-pod-autoscaler.yaml
    
    # Apply ingress
    kubectl apply -f k8s/base/ingress.yaml
    
    # Wait for rollout to complete
    log_info "Waiting for deployments to be ready..."
    kubectl rollout status deployment/dotmac-management -n "$k8s_namespace" --timeout=300s
    kubectl rollout status deployment/dotmac-plugin-runner -n "$plugin_namespace" --timeout=300s
    
    # Health checks
    check_k8s_health
    
    log_success "Kubernetes deployment completed"
}

# Create Kubernetes secrets from environment file
create_k8s_secrets() {
    log_info "Creating Kubernetes secrets..."
    
    local env_file=".env.${ENVIRONMENT}"
    
    if [[ ! -f "$env_file" ]]; then
        log_error "Environment file not found: $env_file"
        exit 1
    fi
    
    # Extract sensitive values
    local database_url=$(grep "^DATABASE_URL=" "$env_file" | cut -d'=' -f2)
    local redis_url=$(grep "^REDIS_URL=" "$env_file" | cut -d'=' -f2)
    local secret_key=$(grep "^SECRET_KEY=" "$env_file" | cut -d'=' -f2)
    local jwt_secret=$(grep "^JWT_SECRET=" "$env_file" | cut -d'=' -f2)
    
    # Create or update secret
    kubectl create secret generic dotmac-secrets \
        --namespace=dotmac-system \
        --from-literal=database-url="$database_url" \
        --from-literal=redis-url="$redis_url" \
        --from-literal=secret-key="$secret_key" \
        --from-literal=jwt-secret="$jwt_secret" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_success "Secrets created successfully"
}

# Check Docker deployment health
check_docker_health() {
    log_info "Checking Docker deployment health..."
    
    # Check management service
    local management_url="http://localhost:8000/api/health"
    if curl -f "$management_url" &>/dev/null; then
        log_success "Management service is healthy"
    else
        log_error "Management service health check failed"
        return 1
    fi
    
    # Check plugin runner if enabled
    if [[ "$PLUGIN_REGISTRY_INIT" == "true" ]]; then
        local plugin_url="http://localhost:8002/health"
        if curl -f "$plugin_url" &>/dev/null; then
            log_success "Plugin runner service is healthy"
        else
            log_warning "Plugin runner service health check failed"
        fi
    fi
}

# Check Kubernetes deployment health
check_k8s_health() {
    log_info "Checking Kubernetes deployment health..."
    
    local k8s_namespace="dotmac-system"
    local plugin_namespace="dotmac-plugins"
    
    # Check management pods
    local management_pods=$(kubectl get pods -n "$k8s_namespace" -l app.kubernetes.io/name=dotmac-management --no-headers | wc -l)
    if [[ "$management_pods" -gt 0 ]]; then
        log_success "Management pods are running ($management_pods pods)"
    else
        log_error "No management pods found"
        return 1
    fi
    
    # Check plugin runner pods
    local plugin_pods=$(kubectl get pods -n "$plugin_namespace" -l app.kubernetes.io/name=dotmac-plugin-runner --no-headers | wc -l)
    if [[ "$plugin_pods" -gt 0 ]]; then
        log_success "Plugin runner pods are running ($plugin_pods pods)"
    else
        log_warning "No plugin runner pods found"
    fi
    
    # Check services
    kubectl get services -n "$k8s_namespace"
    kubectl get services -n "$plugin_namespace"
}

# Initialize plugin registry
init_plugin_registry() {
    if [[ "$PLUGIN_REGISTRY_INIT" != "true" ]]; then
        log_info "Plugin registry initialization skipped"
        return
    fi
    
    log_info "Initializing plugin registry..."
    
    # Wait for services to be fully ready
    sleep 30
    
    if [[ "$DEPLOYMENT_TYPE" == "kubernetes" ]]; then
        # Run initialization in a Kubernetes job
        kubectl run plugin-registry-init \
            --namespace=dotmac-plugins \
            --image=dotmac/management:latest \
            --restart=Never \
            --command -- python -c "
import asyncio
import sys
sys.path.append('/app/src')

async def init_registry():
    try:
        from dotmac_shared.plugins.core.manager import PluginManager
        manager = PluginManager(registry_path='/app/plugins')
        await manager.initialize()
        print('Plugin registry initialized successfully')
    except Exception as e:
        print(f'Plugin registry initialization failed: {e}')
        sys.exit(1)

asyncio.run(init_registry())
"
        kubectl wait --for=condition=complete job/plugin-registry-init --namespace=dotmac-plugins --timeout=300s
        kubectl logs job/plugin-registry-init --namespace=dotmac-plugins
        kubectl delete job plugin-registry-init --namespace=dotmac-plugins
    else
        # Initialize via Docker Compose
        docker-compose exec -T management python -c "
import asyncio
import sys
sys.path.append('/app/src')

async def init_registry():
    try:
        from dotmac_shared.plugins.core.manager import PluginManager
        manager = PluginManager(registry_path='/app/plugins')
        await manager.initialize()
        print('Plugin registry initialized successfully')
    except Exception as e:
        print(f'Plugin registry initialization failed: {e}')
        sys.exit(1)

asyncio.run(init_registry())
"
    fi
    
    log_success "Plugin registry initialized"
}

# Main deployment function
main() {
    echo "=============================================="
    echo "    DotMac Platform Deployment Script"
    echo "=============================================="
    echo ""
    echo "Deployment Type: $DEPLOYMENT_TYPE"
    echo "Environment: $ENVIRONMENT"
    echo "Skip Tests: $SKIP_TESTS"
    echo "Plugin Registry Init: $PLUGIN_REGISTRY_INIT"
    echo ""

    # Parse command line arguments
    parse_args "$@"
    
    # Validate prerequisites
    validate_prerequisites
    
    # Run tests
    run_tests
    
    # Build images
    build_images
    
    # Deploy based on type
    if [[ "$DEPLOYMENT_TYPE" == "docker" ]]; then
        deploy_docker
    elif [[ "$DEPLOYMENT_TYPE" == "kubernetes" ]]; then
        deploy_kubernetes
    fi
    
    # Initialize plugin registry
    init_plugin_registry
    
    echo ""
    log_success "🎉 DotMac Platform deployment completed successfully!"
    echo ""
    
    if [[ "$DEPLOYMENT_TYPE" == "docker" ]]; then
        echo "Services are running at:"
        echo "  • Management API: http://localhost:8000"
        echo "  • Plugin Runner: http://localhost:8002"
        echo "  • Plugin Registry: http://localhost:8001"
    else
        echo "Services are deployed to Kubernetes cluster"
        echo "Check status with: kubectl get pods -n dotmac-system"
    fi
    
    echo ""
    log_info "For monitoring and logs:"
    if [[ "$DEPLOYMENT_TYPE" == "docker" ]]; then
        echo "  docker-compose logs -f"
    else
        echo "  kubectl logs -f deployment/dotmac-management -n dotmac-system"
    fi
}

# Run main function with all arguments
main "$@"