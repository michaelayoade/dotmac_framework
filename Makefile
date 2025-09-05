.PHONY: help install lint type test run-isp run-mgmt run-db run-redis compose-start compose-stop compose-logs compose-status compose-health clean

# Detect poetry; prefer it for running tools
POETRY := $(shell command -v poetry 2>/dev/null)
ifdef POETRY
RUN = poetry run
INSTALL_CMD = poetry install --with dev
else
RUN =
INSTALL_CMD = @echo "Poetry not found. Please install Poetry (https://python-poetry.org/) or install deps manually." && false
endif

UVICORN = $(RUN) uvicorn
RUFF    = $(RUN) ruff
MYPY    = $(RUN) mypy
PYTEST  = $(RUN) pytest

help:
	@echo "DotMac Framework - common developer commands"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Setup:"
	@echo "  install         Install deps (prefers Poetry with dev extras)"
	@echo ""
	@echo "Quality:"
	@echo "  lint            Run Ruff on the repo"
	@echo "  type            Run MyPy on src/"
	@echo "  test            Run pytest"
	@echo ""
	@echo "Run services (FastAPI):"
	@echo "  run-isp         Run ISP app on :8001 (dev, hot-reload)"
	@echo "  run-mgmt        Run Management app on :8002 (dev, hot-reload)"
	@echo ""
	@echo "Infra via compose helper (Postgres, Redis, services):"
	@echo "  compose-start   Build and start all services"
	@echo "  compose-stop    Stop all services"
	@echo "  compose-logs    Tail logs from services"
	@echo "  compose-status  Show compose status"
	@echo "  compose-health  Quick health checks"
	@echo ""
	@echo "Utilities:"
	@echo "  clean           Remove compose resources (volumes may remain)"

install:
	$(INSTALL_CMD)

lint:
	$(RUFF) check .

type:
	$(MYPY) src/

test:
	$(PYTEST)

# FastAPI apps (development-friendly defaults)
run-isp:
	ENVIRONMENT=development LOG_LEVEL=INFO \
	$(UVICORN) dotmac_isp.app:create_app --factory --reload --host 0.0.0.0 --port 8001

run-mgmt:
	ENVIRONMENT=development LOG_LEVEL=INFO \
	$(UVICORN) dotmac_management.main:create_app --factory --reload --host 0.0.0.0 --port 8002

# Legacy docker-compose orchestrator wrapper
LEGACY_COMPOSE := src/dotmac_shared/scripts/legacy/start-backend.sh

compose-start:
	bash $(LEGACY_COMPOSE) start

compose-stop:
	bash $(LEGACY_COMPOSE) stop

compose-logs:
	bash $(LEGACY_COMPOSE) logs --follow

compose-status:
	bash $(LEGACY_COMPOSE) status

compose-health:
	bash $(LEGACY_COMPOSE) health

clean:
	bash $(LEGACY_COMPOSE) clean || true

