# Code Quality Cheatsheet

Purpose: write clean code that passes local checks and CI on the first try. Each rule lists the error code, what it means, and how to fix it.

## Quick Workflow

- Run locally before push:
  - `pre-commit run -a`
  - `make lint type test`
  - For frontend changes: `npm run test:dev4:smoke`
- Auto-fix first: `ruff check . --fix` and `black .`
- If a rule still fails, apply the specific fix below.

## Non‑Negotiable Basics

- Imports at top, grouped: stdlib → third‑party → local; one blank line between groups.
- 4‑space indent; newline at EOF; no trailing whitespace.
- Two blank lines around top‑level defs; one blank line between logical blocks.
- No prints, no wildcard imports, no unused imports/vars.
- Max line length 100; let Black handle wrapping.

## Ruff: Pyflakes (F) — correctness

- F401 Imported but unused: remove the import or use it. For intentional ignore, prefix name with `_`.
- F821 Undefined name: fix typos or import/define the symbol.
- F841 Local variable assigned but never used: remove it or rename to `_` to signal intentional ignore.
- F632 Use `==/!=` to compare, not `is` for literals. Use `x is None` only for None checks.

## Ruff: Pycodestyle (E/W) — layout/whitespace

- E402 Import not at top of file: move all imports into the import section.
- E302/E305 Expected 2 blank lines before/after top‑level defs: add blank lines.
- E231/E241/E242 Missing/extra whitespace: normalize spacing (after commas, around operators; no alignment spaces).
- E203 Whitespace before `:` in slices: `a[1:3]`, not `a[1 : 3]`.
- W291/W293 Trailing whitespace / blank line with spaces: strip them.

## Ruff: Import order (I)

- I001 Imports unsorted/incorrectly grouped: let Ruff reorder. Groups: stdlib, third‑party, local. One blank line between.

## Ruff: Naming (N)

- N801 Class names must be `CapWords`.
- N802 Function names must be `snake_case`.
- N803/N804/N806 Arg/var names should be `snake_case`; constants are `UPPER_CASE`.

## Ruff: Pyupgrade (UP) — modern Python (3.9+)

- UP006 Use `list[str]` not `typing.List[str]`.
- UP007 Use `str | None` not `Optional[str]`.
- UP035 Prefer modern `typing` aliases; remove legacy imports.
- UP036 Use `typing.Self` where appropriate.

## Ruff: Bugbear (B) — common pitfalls

- B006 Mutable defaults: do not use lists/dicts in default args. Use `None` and initialize inside.
- B008 Function call in default arg: move the call into the function body.
- B017 Overly broad `assertRaises`/`except Exception`: catch specific exceptions in tests and code.
- B023 Loop variable referenced outside loop unintentionally: capture the value or restructure.

## Ruff: Comprehensions (C4)

- C401 Unnecessary generator: `list(x for x in it)` → `list(it)`.
- C402/C403/C404/C405 Prefer literals `{}`, `[]`, `{k: v}` over constructors.
- C416 Prefer `any(...)`/`all(...)`/`sum(...)` over creating intermediate lists for simple checks.

## Ruff: Security (S) — bandit rules

- S102 `exec()` detected: avoid dynamic execution.
- S103 Insecure file permissions: use `0o600` for sensitive files.
- S324 Weak hashes (`md5`, `sha1`): use `sha256` or stronger.
- S501 TLS disabled: do not use `verify=False` with HTTP clients.
- S603/S605 `subprocess` with `shell=True` or untrusted input: avoid shell, pass args list, validate input.

## Ruff: No prints (T20)

- T201/T203 `print()`/`pprint()` found: use structured logging (`structlog`) with context.

## Mypy — type errors and fixes

- arg-type Incompatible argument type: convert or adjust function signature; avoid `Any`.
- return-value Wrong return type: align all branches with the annotated return.
- assignment Incompatible assignment: cast or change variable type; prefer precise types over `Any`.
- call-arg Wrong number/kind of args: match the function signature.
- attr-defined Attribute not on type: narrow unions, check with `hasattr`, or fix model/annotation.
- index Invalid index on `Optional[...]`: guard against `None` first.
- union-attr Access on union: `if isinstance(x, T): x.method()`.
- override Override mismatch: match base class signature and types exactly.

## FastAPI Basics (quality‑sensitive)

- Use Pydantic v2 models for request/response; validators via `field_validator`.
- Keep handlers thin; move logic to services/use‑cases; return a typed `APIResponse[...]`.
- No blocking I/O in async handlers; use async clients and `BackgroundTasks` for long operations.

## Examples

Mutable default (B006):

Bad:

```python
def add(item, acc=[]):
    acc.append(item)
    return acc
```

Good:

```python
def add(item, acc=None):
    acc = [] if acc is None else acc
    acc.append(item)
    return acc
```

Imports and order (E402/I001):

Bad:

```python
def handler():
    import os
    from fastapi import APIRouter
```

Good:

```python
import os
from fastapi import APIRouter
from dotmac_shared.api.response import APIResponse
```

Modern typing (UP006/UP007):

Bad:

```python
from typing import List, Optional
def f(x: Optional[List[str]]) -> None:
    ...
```

Good:

```python
def f(x: list[str] | None) -> None:
    ...
```

Security (S603/S501):

Bad:

```python
subprocess.run(cmd, shell=True)
requests.get(url, verify=False)
```

Good:

```python
subprocess.run(["cmd", "arg1"])  # no shell
requests.get(url, timeout=5)  # keep TLS verification
```

## When You Must Ignore

- Prefer code changes over ignores. If unavoidable, add a narrow inline ignore with a reason:
  - `# noqa: F401  // imported for side effects`
  - `# type: ignore[arg-type]  # 3rd‑party stub is wrong`

## Pre‑Push Checklist

- `ruff check . --fix` and `black .`
- `make lint type test`
- Migrations safe and reversible (if changed)
- Update or add tests for changed behavior

