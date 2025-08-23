# DotMac ISP Framework Makefile
# Comprehensive build and development automation

.PHONY: help install install-dev clean lint format type-check test test-unit test-integration test-docker test-docker-unit test-docker-integration test-docker-smoke test-docker-clean test-package security security-strict run run-dev run-api-gateway build docker-build docker-run docker-stop docker-clean check coverage serve docs alembic-upgrade alembic-downgrade setup-db reset-db install-plugin list-plugins remove-plugin install-common-plugins

# Configuration
PYTHON := python3
PIP := pip3
PROJECT_NAME := dotmac-isp-framework
SRC_DIR := src/dotmac_isp
TEST_DIR := tests
PACKAGE ?= dotmac_isp

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)DotMac ISP Framework - Available Commands$(NC)"
	@echo "=========================================="
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# =============================================================================
# AI-FIRST DEVELOPMENT WORKFLOW
# =============================================================================

ai-safety-check: ## Run AI code safety checks (primary quality gate)
	@echo "$(BLUE)Running AI safety checks...$(NC)"
	@echo "$(YELLOW)Detecting AI-generated code patterns...$(NC)"
	$(PYTHON) scripts/ai_code_detector.py --flag-risky --output=ai-safety-report.json
	@echo "$(YELLOW)Verifying business logic integrity...$(NC)"
	$(PYTHON) scripts/verify_business_rules.py --strict
	$(PYTHON) scripts/check_revenue_logic.py --verify-unchanged
	@echo "$(YELLOW)Scanning for AI security anti-patterns...$(NC)"
	bandit -r $(SRC_DIR) -f json -o bandit-ai.json || true
	@echo "$(GREEN)AI safety checks completed!$(NC)"

ai-generate-tests: ## Generate property-based and contract tests using AI
	@echo "$(BLUE)Generating AI-powered tests...$(NC)"
	$(PYTHON) scripts/ai_test_generator.py --type=property_based --count=1000 --smart-coverage
	$(PYTHON) scripts/ai_test_generator.py --type=contract --all-endpoints
	$(PYTHON) scripts/ai_test_generator.py --type=behavior --business-workflows
	@echo "$(GREEN)AI test generation completed!$(NC)"

test-ai-first: ## Run AI-optimized test suite (fast feedback)
	@echo "$(BLUE)Running AI-first test suite...$(NC)"
	pytest -m "property_based or behavior or contract or smoke_critical" \
		--maxfail=5 --tb=short --durations=10 -q
	@echo "$(GREEN)AI-first testing completed!$(NC)"

test-property-based: ## Run property-based tests (AI-generated test cases)
	@echo "$(BLUE)Running property-based tests...$(NC)"
	pytest -m "property_based" --hypothesis-show-statistics --tb=short -v

test-contracts: ## Run API contract validation tests
	@echo "$(BLUE)Running contract tests...$(NC)"  
	pytest -m "contract" --tb=short -v

test-behaviors: ## Run business behavior and outcome tests
	@echo "$(BLUE)Running behavior tests...$(NC)"
	pytest -m "behavior" --tb=short -v

test-smoke-critical: ## Run only revenue-critical smoke tests
	@echo "$(BLUE)Running critical path smoke tests...$(NC)"
	pytest -m "smoke_critical or revenue_critical" --maxfail=1 --tb=line -q

test-ai-suite: ## Run complete AI test suite with reporting
	@echo "$(BLUE)Running complete AI test suite...$(NC)"
	pytest tests/ai_framework/ tests/property_based/ tests/contract_tests/ tests/behavior_tests/ \
		--cov=$(SRC_DIR) --cov-config=.coveragerc-ai \
		--cov-report=html:htmlcov-ai --cov-report=xml:coverage-ai.xml \
		--junit-xml=test-results-ai.xml --tb=short

ai-monitor-deployment: ## Monitor deployment with AI performance baselines
	@echo "$(BLUE)Setting up AI deployment monitoring...$(NC)"
	$(PYTHON) scripts/ai_deployment_monitor.py --establish-baseline --environment=$(ENV)

