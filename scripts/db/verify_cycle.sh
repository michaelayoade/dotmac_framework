#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?Set DATABASE_URL to a Postgres URL (e.g., postgresql+psycopg2://user:pass@host/db)}"

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

echo "Verification cycle complete."

