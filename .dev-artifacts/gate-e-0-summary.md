# Gate E-0 (Infra Layers) – Current Status and Next Actions

This document summarizes the dependency-layered bring-up for Gate E-0 (secrets, DB/cache, observability), what is working, what is not, and concrete next steps.

## Overview

- Layering approach validated:
  1) E-0a OpenBao (secrets) → 2) E-0b Database/Cache → 3) E-0c Observability
- Each layer validates connectivity to previous layers before proceeding.

## Layer Status

- ✅ E-0a OpenBao
  - API reachable; root token auth works.
  - Secrets fetch tested from E-0b.

- ✅ E-0b Database/Cache
  - PostgreSQL up with test schema; basic query works.
  - Redis up; SET/GET verified; connection from E-0a/E-0c OK.

- 🔄 E-0c Observability (SigNoz + ClickHouse + OTEL Collector)
  - ClickHouse healthy (host + in-network checks pass).
  - Query-service and OTEL collector were restarting due to two issues:
    1) SQLite path missing (resolved by mounting `/var/lib/signoz`).
    2) Query-service attempting to connect to `localhost:9000` instead of `clickhouse:9000`.

## What We Fixed

- Added ClickHouse DB initializer to pre-create DBs:
  - `signoz_traces`, `signoz_metrics`, `signoz_logs` before query/collector start.
- Added persistent volume for query-service SQLite path: `/var/lib/signoz`.
- Set multiple explicit ClickHouse connection env vars on query-service:
  - `CLICKHOUSE_HOST=clickhouse`, `CLICKHOUSE_PORT=9000`,
  - `CLICKHOUSE_ADDRESS=clickhouse:9000`, `CLICKHOUSE_ADDR=clickhouse:9000`,
  - `CLICKHOUSE_DSN=tcp://clickhouse:9000?database=signoz_traces`.

## Current Blocker (E-0c)

- Query-service log shows: “Using ClickHouse as datastore”, but it still attempts to connect to `localhost:9000`.
- ClickHouse is accessible on the Docker network as `clickhouse:9000` (validated from a throwaway container), so the issue is config resolution inside query-service.

## Hypotheses

1) Query-service image version expects a specific env var precedence or an internal config file overrides envs.
2) The service parses a single DSN (e.g., `CLICKHOUSE_DSN`/`DATABASE_DSN`) and ignores host/port when DSN is missing or malformed.
3) Older/newer builds of query-service may use a different variable name (e.g., `CLICKHOUSE_URL`).

## Next Actions (Low-Risk)

1) Add an explicit DSN env only (minimal set):
   - `CLICKHOUSE_DSN=tcp://clickhouse:9000?database=signoz_traces` (keep user/pass empty as default)
   - Remove conflicting host/port if the service prioritizes DSN.

2) If still falling back to localhost, mount a small config to override:
   - Provide a config file (e.g., `/etc/signoz/query/config.yaml`) that sets ClickHouse address to `clickhouse:9000` and mount it read-only, then set env `QUERY_CONFIG_PATH=/etc/signoz/query/config.yaml` (exact key name may differ by version; consult query-service docs for the version in use).

3) Confirm env ingestion inside the running container:
   - `docker exec -it gate-e-signoz-query env | grep -i clickhouse`
   - This ensures the expected variables are present in the process environment.

4) Sanity test from within query-service container:
   - `docker exec -it gate-e-signoz-query sh -lc "clickhouse-client -h clickhouse -q 'SELECT 1'"`
   - If the client isn’t present, use netcat: `nc -z clickhouse 9000 && echo ok || echo fail`.

## Validation Script Output (Context)

- `validate-gate-e-0c.sh` indicates E-0a/E-0b connectivity OK, but waits for observability readiness. This aligns with query-service still restarting due to ClickHouse address parsing.

## Commands to Recreate/Validate

1) Recreate only observability services after changes:
```
docker compose -f .dev-artifacts/gate-e/docker-compose.gate-e.yml up -d --force-recreate clickhouse clickhouse-init signoz-query otel-collector
```

2) Watch logs:
```
docker logs -f gate-e-signoz-query
docker logs -f gate-e-otel-collector
```

3) Health checks:
```
curl -sf http://localhost:8080/api/v1/health
```

## Decision Points

- If we want E-0c fast/stable in CI, split into:
  - E-0c-core: OTEL Collector only (no SigNoz/ClickHouse), metrics/traces sent to console/Prom.
  - E-0c-full: Full SigNoz + ClickHouse; run on a nightly or extended pipeline.

## Summary

- The dependency-based startup works for E-0a/E-0b and most of E-0c.
- Remaining work: ensure query-service ingests Docker network hostname for ClickHouse (prefer DSN) and avoids `localhost` fallback.
- Once resolved, Gate E-0c should transition from restarting to healthy, unblocking downstream Gate E tests.

