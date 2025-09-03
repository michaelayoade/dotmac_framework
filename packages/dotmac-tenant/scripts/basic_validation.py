#!/usr/bin/env python3
"""
Basic validation script for dotmac-tenant package structure.

Tests the package structure and core class definitions without
requiring external dependencies.
"""

import sys
from pathlib import Path

def test_package_structure():
    """Test that package structure is correct."""
    print("Testing package structure...")
    
    package_root = Path(__file__).parent.parent
    
    required_files = [
        "pyproject.toml",
        "README.md",
        "CHANGELOG.md",
        "src/dotmac/__init__.py",
        "src/dotmac/tenant/__init__.py",
        "src/dotmac/tenant/identity.py",
        "src/dotmac/tenant/middleware.py",
        "src/dotmac/tenant/boundary.py",
        "src/dotmac/tenant/config.py",
        "src/dotmac/tenant/exceptions.py",
        "src/dotmac/tenant/db.py",
        "tests/__init__.py",
        "tests/conftest.py",
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = package_root / file_path
        if not full_path.exists():
            missing_files.append(str(file_path))
        else:
            print(f"✅ {file_path}")
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required files present")
    return True


def test_basic_syntax():
    """Test that Python files have valid syntax."""
    print("\nTesting Python file syntax...")
    
    package_root = Path(__file__).parent.parent
    src_path = package_root / "src"
    
    python_files = list(src_path.rglob("*.py"))
    
    if not python_files:
        print("❌ No Python files found")
        return False
    
    for py_file in python_files:
        try:
            with open(py_file, 'r') as f:
                content = f.read()
            
            # Basic syntax check by compiling
            compile(content, str(py_file), 'exec')
            print(f"✅ {py_file.relative_to(package_root)} syntax OK")
            
        except SyntaxError as e:
            print(f"❌ {py_file.relative_to(package_root)} syntax error: {e}")
            return False
        except Exception as e:
            print(f"❌ {py_file.relative_to(package_root)} error: {e}")
            return False
    
    return True


def test_basic_imports():
    """Test basic imports without external dependencies."""
    print("\nTesting basic imports...")
    
    package_root = Path(__file__).parent.parent / "src"
    sys.path.insert(0, str(package_root))
    
    try:
        # Test namespace package
        import dotmac
        print("✅ dotmac namespace import successful")
        
        # Test exceptions (no external deps)
        from dotmac.tenant.exceptions import TenantError
        print("✅ Exception imports successful")
        
        # Test config (only pydantic dependency)
        from dotmac.tenant.config import TenantConfig, TenantResolutionStrategy
        config = TenantConfig()
        print(f"✅ Config creation successful: {type(config)}")
        
        return True
        
    except ImportError as e:
        if "pydantic" in str(e) or "loguru" in str(e) or "fastapi" in str(e):
            print(f"⚠️ Expected dependency missing: {e}")
            return True  # This is expected without dependencies
        else:
            print(f"❌ Unexpected import error: {e}")
            return False
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False


def test_pyproject_toml():
    """Test pyproject.toml structure."""
    print("\nTesting pyproject.toml...")
    
    package_root = Path(__file__).parent.parent
    pyproject_path = package_root / "pyproject.toml"
    
    if not pyproject_path.exists():
        print("❌ pyproject.toml missing")
        return False
    
    try:
        with open(pyproject_path, 'r') as f:
            content = f.read()
        
        # Check for required sections
        required_sections = [
            "[build-system]",
            "[tool.poetry]",
            'name = "dotmac-tenant"',
            "[tool.poetry.dependencies]",
        ]
        
        for section in required_sections:
            if section not in content:
                print(f"❌ Missing required section/field: {section}")
                return False
            print(f"✅ Found: {section}")
        
        return True
        
    except Exception as e:
        print(f"❌ pyproject.toml validation failed: {e}")
        return False


def test_documentation():
    """Test documentation files."""
    print("\nTesting documentation...")
    
    package_root = Path(__file__).parent.parent
    
    doc_files = {
        "README.md": ["# dotmac-tenant", "## Features", "## Quick Start"],
        "CHANGELOG.md": ["# Changelog", "## [Unreleased]"],
    }
    
    for doc_file, required_content in doc_files.items():
        doc_path = package_root / doc_file
        
        if not doc_path.exists():
            print(f"❌ {doc_file} missing")
            return False
        
        try:
            with open(doc_path, 'r') as f:
                content = f.read()
            
            for required in required_content:
                if required not in content:
                    print(f"❌ {doc_file} missing required content: {required}")
                    return False
                print(f"✅ {doc_file} contains: {required}")
        
        except Exception as e:
            print(f"❌ {doc_file} validation failed: {e}")
            return False
    
    return True


def main():
    """Run all basic validation tests."""
    print("🚀 Starting dotmac-tenant basic package validation")
    print("=" * 60)
    
    tests = [
        test_package_structure,
        test_basic_syntax,
        test_pyproject_toml,
        test_documentation,
        test_basic_imports,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Basic Validation Results:")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {passed}/{passed+failed} ({100*passed/(passed+failed):.1f}%)")
    
    if failed == 0:
        print("\n🎉 Basic validation successful!")
        print("📝 Package structure and basic functionality validated.")
        print("⚠️  Full functionality tests require dependencies (pydantic, fastapi, etc.)")
        return 0
    else:
        print(f"\n⚠️  {failed} tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())