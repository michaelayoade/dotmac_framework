#!/usr/bin/env python3
"""
Systematically fix remaining syntax errors in ISP Framework.
"""

import ast
import os
import re
from pathlib import Path

def fix_malformed_init_docstrings(file_path: Path):
    """Fix malformed __init__ docstrings that cause indentation errors."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern for malformed __init__ with docstring in parameter list
        # def __init__(        ):\n            """Initialize operation."""
        pattern = r'(def __init__\(\s*)\):\s*\n\s*"""Initialize operation\."""\s*\n(\s*)(.*?)'
        
        def replace_malformed_init(match):
            # Extract the indentation level
            indent = match.group(2) if match.group(2) else "        "
            next_line = match.group(3) if match.group(3) else "pass"
            
            # Create proper __init__ with placeholder parameters
            return f'{match.group(1)}self, *args, **kwargs):\n{indent}"""Initialize operation."""\n{indent}{next_line}'
        
        content = re.sub(pattern, replace_malformed_init, content, flags=re.MULTILINE | re.DOTALL)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def find_syntax_errors():
    """Find all Python files with syntax errors."""
    root_path = Path("/home/dotmac_framework/isp-framework/src")
    syntax_errors = []
    
    for py_file in root_path.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Try to parse the AST
            ast.parse(content, filename=str(py_file))
            
        except SyntaxError as e:
            syntax_errors.append({
                'file': py_file,
                'line': e.lineno,
                'error': str(e),
                'relative_path': str(py_file.relative_to(root_path))
            })
        except Exception as e:
            # Other parsing issues
            syntax_errors.append({
                'file': py_file,
                'line': 'unknown',
                'error': f'Parse error: {str(e)}',
                'relative_path': str(py_file.relative_to(root_path))
            })
    
    return syntax_errors

def fix_specific_files():
    """Fix specific known problematic files."""
    fixes = []
    
    # List of files that commonly have malformed docstrings
    problem_files = [
        "dotmac_isp/core/secrets_manager.py",
        "dotmac_isp/core/secure_config_validator_refactor.py", 
        "dotmac_isp/sdks/platform/file_storage_sdk.py",
    ]
    
    root_path = Path("/home/dotmac_framework/isp-framework/src")
    
    for file_rel_path in problem_files:
        file_path = root_path / file_rel_path
        if file_path.exists():
            if fix_malformed_init_docstrings(file_path):
                fixes.append(file_rel_path)
                print(f"✅ Fixed: {file_rel_path}")
            else:
                print(f"⚠️ No changes: {file_rel_path}")
        else:
            print(f"❌ Not found: {file_rel_path}")
    
    return fixes

def main():
    print("🔧 Fixing Remaining Syntax Errors in ISP Framework")
    print("=" * 60)
    
    # First, find all syntax errors
    print("1. Scanning for syntax errors...")
    errors = find_syntax_errors()
    print(f"   Found {len(errors)} files with syntax errors")
    
    if errors:
        print("\n📋 Files with syntax errors:")
        for error in errors[:10]:  # Show first 10
            print(f"   ❌ {error['relative_path']}:{error['line']} - {error['error']}")
        if len(errors) > 10:
            print(f"   ... and {len(errors) - 10} more")
    
    # Try to fix specific known issues
    print(f"\n2. Fixing specific known issues...")
    fixes = fix_specific_files()
    
    # Check progress
    print(f"\n3. Checking progress...")
    remaining_errors = find_syntax_errors()
    print(f"   Remaining syntax errors: {len(remaining_errors)}")
    
    if len(remaining_errors) < len(errors):
        print(f"   ✅ Progress: Fixed {len(errors) - len(remaining_errors)} files")
    
    return remaining_errors

if __name__ == "__main__":
    remaining = main()
    
    if len(remaining) == 0:
        print(f"\n🎉 All syntax errors fixed!")
    else:
        print(f"\n📝 {len(remaining)} syntax errors still need manual fixing")
        print("Top remaining issues:")
        for error in remaining[:5]:
            print(f"   • {error['relative_path']}:{error['line']} - {error['error']}")