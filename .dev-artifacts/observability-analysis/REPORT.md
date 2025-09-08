Overview

- Codebase includes multiple observability stacks and docs: SigNoz/OTEL configs, unified metrics endpoints, dashboard provisioning, and several environment templates.
- Primary implementation appears under `packages/dotmac-platform-services/src/dotmac/platform/observability` with wrappers at `packages/dotmac-platform-services/src/dotmac/observability`.
- Management and ISP apps wire observability directly and via `src/dotmac_shared/application/observability_setup.py`.

Key Findings

1) Broken config API between config.py and bootstrap/__init__
- Expected by imports: `ExporterType`, `ExporterConfig`, `MetricsConfig`, `DashboardConfig`, `create_default_config`, `create_metrics_config`, `create_dashboard_config`.
- Actual file (`.../observability/config.py`) only defines `Environment`, a simplified `OTelConfig`, and `create_otel_config`.
- Impact: `from dotmac.platform.observability import create_default_config` resolves to `None` (graceful fallback), so calls like `create_default_config(...)` in:
  - `src/dotmac_management/main.py`
  - `src/dotmac_isp/app.py`
  - `src/dotmac_shared/application/observability_setup.py`
  will raise at runtime (`'NoneType' object is not callable`).
- Bootstrap (`bootstrap.py`) imports `ExporterConfig`, `ExporterType`, `OTelConfig` from config and expects `config.tracing_exporters`/`metrics_exporters` to be lists of ExporterConfig, not strings. Current config does not satisfy this.

2) Invalid exporter specification in app wiring
- In `src/dotmac_management/main.py`, `create_default_config(..., tracing_exporters=["otlp", "prometheus"], metrics_exporters=["otlp", "prometheus"])` includes `prometheus` in tracing exporters. Prometheus is a metrics exporter; tracing exporters should be `console|otlp|jaeger`.
- Similar manual overrides are used in `src/dotmac_shared/application/observability_setup.py` (assigning string lists), which will also mismatch a typed ExporterConfig list unless normalized.

3) Health/metrics API mismatch
- `observability_setup.py` logs `len(metrics_registry.metric_definitions)` but `MetricsRegistry` exposes `_metrics` plus helpers like `list_metrics()` and `get_metrics_info()`. There is no `metric_definitions` attribute.
- Impact: AttributeError during setup logging/health checks.

4) Fragmented modules and silent fallbacks mask errors
- There are three layers:
  - `dotmac.platform.observability` (real implementation)
  - `dotmac.observability` (compatibility wrapper)
  - `dotmac_shared` references to `.observability` packages that don’t exist under `src/dotmac_shared/observability`
- `__init__.py` in several packages swallows ImportError and sets symbols to `None`, allowing imports to “succeed” but fail later at runtime when called. This makes failures harder to notice.

5) Metrics namespacing inconsistency
- Docs and management `/metrics` endpoint use `dotmac_*` names for business metrics.
- Default metrics in `MetricsRegistry` are generic (`http_requests_total`, `system_memory_usage_bytes`, etc.).
- Not necessarily a hard bug, but it complicates alerting/Dashboards if expecting a consistent `dotmac_` prefix.

6) Grafana vs SigNoz divergence
- `SIGNOZ_OBSERVABILITY_SUMMARY.md` states Grafana components were removed and Signoz-only is the target.
- Code still provisions “Grafana dashboards” in `observability_setup.setup_platform_dashboards` log lines and uses a dashboard manager referencing Grafana/Signoz.
- This may be intentional dual support but should align with the chosen platform to avoid confusion.

7) Env/config sprawl
- Multiple overlapping env files: `.env.observability.example`, `.env.signoz`, `.env.production.observability`, etc. Values/vars don’t always line up with code’s expectations, increasing misconfiguration risk.

Prioritized Fix Plan

P0 — Make system boot without runtime errors
- Implement the expected API in `.../observability/config.py`:
  - Add `ExporterType`, `ExporterConfig` models.
  - Expand `OTelConfig` to include `enable_tracing`, `enable_metrics`, `trace_sampler_ratio`, exporter batch/time settings, and a `get_resource()` helper.
  - Add `create_default_config` (and simple `create_metrics_config`/`create_dashboard_config` shims) that produce lists of `ExporterConfig`, mapping strings like `"otlp"|"console"|"jaeger"|"prometheus"` to proper types and endpoints.
  - Normalize string lists to `ExporterConfig` via pydantic validators so existing assignment patterns continue to work.
- Update `observability_setup.py` logging to use `len(metrics_registry.list_metrics())` or `len(metrics_registry.get_metrics_info())` instead of non-existent `metric_definitions`.
- Sanitize tracing exporter overrides in app code (ignore or warn on `prometheus` in tracing exporters).

P1 — Reduce fragmentation and confusion
- Decide a single import surface for app teams: either use `dotmac.platform.observability` everywhere (preferred) and keep `dotmac.observability` as a thin, tested shim; or update shared code to the platform package explicitly.
- Remove dead references to `src/dotmac_shared/observability` or add that package only if it wraps the platform implementation.

P2 — Improve coherence and defaults
- Adopt consistent metric name prefixes (e.g., `dotmac_http_requests_total`) or add a registry-level option to prefix default metrics.
- Align dashboard provisioning logs and behavior to SigNoz-only if that’s the decided direction (or explicitly maintain dual mode via env flag).
- Consolidate env examples and document which to use locally vs production.

Concrete Changes Proposed (small, high-impact)

- Add missing config API and converters in `.../observability/config.py` to satisfy `__init__` and `bootstrap.py` without touching calling sites.
- Fix metrics count logging in `observability_setup.py` to use supported registry methods.
- In `create_default_config`, drop `prometheus` from tracing exporters automatically and log a warning when found.

Validation Steps

- Run unit tests that import `dotmac.platform.observability` and `dotmac.observability` to ensure imports no longer return `None` for config helpers.
- Start management/ISP apps and hit `/metrics`; verify it renders without exceptions and includes both default and business metrics.
- If SigNoz is running, verify OTLP export attempts (or console exporters in dev) without import errors.

Open Questions

- Should we enforce a single observability stack (SigNoz-only) now, and remove Grafana references entirely, or keep dual support behind a flag?
- Do we want to add a metrics prefix setting to `MetricsRegistry` to normalize names?

