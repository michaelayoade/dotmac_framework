#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.isp-api.yml"

export MANAGEMENT_API_URL="${MANAGEMENT_API_URL:-}"
export ISP_API_URL="${ISP_API_URL:-http://localhost:8001}"

echo "[isp-api] Starting stack..."
docker compose -f "$COMPOSE_FILE" up -d --build

echo "[isp-api] Waiting for services..."
timeout 180 bash -c 'until curl -sf "$ISP_API_URL/health" > /dev/null; do sleep 3; done'

echo "[isp-api] Basic API smoke..."
curl -sf "$ISP_API_URL/health" | jq '.' || true

if [[ -n "${MANAGEMENT_API_URL}" ]]; then
  echo "[isp-api] Relationship checks (ISP → Management)..."
  curl -sf "$MANAGEMENT_API_URL/metrics" | grep -E "dotmac_(api_requests|customers|notifications)_total" || true
else
  echo "[isp-api] MANAGEMENT_API_URL not set; skipping relationship checks"
fi

echo "[isp-api] Done. Use 'docker compose -f $COMPOSE_FILE down' to stop."
