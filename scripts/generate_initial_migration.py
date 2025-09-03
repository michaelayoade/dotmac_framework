#!/usr/bin/env python3
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

Generate initial Alembic migration from models (autogenerate).

Usage:
  python scripts/generate_initial_migration.py "initial schema"

Creates a new revision under alembic/versions with autogenerate enabled.
Requires that DATABASE_URL is set or alembic.ini has a valid sqlalchemy.url.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    message = sys.argv[1] if len(sys.argv) > 1 else "initial schema"

    cfg = Config(str(repo_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(repo_root / "alembic"))

    # Prefer env var for DATABASE_URL
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        cfg.set_main_option("sqlalchemy.url", db_url)

    # Generate revision with autogenerate
    command.revision(cfg, message=message, autogenerate=True)
    print("✅ Generated autogenerate revision for:", message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