# Legacy commands (optional, non-blocking)
lint-optional: ## Optional linting for human reference (non-blocking)
	@echo "$(YELLOW)Running optional legacy linting...$(NC)"
	black --check $(SRC_DIR) $(TEST_DIR) || echo "$(YELLOW)Linting issues found (informational only)$(NC)"
	isort --check-only $(SRC_DIR) $(TEST_DIR) || echo "$(YELLOW)Import issues found (informational only)$(NC)"
	flake8 $(SRC_DIR) $(TEST_DIR) || echo "$(YELLOW)Style issues found (informational only)$(NC)"

type-check-optional: ## Optional type checking for human reference (non-blocking)
	@echo "$(YELLOW)Running optional type checking...$(NC)"
	mypy $(SRC_DIR) || echo "$(YELLOW)Type issues found (informational only)$(NC)"

install-ai-tools: ## Install AI-first development tools
	@echo "$(BLUE)Installing AI development tools...$(NC)"
	$(PIP) install hypothesis schemathesis pytest-benchmark pytest-xdist
	$(PIP) install bandit semgrep safety pip-audit
	$(PIP) install structlog jsonschema requests

install-ai-testing-tools: ## Install AI testing framework dependencies
	@echo "$(BLUE)Installing AI testing tools...$(NC)"
	$(PIP) install -r requirements-ai.txt

# =============================================================================
# DOCKERIZED TEST ENVIRONMENT (RECOMMENDED)
# =============================================================================

test-env-up: ## Start dockerized test environment with all dependencies
	@echo "$(BLUE)Starting dockerized test environment...$(NC)"
	docker-compose -f docker-compose.test.yml up -d postgres-test redis-test
	@echo "$(YELLOW)Waiting for databases to be ready...$(NC)"
	sleep 15
	@echo "$(GREEN)Test environment ready!$(NC)"
	@echo "$(YELLOW)PostgreSQL: localhost:5433 (test_user/test_password/dotmac_test)$(NC)"
	@echo "$(YELLOW)Redis: localhost:6380$(NC)"

test-env-full: ## Start full test environment with mocks and data generation
	@echo "$(BLUE)Starting full test environment...$(NC)"
	docker-compose -f docker-compose.test.yml up -d
	@echo "$(YELLOW)Waiting for all services to be ready...$(NC)"
	sleep 30
	@echo "$(GREEN)Full test environment ready!$(NC)"
	@echo "$(YELLOW)Services available:$(NC)"
	@echo "  - PostgreSQL: localhost:5433"
	@echo "  - Redis: localhost:6380"
	@echo "  - Mock Payment: localhost:8080"
	@echo "  - Mock SNMP: localhost:8161"
	@echo "  - Metrics Collector: localhost:9090"

test-env-logs: ## View test environment logs
	docker-compose -f docker-compose.test.yml logs -f

test-env-status: ## Check test environment status
	@echo "$(BLUE)Test Environment Status:$(NC)"
	docker-compose -f docker-compose.test.yml ps

test-env-down: ## Stop dockerized test environment
	@echo "$(BLUE)Stopping test environment...$(NC)"
	docker-compose -f docker-compose.test.yml down
	@echo "$(GREEN)Test environment stopped$(NC)"

test-env-clean: ## Clean test environment (removes volumes)
	@echo "$(BLUE)Cleaning test environment...$(NC)"
	docker-compose -f docker-compose.test.yml down -v
	docker-compose -f docker-compose.test.yml rm -f
	@echo "$(GREEN)Test environment cleaned$(NC)"

test-generate-data: ## Generate realistic ISP test data
	@echo "$(BLUE)Generating test data...$(NC)"
	docker-compose -f docker-compose.test.yml run --rm test-data-generator
	@echo "$(GREEN)Test data generated and stored in Redis$(NC)"

