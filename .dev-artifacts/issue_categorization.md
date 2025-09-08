# Outstanding Issues Categorization - dotmac-business-logic

## Ruff Issues (87 total)

### **High Priority - Should Fix**
- **F401: unused-import (20 issues)** - Dead code removal
  - Impact: Code bloat, potential confusion
  - Fix: Remove unused imports with `ruff check --select=F401 --fix`

- **F821: undefined-name (1 issue)** - Runtime error risk
  - Impact: Potential NameError at runtime
  - Fix: Define missing variable or import

- **B904: raise-without-from-inside-except (1 issue)** - Exception chain loss
  - Impact: Makes debugging harder by losing stack trace context
  - Fix: Use `raise ... from e` pattern

### **Medium Priority - Code Quality**
- **B008: function-call-in-default-argument (21 issues)** - Mutable defaults
  - Impact: Shared state bugs, unexpected behavior
  - Fix: Use `None` as default, create object inside function

- **B023: function-uses-loop-variable (1 issue)** - Closure bug
  - Impact: Late binding issues in closures
  - Fix: Capture variable in closure scope

- **N801: invalid-class-name (1 issue)** - Naming convention
  - Impact: Code readability, PEP 8 compliance
  - Fix: Rename class to CapWords format

- **N811: constant-imported-as-non-constant (1 issue)** - Convention violation
  - Impact: Code readability
  - Fix: Import constant with UPPER_CASE alias

- **N818: error-suffix-on-exception-name (1 issue)** - Exception naming
  - Impact: Code readability, convention compliance
  - Fix: Add "Error" suffix to exception class name

### **Low Priority - Style Issues**
- **E402: module-import-not-at-top-of-file (23 issues)** - Import placement
  - Impact: Code organization, PEP 8 compliance
  - Fix: Move imports to top of file (may require conditional imports)

- **E701: multiple-statements-on-one-line-colon (11 issues)** - Code formatting
  - Impact: Code readability
  - Fix: Split statements onto separate lines

## Bandit Issues (381 total)

### **All Low Severity - Acceptable for Development**
- **B110: try-except-pass (majority)** - Empty exception handlers
  - Context: Common in test files and development code
  - Risk: Low - acceptable pattern for tests and optional imports
  - Action: Review case-by-case, may be intentional

- **B106: hardcoded-password-funcarg (1 issue)** - Test credential
  - Context: Example Stripe test key in example code
  - Risk: Low - clearly marked as test/example
  - Action: Consider using placeholder or environment variable

## Priority Recommendations

### **Immediate Action (High Priority)**
1. Fix undefined name (F821) - potential runtime error
2. Remove unused imports (F401) - clean code
3. Fix exception chaining (B904) - better debugging

### **Next Sprint (Medium Priority)**
1. Fix mutable default arguments (B008) - prevent subtle bugs
2. Fix naming conventions (N801, N811, N818) - code consistency
3. Fix closure variable capture (B023) - prevent late-binding issues

### **Backlog (Low Priority)**
1. Organize imports (E402) - may require conditional imports analysis
2. Split multi-statements (E701) - formatting cleanup
3. Review try-except-pass patterns (B110) - context-dependent

## Auto-Fix Commands

```bash
cd /home/dotmac_framework/packages/dotmac-business-logic

# High priority auto-fixes
ruff check src/ --select=F401 --fix  # Remove unused imports

# Medium priority (review first)
ruff check src/ --select=B008,B023,B904 --fix

# Low priority formatting
ruff check src/ --select=E701 --fix
```

## Summary
- **Total Issues**: 468 (87 ruff + 381 bandit)
- **Critical**: 22 issues (F821, F401, B904, B008, B023)
- **Style/Convention**: 56 issues (E402, E701, naming)
- **Security**: 381 low-severity issues (mostly test-related)

The package is in good shape overall with mostly style and test-related issues remaining.