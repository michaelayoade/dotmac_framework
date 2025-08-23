#!/bin/bash

# DotMac ISP Framework - Docker Infrastructure Management Script
# Usage: ./scripts/docker-infrastructure.sh [command] [environment]

set -e

# Configuration
COMPOSE_PROJECT_NAME="dotmac_isp"
DOCKER_BUILDKIT=1
COMPOSE_DOCKER_CLI_BUILD=1

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

# Check if Docker and Docker Compose are installed
check_dependencies() {
    log_info "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    log_success "All dependencies are installed."
}

# Development Environment
start_dev() {
    log_info "Starting development environment..."
    export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME}_dev"
    
    docker-compose -f docker-compose.yml up -d --build
    
    log_info "Waiting for services to be ready..."
    sleep 10
    
    # Run database migrations
    log_info "Running database migrations..."
    docker-compose -f docker-compose.yml exec app alembic upgrade head
    
    log_success "Development environment is running!"
    log_info "Application: http://localhost:8000"
    log_info "Database: postgresql://dotmac:dotmac@localhost:5432/dotmac_isp"
    log_info "Redis: redis://localhost:6379"
    log_info "Nginx: http://localhost"
}

# Testing Environment
start_test() {
    log_info "Starting testing environment..."
    export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME}_test"
    
    # Build test containers
    docker-compose -f docker-compose.test.yml build
    
    # Start test infrastructure
    docker-compose -f docker-compose.test.yml up -d postgres_test redis_test
    
    log_info "Waiting for test services to be ready..."
    sleep 15
    
    log_success "Test environment is ready!"
}

# Run comprehensive tests
run_tests() {
    log_info "Running comprehensive test suite..."
    export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME}_test"
    
    # Ensure test infrastructure is running
    start_test
    
    # Create test reports directory
    mkdir -p test-reports
    
    # Run all tests
    log_info "Running all test categories..."
    docker-compose -f docker-compose.test.yml run --rm test_runner
    
    # Check test results
    if [ $? -eq 0 ]; then
        log_success "All tests passed! ✅"
        
        # Show test reports
        log_info "Test reports available at:"
        log_info "  - HTML Coverage: http://localhost:8080/htmlcov/"
        log_info "  - JUnit XML: test-reports/junit.xml"
        log_info "  - Coverage XML: test-reports/coverage.xml"
        
        # Start test report server
        docker-compose -f docker-compose.test.yml up -d test_reports
        
        return 0
    else
        log_error "Some tests failed! ❌"
        return 1
    fi
}

# Run specific test category
run_test_category() {
    local category=$1
    log_info "Running ${category} tests..."
    export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME}_test"
    
    # Ensure test infrastructure is running
    start_test
    
    case $category in
        "unit")
            docker-compose -f docker-compose.test.yml run --rm unit_tests
            ;;
        "integration")
            docker-compose -f docker-compose.test.yml run --rm integration_tests
            ;;
        "business")
            docker-compose -f docker-compose.test.yml run --rm business_logic_tests
            ;;
        "security")
            docker-compose -f docker-compose.test.yml run --rm security_tests
            ;;
        "performance")
            docker-compose -f docker-compose.test.yml run --rm performance_tests
            ;;
        *)
            log_error "Unknown test category: $category"
            log_info "Available categories: unit, integration, business, security, performance"
            exit 1
            ;;
    esac
}

# Production Environment
start_prod() {
    log_info "Starting production environment..."
    export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME}_prod"
    
    # Build production images
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
    
    # Start production stack
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
    
    log_info "Waiting for production services to be ready..."
    sleep 15
    
    # Run database migrations
    log_info "Running database migrations..."
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml exec app alembic upgrade head
    
    log_success "Production environment is running!"
    log_info "Application: https://localhost"
    log_warning "Make sure to configure SSL certificates and production secrets!"
}

# Stop all environments
stop_all() {
    log_info "Stopping all Docker environments..."
    
    # Stop development
    export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME}_dev"
    docker-compose -f docker-compose.yml down
    
    # Stop testing
    export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME}_test"
    docker-compose -f docker-compose.test.yml down
    
    # Stop production
    export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME}_prod"
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml down 2>/dev/null || true
    
    log_success "All environments stopped."
}

