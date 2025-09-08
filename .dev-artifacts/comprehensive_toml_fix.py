#!/usr/bin/env python3

import re
from pathlib import Path

def comprehensive_toml_fix():
    """Comprehensively fix TOML formatting issues."""
    
    packages_dir = Path("packages")
    fixed_count = 0
    error_count = 0
    
    for pyproject_file in packages_dir.rglob("pyproject.toml"):
        try:
            # Read the file content
            content = pyproject_file.read_text()
            original_content = content
            
            # 1. Fix version/description/authors line merging
            content = re.sub(r'version = "([^"]+)"description = "([^"]+)"authors = (\[[^\]]+\])', 
                           r'version = "\1"\ndescription = "\2"\nauthors = \3', content)
            
            # 2. Fix dependency concatenation on single lines
            # Split concatenated dependencies
            content = re.sub(r'(python = "[^"]+")([\w-]+ = )', r'\1\n\2', content)
            content = re.sub(r'(">=?[^"]+")([\w-]+ = )', r'\1\n\2', content)
            content = re.sub(r'(\})([\w-]+ = )', r'\1\n\2', content)
            
            # 3. Fix tool section headers that got merged
            content = re.sub(r'(\[tool\.[^\]]+\])\n([a-z_]+ = )', r'\1\n\n\2', content)
            
            # 4. Add newlines between major sections
            content = re.sub(r'(\[tool\.poetry\.dependencies\])\n([^[]+)(\[tool\.poetry\.group\.dev\.dependencies\])', 
                           r'\1\n\2\n\3', content)
            
            # 5. Fix merged config lines
            content = re.sub(r'(asyncio_mode = "auto")([a-z_])', r'\1\n\2', content)
            content = re.sub(r'(target-version = "py39")([a-z_])', r'\1\n\2', content)
            content = re.sub(r'(line-length = \d+)([a-z_])', r'\1\n\2', content)
            
            # 6. Fix testpath split issue
            content = re.sub(r'testpath\ns = ', 'testpaths = ', content)
            content = re.sub(r'addopts = ([^[]+)testpath', r'addopts = \1\ntestpath', content)
            content = re.sub(r'asyncio_mod\ne = ', 'asyncio_mode = ', content)
            content = re.sub(r'marker\ns = ', 'markers = ', content)
            
            # Write back if changed
            if content != original_content:
                pyproject_file.write_text(content)
                print(f"✅ Fixed: {pyproject_file}")
                fixed_count += 1
            else:
                print(f"⏭️  No changes needed: {pyproject_file}")
                
        except Exception as e:
            print(f"❌ Error processing {pyproject_file}: {e}")
            error_count += 1
    
    print(f"\n📊 Summary:")
    print(f"   Fixed: {fixed_count} files")
    print(f"   Errors: {error_count} files")

if __name__ == "__main__":
    comprehensive_toml_fix()