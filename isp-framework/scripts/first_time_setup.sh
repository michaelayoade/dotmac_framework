#!/bin/bash
# =============================================================================
# DotMac ISP Framework - First Time Setup Script
# =============================================================================
# This script will set up your DotMac ISP Framework for the first time

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if port is available
port_available() {
    ! nc -z localhost "$1" 2>/dev/null
}

# Main setup function
main() {
    echo "🚀 DotMac ISP Framework - First Time Setup"
    echo "=========================================="
    echo ""
    
    # Check prerequisites
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first:"
        echo "  - Linux: https://docs.docker.com/engine/install/"
        echo "  - macOS: https://docs.docker.com/desktop/mac/"
        echo "  - Windows: https://docs.docker.com/desktop/windows/"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
        print_error "Docker Compose is not installed. Please install Docker Compose."
        exit 1
    fi
    
    # Check Python
    if ! command_exists python3; then
        print_error "Python 3 is not installed. Please install Python 3.8+"
        exit 1
    fi
    
    # Check Make
    if ! command_exists make; then
        print_error "Make is not installed. Please install make:"
        echo "  - Ubuntu/Debian: sudo apt install build-essential"
        echo "  - macOS: xcode-select --install"
        exit 1
    fi
    
    print_success "All prerequisites are installed!"
    
    # Step 1: Environment Configuration
    echo ""
    print_status "Step 1: Setting up environment configuration..."
    
    if [ ! -f .env ]; then
        print_status "Creating .env file from development template..."
        cp .env.development .env
        print_success "Created .env file"
    else
        print_warning ".env file already exists, skipping..."
    fi
    
    # Step 2: Start Infrastructure Services
    echo ""
    print_status "Step 2: Starting infrastructure services..."
    
    # Check if ports are available
    if ! port_available 5432; then
        print_warning "Port 5432 is in use. Please stop any existing PostgreSQL service."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    if ! port_available 6379; then
        print_warning "Port 6379 is in use. Please stop any existing Redis service."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    print_status "Starting PostgreSQL and Redis..."
    docker-compose up -d postgres redis
    
    # Wait for services to be ready
    print_status "Waiting for services to start..."
    sleep 10
    
    # Check PostgreSQL
    for i in {1..30}; do
        if docker-compose exec -T postgres pg_isready -U dotmac_user >/dev/null 2>&1; then
            print_success "PostgreSQL is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "PostgreSQL failed to start after 30 seconds"
            exit 1
        fi
        sleep 1
    done
    
    # Check Redis
    if docker-compose exec -T redis redis-cli ping >/dev/null 2>&1; then
        print_success "Redis is ready"
    else
        print_error "Redis is not responding"
        exit 1
    fi
    
    # Step 3: Install Python Dependencies
    echo ""
    print_status "Step 3: Installing Python dependencies..."
    
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    print_status "Activating virtual environment and installing dependencies..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -e .
    
    # Step 4: Database Setup
    echo ""
    print_status "Step 4: Setting up database..."
    
    print_status "Running database migrations..."
    make setup-db
    
    print_success "Database setup complete"
    
    # Step 5: Create Admin User
    echo ""
    print_status "Step 5: Creating admin user..."
    
    echo "You can create an admin user now, or skip and do it later."
    read -p "Create admin user now? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        python3 scripts/create_admin.py
    else
        print_status "Skipped admin user creation. You can create one later with:"
        echo "  python3 scripts/create_admin.py"
    fi
    
    # Step 6: Start the Application
    echo ""
    print_status "Step 6: Starting the application..."
    
    echo "The application is ready to start!"
    echo ""
    echo "🎯 Quick Start Commands:"
    echo "  Start backend:    make run-dev"
    echo "  Start frontend:   cd frontend && pnpm install && pnpm dev"
    echo "  Create admin:     python3 scripts/create_admin.py"
    echo ""
    echo "🌐 URLs (after starting):"
    echo "  API:              http://localhost:8000"
    echo "  API Docs:         http://localhost:8000/docs"
    echo "  Admin Portal:     http://localhost:3000"
    echo "  Customer Portal:  http://localhost:3001"
    echo "  Reseller Portal:  http://localhost:3002"
    echo ""
    echo "📚 Next Steps:"
    echo "  1. Start the backend: make run-dev"
    echo "  2. In a new terminal, start the frontend"
    echo "  3. Open the admin portal and log in"
    echo "  4. Configure your ISP settings"
    echo ""
    
    read -p "Start the backend now? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        print_success "Starting DotMac ISP Framework..."
        echo ""
        make run-dev
    else
        print_success "Setup complete! Run 'make run-dev' when ready to start."
    fi
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ] || [ ! -d "src/dotmac_isp" ]; then
    print_error "Please run this script from the dotmac_isp_framework root directory"
    exit 1
fi

# Run main setup
main "$@"