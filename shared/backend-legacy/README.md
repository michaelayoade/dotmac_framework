# DotMac Backend - Monorepo

This is the backend monorepo for the DotMac ISP Platform, containing all microservices in a unified Docker environment.

## 📦 Services

| Service | Port | Description |
|---------|------|-------------|
| API Gateway | 8000 | Central API gateway with routing and rate limiting |
| Identity | 8001 | User authentication and customer management |
| Billing | 8002 | Invoicing, payments, and subscriptions |
| Services | 8003 | Service provisioning and catalog |
| Networking | 8004 | Network device management and monitoring |
| Analytics | 8005 | Business intelligence and reporting |
| Platform | 8006 | Core platform utilities and RBAC |
| Events | 8007 | Event bus and messaging |
| Core Ops | 8008 | Workflow orchestration and job scheduling |

## 🚀 Quick Start

### Using Make (Recommended)

```bash
# Build and start all services
make build
make up

# Check service status
make status

# Test all endpoints
make test-endpoints

# View logs
make logs

# Stop services
make down
```

### Using Docker Compose Directly

```bash
# Start with monolithic backend (easier for development)
docker-compose -f docker-compose.simple.yml up -d

# Or start individual services
docker-compose -f docker-compose.yml up -d

# Check logs
docker-compose logs -f

# Stop everything
docker-compose down
```

## 📋 Available Commands

```bash
make help              # Show all available commands
make build            # Build Docker images
make up               # Start all services
make down             # Stop all services
make logs             # View logs
make status           # Check service status
make test-endpoints   # Test all service health endpoints
make swagger          # Generate Swagger documentation
make clean            # Clean up everything
make restart          # Restart all services
make db-shell         # Open PostgreSQL shell
make shell            # Open shell in backend container
```

## 🏗️ Architecture

```
backend/
├── dotmac_api_gateway/     # API Gateway (Port 8000)
├── dotmac_identity/        # Identity Service (Port 8001)
├── dotmac_billing/         # Billing Service (Port 8002)
├── dotmac_services/        # Services Provisioning (Port 8003)
├── dotmac_networking/      # Network Management (Port 8004)
├── dotmac_analytics/       # Analytics Service (Port 8005)
├── dotmac_platform/        # Platform Service (Port 8006)
├── dotmac_core_events/     # Event Bus (Port 8007)
├── dotmac_core_ops/        # Core Ops (Port 8008)
├── docker-compose.yml      # Full microservices setup
├── docker-compose.simple.yml # Monolithic setup
├── Dockerfile              # Individual service Dockerfile
├── Dockerfile.monolith     # Monolithic Dockerfile
└── Makefile               # Development commands
```

## 🔌 API Documentation

Once services are running, access Swagger documentation at:

- API Gateway: http://localhost:8000/docs
- Identity: http://localhost:8001/docs
- Billing: http://localhost:8002/docs
- Services: http://localhost:8003/docs
- Networking: http://localhost:8004/docs
- Analytics: http://localhost:8005/docs
- Platform: http://localhost:8006/docs
- Events: http://localhost:8007/docs
- Core Ops: http://localhost:8008/docs

## 🐛 Troubleshooting

### Services not starting?

1. Check Docker is running: `docker ps`
2. Check logs: `make logs`
3. Ensure ports are free: `netstat -tulpn | grep 800`
4. Reset everything: `make clean && make build && make up`

### Database connection issues?

```bash
# Reset database
make db-reset

# Check PostgreSQL logs
docker logs dotmac-postgres
```

### Individual service debugging

```bash
# Check specific service logs
docker logs dotmac-identity
docker logs dotmac-billing

# Restart specific service
docker-compose restart identity
```

## 🔧 Development

### Running locally without Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Start infrastructure only
docker-compose -f docker-compose.simple.yml up postgres redis

# Run service locally
cd dotmac_identity
python -m dotmac_identity.main
```

### Adding a new service

1. Create service folder in `backend/`
2. Add service to `docker-compose.yml`
3. Update `Dockerfile` or `Dockerfile.monolith`
4. Add health check endpoint
5. Update this README

## 📊 Monitoring

- Health checks: Each service exposes `/health` endpoint
- Metrics: Available at `/metrics` on each service
- Logs: Centralized in Docker logs

## 🔒 Security

- All services run in isolated containers
- Network segmentation via Docker networks
- Environment-based configuration
- JWT authentication between services

## 📝 License

Copyright (c) 2024 DotMac Platform