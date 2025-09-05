#!/usr/bin/env python3
"""
Wrapper to enforce DRY patterns at push time.
- Reuses `tools/validate-service-standards.py` with --fail-on-warnings
- Does NOT depend on Poetry.
- Skips gracefully if `.service-standards.json` is missing.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]  # noqa: B008
    src_dir = repo_root / "src"
    standards_file = repo_root / ".service-standards.json"

    # Soft-skip if standards file doesn't exist yet
    if not standards_file.exists():
        print(
            "[DRY] Skipping enforcement: standards file not found at",
            standards_file,
        )
        return 0

    # Respect an enable/disable flag in the standards file
    try:
        data = json.loads(standards_file.read_text())
        enabled = bool(data.get("enabled", False))
    except Exception as e:
        print(f"[DRY] Skipping enforcement: failed to parse standards file: {e}")
        return 0
    if not enabled:
        print("[DRY] Skipping enforcement: standards 'enabled' is false")
        return 0

    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{src_dir}{os.pathsep}{existing}" if existing else str(src_dir)
    )

    cmd = [
        sys.executable,
        str(repo_root / "tools" / "validate-service-standards.py"),
        str(repo_root / "src"),
        "--standards",
        str(standards_file),
        "--fail-on-warnings",
    ]

    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if proc.stdout:
        print(proc.stdout, end="")
    if proc.returncode != 0 and proc.stderr:
        print(proc.stderr, file=sys.stderr, end="")

    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
