#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?Set DATABASE_URL to a Postgres URL (e.g., postgresql+psycopg2://user:pass@host/db)}"

echo "Upgrading to head..."
alembic upgrade head
echo "Current heads:"
alembic heads

