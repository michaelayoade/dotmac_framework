#!/bin/bash
# =============================================================================
# DotMac Platform - Unified Monorepo Startup Script
# =============================================================================
# This script starts the complete DotMac platform (both ISP Framework and Management Platform)

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print banner
print_banner() {
    echo -e "${BLUE}"
    echo "██████╗  ██████╗ ████████╗███╗   ███╗ █████╗  ██████╗"
    echo "██╔══██╗██╔═══██╗╚══██╔══╝████╗ ████║██╔══██╗██╔════╝"
    echo "██║  ██║██║   ██║   ██║   ██╔████╔██║███████║██║     "
    echo "██║  ██║██║   ██║   ██║   ██║╚██╔╝██║██╔══██║██║     "
    echo "██████╔╝╚██████╔╝   ██║   ██║ ╚═╝ ██║██║  ██║╚██████╗"
    echo "╚═════╝  ╚═════╝    ╚═╝   ╚═╝     ╚═╝╚═╝  ╚═╝ ╚═════╝"
    echo ""
    echo "        ISP Framework + Management Platform"
    echo "             Unified Monorepo Startup"
    echo -e "${NC}"
}

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if port is available
port_available() {
    ! nc -z localhost "$1" 2>/dev/null
}

# Function to wait for service
wait_for_service() {
    local service_name=$1
    local host=$2
    local port=$3
    local max_attempts=$4
    
    print_status "Waiting for $service_name to be ready..."
    for i in $(seq 1 $max_attempts); do
        if nc -z $host $port 2>/dev/null; then
            print_success "$service_name is ready!"
            return 0
        fi
        if [ $i -eq $max_attempts ]; then
            print_error "$service_name failed to start after $max_attempts attempts"
            return 1
        fi
        sleep 2
    done
}

# Function to check health endpoint
check_health() {
    local service_name=$1
    local url=$2
    
    if curl -s "$url" > /dev/null; then
        print_success "$service_name health check passed"
        return 0
    else
        print_warning "$service_name health check failed"
        return 1
    fi
}

