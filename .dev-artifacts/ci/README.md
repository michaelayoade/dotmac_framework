CI/CD Local Venv Runner

This directory contains scripts to create an isolated Python virtual environment
and run CI gates locally, mirroring container/CI commands as closely as
possible.

Quick start

1) Create venv and install tools
   bash scripts/ci/venv_bootstrap.sh

2) Run Core Quality gate (Gate A)
   bash scripts/ci/gate_a_core.sh

3) Run DB + Migrations gate (Gate B)
   bash scripts/ci/gate_b_db.sh

4) Run all scripted gates (incrementally extendable)
   bash scripts/ci/run_all_gates.sh

Environment

- The venv lives at .venv-ci.
- Tooling versions are pinned in .dev-artifacts/ci/requirements.txt.

Notes

- Gate B uses Docker for ephemeral Postgres. If Docker is not available, the
  script prints explicit next steps and exits with non‑zero status.
- Frontend/containers gates are not included here yet; they can be added in the
  same pattern once your environment is ready.

