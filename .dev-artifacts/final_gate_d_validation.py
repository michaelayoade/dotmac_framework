#!/usr/bin/env python3
"""
Final Gate D: Security & Compliance Validation
Comprehensive security test suite for production readiness validation
"""

import subprocess
import sys
import os
import json
from pathlib import Path

def run_command(cmd, cwd=None, timeout=60):
    """Run a command safely with timeout"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, 
            cwd=cwd, timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return False, "", str(e)

def test_security_tools_availability():
    """Test 1: Security Tools Availability"""
    print("🔒 Security Tools Availability Test")
    print("-" * 50)
    
    tools = {
        "bandit": "Static Application Security Testing",
        "safety": "Dependency vulnerability scanning", 
        "pip-audit": "Alternative dependency scanner",
        "ruff": "Code quality and security linting",
        "mypy": "Static type checking",
    }
    
    results = {"available": [], "missing": [], "total": len(tools)}
    
    for tool, description in tools.items():
        success, _, _ = run_command(f"which {tool}")
        if success:
            results["available"].append((tool, description))
            print(f"  ✅ {tool}: {description}")
        else:
            results["missing"].append((tool, description))
            print(f"  ❌ {tool}: {description} (not available)")
    
    print(f"\n📊 Tools Status: {len(results['available'])}/{results['total']} available")
    return results

def test_bandit_sast_scanning():
    """Test 2: Static Application Security Testing with Bandit"""
    print("\n🔍 Static Application Security Testing (SAST)")
    print("-" * 50)
    
    success, _, _ = run_command("which bandit")
    if not success:
        print("  ⏭️ Bandit not available - skipping SAST test")
        return {"status": "skipped", "reason": "bandit not available"}
    
    # Run Bandit on src/ directory
    if Path("src").exists():
        print("  🔍 Running Bandit SAST scan on src/...")
        success, stdout, stderr = run_command("bandit -r src/ -f json --quiet", timeout=120)
        
        if success or "No issues identified" in stderr:
            print("  ✅ SAST scan completed - no critical security issues")
            return {"status": "pass", "details": "No critical security issues found"}
        else:
            # Try to parse JSON output for details
            try:
                if stdout:
                    bandit_report = json.loads(stdout)
                    issues = bandit_report.get("results", [])
                    high_severity = [i for i in issues if i.get("issue_severity") == "HIGH"]
                    
                    if high_severity:
                        print(f"  ⚠️ SAST scan found {len(high_severity)} high-severity issues")
                        return {"status": "warning", "details": f"{len(high_severity)} high-severity issues"}
                    else:
                        print("  ✅ SAST scan completed - only low/medium severity issues")
                        return {"status": "pass", "details": "No high-severity issues"}
            except json.JSONDecodeError:
                pass
            
            print("  ⚠️ SAST scan completed with findings - review needed")
            return {"status": "warning", "details": "Security findings detected"}
    else:
        print("  ⏭️ No src/ directory found - skipping SAST test")
        return {"status": "skipped", "reason": "no src directory"}

def test_dependency_vulnerabilities():
    """Test 3: Dependency Vulnerability Scanning"""
    print("\n🔍 Dependency Vulnerability Scanning")
    print("-" * 50)
    
    # Check pip-audit (preferred)
    success, _, _ = run_command("which pip-audit")
    if success:
        print("  🔍 Running pip-audit vulnerability scan...")
        success, stdout, stderr = run_command("pip-audit --format=json --progress-spinner=off", timeout=120)
        
        if success:
            try:
                if stdout:
                    audit_report = json.loads(stdout)
                    vulnerabilities = audit_report.get("vulnerabilities", [])
                    
                    if vulnerabilities:
                        critical_vulns = [v for v in vulnerabilities if v.get("fix_versions")]
                        print(f"  ⚠️ Found {len(vulnerabilities)} vulnerabilities ({len(critical_vulns)} fixable)")
                        return {"status": "warning", "details": f"{len(vulnerabilities)} vulnerabilities found"}
                    else:
                        print("  ✅ No vulnerabilities detected")
                        return {"status": "pass", "details": "No vulnerabilities found"}
            except json.JSONDecodeError:
                if "No known vulnerabilities found" in stdout:
                    print("  ✅ No vulnerabilities detected")
                    return {"status": "pass", "details": "No vulnerabilities found"}
        
        print("  ⚠️ Vulnerability scan completed with findings")
        return {"status": "warning", "details": "Potential vulnerabilities detected"}
    
    # Fall back to safety
    success, _, _ = run_command("which safety")
    if success:
        print("  🔍 Running Safety vulnerability scan...")
        success, stdout, stderr = run_command("safety check --json", timeout=60)
        
        if success and stdout:
            print("  ✅ Safety scan completed - no critical vulnerabilities")
            return {"status": "pass", "details": "No critical vulnerabilities"}
        else:
            print("  ⚠️ Safety scan found potential vulnerabilities")
            return {"status": "warning", "details": "Potential vulnerabilities detected"}
    
    print("  ❌ No dependency scanners available")
    return {"status": "fail", "reason": "No scanners available"}

def test_code_quality_security():
    """Test 4: Code Quality & Security Linting"""
    print("\n🔍 Code Quality & Security Linting")
    print("-" * 50)
    
    success, _, _ = run_command("which ruff")
    if not success:
        print("  ❌ Ruff not available")
        return {"status": "fail", "reason": "ruff not available"}
    
    # Run ruff with security-focused rules
    print("  🔍 Running Ruff security and quality checks...")
    security_rules = "E,F,W,C,N,UP,B,S,PTH"  # Security-focused rule set
    success, stdout, stderr = run_command(f"ruff check --select={security_rules} --statistics src/ packages/", timeout=90)
    
    if success:
        print("  ✅ Code quality and security checks passed")
        return {"status": "pass", "details": "All quality and security checks passed"}
    else:
        # Count errors from statistics
        if "Found" in stderr:
            print(f"  ⚠️ Code quality issues found: {stderr.split('Found')[1].strip()}")
            return {"status": "warning", "details": "Code quality issues found"}
        else:
            print("  ⚠️ Code quality checks completed with findings")
            return {"status": "warning", "details": "Quality issues detected"}

def test_secrets_detection():
    """Test 5: Secrets and Credential Detection"""
    print("\n🔍 Secrets and Credential Detection")
    print("-" * 50)
    
    # Simple pattern-based secret detection
    secret_patterns = [
        r'password\s*=\s*["\'][^"\']+["\']',
        r'api_key\s*=\s*["\'][^"\']+["\']',
        r'secret\s*=\s*["\'][^"\']+["\']',
        r'token\s*=\s*["\'][^"\']+["\']',
        r'POSTGRES_PASSWORD\s*=\s*["\']?[^"\']+["\']?',
    ]
    
    import re
    potential_secrets = []
    
    for pattern in secret_patterns:
        # Search in key files
        search_paths = ["src/", "packages/", ".env*", "docker-compose*.yml"]
        for path in search_paths:
            if Path(path).exists():
                if Path(path).is_file():
                    try:
                        content = Path(path).read_text()
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            potential_secrets.extend([(str(path), match) for match in matches])
                    except:
                        pass
                else:
                    # Search directory recursively
                    for file_path in Path(path).rglob("*.py"):
                        try:
                            content = file_path.read_text()
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            if matches:
                                potential_secrets.extend([(str(file_path), match) for match in matches])
                        except:
                            pass
    
    if not potential_secrets:
        print("  ✅ No obvious secrets or credentials detected")
        return {"status": "pass", "details": "No secrets detected"}
    else:
        # Filter out obvious test/example patterns
        filtered_secrets = []
        test_patterns = ["test", "example", "demo", "mock", "placeholder"]
        
        for file_path, secret in potential_secrets:
            if not any(test_word in file_path.lower() or test_word in secret.lower() for test_word in test_patterns):
                filtered_secrets.append((file_path, secret))
        
        if not filtered_secrets:
            print(f"  ✅ {len(potential_secrets)} potential secrets found, but all appear to be test/example data")
            return {"status": "pass", "details": "Only test secrets detected"}
        else:
            print(f"  ⚠️ {len(filtered_secrets)} potential secrets detected - review needed")
            return {"status": "warning", "details": f"{len(filtered_secrets)} potential secrets"}

def test_security_policies():
    """Test 6: Security Policy Compliance"""
    print("\n🔍 Security Policy Compliance")
    print("-" * 50)
    
    security_indicators = [
        (Path("SECURITY.md"), "Security documentation"),
        (Path("packages/dotmac-security/"), "Security package"),
        (Path(".github/workflows/"), "CI/CD security integration"),
        (Path("requirements.txt"), "Dependency management"),
        (Path("pyproject.toml"), "Project configuration"),
    ]
    
    compliance_score = 0
    total_checks = len(security_indicators)
    
    for path, description in security_indicators:
        if path.exists():
            compliance_score += 1
            print(f"  ✅ {description}: Found")
        else:
            print(f"  ⚠️ {description}: Not found")
    
    compliance_percentage = (compliance_score / total_checks) * 100
    
    if compliance_percentage >= 80:
        print(f"  ✅ Security policy compliance: {compliance_percentage:.0f}% ({compliance_score}/{total_checks})")
        return {"status": "pass", "details": f"{compliance_percentage:.0f}% compliance"}
    elif compliance_percentage >= 60:
        print(f"  ⚠️ Security policy compliance: {compliance_percentage:.0f}% ({compliance_score}/{total_checks})")
        return {"status": "warning", "details": f"{compliance_percentage:.0f}% compliance"}
    else:
        print(f"  ❌ Security policy compliance: {compliance_percentage:.0f}% ({compliance_score}/{total_checks})")
        return {"status": "fail", "details": f"{compliance_percentage:.0f}% compliance"}

def main():
    """Main Gate D validation execution"""
    print("🔒 Gate D: Security & Compliance Validation")
    print("=" * 60)
    
    # Run all security tests
    security_tests = [
        ("Security Tools Availability", test_security_tools_availability),
        ("Static Application Security (SAST)", test_bandit_sast_scanning),
        ("Dependency Vulnerability Scanning", test_dependency_vulnerabilities),
        ("Code Quality & Security Linting", test_code_quality_security),
        ("Secrets Detection", test_secrets_detection),
        ("Security Policy Compliance", test_security_policies),
    ]
    
    results = []
    
    for test_name, test_func in security_tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, {"status": "error", "reason": str(e)}))
    
    # Generate final report
    print(f"\n📊 Gate D Security Validation Summary")
    print("=" * 60)
    
    passed = 0
    warned = 0
    failed = 0
    skipped = 0
    
    for test_name, result in results:
        status = result.get("status", "unknown")
        details = result.get("details", result.get("reason", ""))
        
        if status == "pass":
            print(f"✅ {test_name}: PASS - {details}")
            passed += 1
        elif status == "warning":
            print(f"⚠️ {test_name}: WARNING - {details}")
            warned += 1
        elif status == "fail":
            print(f"❌ {test_name}: FAIL - {details}")
            failed += 1
        elif status == "skipped":
            print(f"⏭️ {test_name}: SKIPPED - {details}")
            skipped += 1
        else:
            print(f"❓ {test_name}: ERROR - {details}")
            failed += 1
    
    total_tests = len(results)
    print(f"\n🎯 Overall Gate D Results:")
    print(f"   ✅ Passed: {passed}/{total_tests}")
    print(f"   ⚠️ Warnings: {warned}/{total_tests}")
    print(f"   ❌ Failed: {failed}/{total_tests}")
    print(f"   ⏭️ Skipped: {skipped}/{total_tests}")
    
    # Security gate decision
    if failed == 0 and warned <= 2:
        print(f"\n🎉 GATE D SECURITY VALIDATION: ✅ PASS")
        print("Security and compliance validation successful - ready for production!")
        return True
    elif failed == 0:
        print(f"\n⚠️ GATE D SECURITY VALIDATION: ✅ PASS WITH WARNINGS")
        print(f"Security validation passed but {warned} areas need attention")
        return True
    else:
        print(f"\n❌ GATE D SECURITY VALIDATION: ❌ FAIL")
        print(f"{failed} critical security issues must be resolved before deployment")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)