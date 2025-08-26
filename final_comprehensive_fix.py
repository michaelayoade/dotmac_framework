#!/usr/bin/env python3
"""
Final comprehensive fix for all syntax errors.
"""

import os
import re
from pathlib import Path
from datetime import timezone

def fix_comprehensive(file_path: Path):
    """Fix all comprehensive syntax errors in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix double parentheses issues from previous fix attempts
        content = re.sub(r'\)\)', ')', content)
        
        # Fix malformed getLogger calls
        content = re.sub(r'logging\.getLogger\(__name__, timezone\)', 'logging.getLogger(__name__)', content)
        content = re.sub(r'logging\.getLogger\(__name__, timezone\)\)', 'logging.getLogger(__name__)', content)
        
        # Fix malformed class definitions 
        content = re.sub(r'class ([^(]+)\([^)]*timezone\)\):', r'class \1:', content)
        content = re.sub(r'class ([^(]+)\(([^)]*), timezone\)\):', r'class \1(\2):', content)
        
        # Fix enum definitions with timezone
        content = re.sub(r'(class \w+)\(([^)]*), timezone\)\):', r'\1(\2):', content)
        
        # Fix function returns with missing parentheses
        content = re.sub(r'return str\(uuid4\(\)', 'return str(uuid4()))', content)
        
        # Fix datetime calls that are malformed
        content = re.sub(r'datetime\.utcnow\(\)\)', 'datetime.now(timezone.utc)', content)
        content = re.sub(r'datetime\.utcnow\(, timezone\)\)', 'datetime.now(timezone.utc)', content)
        
        # Add timezone import if needed
        if 'timezone.utc' in content and 'from datetime import' in content:
            if not re.search(r'from datetime import[^)]*timezone', content):
                content = re.sub(
                    r'from datetime import ([^, timezone)]+)',
                    lambda m: f'from datetime import {m.group(1, timezone)}, timezone' if 'timezone' not in m.group(1) else m.group(0),
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
    """Main function to fix all comprehensive syntax errors."""
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
                        if any(pattern in content for pattern in [
                            ', timezone)',
                            'timezone)',
                            'getLogger(__name__, timezone',
                            'uuid4()',
                            'datetime.now(timezone.utc)'
                        ]):
                            python_files.append(file_path)
                except:
                    continue
    
    print(f"Found {len(python_files)} files with comprehensive syntax errors")
    
    fixed_count = 0
    for file_path in python_files:
        if fix_comprehensive(file_path):
            fixed_count += 1
    
    print(f"\n🎉 Fixed comprehensive syntax errors in {fixed_count} files")

if __name__ == "__main__":
    main()