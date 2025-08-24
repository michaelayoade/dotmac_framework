# DotMac Management Platform - Development Makefile
# This Makefile provides standardized commands for development, testing, and deployment

.PHONY: help install-dev clean format lint test test-fast test-integration test-e2e security build up down run-api run-worker db-migrate db-reset check pre-commit release docker-build docker-push cost-analysis

# Default target
.DEFAULT_GOAL := help

# Configuration
PYTHON := python3.11
POETRY := poetry
DOCKER_COMPOSE := docker-compose
PROJECT_NAME := dotmac-management-platform
REGISTRY := ghcr.io/dotmac
IMAGE_TAG := $(shell git rev-parse --short HEAD)
ENVIRONMENT := development

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Help target
help: ## Show this help message
	@echo "$(BLUE)DotMac Management Platform - Development Commands$(NC)"
	@echo "=================================================="
	@echo ""
	@echo "$(GREEN)Setup Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(install|clean|setup)" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Development Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(format|lint|test|run|up|down)" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Quality & Security:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(security|check|pre-commit)" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Build & Deploy:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(build|push|release|deploy)" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Database & Infrastructure:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(db-|cost-|infra)" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# Setup and Installation
install-dev: ## Install development dependencies and setup environment
	@echo "$(GREEN)Setting up development environment...$(NC)"
	@command -v $(POETRY) >/dev/null 2>&1 || { echo "$(RED)Poetry not found. Please install Poetry first.$(NC)"; exit 1; }
	$(POETRY) --version
	$(POETRY) install --with dev,security
	$(POETRY) run pre-commit install
	@echo "$(GREEN)Creating .env file from template...$(NC)"
	@if [ ! -f .env ]; then cp .env.example .env; echo "$(YELLOW)Please configure .env file with your settings$(NC)"; fi
	@echo "$(GREEN)Development environment setup complete!$(NC)"

clean: ## Clean build artifacts, caches, and temporary files
	@echo "$(GREEN)Cleaning build artifacts and caches...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -name ".coverage" -delete
	find . -name "coverage.xml" -delete
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/
	rm -rf .tox/
	$(DOCKER_COMPOSE) down --volumes --remove-orphans 2>/dev/null || true
	docker system prune -f 2>/dev/null || true
	@echo "$(GREEN)Cleanup complete!$(NC)"

# Code Quality
format: ## Format code with black and isort
	@echo "$(GREEN)Formatting code...$(NC)"
	$(POETRY) run black src/ tests/ scripts/ portals/
	$(POETRY) run isort src/ tests/ scripts/ portals/
	@echo "$(GREEN)Code formatting complete!$(NC)"

lint: ## Run all linting checks (flake8, mypy, bandit)
	@echo "$(GREEN)Running linting checks...$(NC)"
	@echo "$(BLUE)Running flake8...$(NC)"
	$(POETRY) run flake8 src/ tests/ scripts/
	@echo "$(BLUE)Running mypy type checking...$(NC)"
	$(POETRY) run mypy src/
	@echo "$(BLUE)Running bandit security linting...$(NC)"
	$(POETRY) run bandit -r src/ -f json -o bandit-report.json
	@echo "$(GREEN)Linting complete!$(NC)"

# AI-First Testing Strategy  
test-ai-first: ## Run AI-optimized test suite (property-based + behavior + contract)
	@echo "$(GREEN)🤖 Running AI-first test suite...$(NC)"
	@mkdir -p test-reports
	$(POETRY) run pytest tests/ -m "property_based or behavior or contract" \
		--cov=app --cov=src/mgmt \
		--cov-report=term-missing --cov-report=html --cov-report=xml \
		--html=test-reports/ai-suite-report.html --json-report --json-report-file=test-reports/ai-suite.json \
		-v --tb=short
	@echo "$(GREEN)✅ AI-first test suite complete! Reports in test-reports/$(NC)"

test-ai-suite: test-ai-first ## Alias for test-ai-first

