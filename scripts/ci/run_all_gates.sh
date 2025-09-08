#!/usr/bin/env bash
set -euo pipefail

echo "[ci] Running Gates A and B in local venv"

bash scripts/ci/venv_bootstrap.sh
bash scripts/ci/gate_a_core.sh

# Gate B (DB) is optional if Docker not available
if command -v docker >/dev/null 2>&1; then
  bash scripts/ci/gate_b_db.sh
else
  echo "[ci] Docker not found; skipping Gate B (DB migrations)"
fi

# Gate C (Frontend)
if command -v pnpm >/dev/null 2>&1 && [ -d frontend ]; then
  bash scripts/ci/gate_c_frontend.sh
else
  echo "[ci] Skipping Gate C (Frontend): pnpm or frontend/ missing"
fi

# Gate D (Containers)
if command -v docker >/dev/null 2>&1; then
  bash scripts/ci/gate_d_containers.sh
else
  echo "[ci] Skipping Gate D (Containers): docker not available"
fi

echo "[ci] Done"
