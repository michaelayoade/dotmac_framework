#!/usr/bin/env python3
"""
Final syntax check and report generator for Management Platform
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Any
import json

def check_syntax_errors():
    """Check for remaining syntax errors and generate comprehensive report"""
    root_dir = Path("/home/dotmac_framework/management-platform")
    python_files = list(root_dir.rglob("*.py"))
    
    results = {
        "total_files": len(python_files),
        "files_with_syntax_errors": 0,
        "files_with_pydantic_issues": 0,
        "syntax_errors": [],
        "pydantic_issues": [],
        "clean_files": 0,
        "summary": {}
    }
    
    pydantic_patterns = [
        r'\.dict\(\)',
        r'\.json\(\)',
        r'\.parse_obj\(',
        r'\.parse_raw\(',
        r'@validator\(',
        r'@root_validator\(',
        r'Config\s*:',
        r'orm_mode\s*=',
        r'allow_population_by_field_name\s*=',
    ]
    
    for file_path in python_files:
        # Skip backup directories
        if "backup" in str(file_path).lower():
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.strip():
                continue
            
            # Check syntax
            has_syntax_error = False
            error_message = ""
            try:
                ast.parse(content)
            except SyntaxError as e:
                has_syntax_error = True
                error_message = f"Line {e.lineno}: {e.msg}"
                results["syntax_errors"].append({
                    "file": str(file_path.relative_to(root_dir)),
                    "error": error_message,
                    "line": e.lineno
                })
            except Exception as e:
                has_syntax_error = True
                error_message = str(e)
                results["syntax_errors"].append({
                    "file": str(file_path.relative_to(root_dir)),
                    "error": error_message,
                    "line": None
                })
            
            if has_syntax_error:
                results["files_with_syntax_errors"] += 1
            
            # Check Pydantic issues
            pydantic_issues_found = []
            for pattern in pydantic_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    pydantic_issues_found.extend(matches)
            
            if pydantic_issues_found:
                results["files_with_pydantic_issues"] += 1
                results["pydantic_issues"].append({
                    "file": str(file_path.relative_to(root_dir)),
                    "issues": pydantic_issues_found
                })
            
            # If no issues, it's clean
            if not has_syntax_error and not pydantic_issues_found:
                results["clean_files"] += 1
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Generate summary
    results["summary"] = {
        "total_files_scanned": results["total_files"],
        "clean_files": results["clean_files"],
        "files_with_syntax_errors": results["files_with_syntax_errors"],
        "files_with_pydantic_issues": results["files_with_pydantic_issues"],
        "syntax_error_rate": round((results["files_with_syntax_errors"] / results["total_files"]) * 100, 2),
        "pydantic_issue_rate": round((results["files_with_pydantic_issues"] / results["total_files"]) * 100, 2),
        "overall_health": round((results["clean_files"] / results["total_files"]) * 100, 2)
    }
    
    return results

def generate_report(results):
    """Generate comprehensive report"""
    print("=" * 80)
    print("🔍 FINAL SYNTAX CHECK AND COMPREHENSIVE REPORT")
    print("=" * 80)
    print()
    
    print("📊 SUMMARY STATISTICS:")
    print(f"   Total Python files scanned: {results['summary']['total_files_scanned']}")
    print(f"   Clean files (no issues): {results['summary']['clean_files']}")
    print(f"   Files with syntax errors: {results['summary']['files_with_syntax_errors']}")
    print(f"   Files with Pydantic v1 patterns: {results['summary']['files_with_pydantic_issues']}")
    print(f"   Syntax error rate: {results['summary']['syntax_error_rate']}%")
    print(f"   Pydantic issue rate: {results['summary']['pydantic_issue_rate']}%")
    print(f"   Overall codebase health: {results['summary']['overall_health']}%")
    print()
    
    # Show most common syntax errors
    if results["syntax_errors"]:
        print("🚨 CRITICAL SYNTAX ERRORS (Top 20):")
        for i, error in enumerate(results["syntax_errors"][:20]):
            print(f"   {i+1}. {error['file']}: {error['error']}")
        print(f"   ... and {max(0, len(results['syntax_errors']) - 20)} more")
        print()
    
    # Show files that are ready for startup
    critical_files = [
        "app/main.py",
        "app/config.py", 
        "app/core/database.py",
        "app/api/dashboard.py",
        "app/services/tenant_service.py",
        "app/services/deployment_service.py"
    ]
    
    print("🚀 STARTUP READINESS CHECK:")
    startup_ready = True
    for critical_file in critical_files:
        has_error = any(error["file"] == critical_file for error in results["syntax_errors"])
        status = "❌ ERROR" if has_error else "✅ READY"
        print(f"   {status} {critical_file}")
        if has_error:
            startup_ready = False
    
    print(f"\n   Management Platform Startup Status: {'✅ READY' if startup_ready else '❌ NOT READY'}")
    print()
    
    # Recommendations
    print("🔧 RECOMMENDATIONS:")
    if results["files_with_syntax_errors"] > 0:
        print(f"   1. Fix remaining {results['files_with_syntax_errors']} files with syntax errors")
        print("   2. Focus on critical startup files first")
        print("   3. Consider manual fixes for complex syntax errors")
    
    if results["files_with_pydantic_issues"] > 0:
        print(f"   4. Migrate {results['files_with_pydantic_issues']} files from Pydantic v1 to v2")
        print("   5. Update .dict() calls to .model_dump()")
        print("   6. Replace @validator with @field_validator")
    
    if results["summary"]["overall_health"] > 80:
        print("   7. ✅ Codebase is in good shape overall!")
        print("   8. 🚀 Management Platform should be able to start with minor fixes")
    
    return startup_ready

def main():
    """Main function"""
    print("Running final syntax check...")
    results = check_syntax_errors()
    
    # Generate report
    startup_ready = generate_report(results)
    
    # Save detailed results
    report_file = Path("/home/dotmac_framework/management-platform/syntax_check_report.json")
    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: {report_file}")
    
    return startup_ready

if __name__ == "__main__":
    main()