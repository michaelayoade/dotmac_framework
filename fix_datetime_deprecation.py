#!/usr/bin/env python3
"""
Fix datetime.now(timezone.utc) deprecation warnings for Python 3.12+.
Updates datetime.now(timezone.utc) to datetime.now(timezone.utc).
"""

import os
import re
from pathlib import Path
from datetime import timezone

def fix_datetime_deprecation(file_path: Path):
    """Fix datetime deprecation warnings in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Add timezone import if needed and datetime.utcnow is present
        if 'datetime.now(timezone.utc)' in content or '.utcnow()' in content:
            # Check if timezone is already imported
            if 'from datetime import' in content and 'timezone' not in content:
                # Add timezone to existing datetime import
                content = re.sub(
                    r'from datetime import ([^)]+)',
                    lambda m: f'from datetime import {m.group(1)}, timezone' if 'timezone' not in m.group(1) else m.group(0),
                    content
                )
            elif 'import datetime' in content and 'from datetime import' not in content:
                # Add timezone import after datetime import
                content = re.sub(
                    r'(import datetime)',
                    r'\1\nfrom datetime import timezone',
                    content
                )
        
        # Replace datetime.now(timezone.utc) patterns
        content = re.sub(
            r'datetime\.datetime\.utcnow\(\)',
            'datetime.datetime.now(datetime.timezone.utc)',
            content
        )
        
        content = re.sub(
            r'datetime\.utcnow\(\)',
            'datetime.now(timezone.utc)',
            content
        )
        
        # Handle cases where datetime is imported directly
        content = re.sub(
            r'(\w+)\.utcnow\(\)',
            lambda m: f'{m.group(1)}.now(timezone.utc)' if m.group(1) == 'datetime' else m.group(0),
            content
        )
        
        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed {file_path}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False

def main():
    """Main function to fix all datetime deprecation warnings."""
    framework_root = Path(__file__).parent
    
    # Find Python files with datetime.utcnow usage
    python_files = []
    for root, dirs, files in os.walk(framework_root):
        # Skip certain directories
        if any(skip in root for skip in ['.git', '__pycache__', 'node_modules', '.venv', 'venv', 'docs-env']):
            continue
            
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if '.utcnow()' in content:
                            python_files.append(file_path)
                except:
                    continue
    
    print(f"Found {len(python_files)} files with datetime.now(timezone.utc) usage")
    
    fixed_count = 0
    for file_path in python_files:
        if fix_datetime_deprecation(file_path):
            fixed_count += 1
    
    print(f"\n🎉 Fixed datetime deprecation warnings in {fixed_count} files")

if __name__ == "__main__":
    main()