# Clean up Docker resources
cleanup() {
    log_info "Cleaning up Docker resources..."
    
    # Stop all containers
    stop_all
    
    # Remove unused containers, networks, images
    docker container prune -f
    docker network prune -f
    docker image prune -f
    
    # Remove volumes (WARNING: This will delete data!)
    read -p "Do you want to remove all Docker volumes? This will DELETE ALL DATA! (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume prune -f
        log_warning "All Docker volumes removed!"
    fi
    
    log_success "Cleanup completed."
}

# Show logs
show_logs() {
    local env=$1
    local service=$2
    
    case $env in
        "dev")
            export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME}_dev"
            docker-compose -f docker-compose.yml logs -f $service
            ;;
        "test")
            export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME}_test"
            docker-compose -f docker-compose.test.yml logs -f $service
            ;;
        "prod")
            export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME}_prod"
            docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f $service
            ;;
        *)
            log_error "Unknown environment: $env"
            exit 1
            ;;
    esac
}

# Show status
show_status() {
    log_info "Docker Infrastructure Status:"
    echo
    
    # Development
    log_info "Development Environment:"
    export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME}_dev"
    docker-compose -f docker-compose.yml ps
    echo
    
    # Testing
    log_info "Testing Environment:"
    export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME}_test"
    docker-compose -f docker-compose.test.yml ps
    echo
    
    # System resources
    log_info "Docker System Resources:"
    docker system df
}

# Health check
health_check() {
    local env=$1
    
    case $env in
        "dev")
            log_info "Checking development environment health..."
            export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME}_dev"
            
            # Check application health
            if curl -f http://localhost:8000/health > /dev/null 2>&1; then
                log_success "Application is healthy"
            else
                log_error "Application health check failed"
            fi
            
            # Check database
            docker-compose -f docker-compose.yml exec postgres pg_isready -U dotmac -d dotmac_isp
            
            # Check Redis
            docker-compose -f docker-compose.yml exec redis redis-cli ping
            ;;
        "test")
            log_info "Checking test environment health..."
            export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME}_test"
            
            docker-compose -f docker-compose.test.yml exec postgres_test pg_isready -U dotmac_test -d dotmac_isp_test
            docker-compose -f docker-compose.test.yml exec redis_test redis-cli ping
            ;;
        *)
            log_error "Unknown environment: $env"
            exit 1
            ;;
    esac
}

# Main command handler
main() {
    check_dependencies
    
    case $1 in
        "start")
            case $2 in
                "dev"|"development")
                    start_dev
                    ;;
                "test"|"testing")
                    start_test
                    ;;
                "prod"|"production")
                    start_prod
                    ;;
                *)
                    log_error "Please specify environment: dev, test, or prod"
                    exit 1
                    ;;
            esac
            ;;
        "test")
            case $2 in
                "all"|"")
                    run_tests
                    ;;
                "unit"|"integration"|"business"|"security"|"performance")
                    run_test_category $2
                    ;;
                *)
                    log_error "Unknown test category: $2"
                    exit 1
                    ;;
            esac
            ;;
        "stop")
            stop_all
            ;;
        "logs")
            show_logs $2 $3
            ;;
        "status")
            show_status
            ;;
        "health")
            health_check $2
            ;;
        "cleanup")
            cleanup
            ;;
        "help"|"-h"|"--help")
            echo "DotMac ISP Framework - Docker Infrastructure Management"
            echo
            echo "Usage: $0 [command] [options]"
            echo
            echo "Commands:"
            echo "  start <env>     Start environment (dev/test/prod)"
            echo "  test [category] Run tests (all/unit/integration/business/security/performance)"
            echo "  stop            Stop all environments"
            echo "  logs <env> [service] Show logs for environment"
            echo "  status          Show status of all environments"
            echo "  health <env>    Check health of environment"
            echo "  cleanup         Clean up Docker resources"
            echo "  help            Show this help message"
            echo
            echo "Examples:"
            echo "  $0 start dev                 # Start development environment"
            echo "  $0 test all                  # Run all tests"
            echo "  $0 test unit                 # Run unit tests only"
            echo "  $0 logs dev app              # Show app logs in dev environment"
            echo "  $0 health dev                # Check development environment health"
            ;;
        *)
            log_error "Unknown command: $1"
            log_info "Use '$0 help' for available commands"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"