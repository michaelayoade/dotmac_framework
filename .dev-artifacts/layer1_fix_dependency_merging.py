#!/usr/bin/env python3

import re
from pathlib import Path

def layer1_fix_dependency_merging():
    """Layer 1: Fix dependency line merging issues in TOML files."""
    
    packages_dir = Path("packages")
    fixed_count = 0
    
    print("🔧 Layer 1: Fixing Dependency Line Merging")
    print("=" * 45)
    
    for pyproject_file in packages_dir.rglob("pyproject.toml"):
        try:
            content = pyproject_file.read_text()
            original_content = content
            
            # Fix 1: Dependencies merged after version strings
            # From: pydantic = ">=2.5.0"fastapi = ">=0.110.0" 
            # To:   pydantic = ">=2.5.0"\nfastapi = ">=0.110.0"
            content = re.sub(r'(= ">=?[^"]+")([a-zA-Z])', r'\1\n\2', content)
            
            # Fix 2: Dependencies merged after version numbers with ^
            # From: python = "^3.9"redis = ">=5.0.0"
            # To:   python = "^3.9"\nredis = ">=5.0.0"
            content = re.sub(r'(= "\^[^"]+")([a-zA-Z])', r'\1\n\2', content)
            
            # Fix 3: Dependencies merged after complex version specs
            # From: cryptography = "^41.0.0"python-jose = {
            # To:   cryptography = "^41.0.0"\npython-jose = {
            content = re.sub(r'(= "[^"]+")([\w-]+ = )', r'\1\n\2', content)
            
            # Fix 4: Dependencies merged after closing braces
            # From: }pytest = ">=7.0.0"
            # To:   }\npytest = ">=7.0.0"
            content = re.sub(r'(\})([a-zA-Z])', r'\1\n\2', content)
            
            # Fix 5: Test framework deps merged
            # From: pytest-asyncio = "^0.21.0"mypy = "^1.0.0"
            # To:   pytest-asyncio = "^0.21.0"\nmypy = "^1.0.0"
            content = re.sub(r'(pytest[^"]*= "[^"]+")([a-zA-Z])', r'\1\n\2', content)
            
            if content != original_content:
                pyproject_file.write_text(content)
                print(f"✅ Fixed: {pyproject_file.relative_to(packages_dir)}")
                fixed_count += 1
            else:
                print(f"⏭️  No changes: {pyproject_file.relative_to(packages_dir)}")
                
        except Exception as e:
            print(f"❌ Error: {pyproject_file.relative_to(packages_dir)}: {e}")
    
    print(f"\n📊 Layer 1 Results: Fixed {fixed_count} files")
    return fixed_count

if __name__ == "__main__":
    layer1_fix_dependency_merging()