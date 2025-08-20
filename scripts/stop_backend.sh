#!/bin/bash

# DotMac Platform Backend Stop Script
# Stops all backend services gracefully

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
PID_DIR="$PROJECT_ROOT/pids"
LOG_DIR="$PROJECT_ROOT/logs"

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

# Function to stop a service by port
stop_service_by_port() {
    local service_name=$1
    local port=$2
    
    print_status "Stopping $service_name on port $port..."
    
    # Find process using the port
    local pid=$(lsof -ti:$port 2>/dev/null || true)
    
    if [ -n "$pid" ]; then
        kill $pid 2>/dev/null || kill -9 $pid 2>/dev/null || true
        print_success "$service_name stopped (PID: $pid)"
    else
        print_warning "$service_name was not running on port $port"
    fi
}

# Function to stop a service by PID file
stop_service_by_pidfile() {
    local service_name=$1
    local pid_file="$PID_DIR/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 $pid 2>/dev/null; then
            print_status "Stopping $service_name (PID: $pid)..."
            kill $pid 2>/dev/null || kill -9 $pid 2>/dev/null || true
            print_success "$service_name stopped"
        else
            print_warning "$service_name was not running (stale PID file)"
        fi
        rm -f "$pid_file"
    fi
}

# Function to stop all microservices
stop_microservices() {
    print_status "Stopping all microservices..."
    
    # Service definitions: name, port
    declare -a services=(
        "api-gateway:8000"
        "identity:8001"
        "billing:8002"
        "services:8003"
        "networking:8004"
        "analytics:8005"
        "platform:8006"
        "core-events:8007"
        "core-ops:8008"
    )
    
    # Stop each service
    for service_def in "${services[@]}"; do
        IFS=':' read -r name port <<< "$service_def"
        stop_service_by_port "$name" "$port"
        stop_service_by_pidfile "$name"
    done
    
    print_success "All microservices stopped"
}

# Function to stop FreeRADIUS
stop_freeradius() {
    print_status "Stopping FreeRADIUS..."
    
    if pgrep -x "radiusd" > /dev/null || pgrep -x "freeradius" > /dev/null; then
        sudo pkill -x radiusd 2>/dev/null || sudo pkill -x freeradius 2>/dev/null || true
        print_success "FreeRADIUS stopped"
    else
        print_warning "FreeRADIUS was not running"
    fi
}

# Function to clean up
cleanup() {
    print_status "Cleaning up..."
    
    # Clean PID files
    if [ -d "$PID_DIR" ]; then
        rm -f "$PID_DIR"/*.pid
        print_success "PID files cleaned"
    fi
    
    # Optionally clean logs (commented out by default)
    # if [ -d "$LOG_DIR" ]; then
    #     rm -f "$LOG_DIR"/*.log
    #     print_success "Log files cleaned"
    # fi
    
    print_success "Cleanup complete"
}

# Main execution
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║          DotMac Platform Backend Stop Script                ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Stop all microservices
    stop_microservices
    
    # Stop FreeRADIUS if requested
    if [ "$1" == "--all" ] || [ "$1" == "--with-radius" ]; then
        stop_freeradius
    fi
    
    # Clean up
    cleanup
    
    echo ""
    print_success "All services stopped successfully!"
    echo ""
    echo "To restart services, run: $SCRIPT_DIR/start_backend.sh"
    echo ""
}

# Run main function
main "$@"