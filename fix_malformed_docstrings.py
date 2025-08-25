#!/usr/bin/env python3
"""
Fix malformed docstrings that cause syntax errors.
Pattern: def __init__(\n    \"\"\"  Init   operation.\"\"\"\n    self, ...
Should be: def __init__(self, ...):\n    \"\"\"Initialize...\"""
"""

import os
import re
from pathlib import Path

def fix_malformed_docstring(file_path: Path):
    """Fix malformed docstrings in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern: def __init__(\n    """  Init   operation."""\n    self, ...
        # Replace with: def __init__(self, ...):
        #                   """Initialize operation."""
        
        # First, find and fix the malformed pattern
        pattern = r'(def __init__\(\s*)\n\s*"""  Init   operation\."""\s*\n(\s*)(self.*?\):)'
        replacement = r'\1\2):\n\2    """Initialize operation."""'
        
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
        
        # Handle cases where self is on the same line as def
        pattern2 = r'(def __init__\(\s*"""  Init   operation\."""\s*,?\s*)(self.*?\):)'
        replacement2 = r'def __init__(\2:\n        """Initialize operation."""'
        
        content = re.sub(pattern2, replacement2, content, flags=re.MULTILINE | re.DOTALL)
        
        # More specific pattern for our exact case
        pattern3 = r'def __init__\(\s*\n\s*"""  Init   operation\."""\s*\n\s*(self.*?\):)'
        replacement3 = r'def __init__(\1:\n        """Initialize operation."""'
        
        content = re.sub(pattern3, replacement3, content, flags=re.MULTILINE | re.DOTALL)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    root_path = Path("/home/dotmac_framework/isp-framework/src")
    fixed_files = []
    
    # Find all Python files with the malformed pattern
    for py_file in root_path.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if '"""  Init   operation."""' in content:
                if fix_malformed_docstring(py_file):
                    fixed_files.append(py_file)
                    print(f"Fixed: {py_file.relative_to(root_path)}")
                    
        except Exception as e:
            print(f"Error checking {py_file}: {e}")
    
    print(f"\nFixed {len(fixed_files)} files")
    return fixed_files

if __name__ == "__main__":
    main()