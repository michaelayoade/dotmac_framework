#!/usr/bin/env python3
"""
Final manual TOML fixes targeting specific remaining issues.
"""

import re
from pathlib import Path
import tomllib

def manual_fix_file(filepath: Path) -> bool:
    """Manually fix specific TOML issues in a file."""
    content = filepath.read_text()
    original = content
    
    # Common issue: Orphaned array/config lines without proper section
    # Pattern: ["src"] or ["py.typed"] appearing without context
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Handle orphaned ["src"] and similar lines
        if (line.startswith('["') and line.endswith('"]') and 
            not any(section in ''.join(lines[max(0,i-3):i]) for section in ['[tool.', '[build-'])):
            print(f"    Removing orphaned array: {line}")
            i += 1
            continue
            
        # Handle lines that look like config but aren't in a section  
        if ('=' in line and not line.startswith('#') and not line.startswith('[') and
            not any('[' in prev_line for prev_line in lines[max(0,i-5):i])):
            print(f"    Removing orphaned config: {line}")
            i += 1
            continue
            
        fixed_lines.append(lines[i])
        i += 1
    
    content = '\n'.join(fixed_lines)
    
    # Fix missing newlines between sections
    content = re.sub(r'(\])\n([a-z_-]+ = )', r'\1\n\n\2', content)
    
    # Fix inline table syntax more aggressively
    content = re.sub(r'\{"([^"]+)":\s*"([^"]+)"\}', r'{\1 = "\2"}', content)
    content = re.sub(r'\{"([^"]+)":\s*(\w+)\}', r'{\1 = \2}', content)
    
    # Clean up whitespace
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = content.strip() + '\n'
    
    if content != original:
        filepath.write_text(content)
        return True
    return False

def final_manual_fixes():
    """Apply final manual fixes to problematic TOML files."""
    
    packages_dir = Path("/home/dotmac_framework/packages")
    
    # Files that need manual attention based on validation
    problem_files = [
        "dotmac-observability",
        "dotmac-tasks-utils", 
        "dotmac-application",
        "dotmac-plugins",
        "dotmac-communications",
        "dotmac-service-kernel",
        "dotmac-core",
        "dotmac-benchmarking", 
        "dotmac-platform-services",
        "dotmac-shared-core"
    ]
    
    fixed_count = 0
    
    for package_name in problem_files:
        toml_file = packages_dir / package_name / "pyproject.toml"
        if not toml_file.exists():
            continue
            
        print(f"\n🔧 Manually fixing {package_name}/pyproject.toml")
        
        try:
            # Test current state
            content = toml_file.read_text()
            try:
                tomllib.loads(content)
                print(f"  ✅ Already valid TOML")
                continue
            except:
                pass
            
            # Apply manual fixes
            if manual_fix_file(toml_file):
                print(f"  💾 Applied manual fixes")
                fixed_count += 1
                
                # Test again
                try:
                    new_content = toml_file.read_text()
                    tomllib.loads(new_content)
                    print(f"  ✅ Now valid TOML")
                except Exception as e:
                    print(f"  ⚠️  Still has issues: {e}")
            else:
                print(f"  ✨ No changes made")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print(f"\n📊 Manual Fixes Results:")
    print(f"   Files processed: {len(problem_files)}")
    print(f"   Files modified: {fixed_count}")

if __name__ == "__main__":
    final_manual_fixes()