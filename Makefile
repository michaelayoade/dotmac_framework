# DotMac Platform Unified Makefile
# Manages both ISP Framework and Management Platform

# Colors for output
YELLOW := \033[1;33m
GREEN := \033[0;32m
BLUE := \033[0;34m
RED := \033[0;31m
NC := \033[0m # No Color

.PHONY: help
help:
	@echo "$(BLUE)DotMac Unified Platform - Development Commands$(NC)"
	@echo "=============================================="
	@echo ""
	@echo "$(GREEN)🚀 Quick Start Commands:$(NC)"
	@echo "  $(YELLOW)quick-start         $(NC)  Complete first-time setup (recommended)"
	@echo "  $(YELLOW)dev-simple          $(NC)  Lightweight development (ISP + infrastructure only)"
	@echo "  $(YELLOW)dev-backend         $(NC)  Backend development (both platforms)"
	@echo "  $(YELLOW)dev-frontend        $(NC)  Frontend development (portals only)"
	@echo "  $(YELLOW)dev                 $(NC)  Full development environment"
	@echo "  $(YELLOW)staging             $(NC)  Production-like staging environment"
	@echo ""
	@echo "$(GREEN)📋 Basic Commands:$(NC)"
	@echo "  $(YELLOW)up                  $(NC)  Start complete unified platform"
	@echo "  $(YELLOW)down                $(NC)  Stop all services"
	@echo "  $(YELLOW)status              $(NC)  Show status of all services"
	@echo "  $(YELLOW)logs                $(NC)  Show logs from all services"
	@echo ""
	@echo "$(GREEN)Platform Commands:$(NC)"
	@echo "  $(YELLOW)up-isp              $(NC)  Start only ISP Framework services"
	@echo "  $(YELLOW)up-mgmt             $(NC)  Start only Management Platform services"
	@echo "  $(YELLOW)up-frontend         $(NC)  Start only frontend portals"
	@echo "  $(YELLOW)up-infrastructure   $(NC)  Start only shared infrastructure"
	@echo ""
	@echo "$(GREEN)Development Commands:$(NC)"
	@echo "  $(YELLOW)install-all         $(NC)  Install dependencies for both platforms"
	@echo "  $(YELLOW)test-all            $(NC)  Run tests for both platforms"
	@echo "  $(YELLOW)test-isp            $(NC)  Run ISP Framework tests"
	@echo "  $(YELLOW)test-mgmt           $(NC)  Run Management Platform tests"
	@echo "  $(YELLOW)test-integration    $(NC)  Run cross-platform integration tests"
	@echo "  $(YELLOW)lint-all            $(NC)  Lint both platforms"
	@echo "  $(YELLOW)format-all          $(NC)  Format code in both platforms"
	@echo ""
	@echo "$(GREEN)🤖 AI-First Testing:$(NC)"
	@echo "  $(YELLOW)ai-safety-check     $(NC)  AI safety checks (primary gate)"
	@echo "  $(YELLOW)test-ai-first       $(NC)  AI-optimized test suite (fast)"
	@echo "  $(YELLOW)test-property-based $(NC)  Property-based tests (AI-generated)"
	@echo "  $(YELLOW)test-behavior       $(NC)  Business behavior tests"
	@echo "  $(YELLOW)test-contracts      $(NC)  API contract tests"
	@echo "  $(YELLOW)test-revenue-critical$(NC) Revenue-critical tests (NEVER FAIL)"
	@echo ""
	@echo "$(GREEN)Database Commands:$(NC)"
	@echo "  $(YELLOW)db-setup            $(NC)  Set up databases for both platforms"
	@echo "  $(YELLOW)db-migrate-all      $(NC)  Run migrations for both platforms"
	@echo "  $(YELLOW)db-migrate-isp      $(NC)  Run ISP Framework migrations"
	@echo "  $(YELLOW)db-migrate-mgmt     $(NC)  Run Management Platform migrations"
	@echo "  $(YELLOW)db-reset-all        $(NC)  Reset all databases (DESTRUCTIVE)"
	@echo ""
	@echo "$(GREEN)Build & Deploy:$(NC)"
	@echo "  $(YELLOW)build-all           $(NC)  Build all Docker images"
	@echo "  $(YELLOW)build-isp           $(NC)  Build ISP Framework image"
	@echo "  $(YELLOW)build-mgmt          $(NC)  Build Management Platform image"
	@echo "  $(YELLOW)deploy-dev          $(NC)  Deploy to development environment"
	@echo "  $(YELLOW)deploy-prod         $(NC)  Deploy to production environment"
	@echo ""
	@echo "$(GREEN)Monitoring & Health:$(NC)"
	@echo "  $(YELLOW)health-check        $(NC)  Check health of all services"
	@echo "  $(YELLOW)show-endpoints      $(NC)  Show all service endpoints"
	@echo "  $(YELLOW)monitoring          $(NC)  Open SignOz monitoring dashboard"
	@echo ""
	@echo "$(GREEN)📚 Documentation:$(NC)"
	@echo "  $(YELLOW)docs                $(NC)  View all documentation"
	@echo "  $(YELLOW)deploy-guide        $(NC)  Open deployment guide" 
	@echo "  $(YELLOW)runbooks            $(NC)  Open operational runbooks"
	@echo "  $(YELLOW)testing-guide       $(NC)  Open testing strategy guide"
	@echo "  $(YELLOW)check-setup         $(NC)  Check prerequisites and setup"
	@echo ""

# ===== QUICK START COMMANDS =====

.PHONY: install-all
install-all: install-isp install-mgmt
	@echo "$(GREEN)✅ All dependencies installed successfully$(NC)"

.PHONY: setup-env
setup-env:
	@echo "$(YELLOW)Setting up environment configuration...$(NC)"
	@./env-setup.sh

.PHONY: install-isp
install-isp:
	@echo "$(YELLOW)Installing ISP Framework dependencies...$(NC)"
	cd isp-framework && make install-dev

.PHONY: install-mgmt
install-mgmt:
	@echo "$(YELLOW)Installing Management Platform dependencies...$(NC)"
	cd management-platform && make install-dev

.PHONY: up
up:
	@echo "$(GREEN)🚀 Starting complete DotMac Platform...$(NC)"
	docker-compose -f docker-compose.unified.yml up -d
	@echo "$(GREEN)✅ Platform started successfully!$(NC)"
	@echo ""
	@make show-endpoints

.PHONY: down
down:
	@echo "$(YELLOW)🛑 Stopping DotMac Platform...$(NC)"
	docker-compose -f docker-compose.unified.yml down
	@echo "$(GREEN)✅ Platform stopped$(NC)"

.PHONY: status
status:
	@echo "$(BLUE)DotMac Platform Status$(NC)"
	@echo "====================="
	docker-compose -f docker-compose.unified.yml ps

.PHONY: logs
logs:
	docker-compose -f docker-compose.unified.yml logs -f

# ===== PLATFORM-SPECIFIC COMMANDS =====

.PHONY: up-infrastructure
up-infrastructure:
	@echo "$(YELLOW)Starting shared infrastructure...$(NC)"
	docker-compose -f docker-compose.unified.yml up -d postgres-shared redis-shared

.PHONY: up-isp
up-isp: up-infrastructure
	@echo "$(YELLOW)Starting ISP Framework services...$(NC)"
	docker-compose -f docker-compose.unified.yml up -d db-migrate
	docker-compose -f docker-compose.unified.yml up -d isp-framework

.PHONY: up-mgmt
up-mgmt: up-infrastructure
	@echo "$(YELLOW)Starting Management Platform services...$(NC)"
	docker-compose -f docker-compose.unified.yml up -d db-migrate
	docker-compose -f docker-compose.unified.yml up -d management-platform

.PHONY: up-frontend
up-frontend:
	@echo "$(YELLOW)Starting frontend portals...$(NC)"
	docker-compose -f docker-compose.unified.yml up -d master-admin-portal customer-portal reseller-portal

# ===== TESTING COMMANDS =====

.PHONY: test-all
test-all: test-isp test-mgmt test-integration
	@echo "$(GREEN)✅ All tests completed$(NC)"

.PHONY: test-isp
test-isp:
	@echo "$(YELLOW)Running ISP Framework tests...$(NC)"
	cd isp-framework && make test

.PHONY: test-mgmt
test-mgmt:
	@echo "$(YELLOW)Running Management Platform tests...$(NC)"
	cd management-platform && make test

.PHONY: test-integration
test-integration:
	@echo "$(YELLOW)Running cross-platform integration tests...$(NC)"
	@echo "$(BLUE)Testing ISP Framework ↔ Management Platform integration...$(NC)"
	# Test cross-platform API calls
	cd shared/scripts && python test-cross-platform-integration.py

.PHONY: test-ai-first
test-ai-first:
	@echo "$(YELLOW)🤖 Running AI-first test suite (optimized for speed)...$(NC)"
	cd isp-framework && make test-ai-first
	cd management-platform && make test-ai-first  
	@echo "$(GREEN)✅ AI-first test suite completed$(NC)"

.PHONY: test-ai-suite
test-ai-suite: test-ai-first
	@echo "$(GREEN)✅ AI test suite completed for both platforms$(NC)"

.PHONY: test-property-based
test-property-based:
	@echo "$(YELLOW)🎲 Running property-based tests (AI-generated scenarios)...$(NC)"
	cd isp-framework && make test-property-based
	cd management-platform && make test-property-based
	@echo "$(GREEN)✅ Property-based tests completed$(NC)"

.PHONY: test-behavior
test-behavior:
	@echo "$(YELLOW)👥 Running business behavior tests...$(NC)"  
	cd isp-framework && make test-behaviors
	cd management-platform && make test-behavior
	@echo "$(GREEN)✅ Behavior tests completed$(NC)"

.PHONY: test-contracts
test-contracts:
	@echo "$(YELLOW)📋 Running API contract tests...$(NC)"
	cd isp-framework && make test-contracts
	cd management-platform && make test-contracts
	@echo "$(GREEN)✅ Contract tests completed$(NC)"

.PHONY: test-revenue-critical
test-revenue-critical:
	@echo "$(YELLOW)Running revenue-critical tests...$(NC)"
	cd isp-framework && make test-revenue-critical
	cd management-platform && make test-revenue-critical
	@echo "$(GREEN)✅ Revenue-critical tests completed for both platforms$(NC)"

.PHONY: ai-safety-check
ai-safety-check:
	@echo "$(YELLOW)Running AI safety checks...$(NC)"
	cd isp-framework && make ai-safety-check
	cd management-platform && make ai-safety-check
	@echo "$(GREEN)✅ AI safety checks passed for both platforms$(NC)"

# ===== CODE QUALITY COMMANDS =====

.PHONY: lint-all
lint-all:
	@echo "$(YELLOW)Linting all platforms...$(NC)"
	cd isp-framework && make lint
	cd management-platform && make lint

.PHONY: format-all
format-all:
	@echo "$(YELLOW)Formatting all platforms...$(NC)"
	cd isp-framework && make format
	cd management-platform && make format

.PHONY: security-all
security-all:
	@echo "$(YELLOW)Running security scans on all platforms...$(NC)"
	cd isp-framework && make security
	cd management-platform && make security

# ===== DATABASE COMMANDS =====

.PHONY: db-setup
db-setup:
	@echo "$(YELLOW)Setting up databases for both platforms...$(NC)"
	docker-compose -f docker-compose.unified.yml up -d postgres-shared
	@echo "$(GREEN)Waiting for PostgreSQL to be ready...$(NC)"
	sleep 10
	@make db-migrate-all

.PHONY: db-migrate-all
db-migrate-all: db-validate-schemas db-migrate-mgmt db-migrate-isp
	@echo "$(GREEN)✅ All migrations completed in coordinated order$(NC)"

.PHONY: db-validate-schemas
db-validate-schemas:
	@echo "$(YELLOW)Validating schema compatibility...$(NC)"
	@python3 -c "import sys; sys.path.append('shared'); from database.coordination import validate_schemas; warnings = validate_schemas(); print('\\n'.join(warnings) if warnings else '✅ Schema validation passed')"

.PHONY: db-migrate-isp
db-migrate-isp:
	@echo "$(YELLOW)Running ISP Framework migrations...$(NC)"
	cd isp-framework && make db-migrate

.PHONY: db-migrate-mgmt
db-migrate-mgmt:
	@echo "$(YELLOW)Running Management Platform migrations...$(NC)"
	cd management-platform && make db-migrate

.PHONY: db-reset-all
db-reset-all:
	@echo "$(RED)⚠️  WARNING: This will destroy all data!$(NC)"
	@echo "$(YELLOW)Are you sure? Press Ctrl+C to cancel, Enter to continue...$(NC)"
	@read
	docker-compose -f docker-compose.unified.yml down -v
	docker volume prune -f
	@make db-setup

# ===== BUILD & DEPLOY COMMANDS =====

.PHONY: build-all
build-all: build-isp build-mgmt
	@echo "$(GREEN)✅ All images built successfully$(NC)"

.PHONY: build-isp
build-isp:
	@echo "$(YELLOW)Building ISP Framework image...$(NC)"
	docker-compose -f docker-compose.unified.yml build isp-framework

.PHONY: build-mgmt
build-mgmt:
	@echo "$(YELLOW)Building Management Platform image...$(NC)"
	docker-compose -f docker-compose.unified.yml build management-platform

.PHONY: deploy-dev
deploy-dev: build-all
	@echo "$(YELLOW)Deploying to development environment...$(NC)"
	docker-compose -f docker-compose.unified.yml up -d
	@make health-check

.PHONY: deploy-prod
deploy-prod:
	@echo "$(RED)⚠️  Production deployment requires additional security checks$(NC)"
	@echo "$(YELLOW)Use shared/deployments/kubernetes/ or terraform/ for production$(NC)"

# ===== MONITORING & HEALTH COMMANDS =====

.PHONY: health-check
health-check:
	@echo "$(BLUE)Checking health of all services...$(NC)"
	@echo ""
	@echo "$(YELLOW)ISP Framework Health (http://localhost:8001/health):$(NC)"
	@curl -sf http://localhost:8001/health || echo "$(RED)❌ ISP Framework not responding$(NC)"
	@echo ""
	@echo "$(YELLOW)Management Platform Health (http://localhost:8000/health):$(NC)"
	@curl -sf http://localhost:8000/health || echo "$(RED)❌ Management Platform not responding$(NC)"
	@echo ""

.PHONY: show-endpoints
show-endpoints:
	@echo "$(BLUE)DotMac Platform Service Endpoints$(NC)"
	@echo "================================="
	@echo ""
	@echo "$(GREEN)🏗️  Core Services:$(NC)"
	@echo "  ISP Framework API:       http://localhost:8001"
	@echo "  Management Platform API: http://localhost:8000"
	@echo ""
	@echo "$(GREEN)🌐 Frontend Portals:$(NC)"
	@echo "  Master Admin Portal:     http://localhost:3000"
	@echo "  Customer Portal:         http://localhost:3001"
	@echo "  Reseller Portal:         http://localhost:3002"
	@echo ""
	@echo "$(GREEN)📊 Infrastructure:$(NC)"
	@echo "  PostgreSQL:              localhost:5434"
	@echo "  Redis:                   localhost:6378"
	@echo "  OpenBao (Secrets):       http://localhost:8200"
	@echo "  SignOz (Monitoring):     http://localhost:3301"
	@echo "  ClickHouse:              localhost:9000"
	@echo ""
	@echo "$(GREEN)📡 Observability:$(NC)"
	@echo "  OTLP gRPC:               localhost:4317"
	@echo "  OTLP HTTP:               localhost:4318"
	@echo "  Prometheus Metrics:      localhost:8889"
	@echo ""

.PHONY: monitoring
monitoring:
	@echo "$(YELLOW)Opening SignOz monitoring dashboard...$(NC)"
	@command -v open >/dev/null 2>&1 && open http://localhost:3301 || echo "Open http://localhost:3301 in your browser"

# ===== UTILITY COMMANDS =====

.PHONY: clean
clean:
	@echo "$(YELLOW)Cleaning up build artifacts...$(NC)"
	cd isp-framework && make clean
	cd management-platform && make clean
	docker system prune -f

.PHONY: shell-isp
shell-isp:
	@echo "$(YELLOW)Opening shell in ISP Framework container...$(NC)"
	docker-compose -f docker-compose.unified.yml exec isp-framework bash

.PHONY: shell-mgmt
shell-mgmt:
	@echo "$(YELLOW)Opening shell in Management Platform container...$(NC)"
	docker-compose -f docker-compose.unified.yml exec management-platform bash

.PHONY: logs-isp
logs-isp:
	docker-compose -f docker-compose.unified.yml logs -f isp-framework

.PHONY: logs-mgmt
logs-mgmt:
	docker-compose -f docker-compose.unified.yml logs -f management-platform

# ===== DEVELOPMENT SHORTCUTS =====

.PHONY: quick-start
quick-start: setup-env install-all up
	@echo "$(GREEN)🎉 Welcome to DotMac Platform!$(NC)"
	@echo "$(BLUE)First-time setup complete. Here are your next steps:$(NC)"
	@echo ""
	@make show-endpoints
	@echo ""
	@echo "$(YELLOW)💡 Quick tips:$(NC)"
	@echo "  • Run 'make health-check' to verify all services"
	@echo "  • Run 'make test-all' to run the full test suite"
	@echo "  • Run 'make logs' to view real-time logs"
	@echo "  • Check DEPLOYMENT_GUIDE.md for detailed help"
	@echo ""

.PHONY: dev-simple
dev-simple: up-infrastructure up-isp
	@echo "$(GREEN)🚀 Lightweight development environment ready!$(NC)"
	@echo "$(YELLOW)Note: Only ISP Framework and infrastructure running$(NC)"
	@make show-endpoints

.PHONY: dev-backend
dev-backend: up-infrastructure up-isp up-mgmt
	@echo "$(GREEN)🚀 Backend development environment ready!$(NC)"
	@echo "$(YELLOW)Note: Frontend portals not started$(NC)"
	@make show-endpoints

.PHONY: dev-frontend
dev-frontend: up-infrastructure up-frontend
	@echo "$(GREEN)🚀 Frontend development environment ready!$(NC)"
	@echo "$(YELLOW)Note: Starting frontend development servers...$(NC)"
	cd frontend && pnpm dev &
	@make show-endpoints

.PHONY: dev-full
dev-full: up
	@echo "$(GREEN)🚀 Complete development environment ready!$(NC)"
	@make show-endpoints

.PHONY: dev
dev: dev-full

.PHONY: staging
staging:
	@echo "$(YELLOW)🏗️  Starting production-like staging environment...$(NC)"
	docker-compose -f docker-compose.production.yml up -d
	@echo "$(GREEN)✅ Staging environment ready$(NC)"
	@make health-check

.PHONY: restart
restart: down up
	@echo "$(GREEN)✅ Platform restarted$(NC)"

.PHONY: quick-test
quick-test:
	@echo "$(YELLOW)Running quick smoke tests...$(NC)"
	cd isp-framework && make test-smoke-critical
	cd management-platform && make test-smoke-critical

.PHONY: test-backend
test-backend: test-isp test-mgmt
	@echo "$(GREEN)✅ Backend tests completed$(NC)"

.PHONY: health-check-detailed
health-check-detailed: health-check
	@echo ""
	@echo "$(BLUE)Detailed Health Check:$(NC)"
	@echo "======================"
	@echo "$(YELLOW)Database Connection:$(NC)"
	@docker-compose -f docker-compose.unified.yml exec postgres-shared pg_isready -U dotmac_admin || echo "$(RED)❌ Database not ready$(NC)"
	@echo "$(YELLOW)Redis Connection:$(NC)"
	@docker-compose -f docker-compose.unified.yml exec redis-shared redis-cli ping || echo "$(RED)❌ Redis not responding$(NC)"
	@echo "$(YELLOW)OpenBao Status:$(NC)"
	@curl -sf http://localhost:8200/v1/sys/health | jq '.sealed' || echo "$(RED)❌ OpenBao not accessible$(NC)"

.PHONY: secrets-reset
secrets-reset:
	@echo "$(RED)⚠️  Resetting development secrets (DO NOT USE IN PRODUCTION)$(NC)"
	docker-compose -f docker-compose.unified.yml restart openbao-shared
	@echo "$(GREEN)✅ Secrets reset for development$(NC)"

.PHONY: docs
docs:
	@echo "$(BLUE)DotMac Platform Documentation$(NC)"
	@echo "============================="
	@echo ""
	@echo "$(GREEN)📖 Key Documents:$(NC)"
	@echo "  • DEPLOYMENT_GUIDE.md - Complete deployment guide"
	@echo "  • OPERATIONAL_RUNBOOKS.md - Troubleshooting and operations"
	@echo "  • README.md - Platform overview and quick start"
	@echo ""
	@echo "$(GREEN)🔍 Quick Links:$(NC)"
	@echo "  • API Documentation: http://localhost:8001/docs"
	@echo "  • Management API: http://localhost:8000/docs"
	@echo "  • Monitoring: http://localhost:3301"
	@echo ""

.PHONY: deploy-guide
deploy-guide:
	@command -v open >/dev/null 2>&1 && open DEPLOYMENT_GUIDE.md || echo "Open DEPLOYMENT_GUIDE.md in your text editor"

.PHONY: runbooks
runbooks:
	@command -v open >/dev/null 2>&1 && open OPERATIONAL_RUNBOOKS.md || echo "Open OPERATIONAL_RUNBOOKS.md in your text editor"

.PHONY: testing-guide
testing-guide:
	@command -v open >/dev/null 2>&1 && open TESTING_STRATEGY.md || echo "Open TESTING_STRATEGY.md in your text editor"

.PHONY: clean-restart
clean-restart: down
	@echo "$(YELLOW)Cleaning Docker resources...$(NC)"
	docker system prune -f
	docker volume prune -f
	@make up

.PHONY: check-setup
check-setup:
	@echo "$(BLUE)Checking DotMac Platform Setup$(NC)"
	@echo "=============================="
	@echo ""
	@echo -n "$(YELLOW)Docker: $(NC)"
	@docker --version >/dev/null 2>&1 && echo "$(GREEN)✅ Installed$(NC)" || echo "$(RED)❌ Not found$(NC)"
	@echo -n "$(YELLOW)Docker Compose: $(NC)"
	@docker-compose --version >/dev/null 2>&1 && echo "$(GREEN)✅ Installed$(NC)" || echo "$(RED)❌ Not found$(NC)"
	@echo -n "$(YELLOW)Python 3.11+: $(NC)"
	@python3 --version 2>/dev/null | grep -E "3\.(11|12)" >/dev/null && echo "$(GREEN)✅ Installed$(NC)" || echo "$(RED)❌ Not found or wrong version$(NC)"
	@echo -n "$(YELLOW)Node.js 18+: $(NC)"
	@node --version 2>/dev/null | grep -E "v(1[8-9]|2[0-9])" >/dev/null && echo "$(GREEN)✅ Installed$(NC)" || echo "$(RED)❌ Not found or wrong version$(NC)"
	@echo -n "$(YELLOW)Git: $(NC)"
	@git --version >/dev/null 2>&1 && echo "$(GREEN)✅ Installed$(NC)" || echo "$(RED)❌ Not found$(NC)"
	@echo ""
	@echo -n "$(YELLOW)Environment Config: $(NC)"
	@test -f .env.local && echo "$(GREEN)✅ .env.local exists$(NC)" || echo "$(YELLOW)⚠️  Run 'make setup-env' first$(NC)"
	@echo ""

.PHONY: full-check
full-check: lint-all test-all security-all health-check
	@echo "$(GREEN)✅ Full quality check completed$(NC)"
