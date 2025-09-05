"""
Test helper: extend sys.path to include local packages/*/src during test runs.

Having this file at repo root ensures Python imports it on startup, allowing
pytest and other tools to resolve names like `dotmac` from local packages.
"""

from __future__ import annotations

import glob
import os
import sys


def _add_package_src_paths() -> None:
    repo_root = os.path.dirname(__file__)
    patterns = [
        os.path.join(repo_root, "packages", "*", "src"),
        os.path.join(repo_root, "packages", "*", "*", "src"),
    ]
    for pattern in patterns:
        for path in glob.glob(pattern):
            if os.path.isdir(path) and path not in sys.path:
                sys.path.insert(0, path)


_add_package_src_paths()
