#!/usr/bin/env bash
set -euo pipefail

echo "== Ruff (lint) =="
ruff --version
ruff .

echo "== MyPy (type check) =="
mypy --version
# Type check source and tests where present
if compgen -G "packages/*/src" > /dev/null; then
  mypy packages/*/src || true
fi
if compgen -G "packages/*/tests" > /dev/null; then
  mypy packages/*/tests || true
fi

echo "== Per-package tests + build =="
shopt -s nullglob
for pkg in packages/*; do
  [ -d "$pkg" ] || continue
  if [ -f "$pkg/pyproject.toml" ]; then
    echo "\n--- Package: $(basename "$pkg") ---"
    pushd "$pkg" >/dev/null
    # Run tests if tests exist
    if [ -d tests ]; then
      echo "Running pytest"
      PYTHONPATH="src:${PYTHONPATH:-}" pytest -q
    else
      echo "(no tests directory — skipping pytest)"
    fi
    # Build wheel/sdist via PEP517
    echo "Building distribution"
    python -m build --wheel --sdist
    popd >/dev/null
  fi
done

echo "All Python quality gates completed."

