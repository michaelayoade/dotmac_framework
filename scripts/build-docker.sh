#!/bin/bash
#
# Docker Build Automation Script
# 
# This script automates:
# 1. Poetry dependency verification
# 2. Requirements export
# 3. Docker image builds
#
# Usage:
#   ./scripts/build-docker.sh [--export-only] [--build-only] [--verify-only]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Check if Poetry is available
check_poetry() {
    log "Checking Poetry availability..."
    if command -v poetry &> /dev/null; then
        POETRY_CMD="poetry"
    elif [ -f "/root/.local/share/pypoetry/venv/bin/poetry" ]; then
        POETRY_CMD="/root/.local/share/pypoetry/venv/bin/poetry"
    else
        log_error "Poetry not found. Please install Poetry first."
        exit 1
    fi
    
    log "Using Poetry: $POETRY_CMD"
    $POETRY_CMD --version
}

# Install Poetry export plugin if not available
install_export_plugin() {
    log "Checking Poetry export plugin..."
    if $POETRY_CMD self show plugins | grep -q "poetry-plugin-export"; then
        log "Poetry export plugin already installed"
    else
        log "Installing Poetry export plugin..."
        $POETRY_CMD self add poetry-plugin-export
    fi
}

# Verify Poetry lock file
verify_poetry_lock() {
    log "Verifying Poetry lock file..."
    cd "$PROJECT_ROOT"
    
    if [ ! -f "poetry.lock" ]; then
        log_warning "poetry.lock not found. Generating..."
        $POETRY_CMD lock
    fi
    
    if $POETRY_CMD lock --check &>/dev/null; then
        log "Poetry lock file is up to date"
    else
        log_warning "Poetry lock file is outdated. Updating..."
        $POETRY_CMD lock
    fi
}

# Export dependencies to requirements.docker.txt
export_requirements() {
    log "Exporting dependencies to requirements.docker.txt..."
    cd "$PROJECT_ROOT"
    
    # Try Poetry export first
    if $POETRY_CMD export -f requirements.txt --output requirements.docker.txt --without-hashes --without-urls &>/dev/null; then
        log "Dependencies exported using Poetry export"
    else
        log_warning "Poetry export failed. Using fallback method..."
        
        # Fallback: use existing pyproject.docker.toml
        if [ -f "pyproject.docker.toml" ]; then
            log "Using existing requirements.docker.txt (manually maintained)"
        else
            log_error "No fallback method available"
            return 1
        fi
    fi
    
    # Validate requirements file
    if python3 -m pip install --dry-run -r requirements.docker.txt &>/dev/null; then
        log "requirements.docker.txt validated successfully"
    else
        log_error "requirements.docker.txt validation failed"
        return 1
    fi
}

# Build Docker image
build_docker_image() {
    local dockerfile=$1
    local image_name=$2
    local service=$3
    local tag=${4:-"latest"}
    
    log "Building Docker image: $image_name:$tag ($service service)"
    cd "$PROJECT_ROOT"
    
    if [ ! -f "$dockerfile" ]; then
        log_error "Dockerfile not found: $dockerfile"
        return 1
    fi
    
    # Check service-specific requirements file
    local requirements_file="requirements.${service}.txt"
    if [ ! -f "$requirements_file" ]; then
        log_error "Requirements file not found: $requirements_file"
        return 1
    fi
    
    log "Using requirements: $requirements_file"
    
    if docker build -f "$dockerfile" -t "$image_name:$tag" . &>/dev/null; then
        log "Successfully built $image_name:$tag"
        return 0
    else
        log_error "Failed to build $image_name:$tag"
        return 1
    fi
}

# Build specific service image
build_service_image() {
    local service=$1
    local tag=${2:-"automated"}
    
    case "$service" in
        management)
            build_docker_image "Dockerfile.management" "dotmac-management" "management" "$tag"
            ;;
        isp)
            build_docker_image "Dockerfile.isp" "dotmac-isp" "isp" "$tag"
            ;;
        *)
            log_error "Unknown service: $service. Use 'management' or 'isp'"
            return 1
            ;;
    esac
}

# Build all Docker images
build_all_images() {
    log "Building all Docker images..."
    
    local success=0
    
    # Build management service
    if build_service_image "management"; then
        ((success++))
    fi
    
    # Build ISP service  
    if build_service_image "isp"; then
        ((success++))
    fi
    
    if [ $success -eq 2 ]; then
        log "All Docker images built successfully!"
        return 0
    else
        log_error "Some Docker builds failed"
        return 1
    fi
}

# Main execution
main() {
    case "${1:-}" in
        --verify-only)
            log "Running verification only..."
            check_poetry
            verify_poetry_lock
            ;;
        --export-only)
            log "Running export only..."
            check_poetry
            install_export_plugin
            verify_poetry_lock
            export_requirements
            ;;
        --build-only)
            log "Running build only..."
            build_all_images
            ;;
        --build-management)
            log "Building management service only..."
            build_service_image "management"
            ;;
        --build-isp)
            log "Building ISP service only..."
            build_service_image "isp"
            ;;
        --help)
            echo "Docker Build Automation Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --verify-only      Check Poetry dependencies only"
            echo "  --export-only      Export requirements only"
            echo "  --build-only       Build all Docker images"
            echo "  --build-management Build management service only"
            echo "  --build-isp        Build ISP service only"
            echo "  --help            Show this help message"
            echo ""
            echo "Default: Run full automation (verify + export + build all)"
            ;;
        *)
            log "Running full automation..."
            check_poetry
            install_export_plugin
            verify_poetry_lock
            export_requirements
            build_all_images
            ;;
    esac
}

# Run main function
main "$@"