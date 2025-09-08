#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.mgmt-ui.yml"

export MANAGEMENT_API_URL="${MANAGEMENT_API_URL:-http://localhost:8000}"
export MANAGEMENT_UI_URL="${MANAGEMENT_UI_URL:-http://localhost:3005}"
export GATE_E_API_ONLY="${GATE_E_API_ONLY:-false}"

echo "[mgmt-ui] Starting stack..."
docker compose -f "$COMPOSE_FILE" up -d --build

echo "[mgmt-ui] Waiting for services..."
timeout 120 bash -c 'until curl -sf "$MANAGEMENT_API_URL/health" > /dev/null; do sleep 3; done'
timeout 120 bash -c 'until curl -sf "$MANAGEMENT_UI_URL" > /dev/null; do sleep 3; done'

echo "[mgmt-ui] Running Playwright tests (API_ONLY=$GATE_E_API_ONLY)..."
pushd "$PROJECT_ROOT" >/dev/null

export PLAYWRIGHT_TEST_BASE_URL="$MANAGEMENT_UI_URL"
export MANAGEMENT_URL="$MANAGEMENT_API_URL"

npm install --include=dev >/dev/null 2>&1 || true
npx playwright install >/dev/null 2>&1 || true

GATE_E_API_ONLY="$GATE_E_API_ONLY" MANAGEMENT_API_URL="$MANAGEMENT_API_URL" MANAGEMENT_UI_URL="$MANAGEMENT_UI_URL" \
npx playwright test .dev-artifacts/gate-e/cross-service-flow.spec.ts --reporter=line || true

popd >/dev/null

echo "[mgmt-ui] Done. Use 'docker compose -f $COMPOSE_FILE down' to stop."

