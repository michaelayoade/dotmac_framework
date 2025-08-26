#!/usr/bin/env python3
"""
Fix various syntax errors introduced by previous fixes.
"""

import os
import re
from pathlib import Path
from datetime import timezone

def fix_syntax_errors(file_path: Path):
    """Fix syntax errors in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix malformed logging.getLogger calls
        content = re.sub(
            r'logger = logging\.getLogger\(__name__, timezone\)',
            'logger = logging.getLogger(__name__)',
            content
        )
        
        # Fix malformed function calls with extra timezone parameter
        content = re.sub(
            r'([a-zA-Z_][a-zA-Z0-9_]*)\(([^)]*), timezone\)',
            r'\1(\2)',
            content
        )
        
        # Fix malformed class definitions
        content = re.sub(
            r'class ([a-zA-Z_][a-zA-Z0-9_]*)\(([^)]*), timezone\):',
            r'class \1(\2):',
            content
        )
        
        # Fix malformed method calls
        content = re.sub(
            r'([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*)\(([^)]*), timezone\)',
            r'\1(\2)',
            content
        )
        
        # Fix malformed datetime calls (from previous fix attempts)
        content = re.sub(
            r'datetime\.utcnow\(, timezone\)',
            'datetime.now(timezone.utc)',
            content
        )
        
        content = re.sub(
            r'datetime\.fromisoformat\(([^,]+), timezone\)',
            r'datetime.fromisoformat(\1)',
            content
        )
        
        # Fix date.today calls
        content = re.sub(
            r'date\.today\(, timezone\)',
            'date.today()',
            content
        )
        
        # Fix function definitions with malformed timezone param
        content = re.sub(
            r'def ([a-zA-Z_][a-zA-Z0-9_]*)\(([^)]*), timezone\):',
            r'def \1(\2):',
            content
        )
        
        # Fix router definitions
        content = re.sub(
            r'router = APIRouter\(([^)]*), timezone\)',
            r'router = APIRouter(\1)',
            content
        )
        
        # Fix security declarations
        content = re.sub(
            r'security = HTTPBearer\(, timezone\)',
            'security = HTTPBearer()',
            content
        )
        
        # Fix settings calls
        content = re.sub(
            r'settings = get_settings\(, timezone\)',
            'settings = get_settings()',
            content
        )
        
        # Fix empty parentheses with timezone
        content = re.sub(
            r'\(, timezone\)',
            '()',
            content
        )
        
        # Add timezone import if needed and timezone.utc is used
        if 'timezone.utc' in content and 'from datetime import' in content:
            # Check if timezone is already imported
            if not re.search(r'from datetime import.*timezone', content):
                content = re.sub(
                    r'from datetime import ([^)]+)',
                    lambda m: f'from datetime import {m.group(1)}, timezone' if 'timezone' not in m.group(1) else m.group(0),
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
    """Main function to fix all syntax errors."""
    framework_root = Path(__file__).parent
    
    # Find Python files with syntax issues
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
                        if ')' in content:
                            python_files.append(file_path)
                except:
                    continue
    
    print(f"Found {len(python_files)} files with syntax errors")
    
    fixed_count = 0
    for file_path in python_files:
        if fix_syntax_errors(file_path):
            fixed_count += 1
    
    print(f"\n🎉 Fixed syntax errors in {fixed_count} files")

if __name__ == "__main__":
    main()