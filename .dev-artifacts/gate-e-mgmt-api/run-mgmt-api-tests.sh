#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.mgmt-api.yml"

export MANAGEMENT_API_URL="${MANAGEMENT_API_URL:-http://localhost:8000}"
export SIGNOZ_URL="${SIGNOZ_URL:-http://localhost:3301}"

echo "[mgmt-api] Starting stack..."
docker compose -f "$COMPOSE_FILE" up -d --build

echo "[mgmt-api] Waiting for management backend health..."
timeout 120 bash -c 'until curl -sf "$MANAGEMENT_API_URL/health" > /dev/null; do sleep 3; done'

echo "[mgmt-api] Running API/observability checks..."
MANAGEMENT_URL="$MANAGEMENT_API_URL" python3 "$PROJECT_ROOT/.dev-artifacts/gate-e/observability-sanity-checks.py" || true

echo "[mgmt-api] Basic API smoke..."
curl -sf "$MANAGEMENT_API_URL/health" | jq '.' || true
curl -sf "$MANAGEMENT_API_URL/metrics" | head -n 20 || true

echo "[mgmt-api] Done. Use 'docker compose -f $COMPOSE_FILE down' to stop."

