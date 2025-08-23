# DotMac Framework - Centralized Development Commands
# Provides consistent interface for all development tasks across the monorepo

.PHONY: help install install-dev clean test lint format type-check security build docs deps-check deps-update
.DEFAULT_GOAL := help

# Configuration
PYTHON := python3
PIP := pip
PACKAGES := dotmac_core_events dotmac_core_ops dotmac_identity dotmac_billing dotmac_services dotmac_networking dotmac_analytics dotmac_api_gateway dotmac_platform dotmac_devtools

# Add scripts to PATH
export PATH := $(CURDIR)/scripts/start:$(CURDIR)/scripts/stop:$(CURDIR)/scripts/deploy:$(CURDIR)/scripts/dev-tools:$(PATH)

# Colors for output
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m

define log_info
	@echo -e "$(GREEN)[INFO]$(NC) $(1)"
endef

define log_warn
	@echo -e "$(YELLOW)[WARN]$(NC) $(1)"
endef

define log_error
	@echo -e "$(RED)[ERROR]$(NC) $(1)"
endef

help: ## Show this help message
	@echo -e "$(CYAN)DotMac Framework - Development Commands$(NC)"
	@echo ""
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(CYAN)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Examples:"
	@echo "  make install-dev    # Set up development environment"
	@echo "  make test          # Run all tests"
	@echo "  make lint          # Run linting (with complexity checks)"
	@echo "  make security      # Run security scans"

# =============================================================================
# ENVIRONMENT SETUP
# =============================================================================

install: ## Install production dependencies
	$(call log_info,"Installing production dependencies...")
	$(PIP) install --require-hashes -r requirements.lock

install-dev: ## Install development dependencies and setup pre-commit
	$(call log_info,"Setting up development environment...")
	$(PIP) install pip-tools pre-commit
	./scripts/manage_dependencies.sh compile
	$(PIP) install --require-hashes -r requirements-dev.lock
	pre-commit install
	$(call log_info,"Development environment ready!")

clean: ## Clean up build artifacts and caches
	$(call log_info,"Cleaning up...")
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete -print
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.coverage" -delete
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/
	$(call log_info,"Cleanup complete!")

# =============================================================================
# TESTING
# =============================================================================