test-env-integration: ## Run integration tests in dockerized environment
	@echo "$(BLUE)Running integration tests in Docker environment...$(NC)"
	docker-compose -f docker-compose.test.yml up -d postgres-test redis-test mock-payment mock-snmp metrics-collector
	sleep 20
	POSTGRES_HOST=localhost POSTGRES_PORT=5433 REDIS_PORT=6380 \
	PAYMENT_PROCESSOR_URL=http://localhost:8080 SNMP_GATEWAY_URL=http://localhost:8161 \
	pytest tests/integration/ tests/contract_tests/ tests/behavior_tests/ \
		-m "integration or contract or behavior" \
		--tb=short -v \
		--junit-xml=test-results/docker-integration.xml \
		--html=test-results/docker-integration.html
	@echo "$(GREEN)Docker integration tests completed$(NC)"

test-env-contracts: ## Run contract tests against mock services
	@echo "$(BLUE)Running contract tests against mock services...$(NC)"
	docker-compose -f docker-compose.test.yml up -d mock-payment mock-snmp
	sleep 10
	PAYMENT_PROCESSOR_URL=http://localhost:8080 SNMP_GATEWAY_URL=http://localhost:8161 \
	pytest tests/contract_tests/ -m "contract" -v --tb=short

# =============================================================================
# MULTI-TIER DATABASE TESTING STRATEGY
# =============================================================================

test-database-tier1: ## Run Tier 1 database tests (SQLite, fast)
	@echo "$(BLUE)Running Tier 1 database tests (SQLite)...$(NC)"
	./scripts/test-database-setup.sh tier1
	@echo "$(GREEN)Tier 1 tests completed$(NC)"

test-database-tier3: ## Run Tier 3 database tests (PostgreSQL, production-like)
	@echo "$(BLUE)Running Tier 3 database tests (PostgreSQL)...$(NC)"
	./scripts/test-database-setup.sh tier3
	@echo "$(GREEN)Tier 3 tests completed$(NC)"

test-database-tier4: ## Run Tier 4 database tests (Docker integration)
	@echo "$(BLUE)Running Tier 4 database tests (Docker)...$(NC)"
	./scripts/test-database-setup.sh tier4
	@echo "$(GREEN)Tier 4 tests completed$(NC)"

test-database-all: ## Run all database test tiers (comprehensive)
	@echo "$(BLUE)Running comprehensive multi-tier database tests...$(NC)"
	./scripts/test-database-setup.sh all
	@echo "$(GREEN)All database test tiers completed$(NC)"

test-database-start: ## Start Docker database test environment
	@echo "$(BLUE)Starting database test environment...$(NC)"
	./scripts/test-database-setup.sh docker-start
	@echo "$(GREEN)Database test environment started$(NC)"

test-database-cleanup: ## Clean up database test environment
	@echo "$(BLUE)Cleaning up database test environment...$(NC)"
	./scripts/test-database-setup.sh cleanup
	@echo "$(GREEN)Database test environment cleaned$(NC)"

test-database-factories: ## Show test data factories information
	@echo "$(BLUE)Test Data Factories Information:$(NC)"
	./scripts/test-database-setup.sh factories

test-env-performance: ## Run performance tests in controlled environment
	@echo "$(BLUE)Running performance baseline tests...$(NC)"
	docker-compose -f docker-compose.test.yml up -d postgres-test redis-test metrics-collector
	sleep 15
	DATABASE_URL=postgresql://test_user:test_password@localhost:5433/dotmac_test \
	REDIS_URL=redis://localhost:6380 \
	METRICS_URL=http://localhost:9090 \
	pytest tests/performance/ --benchmark-only --benchmark-json=test-results/docker-benchmarks.json
	@echo "$(GREEN)Performance tests completed$(NC)"

# =============================================================================
# INSTALLATION AND SETUP
# =============================================================================

install: ## Install production dependencies
	@echo "$(BLUE)Installing production dependencies...$(NC)"
	$(PIP) install -r requirements.txt

install-dev: ## Install development dependencies and setup development environment
	@echo "$(BLUE)Setting up development environment...$(NC)"
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -r requirements-test.txt
	@echo "$(GREEN)Development environment ready!$(NC)"

