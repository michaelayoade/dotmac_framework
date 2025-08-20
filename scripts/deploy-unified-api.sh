#!/bin/bash

# DotMac Platform - Deploy Unified API Service
# This script deploys the complete platform with all services accessible through a unified API

set -e

echo "🚀 DotMac Platform - Unified API Deployment"
echo "==========================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Function to stop existing services
stop_existing() {
    echo -e "${YELLOW}🛑 Stopping existing services...${NC}"
    docker-compose -f docker-compose.yml down 2>/dev/null || true
    docker-compose -f docker-compose.backend.yml down 2>/dev/null || true
    docker-compose -f docker-compose.enhanced.yml down 2>/dev/null || true
    docker-compose -f docker-compose.unified.yml down 2>/dev/null || true
    docker stop dotmac-backend 2>/dev/null || true
    docker rm dotmac-backend 2>/dev/null || true
    echo -e "${GREEN}✅ Existing services stopped${NC}"
}

# Function to build unified service
build_unified() {
    echo -e "${BLUE}🔨 Building unified API service...${NC}"
    docker-compose -f docker-compose.unified.yml build --no-cache unified-api
    echo -e "${GREEN}✅ Build complete${NC}"
}

# Function to start services
start_services() {
    echo -e "${BLUE}🚀 Starting unified platform services...${NC}"
    docker-compose -f docker-compose.unified.yml up -d
    echo -e "${GREEN}✅ Services started${NC}"
}

# Function to wait for services to be healthy
wait_for_health() {
    echo -e "${YELLOW}⏳ Waiting for services to be healthy...${NC}"
    
    # Wait for PostgreSQL
    echo -n "Waiting for PostgreSQL..."
    for i in {1..30}; do
        if docker exec dotmac-postgres pg_isready -U dotmac > /dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done
    
    # Wait for Redis
    echo -n "Waiting for Redis..."
    for i in {1..30}; do
        if docker exec dotmac-redis redis-cli ping > /dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done
    
    # Wait for Unified API
    echo -n "Waiting for Unified API..."
    for i in {1..60}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done
}

# Function to display service information
display_info() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✨ DotMac Platform Deployed Successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}📚 API Documentation:${NC}"
    echo "   • Interactive Docs: http://localhost:8000/docs"
    echo "   • ReDoc: http://localhost:8000/redoc"
    echo "   • OpenAPI Spec: http://localhost:8000/openapi.json"
    echo ""
    echo -e "${BLUE}🔧 Service Endpoints:${NC}"
    echo "   • Unified API: http://localhost:8000"
    echo "   • Identity: http://localhost:8000/identity"
    echo "   • Billing: http://localhost:8000/billing"
    echo "   • Services: http://localhost:8000/services"
    echo "   • Networking: http://localhost:8000/network"
    echo "   • Analytics: http://localhost:8000/analytics"
    echo "   • Platform: http://localhost:8000/platform"
    echo "   • Events: http://localhost:8000/events"
    echo "   • Core Ops: http://localhost:8000/ops"
    echo ""
    echo -e "${BLUE}💚 Health Check:${NC}"
    echo "   • Platform Health: http://localhost:8000/health"
    echo ""
    echo -e "${BLUE}🔌 Direct Service Ports:${NC}"
    echo "   • PostgreSQL: localhost:5432"
    echo "   • Redis: localhost:6379"
    echo ""
    echo -e "${YELLOW}📝 Quick Test Commands:${NC}"
    echo "   • Check health: curl http://localhost:8000/health"
    echo "   • List services: curl http://localhost:8000/services"
    echo "   • View logs: docker-compose -f docker-compose.unified.yml logs -f"
    echo ""
    echo -e "${GREEN}========================================${NC}"
}

# Function to run quick tests
run_tests() {
    echo ""
    echo -e "${BLUE}🧪 Running quick tests...${NC}"
    
    # Test health endpoint
    echo -n "Testing health endpoint..."
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        echo -e " ${GREEN}✓${NC}"
    else
        echo -e " ${RED}✗${NC}"
    fi
    
    # Test services list
    echo -n "Testing services list..."
    if curl -s http://localhost:8000/services | grep -q "Identity Service"; then
        echo -e " ${GREEN}✓${NC}"
    else
        echo -e " ${RED}✗${NC}"
    fi
    
    # Test OpenAPI spec
    echo -n "Testing OpenAPI spec..."
    if curl -s http://localhost:8000/openapi.json | grep -q "DotMac ISP Platform"; then
        echo -e " ${GREEN}✓${NC}"
    else
        echo -e " ${RED}✗${NC}"
    fi
}

# Main execution
main() {
    echo "This will deploy the complete DotMac platform with unified API access."
    echo "All existing DotMac services will be stopped and replaced."
    echo ""
    read -p "Do you want to continue? (y/N) " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled."
        exit 0
    fi
    
    # Execute deployment steps
    stop_existing
    build_unified
    start_services
    wait_for_health
    run_tests
    display_info
}

# Run main function
main