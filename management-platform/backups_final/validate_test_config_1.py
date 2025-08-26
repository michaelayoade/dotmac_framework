#!/usr/bin/env python3
"""
Test configuration validation script.
Validates that pytest and coverage configurations are consistent and working.
"""

import os
import sys
import subprocess
import configparser
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        import toml as tomllib
from pathlib import Path


def validate_pytest_config():
    """Validate pytest configuration consistency."""
    print("🔍 Validating pytest configuration...")
    
    # Read pytest.ini
    pytest_ini = configparser.ConfigParser()
    pytest_ini.read("pytest.ini")
    
    # Read pyproject.toml
    with open("pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    
    # Check coverage paths
    pytest_cov = []
    addopts = pytest_ini.get("tool:pytest", "addopts")
    # Handle multi-line addopts
    for line in addopts.split('\n'):
        for opt in line.strip().split():
            if opt.startswith("--cov="):
                pytest_cov.append(opt[6:])
    
    pyproject_cov = []
    if "tool" in pyproject and "pytest" in pyproject["tool"]:
        addopts = pyproject["tool"]["pytest"]["ini_options"]["addopts"]
        for opt in addopts:
            if opt.startswith("--cov="):
                pyproject_cov.append(opt[6:])
    
    coverage_source = pyproject.get("tool", {}).get("coverage", {}).get("run", {}).get("source", [])
    
    print(f"📋 pytest.ini coverage paths: {pytest_cov}")
    print(f"📋 pyproject.toml pytest coverage paths: {pyproject_cov}")  
    print(f"📋 pyproject.toml coverage source: {coverage_source}")
    
    # Validate consistency
    issues = []
    
    if set(pytest_cov) != set(pyproject_cov):
        issues.append("Coverage paths differ between pytest.ini and pyproject.toml")
    
    if set(pytest_cov) != set(coverage_source):
        issues.append("Coverage paths differ between pytest and coverage config")
    
    # Check that paths exist
    for path in pytest_cov:
        if not Path(path).exists():
            issues.append(f"Coverage path does not exist: {path}")
    
    if issues:
        print("❌ Configuration issues found:")
        for issue in issues:
            print(f"  • {issue}")
        return False
    else:
        print("✅ Pytest configuration is consistent")
        return True


def validate_test_discovery():
    """Validate that pytest can discover tests."""
    print("🔍 Validating test discovery...")
    
    try:
        result = subprocess.run()
            ["python3", "-m", "pytest", "--collect-only", "--quiet"],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "PYTHONPATH": "."}
        )
        
        if result.returncode == 0:
            # Count collected tests
            lines = result.stdout.split('\n')
            collected_line = [line for line in lines if 'collected' in line and 'items' in line]
            
            if collected_line:
                print(f"✅ Test discovery successful: {collected_line[0].strip()}")
                return True
            else:
                print("⚠️  Tests collected but count unclear")
                return True
        else:
            print(f"❌ Test discovery failed:")
            print(f"   stdout: {result.stdout}")
            print(f"   stderr: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Test discovery timed out")
        return False
    except Exception as e:
        print(f"❌ Test discovery error: {e}")
        return False


def validate_database_config():
    """Validate database configuration."""
    print("🔍 Validating database configuration...")
    
    # Check test environment file
    env_test_path = Path(".env.test")
    if not env_test_path.exists():
        print("❌ .env.test file missing")
        return False
    
    # Read test environment
    with open(env_test_path) as f:
        env_content = f.read()
    
    required_vars = [
        "DATABASE_URL",
        "REDIS_URL", 
        "SECURITY_JWT_SECRET_KEY",
        "APP_NAME",
        "ENVIRONMENT"
    ]
    
    missing_vars = []
    for var in required_vars:
        if var not in env_content:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required test environment variables: {missing_vars}")
        return False
    
    print("✅ Test environment configuration looks good")
    return True


def validate_imports():
    """Validate that main application modules can be imported."""
    print("🔍 Validating module imports...")
    
    modules_to_test = [
        "app.main",
        "app.config", 
        "app.database",
        "app.models.base",
        "tests.conftest"
    ]
    
    import_issues = []
    
    for module in modules_to_test:
        try:
            result = subprocess.run()
                ["python3", "-c", f"import {module}"],
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": "."}
            )
            
            if result.returncode == 0:
                print(f"✅ {module}")
            else:
                print(f"❌ {module}: {result.stderr.strip()}")
                import_issues.append(f"{module}: {result.stderr.strip()}")
        except Exception as e:
            print(f"❌ {module}: {e}")
            import_issues.append(f"{module}: {e}")
    
    if import_issues:
        print(f"❌ Import issues found: {len(import_issues)}")
        return False
    else:
        print("✅ All critical modules import successfully")
        return True


def run_syntax_checks():
    """Run Python syntax checks on test files."""
    print("🔍 Running syntax checks on test files...")
    
    test_files = list(Path("tests").glob("test_*.py"))
    syntax_issues = []
    
    for test_file in test_files:
        try:
            result = subprocess.run()
                ["python3", "-m", "py_compile", str(test_file)],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"✅ {test_file.name}")
            else:
                print(f"❌ {test_file.name}: {result.stderr}")
                syntax_issues.append(f"{test_file.name}: {result.stderr}")
                
        except Exception as e:
            print(f"❌ {test_file.name}: {e}")
            syntax_issues.append(f"{test_file.name}: {e}")
    
    if syntax_issues:
        print(f"❌ Syntax issues found: {len(syntax_issues)}")
        return False
    else:
        print("✅ All test files have valid syntax")
        return True


def main():
    """Run all validation checks."""
    print("🚀 DotMac Management Platform - Test Configuration Validation")
    print("=" * 60)
    
    # Change to project directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    checks = [
        ("Pytest Configuration", validate_pytest_config),
        ("Test Discovery", validate_test_discovery),
        ("Database Configuration", validate_database_config), 
        ("Module Imports", validate_imports),
        ("Syntax Checks", run_syntax_checks),
    ]
    
    results = {}
    
    for check_name, check_func in checks:
        print(f"\n📋 {check_name}")
        print("-" * 40)
        
        try:
            results[check_name] = check_func()
        except Exception as e:
            print(f"❌ {check_name} failed with error: {e}")
            results[check_name] = False
    
    # Summary
    print("\n=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for check_name, passed_check in results.items():
        status = "✅ PASS" if passed_check else "❌ FAIL"
        print(f"{check_name:25} {status}")
    
    print(f"\nOverall: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 All validation checks PASSED!")
        print("🚀 Test configuration is ready for use!")
        return True
    else:
        print(f"\n⚠️  {total - passed} validation issues found")
        print("🔧 Please fix the issues above before running tests")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)