test-property-based: ## Run property-based tests (AI generates test cases)  
	@echo "$(GREEN)🎲 Running property-based tests with Hypothesis...$(NC)"
	@echo "$(BLUE)Testing: tests/property/test_saas_property_tests.py$(NC)"
	@if command -v poetry >/dev/null 2>&1; then \
		$(POETRY) run python -m pytest tests/property/ -m "property_based" -v --tb=short \
			--hypothesis-show-statistics --hypothesis-verbosity=verbose; \
	else \
		python3 -m pytest tests/property/ -m "property_based" -v --tb=short; \
	fi
	@echo "$(GREEN)✅ Property-based tests complete!$(NC)"

test-behavior: ## Run business behavior tests (outcome focused)
	@echo "$(GREEN)👥 Running business behavior tests...$(NC)"
	@echo "$(BLUE)Testing: tests/behavior/test_saas_tenant_workflows.py$(NC)"
	@if command -v poetry >/dev/null 2>&1; then \
		$(POETRY) run python -m pytest tests/behavior/ -m "behavior" -v --tb=short; \
	else \
		python3 -m pytest tests/behavior/ -m "behavior" -v --tb=short; \
	fi
	@echo "$(GREEN)✅ Behavior tests complete!$(NC)"

test-contracts: ## Run API contract tests (schema validation)
	@echo "$(GREEN)📋 Running API contract tests...$(NC)"
	@echo "$(BLUE)Testing: tests/contracts/test_saas_api_contracts.py$(NC)"
	@if command -v poetry >/dev/null 2>&1; then \
		$(POETRY) run python -m pytest tests/contracts/ -m "contract" -v --tb=short; \
	else \
		python3 -m pytest tests/contracts/ -m "contract" -v --tb=short; \
	fi
	@echo "$(GREEN)✅ Contract tests complete!$(NC)"

test-contract: test-contracts ## Alias for test-contracts

test-smoke-critical: ## Run only revenue-critical smoke tests
	@echo "$(GREEN)Running revenue-critical smoke tests...$(NC)"
	$(POETRY) run pytest tests/ -m "smoke_critical or revenue_critical" -v --tb=short

test-revenue-critical: ## Run all revenue-critical tests (billing, licensing, commissions)
	@echo "$(GREEN)Running revenue-critical tests...$(NC)"
	$(POETRY) run pytest tests/ -m "tenant_billing or plugin_licensing or reseller_commissions or usage_tracking" \
		-v --tb=short --cov=app.services.billing_service --cov=src.mgmt.services.plugin_licensing

# Traditional Testing (Legacy - Optional)
test: ## Run comprehensive test suite with coverage
	@echo "$(GREEN)Running comprehensive test suite...$(NC)"
	@mkdir -p test-reports
	$(POETRY) run pytest tests/ \
		--cov=app --cov=src/mgmt \
		--cov-report=term-missing --cov-report=html --cov-report=xml --cov-report=json \
		--html=test-reports/full-report.html --json-report --json-report-file=test-reports/full-suite.json \
		--durations=10 -v
	@echo "$(GREEN)Full test suite complete! Coverage in htmlcov/ and reports in test-reports/$(NC)"

test-fast: ## Run fast tests only (unit + property-based)
	@echo "$(GREEN)Running fast tests...$(NC)"
	$(POETRY) run pytest tests/ -m "fast or unit" -v --tb=short

test-integration: ## Run integration tests
	@echo "$(GREEN)Running integration tests...$(NC)"
	$(POETRY) run pytest tests/ -m "integration" -v --tb=short

test-e2e: ## Run end-to-end tests
	@echo "$(GREEN)Running end-to-end tests...$(NC)"
	$(POETRY) run pytest tests/ -m "e2e" -v --tb=short

test-security: ## Run security-focused tests
	@echo "$(GREEN)Running security tests...$(NC)"
	$(POETRY) run pytest tests/ -m "security" -v --tb=short

test-saas-platform: ## Run SaaS platform-specific tests
	@echo "$(GREEN)Running SaaS platform tests...$(NC)"
	$(POETRY) run pytest tests/ -m "deployment_orchestration or multi_tenant_isolation or saas_monitoring" \
		-v --tb=short

