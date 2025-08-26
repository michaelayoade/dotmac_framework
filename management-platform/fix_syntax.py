#!/usr/bin/env python3
"""
Script to fix common syntax errors in the management platform codebase.
"""
import os
import re
from pathlib import Path
from datetime import timezone

def fix_common_syntax_patterns(content):
    """Fix common syntax patterns in the content."""
    fixes = [
        # Fix datetime.utcnow(, timezone) -> datetime.now(timezone.utc)
        (r'datetime\.utcnow\(\s*,\s*timezone\)', 'datetime.now(timezone.utc)'),
        
        # Fix missing closing parentheses in function calls
        (r'(\w+\([^)]*)\n\s*SyntaxError:', r'\1)'),
        
        # Fix UUID.uuid4() missing closing paren
        (r'UUID\.uuid4\(\s*$', 'UUID.uuid4()'),
        
        # Fix str(UUID.uuid4() missing closing paren
        (r'str\(UUID\.uuid4\(\s*$', 'str(UUID.uuid4())'),
        
        # Fix hashlib calls missing closing paren
        (r'hashlib\.sha256\([^)]*\.encode\(\)\.hexdigest\(\s*$', lambda m: m.group(0) + ')'),
        
        # Fix f-string with missing closing brace
        (r'f"[^"]*\{[^}]*$', lambda m: m.group(0) + '}'),
        
        # Fix select statements with missing closing paren
        (r'select\([^)]*\n\s*SyntaxError:', lambda m: m.group(0).replace('\nSyntaxError:', ')')),
    ]
    
    for pattern, replacement in fixes:
        if callable(replacement):
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        else:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    return content

def process_file(file_path):
    """Process a single file to fix syntax errors."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        content = fix_common_syntax_patterns(content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to process all Python files."""
    app_dir = Path("app")
    
    if not app_dir.exists():
        print("app/ directory not found. Run from management-platform root.")
        return
    
    python_files = list(app_dir.rglob("*.py"))
    fixed_count = 0
    
    for file_path in python_files:
        if process_file(file_path):
            fixed_count += 1
    
    print(f"Processed {len(python_files)} files, fixed {fixed_count} files")

if __name__ == "__main__":
    main()