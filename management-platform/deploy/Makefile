# DotMac Management Platform Deployment Makefile

# Variables
DOCKER_REGISTRY ?= dotmac
IMAGE_NAME ?= management-platform
VERSION ?= $(shell git describe --tags --always --dirty)
NAMESPACE ?= dotmac-mgmt
KUBECTL ?= kubectl
DOCKER ?= docker

# Environment specific variables
DEV_COMPOSE_FILE = docker-compose.yml
PROD_COMPOSE_FILE = docker-compose.prod.yml

.PHONY: help build push deploy deploy-dev deploy-prod k8s-deploy clean test

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Docker targets
build: ## Build Docker image
	@echo "Building Docker image $(DOCKER_REGISTRY)/$(IMAGE_NAME):$(VERSION)"
	$(DOCKER) build \
		--target production \
		--tag $(DOCKER_REGISTRY)/$(IMAGE_NAME):$(VERSION) \
		--tag $(DOCKER_REGISTRY)/$(IMAGE_NAME):latest \
		--build-arg VERSION=$(VERSION) \
		.

build-dev: ## Build development Docker image
	@echo "Building development Docker image $(DOCKER_REGISTRY)/$(IMAGE_NAME):dev"
	$(DOCKER) build \
		--target development \
		--tag $(DOCKER_REGISTRY)/$(IMAGE_NAME):dev \
		.

push: ## Push Docker image to registry
	@echo "Pushing Docker image $(DOCKER_REGISTRY)/$(IMAGE_NAME):$(VERSION)"
	$(DOCKER) push $(DOCKER_REGISTRY)/$(IMAGE_NAME):$(VERSION)
	$(DOCKER) push $(DOCKER_REGISTRY)/$(IMAGE_NAME):latest

# Docker Compose targets
deploy-dev: ## Deploy using Docker Compose (development)
	@echo "Deploying development environment with Docker Compose"
	docker-compose -f $(DEV_COMPOSE_FILE) up --build -d
	@echo "Development environment deployed at http://localhost:8000"

deploy-dev-logs: ## Show logs from development deployment
	docker-compose -f $(DEV_COMPOSE_FILE) logs -f

deploy-prod: ## Deploy using Docker Compose (production)
	@echo "Deploying production environment with Docker Compose"
	@if [ ! -f .env.prod ]; then \
		echo "Error: .env.prod file is required for production deployment"; \
		exit 1; \
	fi
	docker-compose -f $(PROD_COMPOSE_FILE) --env-file .env.prod up -d
	@echo "Production environment deployed"

stop-dev: ## Stop development environment
	docker-compose -f $(DEV_COMPOSE_FILE) down

stop-prod: ## Stop production environment  
	docker-compose -f $(PROD_COMPOSE_FILE) --env-file .env.prod down

# Kubernetes targets
k8s-deploy: ## Deploy to Kubernetes
	@echo "Deploying to Kubernetes namespace: $(NAMESPACE)"
	@$(KUBECTL) create namespace $(NAMESPACE) --dry-run=client -o yaml | $(KUBECTL) apply -f -
	@$(KUBECTL) apply -f ../k8s/

k8s-deploy-secrets: ## Deploy secrets to Kubernetes (requires manual secret values)
	@echo "Deploying secrets to Kubernetes"
	@echo "WARNING: Update secret values in k8s/secrets.yaml before deploying to production"
	@$(KUBECTL) apply -f ../k8s/secrets.yaml

k8s-deploy-all: k8s-deploy-secrets k8s-deploy ## Deploy everything to Kubernetes

k8s-status: ## Show Kubernetes deployment status
	@echo "Deployment status in namespace: $(NAMESPACE)"
	@$(KUBECTL) get pods,services,ingress -n $(NAMESPACE)

k8s-logs: ## Show API logs from Kubernetes
	@$(KUBECTL) logs -f deployment/mgmt-api -n $(NAMESPACE)

k8s-shell: ## Get shell access to API pod
	@$(KUBECTL) exec -it deployment/mgmt-api -n $(NAMESPACE) -- /bin/bash

k8s-delete: ## Delete Kubernetes deployment
	@echo "Deleting Kubernetes deployment in namespace: $(NAMESPACE)"
	@$(KUBECTL) delete namespace $(NAMESPACE) --ignore-not-found=true

# Database targets
db-migrate: ## Run database migrations
	@echo "Running database migrations"
	@if [ -n "$$DATABASE_URL" ]; then \
		docker run --rm \
			-e DATABASE_URL=$$DATABASE_URL \
			$(DOCKER_REGISTRY)/$(IMAGE_NAME):latest \
			alembic upgrade head; \
	else \
		echo "Error: DATABASE_URL environment variable is required"; \
		exit 1; \
	fi

db-migrate-local: ## Run database migrations locally
	@echo "Running database migrations locally"
	alembic upgrade head

db-seed: ## Seed database with initial data
	@echo "Seeding database with initial data"
	@if [ -n "$$DATABASE_URL" ]; then \
		docker run --rm \
			-e DATABASE_URL=$$DATABASE_URL \
			$(DOCKER_REGISTRY)/$(IMAGE_NAME):latest \
			python -m app.scripts.seed_database; \
	else \
		echo "Error: DATABASE_URL environment variable is required"; \
		exit 1; \
	fi

