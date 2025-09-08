#!/usr/bin/env bash
set -euo pipefail

URL="${1:?Usage: wait_for_http.sh <url> [timeout_seconds]}"
TIMEOUT="${2:-120}"

echo "Waiting for ${URL} (timeout ${TIMEOUT}s)"
SECONDS=0
until curl -fsS "${URL}" >/dev/null; do
  sleep 2
  if (( SECONDS > TIMEOUT )); then
    echo "Timed out waiting for ${URL}" >&2
    exit 1
  fi
done
echo "Healthy: ${URL}"

