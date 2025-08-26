#!/usr/bin/env python3
"""
Bulk fix malformed __init__ methods with docstrings in parameter lists.
"""

import re
from pathlib import Path

def fix_malformed_init_bulk(file_path: Path):
    """Fix malformed __init__ methods in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern 1: def __init__(        ):\n            """Initialize operation."""
        pattern1 = r'def __init__\(\s*\):\s*\n\s*"""Initialize operation\."""\s*\n(\s*)'
        replacement1 = r'def __init__(self, *args, **kwargs):\n\1"""Initialize operation."""\n\1'
        content = re.sub(pattern1, replacement1, content, flags=re.MULTILINE)
        
        # Pattern 2: def __init__(        ):\n            """Initialize operation."""\n        self.something = something
        pattern2 = r'def __init__\(\s*\):\s*\n\s*"""Initialize operation\."""\s*\n(\s*)(.*?)'
        def replace_init_with_params(match):
            indent = match.group(1)
            next_line = match.group(2)
            return f'def __init__(self, *args, **kwargs):\n{indent}"""Initialize operation."""\n{indent}{next_line}'
        
        content = re.sub(pattern2, replace_init_with_params, content, flags=re.MULTILINE)
        
        # Pattern 3: More general malformed init patterns
        # Look for __init__ methods with malformed parameter lists
        init_pattern = r'(def __init__\(\s*)(\s*)(.*?)(\s*\):)'
        
        def fix_init_params(match):
            prefix = match.group(1)  # "def __init__("
            spacing = match.group(2)  # possible whitespace/newlines
            params = match.group(3)   # parameters
            suffix = match.group(4)   # "):"
            
            # If params is empty or just whitespace, add self
            if not params.strip():
                return f"{prefix}self{suffix}"
            
            # If params doesn't start with self, add it
            if not params.strip().startswith('self'):
                return f"{prefix}self, {params}{suffix}"
            
            return match.group(0)  # No change needed
        
        content = re.sub(init_pattern, fix_init_params, content, flags=re.MULTILINE | re.DOTALL)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Fix all malformed __init__ methods in SDK platform files."""
    print("🔧 Bulk Fixing Malformed __init__ Methods")
    print("=" * 50)
    
    root_path = Path("/home/dotmac_framework/isp-framework/src")
    
    # Focus on platform SDK files that commonly have this issue
    sdk_platform_path = root_path / "dotmac_isp" / "sdks" / "platform"
    
    fixed_files = []
    
    for py_file in sdk_platform_path.glob("*.py"):
        if py_file.name.endswith('_sdk.py'):
            print(f"Processing: {py_file.name}")
            if fix_malformed_init_bulk(py_file):
                fixed_files.append(py_file.name)
                print(f"  ✅ Fixed")
            else:
                print(f"  ⚪ No changes needed")
    
    print(f"\n📊 Summary:")
    print(f"   Fixed {len(fixed_files)} files")
    
    if fixed_files:
        print(f"   Files modified:")
        for filename in fixed_files:
            print(f"     • {filename}")
    
    return len(fixed_files)

if __name__ == "__main__":
    count = main()
    if count > 0:
        print(f"\n🎉 Fixed {count} files. Test the imports now!")
    else:
        print(f"\n💡 No files needed fixing in this batch.")