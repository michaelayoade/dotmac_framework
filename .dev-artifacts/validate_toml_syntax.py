#!/usr/bin/env python3
"""
Validate TOML syntax for all pyproject.toml files and identify remaining issues.
"""

import tomllib
from pathlib import Path

def validate_toml_files():
    """Validate all pyproject.toml files and report syntax issues."""
    
    packages_dir = Path("/home/dotmac_framework/packages")
    toml_files = list(packages_dir.glob("*/pyproject.toml"))
    
    print(f"🔍 Validating {len(toml_files)} pyproject.toml files")
    
    valid_files = 0
    invalid_files = 0
    
    for toml_file in toml_files:
        print(f"\n📝 Validating {toml_file.relative_to(Path.cwd())}")
        
        try:
            content = toml_file.read_text()
            
            # Try to parse with tomllib
            parsed = tomllib.loads(content)
            print(f"  ✅ Valid TOML syntax")
            valid_files += 1
            
            # Quick check for Poetry structure
            if 'build-system' in parsed and parsed.get('build-system', {}).get('build-backend') == 'poetry.core.masonry.api':
                print(f"  📦 Poetry build system configured")
            else:
                print(f"  ⚠️  Non-Poetry build system")
                
        except tomllib.TOMLDecodeError as e:
            print(f"  ❌ TOML syntax error: {e}")
            invalid_files += 1
            
            # Show the problematic line for debugging
            lines = content.split('\n')
            if hasattr(e, 'lineno') and e.lineno <= len(lines):
                problem_line = lines[e.lineno - 1] if e.lineno > 0 else "Unknown line"
                print(f"     Line {e.lineno}: {problem_line}")
        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
            invalid_files += 1
    
    print(f"\n📊 Validation Results:")
    print(f"   Total files: {len(toml_files)}")
    print(f"   Valid TOML: {valid_files}")
    print(f"   Invalid TOML: {invalid_files}")
    
    if invalid_files == 0:
        print("   🎉 All files have valid TOML syntax!")
    else:
        print(f"   🔧 {invalid_files} files need additional fixes")

if __name__ == "__main__":
    validate_toml_files()