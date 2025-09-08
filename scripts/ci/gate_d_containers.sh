#!/usr/bin/env bash
set -euo pipefail

echo "[gate D] Containers: build images, compose up, smoke tests"

if ! command -v docker >/dev/null 2>&1; then
  echo "[gate D] Docker not found. Skipping containers gate." >&2
  exit 0
fi

if ! command -v docker compose >/dev/null 2>&1 && ! command -v docker-compose >/dev/null 2>&1; then
  echo "[gate D] docker compose not found. Install Docker Compose." >&2
  exit 1
fi

COMPOSE_CMD="docker compose"
command -v docker-compose >/dev/null 2>&1 && COMPOSE_CMD="docker-compose"

IMG_MGMT="dotmac/management:ci"
IMG_ISP="dotmac/isp:ci"

if [ -f Dockerfile.management ]; then
  echo "[gate D] Building ${IMG_MGMT}"
  docker build -f Dockerfile.management -t "${IMG_MGMT}" .
else
  echo "[gate D] Dockerfile.management not found; skipping management image build"
fi

if [ -f Dockerfile.isp ]; then
  echo "[gate D] Building ${IMG_ISP}"
  docker build -f Dockerfile.isp -t "${IMG_ISP}" .
else
  echo "[gate D] Dockerfile.isp not found; skipping isp image build"
fi

STACK_NAME="dotmac_ci_stack"

echo "[gate D] Bringing stack up via ${COMPOSE_CMD}"
${COMPOSE_CMD} down -v || true
${COMPOSE_CMD} up -d

cleanup() {
  echo "[gate D] Bringing stack down"
  ${COMPOSE_CMD} down -v || true
}
trap cleanup EXIT

# Smoke test parameters (override as needed)
export BASE_URL="${BASE_URL:-http://localhost:8001}"
export X_INTERNAL="${X_INTERNAL:-true}"
export TIMEOUT="${TIMEOUT:-5}"
export RETRIES="${RETRIES:-40}"
export SLEEP_SECS="${SLEEP_SECS:-3}"

echo "[gate D] Running smoke script against ${BASE_URL}"
bash scripts/ci/smoke_containers.sh

echo "[gate D] PASS: Containers gate completed"