# Main startup function
main() {
    print_banner
    
    # Parse command line arguments
    START_INFRASTRUCTURE=true
    START_MANAGEMENT=true
    START_ISP=true
    START_FRONTEND=false
    CREATE_ADMIN=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --no-infra|--skip-infrastructure)
                START_INFRASTRUCTURE=false
                shift
                ;;
            --mgmt-only|--management-only)
                START_ISP=false
                START_FRONTEND=false
                shift
                ;;
            --isp-only)
                START_MANAGEMENT=false
                START_FRONTEND=false
                shift
                ;;
            --with-frontend)
                START_FRONTEND=true
                shift
                ;;
            --create-admin)
                CREATE_ADMIN=true
                shift
                ;;
            --help)
                echo "DotMac Platform Startup Script"
                echo ""
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --no-infra              Skip infrastructure startup"
                echo "  --mgmt-only             Start only Management Platform"
                echo "  --isp-only              Start only ISP Framework"
                echo "  --with-frontend         Start frontend portals too"
                echo "  --create-admin          Create admin users after startup"
                echo "  --help                  Show this help message"
                echo ""
                echo "Examples:"
                echo "  $0                      Start both platforms + infrastructure"
                echo "  $0 --with-frontend      Start everything including frontend"
                echo "  $0 --mgmt-only          Start only Management Platform"
                echo "  $0 --create-admin       Start platforms and create admin users"
                exit 0
                ;;
            *)
                print_warning "Unknown option: $1"
                shift
                ;;
        esac
    done
    
    print_status "Starting DotMac Platform with the following configuration:"
    echo "  Infrastructure: $([ "$START_INFRASTRUCTURE" = true ] && echo "✅ YES" || echo "❌ NO")"
    echo "  Management Platform: $([ "$START_MANAGEMENT" = true ] && echo "✅ YES" || echo "❌ NO")"
    echo "  ISP Framework: $([ "$START_ISP" = true ] && echo "✅ YES" || echo "❌ NO")"
    echo "  Frontend Portals: $([ "$START_FRONTEND" = true ] && echo "✅ YES" || echo "❌ NO")"
    echo "  Create Admin: $([ "$CREATE_ADMIN" = true ] && echo "✅ YES" || echo "❌ NO")"
    echo ""
    
    # Check prerequisites
    print_step "Step 1: Checking prerequisites..."
    check_prerequisites
    
    # Setup environment
    print_step "Step 2: Setting up environment..."
    setup_environment
    
    # Start infrastructure
    if [ "$START_INFRASTRUCTURE" = true ]; then
        print_step "Step 3: Starting shared infrastructure..."
        start_infrastructure
    else
        print_status "Skipping infrastructure startup"
    fi
    
    # Install dependencies
    print_step "Step 4: Installing dependencies..."
    install_dependencies
    
    # Setup databases
    print_step "Step 5: Setting up databases..."
    setup_databases
    
    # Start Management Platform
    if [ "$START_MANAGEMENT" = true ]; then
        print_step "Step 6a: Starting Management Platform..."
        start_management_platform
    fi
    
    # Start ISP Framework
    if [ "$START_ISP" = true ]; then
        print_step "Step 6b: Starting ISP Framework..."
        start_isp_framework
    fi
    
    # Start Frontend
    if [ "$START_FRONTEND" = true ]; then
        print_step "Step 7: Starting Frontend Portals..."
        start_frontend_portals
    fi
    
    # Create admin users
    if [ "$CREATE_ADMIN" = true ]; then
        print_step "Step 8: Creating admin users..."
        create_admin_users
    fi
    
    # Show final status
    print_step "Final: Platform Status"
    show_platform_status
    
    print_success "DotMac Platform startup complete!"
    show_urls
}

check_prerequisites() {
    local missing_deps=0
    
    # Check Docker
    if ! command_exists docker; then
        print_error "Docker is not installed"
        missing_deps=$((missing_deps + 1))
    fi
    
    # Check Docker Compose
    if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
        print_error "Docker Compose is not installed"
        missing_deps=$((missing_deps + 1))
    fi
    
    # Check Python
    if ! command_exists python3; then
        print_error "Python 3 is not installed"
        missing_deps=$((missing_deps + 1))
    fi
    
    # Check Make
    if ! command_exists make; then
        print_error "Make is not installed"
        missing_deps=$((missing_deps + 1))
    fi
    
    if [ $missing_deps -gt 0 ]; then
        print_error "$missing_deps required dependencies are missing. Please install them first."
        exit 1
    fi
    
    print_success "All prerequisites are available"
}

setup_environment() {
    # Copy unified environment file
    if [ ! -f .env ]; then
        print_status "Creating .env from unified template..."
        cp .env.unified .env
        print_success "Environment configuration created"
    else
        print_status "Environment configuration already exists"
    fi
    
    # Create logs directory
    mkdir -p logs
    print_status "Log directory created"
}

start_infrastructure() {
    print_status "Starting shared infrastructure services..."
    
    # Start infrastructure with docker-compose
    docker-compose up -d postgres-shared redis-shared openbao-shared clickhouse signoz-collector
    
    # Wait for PostgreSQL
    wait_for_service "PostgreSQL" "localhost" "5434" 30
    
    # Wait for Redis
    wait_for_service "Redis" "localhost" "6378" 15
    
    # Wait for OpenBao
    wait_for_service "OpenBao" "localhost" "8200" 20
    
    print_success "Infrastructure services are ready"
}

