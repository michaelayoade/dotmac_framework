#!/usr/bin/env python3
"""
Strategies to ensure exception handling fixes persist
"""

def create_pre_commit_hook():
    """Create pre-commit hook to prevent regression"""
    
    hook_config = """
# Add to .pre-commit-config.yaml

repos:
  - repo: local
    hooks:
      - id: check-broad-exceptions
        name: Check for broad exception handling
        entry: python scripts/check_broad_exceptions.py
        language: system
        files: '^(src/|packages/).*\\.py$'
        
      - id: ruff-check-ble001
        name: Check BLE001 violations in critical modules
        entry: ruff check --select=BLE001
        language: system
        files: '^(src/dotmac_shared/repositories/|src/dotmac_management/core/).*\\.py$'
        pass_filenames: false
"""
    
    return hook_config


def create_exception_checker_script():
    """Create script to check for regression in critical modules"""
    
    script = '''#!/usr/bin/env python3
"""
Check for broad exception handling regression in critical modules
"""
import re
import sys
from pathlib import Path

CRITICAL_MODULES = [
    "src/dotmac_shared/repositories/",
    "src/dotmac_management/core/websocket_manager.py",
    "src/dotmac_management/core/csrf_middleware.py",
    "src/dotmac_management/core/tenant_security.py",
    "src/dotmac_management/core/bootstrap.py"
]

FORBIDDEN_PATTERNS = [
    r'except Exception.*:',  # Broad Exception catching
    r'except BaseException.*:',  # Even broader
]

ALLOWED_CONTEXTS = [
    'rollback',  # Database rollback is allowed
    'transaction',  # Transaction management
    'loop resilience',  # Event loop protection
]

def check_file(file_path):
    """Check a single file for broad exception patterns"""
    violations = []
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        lines = content.split('\\n')
        
        for i, line in enumerate(lines, 1):
            for pattern in FORBIDDEN_PATTERNS:
                if re.search(pattern, line):
                    # Check surrounding context for allowed patterns
                    context_start = max(0, i-5)
                    context_end = min(len(lines), i+5)
                    context = '\\n'.join(lines[context_start:context_end]).lower()
                    
                    if not any(allowed in context for allowed in ALLOWED_CONTEXTS):
                        violations.append({
                            'file': file_path,
                            'line': i,
                            'content': line.strip(),
                            'pattern': pattern
                        })
    except Exception as e:
        print(f"Error checking {file_path}: {e}")
    
    return violations

def main():
    """Main check function"""
    violations = []
    
    for module_path in CRITICAL_MODULES:
        path = Path(module_path)
        
        if path.is_file():
            violations.extend(check_file(path))
        elif path.is_dir():
            for py_file in path.rglob('*.py'):
                violations.extend(check_file(py_file))
    
    if violations:
        print("❌ BROAD EXCEPTION HANDLING DETECTED:")
        for v in violations:
            print(f"   {v['file']}:{v['line']} - {v['content']}")
        print("\\nThese modules should use specific exceptions!")
        sys.exit(1)
    else:
        print("✅ No broad exception handling found in critical modules")
        sys.exit(0)

if __name__ == "__main__":
    main()
'''
    
    return script


def create_github_workflow():
    """Create GitHub Actions workflow to enforce standards"""
    
    workflow = """
# .github/workflows/exception-handling-check.yml
name: Exception Handling Standards

on:
  pull_request:
    paths:
      - 'src/dotmac_shared/repositories/**'
      - 'src/dotmac_management/core/**' 
      - 'packages/**/src/**'

jobs:
  check-exception-handling:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
          
      - name: Install dependencies
        run: |
          pip install ruff
          
      - name: Check for broad exceptions in critical modules
        run: |
          ruff check --select=BLE001 src/dotmac_shared/repositories/ src/dotmac_management/core/
          
      - name: Run custom exception checker
        run: |
          python scripts/check_broad_exceptions.py
          
      - name: Check WebSocket error handling
        run: |
          # Verify WebSocket manager uses specific exceptions
          if grep -n "except Exception" src/dotmac_management/core/websocket_manager.py; then
            echo "❌ WebSocket manager should not use broad Exception catching"
            exit 1
          fi
          
      - name: Check repository error handling  
        run: |
          # Verify repositories use SQLAlchemy exceptions
          if grep -n "except Exception" src/dotmac_shared/repositories/*.py; then
            echo "❌ Repositories should use SQLAlchemyError, not Exception"
            exit 1
          fi
"""
    
    return workflow


