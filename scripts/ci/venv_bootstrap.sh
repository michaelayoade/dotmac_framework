#!/usr/bin/env bash
set -euo pipefail

VENV_DIR=".venv-ci"
REQ_FILE=".dev-artifacts/ci/requirements.txt"

echo "[ci] Bootstrapping local CI venv at ${VENV_DIR}"

if [ ! -d "${VENV_DIR}" ]; then
  python3 -m venv "${VENV_DIR}"
fi

source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip setuptools wheel

if [ -f "${REQ_FILE}" ]; then
  python -m pip install -r "${REQ_FILE}"
else
  echo "[ci] Requirements file not found: ${REQ_FILE}" >&2
  exit 1
fi

echo "[ci] Venv ready. To use: source ${VENV_DIR}/bin/activate"

