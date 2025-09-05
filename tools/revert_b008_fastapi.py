#!/usr/bin/env python3
"""
Revert B008-style body/query default moves for FastAPI parameters in unparseable files.

For each unparseable Python file, detect function signatures where parameters are set to
`= None` and, within the first ~40 lines of the function body, locate assignments of the form
    <param> = (Query|Body|Path|Header|Cookie|Depends)(...)
possibly preceded by `if <param> is None:`. Replace the signature default back to the call,
and remove the `if` and assignment lines.

Also perform a light repair to join split identifiers across lines when inside parentheses.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Optional


FASTAPI_CALLS = {"Query", "Body", "Path", "Header", "Cookie", "Depends"}


def parse_ok(text: str) -> bool:
    try:
        ast.parse(text)
        return True
    except SyntaxError:
        return False


def find_def_headers(text: str):
    # Yields (start_idx, end_idx, indent, header_text)
    out = []
    i = 0
    while True:
        m = re.search(r"^\s*(async\s+def|def)\s+\w+\s*\(", text[i:], re.M)
        if not m:
            break
        start = i + m.start()
        # Find header end at colon that ends the signature
        j = start
        paren = 0
        while j < len(text):
            ch = text[j]
            if ch == '(':
                paren += 1
            elif ch == ')':
                paren -= 1
            elif ch == ':' and paren == 0:
                j += 1
                break
            j += 1
        header_end = j
        header_text = text[start:header_end]
        # Indent of the def line
        line_start = text.rfind('\n', 0, start) + 1
        indent = text[line_start:start]
        out.append((start, header_end, indent, header_text))
        i = header_end
    return out


def extract_params_defaults(header_text: str):
    # Return mapping of param name -> (match_span_start, match_span_end)
    params = {}
    # Only handle simple "name: type = None" patterns
    for m in re.finditer(r"\b([A-Za-z_][A-Za-z_0-9]*)\s*:\s*[^=\)]+=\s*None\b", header_text):
        params[m.group(1)] = m.span()
    return params


def find_assignment_in_body(body_text: str, param: str) -> Optional[tuple[int, int, str]]:
    # Find '<param> = CallName(' with CallName in FASTAPI_CALLS, capture full RHS call text
    # including balanced parentheses.
    m = re.search(rf"^\s*{re.escape(param)}\s*=\s*([A-Za-z_][A-Za-z_0-9]*)\s*\(", body_text, re.M)
    if not m:
        return None
    call_name = m.group(1)
    if call_name not in FASTAPI_CALLS:
        return None
    start = m.start(1)  # start of call name
    # Extend to capture full call with balanced parentheses from the '(' following the name
    open_paren = body_text.find('(', start)
    idx = open_paren
    depth = 0
    while idx < len(body_text):
        ch = body_text[idx]
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                idx += 1
                break
        idx += 1
    end = idx
    # Expand to the whole assignment right-hand side from '=' to end
    eq_pos = body_text.rfind('=', 0, start) + 1
    rhs = body_text[eq_pos:end].strip()
    # Now find full assignment line span to remove, including preceding "if <param> is None:" if present
    # Find start of line for the 'if' if exists
    # Locate the line start of the assignment
    line_start = body_text.rfind('\n', 0, eq_pos) + 1
    removal_start = line_start
    # Check if the previous non-empty line is an 'if param is None:'
    prev_break = body_text.rfind('\n', 0, line_start - 1)
    if prev_break != -1:
        prev_line_start = body_text.rfind('\n', 0, prev_break) + 1
        prev_line = body_text[prev_break + 1:line_start]
        if re.search(rf"\bif\s+{re.escape(param)}\s+is\s+None\s*:\s*$", prev_line):
            removal_start = prev_line_start
    # Extend removal to end of the assignment line
    line_end = body_text.find('\n', end)
    if line_end == -1:
        line_end = len(body_text)
    removal_end = line_end
    return removal_start, removal_end, rhs


def join_split_identifiers(text: str) -> str:
    # Heuristic join for identifiers split across lines inside parentheses
    lines = text.splitlines(keepends=True)
    out = []
    depth = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        # update depth for parens on this line (rough heuristic, ignores strings)
        depth += line.count('(') - line.count(')')
        if i + 1 < len(lines) and depth > 0:
            # if line ends with identifier tail and next starts with identifier head
            if re.search(r"[A-Za-z_][A-Za-z_0-9]*\s*$", line) and re.match(r"\s*[A-Za-z_][A-Za-z_0-9]*", lines[i+1]):
                # join without newline
                joined = line.rstrip('\n') + lines[i+1].lstrip()
                out.append(joined)
                i += 2
                continue
        out.append(line)
        i += 1
    return ''.join(out)


def process_file(p: Path) -> bool:
    try:
        text = p.read_text(encoding='utf-8')
    except Exception:
        return False
    if parse_ok(text):
        return False
    original = text
    # Attempt join-split repair first
    text = join_split_identifiers(text)

    # Process function headers and revert defaults
    headers = find_def_headers(text)
    new_text = text
    offset = 0
    for start, end, indent, header in headers:
        # Compute updated positions in new_text
        start += offset
        end += offset
        header = new_text[start:end]
        params = extract_params_defaults(header)
        if not params:
            continue
        # Body immediately after ':'
        body_start = end
        # Grab next ~40 lines of body
        next_part_end = body_start
        for _ in range(40):
            nl = new_text.find('\n', next_part_end)
            if nl == -1:
                next_part_end = len(new_text)
                break
            next_part_end = nl + 1
        body_snippet = new_text[body_start:next_part_end]
        # Try to resolve each param
        for name, (ps, pe) in list(params.items()):
            found = find_assignment_in_body(body_snippet, name)
            if not found:
                continue
            rem_start_rel, rem_end_rel, rhs = found
            # Replace default in header
            header_before = new_text[:start]
            header_after = new_text[end:]
            new_header = header[:ps] + header[ps:pe].replace('= None', f'= {rhs}') + header[pe:]
            new_text = header_before + new_header + header_after
            # Adjust offset due to header change
            delta = len(new_header) - (end - start)
            offset += delta
            end += delta
            # Remove if-block and assignment from body snippet region
            abs_rem_start = body_start + rem_start_rel + offset
            abs_rem_end = body_start + rem_end_rel + offset
            new_text = new_text[:abs_rem_start] + new_text[abs_rem_end:]
            # Update offset after removal
            offset -= (abs_rem_end - abs_rem_start)
            end -= (abs_rem_end - abs_rem_start)
            # Refresh body snippet for subsequent params
            next_part_end = body_start
            for _ in range(40):
                nl = new_text.find('\n', next_part_end)
                if nl == -1:
                    next_part_end = len(new_text)
                    break
                next_part_end = nl + 1
            body_snippet = new_text[body_start:next_part_end]

    if new_text != original and parse_ok(new_text):
        p.write_text(new_text, encoding='utf-8')
        return True
    if new_text != original:
        p.write_text(new_text, encoding='utf-8')
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
    print(f"Reverted FastAPI defaults in {changed} files.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

