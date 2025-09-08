#!/usr/bin/env bash
set -euo pipefail

if [ ! -f alembic.ini ] || [ ! -d alembic ]; then
  echo "No alembic.ini or alembic/ directory found at repo root; skipping migrations."
  exit 0
fi

echo "Using DATABASE_URL=${DATABASE_URL:-}"
if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is not set; aborting." >&2
  exit 1
fi

echo "alembic upgrade head"
alembic upgrade head

echo "alembic downgrade -1 (if possible)"
if alembic downgrade -1; then
  echo "downgrade ok"
else
  echo "downgrade not available; continuing"
fi

echo "alembic upgrade head"
alembic upgrade head

echo "Migrations completed."

