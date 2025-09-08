#!/usr/bin/env bash
set -euo pipefail

# Small health-check and authenticated smoke test for a running container stack.

BASE_URL="${BASE_URL:-http://localhost:8000}"
HEALTH_PATH="${HEALTH_PATH:-/health}"
METRICS_PATH="${METRICS_PATH:-/metrics}"
AUTH_ENDPOINT="${AUTH_ENDPOINT:-/api/tenants}"  # simple authenticated route
INTERNAL_HEALTH_PATH="${INTERNAL_HEALTH_PATH:-/api/workflows/health}"

AUTH_TOKEN="${AUTH_TOKEN:-}"              # if provided, uses Authorization: Bearer
X_INTERNAL="${X_INTERNAL:-false}"         # if true, sets x-internal-request: true and hits internal health
TIMEOUT="${TIMEOUT:-5}"
RETRIES="${RETRIES:-20}"
SLEEP_SECS="${SLEEP_SECS:-3}"

echo "[smoke] Base URL: ${BASE_URL}"

hdrs=("-H" "Accept: application/json")
if [ -n "$AUTH_TOKEN" ]; then
  hdrs+=("-H" "Authorization: Bearer ${AUTH_TOKEN}")
fi

wait_for_200() {
  local url="$1"
  local name="$2"
  for i in $(seq 1 "$RETRIES"); do
    if curl -fsS "${url}" -m "$TIMEOUT" -o /dev/null; then
      echo "[smoke] ${name}: OK (${url})"
      return 0
    fi
    echo "[smoke] ${name}: waiting... (${i}/${RETRIES})"
    sleep "$SLEEP_SECS"
  done
  echo "[smoke] ${name}: FAIL (${url})" >&2
  return 1
}

STATUS=0

# 1) Health endpoint
wait_for_200 "${BASE_URL}${HEALTH_PATH}" "health" || STATUS=1

# 2) Metrics endpoint (optional)
if curl -fsS "${BASE_URL}${METRICS_PATH}" -m "$TIMEOUT" -o /dev/null; then
  echo "[smoke] metrics: OK"
else
  echo "[smoke] metrics: unavailable (continuing)"
fi

# 3) Authenticated list (if token present)
if [ -n "$AUTH_TOKEN" ]; then
  if curl -fsS "${BASE_URL}${AUTH_ENDPOINT}" -m "$TIMEOUT" "${hdrs[@]}" -o /dev/null; then
    echo "[smoke] authenticated request: OK (${AUTH_ENDPOINT})"
  else
    echo "[smoke] authenticated request: FAIL (${AUTH_ENDPOINT})" >&2
    STATUS=1
  fi
else
  echo "[smoke] skipping authenticated request (no AUTH_TOKEN)"
fi

# 4) Internal workflows health (if requested)
if [ "$X_INTERNAL" = "true" ]; then
  if curl -fsS "${BASE_URL}${INTERNAL_HEALTH_PATH}" -m "$TIMEOUT" -H 'x-internal-request: true' -o /dev/null; then
    echo "[smoke] workflows health (internal): OK"
  else
    echo "[smoke] workflows health (internal): FAIL" >&2
    STATUS=1
  fi
fi

if [ "$STATUS" -ne 0 ]; then
  echo "[smoke] FAIL: container smoke test failed" >&2
  exit 1
fi

echo "[smoke] PASS: container smoke test completed"

