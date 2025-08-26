#!/usr/bin/env python3
"""
Fix remaining base import issues in Management Platform models.
"""

import os
import re
from pathlib import Path

def fix_base_imports(file_path):
    """Fix base imports in a single file."""
    if not file_path.suffix == '.py':
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix base imports
        content = re.sub(r'from base import', r'from models.base import', content)
        
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
    """Fix all base imports in models."""
    app_dir = Path("/home/dotmac_framework/management-platform/app")
    models_dir = app_dir / "models"
    
    print("🔧 Fixing base imports in models...")
    
    fixed_count = 0
    
    # Process all Python files in models directory
    for py_file in models_dir.glob("*.py"):
        if fix_base_imports(py_file):
            print(f"   ✅ Fixed: {py_file.name}")
            fixed_count += 1
    
    print(f"\n✅ Fixed {fixed_count} model files")
    
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