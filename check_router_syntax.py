#!/usr/bin/env python3
"""
Check all API routers for syntax errors
"""

import os
import sys
from pathlib import Path
import py_compile
import subprocess

def check_syntax_errors():
    """Check all router files for syntax errors."""
    print("🔍 Checking API routers for syntax errors...")
    
    # Find all router files
    router_patterns = [
        "**/router*.py",
        "**/api/**/*.py",
        "**/routers*.py"
    ]
    
    router_files = []
    for pattern in router_patterns:
        files = list(Path(".").rglob(pattern))
        router_files.extend(files)
    
    # Remove duplicates and test files
    unique_files = set()
    for f in router_files:
        if "test" not in str(f).lower() and "__pycache__" not in str(f):
            unique_files.add(f)
    
    router_files = sorted(unique_files)
    
    print(f"📁 Found {len(router_files)} router/API files to check")
    
    errors = []
    success = []
    
    for file_path in router_files:
        try:
            py_compile.compile(str(file_path), doraise=True)
            success.append(str(file_path))
            print(f"✅ {file_path}")
        except py_compile.PyCompileError as e:
            errors.append((str(file_path), str(e)))
            print(f"❌ {file_path}: {e}")
        except Exception as e:
            errors.append((str(file_path), str(e)))
            print(f"⚠️ {file_path}: {e}")
    
    print(f"\n📊 Results:")
    print(f"✅ Success: {len(success)}")
    print(f"❌ Errors: {len(errors)}")
    
    if errors:
        print(f"\n🔧 Files with syntax errors:")
        for file_path, error in errors:
            print(f"   {file_path}")
            print(f"      → {error}")
    
    return len(errors) == 0

def check_import_errors():
    """Check for import errors in router files."""
    print("\n🔍 Checking for import errors in key routers...")
    
    key_routers = [
        "isp-framework/src/dotmac_isp/api/routers.py",
        "isp-framework/src/dotmac_isp/shared/routers.py", 
        "management-platform/app/api/v1/auth.py",
        "management-platform/app/api/v1/billing.py",
    ]
    
    for router in key_routers:
        if os.path.exists(router):
            try:
                # Try to import the module
                result = subprocess.run([
                    sys.executable, "-c", 
                    f"import sys; sys.path.append('{os.path.dirname(router)}'); "
                    f"exec(open('{router}').read())"
                ], capture_output=True, text=True, cwd=".")
                
                if result.returncode == 0:
                    print(f"✅ {router} - Import successful")
                else:
                    print(f"❌ {router} - Import error:")
                    print(f"   {result.stderr}")
            except Exception as e:
                print(f"⚠️ {router} - Error: {e}")
        else:
            print(f"⚠️ {router} - File not found")

def main():
    """Main function."""
    os.chdir("/home/dotmac_framework")
    
    print("🚀 API Router Syntax & Import Analysis")
    print("=" * 50)
    
    syntax_ok = check_syntax_errors()
    check_import_errors()
    
    print("\n" + "=" * 50)
    if syntax_ok:
        print("🎉 All routers have valid syntax!")
    else:
        print("⚠️ Some routers have syntax errors that need fixing")
    
    return 0 if syntax_ok else 1

if __name__ == "__main__":
    sys.exit(main())