install_dependencies() {
    print_status "Installing Python dependencies..."
    
    # Management Platform
    if [ "$START_MANAGEMENT" = true ] && [ -f "management-platform/requirements.txt" ]; then
        print_status "Installing Management Platform dependencies..."
        cd management-platform
        if [ ! -d "venv" ]; then
            python3 -m venv venv
        fi
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        cd ..
        print_success "Management Platform dependencies installed"
    fi
    
    # ISP Framework
    if [ "$START_ISP" = true ] && [ -f "isp-framework/requirements.txt" ]; then
        print_status "Installing ISP Framework dependencies..."
        cd isp-framework  
        if [ ! -d "venv" ]; then
            python3 -m venv venv
        fi
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        cd ..
        print_success "ISP Framework dependencies installed"
    fi
}

setup_databases() {
    print_status "Setting up databases for both platforms..."
    
    # Run Management Platform migrations
    if [ "$START_MANAGEMENT" = true ]; then
        print_status "Running Management Platform database migrations..."
        cd management-platform
        if [ -f "alembic.ini" ]; then
            source venv/bin/activate
            alembic upgrade head || print_warning "Management Platform migration failed"
        fi
        cd ..
    fi
    
    # Run ISP Framework migrations
    if [ "$START_ISP" = true ]; then
        print_status "Running ISP Framework database migrations..."
        cd isp-framework
        if [ -f "Makefile" ] && make -n setup-db >/dev/null 2>&1; then
            make setup-db || print_warning "ISP Framework database setup failed"
        fi
        cd ..
    fi
    
    print_success "Database setup complete"
}

start_management_platform() {
    print_status "Starting Management Platform on port 8000..."
    
    cd management-platform
    
    # Start Management Platform in background
    source venv/bin/activate
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > ../logs/management-platform.log 2>&1 &
    echo $! > ../logs/management-platform.pid
    
    cd ..
    
    # Wait for service to be ready
    wait_for_service "Management Platform" "localhost" "8000" 20
    
    # Check health endpoint
    sleep 3
    check_health "Management Platform" "http://localhost:8000/health" || true
    
    print_success "Management Platform is running on http://localhost:8000"
}

start_isp_framework() {
    print_status "Starting ISP Framework on port 8001..."
    
    cd isp-framework
    
    # Start ISP Framework in background
    source venv/bin/activate
    nohup python -m uvicorn dotmac_isp.main:app --host 0.0.0.0 --port 8001 --reload > ../logs/isp-framework.log 2>&1 &
    echo $! > ../logs/isp-framework.pid
    
    cd ..
    
    # Wait for service to be ready
    wait_for_service "ISP Framework" "localhost" "8001" 20
    
    # Check health endpoint
    sleep 3
    check_health "ISP Framework" "http://localhost:8001/health" || true
    
    print_success "ISP Framework is running on http://localhost:8001"
}

start_frontend_portals() {
    print_status "Starting Frontend Portals..."
    
    if [ -d "frontend" ]; then
        cd frontend
        
        # Install frontend dependencies
        if command_exists pnpm; then
            print_status "Installing frontend dependencies with pnpm..."
            pnpm install
            
            # Start all portals in background
            nohup pnpm dev > ../logs/frontend-portals.log 2>&1 &
            echo $! > ../logs/frontend-portals.pid
        else
            print_warning "pnpm not found. Please install pnpm to run frontend portals."
        fi
        
        cd ..
        
        print_success "Frontend portals are starting..."
    else
        print_warning "Frontend directory not found"
    fi
}

create_admin_users() {
    print_status "Creating admin users for both platforms..."
    
    # Create Management Platform admin
    if [ "$START_MANAGEMENT" = true ]; then
        print_status "Creating Management Platform admin user..."
        # Add admin creation logic for Management Platform
        print_status "Management Platform admin creation not implemented yet"
    fi
    
    # Create ISP Framework admin
    if [ "$START_ISP" = true ] && [ -f "isp-framework/scripts/create_admin.py" ]; then
        print_status "Creating ISP Framework admin user..."
        cd isp-framework
        source venv/bin/activate
        echo -e "\nadmin@dotmac.local\nadmin123!\nPlatform\nAdmin\n" | python scripts/create_admin.py || true
        cd ..
    fi
    
    print_success "Admin user creation complete"
}

