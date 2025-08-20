# DotMac Backend Makefile

.PHONY: help build up down logs clean restart status test

help: ## Show this help message
	@echo "DotMac Backend - Docker Monorepo Commands"
	@echo ""
	@echo "Usage: make [command]"
	@echo ""
	@echo "Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

build: ## Build all Docker images
	docker-compose -f docker-compose.yml build

build-monolith: ## Build monolithic Docker image
	docker-compose -f docker-compose.simple.yml build

up: ## Start all services
	docker-compose -f docker-compose.yml up -d

up-monolith: ## Start monolithic backend
	docker-compose -f docker-compose.simple.yml up -d

down: ## Stop all services
	docker-compose -f docker-compose.yml down
	docker-compose -f docker-compose.simple.yml down

logs: ## View logs for all services
	docker-compose -f docker-compose.yml logs -f

logs-monolith: ## View logs for monolithic backend
	docker-compose -f docker-compose.simple.yml logs -f backend

clean: ## Clean up everything (containers, volumes, images)
	docker-compose -f docker-compose.yml down -v --rmi all
	docker-compose -f docker-compose.simple.yml down -v --rmi all

restart: ## Restart all services
	$(MAKE) down
	$(MAKE) up

status: ## Check status of all services
	@echo "Service Status:"
	@echo "==============="
	@docker-compose -f docker-compose.yml ps 2>/dev/null || docker-compose -f docker-compose.simple.yml ps

test-endpoints: ## Test all service endpoints
	@echo "Testing Service Endpoints..."
	@echo ""
	@echo "API Gateway (8000):"
	@curl -s http://localhost:8000/health 2>/dev/null || echo "  ✗ Not responding"
	@echo ""
	@echo "Identity (8001):"
	@curl -s http://localhost:8001/health 2>/dev/null || echo "  ✗ Not responding"
	@echo ""
	@echo "Billing (8002):"
	@curl -s http://localhost:8002/health 2>/dev/null || echo "  ✗ Not responding"
	@echo ""
	@echo "Services (8003):"
	@curl -s http://localhost:8003/health 2>/dev/null || echo "  ✗ Not responding"
	@echo ""
	@echo "Networking (8004):"
	@curl -s http://localhost:8004/health 2>/dev/null || echo "  ✗ Not responding"
	@echo ""
	@echo "Analytics (8005):"
	@curl -s http://localhost:8005/health 2>/dev/null || echo "  ✗ Not responding"
	@echo ""
	@echo "Platform (8006):"
	@curl -s http://localhost:8006/health 2>/dev/null || echo "  ✗ Not responding"
	@echo ""
	@echo "Events (8007):"
	@curl -s http://localhost:8007/health 2>/dev/null || echo "  ✗ Not responding"
	@echo ""
	@echo "Core Ops (8008):"
	@curl -s http://localhost:8008/health 2>/dev/null || echo "  ✗ Not responding"

swagger: ## Generate Swagger documentation
	@echo "Collecting Swagger/OpenAPI specs..."
	@mkdir -p docs/swagger
	@for port in 8000 8001 8002 8003 8004 8005 8006 8007 8008; do \
		echo "Fetching OpenAPI spec from port $$port..."; \
		curl -s http://localhost:$$port/openapi.json > docs/swagger/service-$$port.json 2>/dev/null || echo "  ✗ Service on port $$port not available"; \
	done
	@echo "Swagger specs saved to docs/swagger/"

# Development commands
dev-build: ## Build for development with live reload
	docker-compose -f docker-compose.yml build --no-cache

dev-up: ## Start in development mode
	docker-compose -f docker-compose.yml up

shell: ## Open shell in backend container
	docker exec -it dotmac-backend /bin/bash

# Database commands
db-shell: ## Open PostgreSQL shell
	docker exec -it dotmac-postgres psql -U dotmac -d dotmac

db-reset: ## Reset database
	docker-compose -f docker-compose.yml down -v
	docker-compose -f docker-compose.yml up -d postgres redis
	@echo "Waiting for database..."
	@sleep 5
	@echo "Database reset complete"