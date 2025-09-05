#!/usr/bin/env python3
"""
Strategic Documentation Dependencies Checker
Analyzes what dependencies are actually needed vs. what's mocked.
"""

import ast
import importlib
import os
import sys
from pathlib import Path


def find_imports_in_file(file_path: Path) -> set[str]:
    """Extract all imports from a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content, filename=str(file_path))
        imports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
        
        return imports
    except Exception as e:
        print(f"Warning: Could not parse {file_path}: {e}")
        return set()


def scan_project_imports() -> set[str]:
    """Scan the entire project for import statements."""
    project_root = Path(__file__).parent.parent  # noqa: B008
    imports = set()
    
    # Scan ISP framework
    isp_src = project_root / "isp-framework" / "src"
    if isp_src.exists():
        for py_file in isp_src.rglob("*.py"):
            imports.update(find_imports_in_file(py_file))
    
    # Scan management platform
    mgmt_src = project_root / "management-platform" / "app"
    if mgmt_src.exists():
        for py_file in mgmt_src.rglob("*.py"):
            imports.update(find_imports_in_file(py_file))
    
    return imports


def check_import_availability(imports: set[str]) -> dict[str, bool]:
    """Check which imports are actually available."""
    results = {}
    
    for import_name in sorted(imports):
        # Skip standard library and local modules
        if import_name in {'os', 'sys', 'json', 'time', 'datetime', 'typing', 
                          'pathlib', 'logging', 'asyncio', 'functools', 'dataclasses',
                          'dotmac_isp', 'management_platform', 'shared'}:
            continue
            
        try:
            importlib.import_module(import_name)
            results[import_name] = True
        except ImportError:
            results[import_name] = False
    
    return results


def load_current_mocks() -> set[str]:
    """Load currently mocked imports from conf.py."""
    conf_path = Path(__file__).parent / "conf.py"  # noqa: B008
    mocks = set()
    
    if conf_path.exists():
        with open(conf_path, 'r') as f:
            content = f.read()
            
        # Extract mocked imports (simple parsing)
        in_mock_section = False
        for line in content.split('\n'):
            line = line.strip()
            if 'autodoc_mock_imports' in line:
                in_mock_section = True
            elif in_mock_section and line == ']':
                break
            elif in_mock_section and line.startswith("'") and line.endswith("',"):
                mock = line.strip("',")
                mocks.add(mock)
    
    return mocks


def main():
    """Analyze and report on documentation dependencies."""
    print("🔍 Strategic Documentation Dependencies Analysis")
    print("=" * 60)
    
    # Find all imports in the project
    print("Scanning project for imports...")
    project_imports = scan_project_imports()
    print(f"Found {len(project_imports)} unique imports")
    
    # Check availability
    print("\nChecking import availability...")
    availability = check_import_availability(project_imports)
    
    # Load current mocks
    current_mocks = load_current_mocks()
    
    # Analysis
    available = {name for name, avail in availability.items() if avail}
    missing = {name for name, avail in availability.items() if not avail}
    
    print(f"\n📊 Results:")
    print(f"  Available packages: {len(available)}")
    print(f"  Missing packages: {len(missing)}")
    print(f"  Currently mocked: {len(current_mocks)}")
    
    # Strategic recommendations
    print(f"\n🎯 Strategic Recommendations:")
    
    # Packages we're mocking but could import
    unnecessary_mocks = current_mocks.intersection(available)
    if unnecessary_mocks:
        print(f"  ✅ Remove from mocks (available): {sorted(unnecessary_mocks)}")
    
    # Packages we need but aren't mocking
    needed_mocks = missing - current_mocks
    if needed_mocks:
        print(f"  ⚠️  Add to mocks (missing): {sorted(needed_mocks)}")
    
    # Critical packages that should be available
    critical = {'httpx', 'structlog', 'fastapi', 'pydantic', 'sqlalchemy'}
    missing_critical = critical.intersection(missing)
    if missing_critical:
        print(f"  🚨 Install for better docs: {sorted(missing_critical)}")
    
    print(f"\n💡 Install command for missing critical packages:")
    if missing_critical:
        print(f"  pip install {' '.join(sorted(missing_critical))}")


if __name__ == "__main__":
    main()
