#!/usr/bin/env python3
"""
Automated syntax error fixer for common patterns.
"""
import ast
import re
import os
import shutil
from pathlib import Path

class SyntaxFixer:
    def __init__(self):
        self.fixed_count = 0
        self.patterns = [
            # Missing closing parentheses patterns
            (r'\.hexdigest\(\)\}', r'.hexdigest()}'),
            (r'len\(str\([^)]+\),', r'len(str(\1)),'),
            (r'list\([^)]+\.values\(\)\)', r'list(\1.values())'),
            (r'int\(\s*\([^)]+\)\.total_seconds\(\)\s*\)', r'int((\1).total_seconds())'),
            (r'str\(uuid4\(\)\),', r'str(uuid4()),'),
            (r'datetime\.now\([^)]+\),', r'datetime.now(\1)),'),
            (r'bool\(re\.search\([^)]+\)', r'bool(re.search(\1))'),
            
            # Missing closing brackets/braces
            (r'\.items\(\):', r'.items():'),
            (r'\.values\(\)\s*$', r'.values())'),
            
            # Extra parentheses
            (r'\.values\(\)\)\)', r'.values())'),
        ]
    
    def fix_file(self, file_path: str) -> bool:
        """Fix syntax errors in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Apply regex patterns
            for pattern, replacement in self.patterns:
                content = re.sub(pattern, replacement, content)
            
            # Manual fixes for specific patterns
            content = self.fix_manual_patterns(content)
            
            # Only write if changed
            if content != original_content:
                # Test syntax before saving
                try:
                    ast.parse(content, filename=file_path)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    self.fixed_count += 1
                    return True
                except SyntaxError:
                    # Don't save if still has syntax errors
                    pass
            
            return False
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return False
    
    def fix_manual_patterns(self, content: str) -> str:
        """Fix specific manual patterns."""
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            # Fix common missing parentheses patterns
            if 'uuid.uuid4(' in line and line.count('(') > line.count(')'):
                lines[i] = line + ')'
            
            # Fix datetime patterns
            if 'datetime.now(' in line and line.count('(') > line.count(')'):
                lines[i] = line + ')'
            
            # Fix list comprehension patterns
            if '.values(' in line and line.count('(') > line.count(')') and line.strip().endswith('('):
                lines[i] = line + ')'
        
        return '\n'.join(lines)

def main():
    fixer = SyntaxFixer()
    
    # Target directories
    directories = [
        '/home/dotmac_framework/isp-framework/src',
        '/home/dotmac_framework/management-platform/app'
    ]
    
    total_files = 0
    for directory in directories:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    total_files += 1
                    
                    # Check if file has syntax errors before fixing
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            ast.parse(f.read(), filename=file_path)
                        continue  # Skip files without syntax errors
                    except SyntaxError:
                        pass  # File has syntax errors, attempt to fix
                    except Exception:
                        continue
                    
                    if fixer.fix_file(file_path):
                        print(f"Fixed: {file_path}")
    
    print(f"\nFixed {fixer.fixed_count} files out of {total_files} Python files checked")

if __name__ == "__main__":
    main()