test: ## Run all tests with coverage
	$(call log_info,"Running tests with coverage...")
	@failed_packages=(); \
	for package in $(PACKAGES); do \
		if [ -d "$$package" ] && [ -f "$$package/pyproject.toml" ]; then \
			echo -e "$(CYAN)Testing $$package...$(NC)"; \
			cd "$$package" && \
			$(PYTHON) -m pytest \
				--cov="$$package" \
				--cov-report=term-missing \
				--cov-report=xml \
				--cov-fail-under=80 \
				--tb=short \
				-v || failed_packages+=("$$package"); \
			cd ..; \
		fi; \
	done; \
	if [ $${#failed_packages[@]} -ne 0 ]; then \
		$(call log_error,"Tests failed in: $${failed_packages[*]}"); \
		exit 1; \
	fi
	$(call log_info,"All tests passed!")

test-unit: ## Run only unit tests (fast)
	$(call log_info,"Running unit tests...")
	@for package in $(PACKAGES); do \
		if [ -d "$$package" ]; then \
			echo -e "$(CYAN)Unit testing $$package...$(NC)"; \
			cd "$$package" && $(PYTHON) -m pytest -m "unit" --tb=short -q && cd ..; \
		fi; \
	done

test-integration: ## Run integration tests
	$(call log_info,"Running integration tests...")
	@for package in $(PACKAGES); do \
		if [ -d "$$package" ]; then \
			echo -e "$(CYAN)Integration testing $$package...$(NC)"; \
			cd "$$package" && $(PYTHON) -m pytest -m "integration" --tb=short -v && cd ..; \
		fi; \
	done

test-package: ## Run tests for specific package (usage: make test-package PACKAGE=dotmac_identity)
	@if [ -z "$(PACKAGE)" ]; then \
		$(call log_error,"Please specify PACKAGE, e.g., make test-package PACKAGE=dotmac_identity"); \
		exit 1; \
	fi
	$(call log_info,"Testing $(PACKAGE)...")
	cd "$(PACKAGE)" && $(PYTHON) -m pytest --cov="$(PACKAGE)" --cov-report=term-missing -v

# =============================================================================
# DOCKER-BASED TESTING (Recommended)
# =============================================================================

test-docker: ## Run all tests using Docker (standardized environment)
	$(call log_info,"Running tests with Docker...")
	./scripts/test-docker.sh all

test-docker-unit: ## Run unit tests using Docker
	$(call log_info,"Running unit tests with Docker...")
	./scripts/test-docker.sh unit

test-docker-integration: ## Run integration tests using Docker  
	$(call log_info,"Running integration tests with Docker...")
	./scripts/test-docker.sh integration

test-docker-smoke: ## Run smoke tests using Docker
	$(call log_info,"Running smoke tests with Docker...")
	./scripts/test-docker.sh smoke

test-docker-clean: ## Clean Docker test environment
	$(call log_info,"Cleaning Docker test environment...")
	./scripts/test-docker.sh clean

# =============================================================================
# CODE QUALITY
# =============================================================================

lint: ## Run linting with complexity checks (FAILS on violations)
	$(call log_info,"Running linting with complexity enforcement...")
	ruff check . --output-format=github
	@echo ""
	$(call log_info,"Checking for complexity violations...")
	@violations=$$(ruff check . --select C901,PLR0913,PLR0915 --output-format=text 2>/dev/null || echo "violations found"); \
	if [ "$$violations" != "" ] && [ "$$violations" != "All checks passed!" ]; then \
		$(call log_error,"❌ Complexity violations found:"); \
		ruff check . --select C901,PLR0913,PLR0915 --output-format=text; \
		echo ""; \
		$(call log_error,"Please refactor complex functions before proceeding."); \
		exit 1; \
	else \
		$(call log_info,"✅ No complexity violations found."); \
	fi

lint-fix: ## Run linting with auto-fixes
	$(call log_info,"Running linting with auto-fixes...")
	ruff check . --fix --output-format=github
	$(call log_info,"Auto-fixes applied!")

format: ## Format code with Black and Ruff
	$(call log_info,"Formatting code...")
	black .
	ruff format .
	$(call log_info,"Code formatted!")

format-check: ## Check code formatting without making changes
	$(call log_info,"Checking code formatting...")
	black --check --diff .
	ruff format --check .

type-check: ## Run static type checking with MyPy
	$(call log_info,"Running type checking...")
	mypy . --show-error-codes --no-error-summary || true
	$(call log_warn,"Type checking complete (errors allowed during gradual adoption)")

# =============================================================================
# SECURITY
# =============================================================================

security: ## Run security scans
	$(call log_info,"Running security scans...")
	./scripts/manage_dependencies.sh check
	@echo ""
	$(call log_info,"Scanning code for security issues...")
	bandit -r . -f text -x "*/tests/*,*/migrations/*" || true
	@echo ""
	$(call log_info,"Security scan complete!")

security-strict: ## Run security scans with strict mode (fails on issues)
	$(call log_info,"Running strict security scans...")
	./scripts/manage_dependencies.sh check
	bandit -r . -f text -x "*/tests/*,*/migrations/*"
	$(call log_info,"All security checks passed!")

# =============================================================================
# DEPENDENCIES
# =============================================================================

deps-compile: ## Compile dependency lockfiles
	$(call log_info,"Compiling dependencies...")
	./scripts/manage_dependencies.sh compile

deps-update: ## Update dependencies to latest versions
	$(call log_info,"Updating dependencies...")
	./scripts/manage_dependencies.sh update
	$(call log_warn,"Please test thoroughly and commit the updated lockfiles")

deps-check: ## Check for dependency vulnerabilities
	$(call log_info,"Checking dependencies for vulnerabilities...")
	./scripts/manage_dependencies.sh check

deps-audit: ## Audit dependencies for licenses and compliance
	$(call log_info,"Auditing dependencies...")
	./scripts/manage_dependencies.sh audit

deps-tree: ## Show dependency tree
	./scripts/manage_dependencies.sh tree

# =============================================================================
# BUILD & PACKAGING
# =============================================================================

build: ## Build all packages
	$(call log_info,"Building all packages...")
	@for package in $(PACKAGES); do \
		if [ -d "$$package" ] && [ -f "$$package/pyproject.toml" ]; then \
			echo -e "$(CYAN)Building $$package...$(NC)"; \
			cd "$$package" && \
			$(PYTHON) -m build --wheel --no-isolation && \
			cd ..; \
		fi; \
	done
	$(call log_info,"All packages built successfully!")

build-package: ## Build specific package (usage: make build-package PACKAGE=dotmac_identity)
	@if [ -z "$(PACKAGE)" ]; then \
		$(call log_error,"Please specify PACKAGE, e.g., make build-package PACKAGE=dotmac_identity"); \
		exit 1; \
	fi
	$(call log_info,"Building $(PACKAGE)...")
	cd "$(PACKAGE)" && $(PYTHON) -m build --wheel --no-isolation

validate-packages: ## Validate package structure and metadata
	$(call log_info,"Validating package structure...")
	@for package in $(PACKAGES); do \
		if [ -d "$$package" ] && [ -f "$$package/pyproject.toml" ]; then \
			echo -e "$(CYAN)Validating $$package...$(NC)"; \
			cd "$$package" && \
			$(PYTHON) -m build --wheel --no-isolation && \
			$(PYTHON) -m twine check dist/*.whl && \
			cd ..; \
		fi; \
	done
	$(call log_info,"All packages validated!")

# =============================================================================
# DOCUMENTATION
# =============================================================================

docs: ## Build documentation
	$(call log_info,"Building documentation...")
	mkdocs build
	$(call log_info,"Documentation built in site/")

docs-serve: ## Serve documentation locally
	$(call log_info,"Serving documentation at http://localhost:8000")
	mkdocs serve

docs-deploy: ## Deploy documentation to GitHub Pages
	$(call log_info,"Deploying documentation...")
	mkdocs gh-deploy --force

# =============================================================================
# CI/CD HELPERS
# =============================================================================

ci-install: ## Install dependencies for CI environment
	$(call log_info,"Installing CI dependencies...")
	$(PIP) install pip-tools
	$(PIP) install --require-hashes -r requirements-dev.lock

ci-test: ## Run CI test suite
	$(call log_info,"Running CI test suite...")
	make lint
	make type-check
	make security-strict
	make test
	make validate-packages
	$(call log_info,"CI test suite completed successfully!")

ci-quick: ## Run quick CI checks (for fast feedback)
	$(call log_info,"Running quick CI checks...")
	make lint
	make test-unit
	$(call log_info,"Quick checks completed!")

# =============================================================================
# DEVELOPMENT HELPERS
# =============================================================================

check: ## Run all quality checks
	$(call log_info,"Running all quality checks...")
	make lint
	make type-check
	make test
	make security
	$(call log_info,"All checks completed!")

fix: ## Fix all auto-fixable issues
	$(call log_info,"Fixing auto-fixable issues...")
	make format
	make lint-fix
	$(call log_info,"Auto-fixes applied!")

reset: ## Reset development environment
	$(call log_info,"Resetting development environment...")
	make clean
	make install-dev
	$(call log_info,"Environment reset complete!")

complexity-report: ## Generate detailed complexity report
	$(call log_info,"Generating complexity report...")
	@echo "# DotMac Framework - Complexity Report" > complexity-report.md
	@echo "Generated on $$(date)" >> complexity-report.md
	@echo "" >> complexity-report.md
	@echo "## Ruff Complexity Violations" >> complexity-report.md
	@ruff check . --select C901,PLR0913,PLR0915 --output-format=text >> complexity-report.md 2>/dev/null || echo "No violations found" >> complexity-report.md
	@echo "" >> complexity-report.md
	@echo "## Complexity Metrics by Package" >> complexity-report.md
	@for package in $(PACKAGES); do \
		if [ -d "$$package" ]; then \
			echo "### $$package" >> complexity-report.md; \
			radon cc "$$package" --min=B --show-complexity 2>/dev/null >> complexity-report.md || echo "No complex functions" >> complexity-report.md; \
			echo "" >> complexity-report.md; \
		fi; \
	done
	$(call log_info,"Complexity report generated: complexity-report.md")

# =============================================================================
# DEPLOYMENT & AUTOMATION
# =============================================================================

docker-config: ## Generate Docker configurations for all services
	$(call log_info,"Generating Docker configurations...")
	$(PYTHON) scripts/generate_docker_configs.py --all

docker-build: docker-config ## Build all Docker images
	$(call log_info,"Building Docker images...")
	./scripts/docker/build-all.sh

docker-dev: ## Start development environment with Docker
	$(call log_info,"Starting development environment...")
	docker-compose -f docker-compose.development.yml up -d

docker-staging: ## Start staging environment with Docker
	$(call log_info,"Starting staging environment...")
	docker-compose -f docker-compose.staging.yml up -d

docker-prod: ## Start production environment with Docker
	$(call log_info,"Starting production environment...")
	docker-compose -f docker-compose.production.yml up -d

docker-stop: ## Stop all Docker environments
	$(call log_info,"Stopping Docker environments...")
	docker-compose -f docker-compose.development.yml down 2>/dev/null || true
	docker-compose -f docker-compose.staging.yml down 2>/dev/null || true
	docker-compose -f docker-compose.production.yml down 2>/dev/null || true

docker-clean: ## Clean Docker resources
	$(call log_info,"Cleaning Docker resources...")
	docker system prune -f
	docker volume prune -f

deploy-dev: ## Deploy to development environment
	$(call log_info,"Deploying to development...")
	$(PYTHON) scripts/automation/deploy.py development

deploy-staging: ## Deploy to staging environment
	$(call log_info,"Deploying to staging...")
	$(PYTHON) scripts/automation/deploy.py staging

deploy-prod: ## Deploy to production environment
	$(call log_info,"Deploying to production...")
	$(PYTHON) scripts/automation/deploy.py production

workflow: ## Run complete development workflow
	$(call log_info,"Running development workflow...")
	$(PYTHON) scripts/automation/development_workflow.py workflow

workflow-setup: ## Set up development environment using automation
	$(call log_info,"Setting up development environment...")
	$(PYTHON) scripts/automation/development_workflow.py setup

workflow-report: ## Generate project health report
	$(call log_info,"Generating project health report...")
	$(PYTHON) scripts/automation/development_workflow.py report

# =============================================================================
# PACKAGE-SPECIFIC HELPERS
# =============================================================================

run-api-gateway: ## Start API Gateway for development
	$(call log_info,"Starting API Gateway...")
	cd dotmac_api_gateway && $(PYTHON) -m uvicorn dotmac_api_gateway.runtime.app:app --reload --port 8000

run-customer-portal: ## Start Customer Portal for development
	cd templates/isp-customer-portal && $(PYTHON) -m uvicorn main:app --reload --port 8001

run-reseller-portal: ## Start Reseller Portal for development
	cd templates/isp-reseller-portal && $(PYTHON) -m uvicorn main:app --reload --port 8002

# =============================================================================
# SHORTCUTS
# =============================================================================

dev: ## Start development environment (wrapper for docker compose + profiles dev)
	$(call log_info,"Starting development environment...")
	@COMPOSE_PROFILES=dev ./scripts/start/backend.sh -d
	@./scripts/start/monitoring.sh -s signoz -d  
	@./scripts/start/frontend.sh
	
start-backend: ## Start backend services
	@./scripts/start/backend.sh

start-frontend: ## Start frontend applications  
	@./scripts/start/frontend.sh

start-monitoring: ## Start monitoring stack
	@./scripts/start/monitoring.sh

stop: ## Stop all services gracefully
	@./scripts/stop/all.sh

install-dev-alias: install-dev ## Alias for install-dev
qa: check ## Alias for check (Quality Assurance)
build-all: build ## Alias for build