#!/usr/bin/env python3
"""
Layer 3: Fix specific TOML syntax errors identified by validation.

This script addresses:
1. Unclosed arrays/strings
2. Invalid key-value pair syntax  
3. Illegal characters
4. Invalid statements
"""

import re
from pathlib import Path

def layer3_fix_specific_errors():
    """Layer 3: Fix specific TOML syntax errors."""
    
    packages_dir = Path("/home/dotmac_framework/packages")
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
            
            # Fix 1: Dictionary-style dependency syntax (poetry expects inline table)
            # {"version": "^5.2.0", "optional": True} → {version = "^5.2.0", optional = true}
            before_fix1 = content
            content = re.sub(r'\{"version":\s*"([^"]+)",\s*"optional":\s*True\}', r'{version = "\1", optional = true}', content)
            content = re.sub(r'\{"version":\s*"([^"]+)",\s*"optional":\s*False\}', r'{version = "\1", optional = false}', content)
            if content != before_fix1:
                fix1_count = len(re.findall(r'\{"version":', before_fix1))
                if fix1_count > 0:
                    print(f"  ✅ Fixed {fix1_count} dictionary-style dependency syntax")
                    file_fixes += fix1_count
            
            # Fix 2: Unclosed array elements (especially in markers/addopts)
            # ["slow: marks tests as slow (deselect with '-m "not slow"')" → ["slow: marks tests as slow (deselect with '-m \"not slow\"')"]
            before_fix2 = content
            # Fix unescaped quotes in array strings
            content = re.sub(r'(".*?)-m "([^"]*)"([^"]*")', r'\1-m \\\"\2\\\"\3', content)
            # Fix incomplete closing of arrays
            content = re.sub(r'(markers = \[.*?)"([^"]*)"$', r'\1"\2"]', content, flags=re.MULTILINE)
            if content != before_fix2:
                print(f"  ✅ Fixed array quote escaping")
                file_fixes += 1
            
            # Fix 3: Path objects incorrectly formatted
            # {"path": "../dotmac-core", "develop": True} → {path = "../dotmac-core", develop = true}
            before_fix3 = content
            content = re.sub(r'\{"path":\s*"([^"]+)",\s*"develop":\s*True\}', r'{path = "\1", develop = true}', content)
            content = re.sub(r'\{"path":\s*"([^"]+)",\s*"develop":\s*False\}', r'{path = "\1", develop = false}', content)
            if content != before_fix3:
                fix3_count = len(re.findall(r'\{"path":', before_fix3))
                if fix3_count > 0:
                    print(f"  ✅ Fixed {fix3_count} path dependency syntax")
                    file_fixes += fix3_count
            
            # Fix 4: Clean up malformed extend-exclude patterns
            before_fix4 = content
            # Fix broken extend-exclude with unescaped backslashes
            content = re.sub(r'extend-exclude = """\n/(.*?)\n"""', r'extend-exclude = "/(\1)/"', content, flags=re.DOTALL)
            # Fix incomplete extend-exclude blocks
            content = re.sub(r'extend-exclude = \"\"\"\n/\(\n  # directories.*?\n\)/\n\"\"\"', 
                           r'extend-exclude = "/build/"', content, flags=re.DOTALL)
            if content != before_fix4:
                print(f"  ✅ Fixed extend-exclude patterns")
                file_fixes += 1
            
            # Fix 5: Remove Setuptools sections from Poetry files
            before_fix5 = content
            content = re.sub(r'\[tool\.setuptools\].*?(?=\[|\Z)', '', content, flags=re.DOTALL)
            content = re.sub(r'\[tool\.setuptools\.packages\].*?(?=\[|\Z)', '', content, flags=re.DOTALL) 
            content = re.sub(r'\[tool\.setuptools\.packages\.find\].*?(?=\[|\Z)', '', content, flags=re.DOTALL)
            content = re.sub(r'\[tool\.setuptools\.package-data\].*?(?=\[|\Z)', '', content, flags=re.DOTALL)
            if content != before_fix5:
                print(f"  ✅ Removed conflicting Setuptools sections")
                file_fixes += 1
            
            # Fix 6: Clean up excessive blank lines again
            content = re.sub(r'\n{3,}', '\n\n', content)
            
            if content != original_content:
                toml_file.write_text(content)
                fixed_files += 1
                total_fixes += file_fixes
                print(f"  💾 Saved {file_fixes} fixes to {toml_file.name}")
            else:
                print(f"  ✨ No fixes needed for {toml_file.name}")
                
        except Exception as e:
            print(f"  ❌ Error processing {toml_file.name}: {e}")
    
    print(f"\n📊 Layer 3 Results:")
    print(f"   Files processed: {len(toml_files)}")
    print(f"   Files fixed: {fixed_files}")
    print(f"   Total fixes applied: {total_fixes}")

if __name__ == "__main__":
    layer3_fix_specific_errors()