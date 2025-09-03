# On-Call Runbook – DotMac Platform

This runbook outlines quick checks and actions to triage common production issues across the Management Platform and ISP Tenant Containers.

## Quick Links
- Management Admin: `${ADMIN_BASE_URL}`
- Reseller Portal: `${RESELLER_BASE_URL}`
- Tenant Portal: `${TENANT_BASE_URL}`
- Management API: `${MGMT_API_URL}`

## 1) Smoke Test (5–10 min)
- Env vars: `ADMIN_BASE_URL`, `RESELLER_BASE_URL`, `TENANT_BASE_URL`, `MGMT_API_URL`, `TENANT_SLUG`, `API_VERSION`.
- Run: `make smoke`
- Checks performed:
  - `/health` endpoints
  - `/api/health/client-check` with tenant and API version headers
  - `/metrics` exposure (Mgmt API)
  - `bgops` inspection endpoint

## 2) Health & Readiness
- Endpoints:
  - Liveness: `/health/live`
  - Readiness: `/health/ready`
  - Startup: `/health/startup`
- If readiness fails:
  - Inspect logs for DB/Redis/connectivity.
  - Confirm secrets resolved via OpenBao/Vault.
  - Verify Nginx upstreams are reachable and tenant header mapping is active.

## 3) Authentication & Tokens
- Symptoms: 401/403, frequent session drops.
- Actions:
  - Validate refresh via admin/reseller refresh routes.
  - Ensure `JWT_SECRET` and service signing secrets are present in Vault.
  - Check time skew between services (<5 minutes).

## 4) Tenant Isolation & RLS
- Symptoms: cross-tenant data, 403 gateway tenant mismatch.
- Actions:
  - Run RLS setup if necessary: `make setup-rls` with `DATABASE_URL` set.
  - Confirm tenant header mapping in Nginx and app logs for “Tenant resolved”.
  - Check `bgops` and saga logs for operations targeting wrong tenant.

## 5) Background Operations (Idempotency/Sagas)
- List recent idempotency keys: `GET ${MGMT_API_URL}/api/v1/bgops/idempotency?limit=10`
- Inspect a specific key: `GET ${MGMT_API_URL}/api/v1/bgops/idempotency/{key}`
- Saga state/history:
  - `GET ${MGMT_API_URL}/api/v1/bgops/sagas/{saga_id}`
  - `GET ${MGMT_API_URL}/api/v1/bgops/sagas/{saga_id}/history`
- Redis keys (if needed): `bgops:idempo:*`, `bgops:saga:*`

## 6) Observability & Dashboards
- Confirm OTEL exporter is up and Signoz is receiving traces/metrics.
- `/metrics` includes business SLOs; ensure alerts are configured for provisioning latency, login success, and error rates.

## 7) API Gateway & Edge
- Rate limiting and DDoS: ensure Nginx limits and WS caps are in place.
- JWT at edge: enable when module is available; otherwise rely on app-level EdgeAuth.
- mTLS to upstream: optional but recommended for internal traffic.

## 8) Secrets Management
- Prod: All secrets must come from OpenBao/Vault; no env fallbacks.
- Rotation: Verify rotation policies for JWT and service tokens.

## 9) Rollback & Recovery
- Alembic: `alembic downgrade -1` (validate state before rollback).
- Containers: swap to last known good image and re-run `make smoke`.
- Data: for RLS or schema issues, disable new traffic, restore from last backup, reapply RLS policies.

## 10) Contact & Escalation
- Primary on-call: Platform SRE (Slack: #ops-oncall)
- Secondary: App Team Lead
- External dependencies: DNS/SSL provider, Cloud, Signoz maintainer

---

### Appendix: Env Template for Smoke Test
```
export ADMIN_BASE_URL=https://admin.example.com
export RESELLER_BASE_URL=https://reseller.example.com
export TENANT_BASE_URL=https://acme.isp.example.com
export MGMT_API_URL=https://api.example.com
export TENANT_SLUG=acme
export API_VERSION=v1
make smoke
```
