#!/usr/bin/env python3
"""
Fix all relative imports in Management Platform to absolute imports.
"""

import os
import re
from pathlib import Path

def fix_relative_imports(file_path):
    """Fix relative imports in a single file."""
    if not file_path.suffix == '.py':
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix various relative import patterns
        patterns = [
            (r'from \.\.\.(\w+)', r'from \1'),  # from ...module
            (r'from \.\.(\w+)', r'from \1'),   # from ..module  
            (r'from \.(\w+)', r'from \1'),     # from .module
        ]
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)
        
        # Only write if there were changes
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False
    
    return False

def main():
    """Fix all relative imports in Management Platform."""
    app_dir = Path("/home/dotmac_framework/management-platform/app")
    
    print("🔧 Fixing Management Platform relative imports...")
    
    fixed_count = 0
    
    # Process all Python files recursively
    for py_file in app_dir.rglob("*.py"):
        # Skip __init__.py files in some cases to preserve package structure
        if py_file.name == "__init__.py":
            continue
            
        if fix_relative_imports(py_file):
            print(f"   ✅ Fixed: {py_file.relative_to(app_dir)}")
            fixed_count += 1
    
    print(f"\n✅ Fixed {fixed_count} files with relative imports")
    
    # Test the main import
    print("\n🧪 Testing Management Platform imports...")
    
    os.chdir(app_dir)
    os.environ['PYTHONPATH'] = str(app_dir)
    
    try:
        import subprocess
        result = subprocess.run([
            'python3', '-c', 
            'from api.v1 import api_router; print(f"✅ api_router: {len(api_router.routes)} routes")'
        ], capture_output=True, text=True, env=os.environ)
        
        if result.returncode == 0:
            print(result.stdout.strip())
        else:
            print(f"❌ Import test failed: {result.stderr.strip()}")
            
    except Exception as e:
        print(f"❌ Test error: {e}")

if __name__ == "__main__":
    main()