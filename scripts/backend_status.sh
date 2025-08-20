#!/bin/bash

# DotMac Platform Backend Status Script
# Shows the status of all backend services

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to check if a service is running on a port
is_service_running() {
    local port=$1
    nc -z localhost "$port" 2>/dev/null
    return $?
}

# Function to get process info for a port
get_process_info() {
    local port=$1
    lsof -i:$port -P -n 2>/dev/null | grep LISTEN | awk '{print $1, $2}' | head -1
}

# Function to check service health
check_service_health() {
    local port=$1
    local health_endpoint="http://localhost:$port/health"
    
    if command -v curl &> /dev/null; then
        response=$(curl -s -o /dev/null -w "%{http_code}" "$health_endpoint" 2>/dev/null)
        if [ "$response" == "200" ]; then
            echo "Healthy"
        else
            echo "Unhealthy ($response)"
        fi
    else
        echo "Unknown"
    fi
}

# Main function
main() {
    clear
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                    DotMac Platform Service Status Dashboard                   ║"
    echo "║                         $(date +'%Y-%m-%d %H:%M:%S')                          ║"
    echo "╠══════════════════════════════════════════════════════════════════════════════╣"
    echo "║ Service                  │ Port  │ Status      │ Health      │ PID           ║"
    echo "╠══════════════════════════════════════════════════════════════════════════════╣"
    
    # Service definitions
    declare -a services=(
        "API Gateway:8000"
        "Identity Service:8001"
        "Billing Service:8002"
        "Services Platform:8003"
        "Networking Service:8004"
        "Analytics Service:8005"
        "Platform Service:8006"
        "Core Events:8007"
        "Core Operations:8008"
    )
    
    # Check each service
    for service_def in "${services[@]}"; do
        IFS=':' read -r name port <<< "$service_def"
        
        printf "║ %-24s │ %-5s │ " "$name" "$port"
        
        if is_service_running "$port"; then
            printf "${GREEN}%-11s${NC} │ " "Running"
            
            # Check health
            health=$(check_service_health "$port")
            if [ "$health" == "Healthy" ]; then
                printf "${GREEN}%-11s${NC} │ " "$health"
            elif [ "$health" == "Unknown" ]; then
                printf "${YELLOW}%-11s${NC} │ " "$health"
            else
                printf "${RED}%-11s${NC} │ " "$health"
            fi
            
            # Get PID
            process_info=$(get_process_info "$port")
            if [ -n "$process_info" ]; then
                printf "%-13s ║\n" "$process_info"
            else
                printf "%-13s ║\n" "N/A"
            fi
        else
            printf "${RED}%-11s${NC} │ ${RED}%-11s${NC} │ %-13s ║\n" "Not Running" "N/A" "N/A"
        fi
    done
    
    echo "╠══════════════════════════════════════════════════════════════════════════════╣"
    echo "║                               Infrastructure Services                         ║"
    echo "╠══════════════════════════════════════════════════════════════════════════════╣"
    
    # PostgreSQL
    printf "║ %-24s │ %-5s │ " "PostgreSQL" "5432"
    if pg_isready -h localhost -p 5432 &> /dev/null; then
        printf "${GREEN}%-11s${NC} │ ${GREEN}%-11s${NC} │ " "Running" "Healthy"
        process_info=$(get_process_info 5432)
        printf "%-13s ║\n" "${process_info:-N/A}"
    else
        printf "${RED}%-11s${NC} │ ${RED}%-11s${NC} │ %-13s ║\n" "Not Running" "N/A" "N/A"
    fi
    
    # Redis
    printf "║ %-24s │ %-5s │ " "Redis" "6379"
    if redis-cli ping &> /dev/null; then
        printf "${GREEN}%-11s${NC} │ ${GREEN}%-11s${NC} │ " "Running" "Healthy"
        process_info=$(get_process_info 6379)
        printf "%-13s ║\n" "${process_info:-N/A}"
    else
        printf "${RED}%-11s${NC} │ ${RED}%-11s${NC} │ %-13s ║\n" "Not Running" "N/A" "N/A"
    fi
    
    # FreeRADIUS
    printf "║ %-24s │ %-5s │ " "FreeRADIUS" "1812"
    if pgrep -x "radiusd" > /dev/null || pgrep -x "freeradius" > /dev/null; then
        printf "${GREEN}%-11s${NC} │ ${GREEN}%-11s${NC} │ " "Running" "Healthy"
        pid=$(pgrep -x "radiusd" || pgrep -x "freeradius")
        printf "%-13s ║\n" "radiusd $pid"
    else
        printf "${RED}%-11s${NC} │ ${RED}%-11s${NC} │ %-13s ║\n" "Not Running" "N/A" "N/A"
    fi
    
    echo "╠══════════════════════════════════════════════════════════════════════════════╣"
    echo "║                                Quick Actions                                  ║"
    echo "╠══════════════════════════════════════════════════════════════════════════════╣"
    echo "║ • Start all services:    ./scripts/start_backend.sh                          ║"
    echo "║ • Stop all services:     ./scripts/stop_backend.sh                           ║"
    echo "║ • View logs:             tail -f logs/<service-name>.log                     ║"
    echo "║ • API Documentation:     http://localhost:8000/docs                          ║"
    echo "║ • Health Dashboard:      http://localhost:8000/health                        ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Summary
    running_count=0
    total_count=0
    
    for service_def in "${services[@]}"; do
        IFS=':' read -r name port <<< "$service_def"
        total_count=$((total_count + 1))
        if is_service_running "$port"; then
            running_count=$((running_count + 1))
        fi
    done
    
    echo -e "${CYAN}Summary:${NC} $running_count/$total_count microservices running"
    
    # Check if databases are running
    db_status="OK"
    if ! pg_isready -h localhost -p 5432 &> /dev/null; then
        db_status="PostgreSQL not running"
    elif ! redis-cli ping &> /dev/null; then
        db_status="Redis not running"
    fi
    
    if [ "$db_status" == "OK" ]; then
        echo -e "${CYAN}Database Status:${NC} ${GREEN}All databases operational${NC}"
    else
        echo -e "${CYAN}Database Status:${NC} ${RED}$db_status${NC}"
    fi
    
    echo ""
}

# Auto-refresh if requested
if [ "$1" == "--watch" ] || [ "$1" == "-w" ]; then
    while true; do
        main
        sleep 5
    done
else
    main
fi