def create_ruff_specific_config():
    """Create ruff configuration to be stricter on critical modules"""
    
    config_addition = """
# Add to pyproject.toml [tool.ruff.per-file-ignores]

# STRICT: No broad exceptions allowed in these critical modules
"src/dotmac_shared/repositories/*.py" = []  # Remove BLE001 exemptions
"src/dotmac_management/core/websocket_manager.py" = []  # Remove BLE001 exemptions  
"src/dotmac_management/core/*_middleware.py" = []  # Remove BLE001 exemptions
"src/dotmac_management/core/bootstrap.py" = []  # Remove BLE001 exemptions
"src/dotmac_management/core/tenant_security.py" = []  # Remove BLE001 exemptions

# Add to [tool.ruff] section
[tool.ruff.lint.per-file-ignores]
# Critical modules: zero tolerance for broad exceptions
"src/dotmac_shared/repositories/*" = []
"src/dotmac_management/core/websocket_manager.py" = []
"src/dotmac_management/core/*_security.py" = [] 
"src/dotmac_management/core/*_middleware.py" = []
"src/dotmac_management/core/bootstrap.py" = []
"""
    
    return config_addition


def create_documentation():
    """Create documentation for the team"""
    
    docs = """
# Exception Handling Standards

## ✅ APPROVED Exception Patterns

### Database Operations
```python
# ✅ GOOD - Specific database exceptions
try:
    result = await session.execute(query)
    return result.fetchall()
except SQLAlchemyError as e:
    logger.exception("Database query failed: %s", e)
    raise
```

### WebSocket Operations  
```python
# ✅ GOOD - Specific WebSocket exceptions
try:
    await websocket.send_text(message)
except (WebSocketDisconnect, ConnectionResetError, RuntimeError) as e:
    logger.exception("WebSocket send failed: %s", e)
    # Handle disconnect gracefully
```

### File Operations
```python
# ✅ GOOD - Specific file exceptions  
try:
    with open(config_file, 'r') as f:
        return json.load(f)
except (FileNotFoundError, PermissionError, json.JSONDecodeError) as e:
    logger.exception("Config loading failed: %s", e)
    return {}
```

## ❌ FORBIDDEN Exception Patterns

### Broad Exception Catching
```python
# ❌ BAD - Too broad, masks real issues
try:
    critical_operation()
except Exception as e:  # Don't do this!
    logger.error("Something failed: %s", e)
```

## 🔒 CRITICAL MODULES - Zero Tolerance

These modules must use specific exceptions only:
- `src/dotmac_shared/repositories/` - Database layer  
- `src/dotmac_management/core/websocket_manager.py` - WebSocket communications
- `src/dotmac_management/core/*_middleware.py` - Request middleware
- `src/dotmac_management/core/*_security.py` - Security components
- `src/dotmac_management/core/bootstrap.py` - Application startup

## 🛡️ Enforcement

1. **Pre-commit hooks** check for violations
2. **GitHub Actions** blocks PRs with broad exceptions  
3. **Ruff configuration** flags violations in CI/CD
4. **Code reviews** must verify specific exception handling

## 📊 Monitoring

Run this to check compliance:
```bash
ruff check --select=BLE001 src/dotmac_shared/repositories/ src/dotmac_management/core/
python scripts/check_broad_exceptions.py
```
"""
    
    return docs


def main():
    """Generate all persistence strategies"""
    print("🛡️  Generating strategies to ensure exception handling fixes persist...")
    
    strategies = {
        "Pre-commit Hook Config": create_pre_commit_hook(),
        "Exception Checker Script": create_exception_checker_script(), 
        "GitHub Workflow": create_github_workflow(),
        "Ruff Configuration": create_ruff_specific_config(),
        "Team Documentation": create_documentation()
    }
    
    for name, content in strategies.items():
        print(f"\n{'='*60}")
        print(f"📋 {name}")
        print("="*60)
        print(content[:500] + "..." if len(content) > 500 else content)
    
    print(f"\n{'='*60}")
    print("🎯 IMPLEMENTATION RECOMMENDATIONS")  
    print("="*60)
    print("1. Create: scripts/check_broad_exceptions.py (exception checker)")
    print("2. Update: .pre-commit-config.yaml (pre-commit hooks)")
    print("3. Create: .github/workflows/exception-handling-check.yml")
    print("4. Update: pyproject.toml (stricter ruff config for critical modules)")
    print("5. Create: docs/EXCEPTION_HANDLING_STANDARDS.md")
    print("6. Add to code review checklist: 'Uses specific exceptions in critical modules'")
    
    print(f"\n🔒 CRITICAL SUCCESS FACTORS:")
    print("• Make it automatic (CI/CD enforcement)")  
    print("• Make it visible (clear documentation)")
    print("• Make it fast (pre-commit catches issues early)")
    print("• Make it specific (focus on critical modules only)")


if __name__ == "__main__":
    main()