#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.isp-ui.yml"

export ISP_API_URL="${ISP_API_URL:-http://localhost:8001}"
export ISP_ADMIN_UI_URL="${ISP_ADMIN_UI_URL:-http://localhost:3010}"

echo "[isp-ui] Starting stack..."
docker compose -f "$COMPOSE_FILE" up -d --build

echo "[isp-ui] Waiting for services..."
timeout 180 bash -c 'until curl -sf "$ISP_API_URL/health" > /dev/null; do sleep 3; done'
timeout 180 bash -c 'until curl -sf "$ISP_ADMIN_UI_URL" > /dev/null; do sleep 3; done'

echo "[isp-ui] Smoke check complete. Add Playwright tests for ISP UI as needed."

