#!/bin/bash

# DotMac Platform Backend Startup Script
# Starts all backend services in the correct order

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/pids"

# Create necessary directories
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Function to check if a service is running
is_service_running() {
    local port=$1
    nc -z localhost "$port" 2>/dev/null
    return $?
}

# Function to wait for a service to be ready
wait_for_service() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=0
    
    print_status "Waiting for $service_name on port $port..."
    
    while [ $attempt -lt $max_attempts ]; do
        if is_service_running "$port"; then
            print_success "$service_name is ready on port $port"
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done
    
    print_error "$service_name failed to start on port $port"
    return 1
}

# Function to start a Python service
start_python_service() {
    local service_name=$1
    local module=$2
    local port=$3
    local log_file="$LOG_DIR/${service_name}.log"
    local pid_file="$PID_DIR/${service_name}.pid"
    
    # Check if already running
    if is_service_running "$port"; then
        print_warning "$service_name already running on port $port"
        return 0
    fi
    
    print_status "Starting $service_name..."
    
    # Start the service
    cd "$PROJECT_ROOT"
    nohup python -m "$module" > "$log_file" 2>&1 &
    local pid=$!
    echo $pid > "$pid_file"
    
    # Wait for service to be ready
    if wait_for_service "$service_name" "$port"; then
        return 0
    else
        # Kill the process if it didn't start properly
        if [ -f "$pid_file" ]; then
            kill $(cat "$pid_file") 2>/dev/null || true
            rm -f "$pid_file"
        fi
        return 1
    fi
}

# Function to check environment
check_environment() {
    print_status "Checking environment..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    # Check .env file
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        print_warning ".env file not found, creating from example..."
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    fi
    
    # Source environment variables
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
    
    print_success "Environment check complete"
}

# Function to start database services
start_databases() {
    print_status "Starting database services..."
    
    # Check PostgreSQL
    if pg_isready -h localhost -p 5432 &> /dev/null; then
        print_success "PostgreSQL is already running"
    else
        print_warning "PostgreSQL is not running. Please start it manually:"
        echo "  sudo systemctl start postgresql"
        echo "  or"
        echo "  docker run -d --name postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:15"
        return 1
    fi
    
    # Check Redis
    if redis-cli ping &> /dev/null; then
        print_success "Redis is already running"
    else
        print_warning "Redis is not running. Please start it manually:"
        echo "  sudo systemctl start redis"
        echo "  or"
        echo "  docker run -d --name redis -p 6379:6379 redis:7"
        return 1
    fi
    
    # Check FreeRADIUS
    if pgrep -x "radiusd" > /dev/null || pgrep -x "freeradius" > /dev/null; then
        print_success "FreeRADIUS is already running"
    else
        print_warning "FreeRADIUS is not running. Starting it..."
        # Try to start FreeRADIUS
        if command -v freeradius &> /dev/null; then
            sudo freeradius -X > "$LOG_DIR/freeradius.log" 2>&1 &
            sleep 2
            if pgrep -x "freeradius" > /dev/null; then
                print_success "FreeRADIUS started"
            else
                print_warning "FreeRADIUS failed to start. You can start it manually:"
                echo "  sudo freeradius -X"
                echo "  or"
                echo "  docker run -d --name freeradius -p 1812:1812/udp -p 1813:1813/udp freeradius/freeradius-server"
            fi
        else
            print_warning "FreeRADIUS is not installed. You can run it with Docker:"
            echo "  docker run -d --name freeradius -p 1812:1812/udp -p 1813:1813/udp freeradius/freeradius-server"
        fi
    fi
    
    return 0
}

# Function to initialize database
initialize_database() {
    print_status "Initializing database..."
    
    # Run migrations or create tables
    cd "$PROJECT_ROOT"
    
    # Check if database exists
    if psql -U postgres -h localhost -lqt | cut -d \| -f 1 | grep -qw dotmac; then
        print_success "Database 'dotmac' already exists"
    else
        print_status "Creating database 'dotmac'..."
        createdb -U postgres -h localhost dotmac || true
        print_success "Database created"
    fi
    
    # Run any pending migrations (if using alembic or similar)
    # python -m alembic upgrade head || true
    
    print_success "Database initialization complete"
}

