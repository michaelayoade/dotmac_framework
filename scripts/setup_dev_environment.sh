#!/bin/bash
# Development Environment Setup Script for DotMac Framework
# Sets up local development environment using existing infrastructure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Functions for colored output
print_status() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_header() { echo -e "${BLUE}$1${NC}"; }
print_step() { echo -e "${PURPLE}[STEP]${NC} $1"; }

# Usage function
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --full              Full setup with all components"
    echo "  --minimal           Minimal setup for basic development"
    echo "  --docker-only       Setup Docker environment only"
    echo "  --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                  # Interactive setup"
    echo "  $0 --minimal        # Quick minimal setup"
    echo "  $0 --full           # Complete development setup"
}

# Check system requirements
check_requirements() {
    print_step "Checking system requirements..."
    
    local missing_tools=()
    
    # Check required tools
    local required_tools=("git" "python3" "pip3" "docker" "docker-compose")
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_error "Please install the missing tools and run this script again"
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        print_error "Please start Docker and run this script again"
        exit 1
    fi
    
    # Check Python version
    local python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
    if [ "$(echo "$python_version" | tr -d '.')" -lt 38 ]; then
        print_warning "Python 3.8+ recommended, found Python $python_version"
    fi
    
    print_status "All requirements satisfied"
}

# Setup Python development environment
setup_python_environment() {
    print_step "Setting up Python development environment..."
    
    cd "$PROJECT_ROOT"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install development dependencies for ISP Framework
    if [ -f "isp-framework/requirements-dev.txt" ]; then
        print_status "Installing ISP Framework development dependencies..."
        pip install -r isp-framework/requirements-dev.txt
    elif [ -f "isp-framework/requirements.txt" ]; then
        print_status "Installing ISP Framework dependencies..."
        pip install -r isp-framework/requirements.txt
    fi
    
    # Install development dependencies for Management Platform
    if [ -f "management-platform/requirements-dev.txt" ]; then
        print_status "Installing Management Platform development dependencies..."
        pip install -r management-platform/requirements-dev.txt
    elif [ -f "management-platform/requirements.txt" ]; then
        print_status "Installing Management Platform dependencies..."
        pip install -r management-platform/requirements.txt
    fi
    
    # Install common development tools
    print_status "Installing common development tools..."
    pip install pytest black mypy flake8 pre-commit requests python-dotenv
    
    print_status "Python environment setup completed"
}

# Setup Docker development environment
setup_docker_environment() {
    print_step "Setting up Docker development environment..."
    
    cd "$PROJECT_ROOT"
    
    # Create development Docker Compose file if it doesn't exist
    if [ ! -f "docker-compose.dev.yml" ]; then
        print_status "Creating development Docker Compose configuration..."
        
        cat > docker-compose.dev.yml << 'EOF'
version: '3.8'

services:
  postgres-dev:
    image: postgres:15
    container_name: dotmac-postgres-dev
    environment:
      POSTGRES_DB: dotmac_dev
      POSTGRES_USER: dotmac_dev
      POSTGRES_PASSWORD: dev_password_123
    ports:
      - "5432:5432"
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dotmac_dev"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis-dev:
    image: redis:7-alpine
    container_name: dotmac-redis-dev
    ports:
      - "6379:6379"
    volumes:
      - redis_dev_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  mailhog:
    image: mailhog/mailhog:latest
    container_name: dotmac-mailhog-dev
    ports:
      - "1025:1025"  # SMTP server
      - "8025:8025"  # Web interface
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:8025"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_dev_data:
  redis_dev_data:
EOF
        
        print_status "Development Docker Compose file created"
    fi
    
    # Create development environment file
    if [ ! -f ".env.dev" ]; then
        print_status "Creating development environment configuration..."
        
        cat > .env.dev << 'EOF'
# DotMac Framework Development Environment Configuration

# Database Configuration
DATABASE_URL=postgresql://dotmac_dev:dev_password_123@localhost:5432/dotmac_dev
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=dotmac_dev
POSTGRES_USER=dotmac_dev
POSTGRES_PASSWORD=dev_password_123

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Application Configuration
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# Security Configuration (Development Only)
SECRET_KEY=dev-secret-key-change-in-production
JWT_SECRET_KEY=dev-jwt-secret-change-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Email Configuration (using MailHog)
EMAIL_HOST=localhost
EMAIL_PORT=1025
EMAIL_USER=
EMAIL_PASSWORD=
EMAIL_USE_TLS=false
EMAIL_FROM=noreply@dotmac.dev

# API Configuration
API_V1_STR=/api/v1
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000", "http://localhost:8001"]

# Development URLs
ISP_FRAMEWORK_URL=http://localhost:8001
MANAGEMENT_PLATFORM_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
EOF
        
        print_status "Development environment file created"
    fi
    
    # Start development services
    print_status "Starting development services..."
    docker-compose -f docker-compose.dev.yml up -d
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 10
    
    # Check service health
    local services=("postgres-dev" "redis-dev" "mailhog")
    for service in "${services[@]}"; do
        if docker-compose -f docker-compose.dev.yml ps "$service" | grep -q "Up"; then
            print_status "✓ $service is running"
        else
            print_warning "⚠ $service may not be running properly"
        fi
    done
    
    print_status "Docker development environment setup completed"
}

