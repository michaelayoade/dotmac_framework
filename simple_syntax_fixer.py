#!/usr/bin/env python3
"""
Simple syntax error fixer for common patterns.
"""
import ast
import os
from datetime import timezone

def fix_common_patterns(content: str) -> str:
    """Fix common syntax patterns."""
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        original_line = line
        
        # Fix missing closing parentheses in common patterns
        if 'uuid.uuid4(' in line and line.count('(') > line.count(')'):
            if line.strip().endswith('(') or line.strip().endswith('uuid.uuid4('):
                lines[i] = line + ')'
        
        # Fix missing closing parentheses in list() calls
        if 'list(' in line and '.values(' in line:
            if line.count('(') > line.count(')'):
                lines[i] = line + ')'
        
        # Fix datetime patterns
        if 'datetime.now(' in line and line.count('(') > line.count(')'):
            if 'datetime.now(timezone.utc' in line or 'datetime.now(UTC' in line:
                lines[i] = line + ')'
        
        # Fix len() patterns
        if 'len(str(' in line and line.count('(') > line.count(')'):
            # Count missing closing parens
            open_count = line.count('(')
            close_count = line.count(')')
            missing = open_count - close_count
            lines[i] = line + ')' * missing
        
        # Fix .hexdigest() patterns
        if '.hexdigest(' in line and line.count('(') > line.count(')'):
            lines[i] = line + ')'
        
        # Fix .items() patterns
        if '.items(' in line and line.count('(') > line.count(')'):
            lines[i] = line + ')'
        
        # Fix bool(re.search patterns
        if 'bool(re.search(' in line and line.count('(') > line.count(')'):
            open_count = line.count('(')
            close_count = line.count(')')
            missing = open_count - close_count
            lines[i] = line + ')' * missing
        
        # Remove extra closing parentheses
        if line.strip().endswith('))') and 'return' not in line and 'if' not in line:
            # Check if we have too many closing parens
            open_count = line.count('(')
            close_count = line.count(')')
            if close_count > open_count:
                # Remove one closing paren
                lines[i] = line.rstrip(')') + ')'
    
    return '\n'.join(lines)

def fix_file(file_path: str) -> bool:
    """Fix syntax errors in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if file already has valid syntax
        try:
            ast.parse(content, filename=file_path)
            return False  # No fix needed
        except SyntaxError:
            pass  # Has syntax errors, continue to fix
        
        original_content = content
        fixed_content = fix_common_patterns(content)
        
        # Only write if changed and valid
        if fixed_content != original_content:
            try:
                ast.parse(fixed_content, filename=file_path)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print(f"Fixed: {file_path}")
                return True
            except SyntaxError:
                # Still has errors, don't save
                pass
        
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    directories = [
        '/home/dotmac_framework/isp-framework/src',
        '/home/dotmac_framework/management-platform/app'
    ]
    
    total_fixed = 0
    total_checked = 0
    
    for directory in directories:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    total_checked += 1
                    if fix_file(file_path):
                        total_fixed += 1
    
    print(f"\nFixed {total_fixed} files out of {total_checked} Python files checked")

if __name__ == "__main__":
    main()