#!/bin/bash

# Stop DotMac Backend Services

echo "🛑 Stopping DotMac Platform Services..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Function to stop a service
stop_service() {
    local name=$1
    local port=$2
    
    if [ -f logs/$name.pid ]; then
        pid=$(cat logs/$name.pid)
        if kill -0 $pid 2>/dev/null; then
            kill $pid
            echo -e "${GREEN}✓ Stopped $name (PID: $pid)${NC}"
        else
            echo -e "⚠️  $name was not running"
        fi
        rm -f logs/$name.pid
    fi
    
    # Also kill by port if still running
    pid=$(lsof -ti:$port 2>/dev/null)
    if [ -n "$pid" ]; then
        kill $pid 2>/dev/null
        echo -e "${GREEN}✓ Stopped process on port $port${NC}"
    fi
}

# Stop all services
stop_service "api-gateway" 8000
stop_service "identity" 8001
stop_service "billing" 8002
stop_service "services" 8003
stop_service "networking" 8004
stop_service "analytics" 8005
stop_service "platform" 8006

echo ""
echo "✅ All services stopped!"