#!/usr/bin/env bash
set -euo pipefail

VENV_DIR=".venv-ci"

if [ ! -d "${VENV_DIR}" ]; then
  echo "[gate A] venv not found. Run scripts/ci/venv_bootstrap.sh first." >&2
  exit 1
fi
source "${VENV_DIR}/bin/activate"

echo "[gate A] Running Core Quality checks"

STATUS=0

run_python_checks() {
  local target="$1"
  echo "[gate A] >>> ${target}"

  if [ -f "${target}/pyproject.toml" ]; then
    echo "[gate A] Install editable: ${target}"
    python -m pip install -e "${target}" || STATUS=1
  fi

  # Tests
  if rg -q "^def test_" -n "${target}" --glob '!**/__pycache__/**' --glob '!**/.venv*/**' 2>/dev/null; then
    echo "[gate A] pytest: ${target}"
    pytest -q "${target}" || STATUS=1
  else
    echo "[gate A] (no tests found in ${target})"
  fi

  # Types
  echo "[gate A] mypy: ${target}"
  mypy "${target}" || STATUS=1

  # Lint
  echo "[gate A] ruff: ${target}"
  ruff check "${target}" || STATUS=1

  # Build (package dirs only)
  if [ -f "${target}/pyproject.toml" ]; then
    echo "[gate A] build: ${target}"
    (cd "${target}" && python -m build) || STATUS=1
  fi
}

# 1) packages/*
if [ -d packages ]; then
  while IFS= read -r -d '' pkg; do
    run_python_checks "$pkg"
  done < <(find packages -maxdepth 2 -type f -name pyproject.toml -print0 | xargs -0 -n1 dirname -z)
fi

# 2) src/dotmac_shared/* (treat as monorepo src)
if [ -d src/dotmac_shared ]; then
  run_python_checks "src/dotmac_shared"
fi

# Security scans (Python)
echo "[gate A] Security: bandit"
bandit -r src packages -q || echo "[gate A] Bandit reported issues (review output)"

echo "[gate A] Security: pip-audit"
REPORT_DIR=".dev-artifacts/ci/reports"
mkdir -p "$REPORT_DIR"
# Audit installed environment (venv) and export JSON report
pip-audit --format json -o "$REPORT_DIR/python_pip_audit.json" \
  || echo "[gate A] pip-audit reported vulnerabilities (review output)"

# Optional: audit requirements if present
if [ -f requirements.txt ]; then
  pip-audit -r requirements.txt --format json -o "$REPORT_DIR/python_req_audit.json" \
    || echo "[gate A] pip-audit (requirements) reported vulnerabilities"
fi

# Node-side security checks (frontend)
if command -v pnpm >/dev/null 2>&1 && [ -d frontend ]; then
  echo "[gate A] Node Security: pnpm audit"
  # Using --prod to avoid dev-only noise in CI; adjust as needed
  pnpm -C frontend audit --prod --json > "$REPORT_DIR/frontend_pnpm_audit.json" \
    || echo "[gate A] pnpm audit found issues (review $REPORT_DIR/frontend_pnpm_audit.json)"
else
  echo "[gate A] Skipping pnpm audit (pnpm or frontend/ missing)"
fi

if [ "$STATUS" -ne 0 ]; then
  echo "[gate A] FAIL: One or more checks failed" >&2
  exit 1
fi

echo "[gate A] PASS: Core Quality checks completed"
