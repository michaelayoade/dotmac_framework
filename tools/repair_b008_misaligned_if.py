#!/usr/bin/env python3
"""
Repair misaligned "if <param> is None:" blocks introduced during B008 fixes.

Heuristic:
- Find lines that contain an "if ... is None:" but do not start with optional
  whitespace followed by "if" (i.e., there is stray text before "if").
- Rewrite the line to keep only indentation before the "if" token and the
  full "if ...:" part, dropping stray prefix text that precedes "if".
- Ensure the very next non-empty, non-comment line is indented at least one
  additional indent level (4 spaces) compared to the "if" line.

Run this only on files that fail to parse, but it is idempotent and safe.
"""

from __future__ import annotations

import ast
from pathlib import Path


def parse_ok(src: str) -> bool:
    try:
        ast.parse(src)
        return True
    except SyntaxError:
        return False


def repair_text(src: str) -> str:
    lines = src.splitlines(keepends=True)
    changed = False
    i = 0
    while i < len(lines):
        line = lines[i]
        # Find ' if ' occurrence and ' is None:' structure
        if ' is None' in line and 'if ' in line:
            stripped = line.lstrip()
            if stripped.startswith('if '):
                i += 1
                continue  # already aligned
            # Find the index where 'if' starts
            idx_if = line.find('if ')
            if idx_if > 0:
                # Determine indentation before 'if'
                # Find whitespace immediately preceding 'if'
                # but also ensure we start the line at beginning indentation block
                indent_start = 0
                while indent_start < len(line) and line[indent_start] == ' ':
                    indent_start += 1
                # Build new line: indentation up to idx_if, then the 'if ...' remainder
                indent = line[:idx_if]
                remainder = line[idx_if:]
                # Normalize indentation to spaces only
                indent = indent.replace('\t', '    ')
                lines[i] = indent + remainder
                changed = True

                # Ensure next non-empty/non-comment line is indented more
                # Find next content line index
                j = i + 1
                while j < len(lines):
                    nxt = lines[j]
                    if nxt.strip() == '' or nxt.lstrip().startswith('#'):
                        j += 1
                        continue
                    # Compute current and required indentation
                    if_indent = len(indent.expandtabs(4))
                    # Leading whitespace of next line
                    lead_ws_len = len(nxt) - len(nxt.lstrip(' \t'))
                    lead = nxt[:lead_ws_len]
                    lead_spaces = lead.expandtabs(4)
                    if len(lead_spaces) <= if_indent:
                        # Add one indent level (4 spaces) after the if-block
                        new_lead = ' ' * (if_indent + 4)
                        lines[j] = new_lead + nxt.lstrip(' \t')
                        changed = True
                    break
        i += 1

    return ''.join(lines) if changed else src


def process_file(p: Path) -> bool:
    try:
        src = p.read_text(encoding='utf-8')
    except Exception:
        return False
    if parse_ok(src):
        return False
    fixed = repair_text(src)
    if fixed != src and parse_ok(fixed):
        p.write_text(fixed, encoding='utf-8')
        return True
    # Write even if not parseable yet? No, leave for manual follow-ups
    if fixed != src:
        p.write_text(fixed, encoding='utf-8')
        return True
    return False


def main() -> int:
    root = Path('.')
    skip = {'.git', 'venv', '.venv', 'node_modules', 'build', 'dist', '__pycache__'}
    changed = 0
    for p in root.rglob('*.py'):
        if any(seg in p.parts for seg in skip):
            continue
        if process_file(p):
            changed += 1
    print(f"Repaired misaligned if-blocks in {changed} files.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

