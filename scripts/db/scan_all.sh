#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?Set DATABASE_URL to a Postgres URL (e.g., postgresql+psycopg2://user:pass@host/db)}"

echo "== Alembic autogenerate (management) =="
export SERVICE_TYPE=management
alembic revision --autogenerate -m "management: autogen"

echo "== Alembic autogenerate (isp) =="
export SERVICE_TYPE=isp
alembic revision --autogenerate -m "isp: autogen"

echo "Done. Review generated revisions in alembic/versions and edit as needed."

