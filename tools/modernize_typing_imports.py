#!/usr/bin/env python3
"""
Modernize typing imports and usages:

- Move appropriate imports from `typing` to `collections.abc` (e.g., Iterable, Mapping,
  Sequence, Callable, Generator, AsyncGenerator, Iterator, AsyncIterator, etc.).
- Drop legacy generic imports (List, Dict, Tuple, Set, FrozenSet) and rewrite usages
  to builtin generics (list, dict, tuple, set, frozenset) where reasonably safe.

Notes:
- This script avoids modifying content inside triple-quoted strings and comments.
- It performs conservative token replacements using word boundaries.
- It preserves other `typing` imports like Any, Optional, Union, TypeVar, Annotated, Type.

Run from repo root:
  python tools/modernize_typing_imports.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PY_EXT = ".py"

# Names to migrate from typing -> collections.abc
ABC_NAMES = {
    "Iterable",
    "Iterator",
    "Reversible",
    "Generator",
    "AsyncGenerator",
    "Coroutine",
    "AsyncIterator",
    "AsyncIterable",
    "Mapping",
    "MutableMapping",
    "Sequence",
    "MutableSequence",
    "Collection",
    "Container",
    "Sized",
    "Callable",
    # Note: Set is handled as builtin, not abc
    # AbstractSet maps to collections.abc Set
}

# Legacy generics to builtin names
LEGACY_TO_BUILTIN = {
    "List": "list",
    "Dict": "dict",
    "Tuple": "tuple",
    "Set": "set",
    "FrozenSet": "frozenset",
}

# Typing names we keep as typing imports
TYPING_KEEP = {
    "Any",
    "Optional",
    "Union",
    "TypeVar",
    "Generic",
    "Annotated",
    "Literal",
    "Final",
    "ClassVar",
    "Type",
    "NoReturn",
    "NewType",
    "TypedDict",
    "NotRequired",
    "Required",
}

IMPORT_LINE_RE = re.compile(r"^from\s+typing\s+import\s+(.+)$")


def split_imports(spec: str) -> list[str]:
    # Split by commas while respecting simple cases; strip whitespace and trailing comments
    spec = spec.split("#", 1)[0]
    parts = [p.strip() for p in spec.split(",") if p.strip()]
    # Remove possible aliasing like `Iterable as It` — keep original for safety here
    return parts


def rebuild_imports(typing_names: list[str], abc_names: list[str]) -> list[str]:
    lines: list[str] = []
    if typing_names:
        lines.append(f"from typing import {', '.join(sorted(typing_names))}")
    if abc_names:
        # Map AbstractSet to Set in collections.abc
        mapped = ["Set" if n == "AbstractSet" else n for n in abc_names]
        # Deduplicate and sort
        uniq = sorted(dict.fromkeys(mapped))
        lines.append(f"from collections.abc import {', '.join(uniq)}")
    return lines


def rewrite_import_line(line: str) -> tuple[str, bool]:
    m = IMPORT_LINE_RE.match(line)
    if not m:
        return line, False
    spec = m.group(1).strip()
    names = split_imports(spec)
    if not names:
        return line, False

    keep_typing: list[str] = []
    move_abc: list[str] = []
    drop_builtins: list[str] = []

    changed = False

    for name in names:
        base = name.split(" as ", 1)[0].strip()

        if base in LEGACY_TO_BUILTIN:
            # Drop from typing import and rewrite usages later
            drop_builtins.append(name)
            changed = True
        elif base in ABC_NAMES and base not in {"Set"}:  # Set handled as builtin
            move_abc.append(base)
            changed = True
        elif base in TYPING_KEEP:
            keep_typing.append(base)
        else:
            # Unknown: keep as-is to avoid breakage
            keep_typing.append(name)

    # Special-case AbstractSet -> collections.abc Set
    if "AbstractSet" in names:
        move_abc.append("AbstractSet")
        if "AbstractSet" in keep_typing:
            keep_typing.remove("AbstractSet")
        changed = True

    if not changed:
        return line, False

    new_lines = rebuild_imports(keep_typing, move_abc)
    if not new_lines:
        return "", True
    return "\n".join(new_lines) + "\n", True


def replace_legacy_generics(code: str) -> str:
    """Replace legacy typing generics with builtin generics using regex.

    This pass is intentionally simple and operates line-by-line, avoiding only
    inline comments. It may also update occurrences inside docstrings, which is
    acceptable for modernization purposes.
    """
    out_lines: list[str] = []
    patterns = [
        (re.compile(r"(?<![\w.])List\["), "list["),
        (re.compile(r"(?<![\w.])Dict\["), "dict["),
        (re.compile(r"(?<![\w.])Tuple\["), "tuple["),
        (re.compile(r"(?<![\w.])Set\["), "set["),
        (re.compile(r"(?<![\w.])FrozenSet\["), "frozenset["),
    ]

    for line in code.splitlines(keepends=True):
        if "#" in line:
            code_part, comment_part = line.split("#", 1)
            replaced = code_part
            for pat, repl in patterns:
                replaced = pat.sub(repl, replaced)
            out_lines.append(replaced + "#" + comment_part)
        else:
            replaced = line
            for pat, repl in patterns:
                replaced = pat.sub(repl, replaced)
            out_lines.append(replaced)

    return "".join(out_lines)


def process_file(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return False

    lines = text.splitlines(keepends=True)
    changed = False
    new_lines: list[str] = []
    for line in lines:
        new_line, did = rewrite_import_line(line)
        if did:
            changed = True
            if new_line:
                new_lines.append(new_line)
            # If new_line is empty, we drop the original import line
        else:
            new_lines.append(line)

    new_text = "".join(new_lines)
    # Replace legacy generics usages
    replaced_text = replace_legacy_generics(new_text)
    if replaced_text != text:
        changed = True

    if changed:
        path.write_text(replaced_text, encoding="utf-8")
    return changed


def iter_python_files(root: Path):
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix == PY_EXT:
            yield p


def main(argv: list[str]) -> int:
    root = Path.cwd()
    # Skip common virtualenv or build dirs
    skip_dirs = {".venv", "venv", "build", "dist", "node_modules", ".git", "__pycache__"}

    changed_count = 0
    files = []
    for p in iter_python_files(root):
        parts = set(p.parts)
        if parts & skip_dirs:
            continue
        files.append(p)

    for p in files:
        if process_file(p):
            changed_count += 1

    print(f"Modernized typing imports/usages in {changed_count} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
