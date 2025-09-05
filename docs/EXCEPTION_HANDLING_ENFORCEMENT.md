# Exception Handling Enforcement

This document outlines how we ensure the exception handling fixes persist and prevent regression.

## 🎯 What We Fixed

Your targeted improvements replaced broad `except Exception` with specific exceptions in critical modules:

### ✅ Fixed Modules (Zero Tolerance)
- `src/dotmac_shared/repositories/async_base_repository.py` - Uses `SQLAlchemyError`  
- `src/dotmac_shared/repositories/sync_base_repository.py` - Uses `SQLAlchemyError`
- `src/dotmac_management/core/sanitization.py` - Removed unnecessary broad catches

### 🔄 Remaining Work
- `src/dotmac_management/core/websocket_manager.py` - Should use `WebSocketDisconnect`, `ConnectionResetError`, `RuntimeError`
- `src/dotmac_management/core/*_middleware.py` - Should use specific exceptions with `logger.exception()`
- `src/dotmac_management/core/bootstrap.py` - Should use specific exceptions with `logger.exception()`

## 🛡️ Enforcement Mechanisms

### 1. Automated Checking

**Script: `scripts/check_broad_exceptions.py`**
```bash
# Run manually
python3 scripts/check_broad_exceptions.py

# Returns exit code 1 if broad exceptions found in critical modules
```

**Ruff Configuration (pyproject.toml)**
```toml
# Strict enforcement on fixed modules
"src/dotmac_shared/repositories/async_base_repository.py" = []  # No BLE001 exemptions
"src/dotmac_shared/repositories/sync_base_repository.py" = []   # No BLE001 exemptions  
"src/dotmac_management/core/sanitization.py" = []              # No BLE001 exemptions
```

### 2. Pre-commit Hooks

Add to `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: local
    hooks:
      - id: check-critical-module-exceptions
        name: Check critical modules for broad exceptions
        entry: python scripts/check_broad_exceptions.py
        language: system
        pass_filenames: false
        
      - id: ruff-strict-ble001
        name: Strict BLE001 check on fixed modules
        entry: ./.venv/bin/ruff check --select=BLE001
        language: system  
        pass_filenames: true
        files: '^(src/dotmac_shared/repositories/|src/dotmac_management/core/sanitization\.py)$'
```

### 3. CI/CD Pipeline

**GitHub Actions Workflow** (`.github/workflows/exception-standards.yml`):
```yaml
name: Exception Handling Standards
on:
  pull_request:
    paths: ['src/dotmac_shared/repositories/**', 'src/dotmac_management/core/**']
    
jobs:
  check-exceptions:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check critical modules
        run: python3 scripts/check_broad_exceptions.py
      - name: Strict ruff check  
        run: ruff check --select=BLE001 src/dotmac_shared/repositories/ src/dotmac_management/core/sanitization.py
```

### 4. Code Review Checklist

**Required checks for PRs touching critical modules:**
- [ ] Uses specific exceptions instead of `except Exception`
- [ ] Database operations use `SQLAlchemyError` or specific DB exceptions
- [ ] WebSocket operations use `WebSocketDisconnect`, `ConnectionResetError`, `RuntimeError`
- [ ] File operations use `FileNotFoundError`, `PermissionError`, `IOError`
- [ ] Uses `logger.exception()` to preserve stack traces
- [ ] Re-raises exceptions when needed for proper error boundaries

## 📊 Monitoring

### Check Current Status
```bash
# Overall BLE001 violations  
ruff check --select=BLE001 | wc -l

# Critical modules only
python3 scripts/check_broad_exceptions.py

# Specific modules (should return 0 violations)
ruff check --select=BLE001 src/dotmac_shared/repositories/async_base_repository.py
```

### Success Metrics
- ✅ `scripts/check_broad_exceptions.py` exits with code 0
- ✅ Fixed modules have 0 BLE001 violations  
- ✅ Pre-commit hooks pass
- ✅ CI/CD pipeline enforces standards

## 🎯 Benefits Achieved

### Better Error Handling
- **Database errors** surface as database errors, not generic exceptions
- **WebSocket disconnects** treated separately from unexpected failures  
- **Validation errors** no longer masked as system failures

### Improved Debugging
- `logger.exception()` preserves full stack traces
- Specific exception types enable better error classification
- Cleaner separation between expected/unexpected conditions

### Architectural Integrity
- Proper error boundaries maintained
- Transaction rollback patterns preserved  
- Critical vs optional operation handling clarified

## 🔄 Future Improvements

As you continue fixing the remaining modules:

1. **Add to strict enforcement**: Update `pyproject.toml` per-file-ignores to remove BLE001 exemptions
2. **Update checker script**: Add newly fixed modules to `CRITICAL_MODULES` list
3. **Extend pre-commit**: Add file patterns for newly fixed modules  
4. **Document patterns**: Add approved exception patterns for each domain

The enforcement mechanisms scale with your fixes - each module you improve gets automatic protection against regression.