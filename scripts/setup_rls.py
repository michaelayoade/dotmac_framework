"""
Setup RLS (Row Level Security) policies for tenant-aware tables.

This script connects to the database specified by DATABASE_URL (or ASYNC_DATABASE_URL)
and applies RLS to all tables that include a tenant_id column. It creates helper
functions and standard policies if they do not already exist.

Usage:
  ENV:
    DATABASE_URL=postgresql+asyncpg://user:pass@host/db  (or postgresql://)

  Run:
    python scripts/setup_rls.py
"""

import asyncio
import os
from typing import List

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


def _get_async_db_url() -> str:
    url = os.getenv("ASYNC_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL or ASYNC_DATABASE_URL must be set")
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


CREATE_HELPERS_SQL = r"""
-- Helper functions for RLS
CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS TEXT AS $$
BEGIN
    RETURN current_setting('app.current_tenant_id', true);
EXCEPTION
    WHEN undefined_object THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION check_tenant_access(tenant_id TEXT) RETURNS BOOLEAN AS $$
BEGIN
    RETURN current_tenant_id() IS NOT NULL AND current_tenant_id() = tenant_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
"""


async def _fetch_tenant_tables(conn) -> List[str]:
    query = text(
        """
        SELECT table_schema, table_name
        FROM information_schema.columns
        WHERE column_name = 'tenant_id'
          AND table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY table_schema, table_name
        """
    )
    rows = (await conn.execute(query)).fetchall()
    return [f"{r[0]}.{r[1]}" for r in rows]


async def apply_rls():
    db_url = _get_async_db_url()
    engine = create_async_engine(db_url, pool_pre_ping=True)
    async with engine.begin() as conn:
        print("Applying RLS helpers...")
        await conn.execute(text(CREATE_HELPERS_SQL))

        print("Discovering tenant tables (with tenant_id column)...")
        tables = await _fetch_tenant_tables(conn)
        if not tables:
            print("No tenant-aware tables found. Nothing to do.")
            return

        for fqtn in tables:
            print(f"Enabling RLS and policies on {fqtn} ...")
            # Enable RLS
            await conn.execute(text(f"ALTER TABLE {fqtn} ENABLE ROW LEVEL SECURITY"))

            # Create policies (idempotent via IF NOT EXISTS is not supported for policies in old PG; use DO blocks)
            policy_sql = f"""
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE schemaname = split_part('{fqtn}', '.', 1)
          AND tablename = split_part('{fqtn}', '.', 2)
          AND policyname = 'tenant_isolation_select'
    ) THEN
        EXECUTE 'CREATE POLICY tenant_isolation_select ON {fqtn} FOR SELECT USING (check_tenant_access(tenant_id))';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE schemaname = split_part('{fqtn}', '.', 1)
          AND tablename = split_part('{fqtn}', '.', 2)
          AND policyname = 'tenant_isolation_insert'
    ) THEN
        EXECUTE 'CREATE POLICY tenant_isolation_insert ON {fqtn} FOR INSERT WITH CHECK (check_tenant_access(tenant_id))';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE schemaname = split_part('{fqtn}', '.', 1)
          AND tablename = split_part('{fqtn}', '.', 2)
          AND policyname = 'tenant_isolation_update'
    ) THEN
        EXECUTE 'CREATE POLICY tenant_isolation_update ON {fqtn} FOR UPDATE USING (check_tenant_access(tenant_id)) WITH CHECK (check_tenant_access(tenant_id))';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE schemaname = split_part('{fqtn}', '.', 1)
          AND tablename = split_part('{fqtn}', '.', 2)
          AND policyname = 'tenant_isolation_delete'
    ) THEN
        EXECUTE 'CREATE POLICY tenant_isolation_delete ON {fqtn} FOR DELETE USING (check_tenant_access(tenant_id))';
    END IF;
END$$;
"""
            await conn.execute(text(policy_sql))

    await engine.dispose()
    print("✅ RLS setup complete.")


if __name__ == "__main__":
    asyncio.run(apply_rls())

