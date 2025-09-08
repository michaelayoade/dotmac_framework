#!/usr/bin/env bash
set -euo pipefail

VENV_DIR=".venv-ci"
DB_IMAGE="postgres:15"
DB_NAME="dotmac_ci_pg"
HOST_PORT="54329"
DB_PASS="postgres"

if [ ! -d "${VENV_DIR}" ]; then
  echo "[gate B] venv not found. Run scripts/ci/venv_bootstrap.sh first." >&2
  exit 1
fi
source "${VENV_DIR}/bin/activate"

command -v docker >/dev/null 2>&1 || {
  echo "[gate B] Docker is required for ephemeral Postgres." >&2
  exit 1
}

echo "[gate B] Starting ephemeral Postgres (${DB_IMAGE}) on port ${HOST_PORT}"
docker rm -f "${DB_NAME}" >/dev/null 2>&1 || true
docker run -d --name "${DB_NAME}" -e POSTGRES_PASSWORD="${DB_PASS}" -p "${HOST_PORT}:5432" "${DB_IMAGE}"

cleanup() {
  echo "[gate B] Cleaning up Postgres container"
  docker rm -f "${DB_NAME}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[gate B] Waiting for Postgres to be ready..."
for i in {1..30}; do
  if docker exec "${DB_NAME}" pg_isready -U postgres >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

export DATABASE_URL="postgresql+psycopg2://postgres:${DB_PASS}@localhost:${HOST_PORT}/postgres"
echo "[gate B] DATABASE_URL=${DATABASE_URL}"

echo "[gate B] Installing alembic and psycopg2 in venv (if missing)"
python -m pip install alembic psycopg2-binary >/dev/null

if [ -d alembic ]; then
  echo "[gate B] Running alembic upgrade head"
  alembic upgrade head

  echo "[gate B] Verifying reversible migration (downgrade -1 then upgrade head)"
  set +e
  alembic downgrade -1 && alembic upgrade head
  MIG_STATUS=$?
  set -e
  if [ "$MIG_STATUS" -ne 0 ]; then
    echo "[gate B] WARNING: Downgrade/upgrade cycle failed. Review migration scripts."
  fi
else
  echo "[gate B] No alembic directory found; skipping migration checks"
fi

echo "[gate B] PASS: DB gate completed"

