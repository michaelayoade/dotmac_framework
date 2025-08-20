#!/bin/bash

# DotMac Platform - Service Startup Script
# This script starts all DotMac services in the correct order

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
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

# Function to check if a port is open
check_port() {
    local host=$1
    local port=$2
    timeout 1 bash -c "cat < /dev/null > /dev/tcp/$host/$port" 2>/dev/null
    return $?
}

# Function to wait for a service to be ready
wait_for_service() {
    local service_name=$1
    local host=$2
    local port=$3
    local max_attempts=30
    local attempt=0
    
    print_info "Waiting for $service_name to be ready..."
    
    while [ $attempt -lt $max_attempts ]; do
        if check_port $host $port; then
            print_success "$service_name is ready!"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    
    print_error "$service_name failed to start (timeout)"
    return 1
}

# Main execution
clear
echo "========================================="
echo "   DotMac Platform Service Manager"
echo "========================================="
echo ""

# Check for command argument
COMMAND=${1:-status}

case $COMMAND in
    start)
        print_info "Starting DotMac Platform Services..."
        echo ""
        
        # Step 1: Check infrastructure services
        print_info "Checking infrastructure services..."
        
        if ! check_port localhost 5432; then
            print_warning "PostgreSQL not running. Starting infrastructure..."
            docker-compose -f docker-compose.simple.yml up -d
            wait_for_service "PostgreSQL" localhost 5432
        else
            print_success "PostgreSQL is running"
        fi
        
        if ! check_port localhost 6379; then
            print_warning "Redis not running. Starting..."
            docker-compose -f docker-compose.simple.yml up -d redis
            wait_for_service "Redis" localhost 6379
        else
            print_success "Redis is running"
        fi
        
        echo ""
        print_info "Infrastructure services ready!"
        echo ""
        
        # Step 2: Install Python dependencies
        print_info "Installing Python dependencies..."
        pip3 install --user -q \
            fastapi==0.104.1 \
            uvicorn==0.24.0 \
            pydantic==2.5.0 \
            httpx==0.25.1 \
            redis==5.0.1 \
            psycopg2-binary==2.9.9 \
            sqlalchemy==2.0.23 \
            alembic==1.12.1 \
            python-multipart==0.0.6 \
            python-jose==3.3.0 \
            passlib==1.7.4 \
            bcrypt==4.1.1 \
            tenacity==8.2.3 \
            pysnmp==7.1.0 \
            paramiko==3.3.1 \
            networkx==3.2 \
            matplotlib==3.8.2 \
            2>/dev/null || print_warning "Some packages may already be installed"
        
        print_success "Dependencies installed"
        echo ""
        
        # Step 3: Start services in order
        print_info "Starting microservices..."
        echo ""
        
        # Create logs directory
        mkdir -p logs
        
        # Start services (using nohup to run in background)
        services=(
            "dotmac_platform:8006:Platform Service"
            "dotmac_core_events:8007:Event Bus"
            "dotmac_identity:8001:Identity Service"
            "dotmac_billing:8002:Billing Service"
            "dotmac_services:8003:Services Provisioning"
            "dotmac_networking:8004:Network Management"
            "dotmac_analytics:8005:Analytics Service"
            "dotmac_core_ops:8008:Core Ops"
            "dotmac_api_gateway:8000:API Gateway"
        )
        
        for service_info in "${services[@]}"; do
            IFS=':' read -r service port name <<< "$service_info"
            
            if check_port localhost $port; then
                print_warning "$name already running on port $port"
            else
                print_info "Starting $name..."
                
                # Special handling for different services
                case $service in
                    dotmac_platform)
                        cd dotmac_platform && \
                        nohup python3 -m dotmac_platform.app > ../logs/${service}.log 2>&1 &
                        cd ..
                        ;;
                    dotmac_core_events)
                        cd dotmac_core_events && \
                        nohup python3 -m dotmac_core_events.api.rest > ../logs/${service}.log 2>&1 &
                        cd ..
                        ;;
                    *)
                        cd $service && \
                        nohup python3 -m ${service}.main > ../logs/${service}.log 2>&1 &
                        cd ..
                        ;;
                esac
                
                # Wait a bit for service to start
                sleep 2
                
                if wait_for_service "$name" localhost $port; then
                    :
                else
                    print_error "Failed to start $name. Check logs/${service}.log for details"
                fi
            fi
        done
        
        echo ""
        print_success "All services started!"
        echo ""
        print_info "Service URLs:"
        echo "  • API Gateway:    http://localhost:8000/docs"
        echo "  • Identity:       http://localhost:8001/docs"
        echo "  • Billing:        http://localhost:8002/docs"
        echo "  • Services:       http://localhost:8003/docs"
        echo "  • Networking:     http://localhost:8004/docs"
        echo "  • Analytics:      http://localhost:8005/docs"
        echo "  • Platform:       http://localhost:8006/docs"
        echo "  • Events:         http://localhost:8007/docs"
        echo "  • Core Ops:       http://localhost:8008/docs"
        echo ""
        ;;
        
    stop)
        print_info "Stopping DotMac Platform Services..."
        
        # Stop Python services
        print_info "Stopping Python services..."
        pkill -f "python3.*dotmac" 2>/dev/null || true
        
        # Stop infrastructure if requested
        if [[ "$2" == "--all" ]]; then
            print_info "Stopping infrastructure services..."
            docker-compose -f docker-compose.simple.yml down
        fi
        
        print_success "Services stopped"
        ;;
        
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
        
    status)
        echo "DotMac Platform Service Status"
        echo "==============================="
        echo ""
        
        # Check infrastructure
        echo "Infrastructure Services:"
        if check_port localhost 5432; then
            echo "  ✓ PostgreSQL    (5432)"
        else
            echo "  ✗ PostgreSQL    (5432)"
        fi
        
        if check_port localhost 6379; then
            echo "  ✓ Redis         (6379)"
        else
            echo "  ✗ Redis         (6379)"
        fi
        
        echo ""
        echo "Application Services:"
        
        services=(
            "8000:API Gateway"
            "8001:Identity"
            "8002:Billing"
            "8003:Services"
            "8004:Networking"
            "8005:Analytics"
            "8006:Platform"
            "8007:Events"
            "8008:Core Ops"
        )
        
        for service_info in "${services[@]}"; do
            IFS=':' read -r port name <<< "$service_info"
            
            if check_port localhost $port; then
                echo "  ✓ $name ($port)"
            else
                echo "  ✗ $name ($port)"
            fi
        done
        
        echo ""
        ;;
        
    logs)
        service=${2:-all}
        if [[ "$service" == "all" ]]; then
            tail -f logs/*.log
        else
            if [[ -f "logs/${service}.log" ]]; then
                tail -f "logs/${service}.log"
            else
                print_error "Log file not found: logs/${service}.log"
            fi
        fi
        ;;
        
    clean)
        print_info "Cleaning up..."
        rm -rf logs/*.log
        rm -rf __pycache__
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        print_success "Cleanup complete"
        ;;
        
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|clean}"
        echo ""
        echo "Commands:"
        echo "  start           Start all services"
        echo "  stop [--all]    Stop services (--all includes infrastructure)"
        echo "  restart         Restart all services"
        echo "  status          Show service status"
        echo "  logs [service]  Show service logs (default: all)"
        echo "  clean           Clean up logs and cache files"
        echo ""
        echo "Examples:"
        echo "  $0 start                  # Start all services"
        echo "  $0 stop                   # Stop application services"
        echo "  $0 stop --all            # Stop all including infrastructure"
        echo "  $0 logs dotmac_identity  # View identity service logs"
        echo "  $0 status                # Check service status"
        exit 1
        ;;
esac