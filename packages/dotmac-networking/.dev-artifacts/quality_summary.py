#!/usr/bin/env python3
"""
Quick quality summary for dotmac-networking package.
"""

import subprocess
import json

def run_ruff_check():
    """Run ruff check and return summary."""
    print("🔍 Running Ruff Analysis...")
    
    try:
        result = subprocess.run([
            "ruff", "check", "src/", "--output-format=json"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ No ruff issues found")
            return True
        
        try:
            issues = json.loads(result.stdout) if result.stdout else []
            
            # Categorize issues
            issue_types = {}
            severity_levels = {"high": 0, "medium": 0, "low": 0}
            
            for issue in issues:
                rule = issue.get("code", "unknown")
                issue_types[rule] = issue_types.get(rule, 0) + 1
                
                # Classify severity
                if rule.startswith("E"):
                    severity_levels["high"] += 1
                elif rule.startswith("F"):
                    severity_levels["high"] += 1  
                elif rule.startswith("B"):
                    severity_levels["medium"] += 1
                else:
                    severity_levels["low"] += 1
            
            print(f"❌ Found {len(issues)} issues:")
            for rule, count in sorted(issue_types.items()):
                print(f"   {rule}: {count} issues")
            
            print(f"📊 Severity: High={severity_levels['high']}, Medium={severity_levels['medium']}, Low={severity_levels['low']}")
            return False
            
        except json.JSONDecodeError:
            print(f"❌ Ruff output parsing failed: {result.stdout[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Ruff check failed: {e}")
        return False

def run_bandit_security():
    """Run bandit security check."""
    print("\n🔒 Running Security Analysis...")
    
    try:
        result = subprocess.run([
            "bandit", "-r", "src/", "-f", "json", "-ll"
        ], capture_output=True, text=True, timeout=60)
        
        try:
            if result.stdout:
                data = json.loads(result.stdout)
                results = data.get("results", [])
                
                if not results:
                    print("✅ No security issues found")
                    return True
                
                # Count by severity
                high_count = sum(1 for r in results if r.get("issue_severity") == "HIGH")
                medium_count = sum(1 for r in results if r.get("issue_severity") == "MEDIUM")
                low_count = sum(1 for r in results if r.get("issue_severity") == "LOW")
                
                print(f"📊 Security Issues Found: {len(results)} total")
                print(f"   High: {high_count}")
                print(f"   Medium: {medium_count}")
                print(f"   Low: {low_count}")
                
                # Show high severity issues
                for result in results:
                    if result.get("issue_severity") == "HIGH":
                        print(f"❗ HIGH: {result.get('test_name')} - {result.get('issue_text')}")
                        print(f"   File: {result.get('filename')}:{result.get('line_number')}")
                
                return high_count == 0  # Pass if no high severity issues
            
        except json.JSONDecodeError:
            print("❌ Bandit output parsing failed")
            return False
            
    except Exception as e:
        print(f"❌ Bandit check failed: {e}")
        return False

def test_imports():
    """Test basic imports work."""
    print("\n📦 Testing Package Imports...")
    
    import sys
    sys.path.insert(0, "src")
    
    tests = [
        ("dotmac.networking", "Basic package"),
        ("dotmac.networking.NetworkingService", "Main service class"),
        ("dotmac.networking.ipam.core.models.NetworkType", "IPAM models"),
        ("dotmac.networking.ipam.services.ipam_service.IPAMService", "IPAM service"),
    ]
    
    passed = 0
    for import_name, description in tests:
        try:
            parts = import_name.split(".")
            module_name = ".".join(parts[:-1]) if len(parts) > 1 else parts[0]
            attr_name = parts[-1] if len(parts) > 1 and parts[-1] != parts[0] else None
            
            module = __import__(module_name, fromlist=[attr_name] if attr_name else [])
            if attr_name:
                getattr(module, attr_name)
            
            print(f"✅ {description}: OK")
            passed += 1
            
        except Exception as e:
            print(f"❌ {description}: {e}")
    
    print(f"📊 Import Results: {passed}/{len(tests)} passed")
    return passed == len(tests)

def run_pytest_basic():
    """Run basic pytest tests."""
    print("\n🧪 Running Tests...")
    
    try:
        result = subprocess.run([
            "python3", "-m", "pytest", 
            "tests/test_pep8_pydantic2.py", 
            "tests/test_smoke.py",
            "-v", "--tb=short", "--no-header"
        ], capture_output=True, text=True, timeout=120)
        
        output = result.stdout
        passed = output.count("PASSED")
        failed = output.count("FAILED") 
        skipped = output.count("SKIPPED")
        
        print(f"📊 Test Results: {passed} passed, {failed} failed, {skipped} skipped")
        
        if failed > 0:
            print("❌ Some tests failed:")
            lines = output.split('\n')
            for line in lines:
                if "FAILED" in line and "::" in line:
                    print(f"   {line}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Pytest failed: {e}")
        return False

def main():
    """Run quality analysis."""
    print("🚀 DOTMAC NETWORKING - QUALITY ANALYSIS")
    print("=" * 50)
    
    results = {}
    
    # Run all checks
    results["ruff"] = run_ruff_check()
    results["security"] = run_bandit_security() 
    results["imports"] = test_imports()
    results["tests"] = run_pytest_basic()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 QUALITY SUMMARY")
    print("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    
    for check, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{check.upper():12} {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} checks passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All quality checks passed!")
    else:
        print("⚠️  Some quality issues need attention")
    
    return passed == total

if __name__ == "__main__":
    main()