# AI Safety Checks
ai-safety-check: ## Run AI safety checks for critical business logic
	@echo "$(GREEN)Running AI safety checks...$(NC)"
	@echo "$(BLUE)Checking revenue-critical code paths...$(NC)"
	$(POETRY) run pytest tests/ -m "revenue_critical" --tb=short -q
	@echo "$(BLUE)Validating multi-tenant isolation...$(NC)"
	$(POETRY) run pytest tests/ -m "tenant_isolation" --tb=short -q
	@echo "$(BLUE)Testing deployment orchestration safety...$(NC)"
	$(POETRY) run pytest tests/ -m "deployment_orchestration" --tb=short -q
	@echo "$(GREEN)AI safety checks complete!$(NC)"

# Security Scanning
security: ## Run comprehensive security scans
	@echo "$(GREEN)Running security scans...$(NC)"
	@echo "$(BLUE)Running Safety check for vulnerabilities...$(NC)"
	$(POETRY) run safety check --json --output safety-report.json || echo "$(YELLOW)Safety check completed with warnings$(NC)"
	@echo "$(BLUE)Running Bandit security linter...$(NC)"
	$(POETRY) run bandit -r src/ -f json -o bandit-report.json || echo "$(YELLOW)Bandit scan completed with warnings$(NC)"
	@echo "$(BLUE)Running custom security checks...$(NC)"
	$(POETRY) run python scripts/security_check.py
	@echo "$(GREEN)Security scanning complete! Check *-report.json files for details.$(NC)"

# Docker and Services
build: docker-build ## Build Docker images

docker-build: ## Build Docker images for all services
	@echo "$(GREEN)Building Docker images...$(NC)"
	$(DOCKER_COMPOSE) build --parallel
	@echo "$(GREEN)Docker images built successfully!$(NC)"

docker-push: ## Push Docker images to registry
	@echo "$(GREEN)Pushing Docker images to registry...$(NC)"
	docker tag $(PROJECT_NAME):latest $(REGISTRY)/$(PROJECT_NAME):$(IMAGE_TAG)
	docker tag $(PROJECT_NAME):latest $(REGISTRY)/$(PROJECT_NAME):latest
	docker push $(REGISTRY)/$(PROJECT_NAME):$(IMAGE_TAG)
	docker push $(REGISTRY)/$(PROJECT_NAME):latest
	@echo "$(GREEN)Images pushed to $(REGISTRY)/$(PROJECT_NAME):$(IMAGE_TAG)$(NC)"

up: ## Start development environment with Docker Compose
	@echo "$(GREEN)Starting development environment...$(NC)"
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)Services starting up...$(NC)"
	@echo "$(BLUE)API will be available at: http://localhost:8000$(NC)"
	@echo "$(BLUE)Master Admin Portal: http://localhost:3000$(NC)"
	@echo "$(BLUE)Tenant Admin Portal: http://localhost:3001$(NC)"
	@echo "$(BLUE)Reseller Portal: http://localhost:3002$(NC)"
	@echo "$(BLUE)SignOz Monitoring: http://localhost:3301$(NC)"
	@echo "$(BLUE)OpenBao: http://localhost:8200$(NC)"

down: ## Stop development environment
	@echo "$(GREEN)Stopping development environment...$(NC)"
	$(DOCKER_COMPOSE) down
	@echo "$(GREEN)Development environment stopped.$(NC)"

logs: ## Show logs from all services
	$(DOCKER_COMPOSE) logs -f

# Service Management
run-api: ## Start API server locally
	@echo "$(GREEN)Starting API server...$(NC)"
	$(POETRY) run uvicorn src.mgmt.main:app --reload --host 0.0.0.0 --port 8000

run-worker: ## Start Celery worker
	@echo "$(GREEN)Starting Celery worker...$(NC)"
	$(POETRY) run celery -A src.mgmt.shared.tasks worker --loglevel=info

run-beat: ## Start Celery beat scheduler
	@echo "$(GREEN)Starting Celery beat scheduler...$(NC)"
	$(POETRY) run celery -A src.mgmt.shared.tasks beat --loglevel=info

# Database Management
db-migrate: ## Run database migrations
	@echo "$(GREEN)Running database migrations...$(NC)"
	$(POETRY) run alembic upgrade head
	@echo "$(GREEN)Database migrations complete!$(NC)"

