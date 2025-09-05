#!/usr/bin/env python3

import os
import re
import subprocess
from pathlib import Path
from typing import List, Tuple

def find_print_statements() -> List[str]:
    """Find all Python files with print statements."""
    result = subprocess.run([
        './.venv/bin/ruff', 'check', '--select=T201', 'src/', '--output-format=json'
    ], capture_output=True, text=True, cwd='.')
    
    if result.returncode != 0:
        print("No print statements found or ruff error")
        return []
    
    import json
    files_with_prints = set()
    try:
        data = json.loads(result.stdout)
        for violation in data:
            files_with_prints.add(violation['filename'])
    except json.JSONDecodeError:
        # Fallback to text parsing
        for line in result.stdout.split('\n'):
            if 'T201' in line and '.py:' in line:
                file_path = line.split(':')[0]
                files_with_prints.add(file_path)
    
    return list(files_with_prints)

def convert_prints_in_file(file_path: str) -> int:
    """Convert print statements to logging in a single file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    conversions = 0
    
    # Add logging import if not present
    has_logging_import = 'import logging' in content or 'from logging import' in content
    if not has_logging_import and 'print(' in content:
        # Find the best place to insert logging import
        lines = content.split('\n')
        import_line = -1
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_line = i
        
        if import_line >= 0:
            lines.insert(import_line + 1, 'import logging')
        else:
            lines.insert(0, 'import logging')
        
        content = '\n'.join(lines)
    
    # Add logger creation after imports
    has_logger = 'logger = logging.getLogger(' in content or 'logging.getLogger(' in content
    if not has_logger and 'print(' in content:
        lines = content.split('\n')
        # Find end of imports
        insert_line = 0
        for i, line in enumerate(lines):
            if not (line.startswith('import ') or line.startswith('from ') or 
                   line.strip() == '' or line.startswith('#')):
                insert_line = i
                break
        
        module_name = os.path.basename(file_path).replace('.py', '')
        lines.insert(insert_line, f'\nlogger = logging.getLogger(__name__)')
        content = '\n'.join(lines)
    
    # Convert print statements
    patterns = [
        # print("message") -> logger.info("message")
        (r'print\((["\'].*?["\'])\)', r'logger.info(\1)'),
        # print(f"message {var}") -> logger.info(f"message {var}")
        (r'print\((f["\'].*?["\'])\)', r'logger.info(\1)'),
        # print(variable) -> logger.info(str(variable))
        (r'print\(([^"\'f][^)]*)\)', r'logger.info(str(\1))'),
    ]
    
    for pattern, replacement in patterns:
        new_content, count = re.subn(pattern, replacement, content)
        if count > 0:
            content = new_content
            conversions += count
    
    # Write back only if changes were made
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
    
    return conversions

def main():
    """Convert all print statements to logging."""
    print("Finding files with print statements...")
    files_with_prints = find_print_statements()
    
    if not files_with_prints:
        print("No print statements found!")
        return
    
    print(f"Found {len(files_with_prints)} files with print statements")
    total_conversions = 0
    
    for file_path in files_with_prints:
        print(f"Converting prints in {file_path}...")
        conversions = convert_prints_in_file(file_path)
        total_conversions += conversions
        if conversions > 0:
            print(f"  Converted {conversions} print statements")
    
    print(f"\nTotal conversions: {total_conversions}")
    print("\nRunning syntax check...")
    
    # Check syntax after conversion
    result = subprocess.run(['python3', '-m', 'py_compile'] + files_with_prints, 
                          capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ All files compile successfully")
    else:
        print("❌ Syntax errors found:")
        print(result.stderr)

if __name__ == '__main__':
    main()