clean: ## Clean up build artifacts, cache, and temporary files
	@echo "$(BLUE)Cleaning up project...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "coverage.xml" -delete 2>/dev/null || true
	find . -type f -name "coverage.json" -delete 2>/dev/null || true
	find . -type d -name "test-reports" -exec rm -rf {} + 2>/dev/null || true
	rm -f dotmac_isp.db test.db security-report.json safety-report.json
	@echo "$(GREEN)Cleanup complete!$(NC)"

# =============================================================================
# CODE QUALITY AND LINTING
# =============================================================================

format: ## Format code using black and isort
	@echo "$(BLUE)Formatting code...$(NC)"
	$(PYTHON) -m black $(SRC_DIR) $(TEST_DIR) --line-length 88
	$(PYTHON) -m isort $(SRC_DIR) $(TEST_DIR) --profile black

lint: ## Run linting (flake8) with complexity enforcement (FAILS on violations)
	@echo "$(BLUE)Running linting with complexity checks...$(NC)"
	$(PYTHON) -m flake8 $(SRC_DIR) --max-complexity=10 --max-line-length=88 \
		--extend-ignore=E203,E501,W503 \
		--per-file-ignores="__init__.py:F401" \
		--statistics --count
	@echo "$(GREEN)Linting passed!$(NC)"

lint-fix: ## Auto-fix linting issues where possible
	@echo "$(BLUE)Auto-fixing linting issues...$(NC)"
	$(PYTHON) -m autopep8 --in-place --recursive $(SRC_DIR) $(TEST_DIR) --max-line-length=88
	$(PYTHON) -m isort $(SRC_DIR) $(TEST_DIR) --profile black
	@echo "$(GREEN)Auto-fixes applied!$(NC)"

type-check: ## Run type checking with mypy
	@echo "$(BLUE)Running type checking...$(NC)"
	$(PYTHON) -m mypy $(SRC_DIR) --config-file pyproject.toml
	@echo "$(GREEN)Type checking passed!$(NC)"

# =============================================================================
# TESTING
# =============================================================================

test: ## Run all tests with coverage (80% minimum required)
	@echo "$(BLUE)Running all tests with coverage...$(NC)"
	$(PYTHON) -m pytest -v --cov=$(SRC_DIR) --cov-report=term-missing \
		--cov-report=html:htmlcov --cov-report=xml:coverage.xml \
		--cov-fail-under=80 --timeout=300

test-unit: ## Run unit tests only (fast)
	@echo "$(BLUE)Running unit tests...$(NC)"
	$(PYTHON) -m pytest $(TEST_DIR)/unit -v -m unit --timeout=60

test-integration: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	$(PYTHON) -m pytest $(TEST_DIR)/integration -v -m integration --timeout=300

test-package: ## Run tests for specific package (usage: make test-package PACKAGE=dotmac_identity)
	@echo "$(BLUE)Running tests for package: $(PACKAGE)$(NC)"
	$(PYTHON) -m pytest -v -k $(PACKAGE) --timeout=300

coverage: ## Generate coverage report
	@echo "$(BLUE)Generating coverage report...$(NC)"
	$(PYTHON) -m pytest --cov=$(SRC_DIR) --cov-report=html:htmlcov --cov-report=term-missing
	@echo "$(GREEN)Coverage report generated in htmlcov/$(NC)"

# =============================================================================
# DOCKER TESTING (RECOMMENDED - Standardized Environment)
# =============================================================================

test-docker: ## Run all tests in Docker (standardized environment)
	@echo "$(BLUE)Running tests in Docker environment...$(NC)"
	docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
	docker-compose -f docker-compose.test.yml down

test-docker-unit: ## Run unit tests in Docker (fast)
	@echo "$(BLUE)Running unit tests in Docker...$(NC)"
	docker-compose -f docker-compose.test.yml run --rm test_runner \
		pytest tests/unit -v -m unit --timeout=60

test-docker-integration: ## Run integration tests in Docker
	@echo "$(BLUE)Running integration tests in Docker...$(NC)"
	docker-compose -f docker-compose.test.yml run --rm test_runner \
		pytest tests/integration -v -m integration --timeout=300

