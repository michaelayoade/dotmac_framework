#!/usr/bin/env python3
"""
Relocate previously inserted B008 fix blocks to the top of function bodies.

Looks for patterns like:
    if <param> is None:
        <param> = <call>()

that appear after the first non-docstring statement and moves them so they
appear immediately after the docstring (or at the start of the function body).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Cut:
    start: int
    end: int
    text: str


def line_starts(src: str) -> list[int]:
    starts = [0]
    idx = 0
    while True:
        i = src.find("\n", idx)
        if i == -1:
            break
        starts.append(i + 1)
        idx = i + 1
    return starts


def offset(lines: list[int], lineno: int, col: int) -> int:
    return lines[lineno - 1] + col


def node_span(lines: list[int], node: ast.AST) -> tuple[int, int]:
    return offset(lines, node.lineno, node.col_offset), offset(lines, node.end_lineno, node.end_col_offset)  # type: ignore[attr-defined]


def is_simple_param_is_none_if(node: ast.If) -> str | None:
    # Matches: if <name> is None: <newline> <indent><name> = <call>
    test = node.test
    if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Is) and len(test.comparators) == 1):
        return None
    left = test.left
    right = test.comparators[0]
    if not (isinstance(left, ast.Name) and isinstance(right, ast.Constant) and right.value is None):
        return None

    # Body must be a single assignment to the same name, with Call value
    if len(node.body) != 1 or not isinstance(node.body[0], ast.Assign):
        return None
    assign = node.body[0]
    if len(assign.targets) != 1 or not isinstance(assign.targets[0], ast.Name):
        return None
    if assign.targets[0].id != left.id:
        return None
    if not isinstance(assign.value, ast.Call):
        return None
    return left.id


def process_file(path: Path) -> bool:
    try:
        src = path.read_text(encoding="utf-8")
    except Exception:
        return False
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False

    lines = line_starts(src)
    edits: list[tuple[int, int, str]] = []  # replacements

    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = fn.body
        if not body:
            continue

        # Determine insertion point at top of body (after docstring if present)
        insert_before_stmt = None
        for stmt in body:
            if isinstance(stmt, ast.Expr) and isinstance(getattr(stmt, "value", None), ast.Constant) and isinstance(stmt.value.value, str):
                continue
            insert_before_stmt = stmt
            break
        if insert_before_stmt is None:
            continue

        insert_pos = offset(lines, insert_before_stmt.lineno, insert_before_stmt.col_offset)

        # Collect simple if-blocks to move that appear after the first real statement
        cuts: list[Cut] = []
        for stmt in body:
            if stmt is insert_before_stmt:
                continue
            if isinstance(stmt, ast.If):
                pname = is_simple_param_is_none_if(stmt)
                if pname:
                    s, e = node_span(lines, stmt)
                    cuts.append(Cut(start=s, end=e, text=src[s:e]))

        if not cuts:
            continue

        # Build combined text to insert
        combined = "".join(c.text + "\n" if not c.text.endswith("\n") else c.text for c in cuts)

        # Remove original blocks and insert at top. Apply cuts from end to start.
        new_src = src
        for c in sorted(cuts, key=lambda c: c.start, reverse=True):
            new_src = new_src[:c.start] + new_src[c.end:]
        new_src = new_src[:insert_pos] + combined + new_src[insert_pos:]
        src = new_src
        lines = line_starts(src)

    # Write if changes happened
    if path.read_text(encoding="utf-8") != src:
        path.write_text(src, encoding="utf-8")
        return True
    return False


def main() -> int:
    root = Path.cwd()
    skip = {".git", "venv", ".venv", "node_modules", "build", "dist", "__pycache__"}
    changed = 0
    for p in root.rglob("*.py"):
        if any(part in skip for part in p.parts):
            continue
        if process_file(p):
            changed += 1
    print(f"Relocated B008 blocks in {changed} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
