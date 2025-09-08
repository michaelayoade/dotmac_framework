#!/usr/bin/env bash
set -euo pipefail

echo "[gate C] Frontend checks (type-check, lint, unit, build)"

if ! command -v pnpm >/dev/null 2>&1; then
  echo "[gate C] pnpm not found. Install pnpm to run frontend gate." >&2
  exit 1
fi

if [ ! -d frontend ]; then
  echo "[gate C] frontend/ directory not found. Skipping." >&2
  exit 0
fi

STATUS=0

echo "[gate C] pnpm install (frozen lockfile)"
pnpm -C frontend install --frozen-lockfile || STATUS=1

echo "[gate C] type-check"
pnpm -C frontend run type-check || STATUS=1

echo "[gate C] lint:ci"
pnpm -C frontend run lint:ci || STATUS=1

if pnpm -C frontend run | grep -qi "test:unit"; then
  echo "[gate C] test:unit"
  pnpm -C frontend run test:unit || STATUS=1
else
  echo "[gate C] (no test:unit script defined)"
fi

echo "[gate C] build"
pnpm -C frontend run build || STATUS=1

if [ "$STATUS" -ne 0 ]; then
  echo "[gate C] FAIL: Frontend gate failed" >&2
  exit 1
fi

echo "[gate C] PASS: Frontend gate completed"