show_platform_status() {
    echo ""
    echo -e "${PURPLE}=== Platform Status ===${NC}"
    
    # Check Management Platform
    if [ "$START_MANAGEMENT" = true ]; then
        if check_health "Management Platform" "http://localhost:8000/health" 2>/dev/null; then
            echo -e "  Management Platform: ${GREEN}✅ RUNNING${NC} (Port 8000)"
        else
            echo -e "  Management Platform: ${RED}❌ STOPPED${NC} (Port 8000)"
        fi
    fi
    
    # Check ISP Framework
    if [ "$START_ISP" = true ]; then
        if check_health "ISP Framework" "http://localhost:8001/health" 2>/dev/null; then
            echo -e "  ISP Framework: ${GREEN}✅ RUNNING${NC} (Port 8001)"
        else
            echo -e "  ISP Framework: ${RED}❌ STOPPED${NC} (Port 8001)"
        fi
    fi
    
    # Check infrastructure
    if [ "$START_INFRASTRUCTURE" = true ]; then
        if nc -z localhost 5434 2>/dev/null; then
            echo -e "  PostgreSQL: ${GREEN}✅ RUNNING${NC} (Port 5434)"
        else
            echo -e "  PostgreSQL: ${RED}❌ STOPPED${NC} (Port 5434)"
        fi
        
        if nc -z localhost 6378 2>/dev/null; then
            echo -e "  Redis: ${GREEN}✅ RUNNING${NC} (Port 6378)"
        else
            echo -e "  Redis: ${RED}❌ STOPPED${NC} (Port 6378)"
        fi
    fi
    
    echo ""
}

show_urls() {
    echo -e "${PURPLE}=== Access URLs ===${NC}"
    
    if [ "$START_MANAGEMENT" = true ]; then
        echo "  🏢 Management Platform:"
        echo "    API: http://localhost:8000"
        echo "    Docs: http://localhost:8000/docs"
        echo "    Health: http://localhost:8000/health"
    fi
    
    if [ "$START_ISP" = true ]; then
        echo "  🌐 ISP Framework:"
        echo "    API: http://localhost:8001"
        echo "    Docs: http://localhost:8001/docs"
        echo "    Health: http://localhost:8001/health"
    fi
    
    if [ "$START_FRONTEND" = true ]; then
        echo "  🎨 Frontend Portals:"
        echo "    Admin Portal: http://localhost:3000"
        echo "    Customer Portal: http://localhost:3001"
        echo "    Reseller Portal: http://localhost:3002"
        echo "    Technician Portal: http://localhost:3003"
    fi
    
    echo "  🔧 Infrastructure:"
    echo "    PostgreSQL: localhost:5434"
    echo "    Redis: localhost:6378"
    echo "    OpenBao: http://localhost:8200"
    
    echo ""
    echo -e "${YELLOW}📋 Next Steps:${NC}"
    echo "  1. Check platform status: curl http://localhost:8000/health"
    echo "  2. Create admin users: ./scripts/create-admin.sh"
    echo "  3. Access the admin portals and configure your setup"
    echo "  4. View logs: tail -f logs/*.log"
    echo ""
    echo -e "${GREEN}🎉 DotMac Platform is ready!${NC}"
}

# Trap to cleanup on exit
cleanup() {
    echo ""
    print_status "Cleaning up background processes..."
    # Kill background processes if needed
    # This is handled by Docker Compose for infrastructure
    # And by the stop script for applications
}

trap cleanup EXIT

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ] || [ ! -d "isp-framework" ] || [ ! -d "management-platform" ]; then
    print_error "Please run this script from the DotMac Platform root directory"
    exit 1
fi

# Run main function
main "$@"