#!/usr/bin/env bash
set -euo pipefail

# Simple production smoke test for DotMac portals and APIs
#
# Env vars (set to your environment):
#   ADMIN_BASE_URL        e.g. https://admin.yourdomain.com
#   RESELLER_BASE_URL     e.g. https://reseller.yourdomain.com
#   TENANT_BASE_URL       e.g. https://acme.isp.yourdomain.com
#   MGMT_API_URL          e.g. https://api.yourdomain.com or admin service URL
#   TENANT_SLUG           e.g. acme (used for header checks)
#   API_VERSION           e.g. v1 (used for header checks)
#
# Exit codes:
#   0 - All checks passed
#   1 - One or more checks failed

ADMIN_BASE_URL=${ADMIN_BASE_URL:-"http://localhost:3004"}
RESELLER_BASE_URL=${RESELLER_BASE_URL:-"http://localhost:3005"}
TENANT_BASE_URL=${TENANT_BASE_URL:-"http://localhost:3006"}
MGMT_API_URL=${MGMT_API_URL:-"http://localhost:8001"}
TENANT_SLUG=${TENANT_SLUG:-"dev"}
API_VERSION=${API_VERSION:-"v1"}

pass=0
fail=0

check_http() {
  local name=$1 url=$2
  echo "[CHECK] $name -> $url"
  if curl -skf "$url" >/dev/null; then
    echo "  OK"
    ((pass++))
  else
    echo "  FAIL"
    ((fail++))
  fi
}

check_client_headers() {
  local name=$1 base=$2
  echo "[CHECK] $name client-check headers"
  local out
  if out=$(curl -sk -H "X-Tenant-ID: $TENANT_SLUG" -H "X-API-Version: $API_VERSION" "$base/api/health/client-check"); then
    echo "  Response: $out"
    if echo "$out" | grep -q '"ok":true' && echo "$out" | grep -q "$TENANT_SLUG"; then
      echo "  OK"
      ((pass++))
    else
      echo "  FAIL - missing ok/tenant headers"
      ((fail++))
    fi
  else
    echo "  FAIL"
    ((fail++))
  fi
}

echo "=== DotMac Smoke Test ==="

# 1) Health endpoints
check_http "Admin /health"        "$ADMIN_BASE_URL/health"
check_http "Reseller /health"     "$RESELLER_BASE_URL/api/health" || true
check_http "Tenant /health"       "$TENANT_BASE_URL/api/health" || true
check_http "Mgmt API /health"     "$MGMT_API_URL/health"

# 2) Client header validation
check_client_headers "Admin"    "$ADMIN_BASE_URL"
check_client_headers "Reseller" "$RESELLER_BASE_URL"
check_client_headers "Tenant"   "$TENANT_BASE_URL"

# 3) Metrics exposure
check_http "Mgmt API /metrics" "$MGMT_API_URL/metrics"

# 4) Background ops inspection API
check_http "Mgmt API bgops list" "$MGMT_API_URL/api/v1/bgops/idempotency?limit=1"

echo "=== Results: $pass OK, $fail FAIL ==="
if [ "$fail" -gt 0 ]; then
  exit 1
fi
exit 0

