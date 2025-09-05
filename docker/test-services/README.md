# DotMac Test Services (Deprecated)

The standalone Docker-based test services for notifications and file storage have been removed.

What changed
- Removed images and compose stacks for notification/file-storage testers.
- Tests now rely on internal mocks, unit/integration suites, or external providers configured by environment.

How to test now
- Use the regular test runner: `python scripts/run_comprehensive_tests.py --quick`.
- For SMTP/SMS, prefer mocked adapters in integration tests or point to your own sandbox services via env vars.

Why
- Reduce maintenance burden and optional dependency surface.
- Avoid pulling unused images and services in CI.

If you need these again
- Reintroduce targeted test containers in a separate repo or local compose files.