# Testing targets
test: ## Run tests in Docker
	@echo "Running tests in Docker"
	$(DOCKER) run --rm \
		$(DOCKER_REGISTRY)/$(IMAGE_NAME):dev \
		pytest tests/ -v --cov=app

test-local: ## Run tests locally
	@echo "Running tests locally"
	pytest tests/ -v --cov=app

test-security: ## Run security tests
	@echo "Running security tests"
	$(DOCKER) run --rm \
		$(DOCKER_REGISTRY)/$(IMAGE_NAME):dev \
		pytest tests/test_security.py -v

lint: ## Run code linting
	@echo "Running code linting"
	$(DOCKER) run --rm \
		$(DOCKER_REGISTRY)/$(IMAGE_NAME):dev \
		sh -c "black --check app tests && flake8 app tests && mypy app"

# Monitoring targets
logs: ## Show application logs (development)
	docker-compose -f $(DEV_COMPOSE_FILE) logs -f mgmt-api

monitor: ## Open monitoring dashboards
	@echo "Opening monitoring dashboards..."
	@echo "SignOz UI: http://localhost:3301"
	@echo "Celery Flower: http://localhost:5555"
	@echo "API Health: http://localhost:8000/api/v1/health"

# Cleanup targets
clean: ## Clean up Docker images and containers
	@echo "Cleaning up Docker resources"
	docker-compose -f $(DEV_COMPOSE_FILE) down --volumes --remove-orphans
	docker-compose -f $(PROD_COMPOSE_FILE) down --volumes --remove-orphans || true
	$(DOCKER) image prune -f
	$(DOCKER) container prune -f

clean-all: ## Clean up all Docker resources (WARNING: removes all unused Docker resources)
	@echo "WARNING: This will remove all unused Docker resources system-wide"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(DOCKER) system prune -af --volumes; \
	fi

# Backup targets
backup-db: ## Backup database
	@echo "Creating database backup"
	@if [ -n "$$DATABASE_URL" ]; then \
		mkdir -p backups; \
		docker run --rm \
			-e PGPASSWORD=$$POSTGRES_PASSWORD \
			-v $(PWD)/backups:/backups \
			postgres:15-alpine \
			pg_dump -h $$POSTGRES_HOST -U $$POSTGRES_USER $$POSTGRES_DB > backups/backup_$$(date +%Y%m%d_%H%M%S).sql; \
	else \
		echo "Error: Database environment variables are required"; \
		exit 1; \
	fi

restore-db: ## Restore database from backup (set BACKUP_FILE environment variable)
	@echo "Restoring database from backup"
	@if [ -z "$$BACKUP_FILE" ]; then \
		echo "Error: BACKUP_FILE environment variable is required"; \
		exit 1; \
	fi
	@if [ -n "$$DATABASE_URL" ]; then \
		docker run --rm -i \
			-e PGPASSWORD=$$POSTGRES_PASSWORD \
			-v $(PWD)/backups:/backups \
			postgres:15-alpine \
			psql -h $$POSTGRES_HOST -U $$POSTGRES_USER $$POSTGRES_DB < $$BACKUP_FILE; \
	else \
		echo "Error: Database environment variables are required"; \
		exit 1; \
	fi

# SSL Certificate targets (for production)
generate-ssl: ## Generate self-signed SSL certificates (development only)
	@echo "Generating self-signed SSL certificates for development"
	@mkdir -p ssl
	@openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes \
		-subj "/C=US/ST=State/L=City/O=DotMac/OU=Dev/CN=localhost"

# Health check targets
health-check: ## Check application health
	@echo "Checking application health..."
	@curl -f http://localhost:8000/api/v1/health || echo "Health check failed"

health-check-k8s: ## Check Kubernetes application health
	@echo "Checking Kubernetes application health..."
	@$(KUBECTL) exec deployment/mgmt-api -n $(NAMESPACE) -- curl -f http://localhost:8000/api/v1/health

# Development utilities
dev-shell: ## Get shell access to development container
	docker-compose -f $(DEV_COMPOSE_FILE) exec mgmt-api /bin/bash

dev-db-shell: ## Get database shell access (development)
	docker-compose -f $(DEV_COMPOSE_FILE) exec postgres psql -U mgmt_user -d mgmt_platform

dev-redis-shell: ## Get Redis shell access (development)
	docker-compose -f $(DEV_COMPOSE_FILE) exec redis redis-cli

# Version and release targets
version: ## Show current version
	@echo "Current version: $(VERSION)"

tag: ## Tag current version
	@echo "Tagging version: $(VERSION)"
	@git tag -a v$(VERSION) -m "Release version $(VERSION)"
	@git push origin v$(VERSION)

release: build push tag ## Build, push, and tag a release

# Environment setup
setup-dev: ## Set up development environment
	@echo "Setting up development environment..."
	@cp .env.example .env
	@echo "Please edit .env file with your configuration"
	@echo "Then run: make deploy-dev"

setup-prod: ## Set up production environment
	@echo "Setting up production environment..."
	@cp .env.example .env.prod
	@echo "Please edit .env.prod file with your production configuration"
	@echo "Then run: make deploy-prod"