# Function to start all microservices
start_microservices() {
    print_status "Starting microservices..."
    
    # Service definitions: name, module, port
    declare -a services=(
        "api-gateway:dotmac_api_gateway.aggregator:8000"
        "identity:dotmac_identity.main:8001"
        "billing:dotmac_billing.main:8002"
        "services:dotmac_services.main:8003"
        "networking:dotmac_networking.main:8004"
        "analytics:dotmac_analytics.main:8005"
        "platform:dotmac_platform.app:8006"
        "core-events:dotmac_core_events.api.rest:8007"
        "core-ops:dotmac_core_ops.main:8008"
    )
    
    # Start each service
    for service_def in "${services[@]}"; do
        IFS=':' read -r name module port <<< "$service_def"
        start_python_service "$name" "$module" "$port" || print_warning "Failed to start $name"
    done
    
    print_success "All microservices started"
}

# Function to show service status
show_status() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              DotMac Platform Service Status                 ║"
    echo "╠════════════════════════════════════════════════════════════╣"
    
    # Check each service
    declare -a services=(
        "API Gateway:8000"
        "Identity Service:8001"
        "Billing Service:8002"
        "Services Platform:8003"
        "Networking Service:8004"
        "Analytics Service:8005"
        "Platform Service:8006"
        "Core Events:8007"
        "Core Ops:8008"
    )
    
    for service_def in "${services[@]}"; do
        IFS=':' read -r name port <<< "$service_def"
        printf "║ %-30s: " "$name"
        if is_service_running "$port"; then
            printf "${GREEN}%-26s${NC} ║\n" "Running (port $port)"
        else
            printf "${RED}%-26s${NC} ║\n" "Not Running"
        fi
    done
    
    echo "╠════════════════════════════════════════════════════════════╣"
    
    # Database status
    printf "║ %-30s: " "PostgreSQL"
    if pg_isready -h localhost -p 5432 &> /dev/null; then
        printf "${GREEN}%-26s${NC} ║\n" "Running"
    else
        printf "${RED}%-26s${NC} ║\n" "Not Running"
    fi
    
    printf "║ %-30s: " "Redis"
    if redis-cli ping &> /dev/null; then
        printf "${GREEN}%-26s${NC} ║\n" "Running"
    else
        printf "${RED}%-26s${NC} ║\n" "Not Running"
    fi
    
    printf "║ %-30s: " "FreeRADIUS"
    if pgrep -x "radiusd" > /dev/null || pgrep -x "freeradius" > /dev/null; then
        printf "${GREEN}%-26s${NC} ║\n" "Running"
    else
        printf "${RED}%-26s${NC} ║\n" "Not Running"
    fi
    
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
}

# Function to show access URLs
show_urls() {
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                    Service Access URLs                      ║"
    echo "╠════════════════════════════════════════════════════════════╣"
    echo "║ API Gateway:        http://localhost:8000                   ║"
    echo "║ Swagger Docs:       http://localhost:8000/docs              ║"
    echo "║ ReDoc:              http://localhost:8000/redoc             ║"
    echo "║ Health Check:       http://localhost:8000/health            ║"
    echo "╠════════════════════════════════════════════════════════════╣"
    echo "║ Individual Services:                                        ║"
    echo "║ - Identity:         http://localhost:8001                   ║"
    echo "║ - Billing:          http://localhost:8002                   ║"
    echo "║ - Services:         http://localhost:8003                   ║"
    echo "║ - Networking:       http://localhost:8004                   ║"
    echo "║ - Analytics:        http://localhost:8005                   ║"
    echo "║ - Platform:         http://localhost:8006                   ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
}

# Main execution
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║         DotMac Platform Backend Startup Script              ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Check environment
    check_environment
    
    # Start databases
    if ! start_databases; then
        print_error "Database services are required. Please start them first."
        exit 1
    fi
    
    # Initialize database
    initialize_database
    
    # Start microservices
    start_microservices
    
    # Show status
    show_status
    
    # Show URLs
    show_urls
    
    print_success "Backend startup complete!"
    echo ""
    echo "To stop all services, run: $SCRIPT_DIR/stop_backend.sh"
    echo "To view logs, check: $LOG_DIR/"
    echo ""
}

# Run main function
main "$@"