test-docker-smoke: ## Run smoke tests in Docker
	@echo "$(BLUE)Running smoke tests in Docker...$(NC)"
	docker-compose -f docker-compose.test.yml run --rm test_runner \
		pytest -v -m smoke --timeout=60

test-docker-clean: ## Clean Docker test environment
	@echo "$(BLUE)Cleaning Docker test environment...$(NC)"
	docker-compose -f docker-compose.test.yml down --volumes --remove-orphans
	docker system prune -f

# =============================================================================
# SECURITY
# =============================================================================

security: ## Run security scans
	@echo "$(BLUE)Running security scans...$(NC)"
	$(PYTHON) -m bandit -r $(SRC_DIR) -f json -o security-report.json || true
	$(PYTHON) -m safety check --json --output safety-report.json || true
	@echo "$(GREEN)Security scan complete! Check security-report.json and safety-report.json$(NC)"

security-strict: ## Run security scans (fails on issues)
	@echo "$(BLUE)Running strict security scans...$(NC)"
	$(PYTHON) -m bandit -r $(SRC_DIR) -ll
	$(PYTHON) -m safety check
	@echo "$(GREEN)Security scan passed!$(NC)"

# =============================================================================
# DEVELOPMENT SERVERS
# =============================================================================

run: ## Run the application in production mode
	@echo "$(BLUE)Starting DotMac ISP Framework...$(NC)"
	$(PYTHON) -m uvicorn dotmac_isp.app:app --host 0.0.0.0 --port 8000

run-dev: ## Run the application in development mode with auto-reload
	@echo "$(BLUE)Starting DotMac ISP Framework in development mode...$(NC)"
	$(PYTHON) -m uvicorn dotmac_isp.app:app --host 0.0.0.0 --port 8000 --reload

run-api-gateway: ## Start API Gateway for development
	@echo "$(BLUE)Starting API Gateway...$(NC)"
	$(PYTHON) -m uvicorn dotmac_isp.app:app --host 0.0.0.0 --port 8000 --reload

serve: ## Serve the application using the main entry point
	@echo "$(BLUE)Starting application via main.py...$(NC)"
	cd src && $(PYTHON) -m dotmac_isp.main

# =============================================================================
# BUILD AND DOCKER
# =============================================================================

build: ## Build the application
	@echo "$(BLUE)Building application...$(NC)"
	$(PYTHON) -m pip install build
	$(PYTHON) -m build
	@echo "$(GREEN)Build complete!$(NC)"

docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	docker build -t $(PROJECT_NAME):latest .
	@echo "$(GREEN)Docker image built!$(NC)"

docker-run: ## Run application in Docker
	@echo "$(BLUE)Starting Docker containers...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)Application running at http://localhost:8000$(NC)"

docker-stop: ## Stop Docker containers
	@echo "$(BLUE)Stopping Docker containers...$(NC)"
	docker-compose down

docker-clean: ## Clean Docker containers and volumes
	@echo "$(BLUE)Cleaning Docker environment...$(NC)"
	docker-compose down --volumes --remove-orphans
	docker system prune -f

# =============================================================================
# DATABASE MANAGEMENT
# =============================================================================

setup-db: ## Set up database and run migrations
	@echo "$(BLUE)Setting up database...$(NC)"
	docker-compose up -d postgres redis
	sleep 5
	$(PYTHON) -m alembic upgrade head
	@echo "$(GREEN)Database setup complete!$(NC)"

reset-db: ## Reset database (WARNING: destroys all data)
	@echo "$(RED)WARNING: This will destroy all database data!$(NC)"
	@read -p "Are you sure? [y/N]: " confirm && [ "$$confirm" = "y" ]
	docker-compose down --volumes
	docker-compose up -d postgres redis
	sleep 5
	$(PYTHON) -m alembic upgrade head
	@echo "$(GREEN)Database reset complete!$(NC)"

alembic-upgrade: ## Run Alembic migrations (upgrade to latest)
	@echo "$(BLUE)Running database migrations...$(NC)"
	$(PYTHON) -m alembic upgrade head
	@echo "$(GREEN)Migrations complete!$(NC)"