db-reset: ## Reset database for development (DESTRUCTIVE)
	@echo "$(RED)WARNING: This will destroy all data in the development database!$(NC)"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	$(DOCKER_COMPOSE) down postgres
	docker volume rm $$(docker volume ls -q | grep postgres) 2>/dev/null || true
	$(DOCKER_COMPOSE) up -d postgres
	@echo "$(YELLOW)Waiting for database to be ready...$(NC)"
	sleep 10
	$(MAKE) db-migrate
	@echo "$(GREEN)Database reset complete!$(NC)"

db-shell: ## Connect to database shell
	@echo "$(GREEN)Connecting to database...$(NC)"
	$(DOCKER_COMPOSE) exec postgres psql -U mgmt_user -d mgmt_platform

# Quality Gates
check: lint test security ## Run all quality checks (lint + test + security)
	@echo "$(GREEN)All quality checks passed!$(NC)"

pre-commit: ## Run pre-commit hooks manually
	@echo "$(GREEN)Running pre-commit hooks...$(NC)"
	$(POETRY) run pre-commit run --all-files

# Infrastructure and Cost Management
cost-analysis: ## Run infrastructure cost analysis
	@echo "$(GREEN)Running cost analysis...$(NC)"
	$(POETRY) run python scripts/cost_monitor.py --analyze
	@echo "$(GREEN)Cost analysis complete! Check cost-report.json$(NC)"

infra-validate: ## Validate infrastructure configurations
	@echo "$(GREEN)Validating infrastructure configurations...$(NC)"
	@echo "$(BLUE)Validating OpenTofu configurations...$(NC)"
	cd deployment/opentofu && tofu validate
	@echo "$(BLUE)Validating Docker configurations...$(NC)"
	$(DOCKER_COMPOSE) config
	@echo "$(GREEN)Infrastructure validation complete!$(NC)"

infra-plan: ## Show infrastructure deployment plan
	@echo "$(GREEN)Generating infrastructure plan...$(NC)"
	cd deployment/opentofu/environments/$(ENVIRONMENT) && tofu plan

infra-apply: ## Apply infrastructure changes
	@echo "$(RED)WARNING: This will modify cloud infrastructure!$(NC)"
	@read -p "Environment: $(ENVIRONMENT). Continue? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	cd deployment/opentofu/environments/$(ENVIRONMENT) && tofu apply

# Release Management
release-patch: ## Create a patch release
	@echo "$(GREEN)Creating patch release...$(NC)"
	$(POETRY) version patch
	@echo "$(GREEN)Version bumped to $$($(POETRY) version -s)$(NC)"

release-minor: ## Create a minor release
	@echo "$(GREEN)Creating minor release...$(NC)"
	$(POETRY) version minor
	@echo "$(GREEN)Version bumped to $$($(POETRY) version -s)$(NC)"

release-major: ## Create a major release
	@echo "$(GREEN)Creating major release...$(NC)"
	$(POETRY) version major
	@echo "$(GREEN)Version bumped to $$($(POETRY) version -s)$(NC)"

tag-release: ## Tag current version for release
	@VERSION=$$($(POETRY) version -s); \
	git tag -a "v$$VERSION" -m "Release v$$VERSION"; \
	echo "$(GREEN)Tagged release v$$VERSION$(NC)"

# Development Utilities
shell: ## Start Python shell with project context
	$(POETRY) run python -c "from src.mgmt.shared.config import get_settings; print('DotMac Management Platform Shell'); print(f'Environment: {get_settings().app.environment}')"
	$(POETRY) run python

jupyter: ## Start Jupyter lab for development
	$(POETRY) run jupyter lab --ip=0.0.0.0 --port=8888 --no-browser

docs-serve: ## Serve documentation locally
	@echo "$(GREEN)Starting documentation server...$(NC)"
	$(POETRY) run mkdocs serve

docs-build: ## Build documentation
	@echo "$(GREEN)Building documentation...$(NC)"
	$(POETRY) run mkdocs build