# Setup development databases
setup_development_databases() {
    print_step "Setting up development databases..."
    
    cd "$PROJECT_ROOT"
    
    # Wait for PostgreSQL to be ready
    print_status "Waiting for PostgreSQL to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker exec dotmac-postgres-dev pg_isready -U dotmac_dev &> /dev/null; then
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_error "PostgreSQL not ready after $max_attempts attempts"
            return 1
        fi
        
        sleep 2
        attempt=$((attempt + 1))
    done
    
    # Create additional databases
    local databases=("dotmac_isp" "mgmt_platform" "test_db")
    
    for db in "${databases[@]}"; do
        print_status "Creating database: $db"
        docker exec dotmac-postgres-dev createdb -U dotmac_dev "$db" 2>/dev/null || print_warning "Database $db may already exist"
    done
    
    print_status "Development databases setup completed"
}

# Setup development tools and scripts
setup_development_tools() {
    print_step "Setting up development tools..."
    
    cd "$PROJECT_ROOT"
    
    # Create development scripts directory
    mkdir -p dev-scripts
    
    # Create database reset script
    cat > dev-scripts/reset-db.sh << 'EOF'
#!/bin/bash
# Reset development database
echo "Resetting development database..."
docker exec dotmac-postgres-dev dropdb -U dotmac_dev --if-exists dotmac_dev
docker exec dotmac-postgres-dev createdb -U dotmac_dev dotmac_dev
docker exec dotmac-postgres-dev dropdb -U dotmac_dev --if-exists dotmac_isp
docker exec dotmac-postgres-dev createdb -U dotmac_dev dotmac_isp
docker exec dotmac-postgres-dev dropdb -U dotmac_dev --if-exists mgmt_platform
docker exec dotmac-postgres-dev createdb -U dotmac_dev mgmt_platform
echo "Database reset completed"
EOF
    
    # Create start development services script
    cat > dev-scripts/start-services.sh << 'EOF'
#!/bin/bash
# Start development services
echo "Starting development services..."
cd "$(dirname "$0")/.."
docker-compose -f docker-compose.dev.yml up -d
echo "Development services started"
echo "Services available at:"
echo "  PostgreSQL: localhost:5432"
echo "  Redis: localhost:6379"
echo "  MailHog: http://localhost:8025"
EOF
    
    # Create stop development services script
    cat > dev-scripts/stop-services.sh << 'EOF'
#!/bin/bash
# Stop development services
echo "Stopping development services..."
cd "$(dirname "$0")/.."
docker-compose -f docker-compose.dev.yml down
echo "Development services stopped"
EOF
    
    # Create test runner script
    cat > dev-scripts/run-tests.sh << 'EOF'
#!/bin/bash
# Run tests for DotMac Framework
echo "Running tests..."

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Run validation scripts
echo "Running validation tests..."
python3 scripts/validate_imports.py
python3 scripts/validate_environment.py

# Run unit tests if pytest is available
if command -v pytest &> /dev/null; then
    echo "Running pytest..."
    pytest -v
else
    echo "pytest not available, skipping unit tests"
fi

echo "Tests completed"
EOF
    
    # Make scripts executable
    chmod +x dev-scripts/*.sh
    
    # Create VS Code configuration if it doesn't exist
    if [ ! -d ".vscode" ]; then
        mkdir -p .vscode
        
        cat > .vscode/settings.json << 'EOF'
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        ".pytest_cache": true
    },
    "python.envFile": "${workspaceFolder}/.env.dev"
}
EOF
        
        cat > .vscode/launch.json << 'EOF'
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "ISP Framework",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/isp-framework/src/dotmac_isp/main.py",
            "console": "integratedTerminal",
            "envFile": "${workspaceFolder}/.env.dev"
        },
        {
            "name": "Management Platform",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/management-platform/app/main.py",
            "console": "integratedTerminal",
            "envFile": "${workspaceFolder}/.env.dev"
        }
    ]
}
EOF
        
        print_status "VS Code configuration created"
    fi
    
    print_status "Development tools setup completed"
}

# Generate development setup summary
generate_development_summary() {
    print_header "\n🎉 DEVELOPMENT ENVIRONMENT SETUP COMPLETED!"
    print_header "=" * 60
    
    print_status "Environment overview:"
    echo "  🐳 Docker services: PostgreSQL, Redis, MailHog"
    echo "  🐍 Python virtual environment with dev dependencies"
    echo "  🔧 Development tools and scripts"
    echo "  📝 VS Code configuration"
    
    print_status "\nServices available:"
    echo "  📊 PostgreSQL: localhost:5432"
    echo "  🔄 Redis: localhost:6379"  
    echo "  📧 MailHog: http://localhost:8025"
    
    print_status "\nDevelopment commands:"
    echo "  🚀 Start services: ./dev-scripts/start-services.sh"
    echo "  🛑 Stop services: ./dev-scripts/stop-services.sh"
    echo "  🔄 Reset database: ./dev-scripts/reset-db.sh"
    echo "  🧪 Run tests: ./dev-scripts/run-tests.sh"
    
    print_status "\nPython environment:"
    echo "  🐍 Virtual env: source venv/bin/activate"
    echo "  📦 Dependencies: pip install -r requirements-dev.txt"
    echo "  🧪 Tests: pytest"
    echo "  🎨 Format: black ."
    echo "  🔍 Lint: flake8 ."
    
    print_status "\nConfiguration files:"
    echo "  🐳 Docker: docker-compose.dev.yml"
    echo "  ⚙️  Environment: .env.dev"
    echo "  📝 VS Code: .vscode/settings.json"
    
    print_status "\nNext steps:"
    echo "  1. Activate Python environment: source venv/bin/activate"
    echo "  2. Start development services: ./dev-scripts/start-services.sh"
    echo "  3. Run tests to verify setup: ./dev-scripts/run-tests.sh"
    echo "  4. Start developing! 🚀"
}

# Main setup function
setup_development_environment() {
    local setup_type="$1"
    
    print_header "🚀 DotMac Framework Development Environment Setup"
    print_header "Setup type: $setup_type"
    print_header "=" * 60
    
    check_requirements
    
    case "$setup_type" in
        "minimal")
            setup_docker_environment
            setup_development_databases
            ;;
        "docker-only")
            setup_docker_environment
            ;;
        "full")
            setup_python_environment
            setup_docker_environment
            setup_development_databases
            setup_development_tools
            ;;
        *)
            # Interactive setup
            print_status "Choose setup type:"
            echo "  1) Minimal (Docker services only)"
            echo "  2) Full (Python + Docker + Tools)"
            echo "  3) Docker only"
            read -p "Enter choice (1-3): " choice
            
            case $choice in
                1) setup_type="minimal" ;;
                2) setup_type="full" ;;
                3) setup_type="docker-only" ;;
                *) setup_type="full" ;;
            esac
            
            setup_development_environment "$setup_type"
            return
            ;;
    esac
    
    generate_development_summary
    
    print_header "\n✅ Development environment setup completed successfully!"
}

# Parse command line arguments
SETUP_TYPE="interactive"

while [[ $# -gt 0 ]]; do
    case $1 in
        --full)
            SETUP_TYPE="full"
            shift
            ;;
        --minimal)
            SETUP_TYPE="minimal"
            shift
            ;;
        --docker-only)
            SETUP_TYPE="docker-only"
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Run setup
setup_development_environment "$SETUP_TYPE"