#!/usr/bin/env python3
"""
Layer 2: Fix configuration field merging in TOML files.

This script addresses issues like:
- [tool.black]line-length = 100
- [tool.mypy]python_version = "3.9"
- [tool.pytest][tool.pytest.ini_options]

Fixed to:
- [tool.black]\nline-length = 100
- [tool.mypy]\npython_version = "3.9"
- [tool.pytest]\n\n[tool.pytest.ini_options]
"""

import re
import os
from pathlib import Path

def layer2_fix_config_merging():
    """Layer 2: Fix configuration field merging issues in TOML files."""
    
    # Find all pyproject.toml files in packages/
    packages_dir = Path("/home/dotmac_framework/packages")
    if not packages_dir.exists():
        print("❌ Packages directory not found")
        return
    
    toml_files = list(packages_dir.glob("*/pyproject.toml"))
    print(f"🔍 Found {len(toml_files)} pyproject.toml files")
    
    fixed_files = 0
    total_fixes = 0
    
    for toml_file in toml_files:
        print(f"\n📝 Processing {toml_file.relative_to(Path.cwd())}")
        
        try:
            content = toml_file.read_text()
            original_content = content
            file_fixes = 0
            
            # Fix 1: Configuration sections merged with their first field
            # [tool.black]line-length = 100 → [tool.black]\nline-length = 100
            before_fix1 = content
            content = re.sub(r'(\[tool\.[^\]]+\])([a-zA-Z_-]+\s*=)', r'\1\n\2', content)
            if content != before_fix1:
                fix1_count = len(re.findall(r'(\[tool\.[^\]]+\])([a-zA-Z_-]+\s*=)', before_fix1))
                print(f"  ✅ Fixed {fix1_count} tool section merging issues")
                file_fixes += fix1_count
            
            # Fix 2: General section headers merged with content
            # [build-system]requires = ["poetry-core"] → [build-system]\nrequires = ["poetry-core"]
            before_fix2 = content
            content = re.sub(r'(\[[^\]]+\])([a-zA-Z_-]+\s*=)', r'\1\n\2', content)
            if content != before_fix2:
                fix2_count = len(re.findall(r'(\[[^\]]+\])([a-zA-Z_-]+\s*=)', before_fix2)) - file_fixes
                if fix2_count > 0:
                    print(f"  ✅ Fixed {fix2_count} general section merging issues")
                    file_fixes += fix2_count
            
            # Fix 3: Adjacent sections without proper spacing
            # [tool.pytest][tool.pytest.ini_options] → [tool.pytest]\n\n[tool.pytest.ini_options]
            before_fix3 = content
            content = re.sub(r'(\[[^\]]+\])(\[[^\]]+\])', r'\1\n\n\2', content)
            if content != before_fix3:
                fix3_count = len(re.findall(r'(\[[^\]]+\])(\[[^\]]+\])', before_fix3))
                print(f"  ✅ Fixed {fix3_count} adjacent section spacing issues")
                file_fixes += fix3_count
            
            # Fix 4: Clean up excessive newlines (no more than 2 consecutive)
            before_fix4 = content
            content = re.sub(r'\n{3,}', '\n\n', content)
            if content != before_fix4:
                print(f"  ✅ Cleaned up excessive newlines")
            
            if content != original_content:
                toml_file.write_text(content)
                fixed_files += 1
                total_fixes += file_fixes
                print(f"  💾 Saved {file_fixes} fixes to {toml_file.name}")
            else:
                print(f"  ✨ No fixes needed for {toml_file.name}")
                
        except Exception as e:
            print(f"  ❌ Error processing {toml_file.name}: {e}")
    
    print(f"\n📊 Layer 2 Results:")
    print(f"   Files processed: {len(toml_files)}")
    print(f"   Files fixed: {fixed_files}")
    print(f"   Total fixes applied: {total_fixes}")

if __name__ == "__main__":
    layer2_fix_config_merging()