# Production Baseline Checklist

This baseline must be satisfied in production environments to ensure security and reliability.

## Environment Requirements
- ENVIRONMENT=production
- STRICT_PROD_BASELINE=true (to enable runtime enforcement)
- OPENBAO_URL, OPENBAO_TOKEN configured (secrets provider)
- DATABASE_URL points to Postgres (not sqlite)
- REDIS_URL present for durable background ops, WS, and caching
- APPLY_RLS_AFTER_MIGRATION=true (or ensure RLS is enabled post-migrations)

## App Startup Guard (Management + ISP)
At startup, apps verify the above conditions unless ALLOW_INSECURE_PROD=true is set (for emergency use only).

## Observability
- OTEL exporters (OTLP) active; `/metrics` exposed
- Signoz dashboards deployed (Grafana deprecated)

## Gateway
- Nginx tenant header extraction enabled; per-tenant rate limiting active
- (Optional) JWT validation at edge for sensitive endpoints

## Background Ops
- Redis available; idempotency + saga durability enabled
- DLQ monitoring configured

## RLS
- RLS policies applied post-migration; policies verified in CI/staging

## Smoke Tests
- Run `make smoke` with proper env settings after deploy