alembic-downgrade: ## Downgrade Alembic migrations by one version
	@echo "$(BLUE)Downgrading database...$(NC)"
	$(PYTHON) -m alembic downgrade -1
	@echo "$(GREEN)Downgrade complete!$(NC)"

# =============================================================================
# COMPREHENSIVE CHECKS
# =============================================================================

check: ## Run all quality checks (lint, type-check, test, security)
	@echo "$(BLUE)Running comprehensive quality checks...$(NC)"
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) type-check
	$(MAKE) test
	$(MAKE) security
	@echo "$(GREEN)All checks passed!$(NC)"

# =============================================================================
# UTILITY COMMANDS
# =============================================================================

docs: ## Generate API documentation
	@echo "$(BLUE)Starting application to generate OpenAPI docs...$(NC)"
	@echo "Visit http://localhost:8000/docs for interactive API documentation"
	$(PYTHON) -m uvicorn dotmac_isp.app:app --host 0.0.0.0 --port 8000

requirements-update: ## Update requirements files (use with caution)
	@echo "$(BLUE)Updating requirements files...$(NC)"
	$(PIP) freeze > requirements.txt
	@echo "$(YELLOW)Review changes before committing!$(NC)"

env-check: ## Check environment variables and configuration
	@echo "$(BLUE)Checking environment configuration...$(NC)"
	@PYTHONPATH=src $(PYTHON) -c "from dotmac_isp.core.settings import get_settings; s=get_settings(); print(f'Environment: {s.environment}'); print(f'Debug: {s.debug}'); print(f'Database: {s.database_url[:20]}...')" 2>/dev/null || echo "$(YELLOW)Environment not configured - run 'make install-dev' first$(NC)"

# =============================================================================
# PLUGIN MANAGEMENT
# =============================================================================

install-plugin: ## Install a specific integration plugin (Usage: make install-plugin PLUGIN=twilio)
	@echo "$(BLUE)Installing plugin: $(PLUGIN)...$(NC)"
	@$(PYTHON) scripts/install_plugin.py $(PLUGIN)
	@echo "$(GREEN)Plugin $(PLUGIN) installed!$(NC)"

list-plugins: ## List available and installed plugins
	@echo "$(BLUE)Available Plugins:$(NC)"
	@$(PYTHON) scripts/list_plugins.py

remove-plugin: ## Remove a specific integration plugin (Usage: make remove-plugin PLUGIN=twilio)
	@echo "$(BLUE)Removing plugin: $(PLUGIN)...$(NC)"
	@$(PYTHON) scripts/remove_plugin.py $(PLUGIN)
	@echo "$(GREEN)Plugin $(PLUGIN) removed!$(NC)"

install-common-plugins: ## Install commonly used integration plugins
	@echo "$(BLUE)Installing common integration plugins...$(NC)"
	@make install-plugin PLUGIN=twilio
	@make install-plugin PLUGIN=stripe
	@make install-plugin PLUGIN=network-automation
	@echo "$(GREEN)Common plugins installed!$(NC)"

# =============================================================================
# PRODUCTION DEPLOYMENT
# =============================================================================

docker-prod-build: ## Build production Docker image
	@echo "$(BLUE)Building production Docker image...$(NC)"
	docker build -f Dockerfile.production -t $(PROJECT_NAME):production .
	@echo "$(GREEN)Production Docker image built!$(NC)"

docker-prod-run: ## Run production Docker containers
	@echo "$(BLUE)Starting production environment...$(NC)"
	docker-compose -f docker-compose.production.yml up -d
	@echo "$(GREEN)Production environment running!$(NC)"

# Version info
version: ## Show version information
	@echo "$(BLUE)DotMac ISP Framework$(NC)"
	@echo "Version: 1.0.0"
	@echo "Python: $$($(PYTHON) --version)"
	@echo "Environment: $$($(PYTHON) -c 'from dotmac_isp.core.settings import get_settings; print(get_settings().environment)' 2>/dev/null || echo 'Not configured')"