# Monitoring and Health Checks
health-check: ## Check health of all services
	@echo "$(GREEN)Checking service health...$(NC)"
	@echo "$(BLUE)API Health:$(NC)"
	@curl -s http://localhost:8000/health || echo "$(RED)API not responding$(NC)"
	@echo "$(BLUE)Database Health:$(NC)"
	@$(DOCKER_COMPOSE) exec -T postgres pg_isready -U mgmt_user || echo "$(RED)Database not ready$(NC)"
	@echo "$(BLUE)Redis Health:$(NC)"
	@$(DOCKER_COMPOSE) exec -T redis redis-cli ping || echo "$(RED)Redis not responding$(NC)"
	@echo "$(BLUE)OpenBao Health:$(NC)"
	@curl -s http://localhost:8200/v1/sys/health || echo "$(RED)OpenBao not responding$(NC)"

metrics: ## Show system metrics
	@echo "$(GREEN)System Metrics:$(NC)"
	@echo "$(BLUE)Docker Container Status:$(NC)"
	@$(DOCKER_COMPOSE) ps
	@echo "$(BLUE)System Resources:$(NC)"
	@docker stats --no-stream

# Backup and Restore
backup-dev: ## Backup development database
	@echo "$(GREEN)Creating development database backup...$(NC)"
	@mkdir -p backups
	@BACKUP_FILE="backups/dev-backup-$$(date +%Y%m%d-%H%M%S).sql"; \
	$(DOCKER_COMPOSE) exec -T postgres pg_dump -U mgmt_user mgmt_platform > "$$BACKUP_FILE"; \
	echo "$(GREEN)Backup created: $$BACKUP_FILE$(NC)"

restore-dev: ## Restore development database from backup
	@echo "$(GREEN)Available backups:$(NC)"
	@ls -la backups/*.sql 2>/dev/null || echo "$(YELLOW)No backups found$(NC)"
	@read -p "Enter backup file path: " backup_file; \
	if [ -f "$$backup_file" ]; then \
		echo "$(GREEN)Restoring from $$backup_file...$(NC)"; \
		$(MAKE) db-reset; \
		$(DOCKER_COMPOSE) exec -T postgres psql -U mgmt_user mgmt_platform < "$$backup_file"; \
		echo "$(GREEN)Restore complete!$(NC)"; \
	else \
		echo "$(RED)Backup file not found!$(NC)"; \
	fi

# Performance Testing
perf-test: ## Run performance tests
	@echo "$(GREEN)Running performance tests...$(NC)"
	$(POETRY) run locust --headless --users 10 --spawn-rate 2 -H http://localhost:8000 -t 60s

load-test: ## Run load tests
	@echo "$(GREEN)Running load tests...$(NC)"
	$(POETRY) run locust --headless --users 100 --spawn-rate 10 -H http://localhost:8000 -t 300s

# Development Status
status: ## Show development environment status
	@echo "$(GREEN)DotMac Management Platform Status$(NC)"
	@echo "=================================="
	@echo "$(BLUE)Git Status:$(NC)"
	@git status --porcelain || echo "$(RED)Not a git repository$(NC)"
	@echo "$(BLUE)Python Environment:$(NC)"
	@$(POETRY) env info
	@echo "$(BLUE)Service Status:$(NC)"
	@$(MAKE) health-check
	@echo "$(BLUE)Last Commit:$(NC)"
	@git log -1 --oneline 2>/dev/null || echo "$(RED)No git history$(NC)"

# Project Information
info: ## Show project information
	@echo "$(GREEN)DotMac Management Platform$(NC)"
	@echo "================================"
	@echo "$(BLUE)Version:$(NC) $$($(POETRY) version -s)"
	@echo "$(BLUE)Python:$(NC) $$($(POETRY) run python --version)"
	@echo "$(BLUE)Poetry:$(NC) $$($(POETRY) --version)"
	@echo "$(BLUE)Environment:$(NC) $(ENVIRONMENT)"
	@echo "$(BLUE)Project Root:$(NC) $$(pwd)"
	@echo "$(BLUE)Git Branch:$(NC) $$(git branch --show-current 2>/dev/null || echo 'unknown')"
	@echo "$(BLUE)Git Commit:$(NC) $$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"